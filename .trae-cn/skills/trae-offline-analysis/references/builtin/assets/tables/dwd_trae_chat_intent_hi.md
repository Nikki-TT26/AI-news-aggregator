# dwd_trae_chat_intent_hi

AI 对话意图打标表（每小时增量），从 `dwd_trae_chat_input_hi` 中提取用户消息，通过 LLM（Qwen3-8B-intent）进行意图分类，输出意图识别结果。按 user_message_id 唯一标识每条消息。字段与 `dwd_trae_chat_intent_di` 完全一致，区别在于分区粒度为小时级。

- cn: `flow_aipaas.dwd_trae_chat_intent_hi`
- i18n: `ai_application_coding.dwd_trae_chat_intent_hi`
- 分区字段: date（yyyyMMdd）+ hour（HH）
- TTL: 待确认
- Dorado 任务 (cn): [dwd_trae_chat_intent_hi](https://data.bytedance.net/dorado/development/node/124101683?project=cn_11253) (projectId: 11253, taskId: 124101683, PySpark 任务，调用 Qwen3-8B-intent 模型)
- Dorado 任务 (sg): [dwd_trae_chat_intent_hi](https://dataleap-sg.tiktok-row.net/dorado/development/node/305593243?project=sg_300004442) (projectId: 300004442, taskId: 305593243, PySpark 任务)
- GUID (sg): `57999937-af2b-4b5c-bfd7-50f1cec6c2cd`
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=alisg&qualifiedName=HiveTable%3A%2F%2F%2Fai_application_coding%2Fdwd_trae_chat_intent_hi%406#group=alisg
- 上游表: `dwd_trae_chat_input_hi`（cn: `flow_aipaas`，sg: `ai_application_coding`）
- 一级下游表: `dwd_trae_chat_intent_di`（cn: `flow_aipaas`，sg: `ai_application_coding`）
- 设计背景: 小时级意图打标结果，由 PySpark 任务从 `dwd_trae_chat_input_hi` 读取全量数据（**无 type 过滤**）并调用 LLM 进行意图分类。下游 `dwd_trae_chat_intent_di` 按天聚合本表数据（简单 SELECT，无额外过滤）

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_message_id | string | 用户消息的唯一标识符 |
| app_id | string | App ID |
| chat_session_id | string | 聊天会话的唯一标识（= conversation_id） |
| model_pred | string | 模型对用户意图等的预测内容 |
| intent | string | 用户的具体意图类别 |
| user_lang | string | 用户使用的语言类型 |
| code_lang | string | 涉及的代码编程语言 |
| code_framework | string | 使用的代码框架类型 |
| user_source | string | 内外场（internal/public） |

> 分区键: date (string, yyyyMMdd) + hour (string, HH)
