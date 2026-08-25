# trace_from_fornax

Fornax 平台的 Trace 链路追踪表，记录 Trae Agent 每次请求的完整 span 信息，包含模型输入输出、意图识别、经验召回等结构化数据。`_tags` 字段为 JSON，包含 conversation_id、message_id、model_name 等关键 ID。`sensitive_tags` 存放模型请求的结构化数据（model_input、model_output）。适用场景：查询某个 log_id 的完整 trace 详情、排查模型调用问题、查看 Agent 问答上下文。

- cn: `flow_aipaas.trace_from_fornax`
- i18n: 待确认
- 分区字段: date（yyyyMMdd）+ hour（HH）
- TTL: 14天
- GUID: `357aaed6-5640-42e4-ad87-05febee08307`
- 设计背景: Fornax 平台产出的 trace 数据表，是 Trae Agent 链路追踪的核心数据源。查询时**必须限定** `fornax_space_id = '7444123531090067458'`（Trae 的 space ID），否则会查到其他业务的 trace 数据

## 查询要点

- **必须限定条件**: `fornax_space_id = '7444123531090067458'`
- **关键 span 筛选**: `_span_name IN ('[Track]PromptRenderNode', 'LLMCallSpan', 'ExperienceRecall', 'IntentRecognition')`
  - `[Track]PromptRenderNode`: 输入信息
  - `LLMCallSpan`: LLM 上下文
  - `ExperienceRecall`: EAG 相关
  - `IntentRecognition`: 意图相关
- **查看 Agent 问答模型**: 需限定 `_method = 'LLMRawChatV2'`
- **从 _tags 提取 ID**: 使用 `get_json_object(_tags, '$.conversation_id')` 等

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| _trace_id | string | 唯一标识一次请求的 trace ID |
| _span_id | string | 唯一标识一个 span 的 ID |
| __logid | string | 日志 ID（log_id），用于关联模型调用 |
| _server_env | string | 服务器环境 |
| _events | array\<string\> | 事件列表 |
| _span_type | string | span 类型 |
| _duration | bigint | span 持续时间 |
| _tags | string | 标签（JSON），包含 conversation_id、message_id、model_name 等 |
| _start_time | bigint | span 开始时间 |
| _method | string | 调用方法（如 LLMRawChatV2） |
| _parent_id | string | 父 span ID |
| _span_name | string | span 名称（如 LLMCallSpan、IntentRecognition 等） |
| _status_code | bigint | 状态码 |
| file_time | bigint | 归档时间戳 |
| _trace_tags | string | trace 级别的标签 |
| sensitive_tags | string | 敏感字段标签（JSON），包含 model_input、model_output |
| tenant | string | 数据源标识 |
| is_aw | string | is_aw 标记 |
| bot_id | bigint | Agent ID |
| fornax_space_id | bigint | Fornax Space ID（Trae 为 7444123531090067458） |

> 分区键: date (string, yyyyMMdd) + hour (string, HH)
