---
name: bytedance-aeolus
description: "Query, explore, edit, and save Aeolus BI/data analytics datasets via bytedcli: list datasets/dashboards, inspect dataset fields/model info, edit computed fields, batch download/upload fields via XLSX, execute SQL, run/save visual queries, resolve/query reports, patch report chart styles, query charts/dashboards, manage Query Editor folders/files/templates/temp tables/task records, submit/rename/delete query tasks, check task results, and download Excel/CSV outputs. Use when tasks mention Aeolus, BI dashboards, charts, datasets, filters, data analytics queries, Query Editor, Shuttle, data templates, or organizing/moving dashboards and datasets between folders (看板/数据集 文件夹、移动、归类)."
---

# bytedcli Aeolus (Data Analytics Platform)

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

- List dashboards and datasets you have access to
- List recently visited resources and search resources by keyword
- Get dataset field details (dimensions and metrics)
- Batch download/upload dataset fields as XLSX (display name / expression friendly edits)
- Get dataset model info (underlying data source, query, and table schema)
- Create a single-source hive/click_house dataset from a table or custom SQL (`dataset-create`)
- Update custom SQL on an existing sql-node dataset (`dataset-update-sql`)
- Update an existing computed dimension/metric expression in place while preserving its field ID (`dataset-update-fields`)
- Read or update Fabric dataset TTL and scheduled/manual sync mode (`dataset-sync settings`)
- Delete or restore a Dataset with guarded lifecycle commands (`dataset-delete`, `dataset-restore`); deletion is recoverable by default and `--permanent` is irreversible
- Browse the dashboard/dataset folder trees and move resources between folders: `dashboard folder list`, `dashboard move`, `dataset-folder list`, `dataset-move`
- Execute SQL queries against datasets
- Run visual dataset queries and save them as shareable Aeolus report links
- Resolve report URLs to metadata and full dimMet lists, then execute saved reports for either data rows or the underlying SQL (via `report query --format`)
- Read or patch a saved report's chart display style (`report style get` / `report style update`) without rebuilding the query
- Query a dataQuery URL with field-name shortcuts: `report query --url ... --group-by ... --metrics ... --filter ... --top-n ...`
- Get or preview a single chart with `chart get` / `chart query`, including local temporary chart JSON and read-only filter merge explanation
- Discover repeatable report/dashboard filter syntax and option values: `report filters`, `dashboard filters`, `filter options`
- Discover charts/public filters from an Aeolus dashboard URL and query one or all chart reports with bounded preview rows: `dashboard query --url ...`
- Explore Aeolus BI platform data
- Manage Query Editor folders, query files, and task records (rename/delete)
- Run ad-hoc SQL queries via Query Editor (Hive runner by default, including single-day `--adhoc-date` placeholder execution and multi-day Hive batch ranges via `${date}` / `${DATE}`, or ClickHouse when SQL matches the browser Query Editor CH task, e.g. `params{'...'}`)
- Browse Query Editor saved templates: `query-editor template list` (list templates under a folder/node) and `query-editor template get` (fetch a template's SQL)
- Upload a CSV file and create a Query Editor temporary table with inferred schema: `query-editor tmp-table create`
- Manage Shuttle projects, templates, queues, and BATCH tasks through its VA control plane while selecting the task data region separately

In examples, `AEOLUS_REPORT_URL` and `AEOLUS_DASHBOARD_URL` mean the actual user-provided Aeolus URLs. Do not replace them with fabricated hosts or commit real resource IDs into docs.

## 前置条件

- 使用通用调用方式：`references/invocation.md`

> 执行前缀见 `references/invocation.md`；下面示例直接写 `bytedcli`。

## Supported Regions

Dataset / report API 默认域名与 `src/api/aeolus/site.ts` 一致；控制台入口可能因租户不同而异。

| Region      | Description                                    | Default API host                                                                                                                       |
| ----------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `cn`        | China                                          | `https://data.bytedance.net`                                                                                                           |
| `sg`        | Singapore (TikTok row)                         | `https://aeolus-sg.tiktok-row.net`                                                                                                     |
| `va`        | US East (TikTok row)                           | `https://aeolus-va.tiktok-row.net`                                                                                                     |
| `euttp`     | EU-TTP / EU Compliance (GCP)                   | `https://aeolus-eu-ttp.tiktok-eu.net` (office); `https://aeolus-eu-ttp.bytedance.net` (prod). Override: `BYTEDCLI_AEOLUS_EUTTP_ORIGIN` |
| `euttp2`    | EU-TTP2 / NO1A (aliases `eu-ttp2` / `no1a`)    | `https://aeolus-no.tiktok-eu.net`. Override: `BYTEDCLI_AEOLUS_EUTTP2_ORIGIN`                                                           |
| `eupipo`    | EU PIPO / IE2                                  | `https://aeolus-clover-pipo.tiktok-eu.net`                                                                                             |
| `mycis`     | MYCIS                                          | `https://aeolus-mycis.byteintl.net`                                                                                                    |
| `hrbimycis` | HRBI MYCIS (alias `hrbi_mycis` / `hrbi-mycis`) | `https://people-aeolus.byteintl.net`                                                                                                   |
| `mybd`      | MYBD                                           | `https://aeolus-mybd.sinf.net`                                                                                                         |
| `sglark`    | Singapore Lark                                 | `https://aeolus-sglark.bytedance.net`                                                                                                  |
| `usttpusts` | US TTP USTS                                    | `https://aeolus-tx.tiktok-usts.net`                                                                                                    |
| `usbd`      | US ByteDance                                   | `https://aeolus-usbd.byteintl.net`                                                                                                     |

## Invocation Throttling

Call Aeolus commands serially by default. bytedcli does not provide a cross-command lock, and Aeolus operations often read or mutate shared remote state. Do not launch multiple `bytedcli aeolus ...` commands in parallel through parallel tool calls, background shell jobs, or batch runners. This is especially important for data queries, Query Editor runs, task submissions, and dataset/report/dashboard edits. For batch work, process one target at a time and wait for the previous command to finish before starting the next.

## Quick start

For report/dataQuery URLs, prefer this workflow by default:

1. `resolve-report` to get the dataset ID.
2. `dataset-fields` to confirm dimensions/metrics and partition fields.
3. `dataset-model-info` to inspect the underlying query and lineage.
4. If logical dataset SQL fails or only returns `dummy`, inspect `system.query_log` to locate the backing physical `aeolus_data_db_*`.`aeolus_data_table_*`.
5. Query the physical table directly.

```bash
# List authorized datasets and dashboards (region is required)
bytedcli aeolus list-authorized -r va --limit 20

# Filter by type (dashboard or data_set)
bytedcli aeolus list-authorized -r cn --type data_set

# List recently visited resources
bytedcli aeolus resource recent -r va --limit 20

# Search resources by keyword and type
bytedcli aeolus resource search -r va --keyword sample --type dashboard,report --page 1 --page-size 20

# Resolve a dataQuery/report URL to dataset IDs before querying
bytedcli aeolus resolve-report --url "$AEOLUS_REPORT_URL"

# Resolve a report URL to metadata and full dimMet list
bytedcli aeolus report resolve --url "$AEOLUS_REPORT_URL"

# Fetch data from a saved report (auto-resolves config from URL)
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL"

# Rebuild a scratch query from the same URL using dataset field names
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL" \
  --group-by "country,platform" --metrics "revenue" \
  --filter "p_date[lastSync]=1" --top-n 10 --sort-by "revenue"

# Get the underlying SQL for a saved report (still issues a real query)
bytedcli aeolus report query --format sql --url "$AEOLUS_REPORT_URL"

# Download the saved report/history result to a file
bytedcli aeolus report download --url "$AEOLUS_REPORT_URL" --output ./report-export

# Get dataset field details (dimensions and metrics)
bytedcli aeolus dataset-fields -r va 1576311

# Get the edit-time dimMet map with source-table bindings (needs BYTEDCLI_AEOLUS_OPEN_API_TOKEN)
bytedcli aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>

# Get dataset model info plus inspection summary (sync mode, partitions, hot fields, filter-rule metadata hints)
bytedcli aeolus dataset-model-info -r va --app-id <APP_ID> --dataset-id <DATASET_ID>

# Download the native Aeolus dataset-fields XLSX template for batch editing
bytedcli aeolus dataset-fields-download -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --output ./dataset-fields.xlsx

# Upload the edited native template in review mode first (recommended; default is dry-run)
bytedcli --json aeolus dataset-fields-upload -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --file ./dataset-fields.xlsx

# After review passes, execute the real upload
bytedcli aeolus dataset-fields-upload -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --file ./dataset-fields.xlsx --yes

# Create a dataset from a hive/clickhouse source table (default dry-run; pass --yes to submit)
bytedcli aeolus dataset-create -r va --app-id 1000252 --name demo-dataset --db-name demo_db --table-name sample_table --cluster-name default --data-source-type hive --dc sg --parent-id 13361

# Create a dataset from custom SQL (SQL node; use single quotes so ${date} is not expanded by the shell).
# If automatic ClickHouse recommendation fails, copy dataSourceId from a compatible Dataset model.
bytedcli aeolus dataset-create -r va --app-id 1000252 --name demo-sql-dataset --db-name demo_db --cluster-name default --data-source-type hive --dc sg --parent-id 13361 --clickhouse-data-source-id 10001 --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\'''

# Update custom SQL on an existing sql-node dataset (default dry-run; pass --yes to save)
bytedcli aeolus dataset-update-sql -r va --app-id 1000252 --dataset-id 999001 --sql-file ./demo.sql

# Update an existing computed field in place (default dry-run; pass --yes to save)
bytedcli aeolus dataset-update-fields -r va --app-id 1000252 --dataset-id 3436909 --field "accuracy=[right_count]/nullIf([total_count], 0)"

# Preview the default recoverable deletion; exact name is a required safety lock
bytedcli aeolus dataset-delete -r sg --app-id <appId> --dataset-id <dataSetId> --expect-name "demo-canary"

# Apply the recoverable deletion after reviewing the dry-run
bytedcli aeolus dataset-delete -r sg --app-id <appId> --dataset-id <dataSetId> --expect-name "demo-canary" --yes

# Restore a recycled Dataset; add --target-folder-id when the original folder is unavailable
bytedcli aeolus dataset-restore -r sg --app-id <appId> --dataset-id <dataSetId> --expect-name "demo-canary" --target-folder-id 0 --yes

# Permanently delete only a recycle-bin Dataset; irreversible and double-confirmed
bytedcli aeolus dataset-delete -r sg --app-id <appId> --dataset-id <dataSetId> --expect-name "demo-canary" --permanent --confirm-id <dataSetId> --yes

# Add a source table join and expose a metric; use --json + --dry-run to inspect payload first
bytedcli --json aeolus dataset-add-source-table -r cn --app-id <appId> --dataset-id <dataSetId> --db-name demo_db --table-name sample_table --join-from-table sample_prev_table --join-key key1 --join-key key2 --metric-field score --field-descr score=points --increment-field updated_at --dry-run

# List the dataset folder tree; folder ids feed --target-folder-id and dataset-create --parent-id
bytedcli aeolus dataset-folder list -r cn --app-id <appId>

# Restrict the folder listing to one space (public, private, share, official)
bytedcli aeolus dataset-folder list -r cn --app-id <appId> --space public

# Preview moving datasets into a folder; the target space is derived from --target-folder-id
bytedcli aeolus dataset-move -r cn --app-id <appId> --id <dataSetId> --target-folder-id <folderId>

# Apply the move for several datasets at once
bytedcli aeolus dataset-move -r cn --app-id <appId> --id 100,101 --target-folder-id <folderId> --yes

# Move datasets back to a space root; folder id 0 needs an explicit --space
bytedcli aeolus dataset-move -r cn --app-id <appId> --id <dataSetId> --target-folder-id 0 --space public --yes

# Trigger an Aeolus dataFactory dataset sync/backfill range captured from the dataManage page
bytedcli aeolus dataset-sync trigger -r cn --app-id <appId> --dataset-id <dataSetId> --start-date "2026-04-22 00" --end-date "2026-05-06 23" --queue-name root.demo_queue --max-parallelism 5

# Check sync/backfill instance status for the same business time range
bytedcli aeolus dataset-sync status -r cn --app-id <appId> --dataset-id <dataSetId> --start-date "2026-04-22 00" --end-date "2026-05-06 23"

# Read Fabric default and node-specific sync rules (dataSetType=34)
bytedcli aeolus dataset-sync settings get -r sg --app-id <appId> --dataset-id <dataSetId>

# Preview a fixed-TTL and sync-mode update; no write is sent by default
bytedcli aeolus dataset-sync settings update -r sg --app-id <appId> --dataset-id <dataSetId> --ttl-days 60 --sync-type manual --expect-ttl-days 30 --expect-sync-type scheduled

# Apply the reviewed Fabric settings update and verify the asynchronous readback
bytedcli aeolus dataset-sync settings update -r sg --app-id <appId> --dataset-id <dataSetId> --ttl-days 60 --sync-type manual --expect-ttl-days 30 --expect-sync-type scheduled --yes

# If direct logical SQL fails, inspect query_log to find the actual physical table name
bytedcli aeolus query -r va 1576311 "SELECT event_time, query FROM system.query_log WHERE query LIKE '%aeolus_data_table_%' ORDER BY event_time DESC LIMIT 20"

# Query the physical Aeolus table directly after locating it
bytedcli aeolus query -r va 1576311 "SELECT reporting_ad_id, max(pangle_rolling3d_dollar_cost) AS pangle_rolling3d_dollar_cost FROM \`aeolus_data_db_xxx\`.\`aeolus_data_table_xxx\` WHERE p_date = '2026-03-01' GROUP BY reporting_ad_id ORDER BY pangle_rolling3d_dollar_cost DESC LIMIT 10"
```

## Recommended workflow for report/dataQuery links

1. Use `resolve-report` to get the dataset ID from the report URL.
2. Use `dataset-fields` to confirm dimensions/metrics and identify partition fields.
3. Always use `dataset-model-info` before assuming logical dataset SQL will work. Many Aeolus datasets expose derived fields in metadata, but `aeolus query` may only succeed against the backing physical ClickHouse table, not a logical dataset alias like `[DatasetName]` or `"2231500"`.
4. If direct logical dataset SQL fails with errors like `unknownTable`, `unknownIdentifier`, or only returns `dummy`, inspect:
   - `modelInfo.nodeConf[].query` for the source logic
   - `modelInfo.nodeConf[].lineageInfo` for upstream tables
   - `system.query_log` via `aeolus query` to find the real physical table name used by Aeolus (often `aeolus_data_db_*`.`aeolus_data_table_*`)
5. Query the physical Aeolus table directly, and deduplicate with `GROUP BY` / `max(...)` when repeated rows exist per key.
6. Do not stop at `SELECT * LIMIT 1` returning only `dummy`; that usually means you still need the physical table, not that the dataset is unusable.

### Failure signatures

- `unknownTable` when using a logical dataset name or dataset ID as the table
- `unknownIdentifier` / missing field errors even though the field exists in `dataset-fields`
- `SELECT * LIMIT 1` or `select dummy` only returning a `dummy` column

These are all strong signals to switch from logical dataset SQL to physical-table discovery.

Other recurring `aeolus query` error signatures and what they actually mean:

- `指标内含有非聚合字段 ...`：bracket 形式的指标显示名（`[指标名]`）会自动展开成**非聚合表达式**，外面要么包一层聚合函数，要么改用物理表裸列自己写聚合。
- `聚合函数中包含聚合函数`：该 bracket 字段本身已是预聚合指标，不要再套 `sum()` / `count()`。
- `SQL语法错误，请检查面板中字段的语法是否正确`（无行列号）：常见于 `[日期]` 这类分区宏用法不对，或 ORDER BY 里引用了 SELECT 别名；逐段删减定位，不要按普通 ClickHouse 语法错误排查。
- `存在未知字段、或缺失字段权限`（`SELECT *` 触发）：显式列出需要的字段，不要 `SELECT *`；该错误不会告诉你具体是哪个字段。
- `引擎查询失败`（无任何细节）：用 `bytedcli --http-debug ... aeolus query ...` 看原始响应；常见原因是数据集需要特定队列/权限，或保存的查询配置已失效。
- `不支持参数{params}取值为{value}`（占位符未插值）：数据集不支持当前请求形态（典型如不支持 Open API SQL 直查的受限数据集类型）；CLI 会附带 hint。

### End-to-end fallback example

```bash
# 1) Resolve the report URL
bytedcli aeolus resolve-report --url "$AEOLUS_REPORT_URL"

# 2) Inspect semantic fields and partition fields
bytedcli aeolus dataset-fields -r va <DATASET_ID>

# 3) Inspect the underlying model/query
bytedcli aeolus dataset-model-info -r va --app-id <APP_ID> --dataset-id <DATASET_ID>

# 4) Find the backing physical table from recent Aeolus queries
bytedcli aeolus query -r va 2231500 "SELECT event_time, query FROM system.query_log WHERE query LIKE '%aeolus_data_table_%' ORDER BY event_time DESC LIMIT 50"

# 5) Query the physical table directly
bytedcli aeolus query -r va 2231500 "SELECT reporting_ad_id, sum(placement_dollar_cost_1d/100000) AS cost FROM \`aeolus_data_db_xxx\`.\`aeolus_data_table_xxx\` WHERE p_date = '2026-04-07' AND placement = 'Pangle' GROUP BY reporting_ad_id ORDER BY cost DESC LIMIT 5"
```

## Dataset VizQuery (无需写 SQL 的数据集可视化查询)

`aeolus viz-query` 对应浏览器里 Aeolus 报表/数据集页面发起的 `POST /aeolus/vqs/api/v2/vizQuery/query`，
走和 `aeolus query` 一致的 Titan Passport cookie 鉴权。因此它在 `hrbi_mycis` 等
没有 Query Editor 权限的 region 上也能工作，非常适合：

- 只想快速拿某个 dataset 的 row count / 单维度聚合结果；
- 浏览器抓到一份 payload，想复用结构化参数而不是自己拼 SQL；
- 需要和 Aeolus 前端行为完全一致（含权限与过滤下推）。

默认情况下不需要显式传 `--data-source-id`。当某些数据集在 CLI 构造请求下仍返回
`aeolus/unknown`，并且你在浏览器抓到的成功 payload 明确包含 `dataSourceId` 时，
再把该值作为 `--data-source-id` 传入，或直接复用整份 `--body-file`。

实现和排障上还有几个关键点：

- 鉴权优先复用 Titan Passport cookie（与 `aeolus query` 同一路径），避免依赖 QE session，这样才能覆盖 `hrbi_mycis` 等没有 Query Editor 权限的 region。
- 请求体需要补齐顶层 `schema`、`display`、`originalSchema`；服务端会校验这些字段是否存在。
- 响应的真实数据行通常在 `data.vizData.datasets[]`，键名是各字段 `unique_id` 的字符串形式；解析时需要结合 `data.columns[]` 元数据重建列顺序。
- 若无 `--body-file`，默认构造应尽量贴近浏览器 payload：维度列优先使用原始 `dimMetId` 作为 `id` / `groupById` / `locations.dimensions`，指标列保留聚合前缀 id（如 `count_159...`），并默认带浏览器常见的 table `display.conf` / `fieldsFormat` 与 schema where filter 包装。

### VizQuery quick start

一维 count（对应用户示例：dataset=2889 昨日数据条数）：

```bash
bytedcli --site i18n-bd aeolus viz-query \
  -r hrbi_mycis --app-id 667 --dataset-id 2889 \
  --dim-met '{"dimMetId":1590328014122,"name":"app_id","expr":"`app_id`","roleType":1,"aggregation":"count(","dataType":"int"}' \
  --where '{"dimMetId":1590328014119,"name":"partition_date","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'
```

参数说明：

- `--dim-met`（可重复）：一个维度或指标，推荐 JSON 对象形式。必填 `dimMetId` / `name` / `expr`；
  `roleType=0` 为维度、`1` 为指标。指标的聚合函数处理要看 `expr`：
  - 当 `expr` 为原始列（如 `dau`、`dnu`）时，需补 `aggregation`（如 `count(` / `sum(`）。
  - 当 `expr` 已自带聚合（如 `sum(dnu_non_reinstall)/count(distinct p_date)` 这类"日均/比率"指标）时，**不要再传 `aggregation`**，否则后端会报"参数类型不应为 Date"等校验错误。判别依据：在 `aeolus dataset-fields` 输出中 `expr` 已含 `sum(`/`count(`/`avg(` 等。
  - 也支持紧凑的 `dimMetId=1,name=xxx,expr=\`xxx\`,roleType=1,aggr=count(`。
  - **map 类型字段（如 `map<string,int>` 的 flag 计数列）必须按 key 访问**：加 `"mapKey":"<key>"`，此时 `name`/`expr` 可省略（缺省为 key 本身）。例如
    `--dim-met '{"dimMetId":123,"roleType":1,"aggregation":"sum(","mapKey":"my_flag"}'`
    等价于页面上「求和(map_field.my_flag)」。不带 `mapKey` 直接对 map 列做 `sum(` 会被引擎报
    `Illegal type Map(String, Int64) of argument for aggregate function sum` 拒绝。
    ⚠️ Aeolus 平台 report 原始 JSON（`reqJson`）里的 roleType 语义是 `1=维度、2=指标`，与 CLI 的 `0=维度、1=指标` 不同；从浏览器 payload 或 `report resolve` 输出照抄 dimMet 时必须换算，照抄会被 `roleType must be 0 (dim) or 1 (metric)` 拒绝。
- `--where`（可重复）：筛选条件 JSON，需 `name` / `dimMetId` / `op`。`val` 在 preset / `is_null` / `is_empty` 上可省略。
  `op` 可用 `thisWeek` / `last` / `last:week` / `contains` / `not_in` / `having:>` 等别名，CLI 编成 VQS wire。
  绝对日期区间可传 `{"op":"range","val":["2026-08-01","2026-08-03"],"dataTypeName":"date"}`；
  CLI 会规范化为页面/VQS 使用的 `between`、完整日边界时间与 `dateMode:absolute`。
- `--limit`：行数上限，默认 1000。
- `--timeout-ms`：单次请求超时，单位毫秒；适合大数据集或高峰期查询较慢时显式放宽。
- `--transform`：`table`（默认）或 `chart`。
- 响应里的 `queryHistoryId` 可拼成 `<region baseUrl>/pages/dataQuery?appId=<appId>&id=<queryHistoryId>&sid=<datasetId>` 打开 web 页面复现该次查询；CLI 取数与 web 端"展示 X 条"结果一致。`<region baseUrl>` 取上文 region 表里对应行的 host（例如 `va` → `https://aeolus-va.tiktok-row.net`、`cn` → `https://data.bytedance.net`、`jplark` → `https://aeolus-jp-lark.bytedance.net` 等），实现侧以 `src/api/aeolus/site.ts` 的 `REGION_CONFIG[region].baseUrl` 为准。

### `aeolus report create`

Use `aeolus report create` when the user needs an openable/shareable Aeolus page, not just a one-off query result. The legacy flat alias `aeolus save-viz-query` still works but is hidden from help.

Typical cases:

- Turn a verified `viz-query` into a saved report page
- Share "yesterday users", "distinct app_id list", or a simple aggregate result
- Produce a visual page link for `hrbi_mycis`, where Query Editor is unavailable

Examples:

```bash
# Save a grouped page (yesterday distinct users by email)
bytedcli aeolus report create \
  -r hrbi_mycis --app-id 667 --dataset-id 2926 \
  --name "yesterday-users" \
  --dim-met '{"dimMetId":1590328021777,"name":"email","expr":"`email`","roleType":0}' \
  --where '{"dimMetId":1590328021772,"name":"pdate","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'

# Save an aggregate page (yesterday row count)
bytedcli aeolus report create \
  -r hrbi_mycis --app-id 667 --dataset-id 2926 \
  --name "yesterday-count" \
  --dim-met '{"dimMetId":1590328021772,"name":"pdate","expr":"`pdate`","roleType":1,"aggregation":"count("}' \
  --where '{"dimMetId":1590328021772,"name":"pdate","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'
```

Agent Guidance:

- `aeolus report create` calls `POST /aeolus/api/v3/dataMart/report`, and shareable links use `/aeolus/pages/dataQuery?...&rid=<reportId>&sid=<datasetId>`.
- `hrbi_mycis` defaults to `dataSourceId=10035`; other regions require explicit `--data-source-id` when no built-in mapping exists.
- Save responses may return `data.reportId`, `data.id`, or `data.lastInsertId` with `code=0`.
- Before `POST`/`PUT`, the CLI executes the final saved `reqJson` as a one-row VizQuery preflight.
  A query/schema/filter failure aborts without saving, so a success result means the returned page
  configuration was accepted by the same VQS path used by DataQuery.
- Aggregate payloads should stay on the normal aggregate path: use IDs like `count_<dimMetId>`, keep `sourceType: "aggr"`, set `realMetricTableRouteConfig.isRealMetricQuery = false`, and do not emit `real_metrics_*` / `metricConf`.
- To avoid page-side query errors, keep browser-parity metadata such as `query.dimMetList`, `schema.customConfig.fields.details=[]`, `originalSchema`, `requestId`, and `locale: "zh_CN"`.
- If the browser save payload is already available, prefer reusing it directly; otherwise keep the CLI-generated payload as close to browser shape as possible.
- `--table-calc` writes `schema.tableCalculation` on `report create` / `report update`. Types: `percentOfTotal`, `difference`, `percentDifferenceFrom`, `runningTotal`, `rank`, `percentile`, `movingCalculation`. Example: `--table-calc percentOfTotal` or `--table-calc amount=rank`.
- `--mini-chart` writes `display.conf.miniChart.enabled=true` on create/update.
- `--period-compare` writes `schema.periodCompare` plus derived `sourceType: "period_compare"` measures. Types: `relativeRatio` (aliases `wow` / `relative`), `lastyearRatio` (`yoy`), `lastweekRatio`, `lastmonthRatio`. Return types: `ratio`, `store`, `value`, `diff`, `store_ratio`, `reversed_store_ratio`. Examples: `--period-compare relativeRatio`, `--period-compare lastyearRatio=ratio`, `--period-compare '{"periodType":"relativeRatio","retType":"diff","field":"amount"}'`. A type is required. The default shift is the first date/datetime dimension; if none exists, pass `shift`. Derived measure names look like `amount_relativeRatio_ratio`; ids look like `table_<dateId>_1d_<measureId>_<retType>`. Do not write `query.periodCompare`. This only applies to `schema.measures`, not `double_axis` `subMeasures`.
- `--totals` writes `query.calculation.combined`. Default is row totals. Also: `--totals col`, `--totals row,col`, `--totals '{"row":true,"col":false}'`.
- `--forecast` writes `schema.forecast` with `granularity:"day"`. Default is 7 days: `--forecast`, `--forecast 7`, `--forecast 7d`, or `--forecast '{"step":7,"granularity":"day"}'`. The default time pill is the first date/datetime dimension. Do not write `query.forecast`. Week/month forecast is not accepted. CN console may hide the forecast UI even when the schema field is saved.
- `--chart-type <type>` saves the report as a chart instead of the default `table`. Supported family types: `table`, `measure_card`, `line`, `column`, `bar`, `bar_percent`, `area`, `pie`, `double_axis`, `histogram`, `pivot_table`, `funnel`, `combination`, `sankey`, `gauge`, `progress`, `waterfall`, `scatter`, `radar`, `word_cloud`, `bilateral`, `map`. Page aliases that reuse a family preset: `raw_table`, `column_percent`, `column_parallel`, `bar_parallel`, `area_percent`, `annular`, `rose`, `circle_views`, `comparative_measure_card`, `measure_trend`, `waterfall_change`, `scatter_map`, `gis_map`, `gis_mark_map`, `gis_heat_map`, `gis_pulse_map`, `gis_trace_map`, `gis_bar_map`. `trend_table` and `okr_table` are not create types: VizQuery rejects a displayType-only swap. The chart's query transform is not the same string as the displayType: `series` for cartesian/combo/map families, `pie_series` for `pie`/`annular`/`rose`, `histogram` for `histogram`, `funnel` for `funnel`, `table` for `table`/`raw_table`/`pivot_table`, and `measure_card` for measure cards / gauge / progress. `map` needs a dimension with a geographic role. `double_axis` with two or more measures puts the first measure on the main axis and the rest on `schema.subMeasures`.

```bash
# Save a line chart of a metric over a date dimension
bytedcli aeolus report create -r va --app-id 1000252 --dataset-id 3436909 \
  --name "accuracy-trend" --data-source-id 668 --chart-type line \
  --dim-met '{"dimMetId":100,"name":"p_date","expr":"`p_date`","roleType":0}' \
  --dim-met '{"dimMetId":200,"name":"accuracy","expr":"`accuracy`","roleType":1}' \
  --set legend.legendPos=bottom --set label.visible=true \
  --field-format "accuracy=percent"

# Period comparison (环比), row totals, and a 7-day forecast
bytedcli aeolus report create -r va --app-id 1000252 --dataset-id 3436909 \
  --name "accuracy-wow" --data-source-id 668 --chart-type line \
  --dim-met '{"dimMetId":100,"name":"p_date","expr":"`p_date`","roleType":0}' \
  --dim-met '{"dimMetId":200,"name":"accuracy","expr":"`accuracy`","roleType":1}' \
  --period-compare relativeRatio --totals --forecast 7d
```

`--set` writes dotted keys into `display.conf`. `--field-format` writes a per-measure number format. `--conf-file` accepts `report style get --json` output or a bare conf object. The same three options exist on `report update`. `--table-calc` / `--mini-chart` / `--period-compare` / `--totals` / `--forecast` write analysis on create/update only.

### `aeolus report style get` / `aeolus report style update`

Use these when the query (dimensions / metrics / filters) is already correct and only the chart appearance should change. `report style update` reads the existing `reqJson` and patches `display.conf`; it does not rebuild the query. `report update` still rebuilds the query from `--dim-met`.

```bash
# Inspect displayType, styleFamily, allowedConfKeys, paths[], and per-measure formats
bytedcli --json aeolus report style get --url "$AEOLUS_REPORT_URL"

# Preview a patch (default dry-run)
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" \
  --set legend.legendPos=bottom --set label.visible=true \
  --field-format "amount=ms" --field-format "rate=permil"

# Array index from paths[].path, e.g. axisMeasure.0.titleEnable
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" \
  --set axisMeasure.0.titleEnable=true

# Apply the same patch
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" \
  --set legend.legendPos=bottom --set label.visible=true \
  --field-format "amount=ms" --yes

# Edit the get JSON and write it back
bytedcli --json aeolus report style get --url "$AEOLUS_REPORT_URL" > ./style.json
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" --conf-file ./style.json --yes
```

Agent Guidance:

- Always run `report style get --json` first. Copy `--set` paths from `paths[].path`. Do not invent `--legend-pos` flags. `paths[]` is `{path,value,type,source}`: `source=saved` is on this report; `source=preset` is allowed for this family but not set yet.
- Numeric path segments are array indices. `--set axisMeasure.0.titleEnable=true` updates that slot and keeps the array.
- JSON `styleFamily` / `allowedConfKeys` list the top-level keys valid for **this** chart type. A table key such as `tableStyle` is rejected on a line chart; `dualAxis` is only valid on `double_axis`; `majorMeasure` is only valid on measure cards.
- Do not copy one chart's `display.conf` onto another type. `column_percent` / `raw_table` / `annular` reuse the `column` / `table` / `pie` key families.
- Field-format presets: `money`, `money_wan`, `auto` (unit scale 万/亿), `default` (page 自动), `int`, `percent`, `permil` (千分比), `raw` (原始值), `ms`, and 数字 units `千`/`万`/`百万`/`千万`/`亿`/`K`/`M`/`B`. `--field-format "*=percent"` applies to every measure. A full numFormat object is also accepted (`type` is `none`/`digit`/`percent`/`permil`/`custom`).
- Default is dry-run. Pass `--yes` to PUT. The command writes `display.conf` and `schema.display.conf` together, and writes both `display.fieldsFormat` and `schema.measures[].format.numFormat`.
- A `--conf-file` `displayType` must match the saved report. A top-level conf key that is not on this chart type is rejected.
- `report style update` only patches `display.conf` and measure number formats. `--table-calc` / `--mini-chart` / `--period-compare` / `--totals` / `--forecast` stay on `report create` / `report update`.

### `aeolus report update`

`aeolus report update --report-id <id>` overwrites an existing saved report in place via `PUT /aeolus/api/v3/dataMart/report`, keeping the same report ID so any dashboard referencing it stays intact. It takes the same options as `report create`, but **`--report-id` is required** here (for `report create` it is optional). `report create` always creates a new report. `report update` rebuilds the whole query and analysis from the flags you pass. To keep 同环比 / 总计 / 预测, pass `--period-compare` / `--totals` / `--forecast` again.

```bash
bytedcli aeolus report update -r cn --app-id 1000252 --dataset-id 3436909 \
  --report-id 174615 --data-source-id 668 --chart-type table \
  --dim-met '{"dimMetId":200,"name":"amount","expr":"`amount`","roleType":1,"aggregation":"sum("}'
```

### `aeolus dashboard create` / `aeolus dashboard build`

Use `aeolus dashboard create` for an empty dashboard, or `aeolus dashboard build --spec <file>` to build a complete multi-chart dashboard from a JSON spec in one call: it creates each report, auto-lays-out a 12-column masonry `componentTree`, then creates the dashboard embedding all charts (a single `POST /aeolus/api/v3/dashboard/dashboard`).

```bash
# Empty dashboard
bytedcli aeolus dashboard create -r cn --app-id 1000252 --name "demo-dashboard"
# Multi-chart dashboard from a spec
bytedcli aeolus dashboard build -r cn --spec ./dashboard.json
# List published dashboard versions
bytedcli --json aeolus dashboard version list -r cn --app-id 1000252 --dashboard-id 123456
# Fetch a sheet's simpleSheet payload
bytedcli --json aeolus dashboard sheet get -r cn --app-id 1000252 --dashboard-id 123456 --sheet-id 789012
# Compare a local sheet payload with the current online simpleSheet payload
bytedcli --json aeolus dashboard diff -r cn --app-id <appId> --dashboard-id <dashboardId> \
  --sheet-id <sheetId> --payload-file ./simple-sheet.json
# Save/publish an existing dashboard from an editor-compatible PUT payload
bytedcli --json aeolus dashboard update -r cn --app-id 1000252 --dashboard-id 123456 \
  --payload-file ./dashboard-update.json --publish --version-descr "add funnel" \
  --auto-delete-oldest-version --dry-run
# List dashboard charts and public filters from a dashboard URL
bytedcli --json aeolus dashboard query --url "$AEOLUS_DASHBOARD_URL"
# List structured dashboard public/report/chart filters without querying data
bytedcli --json aeolus dashboard filters --url "$AEOLUS_DASHBOARD_URL"
# Query one dashboard chart with bounded preview rows
bytedcli --json aeolus dashboard query --url "$AEOLUS_DASHBOARD_URL" \
  --report-id 345678 --filter "country=SG" --sort-by "revenue" --top-n 10
# Download every report from one dashboard sheet, one file per report
bytedcli --json aeolus dashboard download --url "$AEOLUS_DASHBOARD_URL" \
  --all-reports --output ./dashboard-export
```

Spec shape (`dashboard.json`):

```jsonc
{
  "appId": 1000252,
  "name": "demo-cost-monitor",
  "datasetId": 3436909,
  "dataSourceId": 668,
  "charts": [
    {
      "type": "measure_card",
      "name": "total",
      "dimMet": [{ "field": "amount", "agg": "sum", "as": "total" }],
      "where": [{ "field": "bill_type", "op": "in", "val": ["normal"] }],
      "style": { "numFormat": "money_wan" },
    },
    {
      "type": "table",
      "name": "by product",
      "dimMet": [{ "field": "product_name" }, { "field": "amount", "agg": "sum" }],
      "style": { "topN": 25, "conditionalFormat": "bar" },
    },
  ],
}
```

Agent Guidance:

- `dashboard build` resolves each chart's `dimMet[].field` / `where[].field` to its dimMetId via dataset metadata, so the spec uses field **names**, not IDs.
- A chart's `type` may be omitted or set to `"auto"` to recommend one from the dimMet shape: no measure → `table`; 0 dimensions → `measure_card`; 1 date-dimension + 1 measure → `line` (trend); 1 dimension + 1 measure → `column`; 1 dimension + ≥2 measures → `double_axis`; ≥2 dimensions → `table`. Pass an explicit `type` to override.
- `style.numFormat` takes **either a full numFormat object** (any prefix / suffix / unit / precision / type — not limited to money) **or a shortcut string**. Shortcuts: `"money"` (￥ auto 万/亿), `"money_wan"` (￥ fixed 万), `"auto"` (plain number, auto-scaled 万/亿, no currency), `"default"` (page 自动), `"int"`, `"percent"`, `"permil"` (千分比, wire `type:"permil"`), `"raw"` (原始值, wire `type:"none"`), `"ms"`, and named 数字 units `"千"`/`"万"`/`"百万"`/`"千万"`/`"亿"`/`"K"`/`"M"`/`"B"`. `style.fieldFormat` may use `"*"` to apply one format to every measure. For any other unit, pass the object directly, e.g. a count in 万: `{ "kSep": true, "precision": 1, "unit": "万" }`, or bytes→GB: `{ "precision": 2, "unit": { "ratio": 1073741824, "symbol": " GB" } }`, or a plain suffix: `{ "kSep": true, "precision": 0, "suffix": " 人" }`. Custom tiered rules (`type:"custom"`) only accept a full object copied from a saved report.
- `style.set` is a dotted-path overlay into `display.conf`, same language as `report style update --set`. Example: `{ "legend.legendPos": "bottom", "label.visible": true }`. `style.fieldFormat` maps measure name/id to a preset or numFormat object. `style.conf` is a raw `display.conf` overlay.
- `style.conditionalFormat`: `"bar"` (in-cell data bar) / `"heatmap"` (color scale) / `"tag"` (up/down/flat arrows + colored text by sign, best on diff measures), or a full conditionalFormat object. `style.topN`: keep the top N dimension rows, sorted by the measure desc.
- More analysis configs (reference fields by **name**): `style.sort` `[{ "field": "amount", "order": "desc" }]` (sort by a dimension or a measure); `style.referenceLine` `[{ "name": "目标", "value": 100, "field": "amount" }]` (fixed-value line; `field` defaults to the first measure).
- `layout` is optional per chart; omitted charts auto-flow in a 12-column masonry (measure_card spans 4 columns, table/line span 12, others 6). Pass an explicit `layout` (`width` px / `x` / `gridIndex`) to override.
- Auth reuses `getAeolusHeaders` (Titan Passport cookie), same as `report create`. `appId` and `dataSourceId` are required; when `dataSourceId` is unknown, read it from a `viz-query --http-debug` SQL comment (`data_source_id: <id>`).
- `dashboard update` mirrors the dashboard editor's `PUT /aeolus/api/v3/dashboard/dashboard` call and adds the required `App-Id` header. Use it when modifying an existing dashboard sheet/layout with a browser-compatible payload containing fields such as `id`, `updateDashboard`, `updateSheets`, `publish`, `versionDescr`, and `deleteVersionId`.
- When publishing, pass `--publish --version-descr <text>`. By default the command sets `update_dashboard_resource=true`; use `--no-update-dashboard-resource` only when intentionally preserving the raw payload behavior.
- Aeolus dashboards can have a small published-version cap. `--auto-delete-oldest-version` first calls `dashboard version list` and, when there are already 3 versions and no explicit `--delete-version-id`, adds the oldest version ID to `deleteVersionId`.
- Always run `bytedcli --json aeolus dashboard update --dry-run ...` before a write to inspect the final payload. Then rerun without `--dry-run` to save/publish.
- `dashboard diff` is read-only. It compares a local JSON payload file with the current online simpleSheet from `sheet/simpleSheet`, canonicalizes object key order, preserves array order, and reports stable leaf/path changes with bounded value summaries plus local/remote hashes. It does not save, update, publish, delete, sync, create a new dashboard, or retrieve dashboard data rows.
- `dashboard query` without `--report-id` / `--all-reports` is discovery-only: it lists chart `reportId` / `chartId`, names, display types, and dashboard public-filter summaries. With `--report-id`, it returns a stable single-report result containing `chartId`, `reportId`, `name`, `status`, `columns`, `rows`, `rowCount`, `returnedRows`, `truncated`, and `fileGuidance`. With `--all-reports`, it queries reports serially and isolates individual failures in `failed[]`.
- `dashboard filters` is read-only filter discovery. It returns grouped `dashboard_public`, `report_level`, and `chart_schema` filters with `name`, `dimMetId`, `op`, `defaultValue`, `source`, `overridable`, and dataset/report context. Use it before writing repeatable `--filter` expressions.
- `dashboard query --filter` matches a dashboard filter candidate by **name** first (public filter name / report whereList condition name); an **all-digit** field then matches by `dimMetId` — the only handle for unnamed report whereList conditions, typically dates: `--filter "<dimMetId>[gte]=<date>" --filter "<dimMetId>[lte]=<date>"` (find dimMetIds via `dashboard filters`). Filters matching no candidate fall back to dataset named filters and need dataset access; board-only permission gets a 403 whose hint lists this report's candidates.
- `dashboard query --with-sql` adds per-report `sqlList` (with `sqlWarning` when SQL could not be fetched). The executed SQL is where symbolic date filters (`lastSync` etc.) show up resolved to real partition dates — use it to confirm data freshness on daily-snapshot boards. Costs up to two extra serial requests per report; the SQL can contain sensitive table/column names, keep it out of public logs.
- `dashboard query` is a bounded preview command. Treat `truncated:true` as a signal to use `dashboard download` for CSV/XLSX file exports. `--top-n` requires `--sort-by` and becomes the effective preview limit; otherwise `--limit` defaults to 100.
- `dashboard query` returns every row the server sent for the requested limit, including charts that paginate in the browser. `rowCount` is the display row count and `truncated` is decided by the server-side row count, so a pivot result that expands into more table rows than the limit is still reported as `complete` when nothing was cut.
- `pivot_table` results are the expanded table, so they include the chart's subtotal and grand-total rows (their dimension cells carry the chart's total label). Filter those rows out before summing a pivot result, otherwise every value is counted twice.
- `dashboard download` writes VizQuery export files under `--output`; it does not print report payload rows to stdout. In `--json` mode, read `data.results[]` and `data.failed[]`; batch mode continues after individual report failures. Inspect each result's `completeness`: `complete`, `limit_reached`, or `unknown`.
- `style.tableCalculation`, `style.miniChart`, `style.periodCompare`, `style.totals`, and `style.forecast` write the same analysis blocks as `--table-calc` / `--mini-chart` / `--period-compare` / `--totals` / `--forecast`. `combination` is a `--chart-type`; `double_axis` with two measures uses `schema.subMeasures` for the second axis.

