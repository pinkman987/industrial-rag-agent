# 阶段三验收文档：Function Calling 工具调用

> 历史阶段记录：下文的“单轮、一次工具选择”描述对应早期验收版本。当前版本已支持最多两轮工具执行，保留模型原始调用 ID、每轮解析参数、复用相同查询结果；后续模型失败保留已取得证据。最新接口说明见 [README](../README.md)，回归测试见 `tests/test_tool_loop_reliability.py`。

## 阶段三目标

阶段三目标是在阶段一 RAG 最小闭环和阶段二 MySQL 业务数据层的基础上，引入可观测、可解释的 Function Calling 工具调用能力。

阶段一解决的是“如何从非结构化设备文档中检索依据并生成回答”。阶段二解决的是“如何管理结构化业务数据，例如设备、报警、维修和聊天历史”。阶段三则把这两类能力封装成工具，让大模型可以根据用户问题选择合适的数据来源，并把工具调用过程以 `tool_calls` 的形式返回和保存。

本阶段刻意不做复杂 Agent，不引入 LangGraph，不做多轮规划，只实现一个清晰的工具调用问答接口：

- 用户提出设备故障或运维问题。
- 系统选择知识库检索、设备信息查询、报警查询、维修查询等工具。
- 工具执行结果被整理为上下文。
- 大模型基于工具结果生成最终回答。
- 接口返回 `answer`、`sources`、`tool_calls` 和 `session_id`。
- `tool_calls` 会保存到聊天历史中，便于后续追踪和面试展示。

## 阶段三新增能力

阶段三新增了三类能力：

1. 工具函数封装
   - 将阶段一 Chroma 知识库检索封装为普通 Python 工具函数。
   - 将阶段二 MySQL 查询能力封装为普通 Python 工具函数。
   - 所有工具函数统一返回普通 `dict`，不直接暴露 LangChain 对象或 SQLAlchemy ORM 对象。

2. Function Calling 问答接口
   - 新增独立接口 `POST /api/chat/ask-with-tools`。
   - 保留原有 `POST /api/chat/ask`，不修改阶段一 RAG 主流程。
   - 支持 OpenAI 兼容工具规格。
   - 如果模型不支持标准 `tool_calls`，使用关键词降级选择工具。

3. 工具调用历史保存
   - `chat_records` 新增 `tool_calls_json` 字段。
   - `ask-with-tools` 的工具调用记录会保存到 MySQL。
   - `GET /api/chat/history/{session_id}` 返回历史记录时包含 `tool_calls`。

## 工具函数说明

### search_knowledge_base

文件：

```text
app/tools/rag_tools.py
```

作用：

复用阶段一 Chroma 检索能力，根据用户问题检索工业设备运维知识库。

输入参数：

| 参数 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `str` | 是 | 用户问题 |
| `device_code` | `str` | 否 | 设备编码，第一批只作为辅助过滤或检索提示 |

返回结构：

```json
{
  "success": true,
  "tool_name": "search_knowledge_base",
  "query": "SV300伺服电机出现E-05报警应该怎么排查？",
  "device_code": "SV300-01",
  "sources": [
    {
      "file_name": "SV300_servo_manual.txt",
      "page": null,
      "chunk_index": 0,
      "similarity_score": 0.56,
      "content_preview": "..."
    }
  ],
  "summary": "检索到若干条知识库片段。"
}
```

如果没有可靠依据：

```json
{
  "success": true,
  "tool_name": "search_knowledge_base",
  "query": "...",
  "device_code": null,
  "sources": [],
  "summary": "知识库未检索到高于阈值的可靠依据。"
}
```

### query_device_info

文件：

```text
app/tools/db_tools.py
```

作用：

查询指定设备的基础信息。

输入参数：

| 参数 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| `device_code` | `str` | 是 | 设备编码，例如 `SV300-01` |

返回结构：

