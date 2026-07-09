# 项目演示指南

## 1. 演示前准备

正式演示前建议按下面顺序检查：

1. 启动 MySQL，确认数据库服务可连接。
2. 检查 `.env` 配置，确认 Chat API、Embedding API、MySQL 连接信息已经填写。
3. 初始化数据库，创建设备、报警、维修、聊天历史和诊断报告相关表。
4. 导入样例知识库，把 `data/sample_docs` 中的设备文档写入 Chroma。
5. 启动 FastAPI 后端，确认 Swagger 可以访问。
6. 启动 Streamlit 前端，使用页面侧边栏配置后端地址、`session_id` 和 `device_code`。

演示时建议提前准备好两个终端：一个运行 FastAPI，另一个运行 Streamlit。

## 2. 后端启动命令

```powershell
cd G:\AI_projects\industrial_rag_agent
.\.venv\Scripts\Activate.ps1
python scripts/init_db.py
uvicorn app.main:app --reload
```

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

如果需要重新导入样例知识库，可以运行：

```powershell
python scripts/ingest_sample_docs.py
```

## 3. 前端启动命令

另开一个终端：

```powershell
cd G:\AI_projects\industrial_rag_agent
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/streamlit_app.py
```

Streamlit 页面启动后，在侧边栏确认 FastAPI 服务地址为：

```text
http://127.0.0.1:8000
```

## 4. 推荐演示顺序

建议按下面顺序演示，逻辑会比较顺：

1. 展示 README 项目简介，说明这是一个模拟工业设备运维场景的 RAG 与故障诊断项目。
2. 展示项目目录结构，说明 `app`、`scripts`、`frontend`、`docs`、`tests` 的职责。
3. 展示 Swagger 接口，说明后端能力都通过 FastAPI 暴露。
4. 展示 Streamlit 前端，说明它只通过 HTTP 调用已有后端接口。
5. 演示普通 RAG 知识库问答，展示 `answer` 和 `sources`。
6. 演示 Function Calling 工具问答，展开 `tool_calls`。
7. 演示故障诊断分析，展示 `diagnosis`、`evidence` 和 `tool_calls`。
8. 演示 Markdown 诊断报告生成，展示 `report_id` 和 `report_markdown`。
9. 演示报告历史查询，分别按 `report_id` 和 `session_id` 查询。
10. 演示设备业务数据查询，查询设备基础信息、报警记录和维修记录。
11. 展示 `docs` 中的架构说明、面试笔记和简历项目描述。

## 5. 推荐演示问题

### 普通 RAG 知识库问答

```text
SV300伺服电机出现E-05报警应该怎么排查？
```

### Function Calling 工具问答

```text
SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？
```

### 故障诊断分析

```text
CONV_A1输送线频繁过载，应该怎么诊断？
```

### Markdown 诊断报告生成

```text
SV300伺服电机出现E-05报警，请生成一份诊断报告。
```

### 无依据问题测试

```text
锅炉水位异常，请生成一份诊断报告。
```

## 6. 每个问题的展示重点

| 演示问题 | 适合展示的能力 |
| --- | --- |
| SV300伺服电机出现E-05报警应该怎么排查？ | RAG 检索、sources 引用、知识库依据返回 |
| SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？ | Function Calling、MySQL 业务数据查询、tool_calls 可观测 |
| CONV_A1输送线频繁过载，应该怎么诊断？ | 故障诊断流程、多源 evidence、报警和维修记录整合 |
| SV300伺服电机出现E-05报警，请生成一份诊断报告。 | Markdown 报告、report_id、报告保存和历史追溯 |
| 锅炉水位异常，请生成一份诊断报告。 | 无依据问题不编造、不伪造设备信息、报警记录、维修记录和知识库来源 |

演示 `tool_calls` 时，可以重点说明系统不是只返回一段文本，而是能展示调用了哪些工具、传入了哪些参数、执行是否成功以及结果摘要。

## 7. 面试演示话术

下面是一版 3 到 5 分钟的项目讲解稿：

我这个项目是一个面向工业设备运维场景的知识库 RAG 与故障诊断 Agent 系统。因为我的专业背景是控制工程，所以我选了一个和设备、报警、维修比较贴近的场景：现场工程师遇到设备故障时，通常需要查设备说明书、SOP、历史报警和维修工单。这个过程如果全靠人工翻资料，效率比较低，也很难追溯依据。

所以我把项目拆成了几个阶段来做。第一阶段是 RAG 知识库问答，系统支持把设备说明书、维修手册和 SOP 文档切块、向量化，写入 Chroma，然后根据用户问题检索相关片段，再由 Chat 模型生成回答并返回 sources。这里我把 Chat 模型和 Embedding 模型做了解耦，DeepSeek 负责文本生成，智谱 Embedding 负责向量化。

第二阶段我引入了 MySQL 业务数据层。因为真实运维场景里不只有文档，还有设备台账、报警记录和维修工单。我用 SQLAlchemy 建了设备、报警、维修、聊天历史和诊断报告这些表，并提供了设备查询接口。

第三阶段是 Function Calling。我把知识库检索、设备查询、报警查询和维修查询封装成工具，让系统可以根据问题调用合适的数据源。接口会返回 tool_calls，可以看到调用了哪个工具、传了什么参数、执行是否成功。这一点对调试和面试展示都很有帮助。

第四阶段是在工具能力基础上做故障诊断流程编排。比如用户问 SV300 伺服电机 E-05 报警，系统会查询设备信息、检索知识库、查询历史报警和维修记录，把这些内容整理成 evidence，再生成结构化诊断结论和 Markdown 报告。报告会保存到 MySQL，可以按 report_id 或 session_id 查询。

第五阶段我加了一个轻量 Streamlit 前端，主要用于本地演示。前端不直接连接数据库，也不直接调用模型，只通过 HTTP 请求调用 FastAPI 后端接口。这样演示时可以在一个页面里展示 RAG 问答、工具调用、故障诊断、报告生成、报告历史查询和设备业务数据查询。

这个项目目前是一个模拟工业设备运维场景的完整应用项目，不是生产部署系统。我认为它的价值在于把 RAG、业务数据库、Function Calling、诊断报告和前端演示串成了一条比较完整的大模型应用链路，也体现了我从控制工程背景转向 AI 大模型应用开发时，对业务场景和工程实现的结合能力。
