# 工业设备运维知识库 RAG 与 Function Calling 系统

本项目是一个面向制造业设备运维场景的大模型应用后端，用于演示“工业文档 RAG 知识库 + MySQL 业务数据 + Function Calling 工具调用”的完整分阶段能力。

项目当前已经完成前三个阶段：

1. **阶段一：RAG 知识库问答**
   - 支持设备文档上传、解析、切块、Embedding、Chroma 向量库检索。
   - 支持基于知识库内容生成带引用来源的回答。
   - 知识库无可靠依据时返回兜底提示，并保持 `sources=[]`，不编造引用。

2. **阶段二：MySQL 业务数据层**
   - 新增设备、报警、维修、聊天历史四类业务数据表。
   - 支持本机 MySQL 初始化示例数据。
   - 支持设备列表、设备详情、报警记录、维修记录查询。
   - 支持普通 RAG 问答记录保存和历史查询。

3. **阶段三：Function Calling 工具调用**
   - 将知识库检索、设备信息查询、报警查询、维修查询封装为工具函数。
   - 新增 `POST /api/chat/ask-with-tools` 工具调用问答接口。
   - 返回可观测的 `tool_calls`，展示模型调用了哪些工具、传了什么参数、是否成功。
   - `tool_calls` 会保存到聊天历史，便于后续追踪和面试讲解。

阶段四 Agent 诊断流程尚未实现，后续计划是在当前工具调用能力基础上生成结构化故障诊断报告。

## 当前项目能力

### 阶段一：RAG 知识库问答

- 支持上传 `.txt`、`.pdf`、`.docx` 文档。
- 支持将设备说明书、维修手册、SOP、故障案例等文档写入 Chroma。
- 支持将 Chroma distance 转换为统一的 `similarity_score`。
- 支持根据 `SIMILARITY_THRESHOLD` 过滤低可信检索结果。
- 支持返回统一结构的引用来源：
  - `file_name`
  - `page`
  - `chunk_index`
  - `similarity_score`
  - `content_preview`

### 阶段二：MySQL 业务数据层

当前 MySQL 表：

- `devices`：设备基础信息。
- `alarm_records`：设备报警记录。
- `maintenance_records`：设备维修记录。
- `chat_records`：问答历史记录，包含 `sources_json` 和 `tool_calls_json`。

阶段二接口可以直接在 Swagger 中查看结构化业务数据，为阶段三工具调用提供数据基础。

### 阶段三：Function Calling 工具调用

当前工具函数：

- `search_knowledge_base(query, device_code=None)`
- `query_device_info(device_code)`
- `query_alarm_records(device_code, limit=5)`
- `query_maintenance_records(device_code, limit=5)`

当前工具调用接口：

```text
POST /api/chat/ask-with-tools
```

该接口会根据用户问题选择工具，执行工具后生成回答，并返回 `tool_calls`。

如果模型不支持标准 `tool_calls`，系统会使用关键词降级策略：

- 问题包含“报警”“历史报警”时，调用报警记录查询工具。
- 问题包含“维修”“工单”“历史维修”时，调用维修记录查询工具。
- 问题包含“设备信息”“基础信息”“位置”“厂家”“状态”时，调用设备信息查询工具。
- 其他故障排查类问题，调用知识库检索工具。

## 技术栈

- Python
- FastAPI
- LangChain
- Chroma
- SQLAlchemy
- MySQL / PyMySQL
- DeepSeek Chat API
- 智谱 BigModel Embedding API
- OpenAI-compatible Function Calling 格式

## 项目结构

