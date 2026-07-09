# 阶段四验收文档：故障诊断Agent与报告生成

## 1. 阶段四目标

阶段四的目标是在阶段一 RAG 知识库问答、阶段二 MySQL 业务数据层、阶段三 Function Calling 工具调用的基础上，进一步面向工业设备运维场景实现故障诊断流程编排、Markdown 诊断报告生成、报告保存和历史查询。

前三个阶段分别解决了三个基础问题：

- 阶段一解决“如何从设备说明书、维修手册、SOP 等非结构化文档中检索依据并生成回答”。
- 阶段二解决“如何管理设备台账、报警记录、维修记录和聊天历史等结构化业务数据”。
- 阶段三解决“如何把知识库检索和数据库查询封装成可观察的工具调用能力”。

阶段四在此基础上把工具调用能力组织成固定的故障诊断流程，让系统能够围绕一个设备故障问题，整合知识库、设备台账、历史报警和历史维修记录，生成结构化诊断结论，并进一步输出 Markdown 诊断报告。报告可以保存到 MySQL，后续支持按 `report_id` 查询单份报告，或按 `session_id` 查询一次会话下的报告列表。

本阶段重点不是构建复杂多轮 Agent，也没有引入 LangGraph，而是以清晰、可验收、可讲解的方式完成一个工业故障诊断助手的核心闭环。

## 2. 阶段四新增能力

阶段四新增能力包括：

- 故障诊断流程编排：新增 `POST /api/diagnosis/analyze`，按固定流程调用知识库和业务数据工具。
- 多源证据整合：把 `knowledge_sources`、`device_info`、`alarm_records`、`maintenance_records` 统一整理到 `evidence` 字段。
- 结构化诊断结论：诊断结论包含故障现象、知识库依据、历史报警依据、历史维修依据、可能原因、排查步骤、维修建议和注意事项。
- Markdown 诊断报告生成：新增 `POST /api/diagnosis/report`，把诊断结果整理成固定结构的 Markdown 报告。
- 诊断报告保存到 MySQL：新增 `diagnosis_reports` 表，保存报告正文、证据数据和工具调用记录。
- 按 `report_id` 查询单份报告：新增 `GET /api/diagnosis/reports/{report_id}`。
- 按 `session_id` 查询报告列表：新增 `GET /api/diagnosis/reports/session/{session_id}`。
- 无依据问题不编造来源：知识库无可靠依据时返回空来源；没有设备编号时不编造设备台账、报警记录或维修记录。

## 3. 阶段四接口说明

### 3.1 POST /api/diagnosis/analyze

功能说明：

执行故障诊断流程编排。接口接收用户问题、可选会话编号和可选设备编号，然后复用阶段三工具能力，按顺序查询设备信息、检索知识库、查询历史报警、查询历史维修，并生成结构化诊断结论。

请求示例：

```json
{
  "question": "SV300伺服电机出现E-05报警，现场应该如何排查？",
  "session_id": "diagnosis-session-001",
  "device_code": "SV300-01"
}
```

响应字段说明：

| 字段 | 说明 |
| --- | --- |
| `message` | 诊断流程执行结果提示 |
| `diagnosis` | 结构化诊断结论文本 |
| `evidence` | 多源证据集合 |
| `tool_calls` | 本次诊断流程调用过的工具记录 |
| `session_id` | 本次会话编号，不传时后端生成 |

典型测试用例：

- SV300 伺服电机 E-05 报警，传入 `device_code=SV300-01`，期望返回设备信息、知识库依据、报警记录、维修记录和诊断建议。
- CONV_A1 输送线过载，传入 `device_code=CONV-A1`，期望结合输送线知识库和业务记录生成诊断。
- 锅炉水位异常，不传 `device_code`，期望明确说明缺少设备编号，不编造业务数据。

### 3.2 POST /api/diagnosis/report

功能说明：

生成 Markdown 诊断报告，并保存到 MySQL 的 `diagnosis_reports` 表。接口内部复用 `POST /api/diagnosis/analyze` 的诊断流程，不重新写设备查询、知识库检索、报警查询或维修查询逻辑。

请求示例：

```json
{
  "question": "SV300伺服电机出现E-05报警，请生成一份诊断报告。",
  "session_id": "report-history-001",
  "device_code": "SV300-01"
}
```