```json
{
  "success": true,
  "tool_name": "query_device_info",
  "device_code": "SV300-01",
  "data": {
    "device_code": "SV300-01",
    "device_name": "SV300伺服电机",
    "device_type": "伺服系统",
    "location": "一车间A线",
    "manufacturer": "华东自动化",
    "install_date": "2023-05-18",
    "status": "running"
  },
  "summary": "已查询到设备基础信息。"
}
```

### query_alarm_records

作用：

查询指定设备最近报警记录。

输入参数：

| 参数 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| `device_code` | `str` | 是 | 设备编码 |
| `limit` | `int` | 否 | 返回最近多少条，默认 5 |

返回结构：

```json
{
  "success": true,
  "tool_name": "query_alarm_records",
  "device_code": "SV300-01",
  "data": [
    {
      "alarm_code": "E-05",
      "alarm_level": "major",
      "alarm_message": "伺服驱动器过载报警",
      "occurred_at": "2026-06-20T09:15:00",
      "resolved_at": "2026-06-20T10:05:00",
      "status": "resolved"
    }
  ],
  "summary": "已查询到设备近期报警记录。"
}
```

### query_maintenance_records

作用：

查询指定设备最近维修记录。

输入参数：

| 参数 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| `device_code` | `str` | 是 | 设备编码 |
| `limit` | `int` | 否 | 返回最近多少条，默认 5 |

返回结构：

```json
{
  "success": true,
  "tool_name": "query_maintenance_records",
  "device_code": "SV300-01",
  "data": [
    {
      "work_order_no": "WO-SV300-001",
      "fault_description": "SV300伺服电机运行中出现E-05过载报警。",
      "root_cause": "导轨润滑不足，机械负载偏高，加减速时间设置偏短。",
      "solution": "清理导轨并补充润滑脂，延长加减速时间，复测负载电流。",
      "maintainer": "张工",
      "started_at": "2026-06-20T09:30:00",
      "finished_at": "2026-06-20T10:20:00"
    }
  ],
  "summary": "已查询到设备历史维修记录。"
}
```

## Function Calling 接口说明

### POST /api/chat/ask-with-tools

文件：

```text
app/api/tool_chat.py
```

