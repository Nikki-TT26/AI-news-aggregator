---
name: bytedance-dorado
description: "Operate Dorado (DataLeap) via bytedcli: projects, tasks, instances, task/node lifecycle, SQL updates and adhoc queries, drafts, dependencies, HPSensors, demand work-item discovery/gates/bindings, deploy packages, validation, notebooks, folders, backfills, DECC, resources, Flink, and Spark History diagnosis. Use for Dorado/DataLeap tasks, demand or work-item relations, submit gates, dependencies, owners, deploy review, HSQL/DTS drafts, notebook debugging, task URLs, instance failures, slow runs, backfills, spark-jar configuration, Flink logs, or DECC."
---

# bytedcli Dorado

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

- Dorado/DataLeap 批处理任务管理
- Dorado 实例失败根因定位（实例日志、log-summary、Megatron app/log-link、Spark History）
- Dorado/TQS/Hive 权限失败定位（`NoPrivilegeException`）以及转 Coral 权限申请
- Dorado 慢任务性能分析（Stages/SQL、shuffle/spill/skew、小文件、资源等待）
- 查看项目、任务、实例列表
- 精确重跑单个 Dorado 实例（`dorado instance rerun` 默认 dry-run，显式 `--yes` 才提交）
- 获取任务详情（包括源/目标数据库信息、SQL 代码、依赖任务 ID）
- 获取任务监控配置（告警规则、基线绑定，`dorado task alarms`）
- 创建 / 更新任务运行监控告警规则（`dorado task alarm-rule create` / `dorado task alarm-rule update`，默认 dry-run，`--yes` 提交）
- 关闭 / 开启 Dorado 任务（`dorado task close` / `dorado task open`）
- 检查补数据 (Backfill) 进展和触发器详情 (`dorado backfill triggers`)
- 以精确稀疏日期驱动回溯 pending draft（`dorado backfill draft create/create-instances/update-instances/list-instances/submit`）
- 下载 Dorado 实例日志（页面态 cookie，`dorado download-instance-log`）
- 获取 notebook 实例“运行结果”JSON（`dorado instance notebook-result`，默认读取 `{taskId}_{instanceId}.ipynb`）
- 创建任务（指定 `--type`）
- Resolve the task-template root folder with `bytedcli dorado task template root-folder get --region <region> --project-id <project-id>`, read a template detail with `bytedcli dorado task template get --region <region> --template-id <template-id> --project-id <project-id>`, then create an HSQL task template with `bytedcli dorado task template create --region <region> --project-id <project-id> --name <template-name> [--description <text>]`. `template create` can also accept `--folder-id <folder-id>` directly; when `--folder-id` is omitted it resolves the template root folder from `--project-id`. The create command posts a template form to the region's Dorado `/develop` endpoint (`type=template`, `subType=hsql`); use placeholder values such as `demo-template`, `12345`, `24680`, and `67890` in examples.
- 转交任务 owner（`dorado task transfer-owner`）
- 更新 SQL 任务（hsql/fsql/stream_sql）的查询（`task update --query`/`--query-file`/`--type`；大 SQL 优先用文件参数，避免 argv 长度限制）
- MySQL->Hive binlog 状态检查与接入（`task binlog status` / `task binlog connect`）
- 通过 ad-hoc query API 执行临时查询（Hive SQL；doris_sql 任务会走 Doris IDE debug），并按 debugId 查看运行日志（`dorado adhoc log`）
- 对比 SQL 版本差异（草稿 vs 发布版本、任意两个版本）
- 安全对比任务版本配置（`task version compare`；只输出白名单字段、依赖变化和脱敏后的 opaque 变化统计）
- 拉取 publish-center 发布包列表（`dorado deploy list`；可选 `--creator` 过滤，支持 `--all-pages` 自动翻页）
- 查看 publish-center 发布包详情（`dorado deploy get`）
- 查看发布包详情里的 DIFF SQL（`dorado deploy diff-sql`）
- 查看任务版本历史
- 浏览项目文件夹结构、查看文件夹下的任务和子文件夹
- 创建子目录（`folder create --parent-uri --name`）
- 查看项目可用的 Yarn 队列（支持按 `--task-type` 过滤）
- 更新任务草稿配置（队列、集群、调度时间等）
- 测试运行任务草稿（debug run）
- 校验 HSQL 任务草稿 / 线上版本语法（`task-draft explain`）
- 校验 DTS 任务 reader SQL 语法（`dts-draft explain`）
- 查询 DTS 元数据（`dorado dts region/database/datasource/table/column ...`），用于任务创建、草稿补全和 agent 自动化 lookup
- 查询 Dorado 项目关联的需求空间、模块和工作项，并检查、绑定或解绑任务需求关系（`task demand search/check/bind/unbind`）
- 根据任务 SQL 获取依赖推荐；推荐项是尚未创建的 HPSensor 时，通过 `task hp-sensor create` 先创建，再重新获取 task ID
- 创建 python/notebook/spark(pyspark) 任务节点，支持创建时指定 Docker 镜像（`node create --type python/notebook/spark --image-name/--image-id`）
- 获取 python/notebook/spark 节点草稿内容（`node get`）
- GCP、EU-TTP2 与 US-TTP（含 `tx` 别名、`us-ttp-bdee`）的 Notebook 草稿由 Jupyter Contents API 读取；CLI 使用现有 ByteCloud Auth 身份换取一次性访问 token，并在请求内存中接收短期 Notebook Cookie 和 `_xsrf`，不依赖本地浏览器 session
- 保存 python/notebook/spark 节点草稿（`node save`）
- 启动 notebook kernel 会话（`node start`，支持 `--restricted`/`--no-restricted`，非 cn region 默认开启合规模式）
- 调试执行 notebook 的单个 code cell（`node debug-cell`，会启动/复用 kernel，并通过 Dorado notebook WebSocket 收集 Jupyter 输出）
- 探测 notebook kernel 是否真正就绪可执行代码（`node kernel-status`，单次探测、无副作用，适合在多次 `debug-cell` 前由调用方自行轮询）
- 提交 python/notebook/spark 节点上线（`node submit` / `node submit-approval`）
- 查看节点生产版本历史（`node history`）
- 恢复草稿到指定生产版本（`node rollback --commit-id`）
- 快捷恢复到最新生产版本（`node rollback --latest`）
- 重命名 IDE 节点 / 任务显示名（`node rename --node-id` / `task rename --node-id|--task-id+--project-id`）
- 移动 IDE 节点到目标父目录 URI（`node move --node-id --parent-uri`，默认 dry-run，确认后加 `--yes`）
- 将 IDE 节点移入回收站（`node delete --node-id|--task-id+--project-id`，默认 dry-run，确认后加 `--yes`）
- 管理 Spark-jar 任务的 Operator 配置（`spark-jar create/get/update`，例如读取/更新 `mainClass`、`params`、`sparkConf`）
- 在仅有 taskId、缺少 nodeUid 时解析 IDE nodeUid（`node resolve-uid`，通过 tree-nodes 的 name+type filter 单路径下钻 + node-relations 校验）
- 查询项目可用镜像列表（`image list`），返回镜像 id + name，用于配置 node 的运行镜像
- **注意**：`node create/get/save/submit` 面向 python、notebook、spark 节点；`node start/kernel-status` 面向 python/notebook kernel，`node debug-cell` 面向 notebook cell；SQL 草稿使用 `task-draft`。`node rename/move/delete/resolve-uid` 按各自文档操作 IDE 节点，其中 `node delete` 的两种 selector 都只支持已验证的 `hsql`、`doris_sql`、`python`、`notebook`、`spark`
- 查询 DECC endpoint ID 和注册的 table data ID（`decc endpoints` / `decc datas`）
- 列出项目 UDF（用户自定义函数），包括 Hive 函数和目录（`tree-nodes udf list`）
- 获取 UDF 详情，包括 HDFS 路径、绑定名称和版本（`tree-nodes udf get`）
- 通过 UDF nodeUid 或资源 nodeUid 获取 ID，该 ID 可用于创建函数、更新资源等操作（`tree-nodes id get`）
- 列出所有项目资源，包括文件、jar 包、zip、scm、image、thrift 和目录（`tree-nodes resource list`）
- 获取单个项目资源详情（`tree-nodes resource get`，含 SCM 镜像资源的 imageStatus / imageLatestJobId）
- 更新资源详情，包括 scmVersion（`tree-nodes resource update`）
- 在 SCM 镜像资源上只刷 `scmVersion`，触发后端异步重建镜像（`tree-nodes resource update-scm-version`）
- 创建并保存新的函数（`tree-nodes function create`）
- 上传本地 jar 到 Dorado 全局资源库（页面 `/dorado/settings/resource-file`）：`resource upload --file <local.jar> --name <n>`
- 列出 / 获取全局资源库中的资源（`resource list`、`resource get --id`）
- 更新全局资源（默认只改元信息；带 `--file` 则替换 jar）：`resource update --id <id> --name <n> [--file <local.jar>]`
- 在全局函数库（页面 `/dorado/settings/functions`）创建 UDF/UDTF/UDAF 并绑定到刚上传的 jar 资源（`function create --resource-id ... --name ... --class-name ... --function-type udf|udtf|udaf`）
- 列出 / 获取全局函数库下的函数（`function list --resource-id`、`function get --id`）
- 更新全局函数（`function update --id <id> --resource-id ... --name ... --class-name ... --function-type udf|udtf|udaf`）
- **区别**：`dorado resource` / `dorado function` 操作的是 `/dorado/settings/*` 全局资源库，无需 `--project-id`、支持本地 jar 直传；`dorado tree-nodes resource` / `dorado tree-nodes function` 操作的是项目 IDE 树节点，需要 `--project-id` 等项目级参数，仅能登记已存在的 hdfsPath/SCM 资源
- 获取 Flink 实时任务监控 URL（Grafana 指标、ByteLake、Flink Web UI 等）：`flink monitor get`
- 列出 Flink 实时任务运维操作日志（启动、重启、停止等）：`flink operation-log list`
- 查看 Flink 单条操作日志详情（含事件时间线与 Flink Web UI 链接，仅 start/restart 类日志包含 events）：`flink operation-log get`
- 当目标机房不在内置 region 列表里时，优先引导用户在环境变量或 `~/.local/share/bytedcli/data/.dorado.env` / `./.dorado.env` 中配置 `DORADO_REGION_<NAME>_API_BASE_URL`，再继续调用 Dorado 命令
- 内置 region 里 `sglark`、`jplark`、`uspipo` 和 `mycis` 固定走页面态 session；其余 built-in region 默认走 JWT。自定义 region 可通过 `DORADO_REGION_<NAME>_AUTH=session` 显式声明页面态授权。未显式声明时，先按正常请求处理，只有命中明确的页面态鉴权迹象时，再执行 `bytedcli auth login --session`
- `dorado backfill get --region cn` 是 endpoint 级别的页面态例外：CLI 会复用 CN browser session bootstrap DataLeap Cookie。首次使用或收到 `UserNotLogin` 时执行 `bytedcli auth login --session`，不要切换到 `--site i18n-tt`。
- 对 Dorado / DataLeap 的 `MY-BD` 环境，请特别使用 `bytedcli --site i18n-bd auth login --session`（或 `BYTEDCLI_CLOUD_SITE=i18n-bd bytedcli auth login --session`）先准备浏览器态 session；该环境的页面能力依赖 session/cookie，单独做普通 `auth login` 往往不够。

## Agent Guidance

- **处理 403 错误**：如果 Dorado API 返回 403 认证错误，可以尝试使用 titan 鉴权模式重试。通过环境变量配置对应 region 使用 titan 鉴权（注意 region 名中的 `-` 在环境变量名里要替换为 `_`）：

  ```bash
  # 对 gcp region 使用 titan 鉴权
  export DORADO_REGION_GCP_AUTH=titan

  # 对 us-eastred region 使用 titan 鉴权
  export DORADO_REGION_US_EASTRED_AUTH=titan

  # 对 eu-ttp2 region 使用 titan 鉴权
  export DORADO_REGION_EU_TTP2_AUTH=titan

  # 对 us-ttp region 使用 titan 鉴权
  export DORADO_REGION_US_TTP_AUTH=titan
  ```

  配置后重新执行命令即可。

- Dorado web URL 常见格式：
  - 任务开发页：`<host>/dorado/development/node/<taskId>?groupName=<region>&project=<region>_<projectId>`
  - 临时查询页：`<host>/dorado/development/query/<taskId>?groupName=<region>&project=<region>_<projectId>`
  - 从任务开发页读取当前任务详情时，优先使用 `dorado task get <taskId> --region <region>`；`project` 查询参数主要用于补充上下文，`task get` 本身通常只需要 `taskId + region`
  - 从这两类 URL 中解析 CLI 参数时，路径里的 `<taskId>` 对应 task ID，`groupName` 对应 `--region`，`project` 去掉 `<region>_` 前缀后对应 `--project-id`