### `aeolus dashboard folder list` / `aeolus dashboard move`

`folder list` is how you discover the folder ids that `dashboard move --target-folder-id` and `dashboard create --parent-id` expect. Dashboards live in a `public` or `private` space; `move` derives the target space from `--target-folder-id`, so `--space` is only needed for folder id `0` (the space root). Moving across spaces is supported and the dashboard adopts the target folder's space.

```bash
# Folder tree for one app, every space
bytedcli aeolus dashboard folder list -r cn --app-id 1000252
# Only the public dashboard space
bytedcli --json aeolus dashboard folder list -r cn --app-id 1000252 --space public
# Preview a move; nothing is written without --yes
bytedcli aeolus dashboard move -r cn --app-id 1000252 --id 123456 --target-folder-id 858092
# Apply the move
bytedcli aeolus dashboard move -r cn --app-id 1000252 --id 123456 --target-folder-id 858092 --yes
# Move back to the private space root
bytedcli aeolus dashboard move -r cn --app-id 1000252 --id 123456 --target-folder-id 0 --space private --yes
```

### `aeolus dataset-add-fields`

Add computed dimensions/metrics to an existing editable dataset (the same `dataSetV2` edit path as the dataManage page), without rebuilding the dataset.

```bash
bytedcli aeolus dataset-add-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --metric "accuracy=[right_count]/[total_count]" \
  --dim "category=get_json_object(\`payload\`, '\$.cat')"

# Preview the change without saving
bytedcli --json aeolus dataset-add-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --metric "accuracy=[right_count]/[total_count]" --dry-run
```

