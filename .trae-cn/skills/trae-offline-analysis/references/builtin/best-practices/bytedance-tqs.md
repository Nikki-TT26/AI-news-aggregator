# bytedance-tqs 最佳实践

SQL 校验与执行引擎。

| 操作        | 命令                                                                                                          |
| --------- | ----------------------------------------------------------------------------------------------------------- |
| 校验 SQL 语法与权限 | `bytedcli tqs analyze --sql "SQL"`                                                                          |
| 同步执行 SQL  | `bytedcli tqs execute --sql "SQL"`（阻塞等待结果）                                                                  |
| 异步提交      | `bytedcli tqs submit --sql "SQL"` → `bytedcli tqs wait --job-id <id>` → `bytedcli tqs result --job-id <id>` |

## Auto analyze（自动语法校验）

新版 bytedance-tqs 中，`tqs submit` 和 `tqs execute` **默认在提交前自动执行 SQL analyze**：

- analyze 失败时直接报错退出，**不会继续提交任务**——这解决了之前 Agent 经常忘记手动 `tqs analyze`、直接 `tqs submit` / `tqs execute` 后遇到不明确报错的问题
- **禁止使用 `--skip-analyze`**。如果 analyze 报错，应根据错误信息修正 SQL 或解决权限问题，而不是跳过校验。即使遇到 `Object not found` 错误，也应先确认表名拼写、检查 APP 可见性，而非直接跳过
- 独立使用 `tqs analyze` 仍然有效，适用于只想做语法/权限预检而不执行查询的场景

> **影响**：编排层的「先 analyze 再 execute」流程现在可以简化——直接调用 `tqs execute` 即可获得 analyze 保护。但对于需要精确解读 analyze 错误信息（如区分表级 vs 列级权限问题）的场景，仍建议先独立运行 `tqs analyze` 以获取更清晰的错误诊断。

## 环境变量配置（首次使用）

TQS 需要 `TQS_APP_ID` 和 `TQS_APP_KEY` 凭证。凭证文件存放在**项目根目录**下：

- `.env.local` — 国内凭证
- `.env.sg.local` — 海外 SG 凭证

> **不依赖 bytedcli 自动加载 `.env`**。凭证放在项目根目录下，通过 **source** 或**命令行前缀**方式显式加载，避免 subagent 执行时 cwd 不确定导致凭证加载错误。

## 国内/海外多凭证管理

国内和海外机房使用**不同的 TQS APP**，需要分别申请凭证。由于 TQS 只认 `TQS_APP_ID` / `TQS_APP_KEY` / `TQS_CLUSTER` 三个变量名，无法像 Aeolus 那样按 region 前缀区分，推荐以下方式管理：

1. `.env.local` 文件存放**国内默认凭证**（位于项目根目录 `.env.local`）：

```bash
export TQS_APP_ID=sa:your_cn_app_id
export TQS_APP_KEY=your_cn_app_key
```

2. `.env.sg.local` 文件存放**海外 SG 凭证**（位于项目根目录 `.env.sg.local`）：

```bash
export TQS_APP_ID=your_sg_app_id
export TQS_APP_KEY=your_sg_app_key
export TQS_CLUSTER=sg
```

> 两个文件都使用 `export` 前缀，这样 `source` 后变量才能被子进程（bytedcli）读取。

3. 查询时通过 source 显式加载对应凭证：

```bash
# 查询国内表
(source .env.local && bytedcli tqs execute --sql "SELECT ...")

# 查询海外 SG 表
(source .env.sg.local && bytedcli tqs execute --sql "SELECT ...")
```

> `.env.local` 和 `.env.sg.local` 均已加入 `.gitignore`，不会提交到仓库。

### 替代方案 1：`--env-file` 指定凭证文件

新版 bytedance-tqs 支持通过 `--env-file <path>` 指定 .env 文件路径，无需手动 source：

```bash
# 查询国内表
bytedcli tqs execute --env-file .env.local --sql "SELECT ..."

# 查询海外 SG 表
bytedcli tqs execute --env-file .env.sg.local --sql "SELECT ..."
```

> **注意**：`--env-file` 方式解析 `KEY=VALUE` 格式（不需要 `export` 前缀），但 source 方式需要 `export`。两种格式兼容的写法是保留 `export` 前缀（`--env-file` 会自动忽略 `export`）。

### 替代方案 2：`--profile` 多凭证管理

