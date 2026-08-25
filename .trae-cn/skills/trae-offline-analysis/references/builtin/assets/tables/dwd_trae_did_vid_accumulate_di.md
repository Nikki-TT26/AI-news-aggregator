# dwd_trae_did_vid_accumulate_di

用户实验组留存维度每日增量表（did+vid粒度）。上游为dwd_trae_ai_behavior_accumulate_delta_di。核心字段: vid(实验组ID)、did(设备ID)，包含多档留存标签（1d/3d/7d/14d/30d_retention），is_first_hit(是否首次进组)、first_hit_date(首次进组时间)、is_new(是否新用户)，以及behavior_type、chat_type、message_model等行为维度。适用场景: Libra实验留存分析、新老用户分群、实验进组分析。

- cn: `flow_aipaas.dwd_trae_did_vid_accumulate_di`
- i18n: `cloudide.dwd_trae_did_vid_accumulate_di`（sg 比 cn 多 `agent_type` 字段；`vid` 类型不同：cn=int, sg=string）
- 分区字段: date（yyyyMMdd）
- TTL: 32天
- Dorado 任务 (cn): [dwd_trae_did_vid_accumulate_df](https://data.bytedance.net/dorado/development/node/120568720?project=cn_11253) (projectId: 11253, taskId: 120568720)（注意：任务名为 `_df` 但实际输出到 `_di` 表）
- Dorado 任务 (sg): [dwd_trae_did_vid_accumulate_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/304712692?project=sg_300004344) (projectId: 300004344, taskId: 304712692)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable:///flow_aipaas/dwd_trae_did_vid_accumulate_di@0&subTab=schema&tab=table_info#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_did_vid_accumulate_di%406&subTab=schema&tab=table_info#group=default
- 上游表: `dwd_trae_ai_behavior_info_delta_di`（当日增量行为数据）+ 自身前一天分区（历史累计留存数据，自依赖）+ `origin_log.dwd_abtest_vid_log_di`（活跃 vid 过滤）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| vid | int | 实验组ID |
| did | string | 设备ID |
| 1d_retention | int | 1日留存标识 |
| 3d_retention | int | 3日留存标识 |
| 7d_retention | int | 7日留存标识 |
| 14d_retention | int | 14日留存标识 |
| 30d_retention | int | 30日留存标识 |
| is_first_hit | int | 是否首次进组 |
| first_hit_date | string | 首次进组时间 |
| is_new | int | 是否新用户 |
| behavior_type | string | 行为类型 |
| chat_type | string | 交互类型 |
| message_model | string | 消息模型 |

> 分区键: date (string)