- Dorado 任务页“任务监控/基线监控”配置默认走 `GET /dorado_api/task/{taskId}/alarms?projectId={projectId}&supportTaskAlarm=true`
- 读取任务监控配置时，优先使用 `dorado task alarms --task-id <taskId> --region <region>`（`--project-id` 省略时自动从任务详情解析）；不要再复用 `task get` 猜测 `alarmRules`/`baseline` 字段是否存在
- 按名字搜任务优先用 `dorado task list --project-id <projectId> --keyword <keyword>`（task list v2 端点，匹配 name/uid/owner）；`task search` 的 keyword/status 检索同样走 v2 端点，但 `--folder-id` 会切到 legacy 批量端点，该端点在部分 cn 项目稳定报 `Dorado API error: Unknown error`
- `dorado task copy` 的后端成功响应可能只回显源 task ID。只能在 `verification_status=verified` 时使用 `new_task_id`；若返回 `unresolved` / `ambiguous`，不得把 `source_task_id` 或 backend acknowledgement 当成新任务，也不要自动重试，按输出中的 `folder children` 命令人工核验。
- `task advanced-search` 的参数是 `-k/--keyword` + `--project-id`（均必填），没有 `--name`；JSON 结果在 `data.nodes`（不是 `items`/`tasks`/`list`），且按 IDE 树节点返回 `uid` 而非数字 task ID
- 读取任务 SQL 用 `dorado task code --task-id <taskId>`（`--project-id` 省略时自动从任务详情解析），支持 `--output <path>` 落盘
- 当用户已经明确给出一个不在内置列表里的 Dorado region 名称时，不要遍历或试探 `cn/sg/va/mycis/gcp/boe/boei18n`
- 优先引导用户在环境变量或 `~/.local/share/bytedcli/data/.dorado.env` / `./.dorado.env` 中配置 `DORADO_REGION_<NAME>_API_BASE_URL`
- 若该机房已知依赖页面态 cookie，再补充 `DORADO_REGION_<NAME>_AUTH=session`
- 只有用户没有提供 region 名称时，才允许在内置 region 中选择或追问
- Dorado 审批提交类命令（如 `dorado task commit-approval`、`dorado node submit-approval`）中的 `--review-policy-id`、`--review-users` 必须由用户按当前项目显式提供；不要从项目默认配置、历史记录或页面上下文自动推断后代填
- `task commit` / `task commit-approval` 支持可选 `triggerConfig`（对齐页面「提交上线」弹窗的「重跑历史数据」）。用户只说回溯某天时：用 `--biz-date`（或起止日期）即可，其余默认 `triggerType=rerun`、`maxParallelism=1`、`skipCheck=false`、`submitStrategy=linkageSubmit`。不回溯时不要传任何 lookback flag，body 不得带空 `triggerConfig`。需要队列/分层/依赖检查等时再用对应 flag 或 `--trigger-config` 全量 JSON；全量字段见下方示例与 `src/api/dorado/AGENTS.md`
- 对于页面提交类写操作，如果页面 payload 对字段顺序、字段缺省或附加字段敏感，优先使用与页面一致的专用命令和参数语义，不要复用“相近但不完全一致”的旧命令再额外拼接页面未发送字段
- 发布包详情读取与发布操作统一走 `dorado deploy` 命令组；不要把发布包读取或提交流程混入 `task` 相关命令语义
- publish-center 发布包读取统一走 `dorado deploy list/get/diff-sql`；其中 `deploy list` 以 project 为基础入口，可选叠加 `--creator` 过滤，并支持 `--all-pages` 自动翻页汇总，不要把这类页面型列表混入 `task list`
- 查看发布包 DIFF SQL 使用 `dorado deploy diff-sql` 对接 `/deploy/{deployId}/detail?projectId=...`；若接口未返回显式 diff SQL，可基于 `rawCommitVo` / `newCommitVo` 代码快照生成 diff，但这仍属于发布包详情语义，不要混入 `task diff`
- Dorado 页面提交流程若走专用 `deploy/v2/create` 接口，优先使用专门的 deploy/approval 命令；审批人、commit ID 列表在命令层按数组心智传参，页面默认结构（如 `deployPackage.developConf`）由实现层补齐
- 对于 Dorado 页面镜像型提交/发布 payload，若 body 同时包含告警/监控字段（如 `openDefaultSystemAlarm`、`customAlarmRuleIds`、固定 `alarmVersion`），只把用户有明确心智的字段暴露出来；固定默认值继续视为页面默认透传
- 排查 Dorado 权限失败时，先确认用户给的是 task ID 还是 instance ID；通过 `task get`、`instance record/list` 定位失败 instance，再下载实例日志解析 `NoPrivilegeException`。后续使用 Coral 权限申请流程，详见 `references/dorado.md` 的 “Debug permission failures and apply via Coral” 以及 `bytedance-coral` skill。
- 不要用 `bytedcli hive` 或 `bytedcli iam` 处理 Dorado 任务执行时的 Hive/TQS 权限缺失；`hive` 只适合查元数据，`iam` 只适合查员工身份。权限申请应走 `bytedcli coral permission apply`。

## 故障诊断与性能分析

优先路径使用 bytedcli 单工具，不再调用 dpcli。全流程保持只读；不要在诊断阶段执行 `rerun`、`online`、`commit`、`set-success`、`abort` 或任何 `update*` 命令。

### Agent 最短取证链（不要先跑 `--help`）

用户给出 `taskId + projectId + 业务日` 时，优先用 `instance record` 精确定位当天实例；不要先用 `instance list` 再自行翻页过滤。`--schedule` 格式固定为 `yyyy-MM-dd+HH:mm:00`，空格写成 `+`：

```bash
bytedcli --site <site> --json dorado instance record <taskId> \
  --project-id <projectId> --region <region> --schedule <yyyy-MM-dd+00:00:00>
bytedcli --site <site> --json dorado instance get <instanceId> --region <region>
bytedcli --site <site> --json dorado instance log-summary <instanceId> \
  --project-id <projectId> --region <region>
```

仅当业务日未知、需要观察多日失败/重试趋势时才用 `instance list`。如果 `log-summary` 没给出足够信息，但实例已产生 YARN application，直接用 `get-spark-history` 取得 application ID，再切到 `bytedance-megatron`：

```bash
bytedcli --site <site> --json dorado get-spark-history \
  --instance-id <instanceId> --region <region>
```

```bash
# 1) 已知 instanceId 时拿实例与日志摘要；log-summary 通常能暴露 applicationId 或主要错误片段
bytedcli --json dorado instance get <instanceId> --region <region>
bytedcli --json dorado instance log-summary <instanceId> --project-id <projectId> --region <region>

# 2) 下载实例日志到本地做关键字扫描
bytedcli auth login --session
bytedcli --json dorado download-instance-log --instance-id <instanceId> \
  --project-id <projectId> --region <region> -o temp/instance_<instanceId>.log

# 3) 有 applicationId 时进入 Megatron：应用元数据 + Spark/Flink 日志链接
bytedcli --json megatron app get --app-ids <applicationId> -r <region>
bytedcli --json megatron spark log-link list --app-id <applicationId> -r <region>
bytedcli --json megatron flink log-link list --app-id <applicationId> -r <region> \
  --taskmanager-keyword <keyword> --resolve-taskmanager-downloads

# 4) Spark 深入分析继续用 spark-ui 原子命令
bytedcli --json megatron spark-ui summary get --app-id <applicationId> -r <region>
bytedcli --json megatron spark-ui jobs list --app-id <applicationId> -r <region>
bytedcli --json megatron spark-ui executors list --app-id <applicationId> --all -r <region>

# 兼容入口：已有 Spark History/Megatron diagnostics 链路仍可直接读取
bytedcli --json dorado get-spark-history --instance-id <instanceId> --region <region>
bytedcli --json dorado get-spark-history --application-id <applicationId> --region <region>
```

当 `get-spark-history` 返回 `MEGATRON_APP_ID_NOT_FOUND`（通常表示没有产生 YARN application）时，优先下载实例日志定位 SQL 编译/权限/参数问题：

```bash
bytedcli auth login --session
bytedcli dorado download-instance-log --instance-id <instanceId> --project-id <projectId> --region <region> -o temp/instance_<instanceId>.log
grep -nE 'NoPrivilegeException|permission|privilege|CalciteContextException|SemanticException|ParseException|AnalysisException|Number of INSERT target columns|TQS 查询失败|FAILED|ERROR' temp/instance_<instanceId>.log | head -n 200
```

更完整的失败诊断与慢任务性能分析方法见：`references/troubleshooting.md`

- 使用通用调用方式：`references/invocation.md`

> 执行前缀见 `references/invocation.md`；下面示例直接写 `bytedcli`。

## Quick start

Commands are grouped under `dorado project`, `dorado task`, `dorado dts`, `dorado folder`, `dorado instance`, `dorado adhoc`, `dorado backfill`, `dorado spark-jar`, `dorado decc`, and `dorado flink` (realtime). Old flat names (e.g. `dorado list-projects`, `dorado get-task`, `dorado adhoc-exec`, `dorado folder-structure`, `dorado folder-children`, `dorado task diff-query`, `dorado task list-versions`, `dorado task update-query`) still work as hidden aliases.

```bash
# 创建 Spark-jar 配置（写入到 node draft）
# 说明：--spark-conf 为 k=v，可重复；--jars/--files/--py-files/--archives 接受 JSON 数组字符串
bytedcli dorado spark-jar create --node-id demo-node-id \
  --main-class com.example.Main \
  --main-file-path /path/to/app.jar \
  --main-resource-id 100001234 \
  --spark-conf spark.executor.memory=2g \
  --spark-conf spark.sql.shuffle.partitions=200

# 读取单个字段（示例输出：com.example.Main）
bytedcli dorado spark-jar get --node-id demo-node-id --field mainClass

# 更新 sparkConf（k=v，可重复；handler 会做 merge，不会清空未提及的 key）
bytedcli dorado spark-jar update --node-id demo-node-id \
  --spark-conf spark.sql.adaptive.maxNumPostShufflePartitions=6000 \
  --spark-conf spark.executor.cores=4
```

