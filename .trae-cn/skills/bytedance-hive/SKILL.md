---
name: bytedance-hive
description: "Search, explore, create, and modify Hive/Clickhouse/Doris data assets via bytedcli: search databases and tables, get detailed schema information with columns, locate producer Dorado task IDs, view entity lineage, create new Hive tables or Doris tables through `hive create`, and modify table field definitions. Use when tasks mention Hive, DataLeap, data catalog, table schema, column metadata, Dorado producer tasks, data lineage, creating tables, or modifying table fields."
---

# bytedcli Hive (DataLeap Data Catalog)

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

- Search for Hive databases and tables in DataLeap
- Get detailed table/database information including schema and columns
- Locate upstream producer Dorado task IDs from a Hive table or entity
- Check partition row counts and top partitions for Hive tables
- View data lineage relationships
- Explore Clickhouse and Doris data assets
- Create new Hive tables with fields, partition keys, TTL, and storage settings
- Create Doris tables through `hive create --type DorisTable` using raw DDL plus namespace metadata
- Modify table field definitions (column names, types, comments, security labels)
- Update Hive table alias / description / business metadata / project binding / TTL through `hive table update`
- List Coral projects available for Hive table binding

## 前置条件

- 使用通用调用方式：`references/invocation.md`
- 在 ByteDance 生产网环境下调用 sg region 前，`export BYTEDCLI_NETWORK_PROFILE=prod`。

> 执行前缀见 `references/invocation.md`；下面示例直接写 `bytedcli`。

## Search Asset Types

`hive search --type` filters by DataLeap / Coral asset `typeName`.

| Type                       | Description             |
| -------------------------- | ----------------------- |
| `HiveTable`                | Hive tables             |
| `ClickhouseTable`          | Clickhouse tables       |
| `BmqTopic`                 | BMQ topics              |
| `RocketmqTopic`            | RocketMQ topics         |
| `DorisTable`               | Doris tables            |
| `ABaseLogicalTable`        | ABase logical tables    |
| `AeolusDashboard`          | Aeolus dashboards       |
| `AeolusDataset`            | Aeolus datasets         |
| `MySQLTable`               | MySQL tables            |
| `FlinkLogicalTable`        | Flink logical tables    |
| `EsIndex`                  | Elasticsearch indexes   |
| `NuwaNgMetric`             | Nuwa metrics            |
| `NuwaNgDimension`          | Nuwa dimensions         |
| `NuwaApplication`          | Nuwa applications       |
| `BPPortal`                 | BP portals              |
| `GalleryMetricGroup`       | Gallery metric groups   |
| `DataPowerDataset`         | DataPower datasets      |
| `DataPowerDashboard`       | DataPower dashboards    |
| `Api`                      | APIs                    |
| `LogicalTable`             | Logical tables          |
| `HiveDB`                   | Hive databases          |
| `ClickhouseDB`             | Clickhouse databases    |
| `NuwaNgTheme`              | Nuwa themes             |
| `AeolusDashboardReportV2`  | Aeolus dashboard reports |
| `ByteIOEvent`              | ByteIO events           |
| `Term`                     | Terms                   |
| `AeolusMetadataMetric`     | Aeolus metadata metrics |
| `GaiaPortalSite`           | Gaia portal sites       |
| `DataAlbum`                | Data albums             |
| `AssetAlbum`               | Asset albums            |
| `DataTopics`               | Data topics             |

## Supported Regions

