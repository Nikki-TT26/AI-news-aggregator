# dwd_resource_prompt_completion_di

AI 代码生成服务中用户与模型交互的请求明细表（prompt + completion 粒度）。记录每次模型调用的请求内容、回复内容、token 消耗、延迟指标、排队状态、隐私模式等信息。数据来源于 codeverse_codegen_cn.prompt_completion_hourly 表，经字段提取和转换处理后按天分区存储。适用场景：AI 模型使用情况分析、性能监控、模型调用成本分析、请求级别的排查与追溯。

- cn: `cloudide.dwd_resource_prompt_completion_di`
- i18n: `cloudide.dwd_resource_prompt_completion_di`（sg 同库名 cloudide）
- 分区字段: date（yyyyMMdd）
- TTL: 730天
- Dorado 任务 (cn): [dwd_resource_prompt_completion_di](https://data.bytedance.net/dorado/development/node/119615157?project=cn_11253) (projectId: 11253, taskId: 119615157)
- Dorado 任务 (sg): taskId: 304704920
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_resource_prompt_completion_di%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_resource_prompt_completion_di%406#group=default
- 上游表: `codeverse_codegen_cn.prompt_completion_hourly`（cn 数据来源）
- 关联表: `codeverse_codegen_cn.prompt_completion_bd_hourly`（内场版本，原始表，schema 与 prompt_completion_hourly 相同）
- 设计背景: 插件和 IDE 外场问答请求明细表，记录每次 prompt-completion 交互，是模型调用层面的原始数据，与 DWD 行为表（event_di、delta_di 等前端埋点来源）属于不同数据链路。**外场场景优先使用本表**（已将 token 拆成独立字段）；内场可直接使用 `prompt_completion_bd_hourly`（目前无对应的按天聚合表）

> ⚠️ **session_id / conversation_id 语义反转**：本表中 `session_id` 的实际含义是 **message_id**（消息级标识），`conversation_id` 的实际含义是 **session_id**（会话级标识）。与其他表（如 event_di、delta_di）的命名约定相反。下游表 `dwd_trae_chat_model_cost_di` 已在 Dorado SQL 中通过 `conversation_id AS session_id, session_id AS message_id` 修正了语义。使用本表时务必注意字段语义。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | bigint | 废弃字段，固定为 0 |
| app_id | string | 应用 ID，标识请求来源应用 |
| user_id | string | 用户 ID（账号标识） |
| model_name | string | 调用的 AI 模型名称 |
| status | string | 请求状态：success / fail |
| session_id | string | ⚠️ **注意：该字段实际含义是 message_id**（消息级标识），而非会话级 session。关联同一请求的多次模型交互（意图识别/context 选择/chat）。下游表 `dwd_trae_chat_model_cost_di` 已通过 `session_id AS message_id` 修正语义 |
| prompt | string | 向模型输入的 prompt 内容 |
| type | string | 对话类型：intent_detect（意图识别）/ context_selection（context 选择）/ chat（对话） |
| content_raw | string | 模型返回的原始回复内容 |
| content_processed | string | 处理后的模型回复内容 |
| prompt_template_id | string | prompt 模板 ID |
| request_metadata | string | 模型调用元信息（JSON），含 token 用量、延迟、finish_reason、agent_type、trace_id 等，详见下方说明 |
| total_tokens_cnt | bigint | 总 token 消耗 |
| prompt_tokens_cnt | bigint | prompt token 消耗 |
| completion_tokens_cnt | bigint | completion token 消耗 |
| create_timestamp | bigint | 创建时间戳 |
| create_date | string | 创建日期（yyyyMMdd） |
| update_timestamp | bigint | 更新时间戳 |
| update_date | string | 更新日期（yyyyMMdd） |
| delete_timestamp | bigint | 删除时间戳 |
| delete_date | string | 删除日期（yyyyMMdd） |
| context_variable | string | 调用参数信息 |
| region | string | 数据来源 region |
| is_queue | int | 请求是否排队：1-是，0-否，-1-未知（数据可用时间 2025-02-28） |
| queue_latency_seconds | double | 排队耗时（秒）（数据可用时间 2025-02-28） |
| usage_cnt_up_to_now | bigint | 本次请求前已使用次数（数据可用时间 2025-02-28） |
| cache_creation_tokens_cnt | bigint | 首次创建缓存的 prompt token 数（数据可用时间 2025-03-18） |
| cache_read_tokens_cnt | bigint | 命中缓存的 prompt token 数（数据可用时间 2025-03-18） |
| reasoning_tokens_cnt | bigint | 模型思考过程 token 数（生效时间 2025-04-19） |
| is_privacy_mode_request | int | 本次请求是否隐私模式：1-是，0-否，-1-未知 |
| is_privacy_mode_conversation | int | 会话中是否含隐私模式数据：1-是，0-否，-1-未知 |
| conversation_id | string | ⚠️ **注意：该字段实际含义是 session_id**（会话级标识）。下游表 `dwd_trae_chat_model_cost_di` 已通过 `conversation_id AS session_id` 修正语义 |
| latency | bigint | 模型完整回复的时延（纳秒） |
| first_token_latency | bigint | 首 token 响应延迟（纳秒） |

> 分区键: date (string, yyyyMMdd)

## request_metadata 字段说明

`request_metadata` 是一个 JSON 字符串，包含模型调用的丰富元信息。可通过 `get_json_object(request_metadata, '$.key')` 提取。主要字段：

| JSON 路径 | 类型 | 说明 |
|-----------|------|------|
| `$.id` | string | 请求 ID（如 chatcmpl-xxx） |
| `$.stream` | boolean | 是否流式请求 |
| `$.max_tokens` | int | 最大生成 token 数 |
| `$.temperature` | double | 采样温度 |
| `$.top_p` | double | Top-P 采样 |
| `$.top_k` | int | Top-K 采样 |
| `$.n` | int | 采样数量（通常为 null） |
| `$.frequency_penalty` | double | 频率惩罚（通常为 null） |
| `$.presence_penalty` | double | 存在惩罚（通常为 null） |
| `$.min_new_tokens` | int | 最小新生成 token 数（通常为 null） |
| `$.max_prompt_tokens` | int | 最大 prompt token 数 |
| `$.repetition_penalty` | double | 重复惩罚（通常为 null） |
| `$.usage.prompt_tokens` | int | 实际 prompt token 用量 |
| `$.usage.completion_tokens` | int | 实际 completion token 用量 |
| `$.usage.total_tokens` | int | 实际总 token 用量 |
| `$.usage.custom_prompt_tokens` | int | 自定义 prompt token 用量 |
| `$.usage.custom_completion_tokens` | int | 自定义 completion token 用量 |
| `$.usage.custom_total_tokens` | int | 自定义总 token 用量 |
| `$.usage.reasoning_tokens` | int | 推理 token 用量 |
| `$.latency` | bigint | 延迟（纳秒） |
| `$.first_token_latency` | bigint | 首 token 延迟（纳秒） |
| `$.error` | string | 错误信息（null 表示无错误） |
| `$.finish_reason` | string | 结束原因（如 stop、tool_calls） |
| `$.log_id` | string | 日志 ID |
| `$.function_id` | string | 函数 ID（通常为 null） |
| `$.ai_limit_queue_info` | string | AI 限流排队信息（通常为 null） |
| `$.context_variables` | string | 上下文变量（通常为 null，注意与物理字段 context_variable 区分） |
| `$.user_input_tokens` | int | 用户输入 token 数（通常为 null） |
| `$.intent_name` | string | 意图名称（通常为 null） |
| `$.programming_language` | string | 编程语言（通常为 null） |
| `$.model_usage` | string | 模型用途（如 chat_completion） |
| `$.trace_id` | string | Trace ID（用于链路追踪） |
| `$.span_id` | string | Span ID |
| `$.conversation_id` | string | 会话 ID |
| `$.req_model_name` | string | 请求的模型名称（可能含 __dev 等后缀） |
| `$.req_is_multi_modal` | boolean | 是否多模态请求 |
| `$.device_id` | string | 设备 ID。⚠️ **覆盖率极低**：仅桌面端（Default）上报较完整，Mobile / SoloWeb / SoloLite 等非桌面端几乎不上报（SoloWeb DAU 用 device_id 去重仅 1，用 user_id 则 7000+）。**不可用于 DAU 统计**，应使用 `user_id` |
| `$.user_entitlement` | string | 用户权限信息（通常为 null） |
| `$.ab_version` | array | A/B 实验版本列表 |
| `$.agent_type` | string | Agent 类型（如 builder_v3、chat_v3 等） |
| `$.agent_debug_mode` | int | Agent 调试模式 |
| `$.access_type` | string | 访问类型（如 Default） |
| `$.is_remote_req` | boolean | 是否远程请求 |
| `$.is_cloud_agent` | boolean | 是否云端 Agent |
| `$.is_auth_eval_request` | boolean | 是否认证评估请求 |
| `$.app_version_code` | int | 应用版本号 |
| `$.x_ide_version` | string | IDE 版本 |
| `$.x_ide_version_type` | string | IDE 版本类型（如 stable） |
| `$.client_ip` | string | 客户端 IP |
| `$.region` | string | 请求 region（如 CN） |
| `$.config_name` | string | 配置名称（模型配置标识） |
| `$.prompt_set` | string | Prompt 集合版本 |
| `$.fallback_models` | array | 降级备选模型列表 |
| `$.retried_times` | int | 重试次数 |
| `$.tool_calls` | array | 工具调用列表，含 function.name 和 arguments |
| `$.reason_content_length` | int | 推理内容长度 |
| `$.mode_type` | int | 模式类型 |
| `$.request_type` | string | 请求类型（如 dev） |
| `$.user_input` | string | 用户原始输入 |
| `$.chat_process_version` | string | 对话处理版本 |
| `$.is_privacy_mode` | boolean | 是否隐私模式 |
| `$.function_type` | string | 函数类型（通常为空字符串） |
| `$.from` | string | 来源标识 |
| `$.agent_run_id` | string | Agent 运行 ID |
| `$.parent_agent_run_ids` | array | 父 Agent 运行 ID 列表 |
| `$.end_point` | string | 模型端点（如 openai_qwen3-coder-next） |
| `$.prompt_tokens` | int | prompt token 数（顶层字段，与 usage 内同名字段冗余） |

> **虚拟列提示**：Hive 平台为该表配置了多个基于 `request_metadata` 的虚拟列（原理是使用 `get_json_object` 提取），常用的有：`model_usage`、`log_id`、`ab_version`、`prompt_set`、`agent_type`、`config_name`、`req_model_name`、`req_is_multi_modal`、`x_ide_version`、`x_ide_version_type`、`fallback_models`、`span_id`、`trace_id`、`finish_reason`、`max_prompt_tokens`、`is_stream`、`is_cloud_agent`、`tool_call_function_names`、`device_id`、`request_type`、`access_type`。这些虚拟列可以直接使用，当作普通字段，比如直接 `SELECT device_id FROM ...` 而不需要 `SELECT get_json_object(request_metadata, '$.device_id')`。

## TQS 查询权限注意事项

- `request_metadata` 列是**敏感列**，TQS 查询时会报 `Access denied for column` 错误。如需使用 `get_json_object(request_metadata, '$.model_usage')` 等过滤条件，需要在 Coral 数据地图中额外申请该列的字段级权限
- Gallery 数据源 SQL 在 Dorado 调度执行时使用服务账号，通常有完整权限；但通过 TQS 做 ad-hoc 查询验证时，可能因个人账号缺少敏感列权限而失败
- **替代方案**：如果无法访问 `request_metadata`，可改用 `dwd_trae_chat_model_cost_di` 表的 token 字段做近似验证（status 口径已对齐，仅 `request_type` 和 `model_usage` 过滤有差异，详见该表文档）

## DAU 统计口径建议

> ⚠️ 本表做 DAU 统计时，**必须使用 `user_id`（`COUNT(DISTINCT user_id)`）**，不可使用 `device_id`。

`device_id` 来自 `request_metadata` 的 `$.device_id` 字段（虚拟列），**仅桌面端（access_type = 'Default'）上报较完整**。非桌面端覆盖率极低：

| access_type | DAU (user_id) | DAU (device_id) | device_id 覆盖率 |
|-------------|--------------|-----------------|-----------------|
| Default | 176,868 | 173,532 | ~98% |
| Mobile | 41,189 | 2,996 | ~7% |
| SoloLite | 33,345 | 28,453 | ~85% |
| SoloWeb | 7,119 | 1 | ~0% |

> 数据来源：2026-05-10 实际查询结果。

**原因**：Mobile 和 SoloWeb 等端的请求在服务端未携带 device_id（或为空/固定值），导致 `COUNT(DISTINCT device_id)` 严重低估。

**建议**：
- 本表统一使用 `user_id` 作为 DAU 去重口径
- 若需使用 `device_id`，仅在 `access_type = 'Default'` 条件下使用
- 跨 access_type 的 DAU 对比分析必须使用 `user_id`
