# 阶段二验收文档：MySQL 业务数据与聊天历史

## 阶段二目标

阶段二目标是在阶段一 RAG 最小闭环的基础上，引入结构化业务数据能力，让系统不只能够检索设备文档，还能够管理和查询制造业运维场景中的设备、报警、维修和问答历史数据。

本阶段重点不是引入 Agent 或 Function Calling，而是先把业务数据底座做好：

- 使用 MySQL 保存设备、报警、维修和聊天记录。
- 使用 SQLAlchemy 定义 ORM 模型。
- 使用初始化脚本写入可演示的样例业务数据。
- 在 FastAPI 中提供设备业务查询接口。
- 在 RAG 问答完成后保存问答记录，并支持按 `session_id` 查询历史。

阶段二完成后，系统已经从“只基于文档问答的 RAG Demo”升级为“具备业务数据管理能力的工业运维 RAG 后端”，为阶段三 Function Calling 工具调用打基础。

## 新增 MySQL 业务数据能力

阶段二新增了 MySQL 业务数据库，当前包含四类数据：

- 设备基础信息：记录设备编码、名称、类型、位置、厂家、安装日期和运行状态。
- 报警记录：记录设备历史报警码、报警等级、报警信息、发生时间、恢复时间和处理状态。
- 维修记录：记录工单编号、故障描述、原因分析、处理方案、维修人员和维修时间。
- 聊天记录：记录用户问题、RAG 回答、引用来源、会话 ID 和关联设备。

这些数据可以支撑后续更接近真实企业场景的功能，例如：

- 查询设备当前信息。
- 查询设备最近报警。
- 查询设备历史维修。
- 根据历史问答追踪诊断过程。
- 在阶段三中把这些查询封装为 Function Calling 工具。

## 数据库表结构说明

### devices

设备基础信息表，用于保存工厂中的设备台账。

| 字段 | 说明 |
| --- | --- |
| `id` | 主键，自增 ID |
| `device_code` | 设备编码，唯一，例如 `SV300-01` |
| `device_name` | 设备名称，例如 `SV300伺服电机` |
| `device_type` | 设备类型，例如 `伺服系统` |
| `location` | 设备位置，例如 `一车间A线` |
| `manufacturer` | 设备厂家 |
| `install_date` | 安装日期 |
| `status` | 设备状态 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### alarm_records

报警记录表，用于保存设备历史报警数据。

| 字段 | 说明 |
| --- | --- |
| `id` | 主键，自增 ID |
| `device_id` | 关联 `devices.id` |
| `alarm_code` | 报警码，例如 `E-05` |
| `alarm_level` | 报警等级，例如 `major`、`warning` |
| `alarm_message` | 报警描述 |
| `occurred_at` | 报警发生时间 |
| `resolved_at` | 报警恢复时间 |
| `status` | 报警状态 |
| `created_at` | 创建时间 |

当前通过 `device_id + alarm_code + occurred_at` 作为业务唯一性判断，避免重复插入相同报警记录。

### maintenance_records

维修记录表，用于保存设备维修工单和处理结论。

| 字段 | 说明 |
| --- | --- |
| `id` | 主键，自增 ID |
| `device_id` | 关联 `devices.id` |
| `work_order_no` | 工单编号，唯一 |
| `fault_description` | 故障描述 |
| `root_cause` | 故障原因 |
| `solution` | 维修方案 |
| `maintainer` | 维修人员 |
| `started_at` | 维修开始时间 |
| `finished_at` | 维修完成时间 |
| `created_at` | 创建时间 |

当前通过 `work_order_no` 判断是否已存在，保证初始化脚本重复执行时不会插入脏数据。

### chat_records

问答记录表，用于保存 RAG 问答历史。

| 字段 | 说明 |
| --- | --- |
| `id` | 主键，自增 ID |
| `session_id` | 会话 ID，用于串联多轮问答 |
| `device_id` | 可选关联 `devices.id` |
| `question` | 用户问题 |
| `answer` | RAG 生成的回答 |
| `sources_json` | JSON 字符串，保存原始 `sources` 引用来源 |
| `created_at` | 创建时间 |

`device_id` 是可选字段。如果请求中传入的 `device_code` 不存在，系统不会阻断 RAG 回答，而是保存 `device_id=None`，并在返回 `message` 中给出温和提示。

## 新增接口说明

### 设备业务查询接口

#### GET /api/devices

返回设备列表。

典型用途：

- 在 Swagger 中查看当前系统有哪些设备。
- 为后续 Agent 工具调用提供设备清单查询能力。

#### GET /api/devices/{device_code}

返回单台设备详情。

示例：

```text
GET /api/devices/SV300-01
```

当设备不存在时，返回清晰错误信息：

```text
设备不存在：{device_code}
```

#### GET /api/devices/{device_code}/alarms

返回指定设备最近报警记录，支持 `limit` 参数，默认值为 5。

