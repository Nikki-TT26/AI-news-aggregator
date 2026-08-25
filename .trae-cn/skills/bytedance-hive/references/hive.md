# Hive (DataLeap Data Catalog) CLI Reference

The Hive CLI provides commands to search and explore data assets in the DataLeap data catalog, including Hive, Clickhouse, and Doris databases and tables.

## Commands

### search

Search for databases and tables in DataLeap.

```bash
bytedcli hive search [options]
```

**Options:**

- `--query <query>` - Search query (required)
- `-t, --type <type>` - DataLeap / Coral asset typeName. See [Asset Types](#asset-types) for the full list. (default: "HiveDB")
- `-r, --region <region>` - Region (built-in: cn, sg, gcp, va, mycis, sglark, jplark, uspipo, mybd, us-ttp, eu-ttp2, eu-compliance2, eu-ttp) (default: "cn")
- `-p, --page <page>` - Page number (default: 1)
- `--size <size>` - Page size (default: 20)

**Examples:**

```bash
# Search for Hive databases
bytedcli hive search --query "privacy" --type HiveDB --region gcp

# Search for Hive tables with pagination
bytedcli hive search --query "user" --type HiveTable --region cn --page 1 --size 50

# Search for Clickhouse tables
bytedcli hive search --query "events" --type ClickhouseTable --region sg
```

**Output:**

- Name, Type, Description, Owner, Environment, Location
- For table searches: preview of columns for first matching table

---

### detail

Get detailed database or table information including full schema and producer Dorado task IDs.

```bash
bytedcli hive detail [database] [table] [options]
```

**Arguments:**

- `database` - Database name (required)
- `table` - Table name (optional, omit for database details)

**Options:**

- `-r, --region <region>` - Region (built-in: cn, sg, gcp, va, mycis, sglark, jplark, uspipo, mybd, us-ttp, eu-ttp2, eu-compliance2, eu-ttp) (default: "cn")
- `-t, --type <type>` - Detail asset type (HiveDB, HiveTable, ClickhouseDB, ClickhouseTable, DorisTable)
- `--namespace <name>` - Doris namespace / cluster for exact DorisTable lookup

**Examples:**

```bash
# Get database details
bytedcli hive detail my_database --region gcp

# Get table details with full schema and producer Dorado task IDs
bytedcli hive detail my_database my_table --region gcp

# Get Doris table details when the Doris namespace / cluster is known
bytedcli hive detail my_database my_doris_table --type DorisTable --namespace doris_demo_cn --region cn

# Get Clickhouse database details
bytedcli hive detail clickhouse_db --type ClickhouseDB --region cn
```

`hive detail <db> <table>` defaults to `HiveTable`. If the Hive asset is missing, the CLI searches exact `ClickhouseTable` / `DorisTable` candidates for the same database and table name, auto-uses a unique match, and reports retry commands when multiple non-Hive assets match. For exact Doris metadata lookup, pass `--type DorisTable --namespace <doris_namespace>` because Doris qualified names include the namespace segment.

**Output:**

- GUID, Type, Name, Qualified Name, Description
- Parent DB, DB Type, Environment, Location
- Table Type, Latest Partition (for tables)
- Producer Dorado Task IDs (when upstream lineage exposes `DoradoTask`)
- **Columns**: Name, Type, Comment (for tables)
- **Partition Keys**: Name, Type, Comment (for tables)

---

### get

Get entity details by GUID with full schema information and producer Dorado task IDs.

```bash
bytedcli hive get [guid] [options]
```

**Arguments:**

- `guid` - Entity GUID from search results (required)

**Options:**

- `-r, --region <region>` - Region (built-in: cn, sg, gcp, va, mycis, sglark, jplark, uspipo, mybd, us-ttp, eu-ttp2, eu-compliance2, eu-ttp) (default: "cn")

**Examples:**

```bash
# Get table details by GUID
bytedcli hive get d57dbbcc-bf37-497c-9d2d-63b71b68a91e --region gcp

# Get database details by GUID
bytedcli hive get 42a2ae28-1d37-44fe-8cab-dc910b73361e --region gcp
```

**Output:**

- Entity Details (GUID, Type, Name, Qualified Name)
- Full schema including columns and partition keys
- Producer Dorado Task IDs (when upstream lineage exposes `DoradoTask`)

---

### rows

Get partition row counts for a Hive table.

```bash
bytedcli hive rows [database] [table] [options]
```

**Arguments:**

- `database` - Database name (required)
- `table` - Table name (required)

**Options:**

- `-r, --region <region>` - Region (built-in: cn, sg, gcp, va, mycis, sglark, jplark, uspipo, mybd, us-ttp, eu-ttp2, eu-compliance2, eu-ttp) (default: "cn")

**Examples:**

```bash
# Get partition row counts for a table in CN region
bytedcli hive rows my_database my_table

# Get partition row counts for a table in SG region
bytedcli hive rows db1 table1 --region sg
```

**Output:**

- Database, Table, Region
- Total Rows (sum of all partitions)
- Partition Count
- Top 20 Partitions by Row Count (Partition Value, Rows)

---

### lineage

Get entity lineage showing upstream and downstream data dependencies.

```bash
bytedcli hive lineage [guid] [options]
```

**Arguments:**

- `guid` - Entity GUID (required)

**Options:**

- `-r, --region <region>` - Region (built-in: cn, sg, gcp, va, mycis, sglark, jplark, uspipo, mybd, us-ttp, eu-ttp2, eu-compliance2, eu-ttp) (default: "cn")
- `-d, --depth <depth>` - Lineage depth (default: 3)

**Examples:**

```bash
# Get lineage with default depth
bytedcli hive lineage d57dbbcc-bf37-497c-9d2d-63b71b68a91e --region gcp

# Get deeper lineage
bytedcli hive lineage d57dbbcc-bf37-497c-9d2d-63b71b68a91e --region gcp --depth 5
```

**Output:**

- Base entity GUIDs
- Related entities (Type, Name, GUID)
- Relations (From -> To)

---

### table update

Update table-level Hive metadata through the aggregated entry point.

```bash
bytedcli hive table update [options]
```

**Options:**

- `--guid <guid>` - Entity GUID of the table to update
- `--database <db>` - Database name; used with `--table` when `--guid` is omitted
- `--table <tbl>` - Table name; required when `--database` is used
- `--alias <value>` - Display alias to set; must be non-empty when provided
- `--description <value>` - Table description to set; must be non-empty when provided
- `--business-line <value>` - Business line metadata value
- `--data-layer <value>` - Data layer metadata value
- `--data-category <value>` - Data category metadata value; repeat for multiple. Empty or whitespace-only entries are ignored
- `--storage-strategy <value>` - Storage strategy metadata value
- `--project <name>` - Project name to bind; must be non-empty when provided
- `--ttl <days>` - TTL days
- `--ttl-column <col>` - TTL partition column, used together with `--ttl-pattern`
- `--ttl-pattern <pattern>` - TTL partition pattern, used together with `--ttl-column`
- `-r, --region <region>` - Region (default: `cn`)

**Examples:**

```bash
# Update alias / description together
bytedcli hive table update \
  --database demo_db \
  --table demo_tbl \
  --alias "demo alias" \
  --description "demo description" \
  --region cn

# Update business metadata and TTL in one call
bytedcli hive table update \
  --database demo_db \
  --table demo_tbl \
  --business-line demo-line \
  --data-layer demo-layer \
  --data-category demo-category \
  --storage-strategy demo-strategy \
  --ttl 7 \
  --ttl-column pdate \
  --ttl-pattern yyyyMMdd \
  --region cn
```

**Notes:**

- This is the Hive entry point for table-level metadata updates.
- Empty strings are not treated as clear for Hive text fields. `--alias`, `--description`, and `--project` must be non-empty when provided.
- Empty or whitespace-only `--data-category` values are ignored rather than treated as clear.

---

### project list

List Coral projects available for Hive table binding in the current region.

```bash
bytedcli hive project list [options]
```

**Options:**

- `--keyword <keyword>` - Filter projects by name keyword
- `-r, --region <region>` - Region (default: `cn`)

**Examples:**

```bash
bytedcli hive project list --region cn
bytedcli hive project list --region mycis --keyword demo
```

---

## Asset Types

| Type                       | Description              |
| -------------------------- | ------------------------ |
| `HiveTable`                | Hive table               |
| `ClickhouseTable`          | Clickhouse table         |
| `BmqTopic`                 | BMQ topic                |
| `RocketmqTopic`            | RocketMQ topic           |
| `DorisTable`               | Doris table              |
| `ABaseLogicalTable`        | ABase logical table      |
| `AeolusDashboard`          | Aeolus dashboard         |
| `AeolusDataset`            | Aeolus dataset           |
| `MySQLTable`               | MySQL table              |
| `FlinkLogicalTable`        | Flink logical table      |
| `EsIndex`                  | Elasticsearch index      |
| `NuwaNgMetric`             | Nuwa metric              |
| `NuwaNgDimension`          | Nuwa dimension           |
| `NuwaApplication`          | Nuwa application         |
| `BPPortal`                 | BP portal                |
| `GalleryMetricGroup`       | Gallery metric group     |
| `DataPowerDataset`         | DataPower dataset        |
| `DataPowerDashboard`       | DataPower dashboard      |
| `Api`                      | API                      |
| `LogicalTable`             | Logical table            |
| `HiveDB`                   | Hive database            |
| `ClickhouseDB`             | Clickhouse database      |
| `NuwaNgTheme`              | Nuwa theme               |
| `AeolusDashboardReportV2`  | Aeolus dashboard report  |
| `ByteIOEvent`              | ByteIO event             |
| `Term`                     | Term                     |
| `AeolusMetadataMetric`     | Aeolus metadata metric   |
| `GaiaPortalSite`           | Gaia portal site         |
| `DataAlbum`                | Data album               |
| `AssetAlbum`               | Asset album              |
| `DataTopics`               | Data topics              |

`hive detail --type` intentionally supports only the database/table detail subset:
`HiveDB`, `HiveTable`, `ClickhouseDB`, `ClickhouseTable`, and `DorisTable`.

## Regions

| Region           | Aliases              | CID | Endpoint                         |
| ---------------- | -------------------- | --- | -------------------------------- |
| `cn`             | china                | 0   | data.bytedance.net               |
| `sg`             | singapore, row       | 6   | dataleap-sg.tiktok-row.net       |
| `gcp`            | eu, texas            | 31  | dataleap-gp-ttp-eu.tiktok-eu.net |
| `va`             | us-east, maliva      | 1   | dataleap-va.tiktok-row.net       |
| `mycis`          |                      | 41  | dataleap-mycis.example.net       |
| `mybd`           |                      | 11  | dataleap-mybd.example.net        |
| `us-ttp`         | usttp, us-tx         | 9   | dataleap-tx.tiktok-usts.net      |
| `eu-ttp2`        | euttp2, eu-no        | 39  | dataleap-no1a.tiktok-eu.net      |
| `eu-compliance2` | eucompliance2, eu-c2 | 31  | dataleap-gp-ttp-eu.tiktok-eu.net |
| `eu-ttp`         | euttp, eu-ie         | 47  | dataleap-ttp-eu-ie.tiktok-eu.net |

For `gcp` and `us-ttp`, the CLI also configures a fallback `limitUrl` and
transparently retries the request against it if the primary host is
unreachable from the current network. No extra flag is needed.

`eu-ttp2`, `eu-compliance2`, and `eu-ttp` route through TTP-style gateways
that use a Dataleap-issued JWT (`x-dataleap-jwt-token`) instead of the
bytecloud `x-jwt-token`. The CLI handles this swap automatically; the only
prerequisite is the same bytecloud SSO session used by the other regions.
Note that `eu-compliance2` shares its host with `gcp`'s primary URL but
points at a different Hive cluster (cid=31, vregion=`eu-compliance2`).

## Qualified Name Format

The qualified name uniquely identifies an asset:

- **Database**: `{Type}:///{database}@{cid}`
  - Example: `HiveDB:///my_database@0`
- **Table**: `{Type}:///{database}/{table}@{cid}`
  - Example: `HiveTable:///my_database/my_table@31`
- **Doris table**: `DorisTable:///{namespace}/{database}/{table}@{cid}`
  - Example: `DorisTable:///doris_demo_cn/my_database/my_table@0`

## Common Column Types

| Type        | Description                |
| ----------- | -------------------------- |
| `string`    | String/text data           |
| `bigint`    | 64-bit integer             |
| `int`       | 32-bit integer             |
| `tinyint`   | 8-bit integer              |
| `boolean`   | True/false                 |
| `double`    | Double precision float     |
| `date`      | Date without time          |
| `timestamp` | Date with time             |
| `array<T>`  | Array of type T            |
| `map<K,V>`  | Map with key K and value V |

## Authentication

The CLI uses JWT authentication via SSO. Ensure you are logged in:

```bash
bytedcli auth login
```

## Create Tables

### Hive tables

Use `bytedcli hive create` with `--database`, `--table`, and `--ttl`. You can either:

- pass `--fields` and `--partition-keys` as JSON arrays, or
- pass `--ddl` and let the CLI parse Hive fields and partition keys automatically.

Before submitting a Hive table, the CLI runs local validation and server-side validation through `POST /bridge/hive/explain`.

### Doris tables

Use the same command with `--type DorisTable`:

```bash
bytedcli hive create \
  --database demo_db \
  --table demo_doris_table \
  --type DorisTable \
  --namespace doris_demo_cn \
  --alias "demo table" \
  --ddl "$(cat /tmp/demo_doris.sql)" \
  --region cn
```

Notes:

- `--namespace` is required for Doris tables.
- `--ddl` is required for Doris tables.
- `--ttl` is not required for Doris tables.
- Doris table creation submits the raw DDL directly to the create API.
- Doris table creation does not use Hive field parsing or the Hive explain endpoint.
- If the DDL contains backticks or multiple lines, prefer loading it from a file to avoid shell command substitution issues.
- `mybd` queries require a local `i18n-bd` browser session; run `bytedcli --site i18n-bd auth login --session` before calling `hive detail/get/lineage/rows/search --region mybd`.

## JSON Output

Use `--json` flag for structured output:

```bash
bytedcli --json hive search --query "test" --type HiveTable --region cn
```

Output structure:

```json
{
  "status": "success",
  "data": {
    "entities": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  },
  "context": {
    "execution_time_ms": 500,
    "timestamp": "2026-03-05T10:00:00.000Z"
  }
}
```
