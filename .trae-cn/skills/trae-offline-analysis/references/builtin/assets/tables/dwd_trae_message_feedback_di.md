# dwd_trae_message_feedback_di

消息正负反馈表（message_id粒度，主键message_id）。记录用户对AI消息的点赞/点踩反馈，上游来源为cloudide.dwd_behavior_trae_ide_public_user_log_di和flow_aipaas.dwd_trae_message_bench_tags。适用场景: 消息满意度分析、正负反馈率计算、按session/app维度的用户反馈统计。

- cn: `flow_aipaas.dwd_trae_message_feedback_di`
- i18n: `ai_application_coding.dwd_trae_message_feedback_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 不限
- Dorado 任务 (cn): [dwd_trae_message_feedback_di](https://data.bytedance.net/dorado/development/node/124651725?project=cn_11253) (projectId: 11253, taskId: 124651725)
- Dorado 任务 (sg): [dwd_trae_message_feedback_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/305974277?project=sg_300004442) (projectId: 300004442, taskId: 305974277)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdwd_trae_message_feedback_di%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fai_application_coding%2Fdwd_trae_message_feedback_di%406#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| message_id | string | 消息唯一标识符 |
| session_id | string | 会话唯一标识符，用于跟踪用户的连续操作序列 |
| app_id | string | 应用唯一标识符，用于区分请求来源的具体应用 |
| is_positive_feedback | boolean | 是否为正反馈（点赞） |
| is_negative_feedback | boolean | 是否为负反馈（点踩） |

> 分区键: date (string)
