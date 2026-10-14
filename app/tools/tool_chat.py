import json
import logging
from typing import Optional
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.tools.tool_executor import execute_tool_call
from app.tools.tool_specs import TOOL_SPECS

# 多轮工具调用的最大轮数（成本护栏：防止模型反复调用工具）
MAX_TOOL_ROUNDS = 2
logger = logging.getLogger(__name__)


def ask_with_tools(question: str, session_id: Optional[str] = None, device_code: Optional[str] = None) -> dict:
    resolved_session_id = session_id or str(uuid4())

    tool_call_records, loop_answer = _run_tool_loop(question, device_code)

    sources = _collect_sources(tool_call_records)

    if loop_answer and loop_answer.strip():
        # 模型在工具闭环中直接给出了最终回答
        answer = loop_answer
    else:
        answer = _generate_final_answer(question, tool_call_records)

    return {
        "message": "已基于工具调用结果生成回答。" if tool_call_records else "已生成回答。",
        "answer": answer,
        "sources": sources,
        "tool_calls": [_public_tool_call(record) for record in tool_call_records],
        "session_id": resolved_session_id,
    }


def _run_tool_loop(question: str, device_code: Optional[str]) -> tuple:
    """标准 Function Calling 多轮闭环。

    流程：模型选择工具 -> 执行工具 -> 工具结果以 tool 消息（带 tool_call_id）
    回传给模型 -> 模型基于结果继续调用或直接作答；最多 MAX_TOOL_ROUNDS 轮。
    相同查询复用结果；后续模型失败保留记录，仅在尚无结果时使用关键词兜底。

    返回 (tool_call_records, final_answer_or_empty)。
    """
    records = []
    cached_results = {}
    try:
        from app.core.llm import get_chat_model

        model = get_chat_model()
        messages = [
            SystemMessage(
                "你是工业设备运维助手。请根据用户问题选择并调用工具；"
                "可以多轮调用工具，直到获得足够信息后直接给出最终回答，"
                "不要编造工具结果。"
            ),
            HumanMessage(
                "用户问题：{question}\n设备编码：{device_code}".format(
                    question=question,
                    device_code=device_code or "未提供",
                )
            ),
        ]

        if not hasattr(model, "bind_tools"):
            raise RuntimeError("当前模型不支持工具绑定")

        bound_model = model.bind_tools(TOOL_SPECS)
        response = bound_model.invoke(messages)

        for _ in range(MAX_TOOL_ROUNDS):
            calls = _normalize_tool_calls(
                _extract_tool_calls_full(response), question, device_code
            )
            if not calls:
                answer = _response_text(response)
                if answer:
                    return records, answer
                raise RuntimeError("模型未返回工具调用或回答")

            message_calls = [
                {"name": call["name"], "args": call["args"], "id": call["id"], "type": "tool_call"}
                for call in calls
            ]
            # 一个模型响应对应一个 assistant 消息，保留原文、元数据和调用 ID。
            if isinstance(response, AIMessage):
                assistant_message = response.model_copy(update={
                    "tool_calls": message_calls,
                    "invalid_tool_calls": [],
                    "additional_kwargs": {
                        key: value for key, value in response.additional_kwargs.items()
                        if key != "tool_calls"
                    },
                })
            else:
                assistant_message = AIMessage(
                    content=_response_text(response), tool_calls=message_calls
                )
            messages.append(assistant_message)

            for call in calls:
                tool_name, arguments = call["name"], call["args"]
                if call.get("argument_error"):
                    result = {"success": False, "summary": call["argument_error"]}
                    record = {
                        "tool_name": tool_name, "arguments": arguments,
                        "success": False, "summary": result["summary"],
                        "result_preview": json.dumps(result, ensure_ascii=False),
                        "result": result,
                    }
                    records.append(record)
                else:
                    key = (tool_name, json.dumps(arguments, ensure_ascii=False, sort_keys=True))
                    if key not in cached_results:
                        cached_results[key] = execute_tool_call(tool_name, arguments)
                        records.append(cached_results[key])
                    record = cached_results[key]
                messages.append(
                    ToolMessage(
                        content=json.dumps(
                            record.get("result", {}),
                            ensure_ascii=False,
                            default=str,
                        ),
                        tool_call_id=call["id"],
                    )
                )

            response = bound_model.invoke(messages)
            if not _extract_tool_calls_full(response):
                return records, _response_text(response)

        return records, ""
    except Exception as exc:
        logger.warning(
            "工具循环异常：%s；保留 %d 条已完成记录。",
            type(exc).__name__, len(records),
        )
        if records:
            return records, ""
        selected = _select_tools_by_keywords(question, device_code)
        return [
            execute_tool_call(tool_name, arguments)
            for tool_name, arguments in selected
        ], ""


def _response_text(response) -> str:
    content = getattr(response, "content", "") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item if isinstance(item, str) else item.get("text", "")
            for item in content
            if isinstance(item, str) or (isinstance(item, dict) and isinstance(item.get("text"), str))
        )
    return ""


