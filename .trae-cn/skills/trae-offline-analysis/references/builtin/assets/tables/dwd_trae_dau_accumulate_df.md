# dwd_trae_dau_accumulate_df

Trae活跃用户多日累计全量表（user_id+user_unique_id+vid粒度，主键user_id+user_unique_id+vid）。字段精简，仅包含用户ID、设备ID、实验组ID和新用户标识。适用场景: DAU统计、按实验组统计活跃用户数、新老用户DAU对比。

- cn: `flow_aipaas.dwd_trae_dau_accumulate_df`
- i18n: `cloudide.dwd_trae_dau_accumulate_df`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 32天
- Dorado 任务 (cn): [dwd_trae_dau_accumulate_df](https://data.bytedance.net/dorado/development/node/121412393?project=cn_11253) (projectId: 11253, taskId: 121412393)
- Dorado 任务 (sg): [dwd_trae_dau_accumulate_df](https://dataleap-sg.tiktok-row.net/dorado/development/node/304980124?project=sg_300004344) (projectId: 300004344, taskId: 304980124)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable:///flow_aipaas/dwd_trae_dau_accumulate_df@0&subTab=schema&tab=table_info#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_dau_accumulate_df%406&subTab=schema&tab=table_info#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| user_id | bigint | 用户ID |
| user_unique_id | string | 设备ID |
| vid | bigint | Libra实验组ID |
| is_new | int | 是否是新用户，1表示是 |

> 分区键: date (string)