```bash
# 项目列表
bytedcli dorado project list --region boei18n --page 1 --size 20

# 任务列表 / 按名字搜任务（首选；--keyword 匹配 name/uid/owner）
bytedcli dorado task list --region boei18n --project-id 458 --page 1 --size 20
bytedcli dorado task list --region cn --project-id 458 --keyword "demo_task" --limit 10

# 搜索任务（keyword/status 走 task list v2 端点；--folder-id 走 legacy 批量端点，部分 cn 项目会报错）
bytedcli dorado task search --region cn --project-id 458 --status "init" --keyword "test_task"

# 高级搜索（IDE 树节点检索；--search-scope 可选 owner/name/uid/metadata/content；JSON 结果在 data.nodes）
# metadata=按任务配置参数检索，content=按任务代码(SQL/脚本全文)检索；多个 scope 取交集(AND)，组合越多结果越少
bytedcli dorado task advanced-search --region boei18n --project-id 458 -k "demo_task" --search-scope "owner,name,uid" --owner username --limit 10
# 按引用表名/配置参数检索任务（推荐单独用 metadata）
bytedcli dorado task advanced-search --region boei18n --project-id 458 -k "demo_table" --search-scope metadata

# 获取任务详情（包括源/目标信息、SQL 代码、依赖任务 ID）
bytedcli dorado task get 100274211 --region boei18n

# 获取任务 SQL 代码（--project-id 省略时自动解析；--output 落盘）
bytedcli dorado task code --task-id 100274211 --region boei18n
bytedcli dorado task code --task-id 100274211 --output ./task.sql

# 获取任务监控配置（告警规则、基线绑定；--project-id 省略时自动解析）
bytedcli dorado task alarms --task-id 100274211 --region boei18n
bytedcli dorado task alarms --task-id 1204196659 --project-id 1200002135 --region mycis

# 按 taskId 反查绑定的 baseline（baseline_global task lookup）
bytedcli dorado baseline get --task-id <task-id> --region-value <region-value> --region <region>

# 按项目筛选 baseline 列表（支持 SLA 优先级 D1-D5、baseline 名称关键字和 i18n region_value；SLA 不筛选时用 default）
bytedcli dorado baseline list --project-id <project-id> --baseline "<keyword>" --sla-priority D1 --region-value <region-value> --region <region>

# 按项目筛选 baseline 实例列表（支持 baseline 名称关键字、实例 ID 和 i18n region_value；这些过滤可省略）
bytedcli dorado baseline instances --project-id <project-id> --baseline "<keyword>" --baseline-instance-ids <id1,id2> --start-baseline-time "YYYY-MM-DD HH" --end-baseline-time "YYYY-MM-DD HH" --region-value <region-value> --region <region>

# 按 baseline 实例读取 commit tasks 详情（baseline instance detail）
bytedcli dorado baseline commit-tasks --baseline-id <baseline-id> --baseline-instance-id <baseline-instance-id> --project-id <project-id> --baseline-time "YYYY-MM-DD" --region-value <region-value> --region <region>

# 按 baselineId 读取 baseline 详情（支持 i18n region_value）
bytedcli dorado baseline get --baseline-id <baseline-id> --project-id <project-id> --region-value <region-value> --region <region>

# 创建任务
bytedcli dorado task create --type hsql --project-id <project-id> --folder-id <folder-id> --name "demo_task" --region boei18n
bytedcli dorado task create --type global_hsql --project-id <project-id> --folder-id <folder-id> --name "demo_global_task" --region us-ttp

# 获取任务模板详情：按所选 region 发送 GET /develop/info?id=<template_id>&projectId=<project_id>
bytedcli dorado task template get \
  --template-id 24680 \
  --project-id 12345 \
  --region sg

# 保存任务模板内容：按所选 region 发送 PUT /develop/<template_id>
# --region sg 会使用 Dorado SG site config 中的 region base URL
# 可用 --params-json '[]' 显式传模板参数，或用 --conf-file ./conf.json 传完整 { "code", "engineType", "params" } 对象
bytedcli dorado task template save \
  --template-id 24680 \
  --region sg \
  --code-file ./template.sql \
  --engine-type spark \
  --description "CommonTemplate for demo-group; validation tasks"

# 创建 DTS 批处理任务（common-dts-batch）
bytedcli dorado task create --type common-dts-batch --project-id 300002016 --folder-id 300370052 --name "demo_dts_task" --region sg

# 创建 hive->clickhouse 任务（壳子与 common-dts-batch 同形态，type 升级在 update-conf 阶段完成）
bytedcli dorado task create --type hive-clickhouse --project-id 1200002135 --folder-id 1200221500 --name "hive2ch_demo" --region mycis
bytedcli dorado task update-conf 1204206582 --task-file ./hive2ch-patch.json --type 'hive->clickhouse' --region mycis

# 创建 DTS 流式任务（common-dts-stream，例如 bmq->hive），走 /realtime/create 接口，与 common-dts-batch 相对
bytedcli dorado task create --type common-dts-stream --project-id 300003392 --folder-id 300202455 --name "demo_dts_stream_task" --region sg

# DTS 元数据 lookup（创建/补全 DTS 配置时使用）
bytedcli -j dorado dts datasource list --project-id 300002016 --data-source-type mysql --region sg
bytedcli -j dorado dts database list --project-id 300002016 --data-source-type hive --region sg
bytedcli -j dorado dts table list --project-id 300002016 --data-source-type hive --database-name demo_db --region sg
bytedcli -j dorado dts sql-column get --sql "select id, name from demo_db.demo_table" --region sg
bytedcli -j dorado dts mysql-split-key list --database-name demo_db --table-name demo_table --region sg
bytedcli -j dorado dts clickhouse-shard-num get --cluster demo_ck_cluster --dts-region-name cn --region cn
bytedcli -j dorado dts doris-writer-metadata get --cluster demo_doris --region sg

# 创建 stream_sql 实时 SQL 任务壳子，同样走 /realtime/create；创建时不要传 --query / --query-file
bytedcli dorado task create --type stream_sql --project-id <project-id> --folder-id <folder-id> --name "demo_stream_sql_task" --region sg

# 创建 Java Flink 实时任务壳子，同样走 /realtime/create；创建时不要传 --query / --query-file
bytedcli dorado task create --type java-flink --project-id <project-id> --folder-id <folder-id> --name "demo_java_flink_task" --region sg

# 保存 DTS 流式任务草稿：写入完整 conf（reader=bmq / writer=hive / operator=flink）并指定运行队列
# 队列可先用 `project yarn-queues --task-type common-dts-stream` 找到最空的流式队列
bytedcli dorado task update-conf 306904995 --task-file ./bmq2hive-conf.json --queue root.demo_flink_queue --cluster Demo-Cluster --dc my2 --priority normal --owner demo.user --region sg

# 转交任务 owner（默认会读取任务名；单任务可用 --name 显式传入）
bytedcli dorado task transfer-owner --task-id <task-id> --project-id <project-id> --owner demo-owner --region va
bytedcli dorado task transfer-owner --task-id <task-id> --project-id <project-id> --owner demo-owner --name demo_task --region va
bytedcli dorado task transfer-owner --task-ids 1001,1002,1003 --project-id <project-id> --owner demo-owner --region va

# 更新 SQL 任务（hsql/fsql/stream_sql）的查询
bytedcli dorado task update 100274211 --query "SELECT * FROM table" --region boei18n
bytedcli dorado task update 100274211 --query-file ./task.sql --region boei18n  # 大 SQL / 长 SQL 写回推荐
bytedcli dorado task update 100274211 --type hsql --region boei18n

# 更新 MySQL 到 Hive 任务配置（支持设置 split keys）
bytedcli dorado task update 123456 --type mysql-hive --split-keys id,name --region boei18n
bytedcli dorado task update 123456 --type mysql-hive --source-db source_db --source-table source_table --target-db target_db --target-table target_table --split-keys id,name --region boei18n

# MySQL 到 Hive Binlog 任务
bytedcli dorado task binlog status --task-id 67890 --dorado-region-name demo-region --region cn
bytedcli dorado task binlog status --src-database demo-db --src-storage-region demo-region --subscribe-type incremental --task-type mysql->hive --dorado-region-name demo-region --region cn
bytedcli dorado task binlog connect --tree-node-id 123456 --task-id 67890 --dorado-region-name demo-region --region cn
bytedcli dorado task binlog connect --tree-node-id 123456 --src-database demo-db --src-storage-region demo-region --owner demo-owner --task-type mysql->hive --dorado-region-name demo-region --region cn --wait

# 对比 SQL 版本差异（默认：最新发布版本 vs 草稿）
bytedcli dorado task diff 100274211 --region boei18n
bytedcli dorado task diff 100274211 --from 5 --to 6 --region boei18n  # 版本 5 vs 版本 6
bytedcli dorado task diff 100274211 --from 5 --region boei18n          # 版本 5 vs 草稿

# 安全对比任务配置（默认：最新发布版本 vs 草稿）
# 仅输出白名单字段、结构化依赖变化、opaque 区块大小统计和未知变化布尔标记
bytedcli dorado task version compare --task-id <task-id> --region sg
bytedcli dorado task version compare --task-id <task-id> --from 5 --to 6 --region sg

# 检查任务是否在线
bytedcli dorado task check-online 100274211 --project-id 458 --region boei18n

# 重跑任务（默认仅回溯，不部署）
bytedcli dorado task rerun 100274211 --project-id 458 --biz-date 2026-03-12 --region boei18n

# 双跑任务默认使用最新线上版本；需要基于草稿版本双跑时显式加 --use-draft-version。
# CLI 会自动从 Dorado 草稿版本列表读取 C... commitId；只有自动查询失败时才需要用 --draft-commit-id 兜底。
bytedcli dorado task rerun 100274211 --project-id 458 --biz-date 2026-03-12 \
  --trigger-type dualRun --use-draft-version --region boei18n
bytedcli dorado task rerun 100274211 --project-id 458 --biz-date 2026-03-12 \
  --trigger-type dualRun --use-draft-version --draft-commit-id CsampleDraftCommit --region boei18n

# 切换队列重跑任务（默认仅回溯，不部署）
bytedcli dorado task rerun 100274211 --project-id 458 --biz-date 2026-03-12 --region boei18n --clusters "cluster1,cluster2" --queues "queue1,queue2"

# 区间回溯
bytedcli dorado task rerun <task-id> --project-id <project-id> --start-biz-date 2026-03-01 --end-biz-date 2026-03-31 --region sg

# 指定回溯范围类型（single_task_rerun / single_task_backfill / multi_task_rerun / multi_task_backfill / link_backfill）
bytedcli dorado task rerun <task-id> --project-id <project-id> --biz-date 2026-03-31 --scope single_task_backfill --region sg

# 重跑并提交部署（需显式加 --deploy）
bytedcli dorado task rerun 100274211 --project-id 458 --biz-date 2026-03-12 --deploy --message "rerun reason" --region boei18n

# 传入自定义输入参数（覆盖任务默认参数）
# --input-params 接受 JSON 数组，每个元素包含 name/paramValue/type 字段
# 注意：包含特殊字符（如单引号）的参数值，推荐通过环境变量传入，避免 shell 转义问题
DEMO_PARAM="{ 'key': 'demo-value' }"
INPUT_PARAMS=$(DEMO_PARAM="$DEMO_PARAM" node -e "
const params = [
  {name:'demo_param_a', paramValue:'demo-value-a', type:'task_custom'},
  {name:'demo_param_b', paramValue:'demo-value-b', type:'task_custom'},
  {name:'demo_param_c', paramValue:process.env.DEMO_PARAM, type:'task_custom'},
];
process.stdout.write(JSON.stringify(params));
")
bytedcli --json dorado task rerun <task-id> --project-id <project-id> --biz-date 2026-03-31 \
  --input-params "$INPUT_PARAMS" --region sg

# 指定具体实例（trigger-nodes）和时间区间参数
bytedcli dorado task rerun <task-id> --project-id <project-id> --region sg \
  --interval-start-time "2026-03-30 15:00:00" --interval-end-time "2026-03-30 16:00:00" \
  --trigger-nodes '[{"taskId":<task-id>,"projectId":<project-id>,"taskTime":"2026-03-30 00:00:00"}]'

# 上线任务（提交草稿并部署上线）
# realtime stream 任务（如 kafka2clickhouse / stream_channel_* / conf.typeGroup=stream）会自动走 PUT /realtime/{taskId}/online
bytedcli dorado task online 100274211 --project-id 458 --region boei18n
bytedcli dorado task online 100274211 --project-id 458 --message "deploy v2" --skip-codes "-1005" --region boei18n

# 提交审批（页面同款 commitAndDeploy payload）
# 对应 payload 字段：reviewPolicyId / reviewUserNames / openDefaultSystemAlarm / customAlarmRuleIds / baselineIds / agentConfig / projectId / skipCodes
# review-policy-id / review-users 必须由用户按当前项目显式提供
bytedcli dorado task commit-approval <task-id> --project-id <project-id> \
  --review-policy-id 24 \
  --review-users "demo-user-a,demo-user-b" \
  --custom-alarm-rule-ids 11870,14696 \
  --baseline-ids 33 \
  --agent-config '{"sessionId":"demo-session"}' \
  --region mycis

# 批量提交审批（deploy/v2/create，同一个 deploy package 可包含多个 commit）
# --skip-codes 会同时注入 body 与 URL query（与单任务 commit-approval/online 一致），可跳过 -10000 这类确认告警（如「已存在其他任务同步同名表，请确认上线」）
bytedcli dorado task commit-batch-approval --project-id <project-id> \
  --name demo_pkg_20260507 \
  --message "batch approval" \
  --review-policy-id 24 \
  --review-users "demo-user-a,demo-user-b" \
  --commit-ids "108103,108111,108110" \
  --skip-codes "-1005,-10000" \
  --region mycis

# 拉取 publish-center 发布包列表（可按 creator 过滤；支持自动翻页汇总）
bytedcli dorado deploy list --project-id <project-id> --region mycis
bytedcli dorado deploy list --project-id <project-id> --creator demo.user --all-pages --region mycis

# 查看 publish-center 发布包详情（支持 UUID / 数字 ID）
bytedcli dorado deploy get --deploy-id <deploy-id> --project-id <project-id> --region mycis

# 查看发布包详情里的 DIFF SQL（deploy/{deployId}/detail?projectId=...；无显式 diff 字段时比较 rawCommitVo/newCommitVo 代码快照）
bytedcli dorado deploy diff-sql --deploy-id <deploy-id> --project-id <project-id> --region mycis

# 仅提交（commit 草稿，不部署上线）
# realtime stream 任务会自动走 PUT /realtime/{taskId}/commit
bytedcli dorado task commit <task-id> --project-id <project-id> --region mycis
bytedcli dorado task commit <task-id> --project-id <project-id> \
  --message "commit draft" \
  --review-policy-id 33 \
  --no-open-default-system-alarm \
  --custom-alarm-rule-ids 14032 \
  --baseline-ids 33 \
  --agent-config '{"sessionId":"demo-session"}' \
  --region mycis

# 仅提交 + 重跑历史（页面同款 triggerConfig；只给日期时自动补默认）
bytedcli dorado task commit <task-id> --project-id <project-id> \
  --biz-date 2026-08-05 \
  --message "commit with lookback" \
  --region sg

# 仅提交 + 回溯区间 + 覆盖并行/提交方式
bytedcli dorado task commit <task-id> --project-id <project-id> \
  --start-biz-date 2026-08-01 --end-biz-date 2026-08-05 \
  --max-parallelism 2 --submit-strategy levelSubmit \
  --region sg

# 仅提交 + 单队列回溯
bytedcli dorado task commit <task-id> --project-id <project-id> \
  --biz-date 2026-08-01 \
  --specify-queue-for-lookback --lookback-queue-mode single_queue \
  --cluster badge --queue root.badge_tteng_public \
  --interval-start-time 00:00 --interval-end-time 00:00 \
  --region sg

# 仅提交 + 多队列 / 依赖检查（也可用 --trigger-config 整包 JSON）
bytedcli dorado task commit <task-id> --project-id <project-id> \
  --biz-date 2026-08-04 \
  --submit-strategy levelSubmit \
  --check-types hive-table-partition,upstream-instance-status \
  --lookback-queue-mode multi_queues \
  --lookback-queues '[{"startTime":"00:00","endTime":"23:59","region":"sg","dc":"my","clusterName":"badge","queue":"root.badge_tteng_public"}]' \
  --region sg

# triggerConfig 全量字段（Agent 需知）：triggerType, startBizDay, endBizDay,
# maxParallelism, skipCheck, submitStrategy (linkageSubmit|levelSubmit),
# checkTypes[], specifyQueueForLookback, lookBackQueueMode (single_queue|multi_queues),
# cluster/queue/intervalStartTime/intervalEndTime (single_queue),
# lookBackTimeDivisionQueues[] (multi_queues). 不回溯时省略整个对象。

# 获取实例对应的 Spark History 链接
bytedcli dorado get-spark-history --instance-id 1088059891 --region sg

# 查看版本历史
bytedcli dorado task version list 100274211 --region boei18n

# 查看草稿提交历史（返回可用于 dualRun 的 C... commit ID）
bytedcli dorado task version list <task-id> --draft-history --region sg

# 实例列表；加 --only-self 时仅返回当前登录用户拥有的实例
bytedcli dorado instance list --region boei18n --project-id 458 --task-id 100274211
bytedcli dorado instance list --region sg --project-id 12345 --only-self

# 获取实例详情
bytedcli dorado instance get 258345284 --region boei18n

# 创建完整的回溯计划（批量多任务执行）
bytedcli dorado backfill create --project-id <project-id> --task-ids <task-id1,task-id2> --start-date 2026-03-01 --end-date 2026-03-10 --region sg

# 检查回溯状态（进度和实例数量）
bytedcli dorado backfill get --backfill-id 3614569 --region boei18n

# 查看回溯计划内的具体任务触发器详情
bytedcli dorado backfill triggers --region boei18n --backfill-id 3614569
bytedcli dorado backfill triggers --region sg --backfill-id 123456 -j

# 精确稀疏日期回溯：pending draft 生命周期（create -> calculate -> prune -> launch）
# backfill create 只表达一段连续日期；需要精确 (task, date) 集合时用 draft。
bytedcli dorado backfill draft create --project-id 300003210 --root-task-ids 307663021,307663022 --task-time-stamps 2026-08-18,2026-08-20,2026-08-06 --queues root.queue_a,root.queue_b --message "release backfill" --region sg
bytedcli dorado backfill draft create-instances --backfill-id 7385298 --project-id 300003210 --region sg
# 取消勾选不在精确范围内的 link（ids 为 create-instances 返回的 link ID）
bytedcli dorado backfill draft update-instances --backfill-id 7385298 --project-id 300003210 --ids 132524771 --pruning-type unselect --region sg
# 校验最终选中的 link（默认包含未选中的记录；输出含 total/page/page_size）
bytedcli dorado backfill draft list-instances --backfill-id 7385298 --project-id 300003210 --page 1 --page-size 100 --region sg -j
# draft 创建后为 pending_launch，不 submit 就不会执行任何任务
bytedcli dorado backfill draft submit --backfill-id 7385298 --project-id 300003210 --region sg
# 直接置成功（不跑代码、不刷新产出）：--ins-op-type succeed
bytedcli dorado backfill draft create --project-id 300003210 --root-task-ids 307663022 --task-time-stamps 2026-08-19 --ins-op-type succeed --region sg

# 下载实例日志（纯文本，页面态 cookie）
bytedcli auth login --session
bytedcli dorado download-instance-log --instance-id 1102084977 --project-id 150000021 --region sg -o instance_1102084977.log

# 获取队列资源使用情况
bytedcli dorado task get-queue-resource --clusters snake,badge --queues root.snake_eprivacy_eng,root.badge_privacy_eng --region boei18n

# 查看项目可用的 Yarn 队列
bytedcli dorado project yarn-queues --project-id 458 --region boei18n
bytedcli dorado project yarn-queues --project-id 458 --task-type global_hsql --region us-ttp  # 按任务类型过滤
bytedcli dorado project yarn-queues --project-id 300003392 --task-type notebook --region sg --restricted  # 仅看合规队列（仅 i18n / 非 cn region 有此概念）

# 查看项目文件夹结构
bytedcli dorado folder structure --project-id 458 --region boei18n
bytedcli dorado folder structure --project-id 458 --root-id -2 --region boei18n  # 查看临时查询目录

# 查看文件夹下的子项（子文件夹和任务）
bytedcli dorado folder children --folder-id 268736 --project-id 458 --region boei18n

# 创建子目录
bytedcli dorado folder create --project-id 12345 --parent-uri "task:///HrdNGPWr" --name "demo-folder" --region cn
bytedcli dorado folder create --project-id 12345 --parent-uri "task:///HrdNGPWr" --name "demo-folder" --description "a demo subfolder" --region sg

# 更新任务草稿配置
bytedcli dorado task-draft update 100274211 --queue root.pns_data_infra_core --cluster model01 --region boei18n
bytedcli dorado task-draft update 100274211 --sql "SELECT * FROM table" --region boei18n  # 更新 SQL 代码
bytedcli dorado task-draft update 100274211 --sql-file ./task.sql --region boei18n  # 大 SQL / 长 SQL 写回推荐
bytedcli dorado task-draft update 1204210031 --frequency hourly --schedule-time 5 --schedule-day 16 --region mycis  # 小时调度，直接传页面调度值
bytedcli dorado task-draft update 100274211 --dependencies "100274200:0:set,100274201:0:set" --region boei18n  # 全量替换同机房任务依赖
bytedcli dorado task-draft update 100274211 --add-dependency 100274202 --region boei18n  # 安全增量预览，不写草稿
bytedcli dorado task-draft update 100274211 --add-dependency 100274202 --region boei18n --yes  # 确认后仅追加该依赖
bytedcli dorado task-draft update 100274211 --add-dependency 100274202:0:set --add-dependency 100274203:-1:set --region boei18n --yes
bytedcli dorado task-draft update 100274211 --outer-dependencies "306220763@sg" --region va  # 更新跨机房依赖（va 任务依赖 sg 任务）
bytedcli dorado task-draft update 100274211 --outer-dependencies "100@sg:0:set,200@va:1:set" --region cn  # 多个跨机房依赖

# 更新跨区域查询配置（queryType + sourceRegionInfos）
bytedcli dorado task-draft update 306215786 -r sg --sql "select 1" --query-type FLEXIBLE_UNION \
  --source-region-infos '[{"geo":"SG","yarnQueue":{"region":"sg","dc":"my","clusterName":"badge","queue":"root.badge_example"}},{"geo":"EU_TTP","deccDataId":"7491149792614072631","deccEndpointId":"7252920295022035206","yarnQueue":{"region":"i18n_gcp","dc":"useast2a","clusterName":"coati","queue":"root.coati_example"},"owner":"demo.user"}]'

# 更新 DTS 任务配置（common-dts-batch 类型）
# sourceType=sql: 通过 SQL 查询读取数据
bytedcli dorado task-draft update <task-id> -r sg \
  --dts-read-type hive --dts-read-idc sg --dts-read-source-type sql \
  --dts-read-query "select col1, col2 from example_db.example_table where date = '\${date}'" \
  --dts-read-connector-type hive \
  --dts-read-columns '[{"type":"string","name":"col1"},{"type":"bigint","name":"col2"}]' \
  --dts-writer-type clickhouse --dts-writer-idc sg \
  --dts-writer-cluster cnch_example_cluster \
  --dts-writer-database-name example_db --dts-writer-table-name example_table \
  --dts-writer-partitions '[{"name":"date","type":"TIME","value":"${date}"}]' \
  --dts-writer-shard-column col1 --dts-writer-shard-num 1200 --dts-writer-append-mode 2 \
  --dts-writer-columns '[{"type":"string","name":"col1"},{"type":"int64","name":"col2"}]' \
  --dts-writer-connector-type clickhouse

# sourceType=table: 通过指定库表名读取数据
bytedcli dorado task-draft update <task-id> -r sg \
  --dts-read-type hive --dts-read-idc sg --dts-read-source-type table \
  --dts-read-database-name example_db --dts-read-table-name example_table \
  --dts-read-connector-type hive \
  --dts-read-columns '[{"type":"string","name":"col1","description":"desc1"}]' \
  --dts-read-partitions '[{"name":"date","type":"string","value":"${date}"}]' \
  --dts-writer-type clickhouse --dts-writer-idc sg \
  --dts-writer-cluster cnch_example_cluster \
  --dts-writer-database-name example_target_db --dts-writer-table-name example_target_table \
  --dts-writer-partitions '[{"name":"date","type":"TIME","value":"${date}"}]' \
  --dts-writer-shard-column col1 --dts-writer-shard-num 1200 --dts-writer-append-mode 2 \
  --dts-writer-columns '[{"type":"string","name":"col1"},{"type":"int64","name":"col2"}]' \
  --dts-writer-connector-type clickhouse

# larksheet -> hive: 通过 LarkSheet URL 读取并写入 Hive
bytedcli dorado task-draft update <task-id> -r mycis \
  --dts-read-type larksheet --dts-read-idc pinnacle \
  --dts-read-url "https://example.com/wiki/demo?vwb=1.0.0&sheet=abc123" \
  --dts-read-sheet-type spreadsheet \
  --dts-read-template-param '{}' \
  --dts-read-connector-type larksheet \
  --dts-read-columns '[{"type":"string","name":"col1","extraType":null,"description":null},{"type":"string","name":"col2","extraType":null,"description":null}]' \
  --dts-writer-type hive --dts-writer-idc pinnacle \
  --dts-writer-database-name example_db --dts-writer-table-name example_table \
  --dts-writer-partitions '[{"name":"pdate","type":"TIME"}]' \
  --dts-writer-columns '[{"type":"string","name":"id","description":"col1"},{"type":"string","name":"obj_id","description":"col2"}]' \
  --dts-writer-connector-type hive

# 局部更新（只修改部分字段，其余保留原值）
bytedcli dorado task-draft update <task-id> -r sg --dts-writer-append-mode 3
bytedcli dorado task-draft update <task-id> -r sg --dts-read-query "select col1 from example_db.example_table"

# 测试运行任务草稿（debug run）
bytedcli dorado task-draft test 100274211 --project-id 458 --region boei18n
# 默认会打印本次提交调试所使用的 SQL（debug_sql）；`--json` 输出也会在 `data.debug_sql` 返回该 SQL

# 测试运行时抑制 Manta 数据质量监控触发（HSQL 等非 node-type 任务生效）
# 适用于反复调试 SQL、不希望产生 Manta test_check 告警的场景
bytedcli dorado task-draft test 100274211 --project-id 458 --region boei18n --disable-manta

# 传入自定义输入参数（覆盖任务代码中 {{param}} 占位符）
# --input-params 接受 JSON 数组，每个元素只需 name/debugVal 两个字段（debugVal 为调试时代入占位符的值）
# 注意：${date}、${bizdate} 等系统内置参数不属于自定义参数，不需要通过此选项传入
# 注意：task-draft test 用 name/debugVal（后端自动补全 type 等元数据），与 task rerun 的 name/paramValue/type 字段不同，不要混用
# 注意：doris_sql / spark / python / notebook 这类 node-type 调试会由 CLI 先替换提交内容中的 {{param}}，再调用 IDE debug endpoint
bytedcli dorado task-draft test 100274211 --project-id 458 --region boei18n \
  --input-params '[{"name":"data_version","debugVal":"2026-06-24"}]'

# 指定 Dorado 原生多环境输入表映射，调试时让后端使用已勾选的上游测试表；CLI 只透传映射，不改写 SQL
bytedcli dorado task-draft test 100274211 --project-id 458 --region boei18n \
  --input-table-map '[{"mappingSourceType":"hive","mappingType":"database","metaType":"input_table","mappingValues":[{"dbName":"demo_dev","tableName":"sample_orders","envName":"dev","envType":"dev"},{"dbName":"demo_prod","tableName":"sample_orders","envName":"prod","envType":"prod"}]}]'

# 校验 HSQL / stream_sql 任务草稿语法
bytedcli dorado task-draft explain 100274211 --project-id 458 --region boei18n
bytedcli dorado task-draft explain 100274211 --project-id 458 --date 2025-04-20 --region mycis
bytedcli dorado task-draft explain 100274211 --project-id 458 --template-var hrbi_corehr_global=hrbi_corehr_global --region mycis
bytedcli dorado task-draft explain 100274211 --project-id 458 --online --region mycis
bytedcli dorado task-draft explain 100274211 --project-id 458 --version 6 --region mycis
bytedcli dorado task-draft explain 104905354 --project-id 1566 --region cn

# 校验 DTS 草稿 reader SQL 语法（resource/explain）
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 --region mycis --date 2025-04-20
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 --template-var hrbi_atsx_global=hrbi_atsx_global --region mycis
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 --online --region mycis

# 获取依赖推荐（根据任务 SQL 推荐可依赖的上游任务）
bytedcli dorado task dep-recommendations <downstream-task-id> --region <region>

# 推荐项为 id=null / isOnlineTask=false 的 hive_partition-sensor 时，先预览创建 payload
bytedcli dorado task hp-sensor create \
  --downstream-task-id <downstream-task-id> \
  --database-name sample_database \
  --table-name sample_table \
  --storage-region <physical-storage-region> \
  --region <region>

# 确认表、分区 path、namespace 与 storage region 后再创建
bytedcli dorado task hp-sensor create \
  --downstream-task-id <downstream-task-id> \
  --database-name sample_database \
  --table-name sample_table \
  --storage-region <physical-storage-region> \
  --path '<partition-path>' \
  --namespace <hive-namespace> \
  --frequency daily \
  --region <region> \
  --yes

# 创建后重新获取推荐中的正整数 task ID，再预览并保存依赖
bytedcli dorado task dep-recommendations <downstream-task-id> --region <region>
bytedcli dorado task-draft update <downstream-task-id> \
  --add-dependency <sensor-task-id> \
  --region <region>
bytedcli dorado task-draft update <downstream-task-id> \
  --add-dependency <sensor-task-id> \
  --region <region> \
  --yes

# 获取目录树子节点（返回 UID-based uri，用于 node create 的 --parent-uri）
bytedcli dorado tree-nodes children --project-id {project-id} --region boei18n          # 查询根目录
bytedcli dorado tree-nodes children --project-id {project-id} --uri "task:///f{numericId}" --region boei18n   # 查询指定 uri 的子节点
bytedcli dorado tree-nodes children --project-id {project-id} --uris "task:///,task:///f{numericId}" --region boei18n  # 批量查询
# 返回每个子节点的 uid/name/type/uri/isLeaf；dir 类型子节点的 uri 即可作为创建任务时的 --parent-uri

# 列出项目 UDF（用户自定义函数），包括 Hive 函数和目录
bytedcli dorado tree-nodes udf list --project-id {project-id} --region {region}

# 列出所有项目资源（file, jar, zip, scm, image, thrift, dir），递归遍历目录
bytedcli dorado tree-nodes resource list --project-id {project-id} --region {region}

# 获取 UDF 详情，包括 HDFS 路径、绑定名称和版本
bytedcli dorado tree-nodes udf get --project-id {project-id} --bind-id {bind-id} --region {region}

# 通过 UDF nodeUid 或资源 nodeUid 获取资源 ID（bindId），该 ID 可用于创建函数、更新资源等操作
bytedcli dorado tree-nodes id get --node-ids {node-id-1},{node-id-2} --region {region}

# 更新资源详情，包括 scmVersion
# 注意：
# 1. 正确的参数名是 --owner-user-name（不是 --owner-ownerUserName）
# 2. --de-compression 需要明确传入布尔值：true 或 false
# 3. jar 资源的 --sub-type 应为 jar（不是 scm）
bytedcli dorado tree-nodes resource update --project-id {project-id} --resource-id {resource-id} --name {name} --description {description} --owner-user-name {owner-user-name} --sub-type {sub-type} --type {type} --engine-id {engine-id} --hdfs-path {hdfs-path} --download-url {download-url} --file-name {file-name} --hash {hash} --source-type {source-type} --scm-id {scm-id} --scm-name {scm-name} --scm-version {scm-version} --scm-source-file-path {scm-source-file-path} --de-compression {de-compression} --region {region}

# 获取单个项目资源详情（含 conf JSON：SCM 资源会含 scmName/scmVersion/imageStatus/imageLatestJobId/imageScms）
bytedcli dorado tree-nodes resource get --project-id {project-id} --resource-id {resource-id} -j

# 只刷 SCM 资源（如 Python 镜像）上的 scmVersion，触发后端异步重建镜像
# 仅适用于 conf.scmName 非空的资源；非 SCM 资源请用 `resource update`
# 写完不会阻塞，需要观察构建结果时再次调用 `resource get`，看 conf.imageStatus（1=building/2=ready）与 conf.imageLatestJobId 是否翻新
bytedcli dorado tree-nodes resource update-scm-version --project-id {project-id} --resource-id {resource-id} --scm-version {scm-version}

# 创建函数
bytedcli dorado tree-nodes function create --project-id {project-id} --name {name} --description {description} --type {type} --sub-type {sub-type} --engine-id {engine-id} --folder-id {folder-id} --bind-resource-id {bind-resource-id} --udf-type {udf-type} --class-name {class-name} --region {region}

# Dorado 全局资源库（页面 /dorado/settings/resource-file）：上传本地 jar
# 鉴权：发 x-dataleap-jwt-token，由 ByteCloud JWT 通过 /user/jwt 兑换得到，纯 token，不需要浏览器 session
bytedcli dorado resource upload --file ./demo-udf.jar --name demo_udf --description "demo udf" -r cn

# 全局资源库：列出 / 查看资源（含 fileLink）
bytedcli dorado resource list --type jar -r cn
bytedcli dorado resource get --id 100052827 -r cn

# 全局资源库：更新资源（默认只改 name/description；带 --file 才替换 jar）
bytedcli dorado resource update --id 100052827 --name demo_udf --description "updated desc" -r cn

# Dorado 全局函数库（页面 /dorado/settings/functions）：创建 UDF/UDTF/UDAF 并绑定到刚上传的 jar
bytedcli dorado function create --resource-id 100052827 --name demo_udf --class-name com.example.demo.HelloUDF --function-type udf -r cn

# 全局函数库：列出 / 查看函数
bytedcli dorado function list --resource-id 100052827 -r cn
bytedcli dorado function get --id 13333 -r cn

# 全局函数库：更新函数（body 形态与 create 相同，按 --id 定位）
bytedcli dorado function update --id 13333 --resource-id 100052827 --name demo_udf --class-name com.example.demo.HelloUDF --function-type udf -r cn

# 查询项目可用镜像（返回 id + name，用于 node create/save 的镜像配置）
bytedcli dorado image list --project-id {project-id} --region cn
bytedcli dorado image list --project-id {project-id} --region cn -k demo_image   # 按名称关键词过滤

# 仅有 taskId、解析 IDE nodeUid（tree-nodes name+type filter 单路径下钻）
bytedcli dorado node resolve-uid --project-id {project-id} --task-id 100274211 --region boei18n -j

# Python/Notebook/Spark 任务节点（非 SQL 类任务；SQL 任务请用 task-draft）
# 创建节点（返回 nodeId，后续操作均通过 nodeId 进行）
bytedcli dorado node create --project-id {project-id} --name demo-python-task --type python --region cn
bytedcli dorado node create --project-id {project-id} --name demo-notebook --type notebook --region cn
bytedcli dorado node create --project-id {project-id} --name demo-spark-task --type spark --region cn

# 创建时指定 Docker 镜像（先用 image list 查询可用镜像的 id 和 name）
bytedcli dorado node create --project-id {project-id} --name demo-python-task --type python --image-name demo-image --image-id 400012345 --region cn
bytedcli dorado node create --project-id {project-id} --name demo-notebook --type notebook --image-name demo-image --image-id 400012345 --region cn
bytedcli dorado node create --project-id {project-id} --name demo-spark-task --type spark --image-name demo-image --image-id 400012345 --region cn

# Spark (PySpark) 任务可额外指定语言和 Spark 版本（默认 language=python, spark-version=3.2）
bytedcli dorado node create --project-id {project-id} --name demo-pyspark --type spark --language python --spark-version 3.2 --image-name demo-image --image-id 400012345 --region cn

# 在子目录下创建
bytedcli dorado node create --project-id {project-id} --name demo-notebook --type notebook --parent-uri "task:///f{numericId}" --description "示例notebook" --region cn
# 创建时直接传入代码（inline）
bytedcli dorado node create --project-id {project-id} --name demo-python-task --type python --content "print('hello')" --region cn
# 创建时从文件读取代码
bytedcli dorado node create --project-id {project-id} --name demo-python-task --type python --content-file ./my_script.py --region cn

# 获取节点草稿内容
bytedcli dorado node get --node-id NxyzABC --region boei18n

# 提取完整 notebook JSON（可直接保存为 .ipynb 文件）
bytedcli dorado node get --node-id NxyzABC --region boei18n --notebook-only > my_notebook.ipynb

# 获取当前草稿（用于查看现有配置，包括 dataOutputs 等，再按需修改后回写）
bytedcli dorado node get --node-id NxyzABC --region boei18n --json

# 保存节点草稿（更新代码）
bytedcli dorado node save --node-id NxyzABC --content "print('hello')" --region boei18n
bytedcli dorado node save --node-id NxyzABC --content-file ./my_script.py --region boei18n

# 保存草稿同时登记任务产出（通过 metadata 中的 dataOutputs 字段）
# 登记 HDFS 产出
bytedcli dorado node save --node-id NxyzABC \
  --metadata '{"configuration":{"dataOutputs":[{"type":"hdfs","path":"/example/output/path"}]},"name":"demo-task","type":"python"}' \
  --region boei18n

# 登记 Hive 分区表产出
bytedcli dorado node save --node-id NxyzABC \
  --metadata '{"configuration":{"dataOutputs":[{"type":"partition","databaseName":"example_db","tableName":"example_table","partitions":[{"key":"date","value":"${date}"}],"namespace":"default"}]},"name":"demo-task","type":"python"}' \
  --region boei18n

# 登记其他类型产出
bytedcli dorado node save --node-id NxyzABC \
  --metadata '{"configuration":{"dataOutputs":[{"type":"other"}]},"name":"demo-task","type":"python"}' \
  --region boei18n

# 同时更新代码和产出登记
bytedcli dorado node save --node-id NxyzABC --content-file ./my_script.py \
  --metadata '{"configuration":{"dataOutputs":[{"type":"partition","databaseName":"example_db","tableName":"example_table","partitions":[{"key":"date","value":"${date}"}],"namespace":"default"}]},"name":"demo-task","type":"python"}' \
  --region boei18n

# notebook 草稿保存（含产出登记）
bytedcli dorado node save --node-id NxyzABC --content-file ./notebook.ipynb \
  --metadata '{"configuration":{"dataOutputs":[{"type":"hdfs","path":"/example/output/path"}]},"name":"demo-notebook","type":"notebook"}' \
  --region boei18n

# 更新任务镜像（支持 python/notebook/spark 三种类型，自动检测任务类型）
bytedcli dorado node save --node-id NxyzABC --image-name demo-image --image-id 400012345 --region cn
# spark 任务可额外指定语言和 Spark 版本
bytedcli dorado node save --node-id NxyzABC --image-name demo-image --image-id 400012345 --language python --spark-version 3.2 --region cn

# notebook 草稿保存到合规队列（把目标合规队列写进 computeResourceParam 即可，
# 服务端会原样落进 draft；合规队列对 kernel 真正生效的环节是 node start）
bytedcli dorado node save --node-id NxyzABC --content-file ./notebook.ipynb \
  --metadata '{"configuration":{"computeResourceParam":{"region":"sg","dc":"my","cluster":"nbyodel01","queue":"root.notebook_compliance_public2"}},"name":"demo-notebook","type":"notebook"}' \
  --region sg

# 启动 notebook kernel 会话（用 metadata 里指定的队列拉起 kernel；不会回写 draft）
# - --metadata 省略时会复用当前 draft 的 metadata，等同于 dorado web 点「启动 kernel」直接跑
# - 在非 cn region 默认会注入 X-Restricted-Status: restricted 头，让 kernel 真的落到合规队列；
#   不带这个头时，metadata 里就算写了合规队列，服务端也会把队列选择静默忽略
# - --no-restricted：在非 cn region 关掉合规模式（极少用到）
# - --restricted：在 cn/boe 上加这个 flag 不会报错但也无意义
bytedcli dorado node start --node-id NxyzABC --region sg                      # 用当前 draft 的 metadata 启动 kernel
bytedcli dorado node start --node-id NxyzABC --metadata-file ./meta.json \
  --region sg                                                                  # 用自定义 metadata 启动 kernel（一次性）
bytedcli dorado node start --node-id NxyzABC --no-restricted --region sg      # 非 cn region 关闭合规模式

# 调试执行 notebook 单个 code cell
# --code / --code-file / --cell-index 三选一；未传 --record-id 时会先启动 kernel
bytedcli dorado node debug-cell --node-id NxyzABC --code 'print("hello")' --region sg
bytedcli dorado node debug-cell --node-id NxyzABC --cell-index 0 --region sg --json

# 仅有 DataLeap 页面 taskId 时，可用 taskId + projectId 自动解析 nodeUid
bytedcli dorado node debug-cell --task-id 100274211 --project-id 12345 \
  --cell-index 0 --region sg

# 复用已有 kernel recordId；不会重新启动 kernel
bytedcli dorado node debug-cell --node-id NxyzABC --record-id 1234567 \
  --no-start-kernel --code-file ./cell.py --region sg

# 探测 kernel 是否就绪（单次探测，几秒内返回 ready:true/false，不执行任何代码）
# 重量级 kernel（如 spark32_python_yarn_cluster）启动后可能要等 1~3 分钟才真正就绪，
# 建议：node start 之后自行按固定间隔重复调用本命令轮询，ready:true 后再批量 debug-cell
bytedcli dorado node kernel-status --node-id NxyzABC --record-id 1234567 --region sg -j

# 查询 nodeId → taskId 映射（需要用 task 相关 API 时使用，如 get-task、list-instances 等）
bytedcli dorado node relation --node-id NxyzABC --region boei18n
# 批量查询（逗号分隔）
bytedcli dorado node relation --node-id NxyzABC,NxyzDEF --region boei18n

# 提交节点上线
# 普通提交上线（不带审批字段）
bytedcli dorado node submit --node-id NxyzABC --project-id {project-id} --region boei18n
bytedcli dorado node submit --node-id NxyzABC --project-id {project-id} --message "deploy via bytedcli" --region boei18n

# 带审批的提交上线
bytedcli dorado node submit-approval --node-id NxyzABC --project-id {project-id} --message "deploy with approval" \
  --review-policy-id 33 --review-users "demo.user1,demo.user2" --custom-alarm-rule-ids 17587 --baseline-ids 33 \
  --agent-config '{"sessionId":"demo-session"}' --region mycis

# 查看节点生产版本历史
bytedcli dorado node history --node-id NxyzABC --region cn
bytedcli dorado node history --node-id NxyzABC --page 1 --size 10 --region cn

# 恢复草稿到指定生产版本
bytedcli dorado node rollback --node-id NxyzABC --commit-id C61P1ztyn0R6dknxP --region cn

# 快捷恢复到最新生产版本
bytedcli dorado node rollback --node-id NxyzABC --latest --region cn

# 重命名 IDE 节点（按 nodeUid 直接改名；node create / dorado URL 中 N 开头的就是 nodeUid）
bytedcli dorado node rename --node-id NxyzABC --name new_task_name --region cn

# 删除 IDE 节点默认只预览；命令会验证节点关系与任务类型，确认后显式加 --yes
bytedcli dorado node delete --node-id <node-id> --region <region>
bytedcli dorado node delete --node-id <node-id> --region <region> --yes
# 仅有 taskId 时自动解析 nodeUid；正式删除要求 node-relations 验证成功
bytedcli dorado node delete --task-id <task-id> --project-id <project-id> --region <region>

# 重命名任务显示名（按 task 视角；与 node rename 走同一后端接口）
# A) 已知 nodeUid：跳过 task→nodeUid 解析
bytedcli dorado task rename --node-id NxyzABC --name new_task_name --region cn
# B) 仅有 taskId：自动用 resolveNodeUidFromTask 解析后再改名
bytedcli dorado task rename --task-id 120933017 --project-id 8026 --name new_task_name --region cn

# 临时查询（exec）
# 前置条件：需要先在 Dorado 平台创建一个专用的临时查询任务作为执行载体
#
# 创建方式 A（Web UI）：
#   Dorado 项目 > 临时查询 > 新建查询；建议把执行引擎切到 Spark，配 dc/cluster/queue 并保存
#   保存后从页面 URL 获取 task-id：`/query/<id>` 中的 `<id>` 就是 task-id，例如 `.../query/123456789?project=cn_123` 中的 `123456789`
#
# 创建方式 B（纯 CLI 三步，无需 Web UI）：
#   ① 在临时查询目录（root-id=-2，folder-id 通过 `folder structure --root-id -2` 获取）建 hsql 任务，必须 --schedule-type 3：
#      bytedcli dorado task create --project-id 123 --folder-id 456 --name demo_adhoc --type hsql --schedule-type 3 --region cn
#   ② 配 cluster + queue（cluster 会自动推导出 dc，不必单独传 --dc）：
#      bytedcli dorado task-draft update <new-task-id> --cluster demo_cluster --queue root.demo_queue --region cn
#   ③ 用 dummy SQL 初始化 conf.configuration（关键步骤，缺这步会让 adhoc exec 直接 fail 且 yarn 不提交）：
#      bytedcli dorado task-draft update <new-task-id> --sql "SELECT 1 AS init" --region cn
#   完成后 `task get <new-task-id> --json` 应能看到 conf.configuration 非 null、cluster/queue/dc 均不为空
#
#   只需创建一次，后续 exec 会自动继承该任务的 dc/cluster/queue 配置
#   ⚠️ --task-id 必须是临时查询任务；若传入已在线的生产任务，命令会拒绝执行以避免修改生产任务状态（--force 可绕过）
#   可通过 DORADO_EXEC_TASK_ID 指定默认执行载体任务；适合按项目保存不同 task-id
#   Doris SQL 可使用 doris_sql 任务作为执行载体；默认/auto 模式只读取 DORADO_EXEC_TASK_ID；显式 --engine-type doris_sql 时才优先读取 DORADO_DORIS_EXEC_TASK_ID

# 简单 SQL（默认同步等待结果）
bytedcli dorado adhoc exec "SELECT count(*) FROM db.table" --task-id 100274211                     # 等待完成并展示结果
bytedcli dorado adhoc exec "SELECT * FROM db.table LIMIT 10" --task-id 100274211 -o result.csv     # 等待完成并下载 CSV
DORADO_DORIS_EXEC_TASK_ID=123456789 bytedcli dorado adhoc exec "SELECT 1" --engine-type doris_sql --project-id 123 --region cn --no-wait  # Doris SQL，异步提交并返回 debugId
# 注意：dorado adhoc exec 在 Hive SQL 路径下，默认无条件注入 `executor.disableManta=true` 以抑制 Manta 监控，不提供 CLI 开关
# 因为 ad-hoc 查询本质是实验性调试，默认不希望在 Manta 上产生 test_check 结果

# 临时查询 — 复杂 SQL（异步提交，稍后查询）
# ⚠️ SQL 含 `--` 开头的注释（hsql 标准注释）时，commander.js 会把这些行当成 CLI 选项报错或显示 help
#    解决：在 SQL 位置参数前加 `--` 分隔符，告诉 commander 后面是位置参数
#    例：bytedcli dorado adhoc exec --task-id 100274211 --region cn -- "$(cat my_sql.sql)"
bytedcli dorado adhoc exec "复杂SQL" --task-id 100274211 --no-wait                                 # 异步提交，返回 debugId
bytedcli dorado adhoc status --debug-id 12977673 --task-id 100274211                               # 查询状态
bytedcli dorado adhoc log --debug-id 12977673 --task-id 100274211                                  # 查看运行日志
bytedcli dorado adhoc result --debug-id 12977673 --task-id 100274211                               # 展示结果
bytedcli dorado adhoc result --debug-id 12977673 --task-id 100274211 -o result.csv                 # 下载 CSV

# 查看临时查询执行历史
bytedcli dorado adhoc history --task-id 100274211                                                  # 查看临时查询执行历史
bytedcli dorado adhoc history --task-id 100274211 --only-mine                                      # 仅查看自己的执行记录

# 解析 Hive SQL 的输出列 schema
bytedcli dorado task sql-schema --sql "select col1, count(*) as cnt from example_db.example_table group by col1" --region sg

# 拉取 Hive 表列信息
bytedcli dorado task fetch-columns --data-source-type hive --idc sg --database-name example_db --table-name example_table --region sg

# 拉取 ClickHouse 表列信息（需指定 --schema-name 为集群名）
bytedcli dorado task fetch-columns --data-source-type clickhouse --idc sg --schema-name cnch_example_cluster --database-name example_db --table-name example_table --region sg

# DECC (Data Exchange & Cross-region Compute)
# 查询 DECC endpoint ID（按数据库名称搜索）
bytedcli dorado decc endpoints --database demo_db --decc-region US-TTP --target-region Singapore-Central --region sg

# 查询 endpoint 下注册的所有 table 及 data ID
bytedcli dorado decc datas --endpoint-id 7221281395346276614 --decc-region US-EastRed --target-region Singapore-Central --region sg

# Flink 实时任务监控与运维日志
# 获取实时任务监控 URL（Grafana 指标、ByteLake、Flink Web UI 等）
bytedcli dorado flink monitor get --task-id 100274211 --region cn
bytedcli dorado flink monitor get --task-id 100274211 --region sg -j

# 列出实时任务运维操作日志（启动/重启/停止/编辑等；start/restart 的 log_id 可用于查看事件时间线）
bytedcli dorado flink operation-log list --task-id 100274211 --region cn
bytedcli dorado flink operation-log list --task-id 100274211 --region sg --page 1 --page-size 20

# 查看单条操作日志详情（含 Flink Web UI 链接和事件时间线，仅 start/restart 类日志有 events）
bytedcli dorado flink operation-log get --log-id 83863872 --region cn
bytedcli dorado flink operation-log get --log-id 83863872 --region sg -j
```

