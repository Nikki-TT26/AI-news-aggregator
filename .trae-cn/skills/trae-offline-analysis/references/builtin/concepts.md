# 核心概念

## 1. 离线数据分析各平台职责

| 平台                    | 职责                                       |
| --------------------- | ---------------------------------------- |
| **Hive**              | 存储原始数据与加工后的明细/汇总表                        |
| **Dorado (DataLeap)** | 调度天级/小时级 SQL ETL 任务，完成数据清洗与加工，存入 Hive 表        |
| **TQS**               | 校验 Hive SQL 语法，提交异步查询 Hive 表数据，拉取结果               |
| **Aeolus（风神）**        | 提供 BI 数据集（dataset）和仪表盘（dashboard）        |
| **Libra**             | A/B 实验平台，管理实验、流量分配、查看实验报告与显著性            |
| **Libra Gallery**     | 管理指标组（metric group），指标组挂载到 Libra 实验报告中使用 |

## 2. 关键术语

### 2.1 核心 ID

| 术语              | 含义                   |
| --------------- | -------------------- |
| **vid**         | 实验组 ID，来自 Libra 实验平台 |
| **uid**         | 用户 ID                |
| **did**         | 设备 ID                |
| **session\_id** | 会话 ID，标识一次对话会话       |
| **message\_id** | 消息 ID，标识一条消息         |
| **log\_id**     | 每次请求模型的日志 ID，如调用模型生成 tool call、生成最终回复等。一个 message 内包含多次模型调用，每次有独立 log\_id |

层级关系：`conversation (session) > message > log_id (model call)`

### 2.2 Agent 轨迹（Trajectory）

一个 Trajectory 是 Agent 处理请求时的一段**连续 LLM 交互序列**。一次用户消息（message）可以产生多个 Trajectory，形成树形结构：

```
conversation (会话)
  └── message (一次用户提问)
        ├── master traj（主轨迹）── Agent 主循环的 LLM 交互
        │     └── sub traj（子轨迹）── 子 Agent（如 Search Agent）的 LLM 交互
        └── master traj（第二段主轨迹，因 compact/summary 导致消息变化而切分）
```

| 术语 | 含义 |
|------|------|
| **traj\_id** | 轨迹唯一 ID，格式 `{message_id}_{traj_type}_{uuid}` |
| **traj\_type** | 轨迹类型：`master`（主 Agent 轨迹）/ `sub`（子 Agent 轨迹） |
| **traj\_tag** | 轨迹标签：0=正常结束，1=异常（最后一条 LLMCallSpan 输出仍含 tool_calls） |
| **parent\_traj\_id** | sub 轨迹指向触发它的 master 轨迹 |
| **finish\_reason** | 轨迹结束原因：stop / tool_calls / length / engine_overloaded / sensitive 等 |

数据来源：从 Fornax Trace 数据中提取加工，核心表为 `flow_aipaas.trae_traj_detail_di`，TTL 30 天，每天 T+1 刷新。

### 2.3 Gallery 相关术语

| 术语                    | 含义                                                     |
| --------------------- | ------------------------------------------------------ |
| **ticket**            | Gallery 需求单，用于跟踪指标组的建设需求                               |
| **metric group（指标组）** | 一组相关指标的集合，挂载到 Libra 实验报告                               |
| **data source（数据源）**  | Gallery 中的 SQL 定义，引用 Hive 表，使用 `Tx:column` 格式引用列       |
| **dimension（维度）**     | 分维度类型：`USER_DIMENSION`（用户维度）或 `METRIC_DIMENSION`（指标维度） |
| **metric（指标）**        | 分指标类型：simple（PV/UV）、ratio（PV/PV 比率）、per-user（PV/UV 人均） |

## 3. 环境说明

| 环境             | 说明                    |
| -------------- | --------------------- |
| **cn（中国机房）**   | 使用 `flow_aipaas` 数据库  |
| **i18n（海外机房）** | 数据库名可能不同，但表名与 cn 保持一致 |

进行数据查询或建设指标时，需注意区分环境，确保引用正确的数据库前缀。

## 3.5 TRAE 产品功能模块

### 3.5.1 核心功能模块

