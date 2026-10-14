# 工业设备运维知识库 RAG 与故障诊断 Agent 系统

> 当前状态：阶段一至阶段五均已完成。本项目用于模拟工业设备运维场景的本地演示、GitHub 展示，不宣称生产级部署。

本项目面向设备报警、过载和异常停机等运维问题，将设备说明书、维修手册、SOP、历史报警记录和维修工单组织为一条可追溯的诊断链路。系统提供 RAG 知识库问答、MySQL 业务数据查询、Function Calling 工具调用、固定工具链的故障诊断流程编排、Markdown 诊断报告生成与历史查询，以及 Streamlit 本地演示前端。

## 核心能力

- **RAG 知识库问答**：上传并解析设备文档，切块、向量化后写入 Chroma；回答同时返回 `sources` 引用。
- **无依据问题处理**：知识库没有可靠命中时返回空 `sources` 或明确提示，不伪造文档来源。
- **MySQL 业务数据**：维护设备台账、历史报警、维修记录、聊天历史和诊断报告。
- **Function Calling**：将知识库检索、设备信息、报警记录和维修记录封装为工具；工具问答走**多轮闭环**（模型选工具 → 执行 → 结果以 tool 消息回传 → 直至模型直接作答，最多 2 轮），并保留关键词兜底。
- **`tool_calls` 可观测**：返回工具名称、入参、执行状态、结果摘要和预览，便于调试、追溯和演示。
- **故障诊断流程编排**：整合知识库、设备台账、历史报警和维修记录为 `evidence`，生成结构化诊断结论。
- **Markdown 报告与历史追溯**：生成报告后持久化到 MySQL，支持按 `report_id` 或 `session_id` 查询。
- **Streamlit 演示前端**：只通过 HTTP 调用 FastAPI，集中展示问答、诊断、报告和设备数据查询。
- **本地离线兜底**：Embedding 或 Chat 服务不可用时，使用样例文档完成关键词检索和可追溯的抽取式回答，并明确标注为离线演示模式。

## 项目阶段

### 阶段一：RAG 知识库问答

- 支持 `.txt`、`.pdf`、`.docx` 文档上传、解析、切块和向量化。
- 使用智谱 Embedding API 将文档写入 Chroma 持久化向量库。
- 检索相关片段后由 DeepSeek Chat API 生成回答，并返回带 `sources` 的引用信息。
- 对知识库外问题进行无依据处理，避免编造来源。

### 阶段二：MySQL 业务数据层

- 使用 SQLAlchemy 建模并持久化 `devices`、`alarm_records`、`maintenance_records`、`chat_records` 和 `diagnosis_reports`。
- 提供设备列表、设备详情、报警记录、维修记录和聊天历史查询。
- 支持聊天历史与诊断报告的持久化和追溯。

### 阶段三：Function Calling 工具调用

- 提供 `search_knowledge_base`、`query_device_info`、`query_alarm_records`、`query_maintenance_records` 等工具。
- `POST /api/chat/ask-with-tools` 返回普通回答、来源和可观测的 `tool_calls`。
- 工具问答为标准 **Function Calling 多轮闭环**：模型选择工具 → 执行 → 工具结果以 `role=tool` 消息（带 `tool_call_id`）回传 → 模型基于结果继续调用或直接作答（最多 2 轮）；模型不可用/不支持工具绑定时降级为关键词选择。
- 工具调用记录会保存到聊天历史，便于后续查询和调试。
- 每轮统一解析 JSON 工具参数，保留模型原始调用 ID；同一请求内相同工具与参数复用结果。后续模型请求失败时保留已完成的记录和来源，仅在尚无工具结果时使用关键词兜底。
- `sources[].retrieval_mode` 返回 `chroma_embedding` 或 `local_keyword`；历史记录没有该字段时兼容为 `null`，得分须按对应检索模式理解。

### 阶段四：故障诊断与诊断报告

