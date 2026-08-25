---
name: bytedance-tqs
description: "Use bytedcli TQS commands to validate Hive SQL, submit async query jobs, poll status, fetch preview results, and download full CSV results. Supports multi-cluster routing via `--cluster`, `--profile`, or automatic `--site` inference (e.g. `--site i18n-tt` → sg_row). Use when tasks mention TQS, Hive SQL syntax check, async SQL execution, polling query jobs, `tqs analyze`, `tqs submit`, `tqs wait`, `tqs result`, `tqs execute`, `TQS_APP_ID`, `TQS_YARN_CLUSTER`, `TQS_YARN_QUEUE`, `--cluster`, or `--profile`."
---

# bytedcli TQS

## 如何调用 bytedcli

推荐：先全局安装一次，后续所有命令直接调用 `bytedcli`。

```bash
# 推荐方式：先全局安装，后续直接调用 bytedcli
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npm install -g @bytedance-dev/bytedcli@latest
bytedcli <command> [options]
```

```bash
# Fallback：仅在无法全局安装时使用 npx 临时执行
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest <command> [options]
```

## When to use

- 对 Hive SQL 做语法检查
- 提交 TQS 查询任务并异步等待结果
- 查询已有 TQS job 的状态
- 获取成功任务的预览结果或下载完整 CSV
- 需要显式指定 YARN cluster / queue，或从环境变量提供默认值

## 前置条件