### DECC Region 枚举值

`--decc-region` 和 `--target-region` 支持以下值：`China-North`, `Singapore-Central`, `EU-TTP2`, `US-EastRed`, `EU-Compliance2`, `US-TTP`, `Asia-SouthEastBD`, `Asia_Saas`, `Singapore_Saas`, `Asia_CIS`

## 任务名 -> Task ID（稳定定位）

**首选**：`task list --keyword` 直接按关键词检索（v2 端点，匹配 name/uid/owner），结果行自带数字 `id`（即 Task ID）和 `owner`：

```bash
bytedcli dorado task list --project-id <projectId> --keyword <taskName> --region <region> -j
```

**备选**：若 v2 列表在目标环境不可用，再用 `advanced-search`（IDE 树节点检索）。如果是海外/特定站点的项目，请务必指定正确的 `--site`（例如 `i18n-tt`），避免 JWT 鉴权失败。

```bash
BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli dorado task advanced-search --search-scope owner,name,uid -k <taskName> --region <region> --project-id <projectId> -j
```

在 advanced-search 返回的 JSON 结果中（节点列表在 `data.nodes`）：

- 匹配 `name === taskName` 的节点。
- 该节点的 `uid` 通常带有前缀（例如 `"uid": "t303071958"`）。
- 去除前缀 `'t'` 后的纯数字部分（`303071958`）即为准确的 **Task ID**。

