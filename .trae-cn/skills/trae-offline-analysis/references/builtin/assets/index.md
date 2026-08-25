# Hive 表资产清单（索引）

> 本文件为轻量索引，仅包含通用知识和每张表的摘要。完整字段明细请按需读取 `assets/tables/<table_name>.md`。

## 通用知识

### 核心 ID

| ID | 说明 |
|----|------|
| vid | Libra 实验组 ID（version_id），标识用户所属的 A/B 实验分组。同一用户可能属于多个实验，因此可对应多个 vid。**注意**：大部分 DWD 行为表（delta_di、event_di、dau_accumulate_df 等）中的 vid 是**进组 vid**——用户当天被分入该实验组即会记录，但**进组不等于生效**，某条具体消息是否真正在该实验下生效需要自行甄别。若需确认某条消息实际命中了哪些实验版本，应查看 `dwd_resource_prompt_completion_di` 的 `ab_version` 虚拟列（可直接 `SELECT ab_version FROM ...`），该字段是**消息粒度**的实验命中列表，能准确反映该请求实际生效的实验版本 |
| uid | 用户 ID（user_id），字节内部用户唯一标识 |
| did | 设备 ID（device_id / user_unique_id），唯一标识一台设备。一个 uid 可对应多个 did |
| session_id | 会话 ID（conversation_id），一次连续的 AI 对话为一个 session |
| message_id | 消息 ID，一次用户提问 + AI 回复为一个 message。一个 session 包含多个 message |

### 表名后缀约定

| 后缀 | 全称 | 含义 | 查询建议 |
|------|------|------|----------|
| `_di` | daily increment | 每日增量表，仅包含当天新增/变更的数据 | **优先查询增量表**，数据量小、查询快 |
| `_df` | daily full | 每日全量表，每天包含全部存量数据的快照 | 需要历史全量视角时使用，TTL 通常较短（如 30 天） |
| `_hi` | hourly increment | 每小时增量表 | 需要更细时间粒度时使用 |
| `_hf` | hourly full | 每小时全量表 | 极少使用 |

> **查询优先级**：同一数据若有 `_di` 和 `_df` 两种表，应优先使用 `_di`（增量表），除非需要全量快照。增量表数据量小、查询快、TTL 长。

### 表名前缀约定

| 前缀 | 含义 |
|------|------|
| `ods_` | 原始操作数据层（Operational Data Store），由埋点/日志直接写入 |
| `dwd_` | 明细宽表层（Data Warehouse Detail），经过清洗、标准化，由 Dorado 任务调度生产 |
| `dwm_` | 中间宽表层（Data Warehouse Middle），基于 DWD 层多表关联加工的业务主题宽表 |
| `dim_` | 维度表（Dimension），用于枚举映射或分类聚合，通常数据量小、变化慢 |
| `stg_` | 中间层（Staging），Gallery 指标上线后自动生成，用户级或用户·实验组级的中间聚合数据 |
| `rpt_` | 报表层（Report），Gallery 自动生成，按实验组（vid）聚合的报表数据 |
| `mds_` | 模型层（Model Data Store），Gallery 自动生成，CUPED 等模型计算所需的宽表数据 |
| `calc_` | 计算层（Calculation），Gallery 自动生成的 Python 脚本任务，执行置信度计算等统计分析 |

> **注意**：`stg_`/`rpt_`/`mds_`/`calc_` 前缀的表和 Dorado 任务由 Gallery 平台自动创建和管理（详见 `concepts.md` §5），一般不需要手动修改或在资产索引中逐一记录。

### cn / i18n 环境差异

| 环境 | Hive 库名 | DataLeap Region | TQS Cluster | 说明 |
|------|-----------|-----------------|-------------|------|
| cn（国内） | `flow_aipaas` | cn | cn | 默认环境 |
| i18n（海外） | `cloudide` / `ai_application_coding` | sg | sg（需 TikTok SSO + 海外 TQS APP） | 表名与 cn 一致，库名不同 |

> **i18n 库名映射**：
> - 大部分表（10 张）在 `cloudide` 库下
> - `dim_trae_chat_tool_group`、`dwd_trae_message_feedback_di`、`dwd_trae_chat_input_hi`、`ods_trae_model_price`、`dwd_trae_chat_model_cost_di`、`dwd_trae_message_model_bench_tags`、`trae_agent_fornax_detail_di`、`trae_traj_detail_di`、`trae_message_traj_map_di`、`trae_conversation_message_map_di` 在 `ai_application_coding` 库下
> - `ods_abase_plugin_retrieve_agent_service_di` 在 sg **不存在**