阶段四实现的是**基于固定工具链的故障诊断流程编排**，可称为故障诊断 Agent 应用，但不是复杂多轮自主 Agent、LangGraph 状态机或循环反思系统。

诊断时，系统会在提供 `device_code` 的情况下查询设备基础信息、检索知识库、查询历史报警和维修记录；将结果整合为 `evidence`，生成结构化诊断结论和 Markdown 报告。报告保存到 MySQL 的 `diagnosis_reports` 表中。

- `POST /api/diagnosis/analyze`
- `POST /api/diagnosis/report`
- `GET /api/diagnosis/reports/{report_id}`
- `GET /api/diagnosis/reports/session/{session_id}`

### 阶段五：Streamlit 演示前端与 GitHub 展示材料

`frontend/streamlit_app.py` 提供轻量级本地前端，可演示：

- RAG 知识库问答和来源引用。
- Function Calling 工具问答与 `tool_calls` 展开查看。
- 故障诊断、`evidence` 和诊断结论。
- Markdown 报告生成、单份报告查询和会话报告列表查询。
- 设备基础信息、历史报警和维修记录查询。

前端默认访问 FastAPI `http://127.0.0.1:8000`，不直接连接 MySQL，也不直接调用模型 API。

## 技术栈

- Python
- FastAPI
- LangChain
- Chroma
- MySQL
- SQLAlchemy / PyMySQL
- DeepSeek Chat API
- 智谱 Embedding API
- Function Calling
- Streamlit
- Markdown 报告生成

## 完整诊断流程

```text
用户故障问题
  -> FastAPI 诊断接口
  -> 固定工具链：设备信息（可选）+ 知识库检索 + 报警查询（可选）+ 维修查询（可选）
  -> 汇总为 evidence
  -> 生成结构化诊断结论
  -> 生成 Markdown 诊断报告
  -> 保存到 MySQL diagnosis_reports
  -> 按 report_id 或 session_id 历史查询
```

`evidence` 包含以下字段：

- `knowledge_sources`：知识库检索到的来源。
- `device_info`：设备基础信息；未提供或未找到设备时为空。
- `alarm_records`：历史报警记录。
- `maintenance_records`：历史维修记录。

证据不足时，诊断和报告会明确提示缺少依据，不编造设备信息、报警记录、维修记录或知识库来源。

## 项目结构

```text
app/
  main.py                         FastAPI 应用与路由注册
  api/
    documents.py                  文档上传接口
    chat.py                       普通 RAG 问答与聊天历史接口
    tool_chat.py                  Function Calling 问答接口
    devices.py                    设备、报警、维修记录接口
    diagnosis.py                  故障诊断、报告生成与历史查询接口
  diagnosis/
    fault_diagnosis.py            固定工具链诊断流程与 evidence 聚合
    report_generator.py           Markdown 报告生成
  db/
    models.py                     SQLAlchemy 模型，包括 DiagnosisReport
    crud.py                       数据库查询与报告保存 CRUD
  rag/                            文档解析、切块、向量库和 RAG 问答
  schemas/
    diagnosis.py                  诊断与报告响应模型
  tools/                          工具规范、执行器和工具问答逻辑
frontend/
  streamlit_app.py                Streamlit 本地演示页面
  README.md                       前端说明
scripts/
  init_db.py                      数据库初始化和样例业务数据
  ingest_sample_docs.py           样例知识库导入
data/
  sample_docs/                    样例设备文档
docs/
  stage4_acceptance.md            阶段四验收文档
  demo_guide.md                   项目演示指南
  final_project_summary.md        项目最终总结
  project_architecture.md         项目架构说明
  interview_notes.md              面试讲解笔记
  resume_description.md           简历项目描述
  github_publish_checklist.md     GitHub 发布检查清单
tests/
  test_stage_four_diagnosis_contract.py
  test_stage_four_report_contract.py
  test_stage_four_report_history_contract.py
  ...                             阶段一至阶段三合同测试
```

