# Aeolus CLI Reference

The Aeolus CLI provides commands to interact with the Aeolus BI/data analytics platform, including listing datasets, viewing field details, and executing SQL queries.

Examples using `AEOLUS_REPORT_URL` or `AEOLUS_DASHBOARD_URL` expect the caller to export the actual user-provided URL. Fabricated hosts are intentionally not used because URL parsing rejects unknown Aeolus hosts.

## Table of Contents

- Commands (list-authorized / resource recent / resource search / resolve-report / report resolve / report filters / report query / report download / report style / chart get / chart query / dashboard filters / dashboard query / filter options / dataset-fields / dataset-dim-met-map / dataset-fields-download / dataset-fields-upload / dataset-model-info / dataset-create / dataset-add-source-table / dataset-add-fields / dataset-update-fields / dataset-remove-fields / dataset-sync / query / viz-query / save-viz-query)
- SQL Syntax
- Query Editor (folders, files, templates, query run / status / logs / cancel, single-day date replacement, multi-day Hive batch ranges and `max_tasks`, task rename / delete, `--engine ch`, HTTP 406)
- Resource Types
- Regions
- Authentication
- Shuttle (task submit) — VA control plane, task data region, YARN, and BATCH semantics
- Shuttle (task download) — full Excel/CSV result download
- Shuttle (template + folder organisation) — project template tree management
- JSON Output

## Commands

### list-authorized

List dashboards and datasets you have access to.

```bash
bytedcli aeolus list-authorized [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, hrbimycis, mybd, sglark, uspipo, usttpusts, usbd (required)
- `-t, --type <type>` - Filter by type: dashboard, data_set
- `--limit <limit>` - Number of results (default: 20)
- `--offset <offset>` - Pagination offset (default: 0)
- `--creator <creator>` - Filter by creator (owner username)
- `--keyword <keyword>` - Filter by keyword (matches resource name)

**Examples:**

```bash
# List all authorized resources (VA region)
bytedcli aeolus list-authorized -r va

# List only datasets (CN region)
bytedcli aeolus list-authorized -r cn --type data_set --limit 50

# Pagination (SG region)
bytedcli aeolus list-authorized -r sg --offset 20 --limit 20