| 功能模块 | 说明 | 数据表中的标识 |
|---------|------|--------------|
| **AI Chat（Side Chat）** | 侧边栏对话，用户在聊天面板中与 AI 交互 | `chat_type = 'side_chat'` |
| **Inline Chat** | 行内对话，在编辑器中选中代码后直接与 AI 对话 | `chat_type = 'inline_chat'` |
| **Builder** | Agent 自主编码模式，AI 可自主规划、编写、调试代码 | `chat_type = 'builder'`、`agent_type = 'builder'/'builder_v3'` |
| **代码补全（Code Completion）** | 编码时自动触发的智能补全建议，用户通过 Tab 接受 | `behavior_type = 'code_gen'`，专用表 `dwd_trae_ai_cue_event_di` |
| **MCP 工具调用** | 通过 Model Context Protocol 调用外部工具 | `agent_type` 含 `_with_mcp`，工具调用表 `dwd_trae_tool_call_accumulate_delta_di` |

### 3.5.2 接入端（access_type）

TRAE 支持多种接入端，通过 `dwd_resource_prompt_completion_di` 的 `access_type` 虚拟列（`request_metadata` 的 `$.access_type`）区分：

| access_type | 说明 |
|-------------|------|
| `Default` | 桌面端 IDE（VS Code 插件形态），主要用户群 |
| `Mobile` | 移动端 |
| `SoloLite` | 轻量版（浏览器内轻量 IDE） |
| `SoloWeb` | Web 版 |
| *(空值)* | 部分老版本客户端未上报该字段 |

> ⚠️ `device_id` 仅在 `Default` 端上报较完整，其他端覆盖率极低。跨 access_type 的 DAU 分析**必须用 `user_id`**。

### 3.5.3 打断/取消（Cancel）机制

用户可以在 AI 响应过程中手动取消（打断）当前消息。打断在数据中的体现：

| 数据位置 | 字段/标签 | 含义 |
|---------|----------|------|
| DWD 行为表（event_di、delta_di、df） | `is_canceled = 1` | 该消息被用户手动取消 |
| `dwd_trae_tool_call_accumulate_delta_di` | `is_canceled = 1` | 工具调用所属消息被取消 |
| `dwm_trae_user_message_tags_di` | 标签含 `prev_turn_user_canceled` | 上一轮对话被用户取消（当前消息是取消后的重试） |
| `dwd_trae_ai_cue_event_di` | `event_name = 'code_gen_canceled'` | 代码补全建议被取消（非消息级打断，是补全建议的取消） |
| Trajectory 表 | `finish_reason` | 轨迹结束原因，若为非 `stop` 可能涉及异常中断（`tool_calls` / `length` / `engine_overloaded` 等） |

> **注意**：消息级的「打断」（is_canceled）和代码补全的「取消」（code_gen_canceled）是不同概念。前者是用户中止 AI Chat/Builder 的回复过程，后者是用户忽略/拒绝了代码补全建议。

### 3.5.4 代码补全漏斗

代码补全有一个标准的事件漏斗，数据记录在 `dwd_trae_ai_cue_event_di` 的 `event_name` 字段：

```
code_gen_request（请求触发）
  → code_gen_shown（结果展示给用户）
    → code_gen_accept（用户接受，Tab 采纳）
    → code_gen_canceled（用户忽略/取消）
```

**核心指标**：

| 指标 | 计算方式 | 含义 |
|------|---------|------|
| **触发率** | shown / request | 触发后能成功展示补全建议的比率 |
| **接受率（Accept Rate）** | accept / shown | 展示的补全建议被用户采纳的比率，是代码补全体验的核心指标 |
| **取消率** | canceled / shown | 展示后被忽略/取消的比率 |
| **补全 DAU** | `COUNT(DISTINCT user_id) WHERE event_name = 'code_gen_shown'` | 使用过代码补全的日活用户数 |

**分析维度**：`dwd_trae_ai_cue_event_di` 支持按 `programming_language`（编程语言）、`model_name`（模型）、`trigger_type`（触发方式）、`result_type`（补全结果类型）、`is_comp_fusion`（是否融合补全）切分分析。

**注意**：
- 补全事件表（`dwd_trae_ai_cue_event_di`）与 AI Chat 行为表（`event_di`、`delta_di`）是独立的数据链路。补全事件表记录的是编辑器内的自动补全行为，不包含 Chat 对话
- DWD 行为表中的 `code_gen_shown_cnt` / `code_gen_accept_cnt` / `code_gen_canceled_cnt` 是从 `dwd_trae_ai_cue_event_di` 聚合而来，粒度为 message 级别。如需事件级别的明细分析（如按语言、模型切分），应直接使用 `dwd_trae_ai_cue_event_di`

### 3.5.5 用户情感与对话流转评估

TRAE 通过模型对每条用户消息进行自动评估打标，结果存储在 `dwd_trae_message_model_bench_tags` 表的 `model_pred` JSON 字段中。包含两个独立评估维度：

**1. 情感分析（sentiment）** — 评估用户是否在辱骂或称赞 AI