> **schema 差异**：
> - 大部分表 cn/sg schema 完全一致
> - 少量表 sg 比 cn 多 `agent_type` 字段（`dwd_trae_ai_behavior_info_df`、`dwd_trae_did_vid_accumulate_di`、`dwd_trae_block_detail_di`）
> - `dwd_trae_did_vid_accumulate_di` 的 `vid` 类型不同：cn=int, sg=string
> - 枚举值（behavior_type、chat_type、agent_type 等）cn/sg 预期一致（同一产品不同区域部署）

> **TQS 查询海外表**（详见 `best-practices/bytedance-tqs.md` "海外 TQS 查询完整流程" 章节）：
> - 国内和海外使用**不同的 TQS APP**，需分别申请凭证
> - `.env.local`（国内）和 `.env.sg.local`（海外）位于**项目根目录**下
> - 查询时通过 `source` 显式加载对应凭证（不依赖 bytedcli 自动加载）
> - **推荐使用 `sg` 集群**（`TQS_CLUSTER=sg`）
> - **日期选择**：国内查 **T-1 及之前**，海外查 **T-2 及之前**（时差原因，海外 T-1 可能未就绪）
> - 示例：`(source .env.sg.local && bytedcli tqs execute --sql "SELECT ...")`

> **Hive 查询海外表**：
> - 使用 `bytedcli hive ... --region sg` 查询
> - 海外 hive 查询需要 TikTok SSO 认证：`bytedcli --site i18n-tt auth login`

### 常见枚举值

**behavior_type**（行为类型）：

| 值 | 含义 |
|----|------|
| `ai_chat` | AI 对话（Chat、Builder、Inline Chat 等） |
| `code_gen` | 代码补全（自动补全、Tab 接受等） |
| `other` | 其他行为 |

**chat_type**（交互类型）：

| 值 | 含义 |
|----|------|
| `side_chat` | 侧边栏对话（Side Chat） |
| `inline_chat` | 行内对话（Inline Chat） |
| `builder` | Builder 模式（Agent 自主编码） |
| `custom_agent` | 自定义 Agent |
| `NULL` | 未分类或非 chat 行为 |

**agent_type**（Agent 类型）：

> **注意**：`agent_type` 的来源是前端埋点日志表 `cloudide.dwd_behavior_trae_ide_public_user_log_di` 的 `params['agent_type']` 字段。在 DWD 行为表（`delta_di`、`event_di` 等）中，该字段经 Dorado SQL 的 CASE WHEN 逻辑从 `params['agent_type']` 和 `params['chat_type']` 派生。当 DWD 层找不到目标 agent_type 值时，可通过查看对应 Dorado 任务的 SQL 代码追溯字段映射逻辑。

| 值 | 含义 |
|----|------|
| `chat` | 普通对话 |
| `chat_v3` | 普通对话（V3 架构） |
| `builder` | Builder 模式 |
| `builder_v3` | Builder 模式（V3 架构） |
| `builder_with_mcp` | Builder + MCP 工具调用 |
| `builder_with_mcp_v3` | Builder + MCP 工具调用（V3 架构） |
| `inline_chat` | 行内对话 |
| `solo_coder` | Solo Coder 模式 |
| `solo_builder` | Solo Builder 模式 |
| `solo_agent` | Solo Agent 模式 |
| `code_reviewer` | 代码审查 |
| `code_review_summary` | 代码审查摘要 |
| `refactor_planner` | 重构规划器 |
| `refactor_incrementer` | 增量重构器 |
| `refactor_finder` | 重构发现器 |
| `refactor_scoper` | 重构范围分析器 |
| `custom` | 自定义 Agent |
| `custom_v3` | 自定义 Agent（V3 架构） |
| `ui_builder` | UI Builder 模式 |
| `dev_agent` | Dev Agent 模式 |
| `dsl_agent` | DSL Agent |
| `search` | 搜索 Agent |
| `solo_agent_remote` | Solo Agent 远程模式 |
| `solo_agent_lite` | Solo Agent 轻量模式 |
| `solo_work_lite` | Solo Work 轻量模式 |
| `solo_work_remote` | Solo Work 远程模式 |
| `NULL` / `0` | 未分类（DWD 层中 `0` 表示未设置） |

**block_type**（代码块类型，用于 dwd_trae_block_detail_di）：

| 值 | 含义 |
|----|------|
| `code_block` | 代码块 |
| `shell_block` | Shell 命令块 |
| `run_script` | 运行脚本块 |
| `run_mcp` | MCP 工具调用块 |
| `NULL` | 未分类 |

**event_name**（代码补全事件，用于 dwd_trae_ai_cue_event_di）：

| 值 | 含义 |
|----|------|
| `code_gen_request` | 代码补全请求 |
| `code_gen_shown` | 代码补全展示 |
| `code_gen_accept` | 代码补全接受 |
| `code_gen_canceled` | 代码补全取消 |

**access_type**（接入端类型，用于 dwd_resource_prompt_completion_di 的 `request_metadata` 虚拟列 `$.access_type`）：

