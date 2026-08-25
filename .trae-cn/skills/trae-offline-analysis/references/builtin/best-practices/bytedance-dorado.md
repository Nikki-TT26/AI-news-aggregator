# bytedance-dorado 最佳实践

离线批处理任务管理。

## 命令速查

| 操作 | 命令 |
|------|------|
| 列出任务 | `bytedcli dorado task list --project-id <projectId> [--task-name <name>] [--region <region>]` |
| 获取任务详情 | `bytedcli dorado task get <taskId> [--region <region>]` |
| 创建 HSQL 任务 | `bytedcli dorado task create --project-id <projectId> --folder-id <folderId> --name <name> [--type hsql] [--query "SQL"] [--region <region>]` |
| 更新 SQL | `bytedcli dorado task update <taskId> --query "SQL" [--region <region>]` |
| 比较草稿与线上版本 | `bytedcli dorado task diff <taskId> [--region <region>]` |
| 部署上线 | `bytedcli dorado task online <taskId> --project-id <projectId> [--message "msg"] [--region <region>]` |
| 即席查询 | `bytedcli dorado adhoc exec "SQL" [--task-id <taskId>] [--region <region>]` |

> **region 参数**：国内任务无需指定（默认 `cn`），海外任务需加 `--region sg`。
>
> **注意**：`task get`、`task update`、`task diff` 不需要 `--project-id`，只需 `taskId`（+ 可选 `--region`）。`task list`、`task create`、`task online` 需要 `--project-id`。

## 项目 ID 映射

| 环境 | 项目名 | 项目 ID（`--project-id` 参数值） | 说明 |
|------|--------|---------|------|
| cn（国内） | trae_analysis | `11253` | 默认国内项目，大部分表的 Dorado 任务在此项目下 |
| sg（海外） | — | `300004344` | 海外主项目，大部分海外表的 Dorado 任务在此 |
| sg（海外） | — | `300004442` | 海外辅助项目（`dwd_trae_ai_behavior_event_di`、`dim_trae_chat_tool_group`、`dwd_trae_message_feedback_di`、`dwd_trae_chat_model_cost_di`、`ods_trae_model_price` 等） |

> **ID 格式说明**：Dorado 平台 URL 和资产文件中使用 `cn_11253`、`sg_300004442` 等带前缀的格式，其中前缀表示 region（`cn` 或 `sg`），下划线后的数字才是 `--project-id` 参数值。例如 `cn_11253` → `--project-id 11253`（region 默认 cn 可省略）；`sg_300004442` → `--project-id 300004442 --region sg`。
>
> 具体每张表的 Dorado 任务归属哪个项目，详见 `references/builtin/assets/index.md` 中每个表 section 的「Dorado 任务」行。

## 任务链接格式

当需要向用户展示 Dorado 任务的 Web 链接时，使用以下格式：

| 环境 | 链接格式 | 示例 |
|------|---------|------|
| cn（国内） | `https://data.bytedance.net/dorado/development/node/{taskId}?project=cn_{projectId}` | `https://data.bytedance.net/dorado/development/node/124651725?project=cn_11253` |
| sg（海外） | `https://dataleap-sg.tiktok-row.net/dorado/development/node/{taskId}?project=sg_{projectId}` | `https://dataleap-sg.tiktok-row.net/dorado/development/node/305610838?project=sg_300004442` |

> **注意**：链接中的 project 参数需要带 region 前缀（`cn_` 或 `sg_`），与 `--project-id` CLI 参数（纯数字）不同。

## 根据任务名定位 taskId 的流程

1. 若知识库 assets 索引中已有该表/任务的记录 → 直接取 taskId，用 `task get <taskId>` 获取详情（海外加 `--region sg`）
2. 若不在知识库中 → 用 `task list --project-id <projectId> --task-name <taskName>` 按名称搜索（海外加 `--region sg`）
3. 搜索到 taskId 后 → 用 `task get <taskId>` 获取完整详情（包括 SQL 代码、调度配置、依赖关系、上线状态等）

## 典型工作流：修改已有任务 SQL

1. **获取当前 SQL**：`bytedcli dorado task get <taskId> [--region sg] --json`，从 JSON 响应中提取 `data.conf.configuration.operator.parameter.code` 字段
2. **修改 SQL**：将原始 SQL 保存到临时文件，用脚本做字符串替换生成新 SQL
3. **提交草稿**：`bytedcli dorado task update <taskId> --query "$(cat /tmp/new.sql)" [--region sg]`
4. **验证草稿**：`bytedcli dorado task diff <taskId> [--region sg]` 对比草稿与线上版本的差异
5. **等待用户确认上线**：向用户展示 diff 结果，**询问用户是否需要上线**，只有用户明确要求时才执行下一步
6. **部署上线**（用户确认后）：`bytedcli dorado task online <taskId> --project-id <projectId> --message "变更说明" [--region sg]`

> **长 SQL 传参技巧**：SQL 较长时，先写入临时文件再用 `--query "$(cat /tmp/file.sql)"` 传入，避免 shell 参数截断。

## 约定

- **默认不上线**：修改 SQL 后默认只提交草稿（draft），**不自动执行上线（online）**。只有当用户明确表示"上线"、"部署"、"online"、"发布"时，才执行 `task online` 命令。修改完成后应向用户展示 diff 并询问是否上线
- 任务命名规范：任务名 = 输出表名，保持一一对应
- 配置好依赖关系，推荐使用依赖推荐
- 调度时间规范：一般安排在每日 00:00
- 默认使用国内项目 `11253`，海外任务需指定对应的海外项目 ID 和 `--region sg`