| sentiment_label | 含义 |
|-----------------|------|
| `辱骂` | 用户对 AI 表达不满、使用攻击性语言 |
| `称赞` | 用户对 AI 表达满意、正面评价 |
| `其他` | 中性表达（占绝大多数，>98%） |

**2. 对话流转评估（conv_flow）** — 评估 Agent 解决问题的效率和质量

| conv_flow_label | 含义 |
|-----------------|------|
| `原地踏步` | Agent 反复执行相同或相似的操作，没有实质性进展（如循环修改同一段代码、反复运行失败的命令） |
| `打补丁` | Agent 在不断修复问题，但方式是打补丁式的，未从根本上解决（如修了 A 引发 B，再修 B 又引发 C） |
| `流畅` | Agent 的对话和操作流畅，能高效解决问题 |
| `其他` | 不属于以上明确类别 |

每个标签都附带一个概率分数（scores，0~1），label 取概率最高的标签。详细的 JSON schema、查询方式和样本数据见 `dwd_trae_message_model_bench_tags.md`。

**与其他反馈数据的关系**：
- `dwd_trae_message_model_bench_tags`（本节）：模型自动评估，覆盖所有消息
- `dwd_trae_message_feedback_di`：用户主动反馈（点赞 `is_positive_feedback` / 点踩 `is_negative_feedback`），仅覆盖用户主动操作的消息
- DWD 行为表的 `is_like` / `is_dislike` / `is_revert`：与 feedback 表同源，分别表示点赞、点踩、回退操作

## 4. 数据流分层

```
ODS（原始数据层）
  → DWD（明细数据层，Dorado 任务调度生产）
    → Gallery 数据源 SQL（引用 DWD 表，定义指标计算逻辑）
      → Gallery 上线后自动生成 Dorado 任务链路（stg_ → rpt_ → mds_ → calc_）
        → Libra 指标（挂载到实验报告，用于 A/B 实验分析）

Fornax 在线 Trace（链路追踪数据）
  → trae_agent_fornax_detail_di（ODS 天级表，Span 级原始数据）
    → trae_traj_detail_di（Trajectory 详情表，Agent 分析核心）
    → trae_conversation_message_map_di（会话-消息映射）
    → trae_message_traj_map_di（消息-轨迹映射）
```

- **ODS**：原始操作数据，由埋点或日志直接写入。
- **DWD**：经过清洗、标准化的明细宽表，由 Dorado 任务调度生产。
- **Gallery 数据源**：基于 DWD 表编写 SQL，通过 `Tx:column` 语法声明字段，供指标组使用。
- **Gallery 自动生成任务**：指标组上线后，Gallery 平台自动创建一系列 Dorado 任务和 Hive 表，完成从数据源到最终指标报告的全链路计算（详见下方 §5）。
- **Libra 指标**：最终呈现在实验报告中的指标，由 Gallery 指标组提供数据支撑。
- **Trajectory（轨迹）系列**：从 Fornax Trace 数据中提取加工的离线表体系，是分析 Agent 行为、模型调用效率、工具使用的核心数据源（详见 §2.2）。

## 5. Gallery 指标上线后自动生成的 Dorado 任务链路

Gallery 指标组上线后，平台会自动生成两套 Dorado 任务链路（无需手动创建），所有任务和表命名均带有指标组相关的前缀标识：

### 5.1 整体架构

```
输入源：
  ├── 原始实验数据（多个 AB 实验日志表，用户级实验分组记录）
  └── 业务指标数据（DWD 表，即 Gallery 数据源 SQL 引用的表）

链路一：Daily 链路（天级统计 + 置信度）
  stg_cuped_daily → rpt_daily → calc_confidence_daily

链路二：CUPED ALL 链路（全量累计 + CUPED 方差缩减 + 置信度）
  stg_cuped_daily → stg_cuped_all → stg_2week_all → mds_cuped_all → rpt_cuped_all → calc_confidence_cuped_all
```

### 5.2 各节点详解

