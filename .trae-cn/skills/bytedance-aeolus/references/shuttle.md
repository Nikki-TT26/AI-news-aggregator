# Shuttle 合规查询指南

## 目录

- [定位：Shuttle 解决什么问题](#定位shuttle-解决什么问题)
- [核心概念](#核心概念)
- [数据通道与边界](#数据通道与边界)
- [标准取数流程](#标准取数流程)
- [SQL 合规要求](#sql-合规要求)
- [US 与 EU 的区域差异](#us-与-eu-的区域差异)
- [Agent 决策规则](#agent-决策规则)
- [官方资料](#官方资料)

## 定位：Shuttle 解决什么问题

Shuttle 是 Texas（US Data Security）与 Clover 数据主权约束下的合规数据查询平台，不是一个绕过合规限制的通用 SQL 网关。

它把以下能力串成一条可审计链路：

1. 对 SQL 模板、查询字段、`detection_uv` 血缘和查询方式执行合规分析。
2. 将 TTP 查询结果与已审批的 DECC Data/schema 绑定，校验输出字段的业务语义、字段名和类型。
3. 按数据分类选择合规通道，执行阈值保护、差分隐私、假名化或拒绝传输。
4. 支持 Hive、ClickHouse、RDS 等数据源，以及 US-TTP、EU-TTP、VA、SG 等数据区域的结果查询与汇总。
5. 将审批、执行、结果导出、例行数据集和 Aeolus 可视化纳入同一合规与审计边界。

因此，Agent 应把 Shuttle 理解为“合规策略 + DECC 声明 + SQL 模板 + 区域执行”的组合，而不是“选一个 region 直接跑 SQL”。

Shuttle 的 HTTP 控制面只在 VA。`-r va` 选择控制面；`--shuttle-region` 选择模板 `infos` 中的任务数据区域。US、EU、EU-TTP 或 EU-TTP2 数据都通过 VA 控制面发起，但仍在各自的数据区域和合规规则下执行。

全局 `--site` 选择调用者的身份与权限上下文，例如 `--site us-ttp-bdee`；它不替代 `-r va`，也不决定任务数据区域。默认从 office 网络访问 `aeolus-va.tiktok-row.net`，只有 office host 明确不可达时才设置 `BYTEDCLI_NETWORK_PROFILE=prod`。不要仅因为目标数据在 US-TTP 或 EU-TTP 就切到 prod。

## 核心概念

| 概念                           | 含义                                                                                      | Agent 应如何处理                                                                             |
| ------------------------------ | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Tenant / Project               | Shuttle 自己的隔离单元；与普通 Aeolus project 不是同一个概念，不同项目的 SQL 模板相互隔离 | 先用 `project list` 找到当前用户有权限的项目，不猜项目 ID                                    |
| Data Center / task data region | SQL 实际读取数据的区域，例如 `US`、`EU`、`EU-TTP`、`EU-TTP2`、`VA`、`SG`                  | 从 `template.infos` 读取精确 key；多区域模板显式传 `--shuttle-region`                        |
| Shuttle control plane          | `/shuttle/web/api/v1` 的 API 入口                                                         | 始终使用 `-r va`；不要把 `-r` 当成数据区域                                                   |
| DECC Data Type                 | 数据互通通道，主要包括 Aggregated Data、Default Data，以及经批准的 On Demand 特殊场景     | 按数据语义选通道，不按 SQL 是否使用 `GROUP BY` 猜通道                                        |
| DECC Data / schema             | 对允许传输字段的业务语义、名称和类型的审批声明                                            | TTP 查询的最终 SELECT 字段必须与已审批 schema 一致                                           |
| Template                       | 经过合规检查并绑定 DECC 信息的 SQL 定义                                                   | 只有已批准模板才能执行；修改 SQL 后重新走校验/审批                                           |
| `detection_uv`                 | 聚合用户数据在最细分组下的独立用户保护计数                                                | 必须来自真实用户标识的去重血缘，不能用常量、行数或无关 DAU 模拟                              |
| YARN queue                     | Hive 任务的执行资源                                                                       | 从 `queue get` 返回的 `queues.<REGION>` 取 cluster/queue，区域必须与 `--shuttle-region` 相同 |

## 数据通道与边界

### Aggregated Data

当查询涉及受保护用户数据、用户行为或与用户明细关联的数据时，使用 Aggregated Data 通道。

基本要求：

- 结果只能以合规聚合形式传出，不能包含 `user_id`、`device_id` 等用户明细。
- 每个最细维度组合下的每一行都必须满足适用的 `detection_uv` 规则；换一个维度不能规避阈值。
- `detection_uv` 应表达与指标直接相关的独立用户数，例如 `COUNT(DISTINCT uid) AS detection_uv`。
- CTR、CVR 等由多类用户行为组成的指标，应覆盖公式中每类行为的独立用户保护要求，通常使用相关 UV 的最小值作为保护口径。
- 结果字段名、字段类型和业务语义必须与选定的 DECC schema 一致。

### Default Data

Default Data 用于经批准的单条数据互通，包括用户公开数据、互操作数据、非用户数据以及其他被认定为豁免的数据。

需要特别区分：

- “Default”不等于“无需合规判断”。是否允许传输取决于数据分类、用途和 DECC 声明。
- SQL 是否聚合并不决定通道。非用户数据即使做 `COUNT` 也可能仍走 Default Data；一旦与受保护用户明细关联，通常应转为 Aggregated Data。
- 删除 `uid` 或做简单去标识化，不会自动把受保护明细变成豁免数据。
- EU 数据在 ROW 展示时还可能受假名化规则保护。

### On Demand 特殊豁免

Test Account、Carved-Out Creator 等特殊场景只有在满足对应定义、审批和打标规则时，才能使用 On Demand 能力。Agent 不得仅凭用户描述自行认定豁免，也不得通过修改 SQL 或通道名绕过审批；不确定时应让用户咨询 PDPO、USDS 或 GSO。

### 绝对边界

- US/EU 受保护数据不能因为使用 Shuttle 就被非授权人员访问或传到 ROW。
- 聚合通道不得传出 UID 等用户明细。
- 结果不能通过 Lark、会议共享、录屏、Excel 等非合规路径转交给无权限人员；下载成功不代表可以自由再分发。
- 用户坚持查询疑似不合规数据时，停止构造规避方案，转向合规团队确认。

## 标准取数流程

1. 用 `project list -r va` 发现有权限的 Shuttle project。
2. 用 `template search/get -r va` 检查模板的 `taskType`、`dataSource`、`engine`、`infos`、DECC Data Type、DECC schema 和参数。
3. 判断数据属于 Aggregated Data、Default Data 还是已批准的 On Demand 场景；不要仅凭 SQL 形态判断。
4. 从 `template.infos` 选择任务数据区域。单区域可推导，多区域必须显式传 `--shuttle-region`。
5. Hive 查询用 `queue get -r va --project-id ...` 获取所选区域下的 YARN cluster/queue。
6. 编写 SQL，并保证最终输出字段与 DECC schema 的字段名、类型和语义完全一致。
7. Aggregated Data SQL 使用有真实血缘的 `detection_uv`，并在最细粒度分组下满足适用保护规则。
8. 提交模板合规校验。`Normal` 风险可自动进入执行；`Warning` 或无法自动批准的模板需要申诉或人工审批。只有批准后的模板才能运行。
9. 用 `task submit` 发起任务，用 `task get` 轮询，用 `task result` 预览；完整结果用 `task download`，并保持 `--shuttle-region` 与任务 `infos` key 一致。
10. 对 BATCH 多日任务，在 SQL 中保留 `${date}`，通过 `--start-date` / `--end-date` 让 Shuttle 服务端逐日展开。

## SQL 合规要求

### 正确模式

```sql
SELECT
  country_code,
  COUNT(DISTINCT uid) AS detection_uv,
  COUNT(*) AS event_cnt
FROM sample_db.sample_user_events
WHERE date = '${date}'
GROUP BY country_code
```

这只是结构示例。实际 SQL 仍必须使用已审批的数据源、字段与 DECC schema，并按指标语义选择正确的 `detection_uv`。

### 禁止模式

以下写法会被视为 mock `detection_uv`、无有效血缘或试图绕过保护规则：

```sql
SELECT 1001 AS detection_uv;
SELECT SUM(1001) AS detection_uv;
SELECT COUNT(*) AS detection_uv;
SELECT RAND() * 1000 AS detection_uv;
SELECT SUM(event_cnt) + 1000 AS detection_uv;
```

也不要：

- 用与目标行为无关的 App DAU 代替当前指标的真实独立用户数。
- 用 `MAX(user_id)`、拼接 `user_id` 等方式把受保护明细藏进聚合结果。
- 让最终 SELECT 字段名或类型偏离 DECC schema。
- 将不同数据主体混合后只满足其中一类主体的保护规则。

## US 与 EU 的区域差异

| 区域    | 官方文档描述的主要保护方式                                                                 | Agent 注意事项                                                     |
| ------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| US-TTP  | 聚合数据以独立美国用户阈值保护；文档主体多处写作 `detection_uv > 1000`                     | 不要用常量或无关 UV；每个最细分组单独判断                          |
| EU-TTP  | 聚合数据可使用差分隐私；文档描述 `detection_uv > 20`，低于阈值的结果置 0，并受隐私预算约束 | 结果可能被加噪；相近查询不能被用来反推精确值                       |
| VA / SG | 官方说明普通查询不需要绑定 TTP 的 DECC Data，也不走同一模板审批要求                        | 仍需遵守数据来源本身的权限与分类，不要把 ROW 查询当成 TTP 规避路径 |

官方文档对 US 边界值同时出现过 `> 1000` 与 `>= 1000` 两种写法。Agent 不应自行裁决边界，也不应在客户端复制一套可能过期的阈值判断；以当前 Shuttle 合规引擎、已审批模板和合规团队确认结果为准。

## Agent 决策规则

1. 用户提到 Shuttle、TTP 取数、DECC、合规 SQL、`detection_uv`、跨区域数据结果或多机房合并时，先读本文件，再构造命令。
2. 始终把控制面和任务数据区域分开：`-r va` + `--shuttle-region <template.infos key>`。
3. 先发现 project/template/queue，再使用 ID、region、cluster 和 queue；不猜真实业务标识。
4. 需要临时 SQL 且不涉及 Shuttle project/template/DECC 时，优先考虑 Query Editor；涉及 TTP 合规输出时使用 Shuttle。
5. 任何“把明细拿出来”“调低/伪造 UV”“换维度绕阈值”“借有权限的人导出再转发”的请求都应停止并解释合规边界。
6. `task submit`、`template create/delete/move` 和 `folder create/delete/move/rename` 会改变远端状态；只有用户明确要求执行相应写操作时才调用。只读排查优先使用 `project list`、`template search/get`、`queue get`、`task get/result`。
7. 本文件是官方文档的操作摘要，不替代实时政策。规则冲突、豁免或阈值边界不清时，以官方文档、Shuttle 合规引擎和 PDPO/USDS/GSO 的确认结果为准。

## 官方资料

- [Shuttle 合规取数 One Pager](https://bytedance.sg.larkoffice.com/docx/BIWnd0wW7o4BjQxUQ4YlUfJfgmb) — 本指南的主要来源；读取版本 `revision_id=7542`，读取日期 2026-07-24。