## Supported Regions

| Region            | Description                                                                    | API Endpoint                     | Page Origin                 |
| ----------------- | ------------------------------------------------------------------------------ | -------------------------------- | --------------------------- |
| `cn`              | China (default)                                                                | data.bytedance.net               | —                           |
| `sg`              | Singapore Central                                                              | dataleap-sg.tiktok-row.net       | —                           |
| `sglark`          | Singapore Lark warehouse                                                       | dataleap-sglark.bytedance.net    | —                           |
| `jplark`          | Japan Lark warehouse                                                           | dataleap-jp.byteintl.net         | —                           |
| `uspipo`          | US PIPO warehouse; alias `gp-us`                                               | dataleap-pipo-us.byteintl.net    | —                           |
| `va`              | US East (Virginia)                                                             | dataleap-va.tiktok-row.net       | —                           |
| `mycis`           | ByteIntl MYCIS                                                                 | dataleap-mycis.byteintl.net      | —                           |
| `gcp` / `eu`      | EU Compliance2                                                                 | dataleap.tiktok-eu.net           | dataleap-gcp.tiktok-row.net |
| `us-ttp`          | US TTP; alias `tx` (console host, `tx_<id>` projects)                          | dataleap-bdee.tiktok-us.net      | dataleap-tx.tiktok-row.net  |
| `us-ttp-internal` | US TTP production-network only (reachable only from US-TTP production network) | dataleap-tx.tiktokd.net          | dataleap-tx.tiktok-row.net  |
| `us-eastred`      | US EastRed                                                                     | dataleap.tiktok-eu.net           | —                           |
| `eu-ttp2`         | EU TTP2                                                                        | dataleap-no1a.tiktok-eu.net      | —                           |
| `eu-compliance2`  | EU Compliance2 (IE2); aliases `ie2`, `eu-ttp-gp`                               | dataleap-gp-ttp-eu.tiktok-eu.net | dataleap-ie2.tiktok-row.net |
| `boe`             | BOE (CN)                                                                       | data-boe.bytedance.net           | —                           |
| `boei18n`         | BOE (International)                                                            | data-boe.bytedance.net           | —                           |