Agent Guidance:

- `--dim`/`--metric` are repeatable and take `name=expression`; metric expressions may reference other fields via `[name]`.
- Reads `allDataSetInfoV2`, appends computed fields (metrics `mapType=1`, dims `mapType=0`, both `isUpstreamField=false`), pre-checks via `preCheckDimMetList`, and saves with `dataSetV2`.
- A freshly created/edited dataset can briefly report `saveForbidden`/`updating`; the command retries with backoff.
- Duplicate field names are rejected; pick a unique name or remove the existing field first.

### `aeolus dataset-update-fields`

Update one or more existing computed field expressions in place. The default run performs the same full-model precheck as a save but does not write; pass `--yes` only after inspecting the result.

```bash
# Precheck only (default dry-run)
bytedcli --json aeolus dataset-update-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --field "accuracy=[right_count]/nullIf([total_count], 0)"

# Save after reviewing the dry-run result
bytedcli --json aeolus dataset-update-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --field "accuracy=[right_count]/nullIf([total_count], 0)" --yes
```

Agent Guidance:

- `--field` is repeatable and takes `existing name=new expression`; split on the first `=`, so the expression itself may contain `=`.
- This command does not rename or recreate fields. It preserves the persisted field ID, dimension/metric role (`mapType`), and ordering; Aeolus may re-infer the output data type from the new expression.
- Only editable computed fields are accepted. Source columns and partition/auto-added fields are rejected.
- Updates are atomic: all target fields are validated and prechecked together, then a single `dataSetV2` save is issued with `--yes`.
- The command resets backend-derived expression caches for each target and every direct/transitive field that references it via `[field name]`; Aeolus rebuilds canonical `fullExpr` and `fieldList` values during save.
- Retry attempts re-read the whole dataset model before rebuilding the update, avoiding overwriting concurrent field edits with a stale `dataSetV2` payload.

