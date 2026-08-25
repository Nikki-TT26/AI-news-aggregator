# trae_agent_fornax_detail_di

Trae Agent Fornax Span 明细表（ODS），从 Fornax 平台 Span 数据中按 Trae 业务的 Fornax Space ID 和相关 span_name 筛选出的原始 Span 级数据。每行一个 Span，包含完整的模型输入输出、token 用量、调用参数等信息。适用于需要 Span 级别原始数据的深度分析、自定义聚合场景。

- cn: `flow_aipaas.trae_agent_fornax_detail_di`
- i18n: `ai_application_coding.trae_agent_fornax_detail_di`
- 分区字段: date（yyyyMMdd）
- TTL: 无（未设置）
- GUID: `57e7fb03-fc0d-4ee5-b778-60f2e0daa756`
- 上游表: `loop_dw.dwd_impr_fornax_trace_detail_hi`（Fornax 平台小时表，TTL 7天）
- 一级下游表: `flow_aipaas.trae_traj_detail_di`、`flow_aipaas.trae_conversation_message_map_di`、`flow_aipaas.trae_message_traj_map_di`
- 设计背景: Trae Agent 轨迹数据离线表体系的 ODS 层。从 Fornax 平台小时表按 space_id 和 span_name 筛选后按天存储，是 Trajectory 系列表的数据源。每天 T+1 刷新，SLA T+1 04:00 前

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| trace_id | string | Trace ID，原始 _trace_id |
| span_id | string | Span ID，原始 _span_id |
| log_id | string | Log ID，原始 __logid |
| parent_span_id | string | 父 Span ID，原始 _parent_id，用于识别子 Agent 的 Span 层级 |
| span_name | string | Span 名称：LLMCallSpan / agent 名称（如 SOLO Coder）等 |
| span_type | string | Span 类型：model / agent / Service |
| start_time | bigint | 开始时间（微秒时间戳） |
| duration | bigint | 持续时间（微秒） |
| status_code | bigint | 状态码，0=成功 |
| method | string | 方法名：LLMRawChatV2 / create_agent_task 等 |
| server_env | string | 服务器环境 JSON，含 psm/region/pod_name 等 |
| conversation_id | string | 会话 ID，从 _tags.conversation_id 提取 |
| message_id | string | 消息 ID，从 _tags.message_id 提取 |
| agent_id | string | Agent 运行实例 ID（每次运行生成唯一值），从 _tags 提取 |
| model_name | string | 模型名称，仅 LLMCallSpan 有值，从 _tags 提取 |
| llm_usage | string | LLM 调用用途：chat_completion / compact，从 _tags 提取 |
| agent_name | string | Agent 名称，如 SOLO Coder / Search Agent |
| main_agent_type | string | 主 Agent 类型，如 solo_coder，关联 agent span |
| parent_agent_run_id | string | 父 Agent 运行 ID（子 Agent 才有值），关联 agent span |
| parent_trace_id | string | 父 Trace ID，异步过程关联字段，从 _trace_tags 提取 |
| input_json | string | 模型输入 JSON，从 sensitive_tags.input 提取，含完整 messages 数组 |
| output_json | string | 模型输出 JSON，从 sensitive_tags.output 提取，含 choices 数组 |
| input_tokens | bigint | 输入 token 数，从 sensitive_tags.input_tokens 提取 |
| output_tokens | bigint | 输出 token 数，从 sensitive_tags.output_tokens 提取 |
| total_tokens | bigint | 总 token 数，从 sensitive_tags.tokens 提取 |
| call_options_json | string | 调用参数 JSON（temperature / max_tokens / top_p 等） |
| tags_json | string | 完整 _tags JSON，保留供下游灵活解析 |
| trace_tags_json | string | 完整 _trace_tags JSON |
| sensitive_tags_json | string | 完整 sensitive_tags JSON |
| fornax_space_id | bigint | Fornax Space ID |

> 分区键: date (string, yyyyMMdd)