| 值 | 含义 |
|----|------|
| `Default` | 桌面端 IDE（VS Code 插件形态），主要用户群 |
| `Mobile` | 移动端 |
| `SoloLite` | 轻量版（浏览器内轻量 IDE） |
| `SoloWeb` | Web 版 |
| *(空值)* | 部分老版本客户端未上报该字段 |

> ⚠️ `device_id` 仅在 `Default` 端上报较完整，其他端覆盖率极低。跨 access_type 的 DAU 分析**必须用 `user_id`**。详见 `concepts.md` §3.5.2 和 `dwd_resource_prompt_completion_di.md` 的「DAU 统计口径建议」。

---

### 圈 Query（Query Tag 维度切分）

圈 Query 是指通过 query tag（消息标签）筛选特定子人群或子消息集合，在 Libra Gallery 实验指标中按标签维度切分数据进行分析的机制。query tag 由在线服务在每条消息处理过程中打标并写入 Abase，标识该消息使用的模型名称和触发的行为/功能特征（如 `doubao_dev`、`run_command_tool_called`、`trigger_bugfix_experience` 等），标签总量约 700+ 种且动态增长。

圈 Query 分为两种维度，在 Gallery 指标组中的配置方式不同：

| 维度 | Gallery 配置 | 数据源表 | 粒度 | 适用场景 |
|------|-------------|---------|------|---------|
| **用户维度圈 Query** | 公共维度（uuid 下其他维度细分后唯一） | `dwm_trae_user_message_tags_di` | did（设备） | 用户级指标：活跃天、session 数、人均消息数等 |
| **消息维度圈 Query** | 指标维度 | `ods_abase_trae_message_tags_di` | message_id（消息） | 消息级指标：反馈率、工具调用率、代码块接受率等 |

**数据链路**：
- 在线服务对每条消息打标 → 写入 Abase → `ods_abase_trae_message_tags_di`（消息粒度，Abase2Hive 自动同步）
- `ods_abase_trae_message_tags_di` + `dwd_trae_ai_behavior_info_message_delta_di` 通过 message_id JOIN → 按 did 聚合 → `dwm_trae_user_message_tags_di`（用户粒度）

**Gallery 自动任务生成规则**：
- **stg daily 表**：取实验标签配置（每个实验仅计算已配置的 query tag）与 query tag 表的交集；自动追加 `'all'` 值记录全集数据；将 query tag 数组展开（explode）为多行
- **stg all 表**：将当天 tag 数据与历史全量 tag 聚合，每个 query tag 维度下聚合全量数据
- **rpt all 表**：按圈 query 维度计算统计值；其他维度取 query tag 为 `'all'` 的全量数据