`sglark` / `jplark` / `uspipo` / `mycis` are built in and should be called directly with `--region`.

Custom regions can be added via `~/.local/share/bytedcli/data/.dorado.env` or `./.dorado.env`, for example:

```env
DORADO_REGION_PIPOUS_API_BASE_URL=https://dataleap-pipous.example.net/dorado_api
DORADO_REGION_PIPOUS_ALIASES=us_pipo,pipo-us,pipo_us,uspipo
# Optional: set PAGE_ORIGIN when the web UI uses a different domain than the API
# DORADO_REGION_PIPOUS_PAGE_ORIGIN=https://dataleap-pipous-page.example.net
# Optional: set REQUEST_VREGION when the API gateway expects a vregion different from the region key
# DORADO_REGION_PIPOUS_REQUEST_VREGION=us-pipo-prod
# Optional: only set this for Dataleap environments that require browser-session cookies
# DORADO_REGION_PIPOUS_AUTH=session
```

If the built-in region list does not cover the target IDC/region, prefer adding a custom region in `.dorado.env` instead of changing code. `DORADO_REGION_<NAME>_API_BASE_URL` must be the API base URL including its path prefix (for example `/dorado_api` or `/dorado_tx_api`), not the console host from the browser address bar; a bare host makes every request return 404, and bytedcli warns when it detects one. When `DORADO_REGION_<NAME>_SITE` is omitted, Dorado auth follows the global `--site` / `BYTEDCLI_CLOUD_SITE` setting.

`DORADO_REGION_<NAME>_AUTH` supports `jwt|auto|session`. Built-in regions default to `jwt`, except `sglark`, `jplark`, `uspipo`, and `mycis`, which are built in as `session`; custom regions default to `auto`. Use `session` for known special Dataleap environments that require browser-session cookies in addition to JWT. Without `AUTH=session`, keep the normal JWT flow first and only switch to `bytedcli auth login --session` when the target region shows explicit web-auth signals, such as JSON output already including `error.hint` / `error.auth_command`, login redirects, or web-side auth failures.

## Notes

- 需要结构化输出加 `--json`
- `task update --query` / `--query-file` 支持 hsql、fsql、stream_sql 和 doris_sql 类型任务；大 SQL / 长 SQL 写回优先用 `--query-file`
- `task diff` 默认对比最新发布版本与草稿，可用 `--from`/`--to` 指定任意版本
- `task version compare` 是只读、白名单语义对比：不会输出 SQL、认证信息、headers、reader/writer 参数、notebook 内容、环境变量或未识别配置值；需要查看 SQL 正文时仍使用 `task diff`
- `instance list` 需要 `--project-id` 参数
- `instance list --only-self` 通过后端 `onlyQuerySelf` 过滤当前登录用户；不支持指定任意 owner
- DTS 任务会显示源/目标数据库和表信息
- hsql 任务会显示 SQL 代码
- `task get` 文本输出会附带依赖任务 ID，便于快速查看上游关系
- `task demand search` 是分阶段发现命令：只传 `--project-id` 时列需求空间，增加
  `--demand-project-id` 后列模块，再增加 `--demand-module-id` 后查询工作项；`--keyword`
  只用于工作项阶段。项目未配置需求空间时返回空列表，不应继续 bind
- `task demand check` 仅报告当前门禁状态；只有 `is_bound=true` 且
  `abnormal_work_item_count=0` 时 `passed=true`
- `task demand bind/unbind` 默认 dry-run，必须显式 `--yes` 才写入；bind 自动读取任务类型，
  不要求用户手填 `nodeType`。建议同时传 search 返回的 `--work-item-id` 与
  `--work-item-name`，使 CLI 能精确回查不在默认结果窗口中的 work item，并在写入前确认
  它属于所选项目/模块且 `disabled=false`。写请求成功但回读失败时禁止盲目重试，先重新运行
  `task demand check`
- `folder structure` 默认显示任务开发目录（root-id=-1），可用 `--root-id -2` 查看临时查询目录
- `folder create` 在指定项目下创建子目录，`--parent-uri` 为父目录 URI（如 `task:///HrdNGPWr`），可用 `tree-nodes children` 命令获取，`--name` 为新目录名称，可选 `--description` 添加描述
- `node create/get/save/submit/submit-approval` 适用于 python、notebook 和 spark（含 pyspark）任务；`node start/kernel-status` 适用于 python/notebook kernel，`node debug-cell` 适用于 notebook cell；hsql/fsql/stream_sql 等 SQL 草稿使用 `task-draft update`
- `node create` 返回 nodeId（字符串）；需要 taskId 时，用 `node relation --node-id <nodeId>` 查询对应关系，再用 taskId 调用 `get-task`、`list-instances` 等命令
- `node relation` 支持批量查询，多个 nodeId 用逗号分隔；响应中 taskId 与 nodeId 按顺序一一对应
- 仅有 taskId、需要 IDE nodeUid 时，用 `node resolve-uid`（通过 tree-nodes 的 name+type filter 单路径下钻 + node-relations 校验）
- `image list` 查询项目可用镜像列表，返回的 `id` + `name` 用于 `node save --metadata` 中 `configuration.conf` 里的 `operator.parameter.image` 字段；切换镜像时必须同时写入 `id` 和 `name`
- `node save` 调用时 **必须同时传入 `--metadata`**；API 要求 metadata 不能缺失。标准做法是先用 `node get --json` 获取当前草稿，取出 `data.metadata` 字段，按需修改后整体回写，避免覆盖现有配置
- `node save --content-file` 支持直接传入 Python 脚本路径或 notebook (.ipynb) 文件路径
- `node debug-cell` 用 Dorado IDE `node start` 启动 kernel，随后调用 `POST /datalab/v1/kernel/{nodeUid}/kernelId` 获取 `kernelId` 与 WebSocket token，再连接 `/socket-dorado/km/user/channels` 发送 Jupyter `execute_request`。CLI 输出不会打印 token。传 `--record-id --no-start-kernel` 可复用已有 kernel；不传 `--record-id` 时默认启动新 kernel。`--code`、`--code-file`、`--cell-index` 必须三选一；`--cell-index` 会读取当前 notebook 草稿中的 0-based code cell，并把执行后的 `outputs` / `execution_count` 保存回草稿，页面刷新后可见。`--code` / `--code-file` 只做临时代码执行，不改草稿内容。
- `node debug-cell` 和 `node start` 一样遵循合规队列规则：非 cn region 默认带 `X-Restricted-Status: restricted`，需要关闭时显式传 `--no-restricted`。若页面 URL 只有 taskId，优先用 `--task-id + --project-id` 让 CLI 自动 resolve nodeUid，或先执行 `node resolve-uid`。
- **`node debug-cell` 对重量级 kernel（如 `spark32_python_yarn_cluster`，跑在 YARN 队列上）内置了启动重试**：`kernelId`/`token` 在 kernel 启动请求被接受后很快就会返回，但底层 YARN 容器可能还要再等 1～3 分钟才真正起来；过早连接 WebSocket 会被服务端以 close code `1011` 立即断开（表现为 `Notebook WebSocket closed before execute_reply was received`）。只要还没收到任何 kernel 消息，CLI 会自动换新连接重试（间隔 5s），直到 `--timeout-ms`（默认 120000ms）耗尽；一旦已经收到过 kernel 消息（代码已经开始执行），后续连接异常不会重试，避免重复执行。文本模式下若发生过重试，输出会带一行 `note: kernel was still starting up; retried the WebSocket connection N time(s) ...`。若长期在超时前无法就绪，需要去 Dorado 控制台确认 kernel/YARN 应用状态，或加大 `--timeout-ms`。
- Dorado 后端**没有专门的 kernel 健康状态字段**：`kernel/{nodeId}/kernelId` 接口返回的 `kernelId`/`token`/`kernelCreateTime` 只代表"启动请求已受理、记录已创建"，判断 kernel 是否真正可执行代码只能靠连一次 WebSocket 探测。`node kernel-status` 就是把这个探测单独暴露出来：只连接、不发 `execute_request`，几秒内（默认 8000ms，`--timeout-ms` 可调）返回 `ready:true/false` 和 `detail` 说明，不会污染执行历史或重复跑代码。一个 notebook 要连续调试多个 cell 时，推荐流程是 `node start` → 自行按固定间隔重复调用 `node kernel-status --record-id <id>` 轮询直到 `ready:true` → 用同一个 `--record-id --no-start-kernel` 依次调用多次 `node debug-cell`（此时通常第一次尝试就能成功，不会再触发 debug-cell 内置的重试等待）。
- **`node start` 返回完全空白的 `{"code":"Error","message":null,"data":null}`（没有任何可诊断信息）常见根因是 metadata 里 `configuration.innerScheduleParam`/`businessContact`/`inputParams`/`outputParams` 缺失**：新建 notebook 的草稿默认把这几个字段留空，Web IDE 每次 `/start` 前都会补全，直接用草稿原样调用 `/start` 就会触发后端未捕获异常且不返回文本。`startNodeKernel`（即 `node start`/`node debug-cell` 内部启动 kernel 的路径）已经自动补齐这几个字段（`innerScheduleParam` 用固定默认值，`businessContact` 回退到 `metadata.owner`，`inputParams`/`outputParams` 回退到 `[]`），已设置的字段不会被覆盖，因此正常情况下不需要手工处理。仍然遇到空白 error 时，优先怀疑下面这条"kernel 已经启动过"的场景，而不是继续排查 metadata 字段。
- **`node start` 对已经启动过 kernel 的节点重复调用时，后端返回的错误提示不稳定**：符合预期的响应应该是 `{"data":{"status":"error","hints":[{"message":"Kernel has been started, record id: [xxxxx], please refresh the web page"}]}}`，可以从消息里提取已有的 `recordId` 直接复用；但实测同一个"重复启动"场景，后端有时会退化成完全空白的 `{"code":"Error","message":null,"data":null}`。遇到 `node start` 返回空白 error 或 `hints` 里没有 message 时，不要一直换 `--metadata`/`cluster`/`queue` 排查，优先假设"kernel 可能已经启动过"，直接去 Dorado 网页 IDE 刷新确认，或从网页里拿到 recordId 后跳过 `node start`，直接用 `node kernel-status --record-id <id>` 探测现状。
- **在项目根目录用 `node create --type notebook` 新建的 notebook，草稿默认是空的 `computeResourceParam`（`cluster`/`queue` 均为 `null`）**，直接 `node start` 会报 `"Yarn cluster or queue is empty"`；需要先用 `node save --metadata` 把 `configuration.computeResourceParam.cluster`/`queue`/`dc`/`region` 和 `configuration.kernelType` 补上有效值再启动。项目可用的合规队列可以用 `dorado project yarn-queues --project-id <id> --restricted` 查询（会返回 `cluster`/`queue`/`dc`/`region` 的完整组合，直接原样填入即可，不要只抄队列名而丢了 `dc`）。同理，**新建 notebook 的 `content` 是 `null`**，`node start` 前建议先用 `node save --content-file <ipynb.json> --metadata <json>` 至少写入一个合法的空 ipynb 结构（`node save` 要求 `content` 和 `metadata` 必须一起传，缺 `metadata` 会报 `PayloadMissingKey`）。
- `node submit` 默认启用 autoRelease=true（提交即部署），如需关闭可加 `--no-auto-release`
- `node submit-approval` 默认启用 autoRelease=true（提交即部署），如需关闭可加 `--no-auto-release`
- `task commit-approval` 与 `node submit-approval` 的 `--review-policy-id`、`--review-users` 必须由用户按项目显式提供，不要从项目默认配置或页面上下文自动推断
- `node history` 列出节点的生产版本历史（上线部署后的版本），返回版本号、commitId、创建者、更新时间、提交说明
- `node rollback` 将草稿恢复到指定的生产版本，`--commit-id` 和 `--latest` 二选一
- `node rollback --latest` 等价于先 `node history` 取第一个版本的 commitId，再执行 rollback
- 回滚操作只覆盖草稿，不影响线上；如需线上生效，回滚后需重新 submit
- `node rename` / `task rename` 直接调 IDE 节点重命名接口（`POST /datalab/v1/ide/nodes/{nodeUid}/rename`），按 nodeUid 操作，对 python / notebook / spark / HSQL 等所有节点类型通用；改的是节点显示名，不会改任何代码或调度配置
- `task rename` 提供两种入参方式：`--node-id <uid>` 直传跳过解析；`--task-id <id> --project-id <id>` 自动通过 `resolveNodeUidFromTask` 解析。当只有 Dorado URL 里的数字 taskId 时优先用后者
- `node delete` 默认 dry-run，只有显式 `--yes` 才将节点移入可恢复的回收站，不会物理擦除；两种 selector 都只支持 `hsql`、`doris_sql`、`python`、`notebook`、`spark`，并且必须通过 node-relations 验证
- `node delete --skip-relation-verify` 只能用于 dry-run 诊断；未验证候选不能与 `--yes` 组合执行真实删除
- `node save --metadata` 中的 `configuration.dataOutputs` 用于登记任务产出，支持三种类型：
  - `{"type":"hdfs","path":"<hdfs路径>"}` — 登记 HDFS 产出
  - `{"type":"partition","databaseName":"<库名>","tableName":"<表名>","partitions":[{"key":"date","value":"${date}"}],"namespace":"default"}` — 登记 Hive 分区表产出
  - `{"type":"other"}` — 登记其他类型产出
