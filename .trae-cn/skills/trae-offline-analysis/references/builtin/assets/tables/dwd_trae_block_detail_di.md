# dwd_trae_block_detail_di

Trae代码块明细表（block_id粒度）。相对于dwd_trae_code_suggest_detail_di，主要增加了shell_block类型。核心维度包括聊天类型、用户、模型、代码块、消息、会话、编程语言等。用户活跃标签涵盖新用户和多档历史活跃标识。代码块行为指标覆盖展示、应用、接受、拒绝、复制、插入及diff行数统计。适用场景: 单代码块维度的采纳率/拒绝率分析、block_type对比分析。

- cn: `flow_aipaas.dwd_trae_block_detail_di`
- i18n: `cloudide.dwd_trae_block_detail_di`（sg 比 cn 多 `agent_type` 字段）
- 分区字段: date（yyyyMMdd）
- TTL: 32天
- Dorado 任务 (cn): [dwd_trae_block_detail_di](https://data.bytedance.net/dorado/development/node/121332356?project=cn_11253) (projectId: 11253, taskId: 121332356)
- Dorado 任务 (sg): [dwd_trae_block_detail_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/304980040?project=sg_300004344) (projectId: 300004344, taskId: 304980040)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable:///flow_aipaas/dwd_trae_block_detail_di@0&subTab=schema&tab=table_info#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_block_detail_di%406&subTab=schema&tab=table_info#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| chat_type | string | 聊天类型 |
| user_id | bigint | 用户ID |
| user_unique_id | string | 用户唯一标识 |
| user_is_login | int | 用户是否登录 |
| is_new | int | 是否为新用户 |
| is_active_1d_ago | int | 一天前是否活跃 |
| is_active_7d_ago | int | 七天前是否活跃 |
| is_active_30d_ago | int | 三十天前是否活跃 |
| message_model | string | 模型 |
| block_id | string | 代码块标识 |
| block_type | string | 代码块类型 |
| message_id | string | 消息标识 |
| session_id | string | 会话标识 |
| is_applicable | int | 是否可应用 |
| block_show | int | 代码块或命令块展示次数 |
| code_block_show | int | 代码块展示次数 |
| is_applied | int | 是否已应用 |
| is_apply_click | int | 是否主动点击apply |
| is_block_accepted | int | 是否以代码块的形式接受 |
| is_todo_list_accepted | int | 是否以todo_list的形式接受 |
| is_accepted | int | 是否已接受 |
| accept_diff_insert_line_count | int | 已接受插入代码行数 |
| accept_diff_delete_line_count | int | 已接受删除代码行数 |
| accept_diff_line_count | int | 已接受代码行数（插入+删除） |
| is_block_rejected | int | 是否以代码块的形式拒绝 |
| is_todo_list_rejected | int | 是否以todo_list的形式拒绝 |
| is_rejected | int | 是否已拒绝 |
| is_copied | int | 是否已复制 |
| is_insert | int | 是否为插入 |
| run_script_show | int | 运行脚本展示次数 |
| run_script_click | int | 运行脚本点击次数 |
| run_script_success | int | 运行脚本成功次数 |
| run_script_failed | int | 运行脚本失败次数 |
| diff_insert_line_count | int | diff插入代码行数 |
| diff_delete_line_count | int | diff删除代码行数 |
| diff_line_count | int | diff代码总行数（插入+删除） |
| programming_language | string | 编程语言 |
| ide_duration | bigint | IDE使用时长（毫秒） |
| vids | array<string> | AB实验组ID列表 |
| ai_chat_duration | bigint | AI对话时长（毫秒） |
| ai_chat_end_type | string | AI对话结束类型 |
| message_programming_language | string | 消息中的编程语言 |
| block_programming_language | string | 代码块中的编程语言 |
| is_canceled | int | 是否已取消 |
| is_auto_mode | int | 是否auto模式 |
| model_name | string | 模型名称 |
| reject_diff_insert_line_count | int | 已拒绝插入代码行数 |
| reject_diff_delete_line_count | int | 已拒绝删除代码行数 |
| reject_diff_line_count | int | 已拒绝代码行数（插入+删除） |

> 分区键: date (string)