请求示例：

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-session-001",
  "device_code": "SV300-01"
}
```

响应示例：

```json
{
  "message": "已基于工具调用结果生成回答。",
  "answer": "...",
  "sources": [
    {
      "file_name": "SV300_servo_manual.txt",
      "page": null,
      "chunk_index": 0,
      "similarity_score": 0.62,
      "content_preview": "..."
    }
  ],
  "tool_calls": [
    {
      "tool_name": "search_knowledge_base",
      "arguments": {
        "query": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
        "device_code": "SV300-01"
      },
      "success": true,
      "summary": "检索到若干条知识库片段。",
      "result_preview": "..."
    },
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

说明：

- 该接口是新增接口，不替代原来的 `POST /api/chat/ask`。
- `device_code` 用于工具查询，不会修改阶段一 RAG 接口行为。
- 本阶段只允许一次工具选择和一次结果总结，不做循环推理。
- 如果模型不支持标准 `tool_calls`，系统会使用关键词降级规则选择工具。

## tool_calls 字段说明

`tool_calls` 是阶段三最重要的可观测字段，用于解释系统在回答前调用了哪些工具。

每条记录包含：

| 字段 | 说明 |
| --- | --- |
| `tool_name` | 工具名称，例如 `query_alarm_records` |
| `arguments` | 工具入参 |
| `success` | 工具是否执行成功 |
| `summary` | 工具执行摘要 |
| `result_preview` | 工具结果预览，便于调试和面试展示 |

`tool_calls` 的价值：

- 让大模型回答过程可解释。
- 能清楚展示系统使用了哪些数据来源。
- 能区分知识库检索、设备信息查询、报警查询和维修查询。
- 便于定位工具失败、参数错误或数据缺失问题。
- 为阶段四 Agent 诊断流程提供基础审计记录。

## 工具调用问答流程

阶段三 Function Calling 问答流程如下：

1. 用户调用 `POST /api/chat/ask-with-tools`。
2. 系统接收 `question`、`session_id`、`device_code`。
3. 系统将问题和工具规格发送给 Chat 模型。
4. 如果模型返回标准 `tool_calls`：
   - 解析工具名和参数。
   - 执行白名单内的工具。
5. 如果模型没有返回标准 `tool_calls`：
   - 启用关键词降级逻辑。
   - 问题包含“报警”“历史报警”时调用 `query_alarm_records`。
   - 问题包含“维修”“工单”“历史维修”时调用 `query_maintenance_records`。
   - 问题包含“设备信息”“基础信息”“位置”“厂家”“状态”时调用 `query_device_info`。
   - 其他故障排查类问题调用 `search_knowledge_base`。
6. 工具执行器统一生成 `tool_call` 记录。
7. 系统将工具结果整理为上下文。
8. Chat 模型基于工具结果生成最终回答。
9. 如果总结模型调用失败，使用工具摘要生成兜底回答。
10. 接口返回 `answer`、`sources`、`tool_calls`、`session_id`。
11. 系统将问答、引用来源和 `tool_calls` 保存到 `chat_records`。

这个流程不是复杂 Agent。它没有多轮循环、没有自主规划、没有状态机，只是一个可控的一轮工具调用问答链路。

## Swagger 测试用例

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

启动命令：

```powershell
python scripts/init_db.py
uvicorn app.main:app --reload
```

### 用例 1：SV300 故障排查

接口：

```text
POST /api/chat/ask-with-tools
```

请求：

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-session-001",
  "device_code": "SV300-01"
}
```

期望：

- 返回 HTTP 200。
- 返回 `answer`、`sources`、`tool_calls`、`session_id`。
- `tool_calls` 至少包含知识库检索、报警记录查询或维修记录查询。

### 用例 2：CONV_A1 报警和维修记录

请求：

```json
{
  "question": "CONV_A1输送线最近有哪些报警和维修记录？",
  "session_id": "tool-session-002",
  "device_code": "CONV-A1"
}
```

期望：

- `tool_calls` 包含 `query_alarm_records` 或 `query_maintenance_records`。
- 回答能结合报警记录和维修记录进行说明。

### 用例 3：CNC_X200 基础信息

请求：

```json
{
  "question": "CNC_X200设备的基础信息是什么？",
  "session_id": "tool-session-003",
  "device_code": "CNC-X200"
}
```

期望：

- `tool_calls` 包含 `query_device_info`。
- 回答包含设备名称、类型、位置、厂家或状态等基础信息。

### 用例 4：知识库外问题

请求：

```json
{
  "question": "锅炉水位异常应该怎么处理？",
  "session_id": "tool-session-004"
}
```

期望：

- 如果知识库没有可靠依据，`sources=[]` 或提示无直接依据。
- 不编造引用来源。
- `tool_calls` 中能看到实际调用了哪些工具。

## 历史记录保存 tool_calls 的验证结果

阶段三第三批新增了 `chat_records.tool_calls_json` 字段，用于保存工具调用记录。

兼容处理：

- 新建数据库时，ORM 会创建 `tool_calls_json` 字段。
- 已有数据库中如果 `chat_records` 缺少该字段，`scripts/init_db.py` 会执行兼容迁移：

```sql
ALTER TABLE chat_records ADD COLUMN tool_calls_json TEXT
```

该迁移只新增字段，不删除表，不清空数据，不破坏已有聊天历史。

已验证请求：

```json
{
  "question": "SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
  "session_id": "tool-history-001",
  "device_code": "SV300-01"
}
```

再查询：

```text
GET /api/chat/history/tool-history-001
```

验证结果：

- 历史记录中能看到 `question`。
- 历史记录中能看到 `answer`。
- 历史记录中能看到 `sources`。
- 历史记录中能看到 `tool_calls`。
- 历史记录中能看到 `session_id`。
- 历史记录中能看到 `device_code`。
- 历史记录中能看到 `created_at`。

原 `POST /api/chat/ask` 保存的普通 RAG 问答记录也兼容历史查询，`tool_calls` 为空数组。

## 阶段一 RAG 和阶段二 MySQL 接口未被破坏的验证结果

阶段三完成后，继续验证原有能力：

### 阶段一 RAG

接口：

```text
POST /api/chat/ask
```

验证结果：

- 原接口仍然可以正常返回 200。
- 原请求方式仍然支持。
- 原回答结构没有被阶段三替换。
- 知识库外问题仍然不编造引用。

### 阶段二设备查询

接口：

```text
GET /api/devices
GET /api/devices/{device_code}
GET /api/devices/{device_code}/alarms
GET /api/devices/{device_code}/maintenance
GET /api/chat/history/{session_id}
```

验证结果：

- 设备列表接口仍然正常。
- 设备详情接口仍然正常。
- 报警记录接口仍然正常。
- 维修记录接口仍然正常。
- 历史查询接口在保留原字段基础上新增了 `tool_calls`。

这说明阶段三是新增独立能力，没有破坏阶段一和阶段二主流程。

## 当前仍未做的内容

阶段三仍然没有实现以下内容：

- 复杂 Agent。
- LangGraph 工作流。
- 多轮自主规划。
- 循环工具调用。
- 自动生成完整维修报告。
- Streamlit 前端。
- 权限系统。
- 用户登录和角色管理。
- 复杂报表或数据大屏。
- 工具调用成本统计。
- 人工确认后执行维修动作。

这些内容都属于后续阶段。阶段三的定位是“可观测 Function Calling 工具调用”，不是完整 Agent 系统。

## 阶段四 Agent 诊断流程建议

阶段四可以在阶段三基础上实现“故障诊断 Agent 和 Markdown 报告生成”，但建议仍然保持边界清晰，不要一开始就做复杂多智能体系统。

建议目标：

- 输入用户问题、`device_code` 和可选 `session_id`。
- 自动组合知识库、设备信息、报警记录、维修记录和历史问答。
- 生成结构化 Markdown 故障诊断报告。
- 报告包含故障现象、相关设备、知识库依据、历史报警、维修参考、排查步骤、风险提示和建议动作。
- 保存诊断报告，便于面试展示和后续前端展示。

建议 Agent 流程：

1. 识别问题中的设备和故障线索。
2. 调用 `query_device_info` 获取设备基础信息。
3. 调用 `query_alarm_records` 获取近期报警。
4. 调用 `query_maintenance_records` 获取历史维修记录。
5. 调用 `search_knowledge_base` 获取文档依据。
6. 可选调用历史查询，获取同一 `session_id` 下的上下文。
7. 汇总工具结果。
8. 生成 Markdown 诊断报告。

报告建议结构：

```markdown
# 故障诊断报告

## 1. 问题概述

## 2. 关联设备信息

## 3. 知识库依据

## 4. 历史报警分析

## 5. 历史维修参考

## 6. 可能原因

## 7. 排查步骤

## 8. 维修建议

## 9. 风险提示
```

阶段四面试讲解重点：

- 阶段三解决“工具能被调用且过程可观测”。
- 阶段四解决“如何把多类工具结果组织成可交付诊断报告”。
- Agent 不是让模型无限自由行动，而是把工具、步骤、输出格式和边界收束起来。

## 阶段三结论

阶段三验收通过。

系统已经具备 Function Calling 工具调用能力：可以根据用户问题调用知识库检索、设备信息查询、报警查询和维修查询，并返回可观测的 `tool_calls`。工具调用结果能够保存到聊天历史中，后续可以追踪每次回答使用了哪些工具和数据来源。

从简历和面试角度，阶段三可以重点强调：

- 将 RAG 与 MySQL 业务查询封装成可复用工具。
- 使用 OpenAI 兼容 Function Calling 规格描述工具。
- 用白名单执行器限制工具调用边界。
- 通过 `tool_calls` 增强系统可解释性。
- 在模型不支持标准工具调用时提供关键词降级逻辑。
- 将工具调用记录持久化，为后续 Agent 诊断报告打基础。