### `aeolus dataset-remove-fields`

Remove dimensions/metrics from an existing editable dataset by name.

```bash
bytedcli aeolus dataset-remove-fields -r va --app-id 1000252 --dataset-id 3436909 --field old_metric

# Force-remove a referenced or partition field
bytedcli aeolus dataset-remove-fields -r va --app-id 1000252 --dataset-id 3436909 --field p_date --force
```

Agent Guidance:

- `--field` is repeatable. By default the command blocks removing a field that another field's expression references via `[name]`, or a partition/auto-added field; pass `--force` to override.
- Refuses to remove every field (a dataset must keep at least one).
- Use `--dry-run` to preview the before/after field count without saving.

### `aeolus dataset-dim-met-map`

Read the **edit-time** dimMet map of a dataset through the Aeolus Open API v3 gateway. Compared with `dataset-fields` (consumption-side view), each field additionally carries its source-table bindings (`fieldSource`), authoring flags (`editable`, `visible`, `isPrivate`) and upstream inheritance (`upstreamDimMetId`).

```bash
# Authentication differs from every other aeolus command — export the Open API token first
export BYTEDCLI_AEOLUS_OPEN_API_TOKEN=<token>
bytedcli aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>

# JSON output carries the full field payload including fieldSource bindings
bytedcli --json aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>

# Target a self-hosted or dev deployment instead of a built-in region host
export BYTEDCLI_AEOLUS_OPEN_API_BASE_URL=https://demo-dev.example.net/aeolus/openApi/v3
bytedcli aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>
```