| 节点 | 层级 | 功能 | SQL/脚本逻辑 |
|------|------|------|-------------|
| **stg_cuped_daily** | 用户·实验组·天级 | 合并实验日志 + 关联业务指标，聚合为用户天级指标 | UNION ALL 合并多个实验日志 → LEFT JOIN 业务指标数据 → GROUP BY 聚合用户天级指标 |
| **rpt_daily** | 实验组·天级报表 | 天级指标报表，按 vid 聚合 | GROUP BY vid 聚合 → SUM/AVG 计算统计量 → 协方差和平方和计算 |
| **calc_confidence_daily** | 天级置信度 | 计算天粒度的 p-value 和置信区间 | Python 脚本：基于统计量计算日粒度置信区间 + p-value 显著性检验 |
| **stg_cuped_all** | 用户·实验组级累计 | 当日增量 + 历史存量滚动累计 | FULL OUTER JOIN（当日增量 + 历史数据）→ SUM 滚动累加所有指标 |
| **stg_2week_all** | 用户级2周滑动窗口 | 实验前2周的用户行为数据（用于 CUPED 协变量） | SUM 聚合过去14天 → UNION ALL 合并历史数据 → 滑动窗口累计计算 |
| **mds_cuped_all** | 用户级 CUPED 宽表 | 将实验期数据与实验前2周数据拼接为 CUPED 宽表 | LEFT OUTER JOIN（实验期数据 + 实验前2周数据）→ COALESCE 空值处理 |
| **rpt_cuped_all** | 实验组级 CUPED 报表 | 按 vid 聚合，计算 CUPED 所需的统计量 | GROUP BY vid → SUM 计算 pre/post 指标总和 → AVG 计算平方均值 → 协方差矩阵计算 |
| **calc_confidence_cuped_all** | CUPED 置信度 | 最终 CUPED 调整后的置信区间 | Python 脚本：CUPED 调整 → 计算方差减少效果 → 最终置信区间 |

### 5.3 自动生成任务的表前缀约定

| 前缀 | 含义 | 数据层级 |
|------|------|----------|
| `stg_` | Staging（中间层） | 用户级或用户·实验组级的中间聚合数据 |
| `rpt_` | Report（报表层） | 按实验组（vid）聚合的报表数据，包含统计量 |
| `mds_` | Model Data Store（模型层） | CUPED 等模型计算所需的宽表数据 |
| `calc_` | Calculation（计算层） | Python 脚本任务，执行置信度计算、CUPED 调整等统计分析 |

> **注意**：这些 stg_/rpt_/mds_/calc_ 表和 Dorado 任务由 Gallery 平台自动管理，一般不需要手动修改。排查指标问题时，应优先从 Gallery 数据源 SQL 和 DWD 底表入手，而非直接修改这些自动生成的任务。

### 5.4 CUPED 简介

CUPED（Controlled-experiment Using Pre-Experiment Data）是一种方差缩减技术，利用实验前的用户行为数据（协变量）减小实验指标的方差，从而提高 A/B 实验的检测灵敏度。Gallery 自动生成的 CUPED 链路会：
1. 收集实验前2周的用户行为数据（`stg_2week_all`）
2. 与实验期数据拼接为宽表（`mds_cuped_all`）
3. 按实验组聚合并计算协方差矩阵（`rpt_cuped_all`）
4. 通过 Python 脚本进行 CUPED 调整，输出调整后的置信区间（`calc_confidence_cuped_all`）

## 6. 指标验证方法论

当需要验证 Libra 指标组的数据正确性时，推荐按以下分层方法操作：

### 6.1 数据链路追溯

```
Libra 指标报告
  ← Gallery 指标组（定义指标计算逻辑：left/right key_sql、PV/UV/PV 类型）
    ← Gallery 数据源 SQL（引用 DWD 表、定义 JOIN 逻辑和过滤条件）
      ← DWD 底表（由 Dorado 任务生产，T+1 更新）
        ← ODS 原始数据（埋点/日志写入）
```

验证时**自上而下**逐层排查：先确认指标定义是否正确，再检查数据源 SQL 的 JOIN 逻辑，最后验证底表数据。

### 6.2 验证工具选择

| 层级 | 验证工具 | 关键命令 |
|------|---------|---------|
| Libra 指标报告 | bytedance-libra | `bytedcli libra experiment report --flight-id <id> --metric-group <group_id>` |
| Gallery 指标定义 | libra-gallery-builder | `metrics <ticket_id> <group_index>`、`datasource-sql <ticket_id> T1` |
| DWD 底表 | bytedance-hive | `bytedcli hive detail <db> <table>` |
| Dorado 任务 SQL | bytedance-dorado | `bytedcli dorado task get <task_id> --region cn` |
| 数据验证 | bytedance-tqs | `bytedcli tqs execute --sql "验证 SQL"` |

### 6.3 独立验证 SQL 的构造模式

