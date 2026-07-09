import unittest
from unittest.mock import patch


class StageThreeFunctionCallingContractTests(unittest.TestCase):
    def test_tool_schemas_can_be_imported(self):
        from app.schemas.tools import ToolAskRequest, ToolAskResponse, ToolCallRecord

        request = ToolAskRequest(question="SV300伺服电机E-05报警怎么处理？")
        response = ToolAskResponse(
            message="ok",
            answer="answer",
            sources=[],
            tool_calls=[],
            session_id="session-001",
        )

        self.assertEqual(request.question, "SV300伺服电机E-05报警怎么处理？")
        self.assertEqual(response.session_id, "session-001")
        self.assertTrue(hasattr(ToolCallRecord, "__annotations__"))

    def test_tool_specs_contains_four_openai_compatible_tools(self):
        from app.tools.tool_specs import TOOL_SPECS

        tool_names = {tool["function"]["name"] for tool in TOOL_SPECS}
        self.assertEqual(
            tool_names,
            {
                "search_knowledge_base",
                "query_device_info",
                "query_alarm_records",
                "query_maintenance_records",
            },
        )

        for tool in TOOL_SPECS:
            self.assertEqual(tool["type"], "function")
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])

    def test_tool_executor_enforces_whitelist_and_returns_error_for_unknown_tool(self):
        from app.tools.tool_executor import ALLOWED_TOOLS, execute_tool_call

        self.assertEqual(
            set(ALLOWED_TOOLS),
            {
                "search_knowledge_base",
                "query_device_info",
                "query_alarm_records",
                "query_maintenance_records",
            },
        )

        result = execute_tool_call("unknown_tool", {})

        self.assertIsInstance(result, dict)
        self.assertEqual(result["tool_name"], "unknown_tool")
        self.assertEqual(result["success"], False)
        self.assertIn("未知工具", result["summary"])
        self.assertIn("result_preview", result)

    def test_tool_executor_calls_allowed_tool_and_builds_tool_call_record(self):
        from app.tools import tool_executor

        fake_result = {
            "success": True,
            "tool_name": "query_device_info",
            "device_code": "SV300-01",
            "data": {"device_name": "SV300伺服电机"},
            "summary": "已查询到设备基础信息。",
        }

        with patch.object(tool_executor, "query_device_info", return_value=fake_result):
            result = tool_executor.execute_tool_call("query_device_info", {"device_code": "SV300-01"})

        self.assertEqual(result["tool_name"], "query_device_info")
        self.assertEqual(result["arguments"], {"device_code": "SV300-01"})
        self.assertEqual(result["success"], True)
        self.assertEqual(result["summary"], "已查询到设备基础信息。")
        self.assertIn("SV300", result["result_preview"])

    def test_tool_chat_fallback_returns_answer_sources_tool_calls_and_session_id(self):
        from app.tools import tool_chat

        fake_calls = [
            {
                "tool_name": "query_device_info",
                "arguments": {"device_code": "CNC-X200"},
                "success": True,
                "summary": "已查询到设备基础信息。",
                "result_preview": "CNC_X200数控加工中心",
                "result": {"data": {"device_name": "CNC_X200数控加工中心"}},
            }
        ]

        with patch.object(tool_chat, "_select_tools_with_model", return_value=[]), patch.object(
            tool_chat, "_select_tools_by_keywords", return_value=[("query_device_info", {"device_code": "CNC-X200"})]
        ), patch.object(tool_chat, "execute_tool_call", return_value=fake_calls[0]), patch.object(
            tool_chat, "_generate_final_answer", return_value="CNC_X200设备基础信息如下。"
        ):
            result = tool_chat.ask_with_tools(
                question="CNC_X200设备的基础信息是什么？",
                session_id="tool-session-003",
                device_code="CNC-X200",
            )

        self.assertEqual(result["session_id"], "tool-session-003")
        self.assertEqual(result["answer"], "CNC_X200设备基础信息如下。")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["tool_calls"][0]["tool_name"], "query_device_info")

    def test_main_registers_tool_chat_router_without_replacing_original_chat_route(self):
        main_content = _read_file("app/main.py")
        chat_content = _read_file("app/api/chat.py")
        tool_chat_content = _read_file("app/api/tool_chat.py")

        self.assertIn("tool_chat", main_content)
        self.assertIn("app.include_router(chat.router)", main_content)
        self.assertIn("app.include_router(tool_chat.router)", main_content)
        self.assertIn('@router.post("/ask"', chat_content)
        self.assertIn('@router.post("/ask-with-tools"', tool_chat_content)


def _read_file(path: str) -> str:
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
