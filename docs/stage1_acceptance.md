# 阶段一验收文档：RAG 最小闭环

> 历史阶段记录：本文件保留阶段一验收时的配置和行为（包括 0.50 阈值），不代表当前默认值。2026-10-14 当前版本的向量检索默认阈值为 0.35（`1/(1+distance)`），本地关键词阈值为 0.18。最新运行方式与能力以 [README](../README.md) 和实际配置为准。

## 项目阶段目标

阶段一目标是先跑通一个可独立演示、可独立验收的 RAG 最小闭环，为后续 MySQL 业务数据、Function Calling、故障诊断 Agent 和前端展示打基础。

本阶段只关注“文档进入知识库”和“用户问题基于知识库回答”两件事，不引入 MySQL、FunctionCalling、Agent、Streamlit、Docker、权限系统等额外复杂度。

## 已完成功能

- 支持上传和解析设备文档，当前覆盖 `txt`、`pdf`、`docx`。
- 支持将文档内容切分为 chunk，并保留引用元数据。
- 支持使用智谱 BigModel `embedding-3` 生成向量。
- 支持将向量和元数据持久化到 Chroma。
- 支持用户输入设备故障或运维问题后执行知识库检索。
- 支持使用 DeepSeek Chat 模型基于检索结果生成回答。
- 回答返回统一结构的引用来源 `sources`。
- 支持知识库外问题的兜底回答：不编造引用，返回 `sources=[]`。
- 已将 Chat 模型和 Embedding 模型拆成两套配置，便于接入不同平台。

## 测试接口

本阶段主要通过 FastAPI Swagger 完成验收：

- `GET /health`
  - 用于确认服务是否正常启动。
- `POST /api/chat/ask`
  - 用于测试 RAG 检索、答案生成和引用来源返回。

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

## 测试问题

已使用以下问题完成测试：

1. `SV300伺服电机出现E-05报警应该怎么排查？`
2. `CONV_A1输送线启动前需要检查哪些项目？`
3. `CNC_X200主轴温度过高有哪些可能原因？`
4. `锅炉水位异常应该怎么处理？`

其中第 4 个问题属于知识库外问题，用于验证系统是否会拒绝编造引用。

## 测试结果

### 健康检查

- 接口：`GET /health`
- 结果：服务正常返回，说明 FastAPI 应用启动成功。

### SV300 伺服电机 E-05 报警

- 接口：`POST /api/chat/ask`
- 结果：成功返回 `answer` 和 `sources`。
- 验收点：
  - 能检索到 SV300 伺服电机相关文档。
  - 回答围绕 E-05 过载报警、故障原因、排查步骤和维修建议展开。
  - `sources` 中包含文档引用来源。

### CONV_A1 输送线启动前检查

- 接口：`POST /api/chat/ask`
- 结果：成功返回 `answer` 和 `sources`。
- 验收点：
  - 能检索到 CONV_A1 输送线 SOP 相关文档。
  - 回答包含启动前检查、传感器、急停、安全门、输送带状态等内容。
  - `sources` 中包含文档引用来源。

### CNC_X200 主轴温度过高

- 接口：`POST /api/chat/ask`
- 结果：成功返回 `answer` 和 `sources`。
- 验收点：
  - 能检索到 CNC_X200 故障案例相关文档。
  - 回答包含主轴温度、散热、润滑、风扇积尘、切削参数等排查方向。
  - `sources` 中包含文档引用来源。

### 知识库外问题：锅炉水位异常

- 接口：`POST /api/chat/ask`
- 结果：成功返回通用排查建议，且 `sources=[]`。
- 验收点：
  - 系统没有编造文档引用。
  - 当检索不到可靠依据时，能够明确提示知识库没有直接依据。

## 当前技术栈

- Python
- FastAPI
- LangChain
- Chroma
- DeepSeek Chat 模型：`deepseek-v4-flash`
- 智谱 BigModel Embedding 模型：`embedding-3`
- Pydantic Settings
- OpenAI-compatible SDK 调用方式

当前关键配置：

```text
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-v4-flash

EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-3

SIMILARITY_THRESHOLD=0.50
```

## RAG 执行流程

阶段一 RAG 闭环流程如下：

1. 准备设备文档
   - 示例文档位于 `data/sample_docs/`。
   - 文档内容包含设备名称、报警码、故障原因、排查步骤和维修建议。

2. 文档解析
   - 系统读取 `txt`、`pdf`、`docx` 文档。
   - 将文档解析为统一的文本内容和基础元数据。

3. 文本切块
   - 根据 `CHUNK_SIZE` 和 `CHUNK_OVERLAP` 对文档进行切分。
   - 每个 chunk 保留 `file_name`、`page`、`chunk_index` 等元数据。

4. 向量化
   - 使用智谱 BigModel `embedding-3` 将 chunk 转换为向量。

5. 向量入库
   - 将 chunk 文本、向量和元数据写入 Chroma。

6. 用户提问
   - 用户通过 `POST /api/chat/ask` 输入设备故障问题。

7. 知识库检索
   - 系统将用户问题向量化。
   - 在 Chroma 中检索相似文档片段。
   - 将底层 distance 转换为 `similarity_score = 1 / (1 + distance)`。
   - 低于 `SIMILARITY_THRESHOLD=0.50` 的结果不作为可靠依据。

8. 生成回答
   - 如果存在可靠依据，使用 DeepSeek Chat 模型基于检索内容生成答案。
   - 如果没有可靠依据，返回通用排查建议，并保持 `sources=[]`。

9. 返回引用来源
   - `sources` 字段统一包含：
     - `file_name`
     - `page`
     - `chunk_index`
     - `similarity_score`
     - `content_preview`

## 阶段一结论

阶段一验收通过。

系统已经具备一个完整、可演示、可解释的 RAG 最小闭环：文档可以入库，问题可以检索，回答可以生成，引用可以追溯，知识库外问题不会编造来源。

从面试讲解角度，本阶段可以重点说明：

- 为什么先做 RAG 最小闭环，而不是一开始就堆 Agent 和数据库。
- 如何把非结构化设备文档转为可检索知识库。
- 如何通过 `similarity_score` 和阈值控制回答可靠性。
- 如何保证回答带引用，降低大模型幻觉风险。
- 为什么 Chat 和 Embedding 使用不同平台：DeepSeek 负责生成，智谱 `embedding-3` 负责向量化。

## 下一阶段建议

建议进入阶段二：MySQL 业务数据。

阶段二建议目标：

- 引入 Docker MySQL。
- 使用 SQLAlchemy 建立 ORM 模型。
- 新增设备表、报警记录表、维修记录表、对话记录表。
- 提供 `scripts/init_db.py` 初始化示例设备、报警和维修数据。
- 在问答时保存对话记录，为后续历史查询和 Agent 工具调用做准备。

阶段二完成后，可以继续推进：

- 阶段三：Function Calling 工具调用。
- 阶段四：故障诊断 Agent 和 Markdown 报告生成。
- 阶段五：Streamlit 简版前端和完整项目展示文档。