| Region                   | Description      | Endpoint / notes                                                                        |
| ------------------------ | ---------------- | --------------------------------------------------------------------------------------- |
| `cn`                     | China (default)  | data.bytedance.net                                                                      |
| `sg`                     | Singapore ROW    | dataleap-sg.tiktok-row.net                                                              |
| `gcp` / `eu`             | GCP / US-EastRed | API `dataleap.tiktok-eu.net` (cid=5); console `dataleap-gcp.tiktok-row.net`             |
| `eu-compliance2` / `ie2` | IE2              | API `dataleap-gp-ttp-eu.tiktok-eu.net` (cid=31); console `dataleap-ie2…`; auth `eu-ttp` |
| `va`                     | us-east, maliva  | dataleap-va.tiktok-row.net                                                              |
| `mycis`                  | MYCIS            | dataleap-mycis.example.net                                                              |
| `mybd`                   | MYBD             | dataleap-mybd.example.net                                                               |

## Quick start

```bash
# Search for Hive databases
bytedcli hive search --query "my_database" --type HiveDB --region cn

# Search for Hive tables
bytedcli hive search --query "user" --type HiveTable --region gcp

# Get database details
bytedcli hive detail my_database --region cn

# Get table details with full schema and producer Dorado task IDs
bytedcli hive detail my_database my_table --region gcp

# Get Doris table details when the Doris namespace / cluster is known
bytedcli hive detail my_database my_doris_table --type DorisTable --namespace doris_demo_cn --region cn

# Get entity details by GUID (from search results)
bytedcli hive get <guid> --region cn

# Get partition row counts for a table (shows total rows and top 20 partitions)
bytedcli hive rows my_database my_table --region cn

# View data lineage
bytedcli hive lineage <guid> --region cn --depth 3

# Modify table fields (columns) by GUID
bytedcli hive modify field --guid <guid> --fields '[{"typeName":"HiveColumn","name":"col1","dataType":"string","comment":"description"}]' --region cn

# Prefer database/table on IE2 (eu-compliance2); aliases: ie2, eucompliance2.
# Do not pass --partition-keys to modify field: partition keys are immutable here.
bytedcli hive modify field --database demo_db --table demo_table --fields '[{"typeName":"HiveColumn","name":"col1","dataType":"string","comment":"description"}]' --region ie2

# Update table-level attributes through the aggregated entry point
bytedcli hive table update --database demo_db --table demo_table --alias "demo alias" --description "demo description" --business-line demo-line --data-layer demo-layer --data-category demo-category --storage-strategy demo-strategy --ttl 7 --region cn

# List Coral projects that can be bound to a Hive table
bytedcli hive project list --region cn --keyword demo

# Create a new Hive table (fields + partition keys explicit)
bytedcli hive create \
  --database demo_db \
  --table demo_table \
  --ttl 365 \
  --fields '[{"name":"psm","dataType":"string","comment":"service name"},{"name":"qps","dataType":"double","comment":"qps"}]' \
  --partition-keys '[{"name":"date","dataType":"string","comment":"date"}]' \
  --region cn

# IE2 (eu-compliance2): auth with --site eu-ttp; owner + business contact match console form
bytedcli --site eu-ttp auth login
bytedcli hive create \
  --database demo_db \
  --table demo_table \
  --ttl 30 \
  --fields '[{"name":"data","dataType":"string","comment":"data"}]' \
  --partition-keys '[{"name":"date","dataType":"string","comment":"date"}]' \
  --owner demo.owner \
  --business-contact demo.contact \
  -r ie2

# GCP / US-EastRed: same slim create form; auth site i18n-tt (do not use -r ie2)
bytedcli hive create \
  --database demo_db \
  --table demo_table \
  --ttl 30 \
  --fields '[{"name":"test","dataType":"string","comment":"test"}]' \
  --partition-keys '[{"name":"date","dataType":"string","comment":"date"}]' \
  --owner demo.owner \
  --business-contact demo.contact \
  -r gcp

# Create a new Hive table from DDL (fields and partition keys parsed automatically)
bytedcli hive create \
  --database demo_db \
  --table demo_table \
  --ttl 365 \
  --ddl "CREATE TABLE IF NOT EXISTS \`demo_db\`.\`demo_table\` (\`psm\` string COMMENT 'psm') PARTITIONED BY (\`date\` string COMMENT 'date')" \
  --region cn

# Create a new Doris table from raw DDL
bytedcli hive create \
  --database demo_db \
  --table demo_doris_table \
  --type DorisTable \
  --namespace doris_demo_cn \
  --alias "demo table" \
  --ddl "$(cat /tmp/demo_doris.sql)" \
  --region cn
```

