# dwd_trae_ai_cue_event_di

代码补全事件明细表（user_id+事件粒度）。记录代码补全的触发、展示、接受、取消等事件明细，包含编程语言、补全结果类型、触发方式、模型名称等维度。适用场景: 代码补全触发率/接受率分析、按语言/模型/触发方式的补全效果对比。

- cn: `flow_aipaas.dwd_trae_ai_cue_event_di`
- i18n: `cloudide.dwd_trae_ai_cue_event_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- Dorado 任务 (cn): [dwd_trae_ai_cue_event_di](https://data.bytedance.net/dorado/development/node/120612186?project=cn_11253) (projectId: 11253, taskId: 120612186)
- Dorado 任务 (sg): [dwd_trae_ai_cue_event_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/304882045?project=sg_300004344) (projectId: 300004344, taskId: 304882045)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable:///flow_aipaas/dwd_trae_ai_cue_event_di@0&subTab=schema&tab=table_info#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_ai_cue_event_di%406&subTab=schema&tab=table_info#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| user_id | bigint | 用户ID |
| user_unique_id | string | 设备ID |
| programming_language | string | 编程语言 |
| result_type | string | 补全结果类型 |
| code_lines | string | 代码行数 |
| trigger_type | string | 触发类型 |
| is_comp_fusion | string | 是否融合补全 |
| model_name | string | 模型名称 |
| event_name | string | 事件名称（如shown/accept/canceled） |
| is_new | int | 是否新用户 |

> 分区键: date (string)
