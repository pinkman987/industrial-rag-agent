# 项目架构说明

## 1. 项目整体定位

本项目是一个面向工业设备运维场景的知识库 RAG 与故障诊断 Agent 系统。它模拟制造业现场工程师在遇到设备报警、过载、异常停机等问题时，如何通过设备文档、历史报警、维修工单和大模型能力快速获得排查建议和诊断报告。

项目不是单纯的聊天 Demo，而是围绕“企业知识库问答 + 业务数据库 + 工具调用 + 故障诊断报告”构建的后端应用。它适合展示 RAG 应用开发、FastAPI 接口设计、MySQL 业务建模、Function Calling 工具调用和可追溯报告生成等能力。

## 2. 技术栈

| 技术 | 作用 |
| --- | --- |
| Python | 后端主要开发语言 |
| FastAPI | 提供 HTTP API、Swagger 文档和接口测试入口 |
| LangChain | 组织文档加载、切分、向量检索等 RAG 组件 |
| Chroma | 持久化保存文档向量，执行相似度检索 |
| DeepSeek Chat API | 负责问答、诊断结论和报告相关文本生成 |
| 智谱 Embedding API | 负责把文档片段和用户问题转换成向量 |
| SQLAlchemy | 定义 ORM 模型，封装 MySQL 数据访问 |
| MySQL | 保存设备、报警、维修、聊天历史和诊断报告 |
| Function Calling | 把知识库检索和业务查询封装成可调用工具 |
| Markdown 报告生成 | 输出结构化、可展示、可保存的诊断报告 |

其中 Chat 模型和 Embedding 模型是解耦的：DeepSeek 负责文本生成，智谱 Embedding 负责向量化。这种拆分更贴近真实工程实践，也避免把不适合作为 Embedding 的 Chat 模型强行用于向量化。

## 3. 模块结构说明

```text
app/
  api/
  core/
  rag/
  db/
  tools/
  diagnosis/
  schemas/
scripts/
docs/
tests/
data/
```

### app/api

FastAPI 路由层，负责对外暴露接口。主要包括：

- `chat.py`：普通 RAG 问答和聊天历史查询。
- `documents.py`：文档上传和写入知识库。
- `devices.py`：设备、报警、维修等业务数据查询。
- `tool_chat.py`：Function Calling 工具调用问答。
- `diagnosis.py`：故障诊断、报告生成、报告历史查询。

### app/core

核心配置和模型客户端封装：

- `config.py`：读取 `.env` 环境变量。
- `llm.py`：封装 Chat 模型调用。

### app/rag

RAG 知识库模块：

- `loaders.py`：解析 `.txt`、`.pdf`、`.docx` 文档。
- `splitter.py`：文档切块。
- `vector_store.py`：Chroma 向量库写入和检索。
- `qa.py`：普通 RAG 问答流程。
- `ingest.py`：文档入库编排。

### app/db

MySQL 数据层：

- `models.py`：SQLAlchemy ORM 模型，包括设备、报警、维修、聊天记录和诊断报告。
- `crud.py`：数据库查询和保存函数。
- `session.py`：数据库连接和会话管理。
- `base.py`：ORM Base 定义。

### app/tools

Function Calling 工具层：

- `rag_tools.py`：封装知识库检索工具。
- `db_tools.py`：封装设备、报警、维修查询工具。
- `tool_specs.py`：定义 OpenAI 兼容的工具规格。
- `tool_executor.py`：执行白名单工具并生成 `tool_calls`。
- `tool_chat.py`：工具调用问答流程。

### app/diagnosis

故障诊断和报告生成模块：

- `fault_diagnosis.py`：按固定流程编排诊断工具调用，生成结构化诊断结论。
- `report_generator.py`：把诊断结果、证据和工具调用记录整理成 Markdown 报告。

### app/schemas

Pydantic 请求和响应模型：

- `rag.py`：RAG 问答、聊天历史相关 schema。
- `db.py`：设备、报警、维修接口 schema。
- `tools.py`：工具调用问答 schema。
- `diagnosis.py`：诊断、报告和报告历史 schema。

### scripts

项目脚本：

