# prompt_completion_bd_hourly

原始 AI 对话消息的模型调用明细表（内场/字节内部），一条消息的每次模型调用（意图识别/context选择/chat 等）都有一条记录。按小时分区。与 `prompt_completion_hourly`（外场版本）schema 完全一致，区别在于数据范围：本表仅包含字节内部用户的模型调用数据。**内场场景可直接使用本表**（目前无对应的按天聚合表）。

- cn: `codeverse_codegen_cn.prompt_completion_bd_hourly`
- i18n: 待确认（sg 环境库名未知）
- 分区字段: date（日期）+ hour（小时），双分区键
- TTL: 365天
- Dorado 任务 (cn): taskId `119375218`
- 关联表: `codeverse_codegen_cn.prompt_completion_hourly`（外场版本，schema 完全一致）、`cloudide.dwd_resource_prompt_completion_di`（外场聚合表）
- 设计背景: 内场版本的模型调用原始数据，与外场 `prompt_completion_hourly` 结构一致但数据范围为字节内部用户。目前没有对应的按天聚合表（DWD 层），内场分析直接使用本表

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| app_id | string | 应用 ID，标识请求来源应用 |
| username | string | 用户名（注意：DWD 聚合表中对应字段为 `user_id`） |
| model_name | string | 调用的 AI 模型名称 |
| status | string | 请求状态：success / fail |
| session_id | string | 会话 ID，关联一次请求的与模型多次交互（意图识别/context选择/chat） |
| prompt | string | 向模型输入的 prompt 内容 |
| type | string | 对话类型：intent_detect（意图识别）/ context_selection（context 选择）/ chat（对话） |
| content_raw | string | 模型返回的原始回复内容 |
| content_processed | string | 处理后的模型回复内容 |
| prompt_template_id | string | prompt 模板 ID |
| request_metadata | string | 模型调用元信息（JSON），含 token 用量、延迟、finish_reason、agent_type、trace_id 等 |
| created_at | string | 创建时间 |
| updated_at | string | 上一次更新时间 |
| deleted_at | string | 删除时间 |
| context_variable | string | 调用参数信息 |

> 分区键: date (string, 分区日期) + hour (string, 分区时间)

## token 消耗解析

本表没有独立的 token 消耗字段（如 `total_tokens_cnt`），需通过 `request_metadata` JSON 字段解析：

```sql
get_json_object(request_metadata, '$.usage.prompt_tokens') -- prompt token 用量
get_json_object(request_metadata, '$.usage.completion_tokens') -- completion token 用量
get_json_object(request_metadata, '$.usage.total_tokens') -- 总 token 用量
get_json_object(request_metadata, '$.usage.reasoning_tokens') -- 推理 token 用量
get_json_object(request_metadata, '$.model_usage') -- 模型用途（如 chat_completion）
```

> **`request_metadata` JSON 内容与 `dwd_resource_prompt_completion_di` 的一致性**：本表与 `prompt_completion_hourly` 的 schema 完全一致。已通过数据对比验证，`dwd_resource_prompt_completion_di` 的 `request_metadata` 字段是从 `prompt_completion_hourly` **直接透传**的，JSON 结构和内容完全一致。本表（内场）的 `request_metadata` 结构与外场版本相同，可使用相同的 JSON 路径提取字段。`dwd_resource_prompt_completion_di` 文档中的 "request_metadata 字段说明" 部分有完整的 JSON 路径参考。