## Notes

- Use `--json` for structured JSON output
- Default region is `cn` if not specified
- Default asset type for search is `HiveDB`
- `hive detail --type` is intentionally narrower than `hive search --type`; detail supports `HiveDB`, `HiveTable`, `ClickhouseDB`, `ClickhouseTable`, and `DorisTable`.
- The `detail` and `get` commands show full schema including column names, types, comments, and producer Dorado task IDs when upstream lineage contains `DoradoTask`.
- `hive detail <db> <table>` defaults to `HiveTable`. If the Hive asset is missing, the CLI searches exact `ClickhouseTable` / `DorisTable` candidates for the same database and table name, auto-uses a unique match, and reports retry commands when multiple non-Hive assets match.
- For exact Doris metadata lookup, pass `--type DorisTable --namespace <doris_namespace>`. Doris qualified names use `DorisTable:///{namespace}/{database}/{table}@{cid}`, so type alone is not always enough to build the exact lookup path.
- The `rows` command shows the total row count and the top 20 partitions by row count
- Lineage shows upstream and downstream data dependencies
- The `modify field` command updates field definitions; pass `--guid` or `--database` + `--table`, and use `--fields` for the full non-partition column array as JSON. Each item must use `typeName: "HiveColumn"` and `dataType` (not `type`). Do not pass `--partition-keys`: the Hive fields endpoint does not support partition-key mutation, and malformed partition-key objects can clear the table's partition definition. Get the current fields first via `hive detail <db> <table>` (preferred on IE2 / `eu-compliance2`, where `hive get <guid>` may hit OG schema 403 on `/entities/{guid}`), then submit the updated array. For IE2 auth use `bytedcli --site eu-ttp auth login`; region aliases include `ie2` / `eucompliance2`. GCP (`-r gcp`) is US-EastRed on `dataleap.tiktok-eu.net` (cid=5), not IE2 — do not reuse `-r ie2` for GCP console tables. `--business-contact` applies on IE2 and GCP create only.
- Use `hive table update` for table-level metadata updates.
- `hive table update` does not use empty strings to clear text fields. `--alias`, `--description`, and `--project` must be non-empty when provided. For `--data-category`, empty or whitespace-only entries are ignored rather than treated as clear.
- Use `hive project list` before `hive table update --project <name>` when you need to discover the exact Coral project name in the current region.
- The `create` command requires `--database` and `--table`; `--ttl` is required for `HiveTable` but not for `DorisTable`.
- For `HiveTable`, fields/partition-keys can be provided via `--fields`/`--partition-keys` (JSON arrays) or derived automatically from `--ddl`. When `--ddl` is provided, `--fields` and `--partition-keys` become optional (parsed from DDL), but can still be passed to override.
- For `DorisTable`, use `--type DorisTable --namespace <name> --ddl <sql>`. Doris creation submits the raw DDL directly and does not use Hive field parsing or the Hive explain endpoint.
- When passing Doris DDL that contains backticks or multiple lines, prefer loading it from a file, e.g. `--ddl "$(cat /tmp/demo_doris.sql)"`, to avoid shell command substitution corrupting the SQL.
- Owner defaults to the current SSO user.
- Before submitting a `HiveTable`, `create` performs two layers of validation: (1) local checks — non-empty fields, no duplicate names within fields/partition-keys, and no overlapping names between fields and partition-keys; (2) server-side DDL validation via `POST /bridge/hive/explain` — catches SQL syntax and semantic errors (e.g. duplicate column names) before the actual create request is sent.

## References

- `references/hive.md`
- `references/invocation.md`
