import json
from typing import Optional
from uuid import uuid4

from app.tools.tool_executor import execute_tool_call
from app.tools.tool_specs import TOOL_SPECS


def ask_with_tools(question: str, session_id: Optional[str] = None, device_code: Optional[str] = None) -> dict:
    resolved_session_id = session_id or str(uuid4())

    selected_calls = _select_tools_with_model(question, device_code)
    if not selected_calls:
        selected_calls = _select_tools_by_keywords(question, device_code)

    tool_call_records = [execute_tool_call(tool_name, arguments) for tool_name, arguments in selected_calls]
    sources = _collect_sources(tool_call_records)
    answer = _generate_final_answer(question, tool_call_records)

    return {
        "message": "已基于工具调用结果生成回答。",
        "answer": answer,
        "sources": sources,
        "tool_calls": [_public_tool_call(record) for record in tool_call_records],
        "session_id": resolved_session_id,
    }


def _select_tools_with_model(question: str, device_code: Optional[str]) -> list:
    try:
        from app.core.llm import get_chat_model

        model = get_chat_model()
        messages = [
            (
                "system",
                "你是工业设备运维助手。请根据用户问题选择最有帮助的工具。"
                "只做一次工具选择，不要进行多轮规划。",
            ),
            (
                "user",
                "用户问题：{question}\n设备编码：{device_code}".format(
                    question=question,
                    device_code=device_code or "未提供",
                ),
            ),
        ]
        if hasattr(model, "bind_tools"):
            response = model.bind_tools(TOOL_SPECS).invoke(messages)
        else:
            response = model.invoke(messages)
        return _normalize_selected_calls(_extract_tool_calls(response), question, device_code)
    except Exception:
        return []


def _extract_tool_calls(response) -> list:
    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls:
        extracted = []
        for call in tool_calls:
            if isinstance(call, dict):
                name = call.get("name") or call.get("tool_name")
                args = call.get("args") or call.get("arguments") or {}
                if name:
                    extracted.append((name, args))
        return extracted

    additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
    raw_tool_calls = additional_kwargs.get("tool_calls") or []
    extracted = []
    for call in raw_tool_calls:
        function = call.get("function", {}) if isinstance(call, dict) else {}
        name = function.get("name")
        arguments = function.get("arguments", {})
        if name:
            extracted.append((name, arguments))
    return extracted


def _normalize_selected_calls(selected_calls: list, question: str, device_code: Optional[str]) -> list:
    normalized = []
    seen = set()
    for tool_name, arguments in selected_calls:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        if tool_name == "search_knowledge_base":
            arguments.setdefault("query", question)
            if device_code:
                arguments.setdefault("device_code", device_code)
        elif device_code:
            arguments.setdefault("device_code", device_code)
        key = (tool_name, json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str))
        if key not in seen:
            normalized.append((tool_name, arguments))
            seen.add(key)
    return normalized


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
    except Exception:
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