```text
app/
  main.py
  api/
    chat.py
    devices.py
    documents.py
    tool_chat.py
  core/
    config.py
    llm.py
  db/
    base.py
    crud.py
    models.py
    session.py
  rag/
    ingest.py
    loaders.py
    qa.py
    splitter.py
    vector_store.py
  schemas/
    db.py
    rag.py
    tools.py
  tools/
    db_tools.py
    rag_tools.py
    tool_chat.py
    tool_executor.py
    tool_specs.py
data/
  sample_docs/
    SV300_servo_manual.txt
    SV300_servo_maintenance.txt
    CONV_A1_sop.txt
    CNC_X200_fault_cases.txt
docs/
  stage1_acceptance.md
  stage2_acceptance.md
  stage3_acceptance.md
scripts/
  ingest_sample_docs.py
  init_db.py
  test_zhipu_embedding.py
tests/
  test_stage_one_contract.py
  test_stage_two_db_contract.py
  test_stage_two_devices_api_contract.py
  test_stage_two_chat_history_contract.py
  test_stage_three_tools_contract.py
  test_stage_three_function_calling_contract.py
  test_stage_three_tool_calls_history_contract.py
docker-compose.yml
.env.example
.gitignore
requirements.txt
README.md
```

## 环境配置

进入项目目录：

```powershell
cd G:\AI_projects\industrial_rag_agent
```

创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

复制配置文件：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，填入自己的真实 Key：

```env
CHAT_API_KEY=你的DeepSeek_API_Key
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-v4-flash

EMBEDDING_API_KEY=你的智谱BigModel_API_Key
EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-3

CHROMA_PERSIST_DIR=data/chroma
UPLOAD_DIR=data/uploads
SAMPLE_DOCS_DIR=data/sample_docs

SIMILARITY_THRESHOLD=0.35
CHUNK_SIZE=700
CHUNK_OVERLAP=100
TOP_K=4

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_user
MYSQL_PASSWORD=rag_password
MYSQL_DATABASE=industrial_rag
```

不要把真实 API Key 提交到 GitHub。

## MySQL 启动与初始化

如果使用项目提供的 Docker Compose：

```powershell
docker compose up -d
```

如果使用本机已有 MySQL，请确保 `.env` 中的 MySQL 配置可连接。

初始化数据库表和样例数据：

```powershell
python scripts/init_db.py
```

可以重复运行该脚本。脚本按业务键判断是否已存在数据，不会重复插入设备、报警和维修脏数据。

如果已有 `chat_records` 表缺少 `tool_calls_json` 字段，初始化脚本会用兼容方式补充字段，不会删除已有数据。

## 导入样例知识库文档

样例文档位于：

```text
data/sample_docs/
```

配置好 Embedding Key 后，运行：

```powershell
python scripts/ingest_sample_docs.py
```

该脚本会把样例设备文档写入 Chroma 向量库。

## 启动服务

```powershell
uvicorn app.main:app --reload
```

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

## 主要接口

### 健康检查

```text
GET /health
```

用于确认服务是否启动，并返回 Chroma 路径、上传目录、`TOP_K` 和相似度阈值等配置。

### 文档上传

```text
POST /api/documents/upload
```

上传 `.txt`、`.pdf`、`.docx` 文档，并写入 Chroma 知识库。

### 普通 RAG 问答

```text
POST /api/chat/ask
```

请求示例：

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？",
  "session_id": "test-session-001",
  "device_code": "SV300-01"
}
```

说明：

- `session_id` 可选，不传时后端自动生成。
- `device_code` 可选，只用于关联聊天历史，不参与复杂智能判断。
- 返回 `message`、`answer`、`sources`、`session_id`。
- 知识库无可靠依据时，`sources=[]`。

### Function Calling 工具调用问答

```text
POST /api/chat/ask-with-tools
```

请求示例：

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-session-001",
  "device_code": "SV300-01"
}
```

响应会包含：

```json
{
  "message": "已基于工具调用结果生成回答。",
  "answer": "...",
  "sources": [],
  "tool_calls": [
    {
      "tool_name": "query_alarm_records",
      "arguments": {
        "device_code": "SV300-01",
        "limit": 5
      },
      "success": true,
      "summary": "已查询到设备近期报警记录。",
      "result_preview": "..."
    }
  ],
  "session_id": "tool-session-001"
}
```