# Filter by keyword (matches resource name)
bytedcli aeolus list-authorized -r cn --keyword demo
```

**Output:**

- ID, Type, Name, Owner, App, Last Visit Time

---

### resource recent

List recently visited Aeolus resources.

```bash
bytedcli aeolus resource recent [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, hrbimycis, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--limit <limit>` - Number of results to return (default: 20)

**Examples:**

```bash
# List recently visited resources
bytedcli aeolus resource recent -r va --limit 20
```

**Output:**

- ID, Type, Name, Owner, App, URL
- JSON output includes `limit` and `truncated`.

---

### resource search

Search Aeolus resources by keyword.

```bash
bytedcli aeolus resource search [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, hrbimycis, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--keyword <keyword>` - Search keyword (required)
- `-t, --type <type>` - Comma-separated resource types: dashboard, data_set, report, screen, prep_task, scene
- `--page <n>` - Page number, 1-based (default: 1)
- `--page-size <n>` - Items per page (default: 20)

**Examples:**

```bash
# Search dashboards and reports
bytedcli aeolus resource search -r va --keyword sample --type dashboard,report --page 1 --page-size 20

# Continue from the next page
bytedcli aeolus resource search -r va --keyword sample --page 2 --page-size 20
```

**Output:**

- ID, Type, Name, Owner, App, URL
- JSON output includes `total`, `page`, `page_size`, `types`, and `truncated`.

---

### resolve-report

Resolve report and dataset references from Aeolus URLs.

```bash
bytedcli aeolus resolve-report [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, mybd, sglark, uspipo, usttpusts, usbd (required when URL cannot infer region)
- `--url <aeolusUrl>` - Aeolus URL (`dataQuery` or `dashboard`)
- `--app-id <appId>` - App ID (when not using URL)
- `--report-id <reportId>` - Report ID (when not using URL)
- `--json` is a global option and must appear before `aeolus`

**Examples:**

```bash
# Resolve from dataQuery URL
bytedcli aeolus resolve-report --url "$AEOLUS_REPORT_URL"

# Resolve from dashboard URL
bytedcli aeolus resolve-report --url "$AEOLUS_DASHBOARD_URL"

# Resolve from dashboard URL without sheetId (falls back to current/default sheet)
bytedcli aeolus resolve-report --url "$AEOLUS_DASHBOARD_URL"
```

**Output:**

- `dataQuery` URL: report IDs and resolved dataset IDs
- `dashboard` URL: report IDs, resolved dataset IDs, plus
  - `dashboardName`, `dashboardOwnerEmailPrefix`, `dashboardRoleList[]`
  - `sheets[]`: `sheetId`, `name`, `sheetOrder`, `visible`, `reportIds`
  - `reports[]`: `reportId`, `name`, `displayType`, `ownerEmailPrefix`, `statusCode`, `updatedAt`, `datasetIds`

---

### dataset-fields

Get dataset dimensions and metrics (field details).

```bash
bytedcli aeolus dataset-fields <datasetId> [options]
```

**Arguments:**

- `datasetId` - Dataset ID (from list-authorized output)

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--json` is a global option and must appear before `aeolus`

**Examples:**

```bash
# Get dataset fields (VA region)
bytedcli aeolus dataset-fields -r va 1576311

# Get dataset fields (CN region, JSON output)
bytedcli --json aeolus dataset-fields -r cn 185503
```

**Output:**

- Dataset name
- **Dimensions**: ID, Name, Type, Partition flag, Description
- **Metrics**: ID, Name, Type, Expression, Description
- Text mode also prints the resolved region as `input -> normalized`; JSON mode returns both `inputRegion` and `normalizedRegion`

---

### dataset-dim-met-map

Get the **edit-time** dimMet map of a dataset through the Aeolus Open API v3 gateway (`GET /aeolus/openApi/v3/dataFactory/getDimMetMap`).

Compared with `dataset-fields` (consumption-side view), every field additionally carries its source-table bindings, authoring flags and upstream inheritance. Use `dataset-fields` when you only need names and types to build a query; use this command when you need to know where a field comes from or whether it can be edited.

```bash
bytedcli aeolus dataset-dim-met-map [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, hrbimycis, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--app-id <appId>` - Aeolus app ID (required; sent as the `App-Id` header)
- `--dataset-id <dataSetId>` - Aeolus dataset ID (required)
- `--need-tags <needTags>` - Pass through the upstream `needTags` filter (optional; default empty)
- `--json` is a global option and must appear before `aeolus`

**Authentication (different from every other aeolus command):**

This gateway does not use the `bytedcli auth login` session or region-scoped `ClientID/ClientSecret`. It requires a standalone Open API token, exported as an environment variable:

- `BYTEDCLI_AEOLUS_OPEN_API_TOKEN` - Open API token, issued per Aeolus app from the console Open API settings page (required)
- `BYTEDCLI_AEOLUS_OPEN_API_BASE_URL` - Override the whole base URL to reach a self-hosted or dev deployment (optional)

There is no `--open-api-token` flag on purpose: keeping the credential in the environment avoids leaking it into shell history and the process list. A missing token fails fast with `AEOLUS_OPEN_API_TOKEN_MISSING` and a hint, before any HTTP request is sent.

**Examples:**

```bash
# Export the token once per shell, then query the dimMet map
export BYTEDCLI_AEOLUS_OPEN_API_TOKEN=<token>
bytedcli aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>

# JSON output carries the full field payload including fieldSource bindings
bytedcli --json aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>

# Target a self-hosted or dev deployment instead of a built-in region host
export BYTEDCLI_AEOLUS_OPEN_API_BASE_URL=https://demo-dev.example.net/aeolus/openApi/v3
bytedcli aeolus dataset-dim-met-map -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>
```

**Output:**

- `datasetId`, `appId`, `total` field count
- **Dimensions** (`mapType: 0`): ID, Name, Type, Partition flag, Source Table, Description
- **Metrics** (`mapType: 1`): ID, Name, Type, Expression, Source Table, Description
- JSON mode additionally returns per field: `expr`, `fullExpr`, `filterType`, `defaultDataTypeName`, `dimMetVariety`, `dimMetOrder`, `dimMetMixOrder`, `editable`, `visible`, `isPrivate`, `isDeletedField`, `upstreamDimMetId`, `ownerEmailPrefix`, `traits`, `fieldList`, and the full `fieldSource` array
- Text mode shows only the first `fieldSource` entry per field; a field joined from several source tables keeps all of them in JSON output
- Text mode also prints the resolved region as `input -> normalized`; JSON mode returns both `inputRegion` and `normalizedRegion`

**Notes:**

- Dimensions and metrics are split by the upstream `mapType` field: `0` -> dimension, `1` -> metric. Do not use `dimMetVariety` for this — partition dimensions such as `p_date` come back as `dimMetVariety: 1` with `mapType: 0`.
- `fieldList` is JSON-encoded upstream (`"[\"p_date\"]"`); the CLI decodes it into a string array.

---

### dataset-fields-download

Download the native Aeolus dataset-fields XLSX template file for batch editing. This command follows the browser field editor flow (`dimMetDownload` -> `downloadUrl`) and writes the original Aeolus workbook to disk.

```bash
bytedcli aeolus dataset-fields-download [options]
```

**Options:**

- `-r, --region <region>` - Region (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--output <path>` - Output XLSX path (optional; default `./dataset-fields-<datasetId>.xlsx`)

**Example:**

```bash
bytedcli aeolus dataset-fields-download -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --output ./dataset-fields.xlsx
```

---

### dataset-fields-upload

Batch add/update dataset fields from the native Aeolus XLSX template. The CLI now follows the browser flow (`uploadDimMetFile` -> `checkDimMetName` -> `PUT dimMetList`) and no longer uses a private `_meta` sheet.

```bash
bytedcli aeolus dataset-fields-upload [options]
```

**Options:**

- `-r, --region <region>` - Region (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--file <path>` - Input XLSX file path (required)
- `--dry-run` - Preview add/update diff without saving

**Examples:**

```bash
# Recommended: review changes first
bytedcli --json aeolus dataset-fields-upload -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --file ./dataset-fields.xlsx

# Execute after review
bytedcli aeolus dataset-fields-upload -r sg --app-id <APP_ID> --dataset-id <DATASET_ID> --file ./dataset-fields.xlsx --yes
```

**Recommended workflow:**

- Always run `--dry-run` first and review `addedFields` / `updatedFields` before real upload.
- Use the XLSX file downloaded by `dataset-fields-download`; existing rows should keep their native `ID` column so updates are matched by field id.
- The native template edits `field_name`, `dimensions(0)/measures(1)`, `expression`, `display name`, `desc`, and `ID`; if `checkDimMetName` fails, the CLI stops before `PUT dimMetList`.

---

### dataset-model-info

Get dataset model info from data factory, including the raw model info plus a concise read-only inspection summary for sync mode, partitions, hot fields, filter-rule metadata hints, and bounded preview metadata.

```bash
bytedcli aeolus dataset-model-info [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--app-id <appId>` - Aeolus app ID (required, from list-authorized JSON output `app.id`)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--json` is a global option and must appear before `aeolus`

**Examples:**

```bash
# Get dataset model info (VA region)
bytedcli aeolus dataset-model-info -r va --app-id <APP_ID> --dataset-id <DATASET_ID>

# Get dataset model info with JSON output
bytedcli --json aeolus dataset-model-info -r cn --app-id <APP_ID> --dataset-id <DATASET_ID>
```

**Output:**

- Text mode prints a short summary only: dataset name/id, sync mode, latest partition, partition fields, hot field top list, filter-rule metadata hints, and preview counts.
- JSON mode keeps `data.modelInfo` unchanged for compatibility and adds `data.inspection`.
- `inspection.syncMode`: normalized `full` / `increment` / `unknown` plus raw values when available.
- `inspection.partitionRange`, `inspection.latestPartition`, `inspection.partition.fields`, `inspection.partition.info`: partition metadata when the auxiliary endpoints expose it.
- `inspection.fieldHeat.fields` and `inspection.hotFields`: bounded field heat metadata; `hotFields` is top 10 ranked by heat desc then name asc.
- `inspection.permissionFilterSummary`: filter rule count, bounded field hints, `coverage: "filter_rules_only"`, and warnings. It does not claim complete column-permission denial coverage.
- `inspection.preview`: dimension/metric/field counts and at most 10 preview metadata fields; it does not include raw sample rows.
- `inspection.warnings`: best-effort auxiliary endpoint failures. A warning does not hide a successful `modelInfo`.

`modelInfo` still includes the raw data factory model, such as:

- `baseConf`: Dataset basic configuration (name, owner, description, sync mode, etc.)
- `nodeConf`: Data source configuration, including:
  - `dataSourceType`: e.g., "hive", "click_house"
  - `dbName`: Database name
  - `tbName`: Table name
  - `query`: Underlying SQL query (if any)
  - `fields`: Field schema with types
  - `partitionConfList`: Partition configuration
- `modelType`: Model type (0 = standard)
- Text mode also prints the resolved region as `input -> normalized`; JSON mode returns both `inputRegion` and `normalizedRegion`

**Use cases:**

- Trace metric calculation logic back to underlying data source
- Understand the SQL transformation between raw tables and dataset fields
- Debug data discrepancies by examining the underlying query

---

### dataset-create

Create a **single-source** dataset from a hive/click_house table or custom SQL. Mirrors the dataManage create page.

**Supported create types:**

- Single source table (`--table-name`) → `nodeType=table`
- Custom SQL (`--sql` / `--sql-file`) → `nodeType=sql`

**Supported `--data-source-type`:** `hive` (default, primary) and `click_house`. Multi-table join create and other engines (e.g. Doris) are not supported yet.

```bash
bytedcli aeolus dataset-create [options]
```

**Options:**

- `-r, --region <region>` - Region (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--name <name>` - Dataset name (required)
- `--db-name <dbName>` - Source / SQL-node database name (required)
- `--table-name <tableName>` - Source table name (table mode required); SQL mode optional alias (default `Hive-sql-0` / `ClickHouse-sql-0`)
- `--sql <sql>` / `--sql-file <path>` - Custom SQL for SQL-node create
- `--data-source-type <type>` - `hive` (default) or `click_house`
- `--cluster-name <name>` - Source cluster (default: `cn`)
- `--parent-id <parentId>` - Folder parent ID (default: `0`)
- `--belong <belong>` - Belong flag from dataManage URL (default: `1`)
- `--owner <emailPrefix>` - Owner email prefix (default: current auth user)
- `--dc <dc>` - Data-center for source hive catalog (dataManage VA/SG switcher). `va|sg|cn|ce|cn6`; on VA console **SG → `ce`**, **VA → `cn`**
- `--group-id <groupId>` - Resource group id (auto-picked when the app has exactly one group)
- `--clickhouse-data-source-id <id>` - Destination ClickHouse datasource id written to `syncConf.performanceSettings.dataSourceId`
- `--dimension-field` / `--metric-field` / `--field-descr` - Optional field selection
- `--yes` - Submit create; **default is dry-run**
- `--skip-preview` - Skip previewSchema before create

**Examples:**

```bash
# Dry-run create from SG hive (VA app, console SG switcher)
bytedcli aeolus dataset-create -r va --app-id 1000252 --name demo-dataset --db-name demo_db --table-name sample_table --cluster-name default --data-source-type hive --dc sg --parent-id 13361

# Dry-run create from custom SQL and select the destination ClickHouse datasource
bytedcli aeolus dataset-create -r va --app-id 1000252 --name demo-sql-dataset --db-name demo_db --cluster-name default --data-source-type hive --dc sg --parent-id 13361 --clickhouse-data-source-id 10001 --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\'''

# Submit create and expose selected fields
bytedcli --json aeolus dataset-create -r va --app-id 1000252 --name demo-dataset --db-name demo_db --table-name sample_table --dimension-field p_date --metric-field score --dc sg --yes
```

**Notes:**

- Default is dry-run. Pass `--yes` to actually create.
- On VA dataManage, the left-side VA/SG switcher maps to API `dc` (`cn`/`ce`). Pass `--dc sg` when the hive table lives under the SG catalog.
- If create returns `aeolus/clickHouseCluster/notFoundSuitAbleCluster`, read `syncConf.performanceSettings.dataSourceId` from a compatible Dataset in the same app/resource group and pass it through `--clickhouse-data-source-id`.
- When no field flags are given, all supported source columns are exposed as dimensions.
- Use `--json` to inspect the generated `dataSetV2` payload before submitting.

---

### dataset-update-sql

Update the custom SQL (`nodeType=sql`) on an existing dataset model. Mirrors dataManage edit save:
`allDataSetInfoV2` -> `getTableSchemaFromSql` -> `previewSchema` -> `preCheckDimMetList` -> `PUT /dataFactory/dataSetV2`.

```bash
bytedcli aeolus dataset-update-sql [options]
```

**Options:**

- `-r, --region <region>` - Region (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--sql <sql>` / `--sql-file <path>` - New custom SQL (one required)
- `--node-id` / `--node-name` - Target sql node when multiple exist
- `--dc <dc>` - Optional dc override (default: dataset `baseConf.dc`)
- `--dimension-field` / `--metric-field` / `--field-descr` - Optional field selection
- `--yes` - Submit save; **default is dry-run**
- `--skip-preview` - Skip previewSchema before save

**Examples:**

```bash
# Dry-run SQL update
bytedcli aeolus dataset-update-sql -r va --app-id 1000252 --dataset-id 999001 --sql-file ./demo.sql

# Submit SQL update
bytedcli --json aeolus dataset-update-sql -r va --app-id 1000252 --dataset-id 999001 --sql 'SELECT id FROM demo_db.sample_table WHERE date = '\''${date}'\''' --yes
```

**Notes:**

- Only works for sql-node datasets.
- Keeps existing upstream fields by name; adds new SQL columns as dimensions; drops removed upstream columns; preserves computed fields.
- Default is dry-run. Pass `--yes` to save.

---

### dataset-sync

Trigger or inspect data factory sync/backfill instances for an Aeolus dataset.

```bash
bytedcli aeolus dataset-sync trigger [options]
bytedcli aeolus dataset-sync status [options]
bytedcli aeolus dataset-sync settings get [options]
bytedcli aeolus dataset-sync settings update [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, mybd, sglark, usttpusts (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--start-date <startDate>` - Business start time, e.g. `"2026-04-22 00"` for hourly datasets (required)
- `--end-date <endDate>` - Business end time, e.g. `"2026-05-06 23"` for hourly datasets (required)
- `--queue-name <queueName>` - Trigger only: queue name recorded by the dataManage page
- `--max-parallelism <value>` - Trigger only, default `5`
- `--dry-run` - Trigger only, print the `createSyncJob` payload without submitting
- `--no-check-min-max` - Trigger only, maps to `checkMinMax: false` in the payload
- `--ttl-days <days>` - Settings update only: fixed data lifecycle, `0-1500`
- `--sync-type <type>` - Settings update only: `scheduled` or `manual`
- `--expect-ttl-days <days>` - Settings update only: fail if the current TTL differs
- `--expect-sync-type <type>` - Settings update only: fail if the current mode differs
- `--yes` - Settings update only: submit the Fabric batch PUT; default is dry-run
- `--json` is a global option and must appear before `aeolus`

**Examples:**

```bash
# Submit the same payload as the dataManage sync page
bytedcli aeolus dataset-sync trigger -r cn --app-id <appId> --dataset-id <dataSetId> --start-date "2026-04-22 00" --end-date "2026-05-06 23" --queue-name root.demo_queue --max-parallelism 5

# Inspect the payload first
bytedcli --json aeolus dataset-sync trigger -r cn --app-id <appId> --dataset-id <dataSetId> --start-date "2026-04-22 00" --end-date "2026-05-06 23" --dry-run

# Check instance status after submit
bytedcli aeolus dataset-sync status -r cn --app-id <appId> --dataset-id <dataSetId> --start-date "2026-04-22 00" --end-date "2026-05-06 23"

# Read Fabric default and node-specific sync rules
bytedcli aeolus dataset-sync settings get -r sg --app-id <appId> --dataset-id <dataSetId>

# Preview a Fabric fixed-TTL and sync-mode update
bytedcli aeolus dataset-sync settings update -r sg --app-id <appId> --dataset-id <dataSetId> --ttl-days 60 --sync-type manual --expect-ttl-days 30 --expect-sync-type scheduled

# Apply the reviewed update, poll the async result, and verify the readback
bytedcli aeolus dataset-sync settings update -r sg --app-id <appId> --dataset-id <dataSetId> --ttl-days 60 --sync-type manual --expect-ttl-days 30 --expect-sync-type scheduled --yes
```

**Endpoint mapping:**

- `trigger` mirrors browser `POST /aeolus/api/v3/dataFactory/createSyncJob`
- When `--node-id` is omitted, CLI auto-fills `nodeIdList` from the dataset model. An empty `nodeIdList` returns ok/`previewId` but **does not submit** backfill instances.
- Day-partition datasets (`partitionDefaultFilter=day`) prefer `--start-date/--end-date` as `YYYY-MM-DD`; hourly datasets use `YYYY-MM-DD HH`.
- `status` mirrors browser `POST /aeolus/api/v3/dataFactory/dataSetSyncInfoAllPageBatch`
- `settings get/update` only supports Fabric datasets (`dataSetType=34`).
- Fabric settings read `GET /dataFactory/dataSetSyncSettingsBatch`, save through `PUT /dataFactory/dataSetSyncBatch`, and poll `GET /dataFactory/getDataSetSyncResult`. They do not use ordinary `PUT /dataFactory/dataSetSync`.
- Settings update changes only the `default` rule and preserves node-specific rules, schedule, partition mode, TTL type, and backtracking configuration. Dynamic TTL edits fail closed.
- A single-node Fabric dataset with an empty batch rule list can read its effective ordinary view. Its first CLI save must include `--ttl-days`, because the fallback response does not prove the Fabric TTL type. Multi-node empty configurations fail closed.

---

### dataset-add-source-table

Add a source table into an existing editable dataset model, left join it from an existing table/node, expose selected fields as dimensions or metrics, preview the generated schema, and save through the same V2 data factory endpoint used by the Aeolus edit page.

```bash
bytedcli aeolus dataset-add-source-table [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, mybd, sglark, usttpusts (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <dataSetId>` - Dataset ID (required)
- `--db-name <dbName>` - Source database name (required)
- `--table-name <tableName>` - Source table name (required)
- `--join-from-table <tableOrNode>` - Existing node/table to left join from; accepts `nodeId`, `tbId`, `tbName`, `tableAlias`, or `schemaName` (required)
- `--join-key <key>` - Join key; repeatable. Use `field` for same-name joins or `left=right` when names differ (required)
- `--field <field>` / `--metric-field <field>` - Expose a source field as metric (repeatable)
- `--dimension-field <field>` - Expose a source field as dimension (repeatable)
- `--field-descr <field=descr>` - Override exposed field description (repeatable)
- `--increment-field <field>` - Use incremental extraction by this source field; omitted means full extract
- `--dry-run` - Build and preview the `dataSetV2` payload without saving
- `--skip-preview` - Save without calling `previewSchema`
- `--retry-updating <times>` - Retry save when Aeolus reports the dataset is updating
- `--json` is a global option and must appear before `aeolus`; use it with `--dry-run` to inspect the generated payload

**Example:**

```bash
bytedcli --json aeolus dataset-add-source-table \
  -r cn \
  --app-id <appId> \
  --dataset-id <dataSetId> \
  --db-name demo_db \
  --table-name sample_table \
  --join-from-table sample_prev_table \
  --join-key key1 \
  --join-key key2 \
  --metric-field score \
  --field-descr score=points \
  --increment-field updated_at \
  --dry-run
```

**Notes:**

- This command follows the browser edit flow: `allDataSetInfoV2` -> `tableSchema` -> `previewSchema` -> `dataSetV2`.
- For RDS tables, pass `--db-name` / `--table-name`; do not pass a source `dataSourceId`.
- Use `--dry-run` first on important datasets and review `data.payload` before removing `--dry-run`.

---

### report resolve / report query / report download

Use `aeolus report resolve` to inspect a dataQuery URL's saved report metadata and the dataset field list. Use `aeolus report query` to execute the saved report, fetch generated SQL, or rebuild a scratch query from the same URL using dataset field names. Use `aeolus report download` when the user needs the CSV/XLSX file export written to a file instead of bounded preview rows on stdout.

```bash
# Resolve a dataQuery URL to report metadata, dimMet fields, and saved parameters
bytedcli aeolus report resolve --url "$AEOLUS_REPORT_URL"

# Execute the saved report body
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL"

# Rebuild a scratch query from the same URL using dataset field names
bytedcli aeolus report query --url "$AEOLUS_REPORT_URL" \
  --group-by "country,platform" \
  --metrics "revenue" \
  --filter "p_date[lastSync]=1" \
  --top-n 10 \
  --sort-by "revenue"

# Fetch generated SQL; this still issues a real VizQuery request
bytedcli aeolus report query --format sql --url "$AEOLUS_REPORT_URL"

# Download the saved report result to a file
bytedcli aeolus report download --url "$AEOLUS_REPORT_URL" --output ./report-export

# Download from a query-history id
bytedcli aeolus report download -r va --history-id 789012 --limit 1000000 --output ./history-export

# Download with named filters merged into saved reqJson
bytedcli aeolus report download --url "$AEOLUS_REPORT_URL" --filter "country=SG,US" --output ./filtered-export

# Discover report filters before writing --filter expressions
bytedcli --json aeolus report filters --url "$AEOLUS_REPORT_URL"
```

**Options (`report query`):**

- `--url <aeolusUrl>` - Aeolus dataQuery URL. Region, appId, `id`, `rid`, and `sid` are inferred from the URL when present.
- `-r, --region <region>` - Region; defaults to `cn` when `--url` is not provided.
- `--app-id <appId>` / `--dataset-id <datasetId>` - Explicit app/dataset identity when not using URL.
- `--report-id <reportId>` - Saved report id (`rid`) for auto-resolving `reqJson`.
- `--dim-met <json>` - Low-level dimension/metric entry, repeatable. Keep this as the browser-parity escape hatch.
- `--where <json>` - Low-level where entry, repeatable. Merged into saved `whereList` by field id/name.
- `--group-by <fields>` - Scratch-query dimensions by dataset field name/id; comma-separated and repeatable.
- `--metrics <fields>` - Scratch-query metrics by dataset field name/id; comma-separated. Supports `sum(field)`, `count(field)`, `avg(field)`, and bare metric names.
- `--filter <expr>` - Named filter, repeatable. Form: `field=value`, `field[op]=value`, or `stat_date[thisWeek]`. Date: `last` / `last:week` / `lastSync` / `thisWeek`. Compare: `contains` / `not_in` / `is_null`. Result: `field[having:>]=100` or `avg(field)[>]=100`.
- `--filter-id <expr>` - Field-id filter, repeatable. Form: `123=value1,value2` or `123[op]=value`.
- `--data-source-id <id>` - Override `query.dataSourceId` for report query / scratch VizQuery when the backend requires the browser payload's dataSourceId.
- `--top-n <N>` - Apply server-side Top N to the sort field.
- `--sort-by <field>` / `--sort-order <asc|desc>` - Sort field name/id and order for saved-body sort or scratch Top N.
- `--drill-down <fields>` - Append extra groupBy fields for a follow-up/drill-down scratch query.
- `--limit <N>` - Row limit.
- `--timeout-ms <ms>` - Request timeout in milliseconds.
- `--format <fmt>` - `data` (default) or `sql`.

**Options (`report download`):**

- `--url <aeolusUrl>` - Aeolus dataQuery URL. Region, `rid`, and `id` are inferred from the URL when present.
- `-r, --region <region>` - Region; defaults to `cn` when `--url` is not provided.
- `--report-id <reportId>` - Saved report/chart id (`rid`).
- `--history-id <historyId>` - Query history id (`id`).
- `--filter <expr>` - Named filter, repeatable. Form: `field=value`, `field[op]=value`, or `stat_date[thisWeek]`. Same date / compare / HAVING syntax as `report query`.
- `--filter-id <expr>` - Field-id filter, repeatable. Form: `123=value1,value2` or `123[op]=value`.
- `--limit <N>` - Export row limit. Default is `1000000`; pivot/trend table XLSX downloads are capped at an effective `rowLimit` of `50000`.
- `--output <file>` - Destination CSV/XLSX file. The command writes through a temporary sibling file and atomically replaces the destination after the response is complete.
- An extensionless output path works for every report type. If an extension is used, choose `.csv` for ordinary table/chart reports and `.xlsx` for pivot/trend table reports; mismatched extensions are rejected.
- `--timeout-ms <ms>` - Download request timeout in milliseconds.

**Notes:**

- With `--url` / `--report-id`, saved `reqJson` is reused unless a scratch shape is requested.
- `--filter` / `--filter-id` can be used with saved `reqJson`; they are resolved through the dataset field list and merged into saved filters.
- `--group-by`, `--metrics`, and `--drill-down` rebuild a scratch VizQuery from the resolved dataset. Use them when the URL should be queried at a different grain or with a different metric set.
- `--top-n` / `--sort-by` can be used either with saved config or scratch config. When not rebuilding scratch, pass both `--top-n` and `--sort-by`.
- Most datasets work without `--data-source-id`; add it only when Aeolus returns `aeolus/unknown` and a browser payload or model info shows the required `dataSourceId`.
- `--format sql` extracts `sqlList` from the response, but it is not compile-only; Aeolus still executes the query.
- `report query` and `viz-query` return bounded query results. `report download` uses the Aeolus VizQuery download endpoint for file exports and emits only metadata such as `output`, `sizeBytes`, `queryHistoryId`, format, `rowLimit`, `rowCount`, `limitReached`, and `completeness`.
- CSV `rowCount` excludes the header row. XLSX `rowCount` is `null`; `limitReached` is `"unknown"` and `completeness` is `"unknown"` because bytedcli does not parse workbook contents.

---

### chart get / chart query

Use `aeolus chart get` to read one chart/report's metadata and Simple DSL. Use `aeolus chart query` to preview rows from an online chart ID or from a local temporary chart JSON object.

```bash
# Read chart metadata and Simple DSL
bytedcli aeolus chart get -r va --chart-id 123456

# Include generated SQL; this runs one bounded VizQuery and returns SQL best-effort
bytedcli --json aeolus chart get -r sg --chart-id 123456 --include-sql

# Preview rows from an online chart
bytedcli aeolus chart query -r va --chart-id 123456 --limit 20

# Query with dashboard/sheet context and runtime filters
bytedcli aeolus chart query -r va --chart-id 123456 --dashboard-id 789012 --sheet-id 345678 --filter "country=SG"

# Query a local temporary chart JSON inline
bytedcli aeolus chart query -r va --chart-json-file ./chart.json

# Explain filter merge only; no chart query request is made
bytedcli aeolus chart query -r va --chart-id 123456 --dashboard-id 789012 --sheet-id 345678 --filter "country=SG" --explain-filters
```

**Options (`chart get`):**

- `-r, --region <region>` - Region; defaults to `sg`.
- `--chart-id <chartId>` - Aeolus chart/report id (`rid`).
- `--include-sql` - Execute a bounded VizQuery and return generated SQL best-effort.

**Options (`chart query`):**

- `-r, --region <region>` - Region; defaults to `sg`.
- `--chart-id <chartId>` - Online Aeolus chart/report id (`rid`).
- `--chart-json-file <path>` - Local chart JSON object. Mutually exclusive with `--chart-id`; sent inline and never saved.
- `--dashboard-id <dashboardId>` / `--sheet-id <sheetId>` - Optional dashboard context for permission and sheet filter behavior.
- `--filter <expr>` - Named runtime filter, repeatable. Form: `field=value`, `field[op]=value`, or `stat_date[thisWeek]`. Same date / compare / HAVING syntax as `report query`.
- `--filter-id <expr>` - Field-id runtime filter, repeatable. Form: `123=value1,value2` or `123[op]=value`.
- `--where <json>` - Explicit runtime filter entry, repeatable.
- `--filters-json <json>` - Advanced runtime filter array forwarded as `effectiveFilters`.
- `--explain-filters` - Explain runtime/sheet/chart filter merge and exit before any chart query request.
- `--limit <N>` - Preview row limit. Output is capped at 100 rows.
- `--timeout-ms <ms>` - Request timeout in milliseconds.

**Notes:**

- `--chart-json-file` is read-only. bytedcli sends the parsed JSON to the chart query endpoint and does not call report save/update APIs.
- `--explain-filters` reads metadata/context and makes no real chart query request.
- `chart query` is a preview command. JSON output includes `rowCount`, `returnedRows`, `limit`, `truncated`, `completeness`, and `downloadGuidance`; when truncated, use `report download` or `dashboard download` for file exports.
- `chart get --include-sql` is intentionally not metadata-only. It reads `sqlList` first, falls back to query-history SQL, and may return `sql: null` with `sqlWarning` while metadata retrieval still succeeds.

---

### filter discovery and option values

Use these read-only helpers before applying repeatable `--filter` or `--filter-id`.

```bash
# Structured report filters: report-level, chart/schema, and dataset-field groups
bytedcli --json aeolus report filters --url "$AEOLUS_REPORT_URL"

# Structured dashboard filters: dashboard public, report-level, and chart/schema groups
bytedcli --json aeolus dashboard filters --url "$AEOLUS_DASHBOARD_URL"

# Selectable option values for a filter dimMetId
bytedcli --json aeolus filter options -r va --dataset-id <datasetId> --filter-id <dimMetId> --keyword demo
```

**Output:**

- `groups[]` — grouped filter descriptors.
- Each descriptor includes `name`, `dimMetId`, `op`, `defaultValue`, `source`, `overridable`, `dataSetId`, and optional report/chart context.
- `filter options` returns stable `options[]` entries with normalized `label` and `value`; backend-specific raw fields are not exposed.

**Repeatable filter syntax:**

- `--filter "field=value"` — equality for one value, `in` for comma-separated values.
- `--filter "field[op]=value1,value2"` — explicit operator such as `last`, `lastSync`, `in`, `not_in`, `contains`, `starts_with`, `is_null`, `gt`, or `>=`.
- Date shortcuts: `--filter "stat_date[last]=14"`, `--filter "stat_date[thisWeek]"`, `--filter "stat_date[last:week]=2"`. `lastSync` is only for partition fields.
- Result/HAVING: `--filter "amount[having:>]=100"` or `--filter "avg(amount)[>]=100"`.
- Prefer `--filter` by field name. Use `--filter-id "123=value"` when names are ambiguous and you already have the `dimMetId`.

---

### dashboard query

Discover chart reports and dashboard public filters from a dashboard URL, or query one/all chart reports with bounded preview rows. Use `dashboard download` instead when the user needs CSV/XLSX file exports.

```bash
# Discovery: list selected-sheet charts and public filters
bytedcli aeolus dashboard query --url "$AEOLUS_DASHBOARD_URL"

# Read-only structured filter discovery
bytedcli --json aeolus dashboard filters --url "$AEOLUS_DASHBOARD_URL"

# Query one chart/report with named filters and Top N
bytedcli aeolus dashboard query --url "$AEOLUS_DASHBOARD_URL" \
  --report-id 345678 \
  --filter "country=SG" \
  --sort-by "revenue" \
  --top-n 10

# Query every report in the selected sheet with per-report failure isolation
bytedcli --json aeolus dashboard query -r va --dashboard-id 123456 --sheet-id 789012 --all-reports --limit 20
```

**Options (`dashboard query`):**

- `--url <aeolusUrl>` - Aeolus dashboard URL. Region, dashboard id, optional sheet id, and optional report id are inferred when present.
- `-r, --region <region>` - Region; defaults to `cn` when `--url` is not provided.
- `--dashboard-id <dashboardId>` - Dashboard id.
- `--sheet-id <sheetId>` - Sheet id. If omitted, Aeolus chooses the current/default sheet.
- `--report-id <reportId>` - Query one report from the selected sheet.
- `--all-reports` - Query every report from the selected sheet. Execution is serial and each report failure is isolated in `failed[]`.
- `--filter <expr>` - Named filter, repeatable. Form: `field=value`, `field[op]=value`, or `stat_date[thisWeek]`. Same date / compare / HAVING syntax as `report query`. The field matches a dashboard filter candidate (public filter name or report whereList condition name) first; an all-digit field then matches by `dimMetId` — the only handle for **unnamed** report whereList conditions (typically dates): `--filter "<dimMetId>[gte]=<date>" --filter "<dimMetId>[lte]=<date>"`. Candidate dimMetIds show up in discovery `publicFilters[]` and in the unmatched-filter error's candidate list. Filters that match no candidate fall back to dataset named filters, which requires dataset access (board-only permission gets a 403 with the candidate list in the hint).
- `--top-n <N>` - Apply Top N to `--sort-by` and use `N` as the effective preview limit. Requires `--sort-by`.
- `--sort-by <field>` / `--sort-order <asc|desc>` - Sort field name/id and order.
- `--limit <N>` - Preview row limit. Default is `100`.
- `--timeout-ms <ms>` - Per-report VizQuery timeout in milliseconds.
- `--with-sql` - Include the executed SQL per successful report (`sqlList`; `sqlWarning` explains failures). The executed SQL is where symbolic date filters (e.g. `lastSync`) appear resolved to real partition dates — the way to confirm data freshness on daily-snapshot boards. Adds up to two serial requests per report when the VizQuery response lacks SQL; the SQL may contain sensitive table/column names, avoid pasting into public logs.

**Notes:**

- Without `--report-id` or `--all-reports`, the command is discovery-only and returns `reports[]` plus a `publicFilters[]` summary.
- Single/all-report query results use stable `results[]` and `failed[]` arrays. Successful items include `chartId`, `reportId`, `name`, `status`, `columns`, `rows`, `rowCount`, `returnedRows`, `limit`, `truncated`, `queryHistoryId`, and `fileGuidance`.
- `truncated:true` means returned rows reached the effective preview limit. Use `aeolus dashboard download` for file exports.
- `dashboard query` reuses the selected dashboard sheet's saved report `reqJson` and dashboard public filters, then merges CLI `--filter` overrides by candidate name or dimMetId (all-digit fields; name match wins first).

---

### dashboard diff

Compare a local dashboard sheet JSON payload with the current online `simpleSheet` payload. This is read-only and does not query dashboard data rows.

```bash
bytedcli aeolus dashboard diff -r cn --app-id <appId> --dashboard-id <dashboardId> --sheet-id <sheetId> --payload-file ./simple-sheet.json
bytedcli --json aeolus dashboard diff -r va --app-id <appId> --dashboard-id <dashboardId> --sheet-id <sheetId> --payload-file ./simple-sheet.json
```

**Options (`dashboard diff`):**

- `-r, --region <region>` - Region (required).
- `--app-id <appId>` - Aeolus app id.
- `--dashboard-id <dashboardId>` - Dashboard id.
- `--sheet-id <sheetId>` - Sheet id.
- `--payload-file <file>` - Local JSON object payload. A direct object is compared as-is. Common bytedcli wrappers such as `{ "status": "success", "data": { "data": { ... } } }` are unwrapped when unambiguous.

**Notes:**

- The command fetches online state through `sheet/simpleSheet` only.
- Object keys are canonicalized recursively; array order is preserved.
- Output includes `equal`, `changedCount`, `changes[]`, `localHash`, and `remoteHash`. Each change has a deterministic `path`, `kind` (`added`, `removed`, `changed`), and bounded JSON value summaries.
- `dashboard diff` does not save, update, publish, delete, sync, or create dashboard resources. Dashboard sync/delete/new flows remain unsupported/deferred here.

---

### dashboard download

Download report file exports from a dashboard sheet. Pass either one `--report-id` or `--all-reports`; each successful report writes one CSV/XLSX file under `--output`.

```bash
bytedcli aeolus dashboard download --url "$AEOLUS_DASHBOARD_URL" --all-reports --output ./dashboard-export
bytedcli aeolus dashboard download -r va --dashboard-id 123456 --sheet-id 789012 --report-id 345678 --output ./dashboard-export
bytedcli aeolus dashboard download --url "$AEOLUS_DASHBOARD_URL" --report-id 345678 --report-filter '[{"id":123,"val":["demo"]}]' --output ./dashboard-export
```

**Options (`dashboard download`):**

- `--url <aeolusUrl>` - Aeolus dashboard URL. Region, dashboard id, optional sheet id, and optional report id are inferred when present.
- `-r, --region <region>` - Region; defaults to `cn` when `--url` is not provided.
- `--dashboard-id <dashboardId>` - Dashboard id.
- `--sheet-id <sheetId>` - Sheet id. If omitted, Aeolus chooses the current/default sheet.
- `--report-id <reportId>` - Download one report from the selected sheet.
- `--all-reports` - Download every report from the selected sheet.
- `--report-filter <json>` - JSON array of dashboard filter overrides, for example `[{"id":123,"val":["demo"]}]`.
- `--limit <N>` - Per-report export row limit. Default is `1000000`; pivot/trend table XLSX downloads are capped at an effective `rowLimit` of `50000`.
- `--output <directory>` - Destination directory.
- `--timeout-ms <ms>` - Per-report download timeout in milliseconds.

**Notes:**

- Batch mode is serial and continues after individual report failures.
- JSON mode always returns stable `results[]` and `failed[]` arrays. Use `results[].output` for downloaded files and `failed[].message` for per-report errors.
- Successful `results[]` entries include `rowCount`, `limitReached`, and `completeness`; CSV row counts exclude the header row and XLSX row counts are unknown.
- Filter discovery remains a separate capability; `dashboard download` does not replace dedicated filter-list commands.
- This is a file export, not the bounded preview returned by `report query` / `viz-query`.

---

### report create

Use `aeolus report create` when the user needs an openable/shareable Aeolus page, not just a one-off query result. The legacy flat alias `aeolus save-viz-query` still works but is hidden from help.

Typical cases:

- Turn a verified `viz-query` into a saved report page
- Share "yesterday users", "distinct app_id list", or a simple aggregate result
- Produce a visual page link for `hrbi_mycis`, where Query Editor is unavailable

```bash
bytedcli aeolus report create [options]
```

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, hrbimycis, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--app-id <appId>` - Aeolus app ID (required)
- `--dataset-id <datasetId>` - Dataset ID (required)
- `--name <name>` - Saved query name (required)
- `--desc <desc>` - Saved query description
- `--dim-met <json>` - One dimension/metric entry, repeatable
- `--where <json>` - One filter entry, repeatable. Absolute date range: `{"op":"range","val":["2026-08-01","2026-08-03"],"dataTypeName":"date"}` is normalized to the page/VQS `between` op with full-day boundaries and `option.dateMode:"absolute"`.
- `--param <json>` - One in-chart parameter (dataset public param), repeatable
- `--data-source-id <id>` - Override the region default dataSourceId
- `--report-id <reportId>` - Overwrite an existing saved query by report ID
- `--period-compare <spec>` - Period comparison (同环比), repeatable. Type is required (`relativeRatio`, `lastyearRatio`, `lastweekRatio`, `lastmonthRatio`)
- `--totals [spec]` - Table totals. Default: row. Also: `col`, `row,col`
- `--forecast [spec]` - Forecast. Default: 7 day steps. Also: `7`, `7d`

**Examples:**

```bash
# Save a grouped page (yesterday distinct users by email)
bytedcli aeolus report create -r hrbi_mycis --app-id 667 --dataset-id 2926 --name "yesterday-users" \
  --dim-met '{"dimMetId":1590328021777,"name":"email","expr":"`email`","roleType":0}' \
  --where '{"dimMetId":1590328021772,"name":"pdate","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'

# Save an aggregate page (yesterday row count)
bytedcli aeolus report create -r hrbi_mycis --app-id 667 --dataset-id 2926 --name "yesterday-count" \
  --dim-met '{"dimMetId":1590328021772,"name":"pdate","expr":"`pdate`","roleType":1,"aggregation":"count("}' \
  --where '{"dimMetId":1590328021772,"name":"pdate","op":"lastSync","val":[1],"valOption":{"datetimeUnit":"day","anchorOffset":0}}'
```

**Notes:**

- `aeolus report create` calls `POST /aeolus/api/v3/dataMart/report`, and shareable links use `/aeolus/pages/dataQuery?...&rid=<reportId>&sid=<datasetId>`.
- Before `POST`/`PUT`, the CLI runs the final saved `reqJson` as a one-row VizQuery preflight; a query/schema/filter failure aborts without saving, so a success result means the returned page config was accepted by the same VQS path DataQuery uses.
- `hrbi_mycis` defaults to `dataSourceId=10035`; other regions require explicit `--data-source-id` when no built-in mapping exists.
- Save responses may return `data.reportId`, `data.id`, or `data.lastInsertId` with `code=0`.
- Aggregate payloads should stay on the normal aggregate path: use IDs like `count_<dimMetId>`, keep `sourceType: "aggr"`, set `realMetricTableRouteConfig.isRealMetricQuery = false`, and do not emit `real_metrics_*` / `metricConf`.
- To avoid page-side query errors, keep browser-parity metadata such as `query.dimMetList`, `schema.customConfig.fields.details=[]`, `originalSchema`, `requestId`, and `locale: "zh_CN"`.
- `--chart-type <type>` saves a chart instead of the default `table`. Family types: `table`, `measure_card`, `line`, `column`, `bar`, `bar_percent`, `area`, `pie`, `double_axis`, `histogram`, `pivot_table`, `funnel`, `combination`, `sankey`, `gauge`, `progress`, `waterfall`, `scatter`, `radar`, `word_cloud`, `bilateral`, `map`. Page aliases: `raw_table`, `column_percent`, `column_parallel`, `bar_parallel`, `area_percent`, `annular`, `rose`, `circle_views`, `comparative_measure_card`, `measure_trend`, `waterfall_change`, `scatter_map`, `gis_*`. `trend_table` / `okr_table` are not create types. `--table-calc`, `--mini-chart`, `--period-compare`, `--totals`, and `--forecast` write analysis on create/update. Period comparison writes `schema.periodCompare` plus derived measures. Totals write `query.calculation.combined`. Forecast writes `schema.forecast` with day granularity.
- `--set`, `--field-format`, and `--conf-file` overlay display style after the chart preset is built. Same language as `report style update`.

### report style

Read or patch the display style of a saved report without rebuilding the query.

```bash
bytedcli --json aeolus report style get --url "$AEOLUS_REPORT_URL"
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" --set legend.legendPos=bottom --field-format "amount=ms"
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" --set axisMeasure.0.titleEnable=true
bytedcli aeolus report style update --url "$AEOLUS_REPORT_URL" --set legend.legendPos=bottom --yes
```

Default is dry-run. Pass `--yes` to PUT. `--set` paths are dotted keys inside `display.conf`. Copy them from `style get --json` `paths[].path`; numeric segments are array indices. `style get` also returns `styleFamily` and `allowedConfKeys` for this chart type; do not copy a table conf onto a line chart. Field-format presets: `money`, `money_wan`, `auto`, `default`, `int`, `percent`, `permil`, `raw`, `ms`, and 数字 units `千`/`万`/`百万`/`千万`/`亿`/`K`/`M`/`B`. `--field-format "*=percent"` applies to every measure. Use `report update` only when dimensions, metrics, filters, or analysis (`--table-calc` / `--mini-chart` / `--period-compare` / `--totals` / `--forecast`) must change. `report style update` does not accept those analysis flags.

#### In-chart parameters (`--param`)

图内参数（dataset public params，如 `sample_flag IN({sample_flag})`）是数据集模型 SQL 里的公共参数，和普通 `--where` 是两套机制：`--param` 通过 `paramList` 注入选中值，页面上以「图内参数控件」形式展示，可交互切换。

```bash
# 保存带图内参数的报表：只给 name 即可，id / 可选值 / emptyConfig 由数据集自动解析
bytedcli aeolus report create -r va --app-id 1000000 --dataset-id 2000000 --data-source-id 668 \
  --name "demo report by category" \
  --dim-met '{"dimMetId":1700000000001,"name":"category","expr":"category","roleType":0,"dataType":"string"}' \
  --dim-met '{"dimMetId":1700000000002,"name":"field_cnt","expr":"count(distinct `field_id`)","roleType":1,"dataType":"int"}' \
  --param '{"name":"sample_flag","val":["A"]}' \
  --param '{"name":"sample_region_not_in","val":["region-x","region-y"]}'
# 先查数据集有哪些图内参数及可选值（Dataset in-chart parameters 段）
bytedcli aeolus report resolve -r va --app-id 1000000 --report-id <rid> -j
```

**Agent Guidance:**

- `--param` 条目至少给 `id` 或 `name` 其一；推荐只给 `name` + `val`，`id` / `type` / `initVal` / `emptyConfig` 会自动从 `dataSetModelInfo`（`nodeConf[*].tempParamsInfo`）解析，避免手填出错。
- 保存报表时 CLI 会同时写入 `query.paramList`（决定 SQL 实际过滤）与 `schema.parameters`（决定页面控件渲染，含 `visible` / `isIntial` / `isIntialVisible` / `emptyConfig`）。**两者缺一都会让控件不渲染**——旧版本只写 `paramList` 时页面看不到「图内参数选项」，现已修复。
- `aeolus report resolve` 输出里 `Saved in-chart parameters`（当前报表已保存的选值）与 `Dataset in-chart parameters`（数据集声明的全部可筛选参数及 `Allowed Values`）分开展示；先 resolve 拿可选值，再用 `--param` 复现或调整。

---

### dataset-add-fields

Add computed dimensions/metrics to an existing editable dataset, then save via the same data factory `dataSetV2` edit endpoint used by the dataManage page.

```bash
bytedcli aeolus dataset-add-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --metric "accuracy=[right_count]/[total_count]" \
  --dim "category=get_json_object(\`payload\`, '\$.cat')"
```

**Options:**

- `-r, --region <region>` (required)
- `--app-id <appId>` (required)
- `--dataset-id <dataSetId>` (required)
- `--dim <name=expression>` - Computed dimension, repeatable
- `--metric <name=expression>` - Computed metric, repeatable; expressions may reference other fields via `[name]`
- `--dry-run` - Preview the change without saving

**Notes:**

- Reads `allDataSetInfoV2`, appends computed fields (metrics `mapType=1`, dims `mapType=0`, both `isUpstreamField=false`), pre-checks via `preCheckDimMetList`, and saves with `dataSetV2`.
- Retries with backoff while a freshly edited dataset reports `saveForbidden`/`updating`.
- Duplicate field names are rejected.

---

### dataset-update-fields

Update one or more existing computed dimension/metric expressions in place. The command preserves the persisted field ID, role, and ordering; Aeolus revalidates and may re-infer the expression output type.

```bash
# Default dry-run: fetch and precheck the complete model without saving
bytedcli --json aeolus dataset-update-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --field "accuracy=[right_count]/nullIf([total_count], 0)"

# Apply the checked update
bytedcli --json aeolus dataset-update-fields -r va --app-id 1000252 --dataset-id 3436909 \
  --field "accuracy=[right_count]/nullIf([total_count], 0)" --yes
```

**Options:**

- `-r, --region <region>` (required)
- `--app-id <appId>` (required)
- `--dataset-id <dataSetId>` (required)
- `--field <name=expression>` - Existing computed field and its new expression, repeatable
- `--yes` - Save the update; without it the command is a dry-run

**Notes:**

- Splits each `--field` at the first `=`, so comparisons such as `if([flag] = 1, 1, 0)` remain intact.
- Only editable computed fields can be updated; source, partition, auto-added, missing, duplicate-request, and ambiguous-name fields are rejected before save.
- A batch is atomic: the command applies every requested expression to one in-memory model, calls `preCheckDimMetList`, then performs one `PUT /dataFactory/dataSetV2` only with `--yes`.
- Target fields keep their IDs, roles, and ordering. Their cached `fullExpr`/`fieldList`, plus those of direct/transitive dependents, are invalidated so Aeolus can rebuild canonical dependency expressions.
- Ready-state retries re-fetch the model before applying the patch again, preserving unrelated concurrent edits.

---

### dataset-remove-fields

Remove dimensions/metrics from an existing editable dataset by name.

```bash
bytedcli aeolus dataset-remove-fields -r va --app-id 1000252 --dataset-id 3436909 --field old_metric
```

**Options:**

- `-r, --region <region>` (required)
- `--app-id <appId>` (required)
- `--dataset-id <dataSetId>` (required)
- `--field <name>` - Field name to remove, repeatable
- `--force` - Remove even a referenced or partition field
- `--dry-run` - Preview the change without saving

**Notes:**

- By default blocks removing a field referenced by another field's expression (`[name]`) or a partition/auto-added field; `--force` overrides.
- Refuses to remove every field.

---

### query

Execute SQL query against a dataset.

```bash
bytedcli aeolus query <datasetId> <sql> [options]
```

**Arguments:**

- `datasetId` - Dataset ID
- `sql` - SQL query string

**Options:**

- `-r, --region <region>` - Region: cn, sg, va, euttp, euttp2, eupipo, mycis, jplark, mybd, sglark, uspipo, usttpusts, usbd (required)
- `--json` is a global option and must appear before `aeolus`
- `--version <version>` - API version (default: "v2")
- `--limit <limit>` - Limit rows in output (default: 100)

**Important:** there are two query paths:

- **Logical dataset SQL**: may work for some datasets, especially simpler pre-materialized ones.
- **Physical-table SQL**: often the reliable path for report/dataQuery URLs and for datasets whose semantic fields do not map directly to queryable identifiers.

**Examples:**

```bash
# Logical dataset SQL may work for some datasets
bytedcli aeolus query -r va 1576311 "SELECT \`[p_date]\`, \`[scene]\` FROM \`[DatasetName]\` WHERE \`[p_date]\` = '2026-03-01' LIMIT 5"

# Physical-table SQL is the reliable fallback when logical SQL fails
bytedcli aeolus query -r va 1576311 "SELECT reporting_ad_id, max(pangle_rolling3d_dollar_cost) AS pangle_rolling3d_dollar_cost FROM \`aeolus_data_db_xxx\`.\`aeolus_data_table_xxx\` WHERE p_date = '2026-03-01' GROUP BY reporting_ad_id ORDER BY pangle_rolling3d_dollar_cost DESC LIMIT 10"
```

**Output:**

- Column headers
- Data rows in table format
- Text mode also prints the resolved region as `input -> normalized`; JSON mode returns both `inputRegion` and `normalizedRegion`

**Large integer (Int64) handling:**

ClickHouse / Hive 19-digit ID columns (e.g. `order_id`, `user_id`, `shop_id`) exceed JS `Number.MAX_SAFE_INTEGER` (2^53−1). A naive `JSON.parse` would round them into a `...000` float. bytedcli parses Aeolus query responses through `json-bigint` with `storeAsString: true`, which decides per literal at parse time and emits any long integer as a string so precision is never lost:

- Bare Int64 literal from the backend → returned as a **quoted string** in `--json` output (full 19 digits).
- Explicit `cast(col as String)` in SQL → also returned as a string.
- Short numeric literals stay as JSON numbers. The threshold is based on the JSON numeric literal's character length (json-bigint emits a string when `string.length > 15`, including the sign), which is slightly more conservative than `MAX_SAFE_INTEGER` but always within float64's safe range.
- This parser is not Aeolus column-type-aware: non-Int64 long numeric literals (for example 16-digit safe integers or long decimal literals returned as JSON numbers) may also be returned as strings.

Guidance for LLM / agent consumers:

- Treat long IDs as strings end-to-end. **Do not** call `Number(id)` or `parseInt(id)` — that re-introduces float64 precision loss.
- When forwarding IDs to downstream APIs (order lookup, etc.), pass the string through verbatim.
- You do not need to distinguish "bare Int64" from "cast-as-String" — both arrive as strings on the wire.

Example (`--json` output excerpt):

```json
{
  "rows": [
    ["6926335196492169868", 3998],
    ["6926341275722939951", 2039]
  ]
}
```

---

## SQL Syntax

Aeolus uses ClickHouse SQL syntax, but the table/field syntax depends on whether you are querying a logical dataset alias or the backing physical table.

### Logical dataset names may not be queryable

Some datasets accept logical SQL like:

```sql
FROM `[Dataset Name]`
SELECT `[field_name]`
```

But many report/dataQuery-backed datasets do **not**. Common failure signatures include:

- `unknownTable`
- `unknownIdentifier` / missing field errors
- `SELECT * LIMIT 1` only returning `dummy`

When you see those signals, switch to physical-table discovery instead of continuing to debug the logical alias.

### Physical-table SQL

The reliable fallback is to query the physical table directly after locating it via `dataset-model-info` and `system.query_log`:

```sql
FROM `aeolus_data_db_xxx`.`aeolus_data_table_xxx`
SELECT reporting_ad_id, sum(placement_dollar_cost_1d/100000) AS cost
```

### Partition Fields

If a dataset or physical table has partition fields (for example `p_date`), include them in the `WHERE` clause whenever applicable:

```sql
WHERE p_date = '2026-03-01'
```

### Recommended workflow for report/dataQuery URLs

1. Use `resolve-report` to map the URL to dataset IDs.
2. Use `dataset-fields` to inspect semantic fields and partition fields.
3. Use `dataset-model-info` to inspect `nodeConf[].query`, lineage, and source-table hints.
4. If logical SQL fails or only returns `dummy`, query `system.query_log` to find the backing physical table.
5. Query the physical `aeolus_data_db_*`.`aeolus_data_table_*` table directly.

### End-to-end fallback example

```bash
# Resolve the report URL
bytedcli aeolus resolve-report --url "$AEOLUS_REPORT_URL"

# Inspect the dataset fields
bytedcli aeolus dataset-fields -r va <DATASET_ID>

# Inspect the model / source logic
bytedcli aeolus dataset-model-info -r va --app-id <APP_ID> --dataset-id <DATASET_ID>

# Locate the physical table from query_log
bytedcli aeolus query -r va 2231500 "SELECT event_time, query FROM system.query_log WHERE query LIKE '%aeolus_data_table_%' ORDER BY event_time DESC LIMIT 50"

# Query the physical table directly
bytedcli aeolus query -r va 2231500 "SELECT reporting_ad_id, sum(placement_dollar_cost_1d/100000) AS cost FROM \`aeolus_data_db_xxx\`.\`aeolus_data_table_xxx\` WHERE p_date = '2026-04-07' AND placement = 'Pangle' GROUP BY reporting_ad_id ORDER BY cost DESC LIMIT 5"
```

---

## Query Editor

Ad-hoc SQL under `aeolus query-editor`. Uses QE HTTP APIs under `{baseUrl}/qe/v2/api/...` from the region map in `src/api/aeolus/site.ts`. CN Query Editor uses `https://data.bytedance.net` in both office and production-network profiles because the production CN dataset gateway does not expose the QE path; SG/VA follow their selected network profile host.

**Auth:** Reuses `bytedcli auth login` (Titan Passport cookie) for most regions. **`euttp`** uses the EU-scoped Titan issuer selected by `--site eu-ttp`; do not reuse a ROW `i18n-tt` passport. If EU-TTP QE rejects that passport, use **`bytedcli --site eu-ttp aeolus query-editor login`** as the product-session fallback. **`euttp2`** (NO1A, `aeolus-no.tiktok-eu.net`) also uses `--site eu-ttp`, but exchanges through the host-specific **`do-no.tiktok-eu.net`** issuer because that gateway only accepts a `no/`-prefixed `titan_passport_id`; the `euttp` issuer's `clover/` passport is rejected with HTTP 401 `[Titan] Invalid Params: Invalid titan_passport_id`. `euttp2` is not a session-auth region, so `query-editor login` is not a fallback for it. **`mycis`**, **`mybd`**, **`usttpusts`** and **`usbd`** use **session** auth instead (local browser/product cookies); `usttpusts` requires **`bytedcli --site us-ttp-usts aeolus query-editor login`**. See `references/invocation.md` for `--site` / `BYTEDCLI_CLOUD_SITE`.

**Hive yarn defaults:** the Hive `run` body's `yarn.{cluster_id, idc}` is derived per region, and a mismatch is accepted with `code:0` but never scheduled onto a worker. Known non-default mappings: `sglark` → `shark` / `SGSAAS1LARKIDC1`, `usttpusts` → `default` / `USEAST5`, `eupipo` → `default` / `IE2`, `euttp2` → `wyodel01` / `NO1A` (queue `root.bytecloud_batch_no1a`); everything else defaults to `default` / `LF`. `--idc` overrides the idc; `cluster_id` is always region-derived.

**QE App ID:** Request header `x-qe-appid` defaults from `QE_APP_ID` or `BYTEDCLI_AEOLUS_QE_APP_ID` (CLI default in code if unset). Match the **Query Editor page URL `appId=`** when reproducing browser runs.

### `aeolus query-editor tmp-table create`

Upload a local CSV file, preview the inferred schema, and create a Query Editor temporary table. The command defaults to dry-run and only previews the upload / preview / create plan. Pass `--yes` to execute the browser flow: `POST /tmp_table/upload?db_name=...` (multipart `file`) → `POST /tmp_table/preview` → `POST /tmp_table/create`.

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

- `--file <path>` and `--table-name <name>` are required.
- `--db-name` defaults to `facade_qe_tmp_table`.
- `--ttl` defaults to `30` days.
- `--delimiter` defaults to comma; use `$'\t'` for TSV.
- The default is dry-run. Pass `--yes` to upload and create the table.
- `--idc` defaults to `LF`; pass `--overwrite` with `--yes` to send `over_write:true`.
- The command reuses Query Editor auth and `x-qe-appid`; set `QE_APP_ID` / `BYTEDCLI_AEOLUS_QE_APP_ID` to the page `appId=` when creating temp tables in a non-default workspace.

### `aeolus query-editor folder cleanup-temp`

Clean duplicate Query Editor temp folders, primarily historical `_bytedcli_temp` folders created by one-shot queries. The command is a write operation and defaults to dry-run.

```bash
bytedcli aeolus query-editor folder cleanup-temp -r mycis --dry-run
bytedcli aeolus query-editor folder cleanup-temp -r mycis --keep-id <folderId> --yes
```

**Options:** `-r/--region`, `--name <name>` (default `_bytedcli_temp`), `--keep-id <id>`, `--dry-run`, `--yes`, `--include-non-empty`.

Default behavior: keep the most recently updated matching folder, delete only empty duplicates, and skip non-empty folders. Pass `--keep-id` to choose the retained folder explicitly. Pass `--include-non-empty` only after inspecting the dry-run output.

### `aeolus query-editor query run`

```bash
bytedcli aeolus query-editor query run [options]
```

**Required (soft-required by CLI):**

- `--file-id <id>` — Query file (`block_id` in API body)
- `--folder-id <id>` — Folder (`page_id` in API body)

**Common options:**

- `-r, --region <region>` — `cn` | `sg` | `va` | `euttp` | `euttp2` | `eupipo` | `mycis` | `mybd` | `sglark` | `usttpusts` | `usbd` (default `cn` if omitted)
- `--sql <sql>` — Inline SQL
- `--file <path>` — SQL from disk (if neither `--sql` nor `--file`, CLI may read SQL from the file record)
- `--queue <name>` — **Hive (default): required.** YARN queue name in `yarn.queue` (use `aeolus query-editor queues` to list). **CH (`--engine ch`):** maps to `cluster_name` unless `--cluster-name` is set. **datasource (`--engine datasource`): not used.**
- `--idc <idc>` — **Hive only:** IDC in `yarn.idc`
- `--engine <engine>` — `hive` (default), `ch` (ClickHouse runner: `/ch/task/run`), or `datasource` (user-defined datasource e.g. DORIS: `/datasource/task/run`)
- `--cluster-name <name>` — **CH only:** overrides `cluster_name` in submit body (otherwise use `--queue`)
- `--ch-region <code>` — **CH only:** `region` field in submit body (e.g. `VA`); if omitted, derived from `-r`
- `--datasource-id <id>` — **datasource only:** `datasource_id` from `aeolus query-editor datasources` (e.g. a user-defined DORIS source). Required unless resolved from `--datasource-name`
- `--datasource-type <type>` — **datasource only:** `datasource_type`, e.g. `DORIS`. Required unless resolved from `--datasource-name`
- `--datasource-name <name>` — **datasource only:** resolve `datasource_id` + `datasource_type` by name via `aeolus query-editor datasources`. Needs `QE_APP_ID` set to your Query Editor workspace appId (custom datasources are appId-scoped). `--datasource-id` takes precedence when both are given
- `--adhoc-date <date>` — **Hive only:** set one query date (`YYYY-MM-DD`) for SQL placeholders such as `${date}` or `${DATE}` without changing the SQL text
- `--batch-start-date <date>` / `--batch-end-date <date>` — **Hive only:** submit a multi-day QE batch date range (`YYYY-MM-DD`, inclusive; must span at least two dates)
- `--batch-concurrency <N>` — **Hive only:** multi-day QE batch concurrency, sent as `max_tasks` (`1-120`; default `min(date count, 120)`)
- `--no-wait` — Submit only; do not poll
- `--rows <N>` — Poll/display row cap for status polling path
- `--timeout <seconds>` — Poll timeout

**Engines:**

| `--engine`       | Submit URL suffix      | Body highlights                                                                                                                          |
| ---------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `hive` (default) | `/hive/task/run`       | `query_type`: `ADHOC` by default or `BATCH` with `range` and `max_tasks` for date placeholder runs; `yarn`: `queue`, `idc`, `cluster_id` |
| `ch`             | `/ch/task/run`         | `cluster_name`, `region`, `page_id`, `block_id`, `query`, `query_template`, `task_name`, `template_conf`                                 |
| `datasource`     | `/datasource/task/run` | `datasource_id`, `datasource_type`, `page_id`, `block_id`, `query`, `query_template`, `task_name`, `template_conf`                       |

For **`ch`**, `cluster_name` must be non-empty: provide **`--queue`** and/or **`--cluster-name`**.
For **`datasource`**, identify the source either by **`--datasource-id` + `--datasource-type`** directly, or by **`--datasource-name`** (resolved to id+type via `aeolus query-editor datasources`). No `--queue` / `--idc` is sent. Custom datasources only appear in the list — and name resolution only works — when **`QE_APP_ID`** matches the Query Editor workspace that owns the source (see below).

**Hive date placeholders:** pass `--adhoc-date` for one date; the CLI keeps SQL text unchanged and sends the date through the QE run request as a same-day `range` with `max_tasks=1` so QE can expand `${date}` / `${DATE}`. SQL that already contains `${date}` or `${DATE}` can be used as-is; no source SQL rewrite is needed. If the SQL has no date placeholder and uses a fixed literal, `--adhoc-date` and batch date options are still accepted but usually do not change the query result. Pass `--batch-start-date` + `--batch-end-date` only for a multi-day inclusive range; then the CLI sends `query_type:"BATCH"`, `range.start_date`, `range.end_date`, and `max_tasks` from `--batch-concurrency` or the default `min(date count, 120)`. If date options are omitted, the request remains the legacy `query_type:"ADHOC"` and no date/range fields are sent. Date placeholder options are rejected for `--engine ch` and `--engine datasource`; same-day start/end ranges are rejected and should use `--adhoc-date` instead.

```bash
# Multi-day Hive batch: QE expands ${date}; max_tasks controls batch concurrency.
bytedcli aeolus query-editor query run --file-id <fileId> --folder-id <folderId> --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7

# Single-day query date: keep ${date}/${DATE} in SQL; --adhoc-date is sent through the QE request.
bytedcli aeolus query-editor query run --file-id <fileId> --folder-id <folderId> --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --adhoc-date 2026-08-12
```

QE multi-day batch submission creates one parent task plus date-expanded child tasks. Use the parent `taskId` returned by `query run` with `query status`; the status/result path still returns the merged preview for that parent. In JSON output, inspect `rowCount`, `returnedRows`, and `truncated` to distinguish full vs capped previews.

**`HTTP 406` responses:** QE rejects a run with a bare `HTTP 406` (no body detail) when the account lacks permissions on the queried table, or when the table/cluster requires an explicit queue and IDC. Apply for table permissions via `bytedcli coral permission apply`, or re-run with `--queue <queue> --idc <idc>`. If 406 persists with queue/idc set, re-run with the global `--http-debug` flag to inspect the raw response. The CLI attaches this hint to `HTTP 406` errors automatically.

### `aeolus query-editor query parse`

Parse/check SQL through the same Query Editor endpoint used by the browser Parse button. This does **not** submit or run a task.

```bash
bytedcli aeolus query-editor query parse [options]
```

**Input:** `--sql <sql>` or `--file <path>`

**Options:** `-r/--region`, `--idc` for Hive, **`--engine` / `--cluster-name` / `--ch-region`** for ClickHouse (CH also accepts `--start-date` / `--end-date`, mapping to `query_start_date` / `query_end_date`), and **`--datasource-id` / `--datasource-type` / `--datasource-name`** for a user-defined datasource (see `query run` for how the datasource identity is resolved; `--datasource-name` needs `QE_APP_ID`).

**Endpoint mapping:**

| `--engine`       | Parse URL suffix           | Body highlights                                                                  |
| ---------------- | -------------------------- | -------------------------------------------------------------------------------- |
| `hive` (default) | `/hive/task/explain`       | `query`, `idc` (defaults from the same region mapping used by Hive run)          |
| `ch`             | `/ch/task/explain`         | `query`, optional `cluster_name`, `region`, `query_start_date`, `query_end_date` |
| `datasource`     | `/datasource/task/explain` | `query`, `datasource_id`, `datasource_type` (no `queue` / `idc`)                 |

`status=SUCCESS` means the SQL passed the Query Editor parse/check path. Semantic errors are returned as a successful CLI response with `ok:false`, `status`, `displayMessage`, and `rawErrorMessage`, matching the browser's non-submitting parse behavior.

For **`--engine datasource`**, the check runs against the real custom datasource (e.g. DORIS): a valid query returns the resolved output columns in `fields` (`ok:true`), while a missing table / syntax error returns `ok:false` with the backend message. This is the correct way to parse DORIS SQL — the default (hive) parser cannot see custom-datasource tables and will misreport them as "not found".

### `aeolus query-editor query status`

```bash
bytedcli aeolus query-editor query status [options]
```

**Required:** `--task-id`, `--file-id`, `--folder-id`

**Options:** `-r/--region`, `--rows`, and the same **`--engine` / `--cluster-name` / `--ch-region` / `--datasource-id` / `--datasource-type`** as `query run`. **Must match the engine used for submit**, otherwise the wrong `/hive/task/.../status` vs `/ch/task/.../status` vs `/datasource/task/.../status` path is used.

### `aeolus query-editor query logs`

```bash
bytedcli aeolus query-editor query logs [options]
```

**Required:** `--task-id`

**Options:** `-r/--region`, **`--engine`** (and optional `--cluster-name`, `--ch-region`, `--datasource-id`, `--datasource-type` for consistency with other QE commands). **Must match the engine used for submit.**

### `aeolus query-editor query cancel`

```bash
bytedcli aeolus query-editor query cancel [options]
```

**Required:** `--task-id`

**Options:** `-r/--region`, **`--engine`** (and optional `--cluster-name`, `--ch-region`, `--datasource-id`, `--datasource-type` for consistency with other QE commands). **Must match the engine used for submit**, otherwise the wrong `/hive/task/.../cancel` vs `/ch/task/.../cancel` vs `/datasource/task/.../cancel` path is used.

### `aeolus query-editor task rename`

Rename a Query Editor task record after it has been submitted. This mirrors the browser task rename action and calls `PUT /qe/v2/api/task/{taskId}/rename?id={taskId}&name={name}` with an empty JSON body. Use it after `query run` when several related SQL variants share the same file/folder and the default task name is not descriptive enough.

```bash
bytedcli aeolus query-editor task rename --task-id <taskId> --name "sample-task-name"
```

**Required:** `--task-id`, `--name`

**Options:** `-r/--region`

### `aeolus query-editor task delete`

Delete one or more Query Editor task records. The command mirrors the browser bulk-delete action and calls `DELETE /qe/v2/api/task/batch?task_ids=...`. Default mode is dry-run; pass `--yes` only after confirming the task IDs. Before deleting a task that may be referenced later, record `query status` fields such as `runtime_info.application_id`, `runtime_info.execute_id`, `runtime_info.tracking_url_list`, `query_id`, and the SQL, because the Query Editor task record/status path returns `ResourceDeletedException` after deletion while lower-level Presto/TQS/Spark history is only reachable through those recorded identifiers.

```bash
bytedcli aeolus query-editor task delete --task-id <taskId>
bytedcli aeolus query-editor task delete --task-id <taskId> --yes
bytedcli aeolus query-editor task delete --task-id <taskIdA> --task-id <taskIdB> --yes
```

**Required:** `--task-id` (repeatable; comma-separated values are also accepted)

**Options:** `-r/--region`, `--dry-run`, `--yes`

### `aeolus query-editor query one`

Creates a temp folder + file, writes SQL, then runs `query run`. It waits for completion by default; `--no-wait` returns after submission.

**SQL input (required):** `--sql` or `--file` (`--file` takes precedence when both are provided)

**Options:** `-r/--region`, `--folder`, `--name`, `--queue` (**Hive required**), `--idc`, `--no-wait`, `--timeout`, `--rows`, **`--adhoc-date`**, **`--batch-start-date`**, **`--batch-end-date`**, **`--batch-concurrency`**, plus **`--engine`**, **`--cluster-name`**, **`--ch-region`**, **`--datasource-id`**, **`--datasource-type`**, **`--datasource-name`** (forwarded to the internal `query run`).

`query one` accepts the same `--sql` / `--file` SQL inputs and Hive date placeholder controls as `query run`, but auto-resolves/creates a temp folder and file first, so callers do not need explicit `--file-id` / `--folder-id`:

```bash
bytedcli aeolus query-editor query one --queue root.demo_queue \
  --sql "SELECT id FROM demo_db.sample_table WHERE date = '\${date}'" \
  --batch-start-date 2026-08-06 --batch-end-date 2026-08-12 --batch-concurrency 7

bytedcli aeolus query-editor query one --queue root.demo_queue --file ./queries/demo.sql
```

Both `query run` and `query one` now show the resolved region as `input -> normalized` in text mode, and include `inputRegion` / `normalizedRegion` in JSON output. Errors also carry the normalized region in `error.details`.

### ClickHouse example (align with browser QE)

```bash
export QE_APP_ID=<appIdFromQueryEditorUrl>
# Often for VA/SG on TikTok row:
# export BYTEDCLI_CLOUD_SITE=i18n-tt

bytedcli aeolus query-editor query run -r va --engine ch \
  --queue <cluster_name> \
  --folder-id <folderId> --file-id <fileId> \
  --file ./query.sql

bytedcli aeolus query-editor query status -r va --engine ch \
  --task-id <taskId> --file-id <fileId> --folder-id <folderId>

bytedcli aeolus query-editor query cancel -r va --engine ch \
  --task-id <taskId>
```

### Custom datasource example (user-defined DORIS etc.)

List your custom datasources, then submit SQL against one — either by `--datasource-name` (resolved to id+type) or directly by `datasource_id` + `datasource_type`:

> **Custom datasources are appId-scoped.** `aeolus query-editor datasources` only lists a user-defined source (and `--datasource-name` only resolves it) when `QE_APP_ID` equals the Query Editor workspace appId that owns the source. The appId is the `appId=` in the Query Editor page URL (`.../queryEditor/files/<fileId>?appId=<appId>`). There is currently no CLI command to enumerate your appIds; read it from that URL. Submitting by explicit `--datasource-id` does not require the right appId.

```bash
# 1) List your datasources (custom sources show name + owner). Set QE_APP_ID first.
export QE_APP_ID=<yourWorkspaceAppId>
bytedcli aeolus query-editor datasources -r cn

# 2a) One-shot query by NAME (no --queue needed; needs QE_APP_ID set as above)
bytedcli aeolus query-editor query one -r cn --engine datasource \
  --datasource-name <datasourceName> \
  --sql "select * from sample_db.sample_tbl limit 10"

# 2b) Or identify the source directly by id+type (works without the workspace appId)
bytedcli aeolus query-editor query one -r cn --engine datasource \
  --datasource-id <datasourceId> --datasource-type DORIS \
  --sql "select * from sample_db.sample_tbl limit 10"

# Explicit run/status flow (status must reuse --engine datasource)
bytedcli aeolus query-editor query run -r cn --engine datasource \
  --datasource-name <datasourceName> \
  --folder-id <folderId> --file-id <fileId> \
  --sql "select * from sample_db.sample_tbl limit 10"
bytedcli aeolus query-editor query status -r cn --engine datasource \
  --task-id <taskId> --file-id <fileId> --folder-id <folderId>
```

Other `query-editor` subcommands (`login`, `whoami`, `queues`, `datasources`, `folder`, `file`, `tmp-table`, `template`) are unchanged by `--engine`; only **`query parse` / `run` / `status` / `logs` / `cancel` / `one`** accept engine flags.

### `aeolus query-editor template`

Browse templates saved in Query Editor. These are separate from Shuttle project templates:

```bash
# List templates under a folder/node (defaults: --parent-id 0, --department public)
bytedcli aeolus query-editor template list -r cn
bytedcli aeolus query-editor template list -r cn --parent-id <nodeId> --department public
# Paginate (defaults: --page 1, --page-size 20)
bytedcli aeolus query-editor template list -r cn --page 2 --page-size 50

# Get a template's SQL by its template_id (from list output)
bytedcli aeolus query-editor template get -r cn --template-id <templateId>
```

- `template list` → `POST /qe/v2/api/template/templateNodeList`; the response is a bare JSON array of nodes (`id`, `template_id`, `parent_id`, `name`, `node_type`, `department`, `owner`, …). Since the backend returns no total count, the output exposes `page`/`page_size`/`current_count`/`has_more` (a full page implies more may exist) instead of a faked `total`.
- `template get` → `GET /qe/v2/api/template/selectQuery/<template-id>`; the `query` field holds the SQL.

### `aeolus query-editor login`

Compliance Aeolus QE product session (`euttp`, `usttpusts` only). For `euttp`, use this only when the primary EU-scoped Titan Passport path still fails. For `usttpusts`, use this login path or an injected browser session. Login defaults to `--mode password`: prompts SSO username/password/OTP in the terminal and signs in over HTTP (no browser window — works over SSH / headless hosts). Use `--mode browser` to open a temporary browser window on the compliance host instead. On success the cookies are merged into the SSO jar; on failure retry with the other mode.

```bash
bytedcli --site eu-ttp aeolus query-editor login
bytedcli --site us-ttp-usts aeolus query-editor login
# Force the temporary-browser flow:
bytedcli --site eu-ttp aeolus query-editor login --mode browser
# After a trusted runtime injects BYTEDCLI_AEOLUS_COOKIE:
bytedcli aeolus query-editor whoami -r usttpusts
```

When browser/CDP cookie extraction is unavailable, a human or managed secret store may inject the complete Cookie request-header value through `BYTEDCLI_AEOLUS_COOKIE` (without the `Cookie:` prefix). The variable has priority over the local `usttpusts` session jar, is accepted only for the built-in `usttpusts` HTTPS origin, is verified through `/qe/v2/api/user`, and is never persisted; other regions ignore it. A malformed, expired, or rejected value fails closed without falling back to local credentials. Agents must not request, paste, echo, log, or place the Cookie in argv, scripts, docs, or repositories. In a trusted interactive shell outside the Agent conversation, use a hidden `read -rs BYTEDCLI_AEOLUS_COOKIE`, export it, run the command, then unset it.

---

## Resource Types

| Type        | Description      |
| ----------- | ---------------- |
| `dashboard` | Aeolus dashboard |
| `data_set`  | Aeolus dataset   |

## Regions

Default OpenAPI / QE **hostnames** (see `src/api/aeolus/site.ts`). Developer console URLs may differ; use the console link for your tenant when creating ClientID/Secret.

| Region      | Description            | Default API host                                                                             |
| ----------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| `cn`        | China                  | `https://data.bytedance.net`                                                                 |
| `sg`        | Singapore (TikTok row) | `https://aeolus-sg.tiktok-row.net`                                                           |
| `va`        | US East (TikTok row)   | `https://aeolus-va.tiktok-row.net`                                                           |
| `euttp`     | EU-TTP / EU Compliance | `https://aeolus-eu-ttp.tiktok-eu.net` (office); `https://aeolus-eu-ttp.bytedance.net` (prod) |
| `euttp2`    | EU-TTP2 / NO1A         | `https://aeolus-no.tiktok-eu.net` (aliases `eu-ttp2` / `no1a`)                               |
| `eupipo`    | EU PIPO / IE2          | `https://aeolus-clover-pipo.tiktok-eu.net`                                                   |
| `mycis`     | MYCIS                  | `https://aeolus-mycis.byteintl.net`                                                          |
| `jplark`    | Japan Lark             | `https://aeolus-jp-lark.bytedance.net`                                                       |
| `mybd`      | MYBD                   | `https://aeolus-mybd.sinf.net`                                                               |
| `sglark`    | Singapore Lark         | `https://aeolus-sglark.bytedance.net`                                                        |
| `uspipo`    | US PIPO                | `https://aeolus-uspipo.byteintl.net`                                                         |
| `usttpusts` | US TTP USTS            | `https://aeolus-tx.tiktok-usts.net`                                                          |
| `usbd`      | US ByteDance           | `https://aeolus-usbd.byteintl.net`                                                           |

Note: Aeolus `jplark` uses the CN ByteCloud session because its host is under `bytedance.net`; Coral/Hive/Manta `jplark` use the DataLeap `i18n-bd` session on `dataleap-jp.byteintl.net`.
Note: `mycis`, `jplark`, and `uspipo` may require Aeolus product-side cookie bootstrap even after Titan Passport exchange; run `bytedcli --site i18n-bd auth login --session --auto --yes` for `mycis` / `uspipo`, and `bytedcli --site cn auth login --session --auto --yes` for `jplark` if product login is missing.
Note: `eupipo` uses `--site eu-ttp`, the Clover/PIPO host, and the host-specific `do-pipo.tiktok-eu.net` Titan issuer. If product login is missing, run `bytedcli --site eu-ttp auth login --session --auto --yes` once.

## Authentication

Aeolus uses ClientID/ClientSecret authentication.

### ClientID/ClientSecret

1. Visit the Aeolus Developer Console to get your credentials:
   - **CN**: https://data.bytedance.net/aeolus/pages/developer/console/certification
   - **SG**: https://aeolus-sg.tiktok-row.net/pages/developer/console/certification (tenant-specific; may also use `aeolus-sg.bytedance.net` for some accounts)
   - **VA**: https://aeolus-va.tiktok-row.net/pages/developer/console/certification
   - **EU-TTP (`euttp`)**: https://aeolus-eu-ttp.tiktok-eu.net/pages/developer/console/certification
   - **EU PIPO (`eupipo`)**: https://aeolus-clover-pipo.tiktok-eu.net/pages/developer/console/certification
   - **MYCIS**: https://aeolus-mycis.byteintl.net/#/developer/console/certification
   - **SGLARK**: https://aeolus-sglark.bytedance.net/pages/developer/console/certification
   - **USTTPUSTS**: https://aeolus-tx.tiktok-usts.net/pages/developer/console/certification

2. Configure in `.aeolus.env` file (choose one location):
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
BYTEDCLI_AEOLUS_MYCIS_CLIENT_ID=your_mycis_client_id
BYTEDCLI_AEOLUS_MYCIS_CLIENT_SECRET=your_mycis_client_secret
BYTEDCLI_AEOLUS_MYBD_CLIENT_ID=your_mybd_client_id
BYTEDCLI_AEOLUS_MYBD_CLIENT_SECRET=your_mybd_client_secret
BYTEDCLI_AEOLUS_SGLARK_CLIENT_ID=your_sglark_client_id
BYTEDCLI_AEOLUS_SGLARK_CLIENT_SECRET=your_sglark_client_secret
BYTEDCLI_AEOLUS_USTTPUSTS_CLIENT_ID=your_usttpusts_client_id
BYTEDCLI_AEOLUS_USTTPUSTS_CLIENT_SECRET=your_usttpusts_client_secret
```

## Shuttle (task submit)

Before using Shuttle for TTP, DECC, `detection_uv`, or cross-region compliant data, read [`shuttle.md`](shuttle.md). It explains Shuttle's compliance-platform role and the policy boundaries that command syntax alone cannot capture.

Shuttle has one control plane under `https://aeolus-va.tiktok-row.net/shuttle/web/api/v1/` on the office network. Use `-r va` regardless of the task data location. The task data region is a separate `template.infos` key such as `US`, `EU`, `EU-TTP`, or `EU-TTP2`, selected with `--shuttle-region`; YARN cluster/queue must come from the same key in `queue get`.

`aeolus shuttle task submit` resolves template SQL placeholders in both `${name}` and `{{name}}` forms. Repeatable `--var key=value` overrides template parameter defaults; the submit request carries the merged `params` list expected by Shuttle. For BATCH date ranges, `${date}` / `${date-N}` and `{{date}}` / `{{date-N}}` remain in SQL so Shuttle can expand each child day. Without a caller-supplied range, the CLI expands the reserved date placeholders for a single execution.

Submit and ad-hoc flows inherit `taskType`, `dataSource`, and `engine` from the source template detail (including ClickHouse templates). Using `--query` or `--query-file` creates a temporary template that copies the same fields from `--template-id` instead of defaulting to Hive, and the transient template stays hidden from the project’s "我的模板" sidebar (it submits with `templateSource: "adhoc"` rather than `origin`). The custom SQL must still produce columns that match the source template’s DECC compliance schema; mismatches surface as a misleading `invalidTemplateSnapshotException: failed to parse the template sql`, even though the SQL itself is parseable.

`task submit` rejects `--start-date` / `--end-date` when the source template is an ADHOC base. ADHOC templates are single-day; use a BATCH base template to submit a range. The same rule applies when ad-hoc SQL is submitted via `--query` / `--query-file` against an ADHOC `--template-id`.

Hive task submit requires both `--yarn-cluster` and `--yarn-queue`. Run `aeolus shuttle queue get -r va --project-id <id>`, select the target region from the returned `queues` object, and pass both values from that same region. If a template has multiple `infos` keys, `--shuttle-region` is required; with one key, the CLI infers it safely.

`template get` normalizes template `params` whether the API returns `name` / `defaultValue` or `key` / `value`. `template create` requires either `--clone-template-id` or `--decc-schema-id` together with `--decc-region`; the CLI rejects an empty DECC binding before the backend can return a misleading NPE. When `--clone-template-id` points at an ADHOC base, dates are not needed; the clone also copies the source’s `deccSchemaId` / `taskType` / `dataSource` / `engine` and DECC `infos`.

`template search` requires `--project-id`; without it the upstream search endpoint rejects the request, so the CLI raises a clear error before sending.

## Shuttle (task download)

Shuttle lives under `aeolus shuttle`. To save the **full** query result as Excel or CSV (not only the preview rows from `task result`), use:

```bash
bytedcli aeolus shuttle task download [options]
```

**Options:**

- `-r, --region <region>` — Shuttle control-plane region; only `va` is supported and it is the default
- `--task-id <taskId>` — Shuttle task id; required
- `--shuttle-region <code>` — HTTP query `region=…`; must match a key under `infos` in `aeolus shuttle task get` for the geography you queried (e.g. EU vs US/TTP row — do not mix; exact spelling is backend-defined). **This is not** the same as `-r/--region`.
- `-o, --output <path>` — Local output path; required
- `--fmt <fmt>` — `excel` or `csv` (default: `excel`)
- `--sub-task` — Request sub-task export (boolean flag)
- `--timeout-ms <ms>` — HTTP read timeout for the download (default **180000** ms)

**Examples:**

```bash
bytedcli aeolus shuttle task download -r va --task-id 123456 --shuttle-region US --fmt excel -o ./demo-export.xlsx
bytedcli aeolus shuttle task download -r va --task-id 123456 --shuttle-region EU --fmt csv -o ./demo-export.csv --timeout-ms 240000
bytedcli aeolus shuttle task download -r va --task-id 123456 --shuttle-region EU-TTP --fmt csv -o ./demo-export.csv --timeout-ms 240000
```

**Behavior:** Some environments return raw bytes; others return the Shuttle JSON envelope where `data` is an `https://` object URL. bytedcli follows at most five redirects, validates every hop, and rejects any `http://` target to keep compliance results and presigned credentials encrypted in transit. Aeolus auth headers are recalculated per hop and sent **only when the current file URL has the exact same HTTPS origin** (scheme, hostname, and port) as the Shuttle API; external presigned URLs and same-host URLs on a different HTTPS port are fetched without Aeolus cookies/tokens.

## Shuttle (template + folder organisation)

The same project also exposes template- and folder-level operations so saved SQL can be organised under the "我的模板" sidebar. Templates and folders share the same node tree, so the commands come in matching pairs.

Template-level:

```bash
bytedcli aeolus shuttle template move   -r va --project-id <id> --template-id <id> --target-folder-id <folderId>
bytedcli aeolus shuttle template delete -r va --template-id <id> [--project-id <id>]
```

Folder-level (all `folder` subcommands require `--project-id`):

```bash
bytedcli aeolus shuttle folder tree   -r va --project-id <id>
bytedcli aeolus shuttle folder list   -r va --project-id <id> [--folder-id <id>] [--keyword <kw>] [--creator <u>] [--only-favored] [--page <n>] [--per-page <n>]
bytedcli aeolus shuttle folder create -r va --project-id <id> --name <name> [--parent-id <id>]
bytedcli aeolus shuttle folder rename -r va --project-id <id> --folder-id <id> --name <new-name>
bytedcli aeolus shuttle folder move   -r va --project-id <id> --folder-id <id> [--target-parent-id <id>]
bytedcli aeolus shuttle folder delete -r va --project-id <id> --folder-id <id>
```

`folder list` returns the immediate contents under the given parent (sub-folders + that folder’s templates); `folder tree` returns the entire project tree in one call.

The project root is expressed either by omitting the target-id flag or by passing `0` to `--target-folder-id` / `--target-parent-id` — the CLI translates `0` to the `null` parent the backend actually expects. (Hitting the Shuttle API directly with `0` returns `Directory Node 0 does not exist`.)

`folder delete` only succeeds when the folder is empty, and emptiness is tracked separately from `folder list`: deleting a template via `DELETE /template/{id}` does **not** decrement the parent folder’s child count, so a later `folder delete` would refuse with `Cannot delete directory as it is not empty` even though `folder list` returns zero items. The CLI works around this by detaching the template from its parent first when `template delete --project-id <id>` is supplied. Always pass `--project-id` when deleting a template that lives in a folder.

Pick the right action by what you’re moving: `template move --target-folder-id` reparents a single template, `folder move --target-parent-id` reparents the entire sub-tree.

**No template rename.** Shuttle has no public rename endpoint for templates — `PUT/POST/PATCH /template/{id}` all return 405, the directory-node endpoint rejects template ids, and the Shuttle UI only exposes Move / Save to on templates. The CLI therefore has no `template rename` subcommand. To rename a template, run `template create` with the desired name (clone the original via `--clone-template-id` to preserve DECC), then `template delete --project-id <id>` the old one.

There is no single `save` subcommand and `template create` does not accept a target folder. To save SQL with a chosen name into a specific folder, run `template create --name <name> --query-file <path> --clone-template-id <id>` (plus dates when the base is BATCH), then `template move --target-folder-id <folderId>`; reuse an existing folder id from `folder tree`, or run `folder create` first.

---

## JSON Output

Use `--json` flag for structured output:

```bash
bytedcli --json aeolus list-authorized -r va
```

Output structure:

```json
{
  "status": "success",
  "data": {
    "resources": [...],
    "total": 100,
    "region": "va"
  },
  "context": {
    "execution_time_ms": 500,
    "timestamp": "2026-03-10T10:00:00.000Z"
  }
}
```
