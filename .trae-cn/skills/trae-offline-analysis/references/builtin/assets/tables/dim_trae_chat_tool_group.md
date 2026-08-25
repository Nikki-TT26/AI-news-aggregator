# dim_trae_chat_tool_group

工具类型聚类维度表（tool_type粒度）。用于将细粒度的tool_type（如LS、Grep、Read等）映射到粗粒度的tool_group分类（如Search、FileOps等），常与dwd_trae_tool_call_accumulate_delta_di关联使用。适用场景: 工具调用分类统计、按工具大类聚合分析。

- cn: `flow_aipaas.dim_trae_chat_tool_group`
- i18n: `ai_application_coding.dim_trae_chat_tool_group`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 不限
- Dorado 任务 (cn): [trae_libra_dimension_tool_group](https://data.bytedance.net/dorado/development/node/124475468?project=cn_11253) (projectId: 11253, taskId: 124475468)
- Dorado 任务 (sg): [dim_trae_chat_tool_group](https://dataleap-sg.tiktok-row.net/dorado/development/node/305975797?project=sg_300004442) (projectId: 300004442, taskId: 305975797)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdim_trae_chat_tool_group%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fai_application_coding%2Fdim_trae_chat_tool_group%406#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| tool_type | string | 具体工具类型名称，如LS、Grep、Read等 |
| tool_group | string | 工具分类，如Search、FileOps等 |

> 分区键: date (string)