响应字段说明：

| 字段 | 说明 |
| --- | --- |
| `message` | 报告生成提示 |
| `report_id` | 报告唯一编号，用于查询单份报告 |
| `report_markdown` | Markdown 格式诊断报告正文 |
| `evidence` | 本次报告依据的证据数据 |
| `tool_calls` | 本次报告生成过程中使用的工具调用记录 |
| `session_id` | 本次报告所属会话编号 |

典型测试用例：

- SV300 伺服电机 E-05 报警报告，期望返回完整 Markdown 结构和 `report_id`。
- CONV_A1 输送线过载报告，期望结合输送线知识库、报警记录和维修记录。
- 锅炉水位异常报告，不传设备编号，期望不编造设备、报警、维修和知识库来源，也可以保存报告。

### 3.3 GET /api/diagnosis/reports/{report_id}

功能说明：

根据 `report_id` 查询单份诊断报告，返回报告正文、证据、工具调用记录、设备编号和创建时间。

请求示例：

```text
GET /api/diagnosis/reports/550e8400-e29b-41d4-a716-446655440000
```

响应字段说明：

| 字段 | 说明 |
| --- | --- |
| `report_id` | 报告唯一编号 |
| `session_id` | 报告所属会话编号 |
| `device_code` | 关联设备编号，可能为空 |
| `question` | 用户原始问题 |
| `report_markdown` | Markdown 报告正文 |
| `evidence` | 反序列化后的证据数据 |
| `tool_calls` | 反序列化后的工具调用记录 |
| `created_at` | 报告创建时间 |

典型测试用例：

- 使用 `POST /api/diagnosis/report` 返回的 `report_id` 查询报告，期望能查到完整报告。
- 使用不存在的 `report_id` 查询，期望返回清晰的 404 错误信息。

### 3.4 GET /api/diagnosis/reports/session/{session_id}

功能说明：

按 `session_id` 查询该会话下的诊断报告列表，适合展示一次排查会话中生成过的多份报告。

请求示例：

```text
GET /api/diagnosis/reports/session/report-history-001
```

响应字段说明：

| 字段 | 说明 |
| --- | --- |
| `message` | 查询结果提示 |
| `session_id` | 查询的会话编号 |
| `items` | 报告列表，每条结构与单份报告查询基本一致 |

典型测试用例：

- 先用相同 `session_id` 生成一份或多份报告，再查询该会话报告列表。
- 查询一个暂时没有报告的 `session_id`，期望返回空列表，不报错。

## 4. 诊断流程说明

阶段四完整诊断流程如下：

1. 用户输入故障问题，例如“SV300伺服电机出现E-05报警，请生成一份诊断报告”。
2. 接口接收可选 `device_code`，例如 `SV300-01`。
3. 如果传入设备编号，调用 `query_device_info` 查询设备基础信息。
4. 调用 `search_knowledge_base` 检索知识库，获取说明书、维修手册、SOP 或故障案例中的相关片段。
5. 如果传入设备编号，调用 `query_alarm_records` 查询历史报警记录。
6. 如果传入设备编号，调用 `query_maintenance_records` 查询历史维修记录。
7. 将以上结果整理为统一的 `evidence`。
8. 调用大模型生成结构化诊断结论。
9. 把诊断结论、证据和工具调用记录整理成 Markdown 报告。
10. 将报告保存到 MySQL 的 `diagnosis_reports` 表。
11. 后续可通过 `report_id` 查询单份报告，或通过 `session_id` 查询报告列表。

这个流程的特点是证据链清晰：每一步用了什么工具、查到了什么数据、哪些依据为空，都可以在 `evidence` 和 `tool_calls` 中看到。

## 5. evidence 字段说明

`evidence` 是诊断和报告生成的证据集合，主要包含四类数据：

| 字段 | 说明 |
| --- | --- |
| `knowledge_sources` | 知识库检索结果，包含文件名、chunk 序号、相似度和内容预览 |
| `device_info` | 设备基础信息，来自 MySQL `devices` 表 |
| `alarm_records` | 历史报警记录，来自 MySQL `alarm_records` 表 |
| `maintenance_records` | 历史维修记录，来自 MySQL `maintenance_records` 表 |

