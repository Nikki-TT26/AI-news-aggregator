# dwd_trae_chat_input_hi

AI对话用户消息意图表（每小时增量），记录用户在 AI 对话中发送的每条消息的详细上下文信息，包括用户输入内容、当前文件/工作区上下文、提及内容、MCP 服务器列表、Prompt 工程信息（任务类型、模型名称、文本输出、是否最终轮）以及意图打标结果等。按 user_message_id 唯一标识每条用户消息。

- cn: `flow_aipaas.dwd_trae_chat_input_hi`
- i18n: `ai_application_coding.dwd_trae_chat_input_hi`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）+ hour（HH）
- TTL: cn 365天，sg 60天
- Dorado 任务 (cn): [dwd_trae_chat_input_hi](https://data.bytedance.net/dorado/development/node/122258034?project=cn_11253) (projectId: 11253, taskId: 122258034)
- Dorado 任务 (sg): [dwd_trae_chat_input_hi](https://dataleap-sg.tiktok-row.net/dorado/development/node/304864760?project=sg_300004442) (projectId: 300004442, taskId: 304864760)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdwd_trae_chat_input_hi%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fai_application_coding%2Fdwd_trae_chat_input_hi%406#group=default
- 上游表: `codeverse_codegen_cn.prompt_completion_hourly`（外场）、`codeverse_codegen_cn.prompt_completion_bd_hourly`（内场）、`cloudide_bizide.dwd_trae_ai_agent_parsed_message_hi`（v2 路径）、`flow_aipaas.ods_abase_trae_message_intent_hi`（意图 LEFT JOIN）
- 一级下游表: `dwd_trae_chat_intent_hi`（意图打标）
- 关联表: `flow_aipaas.dwd_trae_ai_behavior_info_message_delta_di`（通过 user_message_id/message_id 关联）

## prompt_task_type 枚举值

`prompt_task_type` 字段来源于 prompt_completion 原始表的 `type` 字段（`t1.biz_type AS prompt_task_type`），通过 IN 白名单过滤。当前包含的值：

| 数据路径 | prompt_task_type 值 | 说明 |
|----------|---------------------|------|
| v3 路径 | `solo_coder` | Solo Coder 模式 |
| v3 路径 | `solo_builder` | Solo Builder 模式 |
| v3 路径 | `builder_v3` | Builder V3 模式 |
| v3 路径 | `chat_v3` | 普通对话 V3 模式 |
| v3 路径 | `solo_agent_remote` | Solo Agent 远程模式 |
| v3 路径 | `solo_agent_lite` | Solo Agent 轻量模式 |
| v3 路径 | `solo_work_lite` | Solo Work 轻量模式 |
| v3 路径 | `solo_work_remote` | Solo Work 远程模式 |
| v3 路径 | `chat` | 普通对话（非 V3） |
| v3 路径 | `dev_agent` | Dev Agent 模式 |
| v3 路径 | `solo_agent` | Solo Agent 模式 |
| v2 路径 | `fusion_chat` | 融合对话（V2 架构） |
| v2 路径 | `fusion_builder` | 融合 Builder（V2 架构） |

> **注意**：`prompt_task_type` 与 DWD 行为表的 `agent_type` 不完全等价。`agent_type` 来自前端埋点，经 CASE WHEN 映射；`prompt_task_type` 来自服务端 prompt_completion 记录的 `type` 字段，直通无映射。

## 字段明细

| 字段名 | 类型 | 描述 |
|--------|------|------|
| user_message_id | string | 用户消息的标识（主键） |
| app_id | string | App ID |
| chat_session_id | string | 聊天会话的标识 |
| user_id | string | 用户 ID |
| model_name | string | 模型名称 |
| pe_version | string | PE版本 |
| user_input | string | 用户输入内容 |
| mcp_server_name_list | array\<string\> | MCP服务器名称列表 |
| current_file_path | string | 当前文件路径 |
| current_file_content | string | 当前文件内容 |
| workspace_folder | string | 工作空间文件夹 |
| relevant_code_and_folders | array\<struct\<type:string,path:string,content:string\>\> | 相关代码和文件夹 |
| mentions | array\<struct\<path:string,line_num_range:string,content:string\>\> | 提及内容（@文件/@代码等） |
| prompt_task_type | string | 提示任务类型 |
| prompt_model_name | string | 提示模型名称 |
| prompt_text_output | string | 提示文本输出 |
| prompt_is_final_round | boolean | 提示是否为最后一轮 |
| server_created_at | string | 服务器创建时间 |
| intent_result | string | 意图打标结果，json格式 |
| user_source | string | 内外场（internal/public） |
| mentions_json | string | 提及内容原始Json |

> 分区键: date (string, yyyyMMdd) + hour (string, HH)
