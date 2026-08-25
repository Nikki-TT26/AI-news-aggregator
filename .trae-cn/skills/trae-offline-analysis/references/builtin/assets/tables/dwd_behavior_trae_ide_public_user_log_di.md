# dwd_behavior_trae_ide_public_user_log_di

TRAE IDE 用户行为日志明细表（DWD 层）。前端埋点的行为日志，是多张 DWD 行为聚合表的核心上游表。`params` 字段为 MAP 类型，包含 `agent_type`、`chat_type`、`message_model` 等前端埋点参数。适用场景：追溯 DWD 行为表中字段的原始值、查看前端埋点层面的 agent_type 完整枚举。

- cn: `cloudide.dwd_behavior_trae_ide_public_user_log_di`
- i18n: `cloudide.dwd_behavior_trae_ide_public_user_log_di`（cn/sg 同库名）
- 分区字段: date（yyyyMMdd）
- TTL: 750天
- 负责人: qinjie.1122（产品研发和工程架构-Dev Infra-APM-前端）
- 一级下游表: `dwd_trae_ai_behavior_event_di`、`dwd_trae_ai_behavior_info_delta_di`、`dwd_trae_ai_behavior_info_message_delta_di`、`dwd_trae_block_detail_di`
- 设计背景: 基于 `cloudide.dwd_behavior_public_user_log_di` 筛选 trae_cn 应用且平台为 electron 的 SSO 用户行为日志。另有 `cloudide_dw` 库下同名表（负责人 chengzhe.hachiko）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| user_id | bigint | 用户 ID |
| event_name | string | 事件名称 |
| params | map<string,string> | 埋点参数（含 agent_type、chat_type、message_model 等） |
| session_id | string | 会话 ID |
| message_id | string | 消息 ID |
| log_id | string | 日志 ID |
| behavior_date | string | 行为日期 |
| behavior_time | string | 行为时间 |
| ide_version | string | IDE 版本 |

> 分区键: date (string)
> 注意：字段列表为部分核心字段，完整 schema 请通过 `bytedcli hive detail cloudide dwd_behavior_trae_ide_public_user_log_di` 查看