示例：

```text
GET /api/devices/SV300-01/alarms?limit=5
```

#### GET /api/devices/{device_code}/maintenance

返回指定设备最近维修记录，支持 `limit` 参数，默认值为 5。

示例：

```text
GET /api/devices/SV300-01/maintenance?limit=5
```

### 问答与历史接口

#### POST /api/chat/ask

阶段二第三批对原 RAG 问答接口做了增强：保留原有 RAG 问答逻辑，同时在回答生成后保存聊天记录。

兼容阶段一请求格式：

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？"
}
```

新增可选字段：

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？",
  "session_id": "test-session-001",
  "device_code": "SV300-01"
}
```

响应中新增 `session_id`：

```json
{
  "message": "已基于知识库检索结果生成回答。",
  "answer": "...",
  "sources": [],
  "session_id": "test-session-001"
}
```

说明：

- `session_id` 不传时由后端自动生成。
- `device_code` 只用于关联 `chat_records.device_id`。
- `device_code` 不参与 RAG 检索、相似度判断或智能诊断。
- 知识库外问题仍保持 `sources=[]`，不会编造引用来源。

#### GET /api/chat/history/{session_id}

按会话 ID 查询历史问答记录。

示例：

```text
GET /api/chat/history/test-session-001
```

返回内容包括：

- `question`
- `answer`
- `sources`
- `session_id`
- `device_code`
- `created_at`

该接口用于验证问答记录是否成功保存，也为后续多轮诊断、报告生成和面试演示提供数据基础。

## 本机 MySQL 部署方式

### 方式一：使用 docker-compose 启动 MySQL

项目提供了 `docker-compose.yml`，可用于快速启动本机 MySQL：

```powershell
docker compose up -d
```

默认数据库配置：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_user
MYSQL_PASSWORD=rag_password
MYSQL_DATABASE=industrial_rag
```

MySQL 容器配置了健康检查，等待 MySQL 就绪后再执行初始化脚本更稳妥。

### 方式二：使用本机已有 MySQL

如果本机已经安装 MySQL，也可以手动创建数据库和用户，并保持 `.env` 中配置一致：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_user
MYSQL_PASSWORD=rag_password
MYSQL_DATABASE=industrial_rag
```

然后安装依赖并初始化数据：

```powershell
python -m pip install -r requirements.txt
python scripts/init_db.py
```

建议连续运行两次：

```powershell
python scripts/init_db.py
python scripts/init_db.py
```

第二次运行不应重复插入设备、报警和维修脏数据。

## 三批验收过程

### 第一批：本机 MySQL 基础能力

目标：

- 新增 MySQL 连接配置。
- 新增 SQLAlchemy ORM 模型。
- 新增 `scripts/init_db.py` 初始化脚本。
- 创建 `devices`、`alarm_records`、`maintenance_records`、`chat_records` 四张表。
- 写入可演示的设备、报警和维修样例数据。

验收结果：

- `requirements.txt` 安装成功。
- `python scripts/init_db.py` 执行成功。
- 第二次运行 `init_db.py` 不会重复插入脏数据。
- MySQL 中可以看到四张表：
  - `devices`
  - `alarm_records`
  - `maintenance_records`
  - `chat_records`
- 阶段一 `POST /api/chat/ask` 仍然正常。

### 第二批：设备业务查询接口

目标：

- 新增设备、报警和维修记录查询接口。
- 让 Swagger 可以直接查看 MySQL 中的业务数据。
- 不修改阶段一 RAG 问答主流程。

验收接口：

```text
GET /api/devices
GET /api/devices/{device_code}
GET /api/devices/{device_code}/alarms
GET /api/devices/{device_code}/maintenance
```

验收结果：

- `GET /api/devices` 可以返回设备列表。
- `GET /api/devices/SV300-01` 可以返回设备详情。
- `GET /api/devices/SV300-01/alarms` 可以返回报警记录。
- `GET /api/devices/SV300-01/maintenance` 可以返回维修记录。
- 查询不存在设备时能返回清晰错误。
- 阶段一 `POST /api/chat/ask` 仍然正常。

### 第三批：问答记录保存和历史查询

目标：

- 增强 `POST /api/chat/ask`，在完成 RAG 回答后保存聊天记录。
- 支持自动生成 `session_id`。
- 支持通过 `device_code` 关联设备。
- 新增历史查询接口。
- 保持 `answer` 和 `sources` 结构不变。

验收接口：

```text
POST /api/chat/ask
GET /api/chat/history/{session_id}
```

验收结果：

- `POST /api/chat/ask` 传 `question`、`session_id`、`device_code` 成功，返回 `answer`、`sources`、`session_id`。
- `GET /api/chat/history/test-session-001` 成功查到历史问答。
- `POST /api/chat/ask` 只传 `question` 成功，后端自动生成 `session_id`。
- 知识库外问题返回 `sources=[]`，并且可以保存到历史记录。
- `device_code` 不存在时不影响 RAG 回答。
- 设备查询接口仍然正常。
- 阶段一 RAG 问答功能未被破坏。