## 环境配置

进入项目目录并创建虚拟环境：

```powershell
cd G:\AI_projects\industrial_rag_agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `.env` 中填写自己的 API Key 与 MySQL 连接信息。`.env.example` 仅包含占位符：

```env
CHAT_API_KEY=your_deepseek_api_key
EMBEDDING_API_KEY=your_zhipu_api_key
OFFLINE_FALLBACK_ENABLED=true
OFFLINE_SIMILARITY_THRESHOLD=0.18
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=industrial_rag
```

不要将真实 API Key、数据库密码或本地 `.env` 提交到 GitHub。

## 本地运行

### Windows 一键启动

环境和依赖准备完成后，可以直接双击项目根目录的 `启动工业RAG网页.cmd`。脚本会启动 FastAPI、启动 Streamlit，并自动打开 `http://127.0.0.1:8501`。使用网页期间请保留两个最小化的服务窗口；关闭服务窗口后，本地网址将无法访问。

### 1. 启动 MySQL

可以使用本地 MySQL，也可以启动仓库提供的 Docker Compose 服务：

```powershell
docker compose up -d
```

确保 `.env` 中的 MySQL 连接配置与实际服务一致。

### 2. 初始化数据库

```powershell
python scripts/init_db.py
```

该脚本会创建或检查业务数据表并写入缺失的样例设备、报警和维修数据；可重复运行，不会删除已有数据或重建已有表。

### 3. 导入样例知识库

```powershell
python scripts/ingest_sample_docs.py
```

样例文档位于 `data/sample_docs/`，包括 SV300 伺服电机、CONV_A1 输送线和 CNC_X200 的演示资料。

### 4. 启动 FastAPI 后端

```powershell
uvicorn app.main:app --reload
```

- Swagger：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

### 5. 启动 Streamlit 前端

另开一个已激活虚拟环境的终端：

```powershell
cd G:\AI_projects\industrial_rag_agent
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/streamlit_app.py
```

- Streamlit：<http://127.0.0.1:8501>
- 后端必须先启动；前端默认使用 `http://127.0.0.1:8000`，可在侧边栏修改。

## 主要接口

| 接口 | 说明 |
| --- | --- |
| `POST /api/documents/upload` | 上传并入库 `.txt`、`.pdf`、`.docx` 文档 |
| `POST /api/chat/ask` | 普通 RAG 知识库问答，返回 `answer`、`sources` 和 `session_id` |
| `POST /api/chat/ask-with-tools` | Function Calling 工具问答，额外返回 `tool_calls` |
| `GET /api/chat/history/{session_id}` | 查询指定会话的聊天历史 |
| `GET /api/devices` | 查询设备列表 |
| `GET /api/devices/{device_code}` | 查询设备基础信息 |
| `GET /api/devices/{device_code}/alarms` | 查询历史报警记录 |
| `GET /api/devices/{device_code}/maintenance` | 查询历史维修记录 |
| `POST /api/diagnosis/analyze` | 执行故障诊断，返回 `diagnosis`、`evidence`、`tool_calls` 和 `session_id` |
| `POST /api/diagnosis/report` | 生成并保存 Markdown 诊断报告，返回 `report_id` |
| `GET /api/diagnosis/reports/{report_id}` | 查询单份诊断报告 |
| `GET /api/diagnosis/reports/session/{session_id}` | 查询会话下的诊断报告列表 |

## 推荐演示步骤

1. 在 Swagger 或 Streamlit 中提交普通 RAG 问答：`SV300伺服电机出现E-05报警应该怎么排查？`，展示 `answer` 和 `sources`。
2. 提交工具问答：`SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？`，展开查看 `tool_calls`。
3. 提交故障诊断：`CONV_A1输送线频繁过载，应该怎么诊断？`，展示多源 `evidence`、诊断结论和工具调用。
4. 生成报告：`SV300伺服电机出现E-05报警，请生成一份诊断报告。`，记录返回的 `report_id`。
5. 使用返回的 `report_id` 查询单份报告，再按同一 `session_id` 查询报告列表。
6. 测试无依据问题：`锅炉水位异常，请生成一份诊断报告。`，确认报告不会伪造设备、报警、维修或知识库来源。

