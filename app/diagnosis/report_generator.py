from datetime import datetime
import json
from typing import Optional


def generate_markdown_report(question: str, device_code: Optional[str], diagnosis_result: dict) -> str:
    evidence = diagnosis_result.get("evidence", {}) or {}
    tool_calls = diagnosis_result.get("tool_calls", []) or []
    session_id = diagnosis_result.get("session_id", "")
    diagnosis = diagnosis_result.get("diagnosis", "")
    diagnosis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections = [
        "# 工业设备故障诊断报告",
        _basic_info(session_id, device_code, diagnosis_time, question),
        _fault_symptom(question),
        _device_info(evidence.get("device_info"), device_code),
        _knowledge_sources(evidence.get("knowledge_sources", []) or []),
        _alarm_records(evidence.get("alarm_records", []) or []),
        _maintenance_records(evidence.get("maintenance_records", []) or []),
        _diagnosis_conclusion(diagnosis),
        _tool_calls(tool_calls),
        _conclusion_note(evidence, device_code),
    ]
    return "\n\n".join(section.strip() for section in sections)


def _basic_info(session_id: str, device_code: Optional[str], diagnosis_time: str, question: str) -> str:
    return f"""## 一、基本信息
- 会话编号：{session_id or "未提供"}
- 设备编号：{device_code or "未提供"}
- 诊断时间：{diagnosis_time}
- 用户问题：{question}"""


def _fault_symptom(question: str) -> str:
    return f"""## 二、故障现象
根据用户问题提炼，当前故障现象为：{question}"""


def _device_info(device_info, device_code: Optional[str]) -> str:
    if not device_code:
        return """## 三、设备基础信息
未提供设备编号，无法结合设备台账、历史报警和维修记录分析。"""
    if not device_info:
        return """## 三、设备基础信息
未查询到该设备编号对应的设备信息。"""
    return """## 三、设备基础信息
- 设备编号：{device_code}
- 设备名称：{device_name}
- 设备类型：{device_type}
- 安装位置：{location}
- 生产厂家：{manufacturer}
- 当前状态：{status}""".format(
        device_code=_value(device_info.get("device_code")),
        device_name=_value(device_info.get("device_name")),
        device_type=_value(device_info.get("device_type")),
        location=_value(device_info.get("location")),
        manufacturer=_value(device_info.get("manufacturer")),
        status=_value(device_info.get("status")),
    )


def _knowledge_sources(sources: list) -> str:
    if not sources:
        return """## 四、知识库依据
知识库未检索到高于阈值的可靠依据。"""
    lines = ["## 四、知识库依据"]
    for index, source in enumerate(sources, start=1):
        lines.extend(
            [
                f"### 依据 {index}",
                f"- 文件名：{_value(source.get('file_name'))}",
                f"- chunk_index：{_value(source.get('chunk_index'))}",
                f"- similarity_score：{_value(source.get('similarity_score'))}",
                f"- content_preview：{_value(source.get('content_preview'))}",
            ]
        )
    return "\n".join(lines)


def _alarm_records(records: list) -> str:
    if not records:
        return """## 五、历史报警依据
未查询到历史报警记录。"""
    lines = ["## 五、历史报警依据"]
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"### 报警记录 {index}",
                f"- 报警码：{_value(record.get('alarm_code'))}",
                f"- 报警等级：{_value(record.get('alarm_level'))}",
                f"- 报警信息：{_value(record.get('alarm_message'))}",
                f"- 发生时间：{_value(record.get('occurred_at'))}",
                f"- 处理状态：{_value(record.get('status'))}",
            ]
        )
    return "\n".join(lines)


def _maintenance_records(records: list) -> str:
    if not records:
        return """## 六、历史维修依据
未查询到历史维修记录。"""
    lines = ["## 六、历史维修依据"]
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"### 维修记录 {index}",
                f"- 工单编号：{_value(record.get('work_order_no'))}",
                f"- 故障描述：{_value(record.get('fault_description'))}",
                f"- 根因分析：{_value(record.get('root_cause'))}",
                f"- 处理方案：{_value(record.get('solution'))}",
                f"- 维修人员：{_value(record.get('maintainer'))}",
                f"- 开始时间：{_value(record.get('started_at'))}",
                f"- 完成时间：{_value(record.get('finished_at'))}",
            ]
        )
    return "\n".join(lines)


def _diagnosis_conclusion(diagnosis: str) -> str:
    content = diagnosis.strip() if diagnosis else "当前诊断结论为空，请结合 evidence 进一步分析。"
    additions = []
    for keyword in ["可能原因", "排查步骤", "维修建议", "注意事项"]:
        if keyword not in content:
            additions.append(f"- {keyword}：请结合证据补充。")
    if additions:
        content = content + "\n\n" + "\n".join(additions)
    return f"""## 七、综合诊断结论
{content}"""


def _tool_calls(tool_calls: list) -> str:
    if not tool_calls:
        return """## 八、工具调用记录
本次诊断未记录到工具调用。"""
    lines = ["## 八、工具调用记录"]
    for index, call in enumerate(tool_calls, start=1):
        lines.extend(
            [
                f"### 工具调用 {index}",
                f"- tool_name：{_value(call.get('tool_name'))}",
                f"- arguments：{json.dumps(call.get('arguments', {}), ensure_ascii=False, default=str)}",
                f"- success：{_value(call.get('success'))}",
                f"- summary：{_value(call.get('summary'))}",
            ]
        )
    return "\n".join(lines)


def _conclusion_note(evidence: dict, device_code: Optional[str]) -> str:
    notes = ["本报告基于知识库、设备台账、历史报警和历史维修记录生成。"]
    if not device_code:
        notes.append("未提供设备编号，无法结合设备台账、历史报警和维修记录分析。")
    if device_code and not evidence.get("device_info"):
        notes.append("未查询到该设备编号对应的设备信息。")
    if not evidence.get("knowledge_sources"):
        notes.append("知识库未检索到高于阈值的可靠依据。")
    if not evidence.get("alarm_records"):
        notes.append("未查询到历史报警记录。")
    if not evidence.get("maintenance_records"):
        notes.append("未查询到历史维修记录。")
    notes.append("证据不足时，应明确提示证据不足，不能编造设备信息、报警记录、维修记录或知识库来源。")
    return "## 九、结论说明\n" + "\n".join(f"- {note}" for note in notes)


def _value(value) -> str:
    if value is None:
        return "无"
    return str(value)