### 聊天历史查询

```text
GET /api/chat/history/{session_id}
```

返回指定会话下的历史问答记录，包括：

- `question`
- `answer`
- `sources`
- `tool_calls`
- `session_id`
- `device_code`
- `created_at`

普通 RAG 问答的历史记录中，`tool_calls` 为空数组。

### 设备业务接口

```text
GET /api/devices
GET /api/devices/{device_code}
GET /api/devices/{device_code}/alarms?limit=5
GET /api/devices/{device_code}/maintenance?limit=5
```

用途：

- 查看设备列表。
- 查询单台设备详情。
- 查询设备近期报警。
- 查询设备历史维修。

## 推荐 Swagger 测试用例

### RAG 问答

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？"
}
```

### Function Calling：故障排查

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-session-001",
  "device_code": "SV300-01"
}
```

### Function Calling：报警和维修

```json
{
  "question": "CONV_A1输送线最近有哪些报警和维修记录？",
  "session_id": "tool-session-002",
  "device_code": "CONV-A1"
}
```

### Function Calling：设备基础信息

```json
{
  "question": "CNC_X200设备的基础信息是什么？",
  "session_id": "tool-session-003",
  "device_code": "CNC-X200"
}
```

### 知识库外问题

```json
{
  "question": "锅炉水位异常应该怎么处理？",
  "session_id": "tool-session-004"
}
```

期望：如果知识库没有可靠依据，不编造引用，`sources` 为空或明确提示无直接依据。

## 自动化测试

运行全部单元测试：

```powershell
python -m unittest discover
```

运行语法编译检查：

```powershell
python -m compileall app scripts tests
```

## 验收文档

项目已生成阶段验收文档：

- [阶段一验收文档](docs/stage1_acceptance.md)
- [阶段二验收文档](docs/stage2_acceptance.md)
- [阶段三验收文档](docs/stage3_acceptance.md)

这些文档适合放入 GitHub，也适合面试时按阶段讲解项目演进。

## .gitignore 说明

当前 `.gitignore` 已排除以下本地敏感或生成内容：

```gitignore
.venv/
.env
__pycache__/
*.py[cod]
data/uploads/
data/chroma/
```

因此真实 API Key、本地虚拟环境、上传文件、Chroma 向量库和 Python 缓存文件不会被提交到 GitHub。

## 当前仍未完成：阶段四 Agent

阶段四暂未实现。

后续建议目标：

- 在阶段三工具调用基础上实现故障诊断 Agent。
- 自动组合知识库检索、设备信息、报警记录、维修记录和历史问答。
- 生成结构化 Markdown 故障诊断报告。
- 报告包含问题概述、设备信息、知识库依据、历史报警、历史维修、可能原因、排查步骤、维修建议和风险提示。

阶段四仍建议保持边界清晰：不是让模型无限制自主行动，而是围绕已封装工具生成可解释、可追踪的诊断报告。
# 工业设备运维知识库 RAG 与故障诊断 Agent 系统

> 最新状态：阶段一 RAG、阶段二 MySQL 业务数据、阶段三 Function Calling、阶段四故障诊断与 Markdown 报告生成均已完成并通过本机 Swagger 验收。

本项目是一个面向工业设备运维场景的大模型应用后端系统。它模拟现场工程师遇到设备报警、过载、异常停机等问题时，如何结合设备说明书、SOP、历史报警、维修工单和大模型能力，快速获得故障排查建议和结构化诊断报告。

项目适合用于 GitHub 展示、简历项目和面试讲解。当前项目定位是“模拟工业设备运维场景的 AI 应用项目”，不宣称生产级上线或真实企业部署。

## 当前已完成阶段