Agent Guidance:

- **This command does not use `bytedcli auth login`.** The `/aeolus/openApi/v3` gateway authenticates with an `Open-Api-Token` + `App-Id` header pair. Export `BYTEDCLI_AEOLUS_OPEN_API_TOKEN` first; the token is issued per Aeolus app from the console Open API settings page. Missing it fails fast with `AEOLUS_OPEN_API_TOKEN_MISSING` before any request is sent.
- The token is env-only on purpose (no `--open-api-token` flag), so it never lands in shell history or the process list. Do not echo it back into logs, docs or MR descriptions.
- Fields are split by upstream `mapType`: `0` -> `dimensions`, `1` -> `metrics`. Do not use `dimMetVariety` for this — partition dimensions such as `p_date` come back as `dimMetVariety:1` with `mapType:0`.
- Text mode shows only the first `fieldSource` entry per field; a field joined from several source tables keeps all of them in `--json` output.
- Use `dataset-fields` when you only need names/types for building a query, and this command when you need to know **where a field comes from** or **whether it can be edited**.
- If the deployment host is not one of the built-in regions (self-hosted or per-developer environments), set `BYTEDCLI_AEOLUS_OPEN_API_BASE_URL` rather than expecting a `--region` value to cover it.

### `aeolus report resolve`

Resolve an Aeolus dataQuery URL to report metadata and the full dimMet list (dimensions + metrics). Useful as a first step before `report query` when you have a browser URL but need the underlying dataset structure.

```bash
# Resolve from a dataQuery URL (region auto-detected from URL)
bytedcli aeolus report resolve --url "$AEOLUS_REPORT_URL"

# Resolve without URL (requires --region and --report-id)
bytedcli aeolus report resolve -r va --report-id <REPORT_ID>
```

Agent Guidance:

- `aeolus report resolve` fetches the report detail and enriches it with the dataset's full dimMet list (dimensions + metrics with IDs, names, expressions, and partition flags). Used to discover the saved query config (dimMet IDs, reqJson) for a single dataQuery URL — typically as input to `report query`.
- The flat `aeolus resolve-report` command serves a different intent: it resolves dashboard or dataQuery URLs to dataset IDs, intended for batch dataset discovery and access-request workflows. Prefer `report resolve` when you have a single dataQuery URL and want the saved query config; prefer `resolve-report` when you have a dashboard URL or only need dataset IDs.
- If the report has an associated dataset, the dimMet list is fetched automatically; a dimMet fetch failure is non-fatal and the report metadata is still returned.
- Saved reports store their dimMet selection in two shapes, and `report resolve` exposes it as `dimMetConfig` in the JSON output when the report has one: inline entry objects land in `dimMetConfig.dimMetMap`, ID-only selections land in `dimMetConfig.dimMetIdsByDataset` (e.g. `{"<datasetId>": [1700059025281, ...]}`). When `dimMetConfig` is present, both maps are present (the unused shape is an empty object). For the ID-list shape, resolve each ID against the `dimensions` / `metrics` arrays in the same output (or `dataset-fields`). The API may return `displayType: null` for saved dataQuery reports; the CLI normalizes that to an omitted field (`reportDisplayType` absent from JSON output).

### `aeolus report filters` / `aeolus dashboard filters` / `aeolus filter options`

Use these read-only commands to discover valid filter names, dimMet IDs, default values, and option values before using repeatable `--filter` on `report query`, `report download`, or `dashboard query`.

```bash
# Discover filters from a saved dataQuery/report URL
bytedcli --json aeolus report filters --url "$AEOLUS_REPORT_URL"

# Discover dashboard public filters plus report-level/chart filters
bytedcli --json aeolus dashboard filters --url "$AEOLUS_DASHBOARD_URL"

# List selectable option values for a filter dimMetId
bytedcli --json aeolus filter options -r va --dataset-id <datasetId> --filter-id <dimMetId> --keyword demo
```

Agent Guidance:

- `report filters` groups `report_level`, `chart_schema`, and `dataset_field` filters. `dashboard filters` groups `dashboard_public`, `report_level`, and `chart_schema` filters.
- Each filter item includes `name`, `dimMetId`, `op`, `defaultValue`, `source`, `overridable`, and dataset/report context. Prefer `name` for repeatable `--filter`; use `dimMetId` with `--filter-id` when names are ambiguous.
- Repeatable filter syntax is `--filter "field=value"` or `--filter "field[op]=value1,value2"`. Examples: `--filter "country=SG"` and `--filter "p_date[lastSync]=1"`.
- Date shortcuts (confirmed on VQS): `--filter "stat_date[last]=14"` is the last 14 calendar days excluding today; `--filter "stat_date[thisWeek]"` / `[thisMonth]` / `[thisYear]` / `[lastWeek]` / `[lastMonth]` / `[lastQuarter]`; `--filter "stat_date[last:week]=2"` is the last two completed weeks. `lastSync` is only for partition fields.
- Compare aliases: `not_in`, `contains`, `starts_with`, `ends_with`, `is_null`, `is_empty`, `gt`/`gte`/`lt`/`lte`. Result/HAVING on a metric: `--filter "amount[having:>]=100"` or `--filter "avg(amount)[>]=100"`.
- `filter options` calls the Aeolus option-suggest endpoint for a dataset field. Use `--keyword` to narrow values; optional `--dashboard-id`, `--sheet-id`, and `--report-id` pass UI context when option values depend on dashboard/report state.

### `aeolus report query`

Execute a saved Aeolus report and output rows (`--format data`, default) or the underlying ClickHouse SQL (`--format sql`). When `--url` is provided, the report's saved dimMet and where clauses are auto-resolved; otherwise specify `--dim-met` explicitly.

```bash
# Fetch data from a saved report URL (auto-resolves config)
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL"

# Rebuild a scratch query from a URL using dataset field names
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL" \
  --group-by "country,platform" --metrics "revenue" \
  --filter "p_date[lastSync]=1" --top-n 10 --sort-by "revenue"

# Fetch data with explicit parameters
bytedcli aeolus report query -r va --app-id <APP_ID> --dataset-id <DATASET_ID> \
  --dim-met '{"dimMetId":1590328014122,"name":"app_id","expr":"`app_id`","roleType":0}' \
  --limit 50

# Fetch with a where filter
bytedcli aeolus report query -r va --app-id <APP_ID> --dataset-id <DATASET_ID> \
  --dim-met '{"dimMetId":1590328014122,"name":"app_id","expr":"`app_id`","roleType":0}' \
  --where '{"dimMetId":1590328014119,"name":"partition_date","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'

# Get the underlying SQL (still issues a real query against Aeolus)
bytedcli aeolus report query --format sql --url "$AEOLUS_REPORT_URL"
```

**Options:**

- `--url <aeolusUrl>` — Aeolus dataQuery URL (auto-resolves report config)
- `-r, --region <region>` — Region (required when `--url` is not provided)
- `--app-id <appId>` — Aeolus app ID (required without `--url`)
- `--dataset-id <datasetId>` — Aeolus dataset ID (required without `--url`)
- `--report-id <reportId>` — Aeolus report ID for auto-resolving dimMet config
- `--dim-met <json>` — One dimension/metric entry, repeatable (required without `--url`)
- `--where <json>` — One filter entry, repeatable
- `--group-by <fields>` — Build a scratch DataQuery grouped by dataset field name/id; comma-separated and repeatable
- `--metrics <fields>` — Build scratch query metrics by dataset field name/id; comma-separated. Supports `sum(field)`, `count(field)`, `avg(field)` and bare metric names (bare raw numeric metrics default to `sum(`)
- `--filter <expr>` — Named filter, repeatable. Form: `field=value`, `field[op]=value`, or `stat_date[thisWeek]`. Date: `last` / `last:week` / `lastSync` / `thisWeek`. Compare: `contains` / `not_in` / `is_null`. Result: `field[having:>]=100` or `avg(field)[>]=100`
- `--filter-id <expr>` — Field-id filter, repeatable. Form: `123=value1,value2` or `123[op]=value`
- `--data-source-id <id>` — Override `query.dataSourceId` for report query / scratch VizQuery when the backend requires the browser payload's dataSourceId
- `--top-n <N>` — Apply server-side Top N to the sort field
- `--sort-by <field>` / `--sort-order <asc|desc>` — Sort field name/id and order for scratch query / Top N
- `--drill-down <fields>` — Append extra groupBy fields for a follow-up/drill-down scratch query; comma-separated and repeatable
- `--limit <N>` — Row limit (default 100)
- `--timeout-ms <ms>` — Request timeout in milliseconds
- `--format <fmt>` — `data` (default) returns rows; `sql` returns the generated ClickHouse SQL extracted from the response. **Note:** `--format sql` still issues a real VizQuery request — there is no compile-only endpoint.

Agent Guidance:

- When `--url` or `--report-id` resolves saved configuration (`reqJson`), it is used as the base request body. Explicit `--where` filters replace saved filters for the same `dimMetId`/`id` (falling back to `name`) and append new fields, while unrelated saved filters remain intact.
- `report query` and `viz-query` are bounded preview/query commands. Use `aeolus report download` when the user asks for a CSV/XLSX file export without a large stdout payload.

### `aeolus chart get` / `aeolus chart query`

Use `chart get` for read-only chart metadata/Simple DSL, and `chart query` for bounded preview rows from either an online chart ID or a local temporary chart JSON file.

```bash
# Get chart metadata / Simple DSL without modifying the online chart
bytedcli aeolus chart get -r va --chart-id 123456

# Include generated SQL; this issues one bounded VizQuery and returns SQL best-effort
bytedcli --json aeolus chart get -r sg --chart-id 123456 --include-sql

# Preview rows from an online chart
bytedcli aeolus chart query -r va --chart-id 123456 --limit 20

# Query with dashboard/sheet context and runtime filters
bytedcli aeolus chart query -r va --chart-id 123456 --dashboard-id 789012 --sheet-id 345678 --filter "country=SG"

# Query a temporary local chart JSON inline; no online asset is saved or updated
bytedcli aeolus chart query -r va --chart-json-file ./chart.json

# Explain chart/sheet/runtime filter merge only; no chart query request is sent
bytedcli aeolus chart query -r va --chart-id 123456 --dashboard-id 789012 --sheet-id 345678 --filter "country=SG" --explain-filters
```

Agent Guidance:

- `chart query --chart-json-file` sends the JSON object inline to the read-only chart query API. It never calls report save/update APIs and must not be used to mutate an online asset.
- `--explain-filters` is a no-query mode. It reads chart/report metadata and optional dashboard context, then explains runtime overrides, sheet/dashboard filters, and chart filters in merge order.
- Preview rows are capped at 100 even if `--limit` is larger. When output has `truncated:true`, use `aeolus report download` or `aeolus dashboard download` for CSV/XLSX file export.
- `--include-sql` on `chart get` is not metadata-only: it executes a bounded VizQuery, uses `sqlList` when returned, and falls back to query-history SQL. SQL extraction is best-effort; inspect `sql` and `sqlWarning`.

