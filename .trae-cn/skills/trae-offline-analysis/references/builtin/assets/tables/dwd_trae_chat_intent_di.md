# dwd_trae_chat_intent_di

AI 对话意图打标表（每日增量），记录每条用户消息的意图识别结果，包含模型预测内容、用户意图分类、用户语言、代码语言和框架等信息。按 user_message_id 唯一标识每条消息。适用场景：用户意图分析、意图分布统计、多语言/多框架使用情况分析。

- cn: `flow_aipaas.dwd_trae_chat_intent_di`
- i18n: `ai_application_coding.dwd_trae_chat_intent_di`
- 分区字段: date（yyyyMMdd）
- TTL: 待确认
- Dorado 任务 (cn): [dwd_trae_chat_intent_di_sql](https://data.bytedance.net/dorado/development/node/124156217?project=cn_11253) (projectId: 11253, taskId: 124156217)
- Dorado 任务 (sg): [dwd_trae_chat_intent_di_sql](https://dataleap-sg.tiktok-row.net/dorado/development/node/305595919?project=sg_300004442) (projectId: 300004442, taskId: 305595919)
- GUID (cn): `bb27dd50-2b7d-4f42-8af4-b911af6bf344`
- GUID (sg): `2ca3db02-bf1f-47e5-b72e-f1b165c8fbf1`
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=alisg&qualifiedName=HiveTable%3A%2F%2F%2Fai_application_coding%2Fdwd_trae_chat_intent_di%406#group=alisg
- 上游表: `dwd_trae_chat_intent_hi`（cn 和 sg 均从 intent_hi 按天聚合，简单 SELECT 无额外过滤）
- 关联表: `dwd_trae_chat_input_hi`（通过 user_message_id + chat_session_id 关联）
- 设计背景: 专门的意图打标表，从对话数据中提取用户意图分类信息。注意 `chat_session_id` 对应的是 `conversation_id`。cn 和 sg 均由 `dwd_trae_chat_intent_hi` 按天聚合（简单 SELECT，无额外过滤），**不做任何 type 过滤**，完整保留上游所有类型的消息

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_message_id | string | 用户消息唯一标识符 |
| app_id | string | App ID |
| chat_session_id | string | 聊天会话标识（= conversation_id） |
| model_pred | string | 模型对用户意图等的预测内容 |
| intent | string | 用户的具体意图类别 |
| user_lang | string | 用户使用的语言类型 |
| code_lang | string | 涉及的代码编程语言 |
| code_framework | string | 使用的代码框架类型 |
| user_source | string | 内外场（internal/public） |

> 分区键: date (string, yyyyMMdd)
