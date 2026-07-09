import json
from typing import Any

from app.tools.db_tools import query_alarm_records, query_device_info, query_maintenance_records
from app.tools.rag_tools import search_knowledge_base


ALLOWED_TOOLS = {
    "search_knowledge_base": "search_knowledge_base",
    "query_device_info": "query_device_info",
    "query_alarm_records": "query_alarm_records",
    "query_maintenance_records": "query_maintenance_records",
}


REQUIRED_ARGUMENTS = {
    "search_knowledge_base": ["query"],
    "query_device_info": ["device_code"],
    "query_alarm_records": ["device_code"],
    "query_maintenance_records": ["device_code"],
}


def execute_tool_call(tool_name: str, arguments: Any) -> dict:
    parsed_arguments = _parse_arguments(arguments)
    if parsed_arguments is None:
        return _build_record(
            tool_name=tool_name,
            arguments={},
            result={
                "success": False,
                "summary": "工具参数格式错误：arguments 必须是 dict 或 JSON 字符串。",
            },
        )

    if tool_name not in ALLOWED_TOOLS:
        return _build_record(
            tool_name=tool_name,
            arguments=parsed_arguments,
            result={"success": False, "summary": f"未知工具：{tool_name}"},
        )

    missing = [name for name in REQUIRED_ARGUMENTS[tool_name] if not parsed_arguments.get(name)]
    if missing:
        return _build_record(
            tool_name=tool_name,
            arguments=parsed_arguments,
            result={"success": False, "summary": f"工具参数缺失：{', '.join(missing)}"},
        )

    try:
        result = _get_tool_function(tool_name)(**parsed_arguments)
    except Exception as exc:
        result = {"success": False, "summary": f"工具执行失败：{exc}"}

    if not isinstance(result, dict):
        result = {"success": False, "summary": "工具返回结果格式错误，期望 dict。", "raw_result": str(result)}

    return _build_record(tool_name=tool_name, arguments=parsed_arguments, result=result)


def _parse_arguments(arguments: Any):
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _get_tool_function(tool_name: str):
    return globals()[ALLOWED_TOOLS[tool_name]]


def _build_record(tool_name: str, arguments: dict, result: dict) -> dict:
    summary = str(result.get("summary", "工具调用完成。"))
    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "success": bool(result.get("success", False)),
        "summary": summary,
        "result_preview": _preview_result(result),
        "result": result,
    }


def _preview_result(result: dict) -> str:
    preview_payload = dict(result)
    text = json.dumps(preview_payload, ensure_ascii=False, default=str)
    return text[:500]