- 使用通用调用方式：`../references/invocation.md`
- 先完成 `bytedcli auth login`
- 在 `.env` 中提供 TQS 凭证：`TQS_APP_ID`、`TQS_APP_KEY`（如何申请见 [TQS 应用申请](https://bytequery.bytedance.net/docs/tqs/super_app_apply)）
- 可选环境变量：`TQS_CLUSTER`、`TQS_YARN_CLUSTER`、`TQS_YARN_QUEUE`
- 如需管理多套凭证（不同集群使用不同 appId/appKey），可使用 `--profile` 机制（见下文）

> 执行前缀见 `../references/invocation.md`；下面示例直接写 `bytedcli`。

## 凭证 Profile

当需要同时管理多套 TQS 应用凭证时，可以使用 `--profile <name>` 选项。

### 环境变量命名规则

```bash
# 默认凭证（不指定 --profile 时使用）
TQS_APP_ID=xxx
TQS_APP_KEY=xxx
TQS_CLUSTER=cn

# profile "sg" 的凭证
TQS_PROFILE_SG_APP_ID=xxx
TQS_PROFILE_SG_APP_KEY=xxx
TQS_PROFILE_SG_CLUSTER=sg
```

### 使用方式

```bash
# 使用默认凭证查询 CN
bytedcli tqs execute --sql "SELECT 1" --json

# 使用 sg profile 的凭证查询 SG 集群
bytedcli tqs execute --profile sg --sql "SELECT 1" --json
```

- `--profile` 的 name 会被转为大写拼接到环境变量前缀：`TQS_PROFILE_<NAME>_`
- 如果 profile 对应的 key 不存在，会回退到默认 key（`TQS_APP_ID` 等）
- `--profile` 中配置的 `TQS_PROFILE_<NAME>_CLUSTER` 会自动设置集群，无需再传 `--cluster`
- `--cluster` 仍可覆盖 profile 中的集群设置

## 集群路由

### `--cluster` 选项

所有 `tqs` 子命令均支持 `--cluster <cluster>` 通用选项，用于显式指定 TQS 集群：

```bash
# 直连新加坡 TikTok ROW 集群
bytedcli tqs execute --sql "SELECT 1" --cluster sg_row --json

# 直连 VA 集群
bytedcli tqs execute --sql "SELECT 1" --cluster va --json
```

可用集群名称：`cn`, `lq`, `va`, `sg`, `sg_row`, `boe`, `boei18n`, `oci`, `gcp`, `jp_lark`, `sg_lark_adhoc`, 以及各 `*_adhoc` 集群。完整列表：

```bash
bytedcli tqs clusters
```

### `--site` 自动推断

当未显式指定 `--cluster` 和 `TQS_CLUSTER` 时，bytedcli 会根据全局 `--site` 参数自动推断目标 TQS 集群：

| `--site` 值                                          | 推断的 TQS 集群 |
| --------------------------------------------------- | ---------- |
| `cn`（默认）                                            | `cn`       |
| `boe`                                               | `boe`      |
| `i18n-tt`                                           | `sg_row`   |
| `i18n-bd` / `i18n`                                  | `sg`       |
| `us-ttp` / `us-ttp-bdee` / `us-ttp-usts` / `eu-ttp` | `va`       |

```bash
# 使用 --site 自动推断到 sg_row 集群
bytedcli --site i18n-tt tqs execute --sql "SELECT 1" --json

# 等效于
bytedcli tqs execute --sql "SELECT 1" --cluster sg_row --json
```

**优先级**：`--cluster` > `TQS_CLUSTER` 环境变量 > `--site` 自动推断 > 默认 `cn`

## Quick start

```bash
# 查看支持的 TQS clusters
bytedcli tqs clusters

# 只做 Hive SQL 语法检查
bytedcli tqs analyze --sql "SELECT 1"

# 提交查询，拿到 jobId 后异步处理
bytedcli tqs submit --sql "SELECT 1" --json

# 查询任务状态
bytedcli tqs status --job-id <job-id> --json

# 轮询直到任务完成
bytedcli tqs wait --job-id <job-id> --json

# 获取结果预览
bytedcli tqs result --job-id <job-id> --json

# 一步完成提交 + 轮询 + 结果预览
bytedcli tqs execute --sql "SELECT 1" --json

# 下载完整 CSV
bytedcli tqs result --job-id <job-id> --format csv --output ./result.csv

# 查询新加坡 TikTok ROW 集群数据
bytedcli tqs execute --sql "SELECT 1" --cluster sg_row --json
```

## Auto analyze

`tqs submit` 和 `tqs execute` 默认在提交前自动执行 SQL analyze：

- analyze 失败时直接报错退出，不会继续提交任务
- 如需跳过自动 analyze，传 `--skip-analyze`

```bash
# 默认行为：先 analyze 再 submit
bytedcli tqs submit --sql "SELECT 1" --json

# 跳过 analyze 直接提交
bytedcli tqs submit --sql "SELECT 1" --skip-analyze --json
```

## Recommended flow

### Validate only

1. 如果只想确认语法或分析信息，用 `tqs analyze --sql ...`。

### Async job flow

1. 用 `tqs submit --sql ... --json` 提交任务并记录 `jobId`（自动包含 analyze）。
2. 后续需要时，用 `tqs status --job-id ...` 或 `tqs wait --job-id ...` 继续查询。
3. 任务成功后，用 `tqs result --job-id ...` 取预览结果。
4. 如果需要完整结果文件，再用 `tqs result --format csv --output <path>` 下载。

### One-shot flow

1. 如果不需要手动拆分流程，直接用 `tqs execute --sql ...`（自动包含 analyze）。
2. `execute` 会先 analyze，再提交任务，再轮询，最后返回结果预览。
3. 如果只想拿到完整文件，仍然推荐显式使用 `result --format csv --output ...`。

## Yarn options

- `--yarn-cluster <cluster>`：单次查询指定 YARN cluster
- `--yarn-queue <queue>`：单次查询指定 YARN queue
- `TQS_YARN_CLUSTER`：默认 YARN cluster，可不填
- `TQS_YARN_QUEUE`：默认 YARN queue，可不填
- 命令行参数优先级高于环境变量默认值

## Polling behavior

- `tqs wait` / `tqs execute` 默认采用自适应轮询
- 前 `60` 秒每 `10` 秒轮询一次
- 超过 `60` 秒后每 `30` 秒轮询一次
- 默认 `--max-wait` 为 `300` 秒
- 如需覆盖默认策略，可显式传 `--poll-interval <seconds>` 和 `--max-wait <seconds>`

## Result behavior

- `tqs result` / `tqs execute` 只对成功任务返回结果数据
- `sample_data` 是预览数据，不单独返回 CSV 表头
- `with_header` 表示当前解析逻辑是否将 CSV 第一行识别为表头
- 如需完整结果，使用 `--format csv --output <path>` 下载
- 需要机器可读输出时，优先使用 `--json`

## 凭证文件加载

bytedcli TQS 从以下位置加载凭证，优先级从高到低：

1. **进程环境变量**（`TQS_APP_ID`、`TQS_APP_KEY` 等）
2. **当前目录** **`.env`** **文件**（自动解析 `KEY=VALUE` 格式）
3. 可通过 `--env-file <path>` 指定其他 `.env` 文件路径

> 注意：不自动读取 `.env.local`，只读取 `.env`。如需使用 `.env.local`，可通过 `source .env.local && bytedcli tqs ...` 手动注入到进程环境变量。

## References

- `../references/invocation.md`
- `../references/troubleshooting.md`
- [TQS 应用申请](https://bytequery.bytedance.net/docs/tqs/super_app_apply)