完整演示顺序、讲解重点和 3 到 5 分钟面试话术见 [项目演示指南](docs/demo_guide.md)。

## 测试与检查

```powershell
python -m unittest discover
python -m compileall app scripts tests frontend
```

`tests/test_tool_loop_reliability.py` 覆盖真实 LangChain 消息类型下的多轮调用、原始 JSON 参数、调用 ID、重复查询缓存、工具成功后的模型超时、并行工具消息、非法参数反馈、直接回答和轮数上限。外部模型、数据库调用使用测试替身，不等同于线上联调。

接口的真实联调可通过 Swagger 和 Streamlit 完成。阶段四报告与历史查询对应合同测试：

- `tests/test_stage_four_diagnosis_contract.py`
- `tests/test_stage_four_report_contract.py`
- `tests/test_stage_four_report_history_contract.py`

## GitHub 展示亮点

- Chat 模型和 Embedding 模型解耦：DeepSeek 负责生成，智谱负责向量化。
- RAG 文档检索、来源引用和无依据问题处理。
- MySQL 业务数据建模与聊天、报告持久化。
- Function Calling 工具调用与 `tool_calls` 可观测。
- 固定工具链的故障诊断流程编排与多源 `evidence` 整合。
- Markdown 诊断报告生成、保存和按会话/报告编号追溯。
- Streamlit 前端将后端核心能力串联成可演示的本地页面。

更多展示资料：

- [项目最终总结](docs/final_project_summary.md)
- [项目架构说明](docs/project_architecture.md)
- [阶段四验收文档](docs/stage4_acceptance.md)
- [面试讲解笔记](docs/interview_notes.md)
- [简历项目描述](docs/resume_description.md)
- [GitHub 发布检查清单](docs/github_publish_checklist.md)

## 当前不足与后续方向

当前项目仍是本地演示系统，尚未实现权限系统、生产级数据库迁移、LangGraph 流程编排、云端部署、CI/CD 和大规模真实工单数据。

检索侧目前以稠密向量检索为主，仅在无可靠命中时触发本地关键词兜底；尚未实现 BM25+向量混合检索（RRF 融合）与 cross-encoder rerank，多租户/设备级元数据过滤也未接入向量库。

后续可考虑：引入 LangGraph 支持更复杂的多步编排；增加角色权限、文件上传前端、报告导出、日志与监控；扩充设备和工单数据，并部署到服务器或云平台。

## 更新记录

- **2026-10-14**：修复工具循环异常丢失既有结果及第二轮 JSON 字符串参数失败；每轮保留调用 ID 和 assistant 消息，缓存相同查询，支持模型直接回答；来源模式保留到 API schema；补充回归测试并标注历史阶段文档。
- **2026-10-13**：
  - Function Calling 升级为**多轮闭环**（tool 消息回传 + `tool_call_id` 对齐，`MAX_TOOL_ROUNDS=2`），并保留关键词兜底；
  - 知识库检索增加**本地关键词兜底补检**：稠密检索无可靠命中时自动补检样例文档并标注来源模式；
  - 离线兜底增加**显式告警日志**，消息文案区分"本地关键词检索"与"外部模型不可用"；
  - 修正检索阈值口径：统一为 0.35（`1/(1+distance)` 换算），更正此前文档/简历中的 0.52 旧口径；同步更新契约测试。

## 安全提示

请勿提交 `.env`、`.venv`、`data/chroma`、`data/uploads`、日志文件或真实密钥。仓库通过 `.gitignore` 忽略这些本地敏感或生成内容；发布前可参考 [GitHub 发布检查清单](docs/github_publish_checklist.md) 复核。