- `node create` 对 `spark` / `python` / `notebook` 在未传 `--data-outputs` 时默认写入 `[{"type":"other"}]`（与命令 help 一致），避免 `node submit` 报「任务产出登记为空」；显式传 `--data-outputs` 时以用户值为准
- 修改产出登记时，建议先用 `node get --json` 获取当前 metadata，在现有配置基础上修改 `dataOutputs` 后整体回写，避免覆盖其他配置字段
- Python 任务提交上线（`node submit`）前，须在 metadata 的 `configuration.conf` 中设置 `operator.parameter.jobType`，默认填 `"cronjob_with_image"`；否则会报"部署类型不能为空"
- `tree-nodes children` 返回的是 IDE 层的 UID-based URI（如 `task:///f{numericId}/{nodeUid}`），与 `folder-structure`/`folder-children` 返回的老式数字 ID 不同；创建 `node create` 时的 `--parent-uri` 必须使用 `tree-nodes children` 返回的 URI，不能用 `task:///f{numericId}` 格式
- `task create --type global_hsql` 创建跨区域 HSQL batch 任务壳子，走普通 `/task/create`，请求体保持 `type=global_hsql`、`typeGroup=global_hsql`；不要把它误分流到 realtime `/realtime/create`。
- `task create --type common-dts-batch` 创建 DTS 批处理任务，创建后可用 `task-draft update` 配置 reader/writer
- `task create --type hive-clickhouse` 创建 Hive→ClickHouse DTS 任务（壳子在 server 端与 `common-dts-batch` 同形态，type 升级在 update-conf 阶段完成）；后续用 `task update-conf <taskId> --task-file <patch.json> --type 'hive->clickhouse'` 把顶层 `type` 升级为 `hive->clickhouse`，并写入 `conf.configuration.reader`（`type=hive`、`engineType=spark`、`sourceType=sql`、`query`、`columns[]`）和 `conf.configuration.writer`（`type=clickhouse`、`chClusterName`、`chDbName`、`chTableName`、`shardColumn`、`shardNum`、`partition`、`partitionTypes`、`columns[]`）
- `task create --type common-dts-stream` 创建 DTS 流式任务壳子（`typeGroup=type=common-dts-stream`，与 batch 的 `common-dts-batch` 相对，适用于 bmq->hive 等流式同步）；该类任务走 `POST /realtime/create?projectId=<id>` 接口，不能用 batch 的 `/task/create`（后端会报“当前操作不支持流任务”），创建后用 `task update-conf` 配置 reader/writer
- `task create --type stream_sql` 创建实时 SQL 任务壳子（`typeGroup=type=stream_sql`），同样走 `POST /realtime/create?projectId=<id>`，不能用 batch 的 `/task/create`；创建命令暂不支持 `--query` / `--query-file` 自动写入 SQL，先建壳子，再用 `task update-conf` 写入已确认的 realtime 配置补丁
- `task create --type java-flink` 创建 Java Flink 实时任务壳子（`typeGroup=stream / type=stream_managed_java_flink`），同样走 `POST /realtime/create?projectId=<id>`，不能用 batch 的 `/task/create`；创建命令暂不支持 `--query` / `--query-file` 或 jar/mainClass 等深字段，先建壳子，再用 `task update-conf` 写入已确认的 realtime 配置补丁
- `task update-conf --type <type>` 可选地覆盖 batch / DTS 草稿顶层 `type`，专为“先用通用壳子创建、再升级到具体 DTS 子类型”的场景设计；realtime stream draft 不支持这个覆盖，不设置时保留 server 上现有 `type`
- `task-draft update` 支持更新队列、集群、调度时间、SQL 代码、任务依赖、跨区域查询配置、DTS 读写配置等
- `task-draft update` 支持小时调度字段；日调度可继续传 `--schedule-time 00:00`，小时调度请按页面原始值传 `--schedule-time <minute>` 与 `--schedule-day <value>`（例如 `--schedule-time 5 --schedule-day 16`）
- realtime stream 任务（如 `kafka2clickhouse`、`stream_channel_*`，或草稿 `conf.typeGroup=stream`）在 `task online` 时自动走 `PUT /realtime/{taskId}/online`，在 `task commit` / `task commit-approval` 时自动走 `PUT /realtime/{taskId}/commit`
- 对 realtime stream 草稿，`task-draft update` 当前只支持 `name` / `description` 和写入 `conf` 的字段（如 `--sql`、`--query-type`、`--source-region-infos`）；`--queue`、`--schedule-time`、`--priority`、`--dependencies`、`--outer-dependencies` 等 top-level 草稿字段会直接报错，避免 `/realtime/{taskId}/draft` 静默丢字段
- `task-draft explain` 会按任务类型分流：`type=hsql` 走 Dorado `resource/explain`，校验 HSQL 草稿或线上版本语法；`type=stream_sql` 走 `realtime/sqlCheck/{taskId}`，校验目标版本的完整实时 SQL 配置；支持 `--online` / `--version <n>` 校验指定发布版本配置
- `task-draft explain` 的 `${DATE}` / `${date}` / `${date-1}` 替换、`--template-var k=v` 与 `--auto-strip-mustache` 仅用于 HSQL 分支；`stream_sql` 分支直接提交目标版本的完整 `conf` 给后端校验
- `task-draft explain` 不适用于 DTS；如果任务是 DTS，请改用 `dts-draft explain`
- `task update-conf` 支持直接保存 stream 类实时任务（包括 `kafka2clickhouse`、`common-dts-stream` 的 bmq->hive）的抓包 `conf`；当任务 `conf.typeGroup=stream` 或 `type` 形如 `stream_channel_*` 时，CLI 会自动走 `POST /realtime/{taskId}/draft`，并保留原始顶层 `conf.typeGroup`
- 保存 DTS 流式任务（common-dts-stream）草稿时，可用 `task update-conf` 的 `--queue`/`--cluster`/`--dc`/`--priority`/`--engine-id`/`--enable-failover`/`--owner` 指定运行位置；这些字段只会附加到 realtime 草稿 body（不传则维持最小 body，避免影响 kafka2clickhouse 仅改运行参数的保存）。运行队列建议先用 `project yarn-queues --task-type common-dts-stream` 找到资源最空的流式队列
- **DTS 流式任务（bmq->hive）端到端保存方案**：用 `task create --type common-dts-stream` 建壳子后，按下面三步组装 `conf` 再 `task update-conf` 保存。Agent 在用户只给出 bmq 源信息时，应主动补齐 hive 表、队列与资源配置，不要直接用空/默认值保存：
  1. **缺少 hive 目标表时，提醒用户提供，不要尝试根据 bmq 自动建表**：目前没有“直接根据 bmq topic 创建 hive 表”的能力——bmq topic 自身元数据（`bmq topic get`/`bmq topic list`）只有 qps/分区/owner/psm，**不含字段 schema**，无法据此推导出 hive 表结构。因此当用户未提供 writer 的 `databaseName`/`tableName` 时，应直接提醒用户提供已存在的 hive 目标表（库名+表名），不要自行猜测或新建。若用户已有目标表但缺字段映射，可用顶层 `hive` 命令（注意不是 `dorado hive`）查已存在表的字段：`bytedcli hive ddl <db> <table> --region <region>` 拿到 `CREATE TABLE` 字段与分区，再写入 `conf.configuration.writer.parameter`；reader 侧设 `fieldSyncMode:auto` + operator 设 `autoParseConnectors:true` 让平台对齐字段，但目标 hive 表必须由用户事先建好并真实存在
  2. **队列必须显式带且要选充足的**：先 `dorado project yarn-queues --project-id <id> --task-type common-dts-stream --region <region>` 列出流式队列，再结合资源使用（Allocated Rate 越低、Free CPU/Free Memory 越多越充足）挑一个，保存时务必带齐 `--queue`/`--cluster`/`--dc`（三者要同属一个机房/集群）；缺队列会落到默认或无法部署
  3. **资源配置（operator.parameter.commonConfig）按吞吐合理设置，不要照搬默认**：页面“资源设置”各项对应 `commonConfig` 字段——`TaskManager 个数=tmNum`、`单 TaskManager CPU 数=containerVcoresD`、`单 TaskManager 内存(MB)=tmMemoryMb`、`单 TaskManager slot 数=slotsPerTm`、`JobManager CPU 数=jmMemoryVcoresD`、`JobManager 内存=jmMemoryMb`、`启用智能资源=enableIntelligent`。默认 `tmNum=4 / containerVcoresD=4 / tmMemoryMb=4096 / slotsPerTm=4 / jmMemoryVcoresD=3 / jmMemoryMb=4096 / enableIntelligent=false` 适合中等吞吐；低吞吐 topic 可下调 `tmNum`（如 1~2）与单 TM 资源以省队列资源，高吞吐再上调 `tmNum`/`slotsPerTm`。`slotsPerTm` 一般与 `containerVcoresD` 对齐，`tmMemoryMb/slotsPerTm` 单 slot 内存不要过低。也可开 `enableIntelligent:true` 交由平台智能调度
- `dts-draft explain` 使用 Dorado `resource/explain` 校验 DTS reader SQL（`conf.configuration.reader.parameter.query`），支持 `typeGroup=dts`、`typeGroup=common-dts-batch` 和 `typeGroup=hive->clickhouse`；如果 DTS reader 是 table 模式、没有 `reader.parameter.query`，命令返回 `status=not_applicable`，不是失败
- `dts-draft explain` 同样支持 `--date`、`--template-var k=v`、`--online`、`--version <n>`；若任务详情无法推导 `dc` 或 `ownerUserName`，调用时需显式传 `--dc` / `--username`
- `task-draft update --query-type` 设置查询类型（如 `FLEXIBLE_UNION`、`COMPLEX_QUERY`），写入 `conf.configuration.operator.parameter.queryType`
- `task-draft update --source-region-infos` 设置跨区域数据源配置，接受 JSON 数组，每个元素包含 `geo`（区域标识）和 `yarnQueue`（含 region/dc/clusterName/queue），可选 DECC 字段（`deccDataId`/`deccEndpointId`/`deccTransmissionTaskId`/`deccTransferJobId`/`owner`），写入 `conf.configuration.operator.parameter.sourceRegionInfos`
- `task-draft update` DTS 参数说明（`common-dts-batch` 类型任务）：
  - DTS 草稿更新统一通过 `task-draft update --dts-read-*` / `--dts-writer-*` 做增量字段映射；尤其是 LarkSheet 等 reader 的 `url`、`urls`、`sheetType`、`templateParam` 这类参数，按调用方传值原样写入，不重建整段 reader/writer 配置
  - **Reader 参数**（写入 `conf.configuration.reader`）：
    - `--dts-read-type`：reader 类型（如 `hive`），写入 `reader.type`
    - `--dts-read-idc`：reader IDC（如 `sg`）
    - `--dts-read-source-type`：数据源模式，`sql`（SQL 查询读取）或 `table`（指定库表读取）
    - `--dts-read-query`：SQL 查询语句（`sourceType=sql` 时使用）
    - `--dts-read-database-name` / `--dts-read-table-name`：库名和表名（`sourceType=table` 时使用）
    - `--dts-read-url` / `--dts-read-urls`：源 URL；LarkSheet 场景下 `--dts-read-url` 会同时写入 `url` 与单元素 `urls`
    - `--dts-read-sheet-type` / `--dts-read-template-param` / `--dts-read-data-source-name`：LarkSheet 等 reader 的补充参数
    - `--dts-read-columns`：列定义 JSON 数组，格式 `[{"type":"string","name":"col1"}]`；`sourceType=table` 时可加 `extraType`、`description` 字段
    - `--dts-read-partitions`：分区定义 JSON 数组（`sourceType=table` 时使用），格式 `[{"name":"date","type":"string","value":"${date}"}]`
    - `--dts-read-connector-type`：连接器类型（如 `hive`）
  - **Writer 参数**（写入 `conf.configuration.writer`）：
    - `--dts-writer-type`：writer 类型（如 `clickhouse`），写入 `writer.type`
    - `--dts-writer-idc`：writer IDC（如 `sg`）
    - `--dts-writer-cluster`：集群名称
    - `--dts-writer-database-name` / `--dts-writer-table-name`：目标库名和表名
    - `--dts-writer-columns`：列定义 JSON 数组，格式 `[{"type":"string","name":"col1"},{"type":"int64","name":"col2"}]`
    - `--dts-writer-partitions`：分区定义 JSON 数组，格式 `[{"name":"date","type":"TIME","value":"${date}"}]`
    - `--dts-writer-shard-column`：hash 分布列
    - `--dts-writer-shard-num`：分片数（如 `1200`）
    - `--dts-writer-append-mode`：写入模式（默认 `1`），`1`（覆盖写）、`0`（追加写）、`-2`（删除分区）、`2`（覆盖写2）、`11`（1 + 数据强一致检查）、`12`（2 + 数据强一致检查）
    - `--dts-writer-connector-type`：连接器类型（如 `clickhouse`）
  - `--dts-read-source-type` 传入时有严格校验：`sql` 必须同时传 `--dts-read-query`；`table` 必须同时传 `--dts-read-database-name` 和 `--dts-read-table-name`
  - 不传 `--dts-read-source-type` 时，其他 DTS 参数支持局部更新，只传需要修改的字段即可