```sql
WITH ab_users AS (
    -- 从 Libra 标准进组口径表获取实验用户
    SELECT CAST(version_id AS BIGINT) AS vid, user_unique_id AS did
    FROM origin_log.dwd_abtest_vid_log_other_apps_df
    WHERE date >= '<start_date>' AND date <= '<end_date>'
      AND app = 'trae_cn'
      AND CAST(version_id AS BIGINT) IN (<vid_v0>, <vid_v1>)
    GROUP BY CAST(version_id AS BIGINT), user_unique_id
),
data_source AS (
    -- 复现 Gallery 数据源 SQL 的核心逻辑（简化版）
    SELECT did, <指标字段1>, <指标字段2>, ...
    FROM <DWD表> ...
    GROUP BY did
)
SELECT
    CASE WHEN u.vid = <vid_v0> THEN 'v0' ELSE 'v1' END AS version,
    <SUM/COUNT_DISTINCT 聚合指标>
FROM ab_users u
LEFT JOIN data_source d ON u.did = d.did
GROUP BY version
```

### 6.4 圈 Query 验证

Libra 实验报告中的「圈 query」是按维度值筛选子人群后查看实验指标的功能。Libra 平台会自动从 Gallery 生成的 `mds_*_cuped_all` 表中聚合数据（含 CUPED 统计量），但独立验证时**不需要**读取这些自动生成的表。

**独立验证圈 query 的方法**：在 §6.3 的标准验证 SQL 基础上，增加维度筛选条件即可。

```sql
WITH ab_users AS (
    -- 同 §6.3，从进组口径表获取实验用户
    SELECT CAST(version_id AS BIGINT) AS vid, user_unique_id AS did
    FROM origin_log.dwd_abtest_vid_log_other_apps_df
    WHERE date >= '<start_date>' AND date <= '<end_date>'
      AND app = 'trae_cn'
      AND CAST(version_id AS BIGINT) IN (<vid_v0>, <vid_v1>)
    GROUP BY CAST(version_id AS BIGINT), user_unique_id
),
user_tags AS (
    -- 从维度表获取 message_tags（按 did 去重，防御性兜底空值）
    -- cn: flow_aipaas.dwm_trae_user_message_tags_di
    -- i18n: cloudide.dwm_trae_user_message_tags_di
    SELECT did AS user_unique_id,
           MAX(COALESCE(message_tags, ARRAY())) AS message_tags
    FROM flow_aipaas.dwm_trae_user_message_tags_di
    WHERE date >= '<start_date>' AND date <= '<end_date>'
    GROUP BY did
),
data_source AS (
    -- 复现 Gallery 数据源 SQL 的核心逻辑
    SELECT did, <指标字段>, ...
    FROM <DWD表> ...
    GROUP BY did
)
SELECT
    CASE WHEN u.vid = <vid_v0> THEN 'v0' ELSE 'v1' END AS version,
    <SUM/COUNT_DISTINCT 聚合指标>
FROM ab_users u
LEFT JOIN data_source d ON u.did = d.did
LEFT JOIN user_tags t ON u.did = t.user_unique_id
WHERE array_contains(t.message_tags, '<圈选的标签值>')  -- 维度筛选
GROUP BY version
```

**维度来源**：
- `message_tags`（模型名/行为特征标签）→ 从 `dwm_trae_user_message_tags_di` 获取（cn: `flow_aipaas`，i18n: `cloudide`）。该表 `message_tags` 字段为 `array<string>` 类型，已按 did 聚合为当日去重标签集合，圈选时使用 `array_contains` 筛选
- `is_new`（新老用户）等其他维度 → 从 Gallery 数据源 SQL 中复现计算逻辑（通常基于进组表的 `enter_date` / `min_date` 判断）

**注意**：独立验证计算的是裸指标（不含 CUPED 校正），与 Libra 报告中经过 CUPED 调整的 Diff% 可能有 0.1~0.5pp 偏差，但方向和量级应一致。

### 6.5 常见陷阱

1. **口径差异**：Gallery 数据源可能对同一底表有不同的 JOIN 路径和过滤条件（如 token 和 cost 分别从不同表获取）。`dwd_trae_chat_model_cost_di` 已包含所有 status（含 fail），但仍排除 `request_type = 'custom'`；而 `dwd_resource_prompt_completion_di` 在 Gallery SQL 中额外按 `model_usage = 'chat_completion'` 过滤。验证时需严格复现原始 SQL 逻辑
2. **敏感列权限**：TQS ad-hoc 查询的个人账号可能缺少某些敏感列的访问权限（如 `request_metadata`），Gallery 的 Dorado 调度使用服务账号不受影响
3. **CUPED 校正**：Libra 报告中的 Diff% 经过 CUPED 方差缩减调整，TQS 独立计算的 Diff% 与之可能有 0.1~0.5pp 偏差，但方向应一致
4. **日期范围**：Libra 的 `sum` 模式（日均）和 `total` 模式（累计）的日期范围可能不同于 TQS 查询的范围，对比时需注意对齐

