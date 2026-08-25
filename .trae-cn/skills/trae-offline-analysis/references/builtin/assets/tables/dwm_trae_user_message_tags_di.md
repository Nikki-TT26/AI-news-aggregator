# dwm_trae_user_message_tags_di

AI对话用户消息问答特征表（每日增量），记录每个设备（did）在每天的用户消息标签信息。按 did 粒度聚合，message_tags 为数组类型，包含该用户当日所有消息的 query tag 去重集合。是**用户维度圈 Query** 的核心数据源。

> **圈 Query 概念**：圈 Query 是指通过 query tag（消息标签）筛选特定子人群或子消息集合，在 Libra Gallery 实验指标中按标签维度切分数据进行分析的机制。query tag 由在线服务在每条消息处理过程中打标并写入 Abase，标识该消息使用的模型名称和触发的行为/功能特征。圈 Query 分为两种维度：
> - **用户维度圈 Query**：在 Gallery 指标组中配置为"公共维度"（uuid 下其他维度细分后唯一），数据源为本表（`dwm_trae_user_message_tags_di`），按 did 聚合当日所有消息的 query tag 去重集合。适用于用户级别的指标分析（如某个 tag 下的用户活跃天、session 数等）。Gallery 生成的 Dorado 任务中，stg daily 表会取实验标签表与本表的交集，仅计算实验配置了的 query tag，并自动追加 `'all'` 值用于记录全集数据
> - **消息维度圈 Query**：在 Gallery 指标组中配置为"指标维度"，数据源为 `ods_abase_trae_message_tags_di`，直接按消息粒度的 query tag 筛选。适用于需要精确到消息级别的指标分析（如某个 tag 下的消息反馈率、工具调用率等）
>
> 参考：[Trae Libra圈Query指标建设](https://bytedance.larkoffice.com/wiki/BA2JwEb7eiqdNPkrxB0cow5QnBb)

- cn: `flow_aipaas.dwm_trae_user_message_tags_di`
- i18n: `cloudide.dwm_trae_user_message_tags_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- Dorado 任务 (cn): [dwm_trae_user_message_tags_di](https://data.bytedance.net/dorado/development/node/123501672?project=cn_11253) (projectId: 11253, taskId: 123501672)
- Dorado 任务 (sg): [dwm_trae_user_message_tags_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/305472989?project=sg_300004442) (projectId: 300004442, taskId: 305472989)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdwm_trae_user_message_tags_di%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fdwm_trae_user_message_tags_di%406#group=default
- 上游表: `flow_aipaas.dwd_trae_ai_behavior_info_message_delta_di`（提供 did、message_id）、`flow_aipaas.ods_abase_trae_message_tags_di`（提供 message_tags 原始标签）
- 数据生成逻辑: 通过 message_id 关联上述两张表，按 did + app_id 分组，对每组内所有消息的 message_tags 执行 COLLECT_SET → FLATTEN → array_distinct，得到用户当日去重标签集合

| 字段名 | 类型 | 描述 |
|--------|------|------|
| did | string | 设备唯一标识符（user_unique_id） |
| app_id | string | 应用ID，当前为固定值 `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8`（Dorado SQL 中硬编码） |
| message_tags | array\<string\> | 用户当日所有消息的 query tag 去重集合，每个用户通常包含 2~7 个标签（最多可达 25 个）。标签值分为两大类，详见下方说明 |

> 分区键: date (string, yyyyMMdd)

## message_tags 标签值说明

标签总量约 700+ 种（动态增长），分为两大类：

### 1. 模型名称标签

标识该用户当日使用过的 AI 模型。常见值（按使用量排序）：

| 标签值 | 说明 |
|--------|------|
| `doubao_dev` | 豆包开发版 |
| `doubao-for-auto` | 豆包自动模式 |
| `Doubao_1_6` / `doubao_1_8` | 豆包 1.6 / 1.8 版本 |
| `Doubao-Seed-2.0-Code` / `Doubao-Seed-2.0-Code-auto` | 豆包 Seed 2.0 Code 系列 |
| `minimax-m2.7` / `minimax-m2.5` / `MiniMax-M2.7-highspeed` | MiniMax M2 系列 |
| `glm-4.7` / `glm-5` / `glm-5.1` / `glm-5v-turbo` | GLM 系列 |
| `kimi-k2.5` | Kimi K2.5 |
| `qwen-3.5` / `qwen-3.6-plus` / `qwen3-coder` / `qwen3-coder-plus` | 通义千问系列 |
| `deepseek-V3.1` / `deepseek-reasoner` / `deepseek-chat` | DeepSeek 系列 |
| `ark-code-latest` | Ark Code 最新版 |

> 模型标签值可能存在大小写不一致的情况（如 `MiniMax-M2.7` 与 `minimax-m2.7` 并存），查询时需注意。

### 2. 行为/特征标签

标识该用户当日消息的交互特征和触发的功能。常见值（按使用量排序）：

| 标签值 | 说明 |
|--------|------|
| `run_command_tool_called` | 调用了运行命令工具 |
| `history_summarized` | 触发了对话历史摘要 |
| `prev_turn_user_canceled` | 上一轮对话被用户取消 |
| `parallel_tool_call` | 触发了并行工具调用 |
| `trigger_micro_compact` | 触发了微压缩（上下文窗口管理） |
| `trigger_bugfix_experience` | 触发了 bugfix 经验匹配 |
| `match_bugfix_experience` | 成功匹配到 bugfix 经验 |
| `trigger_ask_user_question` | 触发了向用户提问 |
| `trigger_ask_user_question_skipped` | 跳过了向用户提问 |
| `call_subagent` | 调用了子 Agent |
| `parallel_sub_agent_call` | 并行调用了子 Agent |
| `search_agent_qwen_fast` | 使用了 Qwen 快速搜索 Agent |
| `search_tool_called_with_sub_agent_route` | 搜索工具通过子 Agent 路由调用 |
| `search_tool_called_without_sub_agent_route` | 搜索工具未通过子 Agent 路由调用 |
| `plan_mode_via_slash_command` | 通过斜杠命令进入 Plan 模式 |
| `spec_mode_via_slash_command` | 通过斜杠命令进入 Spec 模式 |
| `trigger_experience_v2` / `match_experience_v2` | 触发/匹配了 V2 版经验系统 |
| `refactor_planner` | 使用了重构规划器 |

### 样本示例

一条典型记录的 message_tags 值：
```json
["doubao_dev", "trigger_micro_compact", "prev_turn_user_canceled", "Doubao-Seed-2.0-Code", "history_summarized", "parallel_tool_call", "run_command_tool_called", "trigger_bugfix_experience", "match_bugfix_experience"]
```
表示该用户当天使用了 doubao_dev 和 Doubao-Seed-2.0-Code 两个模型，并触发了微压缩、历史摘要、并行工具调用、bugfix 经验匹配等功能。