若需在同一个 `.env.local` 文件中管理多套凭证（如国内 + 海外），可使用 `--profile` 机制：

```bash
# 在 .env.local 中配置多套凭证
TQS_APP_ID=sa:your_cn_app_id         # 默认（国内）
TQS_APP_KEY=your_cn_app_key
TQS_PROFILE_SG_APP_ID=your_sg_app_id  # sg profile（海外）
TQS_PROFILE_SG_APP_KEY=your_sg_app_key
TQS_PROFILE_SG_CLUSTER=sg

# 使用
bytedcli tqs execute --sql "SELECT ..."                  # 使用默认凭证（国内）
bytedcli tqs execute --profile sg --sql "SELECT ..."     # 使用 sg 凭证（海外）
```

> **当前编排层仍推荐 source 方式**：因为 source 方式更明确、不依赖单一 .env.local 文件格式，且与现有流程兼容。`--profile` 和 `--env-file` 作为可选替代方案。

4. `TQS_APP_ID` / `TQS_APP_KEY` 的获取方式：在 DataLeap TQS 平台的应用管理中创建或查看应用凭证。国内和海外需分别申请。

## 集群选择

- 国内查询默认不需要配置 `TQS_CLUSTER`，TQS 会自动选择合适的集群和队列
- **查询海外 SG 表时，推荐使用** **`sg`** **集群**（`TQS_CLUSTER=sg`）
- 集群通过环境变量 `TQS_CLUSTER` 指定（命令行前缀或写入 `.env.local`）
- 可用集群列表通过 `bytedcli tqs clusters` 查看

## 国内 TQS 查询完整流程

1. 确认 `.env.local` 已配置（位于项目根目录 `.env.local`，包含 `TQS_APP_ID`、`TQS_APP_KEY`）
2. **语法与权限校验（前置）**：先用 `tqs analyze` 校验 SQL：
   ```bash
   (source .env.local && bytedcli tqs analyze --sql "SELECT ... FROM <cn_db>.<table> WHERE date = 'yyyyMMdd' ...")
   ```
   - 返回 `status: 'AnalysisCompleted'` → 语法正确且有权限，继续执行
   - 返回 `status: 'AnalysisFailed'` + `SqlParseException` → 语法错误，根据 `errorShort` 中的行号/列号提示修正 SQL
   - 返回 `status: 'AnalysisFailed'` + `NoPrivilegeException`（`User ... does not have privileges for QUERY`）→ 权限不足。错误信息精确列出缺少权限的字段：若列出**所有字段** → 无表级权限；若仅列出**部分字段** → 有表权限但缺少这些敏感列的权限。提示用户去 Coral 申请对应权限
   - 返回 `status: 'AnalysisFailed'` + `Object '...' not found` → 表名可能拼错或 APP 对该库无元数据可见性，应先确认表名拼写正确、检查 APP 权限配置，而非跳过 analyze
   > **简化方式**：由于新版 `tqs execute` 已自动包含 analyze，可以跳过步骤 2 直接执行步骤 3。execute 会在提交前自动 analyze，失败时直接报错退出。仅当需要**精确区分权限问题类型**（如表级 vs 列级权限）时，才建议先独立运行 `tqs analyze`。
3. 使用子 shell 执行查询：
   ```bash
   (source .env.local && bytedcli tqs execute --sql "SELECT ... FROM <cn_db>.<table> WHERE date = 'yyyyMMdd' ...")
   ```
4. **注意日期选择**：国内查询使用 **T-1 及之前**的分区

## 海外 TQS 查询完整流程

