# Streamlit前端演示页面

本目录提供一个轻量级 Streamlit 前端，用于本地演示“工业设备运维知识库 RAG 与故障诊断 Agent 系统”。

前端只通过 HTTP 请求调用已有 FastAPI 接口，不直接调用后端内部函数，不直接连接 MySQL，也不直接调用 DeepSeek 或智谱 API。

## 1. 先启动 FastAPI 后端

在项目根目录运行：

```powershell
uvicorn app.main:app --reload
```

默认后端地址：

```text
http://127.0.0.1:8000
```

可以先打开 Swagger 确认后端可用：

```text
http://127.0.0.1:8000/docs
```

## 2. 再启动 Streamlit 前端

另开一个终端，在项目根目录运行：

```powershell
streamlit run frontend/streamlit_app.py
```

启动后浏览器会打开 Streamlit 页面。页面侧边栏可以配置 FastAPI 服务地址、`session_id`、`device_code`，也可以快速选择常用设备编号。

## 3. 前端功能说明

当前前端支持：

- RAG 知识库问答：调用 `POST /api/chat/ask`，展示 `answer`、`sources`、`session_id`。
- 工具调用问答：调用 `POST /api/chat/ask-with-tools`，展示 `answer`、`sources`、`tool_calls`、`session_id`。
- 故障诊断分析：调用 `POST /api/diagnosis/analyze`，展示 `diagnosis`、`evidence`、`tool_calls`、`session_id`。
- Markdown 诊断报告生成：调用 `POST /api/diagnosis/report`，展示 `report_id`、`report_markdown`、`evidence`、`tool_calls`、`session_id`。
- 诊断报告历史查询：调用 `GET /api/diagnosis/reports/{report_id}` 和 `GET /api/diagnosis/reports/session/{session_id}`。
- 设备业务数据查询：调用设备基础信息、报警记录和维修记录接口。

`tool_calls` 使用展开面板展示，方便演示系统调用了哪些工具、传入了什么参数、执行是否成功。

## 4. 注意事项

- 后端必须先启动，否则前端会显示“FastAPI服务未启动或无法连接”。
- 前端只用于本地演示和面试展示，不包含登录、权限、部署和生产级前端工程能力。
- 如果后端地址不是默认值，可以在侧边栏修改 FastAPI 服务地址。
- 如果接口返回错误、请求超时或 JSON 解析失败，页面会显示错误提示，不会直接崩溃。
