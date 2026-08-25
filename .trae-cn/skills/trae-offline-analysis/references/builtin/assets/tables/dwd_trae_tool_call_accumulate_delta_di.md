# dwd_trae_tool_call_accumulate_delta_di

Trae工具调用增量聚合表（session_id+message_id+tool_type粒度）。核心字段包括用户、会话、工具类型等维度，工具调用指标涵盖前端展现、模型请求、实际运行、成功、失败、跳过全链路。支持vids(AB实验组IDs数组)、is_auto_mode、is_canceled等维度筛选。适用场景: 工具调用成功率分析、各tool_type使用频次统计、工具调用漏斗分析。

- cn: `flow_aipaas.dwd_trae_tool_call_accumulate_delta_di`
- i18n: `cloudide.dwd_trae_tool_call_accumulate_delta_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 32天
- Dorado 任务 (cn): [dwd_trae_tool_call_accumulate_delta_di](https://data.bytedance.net/dorado/development/node/121192837?project=cn_11253) (projectId: 11253, taskId: 121192837)
- Dorado 任务 (sg): [dwd_trae_tool_call_accumulate_delta_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/304979763?project=sg_300004344) (projectId: 300004344, taskId: 304979763)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable:///flow_aipaas/dwd_trae_tool_call_accumulate_delta_di@0&subTab=schema&tab=table_info#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_tool_call_accumulate_delta_di%406&subTab=schema&tab=table_info#group=default
- 上游表: `cloudide.dwd_behavior_trae_ide_public_user_log_di`（埋点行为日志，tool_call 相关事件 + message_cancel 判断 + message_model 获取）、`cloudide.dwm_behavior_trae_public_user_log_statistic`（新用户标识 is_new）、`origin_log.dwd_abtest_vid_log_di`（AB实验组 vids）
- 一级下游表: `dwd_trae_ai_behavior_info_delta_di`（vid+session_id+message_id 粒度行为聚合表，tool_call 指标来源于本表）、`dwd_trae_ai_behavior_event_di`（uid+session_id+message_id 粒度行为事件表，不含 vid）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| user_id | bigint | 用户ID |
| user_unique_id | string | 设备ID |
| user_is_login | int | 用户是否登录 |
| is_new | int | 是否为新用户，1表示是，0或null表示否 |
| vids | array<string> | AB实验组ID列表 |
| session_id | string | 会话ID |
| message_id | string | 用户输入的消息ID |
| tool_type | string | 工具类型 |
| chat_type | string | 聊天类型（例如单人聊天、群组聊天等） |
| message_model | string | 前端模型 |
| programming_language | string | 编程语言（例如Python、Java等） |
| tool_call_show_cnt | int | 工具调用前端展现次数 |
| tool_call_request_cnt | int | 工具调用请求次数，表示模型回复需要调用工具的次数 |
| tool_call_run_cnt | int | 工具调用运行的次数，表示服务端实际发起调用的次数 |
| tool_call_success_cnt | int | 工具调用成功次数 |
| tool_call_failed_cnt | int | 工具调用失败次数 |
| tool_call_skip_cnt | int | 工具调用跳过次数 |
| is_auto_mode | int | 是否为auto模式，1表示是，0或null表示否 |
| is_canceled | int | 消息是否被用户手动取消，1表示是，0或null表示否 |

> 分区键: date (string)