- `init_db.py`：创建 MySQL 表并写入示例设备、报警、维修数据。
- `ingest_sample_docs.py`：导入样例文档到 Chroma。
- 其他脚本用于测试 Embedding 或生成早期计划文档。

### docs

项目文档，包括各阶段验收文档、架构说明、简历描述和面试笔记。

### tests

自动化测试，主要用于保证各阶段接口契约、schema、工具函数和报告历史能力不被破坏。

### data

本地数据目录：

- `sample_docs/`：样例设备文档。
- `uploads/`：上传文档目录，应被 `.gitignore` 排除。
- `chroma/`：Chroma 向量库持久化目录，应被 `.gitignore` 排除。

## 4. 四个阶段能力关系

### 阶段一：RAG 知识库问答

阶段一完成文档上传、解析、切块、Embedding、Chroma 检索和基于知识库依据的回答生成。它解决的是“非结构化设备文档怎么被大模型可靠使用”的问题。

### 阶段二：MySQL 业务数据

阶段二引入设备台账、报警记录、维修记录和聊天历史。它解决的是“企业运维场景不只有文档，还有结构化业务数据”的问题。

### 阶段三：Function Calling 工具调用

阶段三把知识库检索和业务数据查询封装成工具，让模型或系统可以根据问题调用合适工具，并通过 `tool_calls` 记录调用过程。它解决的是“如何把 RAG 和业务数据库变成可调度能力”的问题。

### 阶段四：诊断 Agent 与报告生成

阶段四在工具能力基础上编排固定诊断流程，生成结构化诊断结论和 Markdown 报告，并把报告保存到 MySQL，支持历史查询。它解决的是“如何把问答升级为可追溯的工业故障诊断报告”的问题。

## 5. 核心数据流

完整数据流可以概括为：

1. 用户通过 FastAPI 接口提交问题。
2. 普通 RAG 问题进入知识库检索流程。
3. 工具调用问题进入 Function Calling 流程。
4. 故障诊断问题进入诊断流程编排。
5. 系统根据问题调用知识库检索和数据库查询工具。
6. 知识库检索从 Chroma 返回文档片段和相似度。
7. 数据库查询从 MySQL 返回设备信息、报警记录和维修记录。
8. 工具结果被整理成 `sources`、`evidence` 和 `tool_calls`。
9. 大模型基于证据生成 `answer`、`diagnosis` 或 `report_markdown`。
10. 普通问答保存到 `chat_records`。
11. 诊断报告保存到 `diagnosis_reports`。
12. 用户可通过历史接口回看聊天记录或诊断报告。

主要返回形式包括：

- `answer`：普通 RAG 或工具调用问答结果。
- `diagnosis`：结构化故障诊断结论。
- `report_markdown`：Markdown 格式诊断报告。
- `sources`：RAG 引用来源。
- `evidence`：诊断证据集合。
- `tool_calls`：工具调用过程记录。

## 6. 当前项目适合展示的亮点

- RAG 知识库问答：支持工业设备文档检索和基于来源的回答生成。
- Chat 模型和 Embedding 模型解耦：DeepSeek 负责生成，智谱 Embedding 负责向量化。
- 向量数据库持久化：使用 Chroma 保存文档向量，支持重复查询。
- MySQL 业务数据建模：设计设备、报警、维修、聊天记录和诊断报告表。
- Function Calling 工具调用：把知识库和业务数据查询封装成可调用工具。
- `tool_calls` 可观测：接口返回工具名称、入参、执行状态和摘要。
- 诊断报告生成：把多源证据整理成结构化 Markdown 报告。
- 报告历史追溯：报告保存到 MySQL，支持按 `report_id` 和 `session_id` 查询。
- 知识库外问题不编造来源：无可靠依据时明确提示，避免伪造引用和业务记录。

## 7. 当前架构边界

当前项目仍然是面向学习、展示和面试讲解的后端项目，没有宣称生产级上线。当前暂未实现：

- 权限认证和用户体系。
- 生产级数据库迁移。
- 前端演示页面。
- PDF 或复杂报表导出。
- 复杂多轮 Agent 规划。
- 云端部署和真实企业接入。

这些边界使项目更适合作为应届生求职项目：它展示了完整 AI 应用后端链路，但没有虚构真实生产规模或上线效果。