| 阶段 | 名称 | 状态 | 主要能力 |
| --- | --- | --- | --- |
| 阶段一 | RAG 知识库问答 | 已完成 | 文档上传、解析、切块、Embedding、Chroma 检索、带 sources 的问答 |
| 阶段二 | MySQL 业务数据层 | 已完成 | 设备台账、报警记录、维修记录、聊天历史保存与查询 |
| 阶段三 | Function Calling 工具调用 | 已完成 | 工具函数封装、`ask-with-tools`、`tool_calls` 返回和历史保存 |
| 阶段四 | 故障诊断 Agent 与报告生成 | 已完成 | 诊断流程编排、Markdown 报告生成、报告保存和历史查询 |

## 核心功能

- RAG 知识库问答：支持设备说明书、维修手册、SOP 等文档检索增强问答。
- 文档入库：支持 `.txt`、`.pdf`、`.docx` 文档上传、解析、切块和向量化。
- 知识库外问题处理：无可靠依据时返回空 sources 或明确提示，不编造引用来源。
- MySQL 业务数据：保存设备、报警、维修、聊天历史和诊断报告。
- 设备业务查询：支持设备列表、设备详情、历史报警和历史维修记录查询。
- Function Calling：封装知识库检索、设备查询、报警查询、维修查询等工具。
- `tool_calls` 可观测：返回工具名称、入参、执行状态、摘要和结果预览。
- 故障诊断流程：整合知识库、设备台账、历史报警和维修记录，生成结构化诊断结论。
- Markdown 诊断报告：生成固定结构报告，包含依据、结论和工具调用记录。
- 报告历史追溯：诊断报告保存到 MySQL，支持按 `report_id` 和 `session_id` 查询。

## 技术栈

- Python
- FastAPI
- LangChain
- Chroma
- MySQL
- SQLAlchemy
- PyMySQL
- DeepSeek Chat API
- 智谱 BigModel Embedding API
- Function Calling
- Markdown 报告生成

## 项目目录结构

```text
app/
  api/          FastAPI 路由层
  core/         配置与模型客户端
  rag/          文档解析、切块、向量库和 RAG 问答
  db/           SQLAlchemy 模型、会话和 CRUD
  tools/        Function Calling 工具规格、执行器和工具问答
  diagnosis/    故障诊断流程和 Markdown 报告生成
  schemas/      Pydantic 请求和响应模型
scripts/        数据库初始化、样例文档导入等脚本
docs/           阶段验收、架构、简历和面试文档
tests/          阶段契约测试和回归测试
data/           样例文档、本地上传目录和 Chroma 持久化目录
```

## 环境变量说明

项目使用 `.env` 管理本地配置。不要提交真实 API Key 或真实数据库密码。

示例：

```env
CHAT_API_KEY=your_deepseek_api_key
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=your_chat_model

EMBEDDING_API_KEY=your_zhipu_embedding_api_key
EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-3

CHROMA_PERSIST_DIR=data/chroma
UPLOAD_DIR=data/uploads
SAMPLE_DOCS_DIR=data/sample_docs

SIMILARITY_THRESHOLD=0.35
CHUNK_SIZE=700
CHUNK_OVERLAP=100
TOP_K=4

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=industrial_rag
```

仓库中只应保留 `.env.example`，真实 `.env` 已被 `.gitignore` 排除。

## 本地启动步骤

```powershell
cd G:\AI_projects\industrial_rag_agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填入自己的 DeepSeek、智谱 Embedding 和 MySQL 配置。

启动服务：

```powershell
uvicorn app.main:app --reload
```

Swagger 入口：

```text
http://127.0.0.1:8000/docs
```

## 数据库初始化步骤

启动 MySQL 后运行：

```powershell
python scripts/init_db.py
```

该脚本会创建或检查以下表：

- `devices`
- `alarm_records`
- `maintenance_records`
- `chat_records`
- `diagnosis_reports`

脚本支持重复执行，不会删除已有数据，也不会重建已有表。已有 `chat_records` 表缺少 `tool_calls_json` 字段时，会以兼容方式补充字段。

导入样例知识库文档：

```powershell
python scripts/ingest_sample_docs.py
```

## 主要接口清单

### 健康检查

```text
GET /health
```

### 文档上传

```text
POST /api/documents/upload
```

### 普通 RAG 问答

```text
POST /api/chat/ask
GET /api/chat/history/{session_id}
```

### Function Calling 工具问答

```text
POST /api/chat/ask-with-tools
```

### 设备业务查询

```text
GET /api/devices
GET /api/devices/{device_code}
GET /api/devices/{device_code}/alarms
GET /api/devices/{device_code}/maintenance
```

### 故障诊断与报告

```text
POST /api/diagnosis/analyze
POST /api/diagnosis/report
GET /api/diagnosis/reports/{report_id}
GET /api/diagnosis/reports/session/{session_id}
```

## 典型测试用例

### RAG 问答

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？",
  "session_id": "test-session-001",
  "device_code": "SV300-01"
}
```