- `task-draft update --dependencies` 是**全量替换**：接受 `taskId[:offset:offsetsType]` 格式的逗号分隔列表，offset 默认 0、offsetsType 默认 set；调用方必须提供期望保留的完整列表
- `task-draft update --add-dependency` 是安全增量追加：参数可重复，默认 `offset=0`、`offsetsType=set`；命令先读取 version/-1 草稿，原样保留已有依赖对象及顺序，只在末尾追加尚不存在的依赖。默认仅预览，确认后加 `--yes`；已存在时 no-change，不重复写入
- 可先运行 `task dep-recommendations` 查看候选 producer，再由调用方明确选择一个或多个 task ID 传给 `--add-dependency`；不要自动接受全部推荐
- 推荐结果只是 SQL 表引用对应的候选，不代表都应建立强依赖。选择前同时读取 `task get`：排除已有同 region dependencies；读取 `${date}` 分区通常使用 offset `0`，`${date-N}` 按业务语义选择对应 offset；SQL 明确使用 `max_pt(...)`、注释“不强依赖”或容忍最近可用分区时，默认不要添加，除非用户明确要求
- `id=null / isOnlineTask=false` 的 `hive_partition-sensor` 表示 Sensor 尚未生成。用 `task hp-sensor create` 创建：命令会重新获取下游任务的当前 recommendation，只接受指定 table 对应的未创建 HPSensor，并在多条匹配时要求通过 `--path` / `--namespace` / `--frequency` 消歧；不要伪造 ID，也不要手工重建 recommendation payload
- `task hp-sensor create` 默认 dry-run，检查 payload 后显式加 `--yes`。`--region` 负责 Dorado 路由和认证，`storageRegion` 与 recommendation `namespace` 独立；`path` 必须原样保留，不能改写固定分区、日期占位符或尾部 `/`
- `--storage-region` 可省略：CLI 先读取精确匹配目标表的在线非 Sensor producer `data-outputs`，再回落到已验证映射（`sg -> sg`、`gcp -> gcp_hive`、`us-ttp -> us-ttp`）。producer 值冲突时要求显式参数；映射只可作为候选，agent 必须展示依据并取得用户明确确认，再运行输出中带 `--storage-region <candidate> --yes` 的命令。不得从 namespace、Coral `hive.table.region`、CID 或普通 region 名自行推导
- `task hp-sensor create --region us-ttp` 已按 Web 抓包内置 BDEE `dorado_tx_api` + `X-Titan-Token` + `https://dataleap-tx.tiktok-row.net/` 页面根 Referer；无需手工切到 `us-ttp-bdee` 或设置 `DORADO_REGION_US_TTP_AUTH=titan`。该规则仅适用于 HPSensor `sensorDrafts` 创建链路，不要推断其他 US-TTP endpoint 都有相同 header 契约
- `task dep-recommendations --json` 会额外返回 `uncreated_hp_sensors`、`uncreated_hp_sensor_count` 与每条记录的 `creatable`。优先消费这个结构化摘要，不要自行从完整列表拼 payload；CLI 已合并同一未创建 HPSensor 的完整记录与空字段重复记录，并兼容 `vRegion / priority / version = null`
- recommendation path 若含 `date=/model_version=/app_id=` 这类空分区值，直接创建会返回 `code=1140`。CLI 会在 POST 前阻断；先运行 `bytedcli --json hive detail sample_database sample_table --region <region>` 查看 `latestPartitionName`，或用 `hive rows` 查看完整分区，再通过 `--create-path '<key=value/...>'` 显式提交。`--path` 仍用于匹配原 recommendation，不要混用
- 创建响应中的正整数 `sensor.id` 是后续依赖追加的权威 ID；可先 `task get <sensor.id>` 验证，再用该 ID 执行 `task-draft update --add-dependency` dry-run。不要依赖 recommendation 回查取 ID：SG 实测创建后仍会出现新的 `id=null` / `#2` 候选，重复运行 create 会继续创建重复 Sensor。也不要根据即时响应里的 `version=-1 / isOnlineTask=false` 调用额外 online 接口
- HPSensor 是平台管理的公共 `SENSOR` 项目对象，普通用户通常没有常规编辑/删除权限；只在没有真实 producer 时创建，已有实际产出任务时优先依赖 producer
- producer 不一定是 HSQL；`hive_partition-sensor` 等类型只要有正整数 task ID、`isOnlineTask=true` 且分区语义匹配，也可以作为显式选择的依赖
- 写入流程应先运行不带 `--yes` 的 dry-run，检查 `added`、`already_present`、`before_count/after_count`，再取得用户确认执行 `--yes`。若错误明确说明 POST 已成功但回读校验失败，不要盲目重试；先重新 `task get` 确认依赖是否已保存
- 增量写入在 POST 前会复读草稿并在写后回读校验，但 Dorado 当前没有已确认的 ETag/version 条件写能力，最后一次 GET 到 POST 之间仍存在小的并发覆盖窗口
- `task-draft update --outer-dependencies` 配置跨机房依赖，格式为 `taskId@region[:offsets[:offsetsType]]` 逗号分隔；例如 `--outer-dependencies "306220763@sg"` 表示依赖 sg 机房的任务 306220763，默认 offsets=0、offsetsType=set；支持多 region 混合（如 `"100@sg,200@va:0:set"`）
- `task-draft test` 返回 Debug ID，并默认输出本次调试提交的 SQL（`debug_sql`）；`--json` 输出会在 `data.debug_sql` 返回该 SQL。可用 `adhoc status` 查询状态，用 `adhoc result` 获取结果。HSQL/DTS 等 batch 草稿任务走 `PUT /task/{id}/draft/test`；shell 任务走 `PUT /task/{id}/debug/v2` 并提交完整草稿上下文（含 commonTemplate、依赖、scheduleDateTimes）；doris_sql / spark / python / notebook 这类 node-type 任务走 IDE debug endpoint。HSQL/shell 等支持 conf 形态的任务可通过 `--disable-manta` 抑制 Manta 监控触发。支持 `--input-params` 传入自定义参数覆盖任务代码中的 `{{param}}` 占位符（只需 name/debugVal 两字段，debugVal 为调试代入值；与 task rerun 的 name/paramValue/type 不同）。支持 `--input-table-map` 透传 Dorado 多环境输入表映射（元素形态为 `mappingSourceType/mappingType/metaType/mappingValues`），用于让后端在调试时使用选中的上游测试表；CLI 不解析 SQL、不改写表名。node-type 任务提交前 CLI 会先把 `{{param}}` 替换成 `debugVal`，避免后端忽略 runOptions 中的临时参数覆盖值；Python node 调试会保留/继承草稿里的 `image`、`resources`、`targets` 等运行字段，若缺运行参数再补 `jobType="cronjob_with_image"`、`version="3.7"`、`packages=[]`、`envs=[""]`，规避 Dorado 返回“任务设置信息填写不全”或未进入自定义镜像
- `task dep-recommendations` 解析任务 SQL 并推荐产出相关表的上游任务，便于快速配置任务依赖
- `node save --image-name/--image-id` 支持为 python/notebook/spark 三种任务类型更新 Docker 镜像；save 时会自动获取当前草稿并检测任务类型，将镜像写入对应位置（spark 写入 `conf.configuration.operator.parameter.image`，python 写入 `conf.configuration.operator.parameter.image` 并设置 `jobType`，notebook 写入 `executeParam.image`）
- `node create` 同样支持 `--image-name/--image-id`，适用于 `--type python/notebook/spark`；创建后会自动补写镜像配置（平台 create API 不完全持久化嵌套 conf，CLI 自动做一次 save 补充）
- Spark 任务创建时默认 `--language python --spark-version 3.2`，可通过 option 覆盖
- 三种非 SQL 任务的镜像存储位置不同（spark/python 存在 `conf.configuration.operator.parameter.image`，notebook 存在 `executeParam.image`），`node create` 和 `node save --image-name/--image-id` 会自动处理差异
- `project yarn-queues` 支持 `--task-type` 按任务类型过滤队列（如 `global_hsql`）
- `project yarn-queues --restricted` 走「合规视图」：注入 `X-Restricted-Status: restricted` 请求头，服务端只返回合规授权的队列子集和合规默认队列；输出会同时打印 `Default queue:` 一行。该开关只对 i18n / 非 cn region（sg、va、mybd、gcp、us-ttp、us-eastred、eu-ttp2、eu-compliance2、boei18n 等）有意义，cn 没有合规队列概念，加不加无差别
- `task sql-schema` 解析 Hive SQL 语句，返回输出列的 name 和 type，可用于构造 `--dts-read-columns` 参数
- `task fetch-columns` 拉取 Hive 或 ClickHouse 表的列元数据（名称、类型、是否分区列、是否主键等），可用于构造 `--dts-read-columns` 或 `--dts-writer-columns` 参数；ClickHouse 表需额外传 `--schema-name`（集群名）
- `decc endpoints` 按数据库名称查询 DECC endpoint ID，需指定 `--decc-region`（源区域）和 `--target-region`（目标区域）
- `decc datas` 按 endpoint ID 查询该 endpoint 下注册的所有 table 及其 data ID
- `us-ttp`、`us-eastred`、`eu-ttp2` 等 TTP 区域使用 Dataleap JWT 认证（`x-dataleap-jwt-token`），CLI 会先按该 region 在 `site.ts` 里配置的 **cloud site**（如 `i18n-tt`、`eu-ttp`、`us-ttp`）取 ByteCloud JWT，再向 SG 的 `/user/jwt` 换成 Dataleap JWT；因此 `eu-ttp2`、`eu-compliance2` 请先执行 **`bytedcli --site eu-ttp auth login`**（不要用错成仅 `i18n-tt`）；`us-ttp` 等则对应用 `--site us-ttp` 或 `i18n-tt`。
- **`eu-compliance2`（IE2）**：控制台在 **`dataleap-ie2.tiktok-row.net`**，Dorado API 在 **`dataleap-gp-ttp-eu.tiktok-eu.net/dorado_tx_api`**（与 Hive `eu-compliance2` 同 API 主机）；CLI 请求带 **`Origin`/`Referer` = IE2 控制台**、`x-bcgw-vregion: ie2`。任务草稿里 `region`/`dc` 常为 `eu-ttp-gp` / `ie2`，与 CLI `-r eu-compliance2` 对应。
- **OG 分层（`gcp` / `eu-ttp2` / `eu-compliance2` / `us-ttp-bdee`）**：这些 region 的草稿写入会经过 OG 字段打标检查，CLI 已内置对应绕过，无需手动加环境变量：
  - `task`/`folder structure`/`task online` 等批处理 API 使用 sg 颁发的 Dataleap JWT。登录的 `--site` 必须匹配该 region 在 `site.ts` 里配置的 **cloud site**（CLI 用 `cloudSiteForRegion(region)` 取对应 ByteCloud JWT，不是固定 `eu-ttp`）：`eu-ttp2` / `eu-compliance2` 用 **`bytedcli --site eu-ttp auth login`**，而 **`gcp` 的 cloud site 是 `i18n-tt`，须用 `bytedcli --site i18n-tt auth login`**（用错成 `--site eu-ttp` 会因取不到 `i18n-tt` 的 ByteCloud JWT 导致鉴权失败）。
  - **`tree-nodes children`、`node create`、`task advanced-search`、`node resolve-uid`、`folder create`（IDE）** 等走 `getIdeHeaders`：这些 region 的 datalab IDE 网关拒绝 `X-Dataleap-Jwt-Token`（`invalid tagging: header`），CLI 固定改用 **Titan**（`X-Titan-Token`）；其他 TTP region 在有 Dataleap session cookie 时走区域 `/user/jwt`，否则回退 Titan。`auth login --session` 对这些 region 的 IDE 不是必需条件。
  - **`task-draft update`（batch `POST /task/{id}/draft`）** 的 OG 拒绝 GET-draft 回传的多余字段（`id`/`projectId`/`status`/`version`/`deployed`/`slaTime` 等，`invalid tagging: body`）。CLI 只发字段白名单 body，并在 `dc` 为空时按 region 默认队列回填 `dc`/`region`（`gcp`→`useast2a`/`i18n_gcp`，`eu-ttp2`→`no1a`/`eu-ttp-no`，`eu-compliance2`→`ie2`/`eu-ttp-gp`）。
  - **batch `task-draft test`（`PUT /task/{id}/draft/test`）** 的 OG 拒绝顶层 `engineType` / `username`（`not tagged`）。CLI 在上述三 region 省略这两字段；**仍发送** `dc` / `cluster` / `queue`（队列不丢）。引擎类型留在草稿 `conf.parameter.engineType`，调试身份走 JWT。shell 任务不走该 batch draft/test 端点，而是走 `PUT /task/{id}/debug/v2`。
- **`node create` OG body**：上述 IDE 网关对 `POST .../nodes` 的 `metadata`/`content` 字段有 OG 白名单（与 HSQL `task-draft update` 同类）。CLI 会先以最小 body 创建节点壳，再通过 `saveNodeDraft` 写入 spark/python 配置与代码；`--parent-uri` 须来自 `tree-nodes children` 返回的 URI（如 `task:///` 或 `task:///f{numericId}/{nodeUid}`），不要用 `task:///f{folderId}` 数字 folder ID。当前实测 **spark / python** 可创建；**notebook** 在 IE2 上 `POST .../nodes` 仍返回业务 `Error`（非 OG），需在控制台创建或待平台开放 API。
- 若错误为 **`Failed to parse JSON`** 且预览里出现 **`Restrict Notice`**：多半是打到了 **`dataleap-ie2.../dorado_tx_api`** 而非 **`dataleap-gp-ttp-eu...`**；请使用含 IE2 主机拆分的构建后重试。
- `gp-us` 是 `uspipo` 的兼容别名，使用 DataLeap 页面态 session cookie，首次使用前先执行 `bytedcli --site i18n-bd auth login --session`

## References

- `references/dorado.md`

### 从 DataLeap URL 解析 nodeId

用户经常给出 DataLeap 页面 URL，格式类似：

```
https://dataleap-{region}.tiktok-row.net/dorado/development/node[/notebook]/{taskId}?project={region}_{projectId}&version=-1
```

URL 中的数字 ID 是 **taskId**；对 `dorado node get` / `node save` 等 IDE 接口需要的是 **nodeUid**（`N...`）。

**Step 1：解析 URL**

- `taskId`：URL 路径中的数字，如 `/node/305851780` → `305851780`
- `projectId`：query 参数 `project={region}_{projectId}` 中去掉 region 前缀后的数字（可能不带 region）
- `region`：从 hostname 推断，如 `dataleap-sg` → `sg`

**Step 2：调用 `dorado node resolve-uid`**

```bash
bytedcli dorado node resolve-uid --project-id {projectId} --task-id {taskId} --region {region} -j
```

该命令通过 `get-task` 获取任务名称和类型，然后向 `tree-nodes children` 发起带 `name+type` filter 的请求，后端会只返回沿路径向下命中的那个子节点；沿着这条单路径逐层下钻到匹配的叶子节点后，再用 `node-relations` 与入参 `taskId` 校验；输出中 `verified: true` 表示校验通过。
