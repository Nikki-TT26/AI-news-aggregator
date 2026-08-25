# dwd_trae_ai_behavior_info_message_delta_di

Message粒度Trae AI行为每日增量表（message_id唯一，主键message_id）。与dwd_trae_ai_behavior_info_delta_di的区别: 本表每个message_id只对应一条记录，不按vid拆分。按session_id、message_id、uid、did聚合，包含代码建议、代码块展示、运行脚本、工具调用、代码补全等行为指标，以及auto_mode、点赞点踩回退、重试次数、diff行数统计、agent_type等字段。适用场景: 以单条消息为分析单元的指标统计，如单message维度的代码采纳率、工具调用率。

- cn: `flow_aipaas.dwd_trae_ai_behavior_info_message_delta_di`
- i18n: `cloudide.dwd_trae_ai_behavior_info_message_delta_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- Dorado 任务 (cn): [dwd_trae_ai_behavior_info_message_delta_di](https://data.bytedance.net/dorado/development/node/122570260?project=cn_11253) (projectId: 11253, taskId: 122570260)
- Dorado 任务 (sg): [dwd_trae_ai_behavior_info_message_delta_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/305001416?project=sg_300004344) (projectId: 300004344, taskId: 305001416)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdwd_trae_ai_behavior_info_message_delta_di%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwd_trae_ai_behavior_info_message_delta_di%406#group=default

| 字段名 | 类型 | 描述 |
|--------|------|------|
| session_id | string | 会话标识符 |
| message_id | string | 消息标识符 |
| uid | bigint | 用户ID |
| did | string | 设备ID |
| is_new | int | 是否是新用户 |
| behavior_type | string | 行为类型 |
| chat_type | string | 交互类型 |
| message_model | string | 问答模型 |
| applicable_cnt | int | 代码建议可应用数 |
| block_show_cnt | int | 代码块、命令块展示次数 |
| code_block_show_cnt | int | 代码块展示次数 |
| applied_cnt | int | 代码建议已应用数 |
| apply_click_cnt | int | 主动点击apply次数 |
| block_rejected_cnt | string | 代码块拒绝数 |
| todo_list_rejected_cnt | string | todo_list代码块拒绝数 |
| rejected_cnt | int | 代码建议拒绝数 |
| block_accepted_cnt | int | 代码块接受数 |
| todo_list_accepted_cnt | int | todo_list代码块接受数 |
| accepted_cnt | int | 代码建议已接受数 |
| accept_diff_insert_line_cnt | int | 已接受插入代码行数 |
| accept_diff_delete_line_cnt | int | 已接受删除代码行数 |
| accept_diff_line_cnt | int | 已接受代码行数（插入+删除） |
| copied_cnt | int | 代码建议复制数 |
| insert_cnt | int | 代码建议插入数 |
| run_script_show_cnt | int | 运行脚本展示次数 |
| run_script_click_cnt | int | 运行脚本点击次数 |
| run_script_success_cnt | int | 运行脚本成功次数 |
| run_script_failed_cnt | int | 运行脚本失败次数 |
| tool_call_show_cnt | int | 工具调用展现次数 |
| tool_call_request_cnt | int | 工具调用请求的次数 |
| tool_call_run_cnt | int | 工具调用运行次数 |
| tool_call_success_cnt | int | 工具调用成功次数 |
| code_gen_shown_cnt | int | 代码补全展示数 |
| code_gen_accept_cnt | int | 代码补全接受数 |
| code_gen_canceled_cnt | int | 代码补全取消数 |
| programming_language | string | 语言类型 |
| suggest_code_block_cnt | int | 代码建议代码块数 |
| is_auto_mode | int | 是否是auto模式 |
| is_canceled | int | 取消标识 |
| is_like | int | 是否点赞 |
| is_dislike | int | 是否点踩 |
| is_revert | int | 是否回退 |
| retry_cnt | int | 重试次数 |
| model_call_cnt | int | 模型调用轮数 |
| applied_diff_insert_line_cnt | int | 已应用插入代码行数 |
| applied_diff_delete_line_cnt | int | 已应用删除代码行数 |
| applied_diff_line_cnt | int | 已应用代码行数（插入+删除） |
| reject_diff_insert_line_cnt | int | 已拒绝插入代码行数 |
| reject_diff_delete_line_cnt | int | 已拒绝删除代码行数 |
| reject_diff_line_cnt | int | 已拒绝代码行数（插入+删除） |
| agent_type | string | Agent类型标识 |

> 分区键: date (string)