### Function Calling 问答

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-session-001",
  "device_code": "SV300-01"
}
```

### 故障诊断

```json
{
  "question": "CONV_A1输送线频繁过载，应该怎么诊断？",
  "session_id": "diagnosis-session-002",
  "device_code": "CONV-A1"
}
```

### Markdown 报告生成

```json
{
  "question": "SV300伺服电机出现E-05报警，请生成一份诊断报告。",
  "session_id": "report-history-001",
  "device_code": "SV300-01"
}
```

### 报告历史查询

```text
GET /api/diagnosis/reports/{report_id}
GET /api/diagnosis/reports/session/report-history-001
```

### 知识库外问题

```json
{
  "question": "锅炉水位异常，请生成一份诊断报告。",
  "session_id": "report-history-002"
}
```

期望：无设备编号时明确说明无法结合设备台账、报警和维修记录分析；知识库无可靠依据时不编造来源。

## 自动化测试

```powershell
python -m unittest discover
python -m compileall app scripts tests
```

## 项目文档

- [阶段一验收文档](docs/stage1_acceptance.md)
- [阶段二验收文档](docs/stage2_acceptance.md)
- [阶段三验收文档](docs/stage3_acceptance.md)
- [阶段四验收文档](docs/stage4_acceptance.md)
- [项目架构说明](docs/project_architecture.md)
- [面试讲解笔记](docs/interview_notes.md)
- [简历项目描述](docs/resume_description.md)

## 当前未完成功能

当前没有实现：

- LangGraph
- 复杂多轮 Agent
- 生产级前端工程和部署
- 权限系统
- PDF 导出
- 复杂报表导出
- 生产级数据库迁移
- 部署上线

## 后续阶段计划

阶段五建议聚焦项目展示和求职材料：

- 完善 Streamlit 演示页面、接口截图和项目展示材料。
- 整理接口演示截图。
- 继续完善 README 和 GitHub 展示材料。
- 补充部署说明。
- 将简历项目描述和面试话术进一步压缩成投递版本。

---

## 阶段五第一批：Streamlit前端演示页面

当前项目已新增轻量级 Streamlit 前端，用于本地演示阶段一到阶段四的后端能力。

前端文件位置：

```text
frontend/streamlit_app.py
frontend/README.md
```

启动方式：

```powershell
uvicorn app.main:app --reload
streamlit run frontend/streamlit_app.py
```

使用时需要先启动 FastAPI 后端，再启动 Streamlit 前端。前端默认调用：

```text
http://127.0.0.1:8000
```

前端支持：

- RAG 知识库问答。
- Function Calling 工具问答和 `tool_calls` 展示。
- 故障诊断分析和 `evidence` 展示。
- Markdown 诊断报告生成。
- 按 `report_id` 查询单份报告。
- 按 `session_id` 查询报告列表。
- 查询设备基础信息、报警记录和维修记录。

前端只通过 HTTP 请求访问已有 FastAPI 接口，不直接调用后端内部函数，不直接连接 MySQL，不直接调用 DeepSeek 或智谱 API。该页面仅用于本地演示和面试展示。

以下为项目早期 README 内容，保留作为历史阶段说明。
