# trae_cn_toolcalls

Trae CN 的 Tool Call 工具调用解析表，记录每一轮工具调用的详细结果，包括调用的工具名称、参数、模型信息、token 消耗、延迟等。按 conversation_id + message_id + call_logid 关联每次工具调用。适用场景：分析 Tool Call 执行情况、工具调用分布统计、工具调用链路分析。

- cn: `code_evaluation.trae_cn_toolcalls`
- i18n: 待确认
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- Dorado 任务 (cn): taskId `123156600`
- GUID: `6bdf61f0-4f4f-4c9a-8cfa-a75a0f9da119`
- 设计背景: 包含每一轮工具调用解析的结果，从模型调用数据中提取 tool call 信息并结构化存储

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| conversation_id | string | 会话唯一标识符 |
| message_id | string | 消息唯一标识符 |
| call_logid | string | 调用的日志标识（关联模型调用） |
| result_logid | string | 结果的日志标识 |
| call_time | bigint | 调用时间 |
| first_user_msg | string | 首条用户消息内容 |
| last_user_msg | string | 最近一条用户消息内容 |
| model_name | string | 实际调用的模型名称 |
| req_model_name | string | 请求的模型名称 |
| model_usage | string | 模型用途 |
| agent_type | string | Agent 类型 |
| total_tokens_cnt | bigint | 总 token 数量 |
| prompt_tokens_cnt | bigint | prompt token 数量 |
| completion_tokens_cnt | bigint | completion token 数量 |
| reasoning_tokens_cnt | bigint | 推理 token 数量 |
| cache_creation_tokens_cnt | bigint | 缓存创建 token 数量 |
| cache_read_tokens_cnt | bigint | 缓存读取 token 数量 |
| max_prompt_tokens | bigint | 最大 prompt token 数 |
| latency_ns | bigint | 延迟时间（纳秒） |
| first_token_latency_ns | bigint | 首 token 延迟时间（纳秒） |
| x_ide_version | string | IDE 版本号 |
| ab_version | string | A/B 测试版本号 |
| config_name | string | 模型配置名称 |
| prompt_set | string | Prompt 集合版本 |
| req_is_multi_modal | int | 是否多模态请求（1是/0否） |
| output_msg_content | string | 输出消息内容 |
| output_reasoning_content | string | 输出推理内容 |
| finish_reason | string | 结束原因 |
| current_tool_call_name | string | 当前工具调用名称 |
| current_tool_call_args | string | 当前工具调用参数 |
| result_role | string | 结果角色身份 |
| result_content | string | 结果内容 |
| result_tool_call_id | string | 结果工具调用 ID |
| link_status | string | 链接状态 |

> 分区键: date (string, yyyyMMdd)
