# 项目最终总结

## 1. 项目定位

本项目是“工业设备运维知识库 RAG 与故障诊断 Agent 系统”，面向工业设备运维场景，模拟现场工程师通过知识库、业务数据和大模型能力进行设备故障排查、诊断报告生成和历史追溯的工作流程。

项目定位是一个适合 GitHub 展示、简历描述和面试讲解的大模型应用开发项目。它不是生产级上线系统，而是一个覆盖 RAG、MySQL、Function Calling、故障诊断、报告生成和 Streamlit 演示的完整本地应用。

## 2. 业务背景

在工业设备运维场景中，设备说明书、维修手册、SOP、历史报警和维修工单往往分散在不同系统或文件中。现场工程师遇到设备故障时，需要快速查找相关依据并结合历史记录做判断。

传统方式依赖人工检索文档和经验判断，排查效率较低，也不容易保存诊断过程。本项目通过 RAG 知识库、MySQL 业务数据、Function Calling 工具调用和 Markdown 报告生成，把这些分散信息组织成一条可追溯的诊断链路。

## 3. 技术栈

- Python
- FastAPI
- LangChain
- Chroma
- DeepSeek Chat API
- 智谱 Embedding API
- MySQL
- SQLAlchemy
- FunctionCalling
- Streamlit
- Markdown 报告生成

## 4. 阶段一到阶段五完成内容

### 阶段一：RAG知识库问答

完成文档上传、解析、切块、Embedding、Chroma 向量存储和 RAG 问答。系统可以基于设备说明书、维修手册和 SOP 文档回答问题，并返回 `sources` 引用来源。知识库外问题会返回空 sources 或明确提示无可靠依据。

### 阶段二：MySQL业务数据层

引入 MySQL 和 SQLAlchemy，建立设备台账、报警记录、维修记录和聊天历史等业务数据表。新增设备列表、设备详情、报警记录、维修记录和聊天历史查询接口，为后续工具调用和诊断报告打基础。

### 阶段三：FunctionCalling工具调用

将知识库检索、设备信息查询、报警记录查询、维修记录查询封装成工具函数。新增 `POST /api/chat/ask-with-tools`，返回 `tool_calls`，记录工具名称、入参、执行状态和结果摘要。工具调用记录会保存到聊天历史中。

### 阶段四：故障诊断和诊断报告

在工具能力基础上实现故障诊断流程编排。系统会查询设备信息、检索知识库、查询历史报警和维修记录，整合为 `evidence`，生成结构化诊断结论和 Markdown 报告。报告保存到 MySQL，支持按 `report_id` 和 `session_id` 查询。

### 阶段五：Streamlit前端和GitHub展示整理

新增轻量级 Streamlit 前端，用于本地演示 RAG 问答、工具调用、故障诊断、报告生成、报告历史查询和设备业务数据查询。同时整理 README、演示指南、GitHub 发布检查清单、项目最终总结、面试笔记和简历项目描述。

## 5. 核心接口清单

| 接口 | 说明 |
| --- | --- |
| `POST /api/chat/ask` | 普通 RAG 知识库问答 |
| `POST /api/chat/ask-with-tools` | Function Calling 工具问答 |
| `GET /api/chat/history/{session_id}` | 按会话查询聊天历史 |
| `GET /api/devices` | 查询设备列表 |
| `GET /api/devices/{device_code}` | 查询设备详情 |
| `GET /api/devices/{device_code}/alarms` | 查询设备报警记录 |
| `GET /api/devices/{device_code}/maintenance` | 查询设备维修记录 |
| `POST /api/diagnosis/analyze` | 故障诊断分析 |
| `POST /api/diagnosis/report` | 生成并保存 Markdown 诊断报告 |
| `GET /api/diagnosis/reports/{report_id}` | 查询单份诊断报告 |
| `GET /api/diagnosis/reports/session/{session_id}` | 查询会话下的诊断报告列表 |

## 6. 核心数据库表

| 表名 | 说明 |
| --- | --- |
| `devices` | 设备台账，保存设备编号、名称、类型、位置、厂家和状态 |
| `alarm_records` | 历史报警记录，保存报警码、报警等级、报警信息、发生时间和处理状态 |
| `maintenance_records` | 维修记录，保存工单编号、故障描述、根因分析、处理方案和维修人员 |
| `chat_records` | 聊天历史，保存问题、回答、sources、tool_calls、session_id 和关联设备 |
| `diagnosis_reports` | 诊断报告历史，保存 report_id、Markdown 报告、evidence 和 tool_calls |

## 7. 项目亮点

- Chat 模型和 Embedding 模型解耦：DeepSeek 负责文本生成，智谱 Embedding 负责向量化。
- RAG 知识库问答：支持设备文档检索增强问答，并返回 sources。
- Chroma 向量数据库持久化：样例文档入库后可重复检索。
- MySQL 业务数据建模：设备、报警、维修、聊天历史和诊断报告都有结构化存储。
- FunctionCalling 工具调用：把知识库检索和数据库查询封装成可调用工具。
- `tool_calls` 可观测：展示工具名称、入参、执行状态和摘要。
- 故障诊断流程编排：整合知识库、设备台账、报警记录和维修记录。
- Markdown 诊断报告生成：输出结构化报告，便于前端展示和面试讲解。
- 报告历史追溯：支持按 `report_id` 和 `session_id` 查询诊断报告。
- Streamlit 前端演示：用可视化页面串联后端核心能力。
- 知识库外问题不编造来源：无可靠依据时明确提示，不伪造引用、设备信息或业务记录。

## 8. 当前不足

- 仍是本地演示项目，没有生产环境部署。
- 没有权限系统和用户角色管理。
- 没有生产级数据库迁移，例如 Alembic。
- 没有复杂多轮 Agent。
- 没有 LangGraph 流程编排。
- 没有云端部署和 CI/CD。
- 样例数据规模较小，主要用于演示功能链路。

## 9. 后续优化方向

- 引入 LangGraph 做多步 Agent 编排，适合更复杂的诊断流程。
- 增加用户权限和角色管理，区分管理员、工程师和访客。
- 增加文件上传前端，让 Streamlit 页面支持上传设备文档。
- 增加报告导出能力，例如 Markdown 下载或 PDF 导出。
- 增加更丰富的设备、报警和维修工单数据。
- 增加日志和监控，记录接口耗时、工具调用耗时和异常信息。
- 部署到服务器或云平台，形成可访问的在线演示环境。
- 增加自动化评测集，验证 RAG 命中率、回答质量和无依据问题处理效果。

## 10. 适合写进简历的总结

基于 FastAPI、LangChain、Chroma、MySQL 和 Streamlit 构建工业设备运维知识库 RAG 与故障诊断 Agent 系统，支持设备文档检索问答、MySQL 业务数据查询、Function Calling 工具调用、`tool_calls` 可观测、故障诊断流程编排和 Markdown 诊断报告生成。项目实现聊天历史和诊断报告持久化，支持按会话和报告编号追溯，并针对知识库外问题设计无依据处理逻辑，避免编造来源。该项目模拟工业设备运维场景，适合展示大模型应用后端开发能力。