> 参考：[Trae Libra圈Query指标建设](https://bytedance.larkoffice.com/wiki/BA2JwEb7eiqdNPkrxB0cow5QnBb)

### 表间关系与指标计算主入口

**指标计算的主入口表**是 `dwd_trae_ai_behavior_event_di`（event_di），大部分 Libra Gallery 指标组的数据源 SQL 都基于该表构建。该表不含 vid 维度，按 uid+session_id+message_id 聚合，适用于事件维度的指标计算。

**核心上游表**：`cloudide.dwd_behavior_trae_ide_public_user_log_di` 是 event_di 和 delta_di 等 DWD 行为表的主要数据来源，是前端埋点的行为日志明细表。当需要追溯 DWD 行为表中字段的原始值（如 `agent_type` 的 CASE WHEN 映射逻辑），应查看对应 Dorado 任务的 SQL 代码。

**模型调用数据链路（prompt_completion 系列）**：与前端埋点数据链路（dwd_behavior → event_di/delta_di）平行的另一条数据链路，记录服务端每次模型调用的原始请求与回复。层级关系如下：
- **原始表**：`codeverse_codegen_cn.prompt_completion_hourly`（外场）和 `codeverse_codegen_cn.prompt_completion_bd_hourly`（内场），按小时分区，一条消息的每次模型调用（意图识别/context选择/chat 等）都有一条记录
- **按天加工表**：`cloudide.dwd_resource_prompt_completion_di`（外场，按天分区，仍为明细粒度），数据来源于 `prompt_completion_hourly`，经字段提取和转换后生成，**外场场景优先使用此表**
- **内场**可直接使用 `prompt_completion_bd_hourly`（目前无对应的按天加工表）
- **token 消耗**：`prompt_completion_hourly` / `prompt_completion_bd_hourly` 原始表没有独立的 token 消耗字段，需通过 `get_json_object(request_metadata, '$.usage.total_tokens')` 等方式从 `request_metadata` JSON 中解析；加工表 `dwd_resource_prompt_completion_di` 已将 token 拆成独立字段（`total_tokens_cnt`、`prompt_tokens_cnt`、`completion_tokens_cnt` 等）
- **成本计算表**：`flow_aipaas.dwd_trae_chat_model_cost_di`（i18n：`ai_application_coding.dwd_trae_chat_model_cost_di`）基于 `dwd_resource_prompt_completion_di` 关联单价表 `ods_trae_model_price` 计算每条请求的 CU 成本，采用最长前缀匹配 + 家族兜底 + ark 兜底策略。**注意**：该表已修正字段语义（`session_id` = 会话，`message_id` = 消息），与上游 completion_di 的命名不同
- **字段差异**：原始表中用户字段名为 `username`，DWD 加工表中为 `user_id`；原始表时间字段为 `created_at`/`updated_at`/`deleted_at`（string），DWD 加工表为 `create_timestamp`/`update_timestamp`/`delete_timestamp`（bigint）
- ⚠️ **session_id / conversation_id 语义反转**：`dwd_resource_prompt_completion_di` 中 `session_id` 实际含义是 message_id，`conversation_id` 实际含义是 session_id。下游 `dwd_trae_chat_model_cost_di` 已在 Dorado SQL 中修正语义

**Fornax Trace 链路**：`flow_aipaas.trace_from_fornax` 是 Trae Agent 链路追踪的核心数据源，记录每次请求的完整 span 信息。与 prompt_completion 系列（记录模型调用的请求/回复）互补，trace_from_fornax 提供更底层的链路追踪视角（含 model_input/model_output 结构化数据）。查询时**必须限定** `fornax_space_id = '7444123531090067458'`。关键 span 类型：`LLMCallSpan`（LLM 上下文）、`[Track]PromptRenderNode`（输入信息）、`ExperienceRecall`（EAG 相关）、`IntentRecognition`（意图相关）。

**Agent 轨迹数据链路（Trajectory 系列）**：从 Fornax Trace 数据中提取加工的离线表体系，是分析 Agent 行为、模型调用效率、工具使用模式、对话质量的**核心数据源**。数据链路如下：
```
Fornax 在线 Trace → dwd_impr_fornax_trace_detail_hi（Fornax 平台小时表，TTL 7天）
    → flow_aipaas.trae_agent_fornax_detail_di（ODS 天级表）
        → flow_aipaas.trae_conversation_message_map_di（Conversation-Message 映射）
        → flow_aipaas.trae_traj_detail_di（Trajectory 详情表，最核心）
        → flow_aipaas.trae_message_traj_map_di（Message-Trajectory 映射）
```
- **trae_traj_detail_di**（⭐ 最重要）：每行一条完整轨迹，含 Agent 元信息、完整 messages JSON、token 统计、finish_reason 等。**在做 Agent 相关的深度分析时，应优先考虑此表**
- **trae_agent_fornax_detail_di**：ODS 原始 Span 表，Span 级别原始数据，适合需要深度自定义聚合的场景
- **trae_conversation_message_map_di**：conversation_id → message_id 的 1:N 有序映射，含 Span 统计、意图、经验召回等汇总信息
- **trae_message_traj_map_di**：message_id → traj_id_list 的映射（仅 master 轨迹）
- 刷新频率：每天 T+1，分区字段 `date`（yyyyMMdd），TTL 因表而异（详见各表详情文件）
- 核心概念：一个 Trajectory 是 Agent 处理请求时的一段连续 LLM 交互序列。一次用户消息可产生多个 Trajectory（master + sub），通过 parent_traj_id 和 trigger_tool_call_id 还原主/子 Agent 调用关系

**i18n Fornax 数据链路**：海外 Agent 轨迹数据采用独立链路，经 VA 中间表跨区域同步至 SG：
```
Fornax 原始 Trace (coze_dw..., VA region)
  → flow_aipaas.dwd_impr_fornax_trace_detail_new_hi（VA 中间表筛选）
  → 跨区域同步 VA → SG
  → ai_application_coding.trae_agent_fornax_detail_hi（SG ODS 清洗）
      → trae_traj_detail_di / trae_conversation_message_map_di / trae_message_traj_map_di
```
- 海外 Fornax Space ID：`7449000872878538804`
- 海外 Fornax 链接：`https://fornax-i18n.byteintl.net/space/7449000872878538804/...`（cn 链接为 `https://fornax.bytedance.net/space/7444123531090067458/...`）
- 海外数据就绪时间为 **T-2**（时差原因，T-1 可能未就绪）
- 排查海外 Agent 轨迹时，将 SQL 中的 `flow_aipaas` 替换为 `ai_application_coding`，在 SG region 执行

**Tool Call 数据链路**：`code_evaluation.trae_cn_toolcalls` 记录每一轮 Tool Call 的解析结果（工具名称、参数、模型信息、token 消耗等），是分析工具调用分布和链路的专用表。

**加工表（意图/特征打标）**：
- `dwd_trae_chat_input_hi`：用户消息详情表（小时级），包含用户输入内容、文件上下文、MCP 服务器列表、意图打标结果等。是意图打标链路的入口表，上游来自 `prompt_completion` 系列原始表（海外为 `flow_ide_base.prompt_completion_va_hourly` / `flow_ide_base.prompt_completion_hourly`），通过 `type IN (...)` 白名单过滤业务类型（含 `solo_agent_remote`、`solo_agent_lite`、`solo_work_lite`、`solo_work_remote`、`chat`、`dev_agent`、`solo_agent` 等）
- `dwd_trae_chat_intent_hi`：意图打标小时表，由 PySpark 任务从 `dwd_trae_chat_input_hi` 读取数据并调用 LLM 进行意图分类，**无额外 type 过滤**
- `dwd_trae_chat_intent_di`：意图打标天级表，cn 和 sg 均从 `dwd_trae_chat_intent_hi` 按天聚合（简单 SELECT，无额外过滤）
- `flow_aipaas.dwd_trae_message_model_bench_tags`：特征打标表，记录用户消息的辱骂/称赞等多维度特征评估
- 上述意图/特征表的 `chat_session_id` 对应 `conversation_id`，可通过 `user_message_id` 与 `dwd_trae_chat_input_hi` 关联
- **意图打标完整链路**：`prompt_completion 原始表 → dwd_trae_chat_input_hi → dwd_trae_chat_intent_hi → dwd_trae_chat_intent_di`

### Libra 实验进组口径

Libra 实验的标准进组口径表为 `origin_log.dwd_abtest_vid_log_other_apps_df`：

```sql
SELECT CAST(version_id AS BIGINT) AS vid,
       user_unique_id,
       MIN(min_date) AS min_date,
       MAX(is_active) AS is_active
FROM origin_log.dwd_abtest_vid_log_other_apps_df
WHERE date = '${date}'
  AND app = 'trae_cn'
GROUP BY CAST(version_id AS BIGINT), user_unique_id
```

| 字段 | 含义 |
|------|------|
| `version_id` | 实验版本 ID（vid），对应 Libra 实验的各分组 |
| `user_unique_id` | 设备 ID（did），与 DWD 行为表的 did 对应 |
| `min_date` | 首次进组日期 |
| `is_active` | 当天是否活跃 |
| `app` | 应用标识，TRAE CN 为 `'trae_cn'` |

**用途**：
- 在 TQS 中独立验证 Libra 指标时，需要用此表获取实验各分组的进组用户列表
- Gallery 指标组上线后，Libra 平台会自动使用此口径关联进组数据（通过 AB 日志 SQL），无需手动处理
- 验证时将此表与数据源表（如 `dwd_trae_ai_behavior_info_message_delta_di`）做 JOIN，可复现 Libra 报告的指标值

> **注意**：此表未收录到 assets/tables/ 中，因为它由 Libra 平台统一管理，不属于 TRAE 数据链路。查询时需确认 TQS APP 对 `origin_log` 库有读权限。

### 模型配置说明

- `config_name` 是大类模型配置名称，同一个 config_name 下请求时可能路由到不同的 `model_name`（模型负载均衡，可能部署了多个不同名称的实例）
- **常规豆包模型**（doubao / doubao-dev / 豆包）：`config_name IN ('Doubao_1_6', 'Doubao-Seed-2.0-Code')`
- `config_name = 'doubao_1_8'` 是独立模型，不属于上述常规豆包模型，平时不需要特别关注
- 三方模型：`config_name IN ('glm-5', 'glm-4.7', 'minimax-m2.5', 'kimi-k2.5', ...)`

#### 模型字段跨表命名映射

用户常说 `config_name` 和 `provider_model_name`，但不同表中字段名不同：

| 用户说法 | DWD 行为表字段名 | 模型调用表字段名 | 说明 |
|---------|----------------|----------------|------|
| `config_name` | `message_model`（delta_di / event_di / message_delta_di） | `config_name`（cost_di，从 prompt_completion_di 虚拟列提取） | 大类模型配置名称（如 `Doubao_1_6`、`glm-5`） |
| `provider_model_name` | — | `model_name`（prompt_completion_di / cost_di） | 实际路由到的模型实例名称（如 `seed-exp-d7v8c`） |

- `config_name`（message_model）1:N 对应 `provider_model_name`（model_name）
- 按 `config_name` 筛选 → 在行为表的 `message_model` 字段过滤，或在 `cost_di` 的 `config_name` 字段过滤
- 按 `provider_model_name` 筛选 → 在 `prompt_completion_di` / `cost_di` 的 `model_name` 字段过滤，再通过 message_id 关联行为表
- `traj_detail_di` 中模型信息为 `model_name_list`（一条轨迹可能用多个模型）

#### agent_type 枚举值注意事项

`delta_di` / `event_di` 等行为表中的 `agent_type` 字段值与用户口头说法可能存在差异：

- 用户说 `builder_v3` → 在行为表中**不一定存在**该值。部分实验组中 Builder V3 架构的记录实际存储为 `builder`，而非 `builder_v3`
- **建议**：查询前先用 `GROUP BY agent_type` 确认目标实验组中实际存在的 agent_type 枚举值，避免因枚举值不匹配导致查询结果为空
- 已确认案例：vid=16338079 实验组中，Builder 类型记录的 agent_type 值为 `builder`，而非 `builder_v3`

### ID 跨表映射注意事项

不同表中同名字段含义可能不同：

| 表 | `session_id` 含义 | `chat_session_id` 含义 | `message_id` / `user_message_id` 含义 |
|---|---|---|---|
| `dwd_behavior_trae_ide_public_user_log_di` | conversation_id | — | message_id |
| `dwd_trae_ai_behavior_event_di` / `delta_di` / `df` | conversation_id | — | message_id |
| `dwd_trae_chat_model_cost_di` | conversation_id（从上游 completion_di.conversation_id 重命名而来） | — | message_id（从上游 completion_di.session_id 重命名而来） |
| `dwd_resource_prompt_completion_di` | ⚠️ **message_id**（语义反转！） | — | — （无此字段，message_id 在 session_id 字段中） |
| `dwd_trae_chat_input_hi` | — | conversation_id | user_message_id = message_id |
| `dwd_trae_chat_intent_di` | — | conversation_id | user_message_id = message_id |
| `dwd_trae_message_model_bench_tags` | — | conversation_id | user_message_id = message_id |

> **跨表 JOIN 规则**（经实际数据验证）：
> - **常规表之间**：直接用 `session_id = session_id` + `message_id = message_id` JOIN（如 event_di ↔ cost_di ↔ behavior_log）
> - **chat_session_id 表 ↔ session_id 表**：`chat_session_id = session_id` + `user_message_id = message_id`（如 bench_tags ↔ event_di）
> - **completion_di ↔ cost_di**：`completion_di.session_id = cost_di.message_id`，`completion_di.conversation_id = cost_di.session_id`（因为 completion_di 语义反转，cost_di 已修正）
> - **completion_di ↔ 其他表**：`completion_di.session_id = 其他表.message_id`，`completion_di.conversation_id = 其他表.session_id`
>
> ⚠️ **prompt_completion_di 语义反转**：`dwd_resource_prompt_completion_di` 表中 `session_id` 实际是 message_id，`conversation_id` 实际是 session_id。下游 `dwd_trae_chat_model_cost_di` 已通过 Dorado SQL 修正（`conversation_id AS session_id, session_id AS message_id`），字段名与实际含义一致。

### 查询场景决策

| 场景 | 推荐表 | 原因 |
|------|--------|------|
| ⭐ Agent 轨迹分析（模型对比、性能、对话质量） | `trae_traj_detail_di` | 每行一条完整轨迹，含 messages、token 统计、finish_reason，最适合 Agent 行为分析 |
| ⭐ 子 Agent 调用链分析 | `trae_traj_detail_di` | 通过 parent_traj_id 和 trigger_tool_call_id 还原主/子 Agent 调用关系 |
| ⭐ Span 级深度分析 | `trae_agent_fornax_detail_di` | 原始 Span 数据，含 input_json/output_json，适合自定义聚合 |
| ⭐ Conversation → Message → Traj 追踪 | `trae_conversation_message_map_di` + `trae_message_traj_map_di` | 层级映射，适合从会话维度追踪到轨迹 |
| 查某个 log_id 的 trace | `trace_from_fornax` | trace 信息最完整，有结构化的 model_input/output |
| 日活 / 模型调用量 / 排队等待 | `dwd_resource_prompt_completion_di` | 统计字段最全，request_metadata 包含丰富信息。⚠️ **DAU 必须用 `user_id` 去重**，`device_id` 在非桌面端（Mobile/SoloWeb/SoloLite）覆盖率极低，不可用于 DAU 统计 |
| 模型调用成本分析 | `dwd_trae_chat_model_cost_di` | 已关联单价表计算 CU 成本，含价格匹配信息和各项成本明细 |
| 排查某条消息是否真正命中实验（vid 排查） | `dwd_resource_prompt_completion_di` | `ab_version` 虚拟列是**消息粒度**的实验命中列表，可直接查询；其他行为表的 vid 是进组 vid（进组≠生效），无法确认单条消息是否真正在该实验下生效 |
| 用户前端行为分析 | `dwd_behavior_trae_ide_public_user_log_di` | 前端埋点数据 |
| Tool Call 分析 | `trae_cn_toolcalls` | 专门的工具调用解析表 |
| 用户意图分析 | `dwd_trae_chat_intent_di` | 专门的意图打标表 |
| 用户特征标签（辱骂/称赞） | `dwd_trae_message_model_bench_tags` | 模型自动评估，`model_pred` JSON 含两个维度：情感（`$.sentiment_label`：辱骂/称赞/其他）和对话流转（`$.conv_flow_label`：原地踏步/打补丁/流畅/其他）。用 `get_json_object` 提取，详见该表文档 |
| 原地踏步 / 打补丁分析 | `dwd_trae_message_model_bench_tags` | `get_json_object(model_pred, '$.conv_flow_label') = '原地踏步'`。评估 Agent 是否在循环执行相同操作无进展。详见 `concepts.md` §3.5.5 |
| 辱骂 / 用户情感分析 | `dwd_trae_message_model_bench_tags` | `get_json_object(model_pred, '$.sentiment_label') = '辱骂'`。评估用户是否对 AI 表达不满。详见 `concepts.md` §3.5.5 |
| 用户输入 & 上下文详情 | `dwd_trae_chat_input_hi` | 包含用户输入、文件上下文、mentions、意图打标等丰富信息 |
| 消息维度圈 Query / 按 query tag 筛选消息 | `ods_abase_trae_message_tags_di` | 消息粒度 query tag 表，支持按模型名称或行为特征标签过滤消息，常与 toolcalls / prompt_completion 联合查询。在 Gallery 中配置为"指标维度" |
| 用户维度圈 Query / 按 query tag 筛选子人群 | `dwm_trae_user_message_tags_di` | 按 did 聚合的当日 query tag 去重集合，在 Gallery 中配置为"公共维度"。适合用户粒度的实验指标按标签切分 |
| 圈 query 验证（按维度筛选子人群的实验指标） | 进组表 + DWD 底表 + `dwm_trae_user_message_tags_di` | 按 `concepts.md` §6.4 构造验证 SQL：进组表提供 vid+did，DWD 底表提供指标，`dwm_trae_user_message_tags_di`（cn: `flow_aipaas`，i18n: `cloudide`）提供 message_tags 维度（`array<string>` 类型，用 `array_contains` 筛选），is_new 等维度从 Gallery 数据源 SQL 复现 |
| 代码补全分析（触发率/接受率/取消率） | `dwd_trae_ai_cue_event_di` | 代码补全事件明细表，支持按 `event_name` 区分请求/展示/接受/取消，按语言/模型/触发方式切分。漏斗：`code_gen_request → shown → accept/canceled`。详见 `concepts.md` §3.5.4 |
| 代码补全行为（message 粒度聚合） | `dwd_trae_ai_behavior_event_di` | 行为表含 `code_gen_shown_cnt`/`accept_cnt`/`canceled_cnt`，适合 message 粒度的聚合分析。如需按语言、模型切分，应用 `dwd_trae_ai_cue_event_di` |
| 打断/取消分析 | `dwd_trae_ai_behavior_event_di` | `is_canceled = 1` 标识用户手动取消的消息。注意：消息级打断（is_canceled）与代码补全取消（code_gen_canceled）是不同概念，详见 `concepts.md` §3.5.3 |
| 打断后重试分析 | `dwm_trae_user_message_tags_di` | 标签含 `prev_turn_user_canceled` 表示上一轮被取消，当前消息是取消后的重试 |
| 付费权益分析（订阅/退款/用量） | `dwm_trade_trae_entitlement_order_usage_statistic_df` | 权益粒度宽表，含产品类型、扣费金额、AI 使用量、退款等，适合付费用户行为和商业化分析 |
| 用户画像 / 升降级分析 / 会员分布 | `dwm_trade_trae_user_order_entitlement_statistic` | 用户粒度宽表，每日全量用户快照，含会员状态、升降级判断、订阅取消、订单统计，适合用户维度的商业化分析 |


---

## 表资产索引

> 需要字段列表、Dorado 任务 ID、Hive URL、上下游关系等详情时，读取 `assets/tables/<table_name>.md`。

| 表名 | 说明 | cn 库 | i18n 库 |
|------|------|-------|---------|
| `dwd_behavior_trae_ide_public_user_log_di` | 前端埋点行为日志，多张 DWD 表的核心上游 | cloudide | cloudide |
| `dwd_trae_ai_behavior_info_delta_di` | AI 行为每日增量（vid+session+message 粒度） | flow_aipaas | cloudide |
| `dwd_trae_ai_behavior_info_df` | AI 行为日全量快照，字段同 delta_di | flow_aipaas | cloudide |
| `dwd_trae_did_vid_accumulate_di` | 用户实验组留存（did+vid，含多档留存标签） | flow_aipaas | cloudide |
| `dwd_trae_ai_behavior_event_di` | **指标计算主入口**，AI 行为事件（不含 vid） | flow_aipaas | cloudide |
| `dwd_trae_ai_behavior_info_message_delta_di` | Message 粒度行为增量（message_id 唯一） | flow_aipaas | cloudide |
| `dwd_trae_dau_accumulate_df` | 活跃用户累计全量（uid+did+vid，字段精简） | flow_aipaas | cloudide |
| `dwd_trae_tool_call_accumulate_delta_di` | 工具调用增量聚合（按 tool_type 粒度） | flow_aipaas | cloudide |
| `dwd_trae_ai_cue_event_di` | 代码补全事件明细（触发/展示/接受/取消） | flow_aipaas | cloudide |
| `dwd_trae_block_detail_di` | 代码块明细（block_id 粒度，含 shell_block） | flow_aipaas | cloudide |
| `ods_abase_plugin_retrieve_agent_service_di` | Abase 同步表，在线意图识别数据 | flow_aipaas | **无** |
| `ods_abase_trae_message_tags_di` | Abase 同步表，消息粒度 query tag（**消息维度圈 Query** 核心数据源，含 message_tags 虚拟列） | flow_aipaas | cloudide |
| `dim_trae_chat_tool_group` | 工具类型 → 工具大类映射维度表 | flow_aipaas | ai_application_coding |
| `dwd_trae_message_feedback_di` | 消息正负反馈（点赞/点踩） | flow_aipaas | ai_application_coding |
| `dwd_trae_chat_input_hi` | AI对话用户消息意图表（用户输入内容、上下文、意图打标等） | flow_aipaas | ai_application_coding |
| `dwd_trae_chat_intent_hi` | 意图打标小时表（LLM 意图分类结果，小时级） | flow_aipaas | ai_application_coding |
| `dwd_trae_chat_intent_di` | 意图打标表（用户消息的意图分类、语言、代码语言和框架） | flow_aipaas | ai_application_coding |
| `prompt_completion_hourly` | **原始表**，AI对话消息的模型调用明细（外场，每次模型调用一条记录） | codeverse_codegen_cn | 待确认 |
| `prompt_completion_bd_hourly` | **原始表**，AI对话消息的模型调用明细（内场，每次模型调用一条记录） | codeverse_codegen_cn | 待确认 |
| `dwd_resource_prompt_completion_di` | 模型调用请求明细（prompt+completion 粒度，含 token/延迟/排队等），**外场按天加工表，优先使用**。⚠️ session_id 实际含义是 message_id，conversation_id 实际含义是 session_id | cloudide | cloudide |
| `dwd_trae_chat_model_cost_di` | AI Chat 模型调用成本明细（每条请求关联单价表，含 CU 成本），字段语义已从上游修正（session_id=会话，message_id=消息） | flow_aipaas | ai_application_coding |
| `ods_trae_model_price` | 模型单价配置表（飞书电子表格同步），`dwd_trae_chat_model_cost_di` 的上游价格表 | flow_aipaas | ai_application_coding |
| `dwm_trae_user_message_tags_di` | AI对话用户消息 query tag 聚合表（did 粒度，**用户维度圈 Query** 核心数据源，含 message_tags 数组） | flow_aipaas | cloudide |
| `trace_from_fornax` | Fornax Trace 链路追踪表（span 粒度，含 model_input/output），**查 log_id trace 优先使用** | flow_aipaas | 待确认 |
| `trae_cn_toolcalls` | Tool Call 工具调用解析表（每轮工具调用一条记录） | code_evaluation | 待确认 |
| `dwd_trae_message_model_bench_tags` | 特征打标表（用户消息的辱骂/称赞等特征评估） | flow_aipaas | ai_application_coding |
| `trae_traj_detail_di` | ⭐ **Agent 轨迹详情表**（每行一条完整轨迹，含 messages、token 统计、finish_reason），Agent 分析核心表 | flow_aipaas | ai_application_coding |
| `trae_agent_fornax_detail_di` | ODS 原始 Span 表（从 Fornax Trace 按 Trae space_id 筛选的 Span 级数据） | flow_aipaas | ai_application_coding |
| `trae_conversation_message_map_di` | Conversation-Message 映射表（conversation_id → message_id 有序映射，含 Span 统计和意图信息） | flow_aipaas | ai_application_coding |
| `trae_message_traj_map_di` | Message-Trajectory 映射表（message_id → master traj_id_list 映射） | flow_aipaas | ai_application_coding |
| `dwm_trade_trae_entitlement_order_usage_statistic_df` | 权益订单粒度商业化宽表（权益粒度，含订单关联、AI 使用量、退款信息），付费分析核心表 | — | cloudide |
| `dwm_trade_trae_user_order_entitlement_statistic` | 用户粒度商业化宽表（每日全量用户快照，含会员状态、升降级判断、订阅/取消、订单统计），用户画像与升降级分析核心表 | — | cloudide |
