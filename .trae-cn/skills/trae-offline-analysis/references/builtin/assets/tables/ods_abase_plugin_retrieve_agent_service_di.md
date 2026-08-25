# ods_abase_plugin_retrieve_agent_service_di

Abase同步表，从Abase KV存储同步agent_service数据到Hive（abase_key粒度，主键abase_key）。原始字段包括abase_key（可通过substring_index提取message_id）、abase_value（JSON格式）、dimer_meta（系统元数据含expire_ms）。虚拟列（从abase_value解析）包括message_id、code_lang、intent、user_lang、code_framework。当前用于获取在线意图识别数据，避免离线意图重复计算。

- cn: `flow_aipaas.ods_abase_plugin_retrieve_agent_service_di`
- i18n: 无（sg 不存在此表）
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- Dorado 任务 (cn): 无（ODS 同步表）
- Dorado 任务 (sg): 无（sg 不存在此表）
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fods_abase_plugin_retrieve_agent_service_di%400#group=default
- Hive URL (sg): 无（sg 不存在此表）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| abase_key | string | Abase存储中key字段 |
| abase_value | string | Abase存储中value字段 |
| dimer_meta | struct<expire_ms:bigint> | 系统字段，abase2hive任务元数据 |

> 分区键: date (string)