1. 确认 `.env.sg.local` 已配置（位于项目根目录 `.env.sg.local`，包含 `TQS_APP_ID`、`TQS_APP_KEY`、`TQS_CLUSTER=sg`）
2. 确认 TikTok SSO 已认证（`bytedcli --site i18n-tt auth login`）
3. **语法与权限校验（前置）**：先用 `tqs analyze` 校验 SQL：
   ```bash
   (source .env.sg.local && bytedcli tqs analyze --sql "SELECT ... FROM <sg_db>.<table> WHERE date = 'yyyyMMdd' ...")
   ```
   - 返回 `status: 'AnalysisCompleted'` → 语法正确且有权限，继续执行
   - 返回 `status: 'AnalysisFailed'` + `SqlParseException` → 语法错误，根据 `errorShort` 中的行号/列号提示修正 SQL
   - 返回 `status: 'AnalysisFailed'` + `NoPrivilegeException`（`User ... does not have privileges for QUERY`）→ 权限不足。错误信息精确列出缺少权限的字段：若列出**所有字段** → 无表级权限；若仅列出**部分字段** → 有表权限但缺少这些敏感列的权限。提示用户去 Coral 申请对应权限
   - 返回 `status: 'AnalysisFailed'` + `Object '...' not found` → 表名可能拼错或 APP 对该库无元数据可见性，应先确认表名拼写正确、检查 APP 权限配置，而非跳过 analyze
   > **简化方式**：由于新版 `tqs execute` 已自动包含 analyze，可以跳过步骤 2 直接执行步骤 3。execute 会在提交前自动 analyze，失败时直接报错退出。仅当需要**精确区分权限问题类型**（如表级 vs 列级权限）时，才建议先独立运行 `tqs analyze`。
4. 使用子 shell 执行查询，避免污染当前环境变量：
   ```bash
   (source .env.sg.local && bytedcli tqs execute --sql "SELECT ... FROM <sg_db>.<table> WHERE date = 'yyyyMMdd' ...")
   ```
5. **注意日期选择**：海外查询推荐使用 **T-2 及之前**的分区（详见下方「TQS 查询日期约定」），T-1 分区可能因时差尚未就绪
6. 如果查询报权限错误（如 `Permission denied` 或找不到库/表），**首先排查凭证是否正确加载**：
   - 检查 source 的文件路径是否正确（相对于 cwd）
   - 确认 source 的是 `.env.sg.local` 而非 `.env.local`（国内/海外凭证混用是最常见的错误）
   - 可通过 `(source .env.sg.local && echo $TQS_APP_ID)` 验证变量是否正确加载
   - 如果凭证确认正确但仍无权限，通过 `SHOW DATABASES` 确认 APP 可访问的库列表

> **重要**：国内和海外是**不同的 TQS APP**，权限范围独立管理。执行海外查询时必须显式 source `.env.sg.local`，否则可能误用国内凭证导致查询失败或权限报错。这是之前查询海外表失败的根因——subagent 未正确加载 `.env.sg.local`，导致国内 APP 凭证被用于海外集群查询。

## 日期占位符约定

- Dorado SQL 中使用 `${date}`
- Aeolus SQL 中使用 `{{ ds }}`
- TQS 测试时直接硬编码 `YYYYMMDD` 格式日期

## TQS 查询日期约定

- **国内（cn）**：查 **T-1 及之前**的分区数据（即昨天及更早），T 日分区通常尚未就绪
- **海外（sg）**：查 **T-2 及之前**的分区数据（即前天及更早）。由于时差原因，海外 Dorado 任务调度比国内晚，T-1 分区可能尚未完成写入，查询会超时或返回空
- 示例：今天是 2026-04-15，国内可查 `date = '20260414'`，海外推荐查 `date = '20260413'`

## 权限不足排查与申请

TQS 查询报权限错误时，通常是当前用户对目标 Hive 表/字段权限不足，或 TQS APP 凭证配置有误。

### 快速权限预检：使用 `tqs analyze`

**新版 `tqs execute` / `tqs submit` 已自动包含 analyze 前置校验**（analyze 失败会直接报错退出）。独立使用 `tqs analyze` 做权限预检仍然有效，适用于需要精确解读权限错误信息的场景：

```bash
(source .env.local && bytedcli tqs analyze --sql "SELECT ... FROM <db>.<table> WHERE date = '...' LIMIT 1")
```

analyze 返回的权限错误信息非常精确：
- **`NoPrivilegeException` + 列出所有字段** → 无表级 SELECT 权限，需申请整表权限
- **`NoPrivilegeException` + 仅列出部分字段**（如 `Columns=[content_raw]->action=select`）→ 有表权限但缺少这些敏感列的权限，需额外申请列级权限
- **`Object '...' not found`** → 表名错误或 TQS APP 对该库无元数据可见性（此时应确认表名拼写正确、检查 APP 权限配置）

> **提示**：`tqs analyze` 比 `tqs execute` 更快（不实际执行查询），适合用来快速验证权限是否到位。

### 常见权限错误信息