## 阶段一 RAG 功能未被破坏的验证结果

阶段二所有批次完成后，继续验证阶段一能力：

- 原 `POST /api/chat/ask` 只传 `question` 的请求方式仍然支持。
- RAG 问答仍然返回原有结构：
  - `message`
  - `answer`
  - `sources`
- 阶段二仅新增 `session_id` 字段，不改变 `answer` 和 `sources` 的结构。
- 正常知识库问题仍可返回带引用来源的回答。
- 知识库外问题仍返回 `sources=[]`。
- 没有引入 Function Calling、Agent、LangGraph、Streamlit、权限系统或复杂报表。

这说明阶段二是在阶段一基础上的增量增强，而不是重写 RAG 主流程。

## 问答记录保存与历史查询验证结果

已使用以下请求完成验证：

```json
{
  "question": "SV300伺服电机出现E-05报警应该怎么排查？",
  "session_id": "test-session-001",
  "device_code": "SV300-01"
}
```

验证结果：

- 问答接口正常返回 `answer`、`sources` 和 `session_id`。
- 聊天记录成功写入 `chat_records`。
- `device_code=SV300-01` 可以正确关联到设备。
- 通过 `GET /api/chat/history/test-session-001` 可以查到刚才的问题、回答和引用来源。

同时验证了两类边界场景：

1. 只传 `question`
   - 后端自动生成 `session_id`。
   - 问答记录仍可保存。

2. 传入不存在的 `device_code`
   - 不阻断 RAG 回答。
   - `device_id` 保存为空。
   - `message` 中给出温和提示。

3. 知识库外问题
   - 仍返回 `sources=[]`。
   - 不编造引用。
   - 兜底回答也能保存到历史记录。

## 当前仍未做的内容

阶段二刻意没有实现以下内容：

- Function Calling 工具调用。
- Agent 自动规划和多工具调度。
- LangGraph 工作流。
- Streamlit 前端。
- 权限系统、用户登录和角色管理。
- 复杂报表、可视化大屏或 PDF 报告。
- 将 `device_code` 参与智能判断或自动诊断。
- 将报警记录、维修记录自动注入 RAG Prompt。

这些内容都属于后续阶段。阶段二只负责把结构化业务数据和聊天历史保存能力打牢。

## 阶段三 Function Calling 工具调用建议

阶段三建议围绕“让大模型可观测地调用业务工具”展开，而不是直接上复杂 Agent。

建议新增工具：

1. `search_knowledge_base`
   - 输入：用户问题。
   - 输出：知识库检索结果和 `sources`。
   - 作用：复用阶段一 RAG 检索能力。

2. `get_device_info`
   - 输入：`device_code`。
   - 输出：设备基础信息。
   - 作用：让模型知道设备类型、位置、状态等结构化信息。

3. `list_device_alarms`
   - 输入：`device_code`、`limit`。
   - 输出：最近报警记录。
   - 作用：让模型结合真实报警历史分析故障。

4. `list_device_maintenance`
   - 输入：`device_code`、`limit`。
   - 输出：最近维修记录。
   - 作用：让模型参考历史维修经验给出建议。

5. `get_chat_history`
   - 输入：`session_id`。
   - 输出：历史问答记录。
   - 作用：支持后续多轮诊断。

阶段三接口建议返回 `tool_calls`，用于面试演示：

```json
{
  "answer": "...",
  "sources": [],
  "session_id": "test-session-001",
  "tool_calls": [
    {
      "tool_name": "get_device_info",
      "arguments": {"device_code": "SV300-01"},
      "result_summary": "查询到SV300伺服电机，位于一车间A线。"
    }
  ]
}
```

阶段三的讲解重点：

- 为什么先做数据库接口，再做 Function Calling。
- Function Calling 与普通 RAG 的区别：RAG 面向非结构化文档，工具调用面向结构化业务数据。
- 如何通过 `tool_calls` 让系统行为可观测，方便调试和面试展示。
- 如何限制工具边界，避免模型直接“幻想”设备状态或维修记录。

## 阶段二结论

阶段二验收通过。

系统已经具备 MySQL 业务数据能力，可以查询设备、报警、维修记录，并能在 RAG 问答后保存聊天历史。阶段一 RAG 功能保持稳定，阶段二新增能力没有破坏原有问答逻辑。

从简历和面试角度，阶段二可以重点强调：

- 将非结构化 RAG 与结构化业务数据分阶段集成。
- 使用 SQLAlchemy 建模真实工业运维数据。
- 使用幂等初始化脚本保证本地演示环境可重复搭建。
- 使用 FastAPI 暴露清晰的业务查询接口。
- 保存问答历史，为后续多轮诊断和 Agent 工具调用打基础。