### `aeolus report download`

Download a saved report or query-history result to `--output` using the Aeolus VizQuery download flow. The command accepts a dataQuery URL (`rid` and/or `id` are auto-parsed), `--report-id` / `--chart-id`, or `--history-id`.

```bash
bytedcli aeolus report download --url "$AEOLUS_REPORT_URL" --output ./report-export
bytedcli aeolus report download -r va --history-id 789012 --limit 1000000 --output ./history-export
bytedcli aeolus report download --url "$AEOLUS_REPORT_URL" --filter "country=SG,US" --output ./filtered-export
```

Agent Guidance:

- This is the file-export path. It writes through a sibling temporary file and atomically replaces `--output` after the file response is fully received.
- Do not use this command to preview rows. It intentionally emits only metadata (`output`, `sizeBytes`, `queryHistoryId`, format, `rowLimit`, `rowCount`, `limitReached`, `completeness`) and never prints the downloaded report payload to stdout.
- `--report-id` and `--chart-id` are the same Aeolus `rid` selector; prefer `--report-id` in examples.
- `--limit` defaults to `1000000`; pivot/trend table XLSX downloads are capped at an effective `rowLimit` of `50000`.
- `--filter` / `--filter-id` can be used with saved configuration; they are resolved through the dataset field list and merged into the saved where list.
- CSV `rowCount` excludes the header row. XLSX `rowCount` is `null`; `limitReached` is `"unknown"` and `completeness` is `"unknown"` because the CLI does not parse workbook contents.
- Uses the same VizQuery API as `aeolus viz-query`, so Titan Passport cookie auth applies.

### `hrbi_mycis` 使用提示

- 如果 `dataset-fields` 在 `hrbi_mycis` 返回 `aeolus/clickhouse/invalidRequest`，优先改查同名的迁移数据集。
- 很多 ClickHouse 数据集会强制要求命中日期分区；直接执行 `viz-query` 时，优先补 `partition_date` 过滤，否则容易报 `force_index_by_date`。
- 若需要对 `hrbi_mycis` 等 region 增加仓库内本地策略限制，统一走 `src/services/aeolus/policy.ts` + `config/aeolus/aeolus_policy.json`，并在 handler 调用真实 API 前集中校验；不要把用户名、dataset allowlist 或 region 特判硬编码到 `src/api/*`、command 层或多个 handler 分支里。用户身份优先复用 `~/.local/share/bytedcli/data/userinfo.json`，缺失时再提示执行 `bytedcli auth userinfo`。
- Aeolus 这类随仓库固定交付的策略文件，默认放在 `config/aeolus/` 下，并通过 `src/utils/package_root.ts#getPackageRoot()` 从项目根目录读取；环境变量 override 只作为测试或临时调试兜底，不要再把项目级策略默认放到 `~/.local/share/bytedcli/data/`。
- 例如查询 `用户权限删除记录数据集（MY 迁移）` 的 `new_emp_id` 时，可以这样写：

```bash
bytedcli --site i18n-bd aeolus viz-query \
  -r hrbi_mycis --app-id 667 --dataset-id 2892 \
  --dim-met '{"dimMetId":1590328014236,"name":"new_emp_id","expr":"`new_emp_id`","roleType":0,"dataType":"string"}' \
  --where '{"dimMetId":1590328014230,"name":"partition_date","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'
```

### 复用浏览器 payload

如果直接抓到浏览器的完整 payload，可以整段丢给 `--body` 或 `--body-file`：

```bash
bytedcli --site i18n-bd aeolus viz-query \
  -r hrbi_mycis --app-id 667 --dataset-id 2889 \
  --timeout-ms 90000 \
  --body-file ./payload.json
```

`requestId` 会自动替换为 CLI 生成的新值；旧的 `encryptedReqJson` 会被移除，`schema` 中缺失或不兼容的 web pill 元数据会被归一化，避免生成的 dataQuery history 在 web 端丢失维度、指标或筛选。归一化可能纠正 `isMetric` / `type`，并补齐指标 `format.dataTypeName` / `numFormat`；其余有效字段保持不变。

## SQL Syntax Notes

- Do **not** assume ``FROM `[DatasetName]` `` or `FROM "<datasetId>"` will work. For many datasets this returns `unknownTable`.
- `dataset-fields` lists semantic fields, but not every field name can be queried directly without first locating the physical Aeolus table.
- If `SELECT * LIMIT 1` returns only `dummy`, that does **not** prove the dataset is unusable; it usually means you are not yet querying the backing table.
- Prefer physical-table SQL once you have identified the actual table name from `system.query_log` or dataset model info.
- Partition fields must still be included in `WHERE` clauses where applicable.

## Authentication

By default, Aeolus commands reuse the token obtained from `bytedcli auth login`, just like most other bytedcli domains.

For most Dataset API commands, you can optionally configure region-specific `ClientID/ClientSecret` in `.aeolus.env` or environment variables. When present, CLI will prefer those credentials, which is useful for automation:

1. Visit the Aeolus Developer Console to get your ClientID and ClientSecret（域名以租户为准，常见如下）:
   - **CN region**: [data.bytedance.net](https://data.bytedance.net/aeolus/pages/developer/console/certification)
   - **SG region**: [aeolus-sg.tiktok-row.net](https://aeolus-sg.tiktok-row.net/pages/developer/console/certification)
   - **VA region**: [aeolus-va.tiktok-row.net](https://aeolus-va.tiktok-row.net/pages/developer/console/certification)
   - **EU-TTP region (`euttp`)**: [aeolus-eu-ttp.tiktok-eu.net](https://aeolus-eu-ttp.tiktok-eu.net/pages/developer/console/certification)
   - **EU PIPO region (`eupipo`)**: [aeolus-clover-pipo.tiktok-eu.net](https://aeolus-clover-pipo.tiktok-eu.net/pages/developer/console/certification)
2. Create `.aeolus.env` file (choose one location):
   - **Global**: `~/.bytedcli/.aeolus.env` (recommended for npm global install)
   - **Local**: `./.aeolus.env` in current working directory (overrides global)

```bash
# Region-specific credentials
BYTEDCLI_AEOLUS_CN_CLIENT_ID=your_cn_client_id
BYTEDCLI_AEOLUS_CN_CLIENT_SECRET=your_cn_client_secret
BYTEDCLI_AEOLUS_SG_CLIENT_ID=your_sg_client_id
BYTEDCLI_AEOLUS_SG_CLIENT_SECRET=your_sg_client_secret
BYTEDCLI_AEOLUS_VA_CLIENT_ID=your_va_client_id
BYTEDCLI_AEOLUS_VA_CLIENT_SECRET=your_va_client_secret
BYTEDCLI_AEOLUS_EUTTP_CLIENT_ID=your_euttp_client_id
BYTEDCLI_AEOLUS_EUTTP_CLIENT_SECRET=your_euttp_client_secret
BYTEDCLI_AEOLUS_EUPIPO_CLIENT_ID=your_eupipo_client_id
BYTEDCLI_AEOLUS_EUPIPO_CLIENT_SECRET=your_eupipo_client_secret
```

### Open API v3 token (`dataset-dim-met-map`)

`aeolus dataset-dim-met-map` targets the `/aeolus/openApi/v3` gateway, which authenticates with a standalone token instead of the `bytedcli auth login` session or the `ClientID/ClientSecret` pair above. It is the only Aeolus command with this auth model today.

```bash
# Issued per Aeolus app from the console Open API settings page
export BYTEDCLI_AEOLUS_OPEN_API_TOKEN=<token>

# Optional: point at a self-hosted or dev deployment instead of a built-in region host
export BYTEDCLI_AEOLUS_OPEN_API_BASE_URL=https://demo-dev.example.net/aeolus/openApi/v3
```

- `--app-id` is required and travels in the `App-Id` header; the gateway rejects the call without it.
- The token has no CLI flag by design — keeping it in the environment avoids leaking it into shell history and the process list.
- Missing token fails fast with `AEOLUS_OPEN_API_TOKEN_MISSING` and a hint, before any HTTP request is sent.

## Query Editor (ad-hoc SQL)

Query Editor defaults to the authentication result obtained from `bytedcli auth login`, but it does not support region-specific `ClientID/ClientSecret` overrides. It defaults to `cn`, and also supports `-r/--region` to switch between `cn`, `sg`, `va`, `euttp`, `euttp2`, `eupipo`, `mycis`, `hrbimycis`, `mybd`, `sglark`, `usttpusts`, and `usbd`. For `euttp`, Query Editor exchanges the `eu-ttp` ByteCloud JWT through the EU issuer and uses the resulting host-scoped Titan Passport; if that passport cannot establish a valid QE session, it falls back to an existing compliance product session. For `euttp2`, Query Editor uses the same `eu-ttp` ByteCloud JWT but exchanges it through the host-specific `do-no.tiktok-eu.net` issuer; the NO1A gateway only accepts a `no/`-prefixed `titan_passport_id`, so the `euttp` issuer's `clover/` passport is rejected there. For `mycis`, `mybd`, and `usbd`, Query Editor reuses the local browser session for `i18n-bd`. `eupipo` also uses the `eu-ttp` site, but exchanges Titan credentials through the host-specific `do-pipo.tiktok-eu.net` issuer and targets the Clover/PIPO host. For `usttpusts`, it reuses the local browser session for `us-ttp-usts`. For `hrbimycis`, bytedcli only supports dataset visual queries through `aeolus viz-query`.

### EU-TTP (`euttp`) and US-TTP (`usttpusts`)

|                    | US-TTP (`usttpusts`)        | EU-TTP (`euttp`)                                      |
| ------------------ | --------------------------- | ----------------------------------------------------- |
| Cloud site         | `--site us-ttp-usts`        | `--site eu-ttp`                                       |
| Office Aeolus host | `aeolus-tx.tiktok-usts.net` | `aeolus-eu-ttp.tiktok-eu.net`                         |
| Query Editor `-r`  | `usttpusts`                 | `euttp`                                               |
| Primary auth       | Compliance product session  | EU-scoped Titan Passport from `do.tiktok-eu.net`      |
| Login prerequisite | `aeolus query-editor login` | `bytedcli --site eu-ttp auth login`                   |
| Product fallback   | Required session path       | `aeolus query-editor login` only if Titan is rejected |

Do not reuse a ROW `i18n-tt` Titan Passport for EU-TTP. `euttp` exchanges against the EU issuer and scopes the cookie to the EU Aeolus host.

### EU-TTP2 / NO1A (`euttp2`)

`euttp2` is a separate EU deployment behind the NO1A gateway `aeolus-no.tiktok-eu.net`. It shares the `eu-ttp` cloud site with `euttp` but is **not** interchangeable with it: the two resolve to different clusters and different Hive catalogs, so a table that exists in one may not exist in the other.

|                   | EU-TTP (`euttp`)                | EU-TTP2 (`euttp2`)                    |
| ----------------- | ------------------------------- | ------------------------------------- |
| Query Editor `-r` | `euttp`                         | `euttp2` (aliases `eu-ttp2` / `no1a`) |
| Aeolus host       | `aeolus-eu-ttp.tiktok-eu.net`   | `aeolus-no.tiktok-eu.net`             |
| Cloud site        | `--site eu-ttp`                 | `--site eu-ttp` (same)                |
| Titan issuer      | `do.tiktok-eu.net` (`clover/`)  | `do-no.tiktok-eu.net` (`no/`)         |
| Default Hive yarn | `cluster_id` per region default | `cluster_id=wyodel01`, `idc=NO1A`     |
| Typical queue     | `root.bytecloud_trade`          | `root.bytecloud_batch_no1a`           |
| Origin override   | `BYTEDCLI_AEOLUS_EUTTP_ORIGIN`  | `BYTEDCLI_AEOLUS_EUTTP2_ORIGIN`       |

```bash
# euttp2 needs no extra login beyond the eu-ttp ByteCloud JWT
bytedcli --site eu-ttp auth login
bytedcli aeolus query-editor whoami -r euttp2
bytedcli aeolus query-editor queues -r euttp2
bytedcli aeolus query-editor query one -r euttp2 --queue root.bytecloud_batch_no1a --sql "SELECT 1"
```

Agent Guidance:

- **The NO1A gateway only accepts a `no/`-prefixed `titan_passport_id`.** The issuer used by `euttp` (`do.tiktok-eu.net`) mints `clover/...`, which NO1A rejects with HTTP 401 `[Titan] Invalid Params: Invalid titan_passport_id`. A new Aeolus host of this kind therefore needs its **host and Titan issuer added as a pair** — pointing an existing region's origin at the new host is not enough.
- `euttp2` authenticates with the ordinary `--site eu-ttp` ByteCloud JWT. It is **not** a session-auth region: do not run `aeolus query-editor login` for it, and do not expect `BYTEDCLI_AEOLUS_COOKIE` (that variable is bound to `usttpusts` only).
- Hive `run` on `euttp2` derives `yarn.cluster_id=wyodel01` / `idc=NO1A`. A mismatched cluster/idc is accepted with `code:0` but never gets a worker, so the task silently never finishes. `--idc` can override the idc; `cluster_id` is always derived from the region.
- `euttp` and `euttp2` are different data planes. Confirm which one actually holds the table before concluding data is missing: the same query can return `SEMANTIC_ERROR ... not found` on one and succeed on the other (their SQL engines report different catalog prefixes).

### Query Editor authentication

```bash
# One-time login
bytedcli auth login

# EU-TTP: EU-scoped Titan Passport (primary)
bytedcli --site eu-ttp auth login

# Query Editor on mycis / mybd / usbd
bytedcli --site i18n-bd auth login --session

# EU-TTP fallback only when Titan Passport is rejected
bytedcli --site eu-ttp aeolus query-editor login

# US-TTP compliance product session
bytedcli --site us-ttp-usts aeolus query-editor login

# Headless/agent fallback after a trusted runtime injects the Aeolus Cookie secret
bytedcli aeolus query-editor whoami -r usttpusts
```

`query-editor login` defaults to `--mode password`: it prompts your SSO username/password/OTP in the terminal and signs in over HTTP, so it works over SSH / headless hosts with no browser window. If password mode cannot establish a session (for example the compliance gateway requires an interactive sign-in), retry with `--mode browser`, which opens a temporary browser window on the compliance host.

For `usttpusts`, `BYTEDCLI_AEOLUS_COOKIE` has priority over the local session jar. Its value is the complete `Cookie` request-header value from an authenticated Query Editor browser request, without the `Cookie:` prefix. bytedcli binds it to the built-in `usttpusts` HTTPS origin, validates it against `/qe/v2/api/user`, never persists it, and fails closed when it is malformed, expired, or rejected. Other regions ignore this variable.

A human or managed secret store must inject the Cookie outside the Agent conversation. Agents must never request, paste, echo, log, or place the value in argv, scripts, skill files, or repositories. For a local interactive shell, paste it through a hidden `read -rs BYTEDCLI_AEOLUS_COOKIE` prompt, then `export` the variable; unset it after the command. Managed Agent runtimes should use their secret environment injection mechanism.

For `euttp`, the CLI first verifies the EU-scoped Titan Passport against `/qe/v2/api/user`, refreshes it once if needed, then tries an existing compliance product session. For `euttp2`, the CLI verifies the NO1A-scoped Titan Passport (`do-no.tiktok-eu.net`) the same way; there is no product-session fallback to run for it, so a persistent failure there means the `--site eu-ttp` JWT itself is missing or invalid. For `mycis`, `mybd`, and `usbd`, make sure the `i18n-bd` browser session is ready first. For `usttpusts`, use `query-editor login` on `aeolus-tx.tiktok-usts.net`, or use the injected session in headless/agent execution. For `hrbimycis`, use `aeolus viz-query` instead of Query Editor or `aeolus query`.

For `eupipo`, use `bytedcli --site eu-ttp auth login`; if Aeolus still returns a product-login page, run `bytedcli --site eu-ttp auth login --session --auto --yes` once to seed the Clover/PIPO product cookie, then retry with `-r eupipo`.

### Query Editor quick start

```bash
# Check current user
bytedcli aeolus query-editor whoami
bytedcli aeolus query-editor whoami --region sg

# Folder management
bytedcli aeolus query-editor folder list
bytedcli aeolus query-editor folder list --region va
bytedcli aeolus query-editor folder tree
bytedcli aeolus query-editor folder create --name "my-queries"
bytedcli aeolus query-editor folder cleanup-temp --region mycis --dry-run
bytedcli aeolus query-editor folder cleanup-temp --region mycis --keep-id <folderId> --yes

# File management
bytedcli aeolus query-editor file create --name "test" --folder-id 123
bytedcli aeolus query-editor file write-sql --file-id 456 --sql "SELECT 1"
bytedcli aeolus query-editor file search --keyword "test"

# SQL execution
bytedcli aeolus query-editor queues
bytedcli aeolus query-editor query parse --sql "SELECT 1"
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue <your_queue> --sql "SELECT 1"
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue <your_queue> --file ./queries/demo.sql
# Multi-day Hive batch date range: keep the ${date} placeholder in SQL; QE expands one task per date.
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7
# One-shot temp query can run the same multi-day batch without explicit file/folder IDs.
bytedcli aeolus query-editor query one --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7
# Single-day query date: keep ${date}/${DATE} in SQL; QE uses --adhoc-date from the request.
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --adhoc-date 2026-08-12
bytedcli aeolus query-editor query status --task-id 789 --file-id 456 --folder-id 123
bytedcli aeolus query-editor query logs --task-id 789
bytedcli aeolus query-editor query cancel --task-id 789

# Task record management: rename tasks and dry-run/delete noisy records
bytedcli aeolus query-editor task rename --task-id 789 --name "sample-task-name"
bytedcli aeolus query-editor task delete --task-id 789
bytedcli aeolus query-editor task delete --task-id 789 --yes

# One-shot query (auto-creates file, runs SQL, returns results)
bytedcli aeolus query-editor query one --queue <your_queue> --sql "SELECT 1"
bytedcli aeolus query-editor query one --queue <your_queue> --file ./queries/demo.sql
# Submit without polling; JSON includes engine, taskId, fileId, folderId, status, and taskUrl.
bytedcli --json aeolus query-editor query one --queue <your_queue> --sql "SELECT 1" --no-wait

# Custom datasource (user-defined, e.g. DORIS): list sources, then query (no --queue)
export QE_APP_ID=<yourWorkspaceAppId>   # custom datasources are appId-scoped
bytedcli aeolus query-editor datasources
# by name (resolved to id+type via the datasources list):
bytedcli aeolus query-editor query one --engine datasource --datasource-name <datasourceName> --sql "select * from sample_db.sample_tbl limit 10"
# or directly by id+type (works without the workspace appId):
bytedcli aeolus query-editor query one --engine datasource --datasource-id <datasourceId> --datasource-type DORIS --sql "select * from sample_db.sample_tbl limit 10"
```

### Query Editor: Hive 日期占位符与多日 batch 查询

Hive `query run` 和 `query one` 都支持 `--sql` 内联 SQL 或 `--file` 读取本地 SQL 文件；两者同时提供时 `--file` 优先。SQL 中可保留 `${date}` 或 `${DATE}` 占位符：`--adhoc-date` 是单日日期便捷参数，CLI 会把日期放进 QE run 请求体，SQL 文本保持原样；QE 后端会按同日 `range` 执行占位符替换。`--batch-start-date` / `--batch-end-date` 会提交 QE 多日 `query_type=BATCH`，由 QE 按日期展开子任务。`--batch-concurrency <N>` 只适用于多日 BATCH，会写入 QE `max_tasks`，取值 `1-120`；省略时默认使用 `min(日期天数, 120)`。`query one` 会自动复用/创建 `_bytedcli_temp` 目录和临时文件，因此不需要显式传 `--file-id` / `--folder-id`。两个命令默认等待执行结束；传 `--no-wait` 时会在提交后立即返回，JSON 输出包含后续查询状态所需的 `engine`、`taskId`、`fileId`、`folderId` 和 `taskUrl`。不传任何日期参数时保持普通 `ADHOC` 查询体验；如果 SQL 写死了日期而没有 `${date}` / `${DATE}`，日期参数不会报错，但基本不会改变查询结果。

```bash
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue root.demo_queue \
  --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\''' \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7

bytedcli aeolus query-editor query one --queue root.demo_queue \
  --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\''' \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7

bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue root.demo_queue \
  --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\''' \
  --adhoc-date 2026-08-12
```

日期占位符参数仅支持默认 Hive runner；`--engine ch` 或 `--engine datasource` 请移除这些参数。`--batch-start-date` 与 `--batch-end-date` 必须至少跨 2 天；同一天请改用 `--adhoc-date`。多日批量提交会生成父任务和按日期展开的子任务，后续仍使用父 `taskId` 查询状态和预览合并结果。预览结果可能被 `--rows` 截断，JSON 输出里的 `rowCount`、`returnedRows`、`truncated` 用来判断是否需要改用下载或调大预览上限。

### Query Editor: ClickHouse (`--engine ch`)

默认走 Hive `/hive/task/run`；与浏览器 Query Editor 一致的 ClickHouse 任务请用 **`--engine ch`**（`/ch/task/*`）、并保证 **`status` / `logs` / `cancel` 与 `run` 使用相同 `--engine`**。参数表、`QE_APP_ID`、`BYTEDCLI_CLOUD_SITE`（VA/SG 常为 `i18n-tt`）等完整说明见 **`references/aeolus.md` 的「Query Editor」章节**。

### Query Editor: parse/check SQL

`query parse` mirrors the browser Query Editor Parse button. It calls `/hive/task/explain` by default, `/ch/task/explain` with `--engine ch`, or `/datasource/task/explain` with `--engine datasource` (user-defined sources such as DORIS), and does not submit a task:

```bash
bytedcli aeolus query-editor query parse --sql "SELECT 1"
bytedcli aeolus query-editor query parse --file ./queries/demo.sql
bytedcli aeolus query-editor query parse --engine ch --cluster-name <cluster_name> --ch-region VA --sql "SELECT 1"
# Custom datasource (DORIS etc.): checks against the real datasource, not the Hive parser.
# Needs a datasource identity (--datasource-name needs QE_APP_ID; or pass --datasource-id/-type).
bytedcli aeolus query-editor query parse --engine datasource --datasource-name <datasourceName> --sql "select * from sample_db.sample_tbl limit 1"
bytedcli aeolus query-editor query parse --engine datasource --datasource-id <datasourceId> --datasource-type DORIS --sql "select 1"
```

⚠️ Parsing a DORIS/custom-datasource table with the **default (hive)** parser misreports real tables as "not found" — you must pass `--engine datasource` (with a datasource identity) so the check routes to the actual datasource backend. On success, datasource parse returns the resolved output columns as `fields`; a missing table / syntax error comes back as a successful CLI response with `ok:false` and the backend message.

### Query Editor: 自定义数据源（`--engine datasource`）

针对用户在风神里自建的数据源（如 DORIS）提交查询。两种指定方式：**`--datasource-name <name>`**（自动从 `aeolus query-editor datasources` 解析出 id+type）或 **`--datasource-id <id> --datasource-type <type>`**（直接指定，`--datasource-id` 优先）。走 `/datasource/task/*`，不需要 `--queue`/`--idc`；`status` / `logs` / `cancel` 必须复用同一个 `--engine datasource`。⚠️ 自定义源是 **appId 作用域**的：`datasources` 列表能列出该源、`--datasource-name` 能解析，都要求 `QE_APP_ID` 等于拥有该源的 Query Editor 工作区 appId（即页面 URL 里的 `appId=`）；用显式 `--datasource-id` 提交则不依赖 appId。完整参数与示例见 **`references/aeolus.md` 的「Query Editor」与「Custom datasource example」章节**。

### Query Editor: CSV 临时表

`query-editor tmp-table create` 复刻浏览器上传 CSV 创建临时表的三步流程：`tmp_table/upload` 上传文件，`tmp_table/preview` 推断 schema，`tmp_table/create` 创建表。默认是 dry-run，只预览 upload / preview / create 计划；确认后加 `--yes` 才会真正发起上传并创建表。它复用 Query Editor 鉴权与 `x-qe-appid`；如果页面工作区不是默认 appId，先设置 `QE_APP_ID` 或 `BYTEDCLI_AEOLUS_QE_APP_ID` 为 Query Editor 页面 URL 的 `appId=`。

```bash
bytedcli aeolus query-editor tmp-table create \
  --file ./sample.csv \
  --table-name demo_tmp \
  --db-name facade_qe_tmp_table \
  --ttl 30 \
  --delimiter ','

bytedcli aeolus query-editor tmp-table create \
  --file ./sample.tsv \
  --table-name demo_tmp_tsv \
  --delimiter $'\t' \
  --ttl 7 \
  --yes
```

### Query Editor: `HTTP 406` 解码

`query run` / `query one` 报 **`HTTP 406`** 不是协议问题，而是后端拒绝执行，两个常见原因：

1. 当前账号缺少所查表的权限 —— 走 `bytedcli coral permission apply` 申请表权限。
2. 该表/集群要求显式指定队列与机房 —— 重跑时带上 `--queue <queue> --idc <idc>`。

带了 queue/idc 仍 406 时，用 `bytedcli --http-debug ... query-editor query run ...` 看原始响应定位。

### Recommended usage: `query one` vs full Query Editor workflow

- Use `aeolus query-editor query one` for one-off or exploratory SQL where you only need to run a small number of temporary queries quickly.
- If historical one-shot runs created many `_bytedcli_temp` folders, use `aeolus query-editor folder cleanup-temp` first with `--dry-run`, then rerun with `--yes` after confirming the retained folder ID.
- Use the full Query Editor workflow when you are analyzing one system or topic and expect multiple related SQL queries over time.
- The full workflow avoids creating a new temporary folder on every query, lets you reuse the same folder/file IDs, and keeps related SQL under one theme directory so you can search and review query history later.
- In the full workflow, prefer passing SQL directly to `query run --sql ...` or `query run --file ...`. Writing SQL into the file first is optional, not required for execution.
- Under the hood, both `query run --sql ...` and `query run --file ...` call the same Query Editor `run` API with the same `page_id` / `block_id`; **Hive** (default) sends `yarn` queue fields, while **`--engine ch`** sends `cluster_name` / `region` instead. The only difference between `--sql` and `--file` is where `query` / `query_template` text comes from.
- A practical organization pattern is: create one folder for the overall analysis theme, create multiple files for different sub-scenarios under that theme, and then reuse the same `file-id` for multiple `query run` executions when one sub-scenario needs several SQL variants.
- Rename submitted tasks with `aeolus query-editor task rename` so task history makes the SQL purpose clear when several runs live in the same file.
- When the user explicitly wants to cancel or remove noisy Query Editor tasks, first capture the task status fields that preserve lower-level history (`runtime_info.application_id`, `runtime_info.execute_id`, `runtime_info.tracking_url_list`, `query_id`, and the SQL), then run `aeolus query-editor task delete --task-id <taskId> --yes` to keep the Query Editor folder clean.
- Deleting a Query Editor task removes the QE task record/status entry; lower-level Presto/TQS/Spark history may still be reachable only through identifiers captured before deletion.
- In that model, `folder-id` is the theme container, and `file-id` is closer to a reusable query context for one sub-scenario than a hard binding to exactly one SQL statement.

Recommended persistent workflow:

```bash
# 1) Create or reuse a theme folder once
bytedcli aeolus query-editor folder create --name "svc-frk-analysis"

# 2) Create one or more query files inside that folder
bytedcli aeolus query-editor file create --name "partitions" --folder-id 123
bytedcli aeolus query-editor file create --name "daily-sample" --folder-id 123
bytedcli aeolus query-editor file create --name "rootcause-drilldown" --folder-id 123

# 3) Run queries against the same reusable file/folder IDs
bytedcli aeolus query-editor query run --file-id 456 --folder-id 123 --queue <your_queue> --sql "SHOW PARTITIONS svc_frk.ods_cp_cds_keys_df"
bytedcli aeolus query-editor query run --file-id 457 --folder-id 123 --queue <your_queue> --sql "SELECT * FROM svc_frk.ods_cp_cds_keys_df WHERE date = '20260412' LIMIT 100"
bytedcli aeolus query-editor query run --file-id 457 --folder-id 123 --queue <your_queue> --file ./queries/daily-sample.sql
bytedcli aeolus query-editor query run --file-id 458 --folder-id 123 --queue <your_queue> --sql "SELECT protocol, date FROM svc_frk.ods_cp_cds_keys_usttp_df WHERE date = '20260412' LIMIT 10"
bytedcli aeolus query-editor query run --file-id 458 --folder-id 123 --queue <your_queue> --sql "SELECT to_service, count(*) FROM svc_frk.ods_cp_cds_keys_usttp_df WHERE date = '20260412' GROUP BY to_service LIMIT 20"

# 4) Optionally persist SQL into the file body for later viewing/editing in Query Editor UI
bytedcli aeolus query-editor file write-sql --file-id 456 --sql "SHOW PARTITIONS svc_frk.ods_cp_cds_keys_df"
bytedcli aeolus query-editor file write-sql --file-id 457 --sql "SELECT * FROM svc_frk.ods_cp_cds_keys_df WHERE date = '20260412' LIMIT 100"

# 5) Inspect task status / logs, rename meaningful task records, and search historical SQL files later
bytedcli aeolus query-editor query status --task-id 789 --file-id 456 --folder-id 123
bytedcli aeolus query-editor query logs --task-id 789
bytedcli aeolus query-editor task rename --task-id 789 --name "partition-check-sample"
bytedcli aeolus query-editor query cancel --task-id 789
# Before deleting a noisy task, record runtime_info.application_id / execute_id / tracking_url_list from status.
bytedcli aeolus query-editor task delete --task-id 789 --yes
bytedcli aeolus query-editor file search --keyword "svc_frk"
```

Notes:

- `query one` is optimized for convenience, not long-term organization.
- `query run` should include `--sql` or `--file` when you want to execute against an existing `file-id` / `folder-id`.
- For repeated analysis, prefer naming folders by topic/system (for example `svc-frk-analysis`, `creator-growth-debug`, `dashboard-245033-rootcause`).
- Query Editor commands default to `cn`, and support `-r/--region` to switch host/domain consistently with Aeolus dataset/report APIs.

### Query Editor command structure

```
aeolus query-editor
  ├── whoami / queues / datasources
  ├── folder   list|tree|create|rename|move|delete|cleanup-temp
  ├── file     get|create|write-sql|rename|move|delete|search
  ├── tmp-table create
  ├── template list|get
  ├── task     rename|delete
  └── query    parse|run|status|logs|cancel|one
```

### Query Editor templates

`template list/get` 浏览 Query Editor 自己的已保存模板；它与 Shuttle project/template/DECC 工作流是不同能力：

```bash
# 列模板（默认 parent-id=0 根目录、department=public）
bytedcli aeolus query-editor template list -r cn
bytedcli aeolus query-editor template list -r cn --parent-id 123 --department public
# 分页（默认 --page 1、--page-size 20）
bytedcli aeolus query-editor template list -r cn --page 2 --page-size 50
# 取某模板的 SQL（--template-id 用 list 返回的 template_id）
bytedcli aeolus query-editor template get -r cn --template-id 17
```

## Shuttle (Data Query Projects)

Shuttle 是 Aeolus 平台上的数据查询项目管理工具。其 `/shuttle/web/api/v1/` 控制面只部署在 VA；`-r va` 只选择控制面，不代表任务查询 VA/US/EU-TTP 数据。任务数据区域来自模板 `infos` 的 key（例如 `US`、`EU`、`EU-TTP`、`EU-TTP2`），YARN cluster/queue 必须从 `queue get` 返回的同名区域下选择。

使用 Shuttle、TTP 取数、DECC、`detection_uv` 或跨区域合规数据时，**必须先读 `references/shuttle.md`**。该 reference 基于官方 [Shuttle 合规取数 One Pager](https://bytedance.sg.larkoffice.com/docx/BIWnd0wW7o4BjQxUQ4YlUfJfgmb)，说明 Shuttle 的合规平台定位、数据通道、SQL 边界、US/EU 差异与 Agent 决策规则。

| 概念             | CLI/响应位置                              | 示例                              |
| ---------------- | ----------------------------------------- | --------------------------------- |
| 身份与站点上下文 | 全局 `--site`                             | `--site us-ttp-bdee`              |
| Shuttle 控制面   | `-r/--region`，固定 `va`                  | `aeolus-va.../shuttle/web/api/v1` |
| 任务数据区域     | `--shuttle-region` / `template.infos` key | `US`                              |
| 执行队列区域     | `queue get` 的 `queues` key               | `queues.US`                       |

默认使用 office 网络的 `aeolus-va.tiktok-row.net`。只有 office host 明确不可达时才设置 `BYTEDCLI_NETWORK_PROFILE=prod`，切换到生产网 host；不要因为目标数据在 US-TTP 就直接切 prod。

需要 Shuttle project/template/DECC、多日 BATCH fan-out、区域队列执行或完整任务下载时使用 Shuttle。只需执行不依赖 Shuttle project/template/DECC 的临时 SQL 时使用 Query Editor。

最短发现流程只需要先读取有权限的 project、模板详情和区域队列：

```bash
bytedcli aeolus shuttle project list -r va
bytedcli aeolus shuttle template search -r va --project-id <project-id>
bytedcli aeolus shuttle template get -r va --template-id <template-id>
bytedcli aeolus shuttle queue get -r va --project-id <project-id>
```

发现结果后，按 `references/shuttle.md` 判断合规通道、数据区域、DECC schema 与写操作边界；需要提交、下载、模板或文件夹操作的参数时，再读 `references/aeolus.md` 的 Shuttle 章节。不要在未读取这两个 reference 时猜测业务 ID、YARN queue、DECC schema 或 SQL 输出字段。

## Notes

- Use `--json` for structured JSON output (global option before subcommand)
- **Region (`-r`) is required** for all Dataset API commands
- Dataset ID can be found in `list-authorized` output
- App ID can be found in `list-authorized` JSON output (`app.id` field)
- Partition fields are marked in `dataset-fields` output
- `dataset-fields`, `dataset-model-info` and `query` only work with `data_set` type, not `dashboard`
- Query Editor commands default to `cn`; pass `-r/--region <region>` to target `sg`, `va`, `euttp`, `euttp2`, `eupipo`, `mycis`, `hrbimycis`, `mybd`, `sglark`, `usttpusts`, or `usbd`

## References

- `references/aeolus.md`（命令级参考；含 **Query Editor**、`--engine ch`、Regions 与鉴权）
- `references/shuttle.md`（Shuttle 合规平台定位、DECC 数据通道、SQL 合规边界、US/EU 规则；涉及 Shuttle 时必须读取）
- `references/invocation.md`
- `references/troubleshooting.md`（工具版本过期与常见错误自查，排错前先看）
