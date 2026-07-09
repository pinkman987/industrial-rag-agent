from typing import Any, Optional

import requests
import streamlit as st


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 30


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def request_json(
    method: str,
    base_url: str,
    path: str,
    *,
    json_body: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Optional[dict[str, Any]]:
    url = build_url(base_url, path)
    try:
        response = requests.request(method, url, json=json_body, timeout=timeout)
    except requests.exceptions.ConnectionError:
        st.error(f"FastAPI服务未启动或无法连接：{url}")
        return None
    except requests.exceptions.Timeout:
        st.error(f"请求超时：{url}")
        return None
    except requests.exceptions.RequestException as exc:
        st.error(f"请求失败：{exc}")
        return None

    try:
        data = response.json()
    except ValueError:
        st.error(f"JSON解析失败。状态码：{response.status_code}，响应内容：{response.text[:500]}")
        return None

    if response.status_code >= 400:
        detail = data.get("detail") if isinstance(data, dict) else data
        st.error(f"接口返回错误。状态码：{response.status_code}，详情：{detail}")
        return None

    if not isinstance(data, dict):
        st.error("JSON解析失败：接口返回的不是对象结构。")
        return None

    return data


def request_get(base_url: str, path: str) -> Optional[dict[str, Any]]:
    return request_json("GET", base_url, path)


def request_post(base_url: str, path: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    return request_json("POST", base_url, path, json_body=payload)


def build_payload(question: str, session_id: str, device_code: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"question": question}
    if session_id.strip():
        payload["session_id"] = session_id.strip()
    if device_code.strip():
        payload["device_code"] = device_code.strip()
    return payload


def show_sources(sources: Any) -> None:
    if not sources:
        st.info("未返回sources或sources为空。")
        return
    for index, source in enumerate(sources, start=1):
        title = source.get("file_name", f"source-{index}") if isinstance(source, dict) else f"source-{index}"
        with st.expander(f"来源 {index}: {title}", expanded=index == 1):
            st.json(source)


def show_tool_calls(tool_calls: Any) -> None:
    if not tool_calls:
        st.info("未返回tool_calls或tool_calls为空。")
        return
    for index, tool_call in enumerate(tool_calls, start=1):
        tool_name = tool_call.get("tool_name", f"tool-{index}") if isinstance(tool_call, dict) else f"tool-{index}"
        success = tool_call.get("success") if isinstance(tool_call, dict) else None
        status = "成功" if success is True else "失败" if success is False else "未知"
        with st.expander(f"工具调用 {index}: {tool_name}（{status}）", expanded=index == 1):
            st.json(tool_call)


def show_evidence(evidence: Any) -> None:
    if not isinstance(evidence, dict):
        st.info("未返回evidence或evidence格式不是对象。")
        return

    st.subheader("knowledge_sources")
    show_sources(evidence.get("knowledge_sources", []))

    st.subheader("device_info")
    device_info = evidence.get("device_info")
    if device_info:
        st.json(device_info)
    else:
        st.info("未返回设备基础信息。")

    st.subheader("alarm_records")
    alarm_records = evidence.get("alarm_records", [])
    if alarm_records:
        st.dataframe(alarm_records, use_container_width=True)
    else:
        st.info("未返回历史报警记录。")

    st.subheader("maintenance_records")
    maintenance_records = evidence.get("maintenance_records", [])
    if maintenance_records:
        st.dataframe(maintenance_records, use_container_width=True)
    else:
        st.info("未返回历史维修记录。")


def show_report_summary(report: dict[str, Any], expanded: bool = False) -> None:
    report_id = report.get("report_id", "未返回report_id")
    question = report.get("question", "未返回question")
    created_at = report.get("created_at", "未返回created_at")
    with st.expander(f"{report_id} | {created_at}", expanded=expanded):
        st.write(f"**问题：** {question}")
        st.markdown(report.get("report_markdown", ""))


def show_json_or_table(data: Any) -> None:
    if isinstance(data, dict):
        item = data.get("item")
        items = data.get("items")
        if isinstance(items, list):
            st.dataframe(items, use_container_width=True)
        elif isinstance(item, dict):
            st.json(item)
        else:
            st.json(data)
    elif isinstance(data, list):
        st.dataframe(data, use_container_width=True)
    else:
        st.write(data)


st.set_page_config(
    page_title="工业设备运维RAG与诊断Agent",
    layout="wide",
)

st.title("工业设备运维知识库RAG与故障诊断Agent系统")
st.caption(
    "本系统面向工业设备运维场景，集成RAG知识库问答、MySQL业务数据、"
    "FunctionCalling工具调用、故障诊断、Markdown报告生成和报告历史查询能力。"
)

with st.sidebar:
    st.header("配置")
    api_base_url = st.text_input("FastAPI服务地址", value=DEFAULT_API_BASE_URL)
    session_id = st.text_input("session_id", value="demo-session-001")
    manual_device_code = st.text_input("device_code", value="SV300-01")
    quick_device_code = st.selectbox(
        "常用设备快捷选择",
        ["手动输入", "SV300-01", "CONV-A1", "CNC-X200", "空设备编号"],
    )
    if quick_device_code == "手动输入":
        device_code = manual_device_code
    elif quick_device_code == "空设备编号":
        device_code = ""
    else:
        device_code = quick_device_code

    st.divider()
    st.write("当前请求参数")
    st.code(
        f"base_url = {api_base_url}\n"
        f"session_id = {session_id or '(自动生成)'}\n"
        f"device_code = {device_code or '(空)'}"
    )

tab_rag, tab_tools, tab_diagnosis, tab_report, tab_history, tab_devices = st.tabs(
    [
        "RAG知识库问答",
        "工具调用问答",
        "故障诊断分析",
        "生成诊断报告",
        "诊断报告历史查询",
        "设备业务数据查询",
    ]
)

with tab_rag:
    st.header("RAG知识库问答")
    rag_question = st.text_area(
        "question",
        value="SV300伺服电机出现E-05报警应该怎么排查？",
        key="rag_question",
        height=100,
    )
    if st.button("提交普通问答", type="primary"):
        data = request_post(api_base_url, "/api/chat/ask", build_payload(rag_question, session_id, device_code))
        if data:
            st.subheader("answer")
            st.write(data.get("answer", ""))
            st.subheader("sources")
            show_sources(data.get("sources", []))
            st.subheader("session_id")
            st.code(data.get("session_id", ""))

with tab_tools:
    st.header("工具调用问答")
    tool_question = st.text_area(
        "question",
        value="SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
        key="tool_question",
        height=100,
    )
    if st.button("提交工具问答", type="primary"):
        data = request_post(api_base_url, "/api/chat/ask-with-tools", build_payload(tool_question, session_id, device_code))
        if data:
            st.subheader("answer")
            st.write(data.get("answer", ""))
            st.subheader("sources")
            show_sources(data.get("sources", []))
            st.subheader("tool_calls")
            show_tool_calls(data.get("tool_calls", []))
            st.subheader("session_id")
            st.code(data.get("session_id", ""))

with tab_diagnosis:
    st.header("故障诊断分析")
    diagnosis_question = st.text_area(
        "question",
        value="CONV_A1输送线频繁过载，应该怎么诊断？",
        key="diagnosis_question",
        height=100,
    )
    if st.button("开始诊断", type="primary"):
        data = request_post(
            api_base_url,
            "/api/diagnosis/analyze",
            build_payload(diagnosis_question, session_id, device_code),
        )
        if data:
            st.subheader("diagnosis")
            st.markdown(data.get("diagnosis", ""))
            st.subheader("evidence")
            show_evidence(data.get("evidence", {}))
            st.subheader("tool_calls")
            show_tool_calls(data.get("tool_calls", []))
            st.subheader("session_id")
            st.code(data.get("session_id", ""))

with tab_report:
    st.header("生成诊断报告")
    report_question = st.text_area(
        "question",
        value="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
        key="report_question",
        height=100,
    )
    if st.button("生成Markdown报告", type="primary"):
        data = request_post(
            api_base_url,
            "/api/diagnosis/report",
            build_payload(report_question, session_id, device_code),
        )
        if data:
            st.subheader("report_id")
            st.code(data.get("report_id", ""))
            st.subheader("report_markdown")
            st.markdown(data.get("report_markdown", ""))
            st.subheader("evidence")
            show_evidence(data.get("evidence", {}))
            st.subheader("tool_calls")
            show_tool_calls(data.get("tool_calls", []))
            st.subheader("session_id")
            st.code(data.get("session_id", ""))

with tab_history:
    st.header("诊断报告历史查询")
    col_report, col_session = st.columns(2)

    with col_report:
        st.subheader("查询单份报告")
        report_id = st.text_input("report_id", key="history_report_id")
        if st.button("查询单份报告"):
            if not report_id.strip():
                st.warning("请输入report_id。")
            else:
                data = request_get(api_base_url, f"/api/diagnosis/reports/{report_id.strip()}")
                if data:
                    st.write(f"**report_id：** {data.get('report_id', '')}")
                    st.write(f"**question：** {data.get('question', '')}")
                    st.write(f"**created_at：** {data.get('created_at', '')}")
                    st.markdown(data.get("report_markdown", ""))

    with col_session:
        st.subheader("查询会话报告列表")
        history_session_id = st.text_input("session_id", value=session_id, key="history_session_id")
        if st.button("查询会话报告列表"):
            if not history_session_id.strip():
                st.warning("请输入session_id。")
            else:
                data = request_get(api_base_url, f"/api/diagnosis/reports/session/{history_session_id.strip()}")
                if data:
                    items = data.get("items", [])
                    st.write(f"共查询到 {len(items)} 份报告。")
                    for index, item in enumerate(items, start=1):
                        show_report_summary(item, expanded=index == 1)

with tab_devices:
    st.header("设备业务数据查询")
    query_device_code = st.text_input("查询device_code", value=device_code or "SV300-01")
    col_device, col_alarm, col_maintenance = st.columns(3)

    with col_device:
        if st.button("查询设备基础信息"):
            if not query_device_code.strip():
                st.warning("请输入device_code。")
            else:
                data = request_get(api_base_url, f"/api/devices/{query_device_code.strip()}")
                if data:
                    show_json_or_table(data)

    with col_alarm:
        if st.button("查询报警记录"):
            if not query_device_code.strip():
                st.warning("请输入device_code。")
            else:
                data = request_get(api_base_url, f"/api/devices/{query_device_code.strip()}/alarms")
                if data:
                    show_json_or_table(data)

    with col_maintenance:
        if st.button("查询维修记录"):
            if not query_device_code.strip():
                st.warning("请输入device_code。")
            else:
                data = request_get(api_base_url, f"/api/devices/{query_device_code.strip()}/maintenance")
                if data:
                    show_json_or_table(data)