def _normalize_tool_calls(calls, question, device_code):
    normalized = []
    for call in calls:
        arguments = call["args"]
        argument_error = ""
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                argument_error = "工具参数格式错误：arguments 不是合法 JSON。"
        if not isinstance(arguments, dict):
            argument_error = argument_error or "工具参数格式错误：arguments 必须是对象。"
            arguments = {}
        else:
            arguments = dict(arguments)
        if not argument_error:
            if call["name"] == "search_knowledge_base":
                arguments.setdefault("query", question)
            if device_code:
                arguments.setdefault("device_code", device_code)
        normalized.append({**call, "args": arguments, "argument_error": argument_error})
    return normalized


def _extract_tool_calls_full(response) -> list:
    """提取带 id 的工具调用，供多轮闭环回传 tool 消息使用。

    返回 [{"name": str, "args": 原始参数, "id": str}]；每轮随后归一化参数。
    id 缺失时自动生成；非法参数保留供模型接收错误反馈并修正。
    """
    tool_calls = list(getattr(response, "tool_calls", None) or [])
    tool_calls.extend(getattr(response, "invalid_tool_calls", None) or [])
    if tool_calls:
        extracted = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name") or call.get("tool_name")
            args = call.get("args", call.get("arguments", {}))
            if name:
                extracted.append({
                    "name": name,
                    "args": args,
                    "id": call.get("id") or str(uuid4()),
                })
        return extracted

    additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
    raw_tool_calls = additional_kwargs.get("tool_calls") or []
    extracted = []
    for call in raw_tool_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function", {}) or {}
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        arguments = function.get("arguments", {})
        if name:
            extracted.append({
                "name": name,
                "args": arguments,
                "id": call.get("id") or str(uuid4()),
            })
    return extracted


def _select_tools_by_keywords(question: str, device_code: Optional[str]) -> list:
    calls = []
    if _contains_any(question, ["报警", "历史报警"]):
        if device_code:
            calls.append(("query_alarm_records", {"device_code": device_code, "limit": 5}))
    if _contains_any(question, ["维修", "工单", "历史维修"]):
        if device_code:
            calls.append(("query_maintenance_records", {"device_code": device_code, "limit": 5}))
    if _contains_any(question, ["设备信息", "基础信息", "位置", "厂家", "状态"]):
        if device_code:
            calls.append(("query_device_info", {"device_code": device_code}))
    if not calls or _contains_any(question, ["故障", "排查", "怎么处理", "原因", "建议"]):
        calls.insert(0, ("search_knowledge_base", {"query": question, "device_code": device_code}))
    return _dedupe_calls(calls)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _dedupe_calls(calls: list) -> list:
    result = []
    seen = set()
    for tool_name, arguments in calls:
        key = (tool_name, json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str))
        if key not in seen:
            result.append((tool_name, arguments))
            seen.add(key)
    return result


def _generate_final_answer(question: str, tool_call_records: list) -> str:
    context = _build_tool_context(tool_call_records)
    try:
        from app.core.llm import get_chat_model

        prompt = f"""
你是制造业设备运维助手。请基于工具调用结果回答用户问题。

要求：
1. 优先使用工具结果中的事实。
2. 如果知识库没有可靠依据，请明确说明，不要编造来源。
3. 回答聚焦故障原因、排查步骤和维修建议。
4. 不要声称使用了未调用的工具。

用户问题：
{question}

工具调用结果：
{context}
"""
        response = get_chat_model().invoke(prompt)
        return getattr(response, "content", str(response))
    except Exception as exc:
        logger.warning("工具结果回答生成失败：%s；使用已有结果生成本地回答。", type(exc).__name__)
        return _fallback_answer(question, tool_call_records)


def _build_tool_context(tool_call_records: list) -> str:
    blocks = []
    for index, record in enumerate(tool_call_records, start=1):
        blocks.append(
            "工具{index}: {tool_name}\n参数: {arguments}\n是否成功: {success}\n摘要: {summary}\n结果: {result}".format(
                index=index,
                tool_name=record.get("tool_name"),
                arguments=json.dumps(record.get("arguments", {}), ensure_ascii=False, default=str),
                success=record.get("success"),
                summary=record.get("summary"),
                result=json.dumps(record.get("result", {}), ensure_ascii=False, default=str),
            )
        )
    return "\n\n".join(blocks)


def _fallback_answer(question: str, tool_call_records: list) -> str:
    if not tool_call_records:
        return f"问题：{question}\n\n当前没有可用工具结果，建议先检查设备状态、报警记录和维修记录。"

    summaries = [f"- {record.get('tool_name')}: {record.get('summary')}" for record in tool_call_records]
    return (
        f"问题：{question}\n\n"
        "已完成以下工具查询：\n"
        + "\n".join(summaries)
        + "\n\n建议结合以上工具结果，优先核对报警码、最近维修记录、设备状态和知识库中的排查步骤。"
    )


def _collect_sources(tool_call_records: list) -> list:
    sources = []
    for record in tool_call_records:
        result = record.get("result", {})
        for source in result.get("sources", []) or []:
            sources.append(source)
    return sources


def _public_tool_call(record: dict) -> dict:
    return {
        "tool_name": record.get("tool_name", ""),
        "arguments": record.get("arguments", {}),
        "success": bool(record.get("success", False)),
        "summary": record.get("summary", ""),
        "result_preview": record.get("result_preview", ""),
    }
