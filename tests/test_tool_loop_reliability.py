import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

from app.core import llm
from app.tools import tool_chat, tool_executor


class FakeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.histories = []

    def bind_tools(self, _specs):
        return self

    def invoke(self, messages):
        self.histories.append(list(messages))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id}


class ToolLoopReliabilityTests(unittest.TestCase):
    def test_two_rounds_keep_model_ids_and_parse_raw_json_arguments(self):
        model = FakeModel([
            AIMessage(content="先查设备", tool_calls=[call("query_device_info", {"device_code": "SV300-01"}, "device-1")]),
            SimpleNamespace(content="再查报警", tool_calls=[], additional_kwargs={"tool_calls": [{"id": "alarm-2", "function": {"name": "query_alarm_records", "arguments": '{"device_code":"SV300-01"}'}}]}),
            AIMessage(content="最终结论"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(
            tool_executor, "query_device_info", return_value={"success": True, "summary": "设备正常"}
        ) as device, patch.object(
            tool_executor, "query_alarm_records", return_value={"success": True, "summary": "报警记录"}
        ) as alarm:
            records, answer = tool_chat._run_tool_loop("报警历史", "SV300-01")
        self.assertEqual(answer, "最终结论")
        self.assertEqual(len(records), 2)
        self.assertEqual(device.call_count, 1)
        self.assertEqual(alarm.call_count, 1)
        final_messages = model.histories[-1]
        self.assertEqual([m.tool_call_id for m in final_messages if isinstance(m, ToolMessage)], ["device-1", "alarm-2"])
        self.assertEqual([m.content for m in final_messages if isinstance(m, AIMessage)], ["先查设备", "再查报警"])

    def test_model_failure_after_retrieval_keeps_sources_without_reexecuting_tools(self):
        source = {"file_name": "manual.txt", "content_preview": "已取得的证据"}
        model = FakeModel([
            AIMessage(content="", tool_calls=[call("search_knowledge_base", {"query": "q"}, "kb-1")]),
            RuntimeError("post-tool timeout"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(
            tool_executor, "search_knowledge_base", return_value={"success": True, "sources": [source], "summary": "已找到证据"}
        ) as search, patch.object(tool_executor, "query_alarm_records") as alarm:
            records, answer = tool_chat._run_tool_loop("报警历史", "SV300-01")
        self.assertEqual(search.call_count, 1)
        alarm.assert_not_called()
        self.assertEqual(tool_chat._collect_sources(records), [source])
        self.assertEqual(answer, "")

    def test_repeated_query_uses_cached_result_but_replies_to_each_call_id(self):
        args = {"device_code": "SV300-01"}
        model = FakeModel([
            AIMessage(content="", tool_calls=[call("query_device_info", args, "first")]),
            AIMessage(content="", tool_calls=[call("query_device_info", args, "repeat")]),
            AIMessage(content="最终结论"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(
            tool_executor, "query_device_info", return_value={"success": True, "summary": "设备信息"}
        ) as device:
            records, answer = tool_chat._run_tool_loop("设备信息", "SV300-01")
        self.assertEqual(device.call_count, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(answer, "最终结论")
        self.assertEqual([m.tool_call_id for m in model.histories[-1] if isinstance(m, ToolMessage)], ["first", "repeat"])

    def test_direct_model_answer_does_not_trigger_keyword_tools(self):
        model = FakeModel([AIMessage(content="你好，请提供设备问题。")])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(tool_chat, "execute_tool_call") as execute:
            records, answer = tool_chat._run_tool_loop("你好", None)
        execute.assert_not_called()
        self.assertEqual(records, [])
        self.assertEqual(answer, "你好，请提供设备问题。")

    def test_parallel_tool_calls_share_one_assistant_message(self):
        model = FakeModel([
            AIMessage(content="同时查询", tool_calls=[call("query_device_info", {}, "device"), call("query_alarm_records", {}, "alarm")]),
            AIMessage(content="完成"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(
            tool_executor, "query_device_info", return_value={"success": True}
        ) as device, patch.object(tool_executor, "query_alarm_records", return_value={"success": True}) as alarm:
            records, answer = tool_chat._run_tool_loop("报警和设备信息", "SV300-01")
        self.assertEqual(len(records), 2)
        self.assertEqual(answer, "完成")
        device.assert_called_once_with(device_code="SV300-01")
        alarm.assert_called_once_with(device_code="SV300-01")
        assistants = [m for m in model.histories[-1] if isinstance(m, AIMessage)]
        self.assertEqual(len(assistants), 1)
        self.assertEqual(len(assistants[0].tool_calls), 2)

    def test_invalid_json_arguments_are_reported_to_model_without_executing(self):
        model = FakeModel([
            SimpleNamespace(content="", tool_calls=[], additional_kwargs={"tool_calls": [{"id": "bad-args", "function": {"name": "query_device_info", "arguments": "not-json"}}]}),
            AIMessage(content="参数格式错误，请确认设备编码。"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(tool_chat, "execute_tool_call") as execute:
            records, answer = tool_chat._run_tool_loop("设备信息", "SV300-01")
        execute.assert_not_called()
        self.assertFalse(records[0]["success"])
        self.assertIn("参数", records[0]["summary"])
        self.assertEqual(answer, "参数格式错误，请确认设备编码。")

    def test_tool_round_limit_does_not_execute_next_requested_tool(self):
        model = FakeModel([
            AIMessage(content="", tool_calls=[call("query_device_info", {"device_code": "A"}, "1")]),
            AIMessage(content="", tool_calls=[call("query_device_info", {"device_code": "B"}, "2")]),
            AIMessage(content="", tool_calls=[call("query_device_info", {"device_code": "C"}, "3")]),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(
            tool_executor, "query_device_info", return_value={"success": True}
        ) as device:
            records, answer = tool_chat._run_tool_loop("设备信息", None)
        self.assertEqual(device.call_count, 2)
        self.assertEqual(len(records), 2)
        self.assertEqual(answer, "")

    def test_native_invalid_tool_call_is_returned_as_error_for_model_repair(self):
        model = FakeModel([
            AIMessage(content="", additional_kwargs={"tool_calls": [{"id": "invalid-native", "type": "function", "function": {"name": "query_device_info", "arguments": "not-json"}}]}),
            AIMessage(content="参数有误"),
        ])
        with patch.object(llm, "get_chat_model", return_value=model), patch.object(tool_chat, "execute_tool_call") as execute:
            records, answer = tool_chat._run_tool_loop("设备信息", "SV300-01")
        execute.assert_not_called()
        self.assertFalse(records[0]["success"])
        self.assertEqual(answer, "参数有误")
        tool_messages = [m for m in model.histories[-1] if isinstance(m, ToolMessage)]
        self.assertEqual(tool_messages[0].tool_call_id, "invalid-native")
        assistant = next(m for m in model.histories[-1] if isinstance(m, AIMessage))
        self.assertEqual(assistant.invalid_tool_calls, [])

    def test_retrieval_mode_survives_source_schema_serialization(self):
        from app.rag.qa import build_sources
        from app.schemas.rag import AskResponse

        sources = build_sources([{"content": "本地文档依据", "metadata": {"file_name": "manual.txt"}, "similarity_score": 0.3, "retrieval_mode": "local_keyword"}])
        response = AskResponse(message="ok", answer="回答", sources=sources, session_id="test")
        self.assertEqual(response.model_dump()["sources"][0]["retrieval_mode"], "local_keyword")


if __name__ == "__main__":
    unittest.main()
