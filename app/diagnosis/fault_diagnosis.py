import json
from typing import Optional
from uuid import uuid4

from app.tools.tool_executor import execute_tool_call


REQUIRED_SECTIONS = [
    "故障现象",
    "知识库依据",
    "历史报警依据",
    "历史维修依据",
    "可能原因",
    "排查步骤",
    "维修建议",
    "注意事项",
]


def analyze_fault(question: str, session_id: Optional[str] = None, device_code: Optional[str] = None) -> dict:
    resolved_session_id = session_id or str(uuid4())
    internal_tool_calls = _run_diagnosis_tools(question, device_code)
    evidence = _build_evidence(internal_tool_calls)
    diagnosis = _generate_diagnosis(question, device_code, evidence, internal_tool_calls)

    return {
        "message": "已完成故障诊断流程编排。",
        "diagnosis": diagnosis,
        "evidence": evidence,
        "tool_calls": [_public_tool_call(record) for record in internal_tool_calls],
        "session_id": resolved_session_id,
    }


def _run_diagnosis_tools(question: str, device_code: Optional[str]) -> list:
    tool_calls = []
    if device_code:
        tool_calls.append(execute_tool_call("query_device_info", {"device_code": device_code}))

    tool_calls.append(
        execute_tool_call(
            "search_knowledge_base",
            {
                "query": question,
                "device_code": device_code,
            },
        )
    )

    if device_code:
        tool_calls.append(execute_tool_call("query_alarm_records", {"device_code": device_code, "limit": 5}))
        tool_calls.append(execute_tool_call("query_maintenance_records", {"device_code": device_code, "limit": 5}))
    return tool_calls


def _build_evidence(tool_calls: list) -> dict:
    evidence = {
        "knowledge_sources": [],
        "device_info": None,
        "alarm_records": [],
        "maintenance_records": [],
    }
    for record in tool_calls:
        result = record.get("result", {}) or {}
        if not record.get("success"):
            continue
        tool_name = record.get("tool_name")
        if tool_name == "search_knowledge_base":
            evidence["knowledge_sources"] = result.get("sources", []) or []
        elif tool_name == "query_device_info":
            evidence["device_info"] = result.get("data")
        elif tool_name == "query_alarm_records":
            evidence["alarm_records"] = result.get("data", []) or []
        elif tool_name == "query_maintenance_records":
            evidence["maintenance_records"] = result.get("data", []) or []
    return evidence


def _generate_diagnosis(question: str, device_code: Optional[str], evidence: dict, tool_calls: list) -> str:
    try:
        from app.core.llm import get_chat_model

        prompt = _build_diagnosis_prompt(question, device_code, evidence, tool_calls)
        response = get_chat_model().invoke(prompt)
        diagnosis = getattr(response, "content", str(response))
    except Exception:
        diagnosis = _fallback_diagnosis(question, device_code, evidence, tool_calls)
    return _ensure_required_sections(diagnosis, question, device_code, evidence)


def _build_diagnosis_prompt(question: str, device_code: Optional[str], evidence: dict, tool_calls: list) -> str:
    return f"""
你是制造业设备运维故障诊断助手。请严格基于给定 evidence 和 tool_calls 生成结构化诊断结论。

要求：
1. 必须包含以下小节：故障现象、知识库依据、历史报警依据、历史维修依据、可能原因、排查步骤、维修建议、注意事项。
2. 不要编造不存在的设备、报警、维修记录。
3. 如果 knowledge_sources 为空，请明确说明知识库没有检索到可靠依据。
4. 如果 device_code 为空，请明确说明缺少设备编号，无法结合历史业务数据分析。
5. 输出 Markdown 文本。

用户问题：
{question}

设备编码：
{device_code or "未提供"}

evidence：
{json.dumps(evidence, ensure_ascii=False, default=str)}

tool_calls：
{json.dumps([_public_tool_call(record) for record in tool_calls], ensure_ascii=False, default=str)}
"""


def _fallback_diagnosis(question: str, device_code: Optional[str], evidence: dict, tool_calls: list) -> str:
    no_device_note = "" if device_code else "缺少设备编号，无法结合设备基础信息、历史报警和历史维修记录进行业务数据分析。"
    knowledge_note = (
        "已检索到知识库依据，建议优先参考 evidence.knowledge_sources。"
        if evidence.get("knowledge_sources")
        else "知识库未检索到高于阈值的可靠依据，不能编造文档来源。"
    )
    alarm_note = (
        "已查询到历史报警记录，建议结合报警码、发生时间和处理状态分析。"
        if evidence.get("alarm_records")
        else "未查询到可用历史报警记录。"
    )
    maintenance_note = (
        "已查询到历史维修记录，建议结合历史根因和处理方案复核。"
        if evidence.get("maintenance_records")
        else "未查询到可用历史维修记录。"
    )

    return f"""## 故障现象
用户描述：{question}
{no_device_note}

## 知识库依据
{knowledge_note}

## 历史报警依据
{alarm_note}

## 历史维修依据
{maintenance_note}

## 可能原因
- 可能存在设备负载、传感器、执行机构、控制参数或现场环境异常。
- 若缺少知识库或历史数据依据，应先完成现场信息采集，再做进一步判断。

## 排查步骤
1. 确认设备处于安全维护状态，记录报警码、发生时间和现场现象。
2. 检查电源、急停、安全联锁、传感器和执行机构状态。
3. 结合知识库依据和历史记录逐项复核可能原因。
4. 完成处理后进行低速或空载复测，再恢复正常生产。

## 维修建议
- 优先处理与报警码和历史维修根因一致的高概率问题。
- 如果现场现象与历史记录不一致，应升级给设备负责人或厂家技术支持。

## 注意事项
- 不要编造未检索到的知识库来源。
- 不要编造不存在的报警或维修记录。
- 维修前必须确认设备断电、泄压或处于安全维护模式。
"""


def _ensure_required_sections(diagnosis: str, question: str, device_code: Optional[str], evidence: dict) -> str:
    text = diagnosis or _fallback_diagnosis(question, device_code, evidence, [])
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
    if not missing_sections:
        return text
    additions = []
    for section in missing_sections:
        additions.append(f"## {section}\n当前诊断文本未覆盖该小节，请结合 evidence 进一步补充。")
    return text.rstrip() + "\n\n" + "\n\n".join(additions)


def _public_tool_call(record: dict) -> dict:
    return {
        "tool_name": record.get("tool_name", ""),
        "arguments": record.get("arguments", {}),
        "success": bool(record.get("success", False)),
        "summary": record.get("summary", ""),
        "result_preview": record.get("result_preview", ""),
    }