| 错误关键字 | 含义 | 处理方式 |
|-----------|------|---------|
| `NoPrivilegeException` / `does not have privileges` | 无表级或字段级 SELECT 权限（analyze 阶段即可检出） | 根据列出的字段判断是表级还是列级问题 |
| `Permission denied` | 无表级读权限（execute 阶段报出） | 申请 Hive 表权限 |
| `Table not found` / `Database does not exist` | 库/表不存在或无权限导致不可见 | 先确认库表名拼写，再排查权限 |
| `Authorization failed` / `Access denied` | TQS APP 凭证无效或无权限 | 检查 APP_ID/APP_KEY 是否正确加载 |
| `Object '...' not found`（analyze 阶段） | 表不存在或 APP 无该库的元数据可见性 | 确认表名拼写正确，检查 APP 权限配置 |

### 排查流程

```
查询报权限错误？
├── 0. 先排查 TQS APP 凭证问题（最常见）：
│   ├── 凭证是否正确加载？（source 路径对不对、.env.local vs .env.sg.local 是否混用）
│   ├── 验证：(source .env.local && echo $TQS_APP_ID)
│   └── 凭证确认正确 → 继续下一步
│
├── 1. 用 tqs analyze 快速定位权限问题：
│   (source .env.local && bytedcli tqs analyze --sql "SELECT <fields> FROM <db>.<table> ...")
│   → 返回 NoPrivilegeException + 字段列表 → 直接知道缺哪些权限，进入步骤 2
│   → 返回 AnalysisCompleted → 权限 OK，问题在别处（可能是运行时环境问题）
│   → 返回 Object not found → analyze 无法判断（APP 对该库无元数据可见性），应确认表名拼写正确并检查 APP 权限配置
│
├── 2. 根据报错信息区分权限类型：
│   ├── 报 NoPrivilegeException + 列出所有字段 / Permission denied（无具体字段名）
│   │   → 无表级读权限，去 Coral 申请表级 SELECT 权限
│   │
│   └── 报 NoPrivilegeException + 仅列出部分字段 / Access denied for column
│       → 表权限已有，但这些字段是敏感列，需额外申请字段级权限
│
└── 3. 补充说明：
    ├── 申请表权限时，通常**不包含敏感列**的访问权限。即使表权限申请通过，
    │   查询含敏感列的 SQL（包括 SELECT *）仍可能报字段级权限错误
    ├── 如需访问敏感列，需在 Coral 表详情页**额外申请「列级权限」**
    └── 建议：排查时先用明确的非敏感字段查询（如 SELECT date, ... LIMIT 1），
        确认表级权限正常后，再尝试访问敏感列
```

> **注意**：
> - `SHOW DATABASES` / `SHOW TABLES` 通常不需要表级读权限即可看到库表列表，**能看到表不代表有查询权限**
> - `SELECT *` 会查所有列，如果表中有敏感列且未申请字段级权限，即使有表权限也会报错。排查时建议先用非敏感字段验证表级权限

### 权限申请方式

**1. 通过 Coral 数据地图申请表/列权限**

在 Coral 数据地图中找到目标表，进入表详情页即可查看权限状态并发起申请：

- **国内**：`https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2F{db}%2F{table}%400`
- **海外（SG）**：`https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=alisg&qualifiedName=HiveTable%3A%2F%2F%2F{db}%2F{table}%406#group=alisg`

> 将 `{db}` 和 `{table}` 替换为实际的库名和表名。例如查询 `flow_aipaas.dwd_trae_ai_behavior_info_message_delta_di` 的权限：
> <https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fdwd_trae_ai_behavior_info_message_delta_di%400>

在表详情页可以：
1. 查看当前账号/项目账号对该表的权限状态
2. 申请表级 SELECT 读权限
3. **申请字段级权限**（如需访问敏感列）：选择「列级权限」，勾选需要的敏感列；
4. 查看表的「权限负责人」，可直接联系授权

### 权限申请后验证

申请通过后，直接尝试查询验证权限是否生效：

```bash
# 验证表级权限（用非敏感字段，避免因敏感列权限未申请而报错）
(source .env.local && bytedcli tqs execute --sql "SELECT date FROM <db>.<table> WHERE date = '<latest_date>' LIMIT 1")

# 如果额外申请了敏感列权限，再验证敏感列可查
(source .env.local && bytedcli tqs execute --sql "SELECT <sensitive_col> FROM <db>.<table> WHERE date = '<latest_date>' LIMIT 1")
```