如果没有知识库可靠依据，`knowledge_sources=[]`，报告中会明确写“知识库未检索到高于阈值的可靠依据”。如果没有传入设备编号，则不会查询设备台账、报警记录和维修记录，报告中会明确说明无法结合这些业务数据分析。

## 6. tool_calls 字段说明

`tool_calls` 用于记录本次诊断流程调用了哪些工具，以及每个工具的输入、执行状态和结果摘要。

返回 `tool_calls` 的价值包括：

- 方便观察模型或系统调用了哪些工具。
- 方便调试工具输入参数和执行结果。
- 方便在面试中展示 Function Calling 的执行过程。
- 方便后续扩展 Agent 可观测性，例如展示推理链路、工具耗时或工具失败原因。

每条 `tool_calls` 通常包含：

| 字段 | 说明 |
| --- | --- |
| `tool_name` | 工具名称 |
| `arguments` | 工具入参 |
| `success` | 工具是否执行成功 |
| `summary` | 工具执行摘要 |
| `result_preview` | 工具结果预览 |

## 7. Markdown 报告结构说明

阶段四生成的 Markdown 报告固定包含以下结构：

1. 基本信息
2. 故障现象
3. 设备基础信息
4. 知识库依据
5. 历史报警依据
6. 历史维修依据
7. 综合诊断结论
8. 工具调用记录
9. 结论说明

这种结构适合后续在前端展示，也适合面试时讲清楚“报告不是凭空生成，而是来自知识库、设备台账、历史报警和历史维修记录的综合整理”。

## 8. 数据库表说明

阶段四新增 `diagnosis_reports` 表，用于保存诊断报告历史。

| 字段 | 说明 |
| --- | --- |
| `id` | 数据库自增主键 |
| `report_id` | 报告唯一编号，使用 UUID 或唯一字符串 |
| `session_id` | 会话编号，用于按会话查询报告列表 |
| `device_id` | 可选关联 `devices.id`，无设备编号或设备不存在时为空 |
| `question` | 用户原始问题 |
| `report_markdown` | Markdown 报告正文 |
| `evidence_json` | JSON 字符串，保存证据数据 |
| `tool_calls_json` | JSON 字符串，保存工具调用记录 |
| `created_at` | 报告创建时间 |

该表让诊断报告具备可追溯性：不仅能看到最终报告，还能回看报告生成时使用的证据和工具调用过程。

## 9. 验收测试记录

阶段四已通过以下验证：

- `python -m unittest discover`
- `python -m compileall app scripts tests`
- Swagger 真实测试
- MySQL 报告保存和查询测试

Swagger 已验证：

- `POST /api/diagnosis/analyze` 正常。
- `POST /api/diagnosis/report` 可以返回 `report_id`、`report_markdown`、`evidence`、`tool_calls`、`session_id`。
- `GET /api/diagnosis/reports/{report_id}` 可以查询单份报告。
- `GET /api/diagnosis/reports/session/{session_id}` 可以查询会话下报告列表。
- 无 `device_code` 的问题也能生成和保存报告，并且不编造设备、报警、维修和知识库来源。
- 原 `POST /api/chat/ask`、`POST /api/chat/ask-with-tools`、`GET /api/devices` 等接口仍然正常。

## 10. 未做内容说明

当前阶段没有做以下内容：

- LangGraph
- 复杂多轮 Agent
- Streamlit 前端
- 权限系统
- PDF 导出
- 复杂报表导出
- 生产级数据库迁移
- 部署上线

这些内容被刻意放到后续阶段，避免在当前阶段把系统复杂度拉得过高。当前阶段的重点是把故障诊断、报告生成、报告保存和历史查询这条后端主链路做完整。

## 11. 阶段五建议

阶段五可以围绕项目展示和求职材料继续完善：

- Streamlit 前端：提供文档上传、设备选择、问题输入、回答展示、报告展示和历史查询页面。
- 项目 README 完善：补齐完整启动流程、接口列表、典型测试用例和阶段说明。
- 接口演示截图：整理 Swagger、报告生成、历史查询等关键截图。
- 简历项目描述：提炼技术栈、职责、项目亮点和量化表达。
- GitHub 整理：清理敏感配置，补充 `.env.example`、验收文档和项目结构说明。
- 部署说明：如果后续需要，可以补充本地 Docker Compose 或云服务器部署步骤。
