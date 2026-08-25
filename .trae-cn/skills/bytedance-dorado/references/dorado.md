# Dorado (DataLeap) CLI Reference

Dorado is part of the DataLeap platform for data pipeline orchestration. This CLI provides commands to manage batch tasks, view instances, and update SQL queries.

Supported built-in regions: `cn`, `sg`, `sglark`, `jplark`, `uspipo` (alias `gp-us`), `va`, `mycis`, `gcp`/`eu`, `us-ttp` (alias `tx`), `us-ttp-internal` (US-TTP production-network only, API base `https://dataleap-tx.tiktokd.net/dorado_tx_api`), `us-eastred`, `eu-ttp2`, `eu-compliance2` (aliases `ie2`, `eu-ttp-gp`), `boe`, `boei18n`.

`sglark` / `jplark` / `uspipo` / `mycis` are built in and should be called directly with `--region`. If the target IDC/region is not covered by the built-in list, add a custom region in `~/.local/share/bytedcli/data/.dorado.env` or `./.dorado.env`. When `DORADO_REGION_<NAME>_SITE` is omitted, Dorado auth follows the global `--site` / `BYTEDCLI_CLOUD_SITE`.

Custom regions can be configured via `.dorado.env`:

```env
DORADO_REGION_PIPOUS_API_BASE_URL=https://dataleap-pipous.example.net/dorado_api
DORADO_REGION_PIPOUS_ALIASES=us_pipo,pipo-us,pipo_us,uspipo
DORADO_REGION_PIPOUS_GROUP_NAME=sample_group
DORADO_REGION_PIPOUS_PROJECT_PREFIX=sample_group
# Optional: only set this for Dataleap environments that require browser-session cookies
# DORADO_REGION_PIPOUS_AUTH=session
```

`DORADO_REGION_<NAME>_AUTH` supports `jwt|auto|session`. Built-in regions default to `jwt`, except `sglark`, `jplark`, `uspipo`, and `mycis`, which are built in as `session`; custom regions default to `auto`. Use `session` for known special Dataleap environments that require browser-session cookies in addition to JWT. Without `AUTH=session`, keep the normal JWT flow first and only switch to `bytedcli auth login --session` when the target region shows explicit web-auth signals, such as JSON output already including `error.hint` / `error.auth_command`, login redirects, or web-side auth failures.

Custom group-based Dataleap regions use `DORADO_REGION_<NAME>_GROUP_NAME` and `DORADO_REGION_<NAME>_PROJECT_PREFIX`; Dorado task-list referers then use `groupName=<group>` and `project=<projectPrefix>_<projectId>` to match web console routing.

When a user already provides an unknown custom region name, do not probe built-in regions as a fallback. Prefer configuring `DORADO_REGION_<NAME>_API_BASE_URL` in `.dorado.env`, and let the CLI return a direct configuration hint if the region is still unknown.

## Web URL formats

Dorado task and ad-hoc query pages can be mapped to CLI parameters:

- Task development page: `<host>/dorado/development/node/<taskId>?groupName=<region>&project=<region>_<projectId>`
- Ad-hoc query page: `<host>/dorado/development/query/<taskId>?groupName=<region>&project=<region>_<projectId>`

Use the path `<taskId>` as the task ID, `groupName` as `--region`, and the numeric suffix of `project` as `--project-id`.

When the user gives a task development page URL and wants the current task detail, prefer:

```bash
bytedcli dorado task get <taskId> --region <region>
```

Treat `project=<region>_<projectId>` as context unless the task also needs project-scoped APIs.

For the task page's "Task Monitoring / Baseline Monitoring" config, prefer:

```bash
bytedcli dorado task alarms --task-id <taskId> --region <region>
```

This maps to `GET /dorado_api/task/{taskId}/alarms?projectId={projectId}&supportTaskAlarm=true`; `--project-id` is auto-resolved from task details when omitted. Do not rely on `dorado task get` to infer alarm rules or baseline bindings.

To create or update a monitoring (alarm) rule ("运行监控") for a project, use:

```bash
bytedcli dorado task alarm-rule create --project-id <projectId> --name "<rule name>" --task-ids <id1,id2> --alarm-channels lark,phone --region <region>
bytedcli dorado task alarm-rule update --rule-id <ruleId> --project-id <projectId> --frequency 3 --add-task-ids <id> --region <region>
```

Create maps to `POST /dorado_api/rule?projectId=<projectId>` (body wraps the rule under `alarmRuleQOs`; response returns the new rule ID array). Update maps to `PUT /dorado_api/rule/{ruleId}?projectId=<projectId>` and is read-modify-write: the CLI fetches the existing rule first, overlays only the fields you pass, then PUTs the full payload so unspecified fields are not cleared. Common fields are structured flags (`--name`, `--monitor-scope all|specify_instance`, `--alarm-channels lark,phone`, `--frequency`, `--alarm-interval`, `--oncalls`, `--task-ids`, `--failed-alarm-item-type`, `--send-to-owner`, `--send-to-business-contact`); pass evolving nested items via `--timeout-alarm-items '<json array>'`, and pass any rare/extra keys via `--body '<json>'` / `--body-file <path>`, which is shallow-merged last (top-level `Object.assign` — an override key replaces the whole value, including nested objects, so pass a complete object for any nested field you change). Both writes default to a dry-run preview of the final payload; add `--yes` to actually submit. To turn off `sendToOwner` explicitly, use `--body '{"sendToOwner":false}'`.

When the user already has a baseline-global task lookup endpoint (for example `/dorado_api/baseline_global/baseline/task/{taskId}/v2?region_value=<regionValue>`) and wants the bound baseline detail, prefer:

```bash
bytedcli dorado baseline get --task-id <taskId> --region-value <regionValue> --region <region>
```

Use `--region-value` for i18n baseline lookups when an explicit backend region enum is needed. For `--baseline-id <baselineId> --project-id <projectId>`, still pass `--region mycis` for mycis because the CLI switches baseline detail to the Oceanus baseline host internally while preserving the `mycis` page context and `x-dataleap-jwt-token` request shape.

For `mycis`, these baseline-global BFFs all share the same host-split rule: `baseline/task/{taskId}/v2`, `baseline/detail/{baselineId}`, `baseline/list`, `baseline/instance/list`, `baseline/{baselineId}/commitTasks/v2`, `baseline/alarm/instance/record`, `baseline/alarm/ack/record`, and `PUT baseline/{baselineId}` (baseline update) are sent to the Oceanus host physically, while `Origin/Referer`, `x-bcgw-vregion`, and `x-dataleap-jwt-token` still follow the `mycis` page context. `mycis` baseline_global uses `region_value=107`; pass `--region mycis` and the CLI fills it automatically, or pass `--region-value 107` explicitly. Reuse this route when adding similar baseline BFFs and cover the `mycis` host/header branch with offline tests.

When the user instead wants the project-scoped baseline list page (for example `/dorado_api/baseline_global/baseline/list?...&projectId=<projectId>&baseline=<keyword>`), prefer:

```bash
bytedcli dorado baseline list --project-id <projectId> --baseline "<keyword>" --sla-priority D1 --region-value <regionValue> --region <region>
```

Use `--sla-priority D1` through `D5` to filter baseline definitions by SLA priority, or omit it / pass `default` to include all priorities. CN and `mycis` use the same query field. Use `--region-value` for i18n baseline-list BFF calls the same way; for `mycis`, keep `--region mycis` because the CLI routes the list search to the Oceanus host while preserving the `mycis` page context and `x-dataleap-jwt-token` header shape.

When the user wants baseline business-date instances from `/dorado_api/baseline_global/baseline/instance/list?...&projectId=<projectId>`, prefer:

```bash
bytedcli dorado baseline instances --project-id <projectId> --baseline "<keyword>" --baseline-instance-ids <id1,id2> --start-baseline-time "YYYY-MM-DD HH" --end-baseline-time "YYYY-MM-DD HH" --region-value <regionValue> --region <region>
```

`--baseline-id`、`--baseline`、`--baseline-instance-ids` are optional filters for narrowing the instance search; the command can also query by project + time window only. For `mycis`, keep `--region mycis`; the CLI routes baseline instance lookups to the Oceanus host while preserving the `mycis` page context and `x-dataleap-jwt-token` header shape.

When the user wants baseline instance commit-task detail from `/dorado_api/baseline_global/baseline/<baselineId>/commitTasks/v2?...&projectId=<projectId>&baselineTime=<date>&baselineInstanceId=<instanceId>`, prefer:

```bash
bytedcli dorado baseline commit-tasks --baseline-id <baselineId> --baseline-instance-id <baselineInstanceId> --project-id <projectId> --baseline-time "YYYY-MM-DD" --region-value <regionValue> --region <region>
```

For `mycis`, keep `--region mycis`; the CLI routes this baseline instance detail lookup to the Oceanus host while preserving the `mycis` page context and `x-dataleap-jwt-token` header shape.

When the user wants to update a baseline definition (the web edit page's `PUT /dorado_api/baseline_global/baseline/<baselineId>?projectId=<projectId>&region_value=<regionValue>` call), prefer:

```bash
bytedcli dorado baseline update --baseline-id <baselineId> --project-id <projectId> --region <region> --region-value <regionValue> --body-file <path>
```

The baseline edit payload is large and evolving (`name`, `slaPriority`, `type`, `taskIds`, `hourlyCommitTimes`, `alarmConfs`, `baselineAlarmItems`, …), so pass the full JSON body through `--body-file <path>` (or inline `--body '<json>'`); the CLI forwards it unchanged. Provide exactly one of `--body`/`--body-file`. For `mycis`, keep `--region mycis`; the CLI routes the update PUT to the Oceanus host while preserving the `mycis` page context and `x-dataleap-jwt-token` header shape.

When the user only wants to add or remove task bindings on a baseline (the common "把某个 task 加入/移出基线" ask), prefer the incremental command instead of hand-building the full PUT body:

```bash
bytedcli dorado baseline update-tasks --baseline-id <baselineId> --project-id <projectId> --region <region> --add-task-ids <id1,id2> --remove-task-ids <id3>
```

The CLI fetches the baseline detail, projects it back into the edit-page PUT body, merges the task list (removals first, then additions, de-duplicated while preserving the existing order), and PUTs it — no manual body needed. Provide at least one of `--add-task-ids`/`--remove-task-ids` (comma-separated positive task IDs). When the merged task list equals the current one (e.g. adding a task that is already bound), the command short-circuits and reports `no change` without issuing a PUT. For `mycis`, keep `--region mycis`; routing follows the same Oceanus host-split rule as `baseline update`.

Note that `update-tasks` is equivalent to opening the web edit page, changing only the task list, and saving — it rebuilds the whole baseline via the edit-page projection. Fields the edit page does not write back (e.g. `alarmConf`, `baselineAlarmItems[*].params`, `alarmConfs[*].{alarmItems,larkGroups,openAlarmUpgrade}`) are reset to their edit-page projection (emptied or dropped), not the values currently stored on the baseline. If you must preserve those alarm fields, use `baseline update --body-file` with the full payload instead.

For page-shaped submit flows such as `dorado task commit`, `dorado task commit-approval`, and `dorado node submit-approval`, if the web payload includes monitoring fields like `openDefaultSystemAlarm`, `customAlarmRuleIds`, and `baselineIds`, only expose the fields users can reason about directly. Keep fixed/default payload structures such as `noticeConf` in the implementation layer instead of asking users to pass empty objects.

When the web 「提交上线」dialog enables 「重跑历史数据」, the same commit endpoints accept optional `triggerConfig`. `task commit` / `task commit-approval` expose this via `--biz-date` (or start/end) plus overlays (`--submit-strategy`, `--check-types`, queue flags) or `--trigger-config` JSON. Omit lookback flags entirely for no-rerun commits — do not send an empty `triggerConfig` object.

## Commands

### spark-jar

Manage Spark-jar operator configuration on a Dorado node draft.

```bash
bytedcli dorado spark-jar create [options]
bytedcli dorado spark-jar update [options]
bytedcli dorado spark-jar get [options]
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `--main-class <mainClass>` - Spark main class (create: required; update: optional)
- `--main-file-path <path>` - Spark main file path (create: required; update: optional)
- `--main-resource-id <id>` - Main resource ID (create: required; update: optional)
- `--spark-version <ver>` - Spark version (create only, default: "3.2")
- `--params <params>` - Spark application params (create/update)
- `--spark-conf <k=v>` - Repeatable Spark conf entry as k=v (create/update)
- `--jars <json>` - JSON array string for jars (create/update)
- `--files <json>` - JSON array string for files (create/update)
- `--py-files <json>` - JSON array string for pyFiles (create/update)
- `--archives <json>` - JSON array string for archives (create/update)
- `--field <field>` - Field name to print (get only)
- `-r, --region <region>` - Dorado region (default: "cn")

`spark-jar update` requires at least one update field, e.g. `--main-class` or `--spark-conf`.

**Examples:**

```bash
# Create Spark-jar configuration on a node draft
bytedcli dorado spark-jar create --node-id demo-node-id \
  --main-class com.example.Main \
  --main-file-path /path/to/app.jar \
  --main-resource-id 100001234 \
  --spark-conf spark.executor.memory=2g \
  --spark-conf spark.sql.shuffle.partitions=200

# Read a single field (example output: com.example.Main)
bytedcli dorado spark-jar get --node-id demo-node-id --field mainClass

# Update sparkConf (repeat --spark-conf to set multiple keys)
bytedcli dorado spark-jar update --node-id demo-node-id \
  --spark-conf spark.sql.shuffle.partitions=200 \
  --spark-conf spark.executor.cores=4
```

---

### project list

List Dorado projects accessible to the user.

```bash
bytedcli dorado project list [options]
```

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `-p, --page <page>` - Page number (default: 1)
- `--size <size>` - Page size (default: 50)

**Example:**

```bash
bytedcli dorado project list --region boei18n
```

---

### folder structure

Show the folder structure of a Dorado project.

```bash
bytedcli dorado folder structure [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--root-id <rootId>` - Root folder ID: -1 for task development (default), -2 for temp queries
- `--engine-id <engineId>` - Engine ID filter
- `--exclude-folder-id <excludeFolderId>` - Exclude folder ID

**Example:**

```bash
bytedcli dorado folder structure --project-id 458 --region cn
```

---

### folder children

List children of a Dorado folder.

```bash
bytedcli dorado folder children [options]
```

**Options:**

- `--folder-id <folderId>` - Folder ID (required)
- `--project-id <projectId>` - Project ID (required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado folder children --folder-id 45678 --project-id 458 --region cn
```

---

### folder create

Create a subfolder in a Dorado project.

```bash
bytedcli dorado folder create [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--parent-uri <parentUri>` - Parent directory URI, e.g. 'task:///HrdNGPWr' (defaults to root 'task:///' if omitted)
- `--name <name>` - Folder name (required)
- `--description <description>` - Folder description (optional)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Create a subfolder under a specific parent directory
bytedcli dorado folder create --project-id 12345 --parent-uri "task:///HrdNGPWr" --name "demo-folder" --region cn

# Create with description
bytedcli dorado folder create --project-id 12345 --parent-uri "task:///HrdNGPWr" --name "demo-folder" --description "a demo subfolder" --region sg

# Create at root level
bytedcli dorado folder create --project-id 12345 --name "demo-folder" --region cn
```

**Output example:**

```
✓ Folder created successfully. Node UID: NB6LBxtiz, Name: demo-folder
```

---

### task list

List Dorado batch tasks via the web console task-list endpoint, with rich filters (status/priority/frequency/task type/tags/sort). Works across regions (cn, mycis, ...).

```bash
bytedcli dorado task list [options]
```

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `--project-id <projectId>` - Filter by project ID (required)
- `--task-id <taskId>` - Filter by task ID
- `--keyword <keyword>` - Search keyword (task name/uid/owner)
- `--owner <owner>` - Filter by owner
- `--status <status>` - Filter by task status; known values: `default` (all), `runnable`, `init`, `closed`. Unknown values are passed through to the backend with a warning (the registered enum may be incomplete).
- `--task-type <taskType>` - Filter by task type (e.g. `hsql`, `python`, `notebook`); default all
- `--priority <priority>` - Filter by data-asset SLA level: `D1`, `D2`, `D3`, `D4`, `D5` (legacy backend codes `super_core_task`/`core_task`/`super_high`/`high`/`normal` also accepted). Unknown values are passed through to the backend with a warning.
- `--frequency <frequency>` - Filter by schedule frequency; known values: `default` (all), `hourly`, `daily`, `weekly`, `monthly`, `every_ten_minutes`, `near_real_time`. Unknown values are passed through to the backend with a warning.
- `--schedule-type <scheduleType>` - Filter by schedule type; default all
- `--node-type <nodeType>` - Filter by node type (default: task_flow)
- `--search-type <searchType>` - Search match type (default: `content`)
- `--only-self` - Only return tasks owned by the current user
- `--alarm-rule-type <n>` - Filter by alarm-rule type (0=all, 1, 2, 3)
- `--tag-ids <ids>` - Comma-separated tag IDs to filter by
- `--sort-by <column>` - Sort column: update_time (default) or create_time
- `--sort-order <order>` - Sort order: desc (default) or asc
- `--limit <limit>` - Limit the number of results returned
- `--page <page>` - Page number (default: 1)
- `--page-size <size>` - Page size (default: 20)

**Example:**

```bash
# List runnable tasks in a project, sorted by create time
bytedcli dorado task list --region cn --project-id 9744 --status runnable --sort-by create_time --page-size 30

# Filter by owner and tags
bytedcli dorado task list --region cn --project-id 9744 --owner demo_user --tag-ids 1,2

# Filter D1 (highest SLA level) tasks
bytedcli dorado task list --region cn --project-id 9744 --priority D1
```

---

### task search

Search Dorado tasks by keyword/status. Keyword/status searches go through the task list v2 endpoint (the same one `task list` and the Dorado web console use). `--folder-id` switches to the legacy batch-search endpoint — the only one with a folder filter — which is known to fail with `Dorado API error: Unknown error` on many cn projects. For day-to-day "find a task by name" lookups, prefer `task list --keyword` (matches name/uid/owner and supports richer filters).

```bash
bytedcli dorado task search [options]
```

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `--project-id <projectId>` - Filter by project ID (required)
- `--folder-id <folderId>` - Filter by folder ID (legacy batch-search endpoint only)
- `--status <status>` - Filter by status (e.g. "init", "runnable", "closed"); single value for keyword search, comma-separated values only with `--folder-id`
- `--keyword <keyword>` - Filter by keyword in task name
- `-p, --page <page>` - Page number (default: 1)
- `--size <size>` - Page size (default: 20)

**Example:**

```bash
# Keyword search (task list v2 endpoint)
bytedcli dorado task search --region cn --project-id 458 --keyword "daily_report"

# Folder-scoped search (legacy endpoint; may fail on some cn projects)
bytedcli dorado task search --region boei18n --project-id 458 --folder-id 123456 --status "init"
```

---

### task get

Get Dorado task details including dependency task IDs, source/target info for DTS tasks, and SQL code for hsql tasks.

```bash
bytedcli dorado task get [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado task get 100274211 --region boei18n
```

**Output for DTS tasks:**

- Source Type, Source DB, Source Table, Source Region
- Target Type, Target DB, Target Table, Target Region

**Output for tasks with dependencies:**

- Dependency Task IDs

**Output for hsql tasks:**

- SQL Code section with the query

---

### task demand search / check / bind / unbind

Discover configured demand projects, modules, and work items, inspect a task's submit-time demand
gate, or explicitly change its work-item relations.

Discovery is staged so the CLI never guesses among configured projects or modules:

```bash
# 1. List enabled demand projects configured for the Dorado project.
bytedcli dorado task demand search \
  --project-id <project-id> \
  --region <region>

# 2. List modules in one selected demand project.
bytedcli dorado task demand search \
  --project-id <project-id> \
  --demand-project-id <demand-project-id> \
  --region <region>

# 3. Search work items in one selected module.
bytedcli dorado task demand search \
  --project-id <project-id> \
  --demand-project-id <demand-project-id> \
  --demand-module-id <demand-module-id> \
  --keyword '<keyword>' \
  --limit 50 \
  --region <region>
```

Search JSON output always contains `scope`, `projects`, `modules`, `work_items`, `current_count`,
`limit`, `truncated`, and `next_command`. The backend does not report a full work-item count, so
`current_count` describes only the returned CLI window. Unfiltered work-item discovery is always
marked `truncated=true`; keyword searches are also marked truncated when they reach `--limit`.
Refine `--keyword` instead of treating a truncated window as complete. A Dorado project without
demand configuration returns `scope=projects`, `projects=[]`, and `next_command=null`.

Check a task without changing any relation:

```bash
bytedcli dorado task demand check \
  --task-id <task-id> \
  --project-id <project-id> \
  --region <region>
```

`passed=true` requires both `is_bound=true` and `abnormal_work_item_count=0`. An unmet gate is
returned as data rather than a command failure so callers can inspect current relations and choose
the next action.

Bind one explicitly selected work item:

```bash
# Preview only.
bytedcli dorado task demand bind \
  --task-id <task-id> \
  --project-id <project-id> \
  --demand-project-id <demand-project-id> \
  --demand-module-id <demand-module-id> \
  --work-item-id <work-item-id> \
  --work-item-name '<work-item-name>' \
  --region <region>

# Submit after reviewing the preview.
bytedcli dorado task demand bind \
  --task-id <task-id> \
  --project-id <project-id> \
  --demand-project-id <demand-project-id> \
  --demand-module-id <demand-module-id> \
  --work-item-id <work-item-id> \
  --work-item-name '<work-item-name>' \
  --region <region> \
  --yes
```

The CLI reads the task type and validates task/project ownership plus demand project/module
configuration before POST. It also verifies that the selected work-item ID belongs to that module
and has `disabled=false`. Pass `--work-item-name` from the same search row so older items outside
the unfiltered result window can be resolved without trusting an ID alone. It does not create,
select, or skip a work item automatically. An exact existing relation returns `changed=false`
without another POST.

Unbind by the relation ID returned from `demand check`:

```bash
# Preview only.
bytedcli dorado task demand unbind \
  --task-id <task-id> \
  --project-id <project-id> \
  --relation-id <relation-id> \
  --region <region>

# Submit after reviewing the relation.
bytedcli dorado task demand unbind \
  --task-id <task-id> \
  --project-id <project-id> \
  --relation-id <relation-id> \
  --region <region> \
  --yes
```

Both mutations read relations back once after submission. If the write succeeds but readback fails
or cannot confirm the returned ID, JSON reports `verification_status=unresolved` and a warning.
Do not retry blindly; run `demand check` first.

---

### task code

Get the SQL code of a task. `--project-id` is auto-resolved from task details when omitted.

```bash
bytedcli dorado task code --task-id <taskId> [options]
```

**Options:**

- `--task-id <taskId>` - Task ID (required)
- `--project-id <projectId>` - Project ID (auto-resolved from task details when omitted)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--output <path>` - Write SQL code to a file

**Example:**

```bash
# Print the SQL of a task (project resolved automatically)
bytedcli dorado task code --task-id 100274211 --region boei18n

# Save the SQL to a local file
bytedcli dorado task code --task-id 100274211 --output ./task.sql
```

---

### task close / open

Close or reopen a Dorado task, matching the web task operation APIs.

```bash
bytedcli dorado task close [taskId] [options]
bytedcli dorado task open [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (auto-resolved from task details when omitted)
- `--name <name>` - Task name (auto-resolved from task details when omitted)
- `--skip-codes <codes>` - Skip specific error codes during the batch operation
- `-r, --region <region>` - Dorado region (default: "cn")

**APIs:** `POST /task/batch/v3/close` for close, `POST /task/batch/open` for open.

**Examples:**

```bash
bytedcli dorado task close 100274211 --project-id 458 --region cn
bytedcli dorado task open 100274211 --project-id 458 --region cn
```

If Dorado blocks the operation because enabled upstream/downstream tasks need attention, the backend error is surfaced directly. Use `--skip-codes` only when the web operation reports an error code that you intentionally want to skip.

---

### task copy

Copy a Dorado task to a target folder (same API as web **批量操作 → 复制**).

```bash
bytedcli dorado task copy [taskId] [options]
```

**Arguments:**

- `taskId` - Source task ID (required)

**Options:**

- `--project-id <projectId>` - Source project ID (required)
- `--folder-id <folderId>` - Target folder ID, sent as `opId` to Dorado (required)
- `--name <name>` - New task name (default: `{sourceTaskName}_copy`)
- `--target-project-id <projectId>` - Target project (default: same as `--project-id`)
- `-r, --region <region>` - Dorado region (default: "cn")

**API:** `POST /task/batch/v3/copy`

**Output contract:** Dorado may acknowledge a successful copy by echoing the source node and source task ID. bytedcli snapshots the target folder before the write and reads it back afterward; only a unique newly appeared task is returned as `new_task_id` with `verification_status=verified`. Text output labels both `New Task ID` and `Source Task ID` explicitly.

If readback cannot identify one task, JSON returns `new_task_id: null` with `verification_status: unresolved|ambiguous`, and text output prints a verification command. Do not use `source_task_id` as the copied task ID and do not retry blindly, because the copy request may already have succeeded.

**Example (from task development URL `.../node/305307463?project=sg_300002016`):**

```bash
bytedcli dorado task copy 305307463 \
  --project-id 300002016 \
  --folder-id 300164470 \
  --region sg
```

Use `dorado folder structure` or `dorado folder children` to find the target `--folder-id`.

---

### task update

Update SQL query for a task (hsql/fsql/stream_sql, saves as draft).

```bash
bytedcli dorado task update [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-q, --query <query>` - New SQL query (inline; use `--query-file` for large SQL)
- `--query-file <file>` - Read new SQL query from a file (recommended for large SQL; avoids the OS argv length limit)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado task update 100274211 --query "SELECT * FROM users WHERE active = 1" --region boei18n
bytedcli dorado task update 100274211 --query-file ./task.sql --region boei18n
```

**Note:** This command supports hsql, fsql, and stream_sql task types. It will reject unsupported task types. Prefer `--query-file` for large SQL instead of passing long SQL inline.

---

### task update-conf

Apply a partial `conf` JSON patch to a task draft. Designed for stream tasks (and any task whose runtime parameters live under `conf.configuration.{reader,writer,operator}.parameter`) that aren't covered by `task update` (SQL-only) or `task-draft update` (named DTS options).

```bash
bytedcli dorado task update-conf [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID to patch (required)

**Options:**

- `--task-file <path>` - JSON file containing the conf patch. Accepts three shapes:
  - raw `dorado task get` output: `{ data: { conf: {...} } }` (auto-unwrap)
  - task-shaped object: `{ conf: {...} }`
  - bare conf object: `{ configuration: {...} }`
- `--patch <json>` - Inline JSON object as conf patch (mutually exclusive with `--task-file`)
- `--expected-type <type>` - Optional sanity guard: fail before PUT when `draft.type` doesn't match (e.g. `stream_channel_rocketmq_hive`, `hive->clickhouse`)
- `--type <type>` - Optional override for the batch / DTS draft top-level `type` field (e.g. promote a freshly-created `common-dts-batch` shell into `hive->clickhouse`); realtime stream drafts reject this override and preserve the existing `type`
- `--queue <queue>` - Stream DTS draft: yarn queue to place the task on (e.g. `root.demo_flink_queue`). Only applied to realtime stream drafts
- `--cluster <cluster>` - Stream DTS draft: yarn cluster (e.g. `Demo-Cluster`)
- `--dc <dc>` - Stream DTS draft: data center (e.g. `my2`)
- `--priority <priority>` - Stream DTS draft: task priority (e.g. `normal`)
- `--engine-id <id>` - Stream DTS draft: engine id (default `0`)
- `--enable-failover` - Stream DTS draft: enable failover (default `false`)
- `--owner <owner>` - Stream DTS draft: `ownerUserName` for the saved draft
- `-r, --region <region>` - Dorado region (default: `cn`)

Exactly one of `--task-file` / `--patch` is required.

**Merge semantics:**

- Objects are deep-merged into the existing draft conf
- Arrays (e.g. `sourceSinks`) are replaced wholesale — supply the full array you want
- Scalars / `null` overwrite the target value
- Everything not mentioned in the patch is preserved verbatim

**API:** `POST /task/{taskId}/draft`

For realtime stream drafts (for example `kafka2clickhouse`, or any task whose `conf.typeGroup=stream` / `type` starts with `stream_channel_`), bytedcli automatically switches to `POST /realtime/{taskId}/draft` and preserves the original top-level `conf.typeGroup` instead of rewriting it. The base realtime draft body carries `taskId + conf + name + description`, so `--type` is rejected in this mode. For DTS streaming tasks (`common-dts-stream`, e.g. bmq->hive) the realtime body additionally accepts the runtime placement fields `queue` / `cluster` / `dc` / `priority` / `engineId` / `enableFailover` / `ownerUserName`; supply them via `--queue` / `--cluster` / `--dc` / `--priority` / `--engine-id` / `--enable-failover` / `--owner`. These extra fields are only attached when at least one of them is provided, so `kafka2clickhouse` runtime-parameter saves keep the minimal body.

**Example (from task development URL `.../node/306685092?project=sg_300002016`):**

```bash
bytedcli dorado task update-conf 306685092 \
  --patch '{"configuration":{"writer":{"parameter":{"tableName":"demo_table_test"}},"operator":{"parameter":{"commonConfig":{"tmNum":3}}}}}' \
  --expected-type stream_channel_rocketmq_hive \
  --region sg

# kafka2clickhouse / realtime stream task: keep a captured conf JSON, edit only the needed fields, then save
bytedcli dorado task update-conf 118524049 --task-file /tmp/demo-kafka2clickhouse.json --region cn
```

**Example (`global_hsql` batch shell):**

Create a global HSQL batch task shell through `/task/create`; the request keeps `type=global_hsql` and `typeGroup=global_hsql`.

```bash
bytedcli dorado task create --type global_hsql \
  --project-id <project-id> --folder-id <folder-id> \
  --name demo_global_hsql_task --region us-ttp
```

**Example with a JSON file (captured from `dorado task get`):**

```bash
bytedcli dorado task get 306685092 --region sg -j > /tmp/demo-task.json
# edit /tmp/demo-task.json: change conf.configuration.writer.parameter.tableName etc.
bytedcli dorado task update-conf 306685092 --task-file /tmp/demo-task.json --region sg
```

**Example (promote a `common-dts-batch` shell into `hive->clickhouse`):**

```bash
# Resolve the HSQL task-template root folder.
bytedcli dorado task template root-folder get \
  --region sg \
  --project-id 12345

# Read an HSQL task template detail; projectId is required by the Dorado detail endpoint.
bytedcli dorado task template get \
  --region sg \
  --template-id 24680 \
  --project-id 12345

# Create an HSQL task template; --folder-id is auto-resolved from --project-id.
bytedcli dorado task template create \
  --region sg \
  --project-id 12345 \
  --name demo-template \
  --description "sample template"

# 1) Create the shell (server-side type=common-dts-batch).
bytedcli dorado task create --type hive-clickhouse \
  --project-id 12345 --folder-id 67890 \
  --name hive2ch_demo --region mycis

# 2) Write reader=hive / writer=clickhouse via a conf patch and bump top-level type.
#    Patch shape mirrors the captured draft, e.g.:
#    {"configuration":{"reader":{"type":"hive","parameter":{"sourceType":"sql","engineType":"spark","query":"SELECT ...","columns":[...]}},
#                       "writer":{"type":"clickhouse","parameter":{"chClusterName":"...","chDbName":"...","chTableName":"...","shardColumn":"...","shardNum":16,"partition":"partition_date=${DATE}","partitionTypes":"time","columns":[...]}}}}
bytedcli dorado task update-conf 1204206582 \
  --task-file /tmp/hive2ch-patch.json \
  --type 'hive->clickhouse' \
  --region mycis
```

**Example (`stream_sql` realtime shell):**

Create the realtime shell via `/realtime/create`. Do not pass `--query` or `--query-file` at creation time; write the confirmed realtime configuration after the shell exists.

```bash
bytedcli dorado task create --type stream_sql \
  --project-id <project-id> --folder-id <folder-id> \
  --name demo_stream_sql_task --region sg
```

**Example (`java-flink` realtime shell):**

Create the Java Flink realtime shell via `/realtime/create` (`typeGroup=stream`, `type=stream_managed_java_flink`). Do not pass `--query` or `--query-file` at creation time; write the confirmed realtime configuration after the shell exists.

```bash
bytedcli dorado task create --type java-flink \
  --project-id <project-id> --folder-id <folder-id> \
  --name demo_java_flink_task --region sg
```

**Example (end-to-end `common-dts-stream` bmq->hive: target table + queue + resources):**

When the user only gives the bmq source, the agent must ask for the hive target table (there is no capability to create a hive table from a bmq topic), pick a healthy queue, and set sensible Flink resources before saving — do not save with empty/default placeholders.

```bash
# 1) Create the stream shell (server-side type=common-dts-stream via /realtime/create).
bytedcli dorado task create --type common-dts-stream \
  --project-id 300003392 --folder-id 300202455 \
  --name demo_dts_stream_task --region sg

# 2) Hive target table: bmq topic metadata has NO field schema, so there is NO way to derive
#    or auto-create a hive table from a bmq topic. If the user did not provide a hive target
#    table, ask them to provide an existing database + table. Once they do, you can read the
#    columns of that EXISTING table via the top-level `hive` command (NOT `dorado hive`):
bytedcli hive ddl <db> <existing_table> --region sg

# 3) Pick a healthy stream queue (lowest Allocated Rate / most Free CPU & Memory).
bytedcli dorado project yarn-queues --project-id 300003392 --task-type common-dts-stream --region sg

# 4) Save the full conf and pin runtime placement + resources.
#    /tmp/bmq2hive-conf.json holds {"typeGroup":"stream","configuration":{
#      "reader":{"type":"bmq","parameter":{"fieldSyncMode":"auto", ...}},
#      "writer":{"type":"hive","parameter":{"databaseName":"...","tableName":"...","partitions":[{"name":"date","type":"TIME"},{"name":"hour","type":"TIME"}]}},
#      "operator":{"parameter":{"autoParseConnectors":true,"commonConfig":{
#         "tmNum":4,"containerVcoresD":4,"tmMemoryMb":4096,"slotsPerTm":4,"jmMemoryVcoresD":3,"jmMemoryMb":4096},"enableIntelligent":false}}}}
bytedcli dorado task update-conf 306904995 \
  --task-file /tmp/bmq2hive-conf.json \
  --queue root.demo_flink_queue --cluster Demo-Cluster --dc my2 \
  --priority normal --owner demo.user --region sg
```

`commonConfig` field mapping (matches the "资源设置" panel): `tmNum`=TaskManager 个数, `containerVcoresD`=单 TaskManager CPU 数, `tmMemoryMb`=单 TaskManager 内存(MB), `slotsPerTm`=单 TaskManager slot 数, `jmMemoryVcoresD`=JobManager CPU 数, `jmMemoryMb`=JobManager 内存, `enableIntelligent`=启用智能资源. Tune `tmNum`/`slotsPerTm` to the topic throughput instead of copying the defaults.

**When to use which `update` command:**

| Goal                                                                                                                                                                                                                                                                                 | Recommended command        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------- |
| Change SQL of a hsql/fsql/stream_sql task. Use `--query-file` for large SQL instead of passing the SQL body inline.                                                                                                                                                                  | `dorado task update`       |
| Change top-level draft fields (name, schedule, dependencies, queue, ...) or DTS reader/writer parameters with named options. Realtime stream drafts only allow `name` / `description` and conf-backed fields in this command; queue/schedule/priority/dependency flags are rejected. | `dorado task-draft update` |
| Change stream-task runtime fields (`commonConfig`, `sourceSinks`, reader/writer `group`/`topic`/`tableName`, realtime `kafka2clickhouse` conf, ...) or apply an arbitrary captured conf patch                                                                                        | `dorado task update-conf`  |
| Register/list a stream task's 数据源登记 (input/output MQ topics for lineage & lag monitoring) without hand-writing the `sourceSinks[]` JSON                                                                                                                                         | `dorado task datasource`   |

---

### task datasource: 数据源登记 (data-source registration)

Stream / java-flink tasks can't have their lineage derived from code, so the
DataLeap web IDE exposes a **参数设置 → 数据源登记** table where input MQ topics
(`source`) and output MQ topics (`sink`) are registered by hand. They persist in
the draft at `conf.configuration.operator.parameter.sourceSinks[]`. This command
group reads and writes that list for you (writes save the draft only — commit /
online are still separate steps). Write requires a writable region (SG works;
see the `update-conf` region notes).

```bash
# List the current registration.
bytedcli dorado task datasource list 307220806 --region sg

# Auto-derive the whole registration from the task's own conf_meta and write it:
#   sources  <- conf_meta.sourceConfig[]  (kafkaCluster/kafkaTopic), tagged with --group
#   sinks    <- every SendToKafkaOp in conf_meta.pipelineConfig[].ops[]
# --group defaults to the task name (matching the web UI). Use --dry-run to preview.
bytedcli dorado task datasource sync 307220806 --region sg --dry-run
bytedcli dorado task datasource sync 307220806 --region sg --replace   # rewrite the list

# Register entries manually (repeatable). Sources take an optional :group segment.
bytedcli dorado task datasource set 307220806 --region sg \
  --source bmq_web_sg:ad_joiner_tiktok_search_click_trigger:ldp_search_app_cvr \
  --sink bmq_common_sg:ad_search_app_ldp_cvr_instance
```

Notes:

- `sync`/`set` **merge** with existing entries by default (dedupe key = type +
  cluster + topic; an incoming entry overrides a matching one, e.g. to fix a
  consumer group). Pass `--replace` to overwrite the whole list.
- `--mq-type` defaults to `bytemq` (BMQ clusters are `bmq_*`); override for
  `kafka` / `rocketmq`. `connectorType` mirrors `mqType`.
- `sync` requires the task to have a `userDefineConfig.conf_meta` (joiner
  pipelines); otherwise use `set`.

---

### task-draft update: dependency modes

`task-draft update` exposes two deliberately different same-region dependency modes:

- `--dependencies <deps>` performs a full replacement. Pass the complete dependency list that should remain after the update. Each comma-separated item uses `taskId[:offset:offsetsType]`.
- `--add-dependency <taskId[:offset:set]>` safely appends selected dependencies to the latest version `-1` draft. The option is repeatable; `offset` defaults to `0` and `offsetsType` defaults to `set`.

Incremental mode preserves the order and complete object shape of every existing dependency, including backend fields such as `dependNonExistParents`, `offsetFrequency`, `branchIds`, and `parentTaskInfo`. An exact existing `parentTaskId + offsets + offsetsType` tuple is reported as `already_present` and is not appended again.

Incremental mode is isolated from other draft mutations: do not combine `--add-dependency` with `--dependencies`, SQL/conf, schedule, queue, owner, outer-dependency, or DTS reader/writer options. Realtime stream drafts are rejected because the confirmed `/realtime/{taskId}/draft` body does not support top-level dependencies.

The default behavior is a dry-run. `--yes` performs the batch `POST /task/{taskId}/draft`; explicit `--dry-run` wins over `--yes`. Before POST, the CLI re-reads the draft and aborts if it changed. After POST, it re-reads version `-1` and verifies the dependency prefix plus unrelated draft fields. Dorado does not currently expose a confirmed ETag/version conditional-write contract, so a small race remains between the final preflight GET and POST.

Use dependency recommendations as candidates only. The caller must inspect the results and explicitly select producer task IDs:

Selection checklist:

- Read `task get` as well as `task dep-recommendations`, then remove task IDs already present in same-region `dependencies`. Do not confuse `outerDependencies` with same-region dependencies.
- Match partition semantics before choosing an offset: `${date}` normally maps to offset `0`; `${date-N}` requires the corresponding business offset.
- Treat `max_pt(...)`, SQL comments such as “not a strong dependency”, and other “latest available partition” logic as intentionally weak reads. Do not add those producers unless the caller explicitly wants scheduling to block on them.
- A producer may be an HSQL task or an online `hive_partition-sensor`; require a valid task ID and matching table/partition semantics rather than filtering only by task type.
- A `hive_partition-sensor` recommendation with `id=null` / `isOnlineTask=false` means the Sensor task has not been generated yet. Use `task hp-sensor create`; the command re-fetches the downstream task's current recommendations and refuses caller-constructed Sensor payloads.
- HPSensor creation matches `--database-name + --table-name`; add exact `--path`, `--namespace`, or `--frequency` selectors when multiple recommendations match. The selected recommendation's `databaseName`, `tableName`, `type`, `frequency`, optional `namespace`, and `path` are preserved without reconstruction.
- `--region` selects Dorado routing and authentication. `--storage-region` is the physical Hive storage region. Recommendation `namespace` is a third, independent value. Do not derive one from another.
- `--storage-region` may be omitted. Resolution order is explicit value, then the exact target-table output of online non-Sensor producer tasks, then the verified region mapping (`sg -> sg`, `gcp -> gcp_hive`, `us-ttp -> us-ttp`). Producer discovery combines the current recommendation with Coral table-task associations, but only Dorado `task data-outputs` is authoritative evidence.
- When producer tasks disagree, pass `--storage-region` explicitly. If an explicit value disagrees with producer evidence, the explicit value wins and the preview reports a warning.
- A verified mapping is only a recommendation. The dry-run returns `confirmation_required=true` and a command containing the candidate; obtain explicit user confirmation before running that command with `--storage-region <candidate> --yes`. Do not run `--yes` directly against an inferred mapping.
- HPSensor creation defaults to dry-run. Add `--yes` only after checking the selected recommendation and payload. A trailing slash, fixed partition, or date/hour placeholder in `path` is meaningful and must not be rewritten.
- For `--region us-ttp`, HPSensor creation uses the captured Web contract automatically: BDEE `dorado_tx_api`, `X-Titan-Token`, and the `https://dataleap-tx.tiktok-row.net/` page-root Referer. Do not switch to a caller-supplied JWT or copy browser fingerprint headers. This is specific to `sensorDrafts`; do not generalize it to other US-TTP endpoints without a capture.
- JSON recommendation output includes `uncreated_hp_sensors`, `uncreated_hp_sensor_count`, and `creatable`. Prefer this summary over scanning the full list. The CLI accepts nullable `vRegion` / `priority` / `version` and merges duplicate uncreated HPSensor records by `type + name`, preserving the non-empty table, namespace, and path fields.
- If the recommendation path contains empty values such as `date=/model_version=/app_id=`, Dorado rejects creation with code `1140`. The CLI now blocks before POST. Read `latestPartitionName` with `bytedcli --json hive detail sample_database sample_table --region <region>` or inspect `hive rows`, then pass a complete partition through `--create-path '<key=value/...>'`; keep `--path` unchanged as the recommendation selector.
- The create response does not prove that the downstream dependency has been saved, but its positive `sensor.id` is authoritative for the append workflow. Verify it with `task get`, then use that exact ID in `task-draft update --add-dependency`. Recommendation refresh is diagnostic only: SG can keep returning a new `id=null` / `#2` candidate after successful creation, so do not use refresh as the required ID source and do not create again.
- Do not call a separate Sensor online operation when the immediate response contains `version=-1` or `isOnlineTask=false`; the platform manages Sensor publication in the public `SENSOR` project.

```bash
# 1) Inspect producer candidates derived from the latest draft SQL.
bytedcli dorado task dep-recommendations <downstream-task-id> --region <region>

# 2a) For an existing producer with a positive task ID, preview the append (no POST).
bytedcli dorado task-draft update <downstream-task-id> \
  --add-dependency <producer-task-id>:0:set \
  --region <region>

# 2b) If the recommendation is an uncreated HPSensor, preview its creation payload.
bytedcli dorado task hp-sensor create \
  --downstream-task-id <downstream-task-id> \
  --database-name sample_database \
  --table-name sample_table \
  --region <region>

# Add exact selectors if the table has multiple HPSensor recommendations.
# When the recommendation path has empty partition values, provide a complete
# Hive partition separately through --create-path. Add --storage-region
# explicitly when confirming a mapped candidate or resolving ambiguous evidence.
bytedcli dorado task hp-sensor create \
  --downstream-task-id <downstream-task-id> \
  --database-name sample_database \
  --table-name sample_table \
  --storage-region <physical-storage-region> \
  --path '<partition-path>' \
  --create-path '<partition-key=value/...>' \
  --namespace <hive-namespace> \
  --frequency daily \
  --region <region> \
  --yes

# 3) Verify and use the positive sensor.id from the create response.
bytedcli dorado task get <sensor-task-id> --region <region>
bytedcli dorado task-draft update <downstream-task-id> \
  --add-dependency <sensor-task-id>:0:set \
  --region <region>

# 4) Re-run with --yes after reviewing added/already_present and before/after counts.
bytedcli dorado task-draft update <downstream-task-id> \
  --add-dependency <sensor-task-id>:0:set \
  --region <region> \
  --yes
```

JSON output includes `added`, `already_present`, `before_count`, `after_count`, `before_dependencies`, `after_dependencies`, `preservation_check`, `dry_run`, and `changed`.

On a successful save, Dorado may set top-level draft metadata such as `changed=true` and enrich newly appended dependency objects with nullable fields (`offsetFrequency`, `branchIds`, `parentTaskInfo`, `dependNonExistParents`). The CLI treats these as server-managed normalization while still requiring the original dependency prefix and unrelated draft configuration to remain intact. If an error says the POST succeeded but read-back verification failed, do not retry blindly: run `task get`, inspect whether the requested dependency is already present, and only retry if a fresh dry-run still reports it in `added`.

---

### task hp-sensor create

Create one Hive Partition Sensor selected from a downstream task's current dependency recommendations.

```bash
bytedcli dorado task hp-sensor create [options]
```

**Required options:**

- `--downstream-task-id <taskId>` - Downstream task whose SQL produced the recommendation.
- `--database-name <databaseName>` - Recommended Hive database.
- `--table-name <tableName>` - Recommended Hive table.

**Optional selectors and write controls:**

- `--storage-region <storageRegion>` - Explicit physical Hive storage region. When omitted, the CLI first checks online producer task outputs and then a verified mapping.
- `--path <path>` - Exact recommendation partition path.
- `--create-path <path>` - Complete `key=value/...` partition submitted when the recommendation path contains empty values.
- `--namespace <namespace>` - Exact recommendation namespace.
- `--frequency <frequency>` - Exact recommendation frequency.
- `-r, --region <region>` - Dorado routing/authentication region (default: `cn`).
- `--yes` - Submit creation; omitted means dry-run.

Dry-run output includes the selected recommendation, exact `sensorDrafts` payload, `path_override_applied`, `storage_region_resolution`, warnings, and the next command. `storage_region_resolution.source` is `explicit`, `producer_task`, or `verified_mapping`; a mapping has `confirmation_required=true` and cannot be submitted until the user explicitly confirms and reruns with `--storage-region`. Successful output includes the authoritative generated Sensor ID/name/project plus next-step commands. Follow those commands in order: verify the created Sensor, preview dependency append with the returned ID, then save with `--yes`. Recommendation refresh is optional diagnostics and may still return another uncreated candidate.

---

### task-draft explain

Validate task draft SQL using the backend checker that matches the task type:

- `type=hsql` -> Dorado `resource/explain`
- `type=stream_sql` -> Dorado `realtime/sqlCheck/{taskId}`

This command also supports checking the latest online version or a specific published version.

```bash
bytedcli dorado task-draft explain [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-p, --project-id <projectId>` - Project ID (required)
- `--dc <dc>` - Data center, e.g. `mycisb` (optional; defaults to task dc)
- `--username <username>` - Username to validate as (optional; defaults to task owner)
- `--date <date>` - Biz date used for `${DATE}` / `${date}` / `${date-1}` substitution
- `--online` - Validate the latest published version instead of the draft
- `--version <version>` - Validate a specific published version
- `--template-var <key=value>` - Repeatable template replacement for `{{key}}`
- `--auto-strip-mustache` - Best-effort replace `{{foo}} -> foo`
- `--engine <engine>` - Engine name (default: `HIVE`)
- `--engine-type <engineType>` - Engine type (default: `spark`)
- `--prod-env` - Validate against production env
- `--no-inject-dorado-sets` - Do not append `set dorado.job.*`
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Validate the latest draft
bytedcli dorado task-draft explain 100274211 --project-id 458 --region boei18n

# Validate with biz date substitution
bytedcli dorado task-draft explain 100274211 --project-id 458 --date 2025-04-20 --region mycis

# Validate a template-based SQL draft
bytedcli dorado task-draft explain 100274211 --project-id 458 \
  --template-var hrbi_corehr_global=hrbi_corehr_global --region mycis

# Validate the latest online version
bytedcli dorado task-draft explain 100274211 --project-id 458 --online --region mycis

# Validate a specific published version
bytedcli dorado task-draft explain 100274211 --project-id 458 --version 6 --region mycis

# Validate a stream_sql draft via realtime sqlCheck
bytedcli dorado task-draft explain 104905354 --project-id 1566 --region cn
```

**Notes:**

- For `type=hsql`, `--date`, `--template-var`, `--auto-strip-mustache`, `--engine`, `--engine-type`, `--prod-env`, and `--no-inject-dorado-sets` affect the generated `resource/explain` payload.
- For `type=stream_sql`, the CLI sends the selected task version's full `conf` plus `dc` to `realtime/sqlCheck/{taskId}`. The HSQL-specific SQL rewrite options above are accepted for CLI compatibility but do not modify the realtime-check payload.
- On OG-gated regions (`gcp`, `eu-ttp2`, `eu-compliance2`, `us-ttp-bdee`), `task-draft test` omits top-level `engineType` and `username` because `PUT /task/{id}/draft/test` rejects those fields as not tagged. The CLI still sends `dc`, `cluster`, and `queue`; engine selection stays in the draft conf and the effective identity comes from JWT.
- `task-draft test --input-table-map <json>` forwards Dorado's native multi-env input-table mapping for selecting upstream test tables during debug. Pass the same mapping shape used by the web UI (`mappingSourceType`, `mappingType`, `metaType`, `mappingValues:[devTable,prodTable]`); the CLI does not rewrite SQL table names.

---

### dts-draft explain

Validate DTS reader SQL syntax via Dorado `resource/explain`. The SQL source is `conf.configuration.reader.parameter.query`.

```bash
bytedcli dorado dts-draft explain [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-p, --project-id <projectId>` - Project ID (required)
- `--dc <dc>` - Data center, e.g. `mycisb` (optional; defaults to task dc)
- `--username <username>` - Username to validate as (optional; defaults to task owner)
- `--date <date>` - Biz date used for `${DATE}` / `${date}` / `${date-1}` substitution
- `--online` - Validate the latest published version instead of the draft
- `--version <version>` - Validate a specific published version
- `--template-var <key=value>` - Repeatable template replacement for `{{key}}`
- `--auto-strip-mustache` - Best-effort replace `{{foo}} -> foo`
- `--engine <engine>` - Engine name (default: `HIVE`)
- `--engine-type <engineType>` - Engine type (default: `spark`)
- `--prod-env` - Validate against production env
- `--inject-dorado-sets` - Append `set dorado.job.*` when `--date` is provided
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Validate DTS draft reader SQL
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 --region mycis --date 2025-04-20

# Validate with template replacement
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 \
  --template-var hrbi_atsx_global=hrbi_atsx_global --region mycis

# Validate the latest online version
bytedcli dorado dts-draft explain 1204196358 --project-id 1200002135 --online --region mycis
```

**Note:** This command supports DTS tasks where `conf.typeGroup` is `dts`, `common-dts-batch`, or `hive->clickhouse`. If a DTS reader is table-mode and has no `reader.parameter.query`, the command returns `status=not_applicable` and skips `resource/explain`; present-but-empty SQL still fails with `NO_DTS_QUERY`. If task details cannot infer `dc` or `ownerUserName`, pass `--dc` and `--username` explicitly.

---

### dts metadata lookup

Read DTS metadata through Dorado's DTS backend. Use these commands when creating DTS tasks, filling DTS drafts, resolving data source IDs, or building agent automation. These are native bytedcli commands and do not call `dpcli`.

DTS backend requests use Dataleap/Titan cookie auth. Run `bytedcli auth login --session` first; bytedcli reuses the local session and refreshes `titan_passport_id` for the target Dataleap host when needed.

```bash
bytedcli dorado dts region list --data-source-type <type> [--dorado-region-name <name>] [-r <region>]
bytedcli dorado dts database list --project-id <projectId> --data-source-type <type> [--instance-name <name>] [--dts-region-name <name>] [-r <region>]
bytedcli dorado dts database-region get --data-source-type <type> --database-name <db> [--dorado-region-name <name> ...] [-r <region>]
bytedcli dorado dts datasource list --project-id <projectId> --data-source-type <type> [--page <n>] [--page-size <n>] [-r <region>]
bytedcli dorado dts datasource get --project-id <projectId> --data-source-type <type> [--datasource-name <name> | --datasource-id <id>] [-r <region>]
bytedcli dorado dts table list --project-id <projectId> --data-source-type <type> [--database-name <db>] [--datasource-id <id>] [-r <region>]
bytedcli dorado dts column list --project-id <projectId> --data-source-type <type> [--database-name <db>] [--table-name <table>] [--query <sql>] [--schema-name <name>] [--datasource-id <id>] [-r <region>]
bytedcli dorado dts sql-column get --sql <sql> [-r <region>]
bytedcli dorado dts hdfs-cluster-prefix get [--dts-region-name <name>] [-r <region>]
bytedcli dorado dts clickhouse-shard-num get --cluster <cluster> [--dts-region-name <name>] [-r <region>]
bytedcli dorado dts clickhouse-cluster-name get --database-name <db> [--dts-region-name <name>] [-r <region>]
bytedcli dorado dts doris-writer-metadata get --cluster <cluster> [--dts-region-name <name>] [-r <region>]
bytedcli dorado dts abase-logical-table get --database-name <db> --table-name <table> --logical-table-name <logical> [--format <format>] [--value-type <type>] [--key-format <format>] [-r <region>]
bytedcli dorado dts mysql-split-key list --database-name <db> --table-name <table> [--dts-region-name <name>] [-r <region>]
```

Common options:

- `--data-source-type <type>`：DTS source/target type, such as `mysql`, `hive`, `doris`, or `clickhouse`.
- `--subtype <subtype>`：default `internal`.
- `--dts-region-name <name>`：DTS region name. Omit it when the command can infer from DTS regions.
- `--execution-mode <mode>`：default `batch`.
- `--page <n>` / `--page-size <n>`：standard datasource list pagination; defaults to page 1 and 20 items per page.
- `--schema-name <name>`：schema or cluster name; required for Doris writer-mode column lookup and useful for ClickHouse.
- `database-region get` uses DTS `fetch_regions` and returns candidate regions for the requested data source type; it does not validate database existence.
- `datasource get` accepts exactly one selector, `--datasource-name` or `--datasource-id`, and returns both ID and name.
- `sql-column get` reuses Dorado's Hive SQL schema parser and returns parsed output columns.
- `hdfs-cluster-prefix get` defaults `--dts-region-name` to `default`.
- `clickhouse-cluster-name get` calls Coral metadata; unsupported custom regions should be configured in Coral before use.
- `abase-logical-table get` falls back to `--format` / `--value-type` / `--key-format` when the logical table is not returned by DTS.
- `mysql-split-key list` returns primary-key columns from DTS `fetch_columns` with `skipAuth=true`.

Examples:

```bash
bytedcli -j dorado dts datasource list --project-id 300002016 --data-source-type mysql --region sg
bytedcli -j dorado dts datasource get --project-id 300002016 --data-source-type mysql --datasource-name demo_mysql --region sg
bytedcli -j dorado dts database-region get --data-source-type hive --database-name demo_db --dorado-region-name sg --region sg
bytedcli -j dorado dts table list --project-id 300002016 --data-source-type hive --database-name demo_db --region sg
bytedcli -j dorado dts column list --project-id 300002016 --data-source-type doris --query "select * from demo_table limit 1" --region sg
bytedcli -j dorado dts sql-column get --sql "select id, name from demo_db.demo_table" --region sg
bytedcli -j dorado dts hdfs-cluster-prefix get --dts-region-name default --region cn
bytedcli -j dorado dts clickhouse-shard-num get --cluster demo_ck_cluster --dts-region-name cn --region cn
bytedcli -j dorado dts clickhouse-cluster-name get --database-name demo_ck_db --dts-region-name ce --region cn
bytedcli -j dorado dts doris-writer-metadata get --cluster demo_doris --region sg
bytedcli -j dorado dts abase-logical-table get --database-name demo_db --table-name demo_table --logical-table-name demo_logical --value-type hash --region sg
bytedcli -j dorado dts mysql-split-key list --database-name demo_db --table-name demo_table --region sg
```

JSON output is normalized for agent use: list commands return arrays plus request context; `datasource get` returns the exact matched datasource record with both ID and name; `column list` returns normalized column names/types and preserves raw backend records.

---

### task binlog status

Check MySQL->Hive binlog task status.

```bash
bytedcli dorado task binlog status [options]
```

**Options:**

- `--task-id <taskId>` - Task ID used to infer source database/storage region and task type
- `--src-database <db>` - Source database (required if not inferred)
- `--src-storage-region <region>` - Source storage region (required if not inferred)
- `--subscribe-type <type>` - Subscribe type (default: "incremental")
- `--task-type <type>` - Task type (required if not inferred from --task-id)
- `--dorado-region-name <name>` - Dorado region name (required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Infer source info from task-id
bytedcli dorado task binlog status --task-id 67890 --dorado-region-name demo-region --region cn

# Explicit source info
bytedcli dorado task binlog status --src-database demo-db --src-storage-region demo-region --subscribe-type incremental --task-type mysql->hive --dorado-region-name demo-region --region cn
```

**Note:** When `--task-id` is provided, explicit `--src-database` / `--src-storage-region` / `--task-type` override inferred values.

---

### task binlog connect

Create and connect a MySQL->Hive binlog task.

```bash
bytedcli dorado task binlog connect [options]
```

**Options:**

- `--tree-node-id <id>` - Tree node ID (required)
- `--task-id <taskId>` - Task ID used to infer source info, owner, and task type
- `--owner <owner>` - Task owner (required if not inferred)
- `--src-database <db>` - Source database (required if not inferred)
- `--src-storage-region <region>` - Source storage region (required if not inferred)
- `--subscribe-type <type>` - Subscribe type (default: "incremental")
- `--task-type <type>` - Task type (required if not inferred from --task-id)
- `--dorado-region-name <name>` - Dorado region name (required)
- `--wait` - Wait until binlog is active
- `--wait-timeout-ms <ms>` - Wait timeout in ms (default: 60000)
- `--poll-interval-ms <ms>` - Poll interval in ms (default: 5000)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Infer source info from task-id
bytedcli dorado task binlog connect --tree-node-id 123456 --task-id 67890 --dorado-region-name demo-region --region cn

# Explicit source info, wait for activation
bytedcli dorado task binlog connect --tree-node-id 123456 --src-database demo-db --src-storage-region demo-region --owner demo-owner --task-type mysql->hive --dorado-region-name demo-region --region cn --wait
```

**Note:** `--tree-node-id` must be provided. When `--wait` times out, retry the same command later.

---

### task diff

Compare SQL between two versions of a task.

```bash
bytedcli dorado task diff [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `--from <version>` - Source version number (default: latest published)
- `--to <version>` - Target version number, -1 for draft (default: -1 = draft)

**Examples:**

```bash
# Compare latest published version vs draft (default)
bytedcli dorado task diff 100274211 --region boei18n

# Compare two specific versions
bytedcli dorado task diff 100274211 --from 5 --to 6 --region boei18n

# Compare a specific version vs draft
bytedcli dorado task diff 100274211 --from 5 --region boei18n
```

**Output:** Unified diff of SQL code between the two versions. With `--json`, returns structured object including `from_sql`, `to_sql`, `has_diff`, and `diff` fields.

---

### task version compare

Compare task configuration versions through a fixed, non-sensitive allowlist.

```bash
bytedcli dorado task version compare --task-id <task-id> [options]
```

**Options:**

- `--task-id <taskId>` - Task ID (positive integer, required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--from <version>` - Published source version (default: latest published)
- `--to <version>` - Target version, `-1` for draft (default: `-1`)

**Examples:**

```bash
# Compare the latest published version with the current draft
bytedcli dorado task version compare --task-id <task-id> --region sg

# Compare two explicit published versions
bytedcli dorado task version compare --task-id <task-id> --from 5 --to 6 --region sg

# Request the stable machine-readable result
bytedcli --json dorado task version compare --task-id <task-id> --from 5 --to -1 --region sg
```

This command is GET-only. Its JSON result declares `coverage: "allowlist"` and reports:

- scalar or scalar-array changes for explicitly allowlisted identity, schedule, runtime, and execution fields;
- local and cross-region dependency additions, removals, and modifications;
- only value counts and serialized byte counts for opaque sections such as SQL, auth, headers, reader/writer parameters, notebook content, environment data, and connectors;
- `unclassified_changes_detected` as a boolean when other configuration changed, without returning those values.

The output never returns raw task snapshots, SQL, authentication material, headers, reader/writer configuration, notebook content, environment values, or unclassified configuration values. Use `task diff` only when raw SQL comparison is intentionally required.

---

### task version list

List version history for a task.

```bash
bytedcli dorado task version list [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `--page <n>` - Page number, 1-based (default: 1)
- `--page-size <pageSize>` - Page size (default: 20)
- `--include-draft` - Include the latest synthetic draft row in published version results
- `--draft-history` - List draft commit history with full `C...` commit IDs; mutually exclusive with `--include-draft`

**Examples:**

```bash
# Published version history
bytedcli dorado task version list <task-id> --region sg

# Draft commit history for selecting a C... commit ID
bytedcli dorado task version list <task-id> --draft-history --region sg
```

`--draft-history` is read-only and uses Dorado's draft-version history endpoint. JSON output keeps the standard `versions`, `total`, `page`, and `page_size` fields; each draft row includes its `commitId` when provided by Dorado.

---

### task online

Deploy (bring online) a task by committing its current draft.

For realtime stream tasks (for example `kafka2clickhouse`, `stream_channel_*`, or tasks whose draft `conf.typeGroup=stream`), bytedcli automatically switches from the batch `PUT /task/{taskId}/commit` path to `PUT /realtime/{taskId}/online`.

```bash
bytedcli dorado task online [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--message <message>` - Deploy message
- `--skip-codes <codes>` - Skip specific error codes during commit
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado task online 100052730 --project-id 458 --region boei18n
bytedcli dorado task online 100052730 --project-id 458 --message "deploy v2" --skip-codes "-1005" --region va
```

---

### task stream-online

Run the legacy two-step deploy-package flow for a Dorado streaming-channel task. Prefer `task online` for normal stream-task deploys; it now uses the realtime `PUT /realtime/{taskId}/online` endpoint automatically when the draft is a realtime stream task.

**Why this exists** (vs. `task online`):

- `task online` now handles realtime stream drafts directly through `PUT /realtime/{taskId}/online`.
- `task stream-online` is kept for the explicit deploy-package workflow where you intentionally want:
  1. `PUT /task/{id}/commit` with `commitType=commit` → returns `tmpCommitId`
  2. `PUT /deploy/v2/create` with `reviewPackages=[{ commitIdLists:[tmpCommitId] }]` → creates the deploy package
- `task stream-online` wraps both steps in a single CLI call and is implemented in the service layer (`src/services/dorado/stream_online.ts`) since it orchestrates two API endpoints.

```bash
bytedcli dorado task stream-online [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--review-users <users>` - Comma-separated reviewer LDAPs (required; for self-approval, pass the task owner's LDAP)
- `--review-policy-id <id>` - Review policy ID (default: `-1`)
- `--message <message>` - Deploy message (used in both step 1 and step 2)
- `--deploy-package-name <name>` - Deploy package display name (default: `stream-online_<taskId>_<ts>`)
- `--skip-codes <codes>` - Skip specific error codes during commit (e.g. `-1005`)
- `--no-open-default-system-alarm` - Disable default system alarm on the commit step (default: enabled, matches `task commit`)
- `--custom-alarm-rule-ids <ids>` - Comma-separated alarm rule IDs (optional)
- `--baseline-ids <ids>` - Comma-separated baseline IDs (optional)
- `--agent-config <json>` - Agent config JSON string, e.g. `'{"sessionId":"demo"}'`
- `-r, --region <region>` - Dorado region (default: `cn`)

**APIs:** `PUT /task/{taskId}/commit` (commitType=commit) → `PUT /deploy/v2/create`

**Example (from task development URL `.../node/305399999?project=sg_300002016`):**

```bash
bytedcli dorado task stream-online 305399999 \
  --project-id 300002016 \
  --review-users demo.owner \
  --review-policy-id -1 \
  --message "stream-online via bytedcli" \
  --region sg
```

**Note**: If your goal is simply to bring a realtime stream task online, prefer `task online`. Keep `task stream-online` only for the deploy-package workflow itself.

---

### task commit-approval

Submit a task draft for approval using the web IDE commit-and-deploy payload shape.

For realtime stream tasks (for example `kafka2clickhouse`, `stream_channel_*`, or tasks whose draft `conf.typeGroup=stream`), bytedcli automatically routes this command to `PUT /realtime/{taskId}/commit` instead of the batch `PUT /task/{taskId}/commit`.

```bash
bytedcli dorado task commit-approval [taskId] [options]
```

**Arguments:**

- `taskId` - Task ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--review-policy-id <id>` - Review policy ID (required; must be explicitly provided by the caller for the current project)
- `--review-users <users>` - Comma-separated reviewer usernames (required; must be explicitly provided by the caller for the current project)
- `--baseline-ids <ids>` - Comma-separated baseline IDs
- `--custom-alarm-rule-ids <ids>` - Comma-separated alarm rule IDs
- `--agent-config <json>` - Agent config JSON string
- `--skip-codes <codes>` - Skip specific error codes during commit
- `--no-open-default-system-alarm` - Disable default system alarm
- `-r, --region <region>` - Dorado region (default: "cn")

**Note:** `review-policy-id` and `review-users` vary by project. Do not infer them from project defaults; ask the user to provide both values explicitly.
Use this dedicated command because the approval payload is page-shaped and sensitive to field presence/semantics; do not emulate it with nearby non-approval commands plus extra fields.

**Example:**

```bash
bytedcli dorado task commit-approval 100052730 --project-id 458 \
  --review-policy-id 24 \
  --review-users "demo-user-a,demo-user-b" \
  --custom-alarm-rule-ids 11870,14696 \
  --baseline-ids 33 \
  --agent-config '{"sessionId":"demo-session"}' \
  --region mycis
```

---

### task commit-batch-approval

Submit multiple Dorado commits for approval in one deploy package through the web `deploy/v2/create` payload shape.

```bash
bytedcli dorado task commit-batch-approval [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--name <name>` - Deploy package name (required)
- `--message <message>` - Approval message shown in the deploy package
- `--review-policy-id <id>` - Review policy ID (required; must be explicitly provided by the caller for the current project)
- `--review-users <users>` - Comma-separated reviewer usernames (required; must be explicitly provided by the caller for the current project)
- `--commit-ids <ids>` - Comma-separated commit IDs to include in the batch (required)
- `--skip-codes <codes>` - Skip specific error codes during approval submission (e.g. `-1005`, or `-10000` for confirmation-class alarms such as "another task already syncs the same table, confirm to deploy"). The value is injected into both the request body and the URL query, matching single-task `commit-approval`/`online`, so batch approval can skip these confirmation prompts.
- `--develop-conf <json>` - Optional `deployPackage.developConf` JSON object
- `-r, --region <region>` - Dorado region (default: "cn")

**Note:** Keep this separate from `task commit-approval` because batch approval uses `reviewPackages[]` plus a `deployPackage` envelope. Do not emulate it by looping single-task approval commands.

**Example:**

```bash
bytedcli dorado task commit-batch-approval --project-id 458 \
  --name demo_pkg_20260507 \
  --message "batch approval" \
  --review-policy-id 24 \
  --review-users "demo-user-a,demo-user-b" \
  --commit-ids "108103,108111,108110" \
  --region mycis
```

---

### deploy list

List Dorado publish-center deploys for a project. Optionally add `--creator` to filter by applicant/creator using `deployUserName`; add `--all-pages` when you need the full aggregated history for the current project/filter instead of a single page.

```bash
bytedcli dorado deploy list --project-id <projectId> [--creator <username>] [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--creator <username>` - Optional creator username filter for publish-center deploys
- `--page <n>` - Page number (default: `1`)
- `--page-size <n>` - Items per page (default: `20`)
- `--all-pages` - Auto-fetch all pages for the current project/filter
- `-r, --region <region>` - Dorado region (default: `cn`; use `mycis` for `dataleap-mycis.byteintl.net`)

**Example:**

```bash
bytedcli dorado deploy list --project-id <project-id> --region mycis
bytedcli dorado deploy list --project-id <project-id> --creator demo.user --all-pages --region mycis
```

---

### deploy get

Get a Dorado publish-center deploy detail (`GET /deploy/{deployId}/detail?projectId=...`). `--deploy-id` accepts either the legacy numeric deploy package ID or a publish-center UUID.

```bash
bytedcli dorado deploy get --deploy-id <deployId> --project-id <projectId> [options]
```

**Options:**

- `--deploy-id <deployId>` - Deploy package ID or publish-center UUID (required)
- `--project-id <projectId>` - Project ID (required)
- `-r, --region <region>` - Dorado region (default: `cn`; use `mycis` for `dataleap-mycis.byteintl.net`)

**Example:**

```bash
bytedcli dorado deploy get --deploy-id <deploy-id> --project-id <project-id> --region mycis
```

---

### deploy diff-sql

View SQL diff fields from a Dorado deploy package detail page (`GET /deploy/{deployId}/detail?projectId=...`). It also compares `rawCommitVo` and `newCommitVo` code snapshots when the API does not return a dedicated diff SQL field.

```bash
bytedcli dorado deploy diff-sql --deploy-id <deployId> --project-id <projectId> [options]
```

**Options:**

- `--deploy-id <deployId>` - Deploy package ID (required)
- `--project-id <projectId>` - Project ID (required)
- `-r, --region <region>` - Dorado region (default: "cn"; use `mycis` for `dataleap-mycis.byteintl.net`)

**Example:**

```bash
bytedcli dorado deploy diff-sql --deploy-id <deploy-id> --project-id <project-id> --region mycis
```

---

### deploy approve

Approve a Dorado deploy package (`PUT /deploy/{deployId}/approve?projectId=...`).
This is a write operation that takes effect immediately and cannot be undone; omit `--yes` to preview the target deploy package before execution.

```bash
bytedcli dorado deploy approve --deploy-id <deployId> --project-id <projectId> [options]
```

**Options:**

- `--deploy-id <deployId>` - Deploy package ID (required)
- `--project-id <projectId>` - Project ID (required)
- `--review-message <message>` - Review message passed as `reviewMessage`
- `--skip-codes <codes>` - Skip specific error codes during deploy package review
- `--yes` - Confirm and execute the approve operation
- `-r, --region <region>` - Dorado region (default: "cn"; use `mycis` for `dataleap-mycis.byteintl.net`)

**Example:**

```bash
bytedcli dorado deploy approve --deploy-id <deploy-id> --project-id <project-id> --region mycis --yes
```

---

### deploy reject

Reject a Dorado deploy package (`PUT /deploy/{deployId}/reject?projectId=...`).
This is a write operation that takes effect immediately and cannot be undone; omit `--yes` to preview the target deploy package before execution.

```bash
bytedcli dorado deploy reject --deploy-id <deployId> --project-id <projectId> [options]
```

**Options:**

- `--deploy-id <deployId>` - Deploy package ID (required)
- `--project-id <projectId>` - Project ID (required)
- `--review-message <message>` - Review message passed as `reviewMessage`
- `--skip-codes <codes>` - Skip specific error codes during deploy package review
- `--yes` - Confirm and execute the reject operation
- `-r, --region <region>` - Dorado region (default: "cn"; use `mycis` for `dataleap-mycis.byteintl.net`)

**Example:**

```bash
bytedcli dorado deploy reject --deploy-id <deploy-id> --project-id <project-id> --region cn --review-message "not approved" --yes
```

---

### instance list

List Dorado task instances.

```bash
bytedcli dorado instance list [options]
```

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")
- `--project-id <projectId>` - Filter by project ID (required for listing)
- `--task-id <taskId>` - Filter by task ID
- `--status <status>` - Filter by status (running, success, failed, etc.)
- `--start-time <time>` - Filter by start time (ISO format)
- `--end-time <time>` - Filter by end time (ISO format)
- `-p, --page <page>` - Page number (default: 1)
- `--size <size>` - Page size (default: 20)

**Example:**

```bash
bytedcli dorado instance list --region boei18n --project-id 458 --task-id 100052730
```

---

### instance get

Get Dorado instance details.

```bash
bytedcli dorado instance get [instanceId] [options]
```

**Arguments:**

- `instanceId` - Instance ID (required)

**Options:**

- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado instance get 258345284 --region boei18n
```

---

### instance rerun

Rerun one exact Dorado instance. This is different from task-level lookback: the command checks and submits the specified instance ID through the instance rerun endpoints. It performs a dry-run by default and sends no write request until `--yes` is provided.

```bash
bytedcli dorado instance rerun --project-id <projectId> --instance-id <instanceId> [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--instance-id <instanceId>` - Exact instance ID (required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--yes` - Submit after repeating the instance eligibility checks; omit for dry-run

Common console mappings are Singapore → `sg`, GCP/US-EastRed → `gcp`, and Norway/NO1A → `eu-ttp2`. Prefer `gcp` over the lower-level `us-eastred` profile because the `gcp` configuration also supplies the required `us-eastred` request vregion. The region configuration selects the authentication site automatically, so `--site` is not required for these commands. On an office network, leave `BYTEDCLI_NETWORK_PROFILE` unset for SG; set it to `prod` only from a production network that can reach the internal SG host.

The submission body contains only the instance ID and project ID. After submission, bytedcli reads the instance records for the same task and schedule to identify the new rerun instance. If the write is accepted but the new ID cannot be verified, do not retry blindly; inspect `instance record` first.

**Example:**

```bash
# Preview only
bytedcli dorado instance rerun --project-id 12345 --instance-id 67890 --region us-ttp

# Submit the exact instance rerun
bytedcli dorado instance rerun --project-id 12345 --instance-id 67890 --region us-ttp --yes

# Regional examples
bytedcli dorado instance rerun --project-id 12345 --instance-id 67890 --region sg
bytedcli dorado instance rerun --project-id 12345 --instance-id 67890 --region gcp
bytedcli dorado instance rerun --project-id 12345 --instance-id 67890 --region eu-ttp2
```

---

### instance slowest-link

Get the slowest task link in each layer of the upstream execution chain of a specified task instance.

```bash
bytedcli dorado instance slowest-link [instanceId] [options]
```

**Arguments:**

- `instanceId` - Instance ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--root-instance-id <rootInstanceId>` - Root instance ID (optional, defaults to instanceId)
- `--root-project-id <rootProjectId>` - Root project ID (optional, defaults to projectId)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado instance slowest-link 258345284 --project-id 458 --region cn
bytedcli dorado instance slowest-link 258345284 --project-id 458 --region sg --root-instance-id 258345284 --root-project-id 458
```

---

### instance log-summary

Get the log summary for a Dorado instance.

```bash
bytedcli dorado instance log-summary [instanceId] [options]
```

**Arguments:**

- `instanceId` - Instance ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--fetch-rule <fetchRule>` - Fetch rule (default: 2)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado instance log-summary 258345284 --project-id 458 --region cn
```

---

### instance diagnose

Get diagnose data for a Dorado offline task instance (e.g. Spark).

```bash
bytedcli dorado instance diagnose [instanceId] [options]
```

**Arguments:**

- `instanceId` - Instance ID (required)

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--engine <engine>` - Compute engine segment in URL path (default: "spark")
- `--run-mode <runMode>` - Diagnose run mode (default: "system")
- `--no-trigger` - Do not trigger a new diagnose, only read cached result
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado instance diagnose 6330831719 --project-id 1118 --region cn
```

---

### Dorado task diagnosis with bytedcli only

Use this read-only flow when diagnosing a Dorado failed instance, slow Spark run, or Flink runtime failure. Do not call `dpcli`; the first-phase replacement path is fully native in bytedcli. Do not run mutating commands such as `rerun`, `online`, `commit`, `set-success`, `abort`, or any `update*` command unless the user explicitly asks for remediation after diagnosis.

1. Confirm task/project/instance context. If the user gives a task ID, resolve failed instance IDs from records or a bounded instance list.

```bash
bytedcli --json dorado task get <task_id> --region <region>
bytedcli --json dorado instance record <task_id> \
  --project-id <project_id> --region <region> --schedule <yyyy-MM-dd+HH:mm:00>
bytedcli --json dorado instance get <instance_id> --region <region>
```

2. Collect Dorado-side evidence. `instance log-summary` is the fast first pass; `download-instance-log` gives the full text log for SQL compile, permission, config, and YARN submission errors.

```bash
bytedcli --json dorado instance log-summary <instance_id> \
  --project-id <project_id> --region <region>
bytedcli --json dorado instance diagnose <instance_id> \
  --project-id <project_id> --region <region>
bytedcli --json dorado download-instance-log --instance-id <instance_id> \
  --project-id <project_id> --region <region> -o /tmp/dorado_<instance_id>.log
```

3. If an application ID is present, collect Megatron-side evidence.

```bash
bytedcli --json megatron app get --app-ids <application_id> -r <region>

# Spark application: history URL + AppMaster log files.
bytedcli --json megatron spark log-link list --app-id <application_id> -r <region>

# Flink application: JobManager log plus selected TaskManager logs.
bytedcli --json megatron flink log-link list --app-id <application_id> -r <region>
bytedcli --json megatron flink log-link list --app-id <application_id> -r <region> \
  --taskmanager-keyword <container_or_host_keyword> --resolve-taskmanager-downloads
```

4. For Spark applications, continue with Spark History REST data when log links or summary indicate an execution-level issue.

```bash
bytedcli --json megatron spark-ui summary get --app-id <application_id> -r <region>
bytedcli --json megatron spark-ui jobs list --app-id <application_id> -r <region>
bytedcli --json megatron spark-ui executors list --app-id <application_id> --all -r <region>
bytedcli --json megatron spark-ui stages get --app-id <application_id> --stage-id <stage_id> -r <region>
bytedcli --json megatron spark-ui sql get --app-id <application_id> --sql-id <sql_id> -r <region>
```

5. If no application ID exists, prioritize local log patterns from `/tmp/dorado_<instance_id>.log`: `NoPrivilegeException`, `SemanticException`, `ParseException`, `AnalysisException`, `CalciteContextException`, `Number of INSERT target columns`, `TQS 查询失败`, `FAILED`, and `ERROR`.

---

### Debug permission failures and apply via Coral

Use this flow when a Dorado instance fails quickly with a TQS/Hive permission error. If the user gives a numeric ID and calls it an "instance", verify whether it is actually a task ID: `instance get` will fail or not find recent records, while `task get <id> --region <region>` returns task metadata.

Do not use `bytedcli hive` or `bytedcli iam` to apply missing Hive/TQS permissions for a Dorado task. `hive` is useful for metadata lookup and `iam` for employee identity lookup; permission application should go through `bytedcli coral permission apply`.

1. Confirm task and project metadata:

```bash
bytedcli --json dorado task get <task_id> --region va
bytedcli --json dorado project get <project_id> --region va
```

2. For a task ID, list recent records by schedule date to find failed instance IDs:

```bash
bytedcli --json dorado instance record <task_id> \
  --project-id <project_id> --region va --schedule <yyyy-MM-dd+HH:mm:00>
```

For broad recent searches, always bound the time window and page through results. Unbounded project instance lists can time out.

```bash
bytedcli --json dorado instance list --project-id <project_id> --region va \
  --start-time <start_iso_time> --end-time <end_iso_time> \
  --page-size 100 --page 1
```

3. Inspect the failed instance and fetch the log to `/tmp`:

```bash
bytedcli --json dorado instance get <instance_id> --region va
bytedcli --json dorado instance diagnose <instance_id> --project-id <project_id> --region va
bytedcli dorado download-instance-log --instance-id <instance_id> \
  --project-id <project_id> --region va --output /tmp/dorado_<instance_id>.log --json
```

4. Parse `NoPrivilegeException` lines from the log. Required privileges are emitted in this shape:

```text
User <user_or_psm> does not have privileges for QUERY
Server=hive->Db=<db>->Table=<table>->Columns=[<column>]->action=select
Server=hive->Db=<db>->Table=<table>->Rows=[<row_policy>]->action=select
```

Apply read permission through Coral for every affected auth subject. For Dorado tasks that run with a project PSM/account, apply for both the human owner and the project PSM if both appear in the error. Repeat `--column` for the missing columns; omit `--column` only for table-level access.

```bash
bytedcli --json coral permission apply --region va \
  --db-name example_db --table-name example_table \
  --auth-type person --auth-object demo-user --permission read \
  --column sample_col --column sample_col_2 \
  --requirement-type index-calculation \
  --reason "Dorado task <task_id> needs these columns for scheduled aggregation."

bytedcli --json coral permission apply --region va \
  --db-name example_db --table-name example_table \
  --auth-type psm --auth-object demo.project.psm --permission read \
  --column sample_col --column sample_col_2 \
  --requirement-type index-calculation \
  --reason "Dorado task <task_id> runs with this project PSM and needs these columns."
```

If Coral returns `CORAL_PERMISSION_RESOURCE_CLOSED`, the table is not open for Coral permission applications. Report that no application was created and include the returned table URL/resource details; do not claim success or invent an approval link.

---

### task relation-nodes

Get task upstream/downstream lineage nodes at specified time.

```bash
bytedcli dorado task relation-nodes [options]
```

**Options:**

- `--project-id <projectId>` - Project ID (required)
- `--task-id <taskId>` - Task ID (required)
- `--task-time <taskTime>` - Task time (yyyy-MM-dd+HH:mm:00) (required)
- `--relation <relation>` - Relation type: parent (upstream) or children (downstream) (default: "parent")
- `--depth <depth>` - Lineage depth (default: 1)
- `--no-combine` - Do not combine nodes (default: combine)
- `--task-type <taskType>` - Task type (e.g., hsql) (optional)
- `--cross-region` - Whether to enable cross-region query (optional)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Query upstream lineage (default) without task-type
bytedcli dorado task relation-nodes --project-id 10 --task-id 123651434 --task-time "2026-04-13+02:00:00" --region cn

# Query upstream lineage (default) with task-type
bytedcli dorado task relation-nodes --project-id 10 --task-id 123651434 --task-time "2026-04-13+02:00:00" --task-type hsql --region cn

# Query downstream lineage
bytedcli dorado task relation-nodes --project-id 10 --task-id 123651434 --task-time "2026-04-13+02:00:00" --task-type hsql --relation children --region cn

# Query lineage with depth 2
bytedcli dorado task relation-nodes --project-id 10 --task-id 123651434 --task-time "2026-04-13+02:00:00" --task-type hsql --depth 2 --region sg

# JSON mode
bytedcli dorado task relation-nodes --project-id 10 --task-id 123651434 --task-time "2026-04-13+02:00:00" --task-type hsql -j
```

---

### node create

Create a new python/notebook/spark task node in a project.

```bash
bytedcli dorado node create --project-id <projectId> --name <name> --type <type> -r <region>
```

**Options:**

- `-p, --project-id <projectId>` - Project ID (required)
- `--name <name>` - Node name (required)
- `--type <type>` - Task type: `python`, `notebook`, or `spark` (default: "python")
- `--parent-uri <uri>` - Parent directory URI (default: "task:///"); use URIs from `tree-nodes children`
- `--description <description>` - Node description
- `--content <content>` - Initial code content (inline string)
- `--content-file <path>` - Path to file containing initial code
- `--metadata <json>` - Task configuration metadata as JSON string
- `--image-name <name>` - Docker image name
- `--image-id <id>` - Docker image ID (use `image list` to find)
- `--language <lang>` - Spark language: python, java, scala (spark only, default: "python")
- `--spark-version <ver>` - Spark version (spark only, default: "3.2")
- `--data-outputs <spec>` - Task data outputs config. Accepts JSON array (e.g. `'[{"type":"partition","databaseName":"dp_compliance","tableName":"demo_table","partitions":[{"key":"date","value":"${date}"}],"namespace":"sg"}]'`) or shorthand notation: `"other"`, `"db.table:date=${date},ns=sg"`, `"hdfs:/path"`, multiple entries separated by `";"`. Default: `[{"type":"other"}]`
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Create a python task
bytedcli dorado node create --project-id 458 --name demo-python-task --type python --region cn

# Create a notebook
bytedcli dorado node create --project-id 458 --name demo-notebook --type notebook --region cn

# Create a spark (PySpark) task
bytedcli dorado node create --project-id 458 --name demo-spark-task --type spark --region cn

# Create with Docker image (use image list to find id + name first)
bytedcli dorado node create --project-id 458 --name demo-python-task --type python --image-name demo-image --image-id 400012345 --region cn
bytedcli dorado node create --project-id 458 --name demo-notebook --type notebook --image-name demo-image --image-id 400012345 --region cn
bytedcli dorado node create --project-id 458 --name demo-spark-task --type spark --image-name demo-image --image-id 400012345 --region cn

# Spark task with explicit language and version (defaults: python, 3.2)
bytedcli dorado node create --project-id 458 --name demo-pyspark --type spark --language python --spark-version 3.2 --image-name demo-image --image-id 400012345 --region cn

# Create in a subfolder with initial code from file
bytedcli dorado node create --project-id 458 --name demo-notebook --type notebook --parent-uri "task:///f123/NdemoDir" --content-file ./my_notebook.ipynb --region cn

# Create with data outputs: partitioned Hive table
bytedcli dorado node create --project-id 458 --name demo-task --type python --data-outputs 'dp_compliance.demo_table:date=${date},ns=sg' --region sg

# Create with data outputs: HDFS path
bytedcli dorado node create --project-id 458 --name demo-task --type python --data-outputs 'hdfs:/sg/data/demo/output' --region sg

# Create with mixed data outputs (JSON array)
bytedcli dorado node create --project-id 458 --name demo-task --type spark --data-outputs '[{"type":"partition","databaseName":"dp_compliance","tableName":"demo_table","partitions":[{"key":"date","value":"${date}"}],"namespace":"sg"},{"type":"other"}]' --region sg
```

**Note:** When `--image-name`/`--image-id` is provided, `node create` automatically performs a follow-up save to ensure the image configuration persists correctly (the platform's create API does not fully persist nested `conf` on creation).

---

### node get

Get node draft content (code and metadata) for a python/notebook/spark task.

```bash
bytedcli dorado node get --node-id <nodeId> -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID, e.g. `NxyzABC` (required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado node get --node-id NxyzABC --region boei18n -j
```

---

### node save

Save (update) a python/notebook/spark node draft. Must include `--metadata` — API requires it. Standard practice: first `node get -j` to get current metadata, modify as needed, then write back the full metadata.

```bash
bytedcli dorado node save --node-id <nodeId> --metadata '<json>' -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `--content <content>` - Code content (inline string)
- `--content-file <path>` - Path to file containing code content
- `--metadata <json>` - Full task configuration metadata as JSON string (required for most updates)
- `--image-name <name>` - Docker image name
- `--image-id <id>` - Docker image ID
- `--language <lang>` - Spark language (spark only)
- `--spark-version <ver>` - Spark version (spark only)
- `--data-outputs <spec>` - Task data outputs config. Accepts JSON array or shorthand notation (see `node create` for format). When provided without `--metadata`, automatically fetches and merges with the existing draft metadata
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
# Save code from file with existing metadata
bytedcli dorado node save --node-id NxyzABC --content-file ./script.py --metadata '{"name":"demo","type":"python","configuration":{...}}' --region boei18n

# Update data outputs to a partitioned Hive table (shorthand)
bytedcli dorado node save --node-id NxyzABC --data-outputs 'dp_compliance.demo_table:date=${date},ns=sg' --region sg

# Update data outputs with multiple entries separated by ;
bytedcli dorado node save --node-id NxyzABC --data-outputs 'dp_compliance.demo_table:date=${date},ns=sg;other' --region sg
```

---

### node submit

Submit (commit and deploy) a python/notebook/spark node without approval fields. Defaults to auto-release.

```bash
bytedcli dorado node submit --node-id <nodeId> --project-id <projectId> -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `-p, --project-id <projectId>` - Project ID (required)
- `--message <message>` - Commit message
- `--no-auto-release` - Do not auto-release after commit
- `--no-skip-commit-pipeline` - Do not skip commit pipeline checks
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado node submit --node-id NxyzABC --project-id 458 --message "deploy via bytedcli" --region boei18n
```

---

### node submit-approval

Submit (commit and deploy) a python/notebook/spark node with approval fields. Defaults to auto-release.

```bash
bytedcli dorado node submit-approval --node-id <nodeId> --project-id <projectId> -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `-p, --project-id <projectId>` - Project ID (required)
- `--message <message>` - Commit message
- `--no-auto-release` - Do not auto-release after commit
- `--no-skip-commit-pipeline` - Do not skip commit pipeline checks
- `--review-policy-id <id>` - Review policy ID (required; must be explicitly provided by the caller for the current project)
- `--review-users <users>` - Comma-separated reviewer usernames (required; must be explicitly provided by the caller for the current project)
- `--baseline-ids <ids>` - Comma-separated baseline IDs
- `--custom-alarm-rule-ids <ids>` - Comma-separated alarm rule IDs
- `--agent-config <json>` - Agent config JSON string
- `-r, --region <region>` - Dorado region (default: "cn")

**Note:** `review-policy-id` and `review-users` vary by project. Do not infer them from project defaults; ask the user to provide both values explicitly.
Use this dedicated command because the approval payload is page-shaped and sensitive to field presence/semantics; do not emulate it with plain `node submit` plus extra approval fields.

**Example:**

```bash
bytedcli dorado node submit-approval --node-id NxyzABC --project-id 458 --message "deploy via bytedcli" \
  --review-policy-id 33 --review-users "demo.user1,demo.user2" --custom-alarm-rule-ids 17587 --baseline-ids 33 --region boei18n
```

---

### node relation

Query nodeId → taskId mapping. Use the returned taskId with task-related APIs (`task get`, `instance list`, etc.).

```bash
bytedcli dorado node relation --node-id <nodeIds> -r <region>
```

**Options:**

- `--node-id <nodeIds>` - Node ID(s), comma-separated for batch query (required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
# Single query
bytedcli dorado node relation --node-id NxyzABC --region boei18n

# Batch query
bytedcli dorado node relation --node-id NxyzABC,NxyzDEF --region boei18n -j
```

---

### node history

List node commit history (production versions). Returns version number, commitId, creator, update time, and commit message.

```bash
bytedcli dorado node history --node-id <nodeId> -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `--page <page>` - Page number (default: 1)
- `--size <size>` - Page size (default: 30)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado node history --node-id NxyzABC --region cn
bytedcli dorado node history --node-id NxyzABC --page 1 --size 10 --region cn
```

---

### node rollback

Rollback node draft to a historical production version. Only affects draft, not online production.

```bash
bytedcli dorado node rollback --node-id <nodeId> --commit-id <commitId> -r <region>
bytedcli dorado node rollback --node-id <nodeId> --latest -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node ID (required)
- `--commit-id <commitId>` - Commit ID to rollback to (mutually exclusive with `--latest`)
- `--latest` - Rollback to the latest production version (mutually exclusive with `--commit-id`)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Rollback to a specific version
bytedcli dorado node rollback --node-id NxyzABC --commit-id C61P1ztyn0R6dknxP --region cn

# Quick rollback to latest production version
bytedcli dorado node rollback --node-id NxyzABC --latest --region cn
```

**Note:** `--commit-id` and `--latest` are mutually exclusive. After rollback, submit again with `node submit` to deploy to production.

---

### node rename

Rename an IDE node by its `nodeUid`. Calls `POST /datalab/v1/ide/nodes/{nodeUid}/rename`. Works for any node type (python / notebook / spark / HSQL / etc.) — only the display name is changed; code and scheduling config are untouched.

```bash
bytedcli dorado node rename --node-id <nodeId> --name <newName> -r <region>
```

**Options:**

- `--node-id <nodeId>` - Node UID, e.g. `NxyzABC` (required)
- `--name <name>` - New display name (required, trimmed)
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
bytedcli dorado node rename --node-id NxyzABC --name demo_renamed_task --region cn
```

---

### node move

Move an IDE node under another parent URI. Calls `POST /datalab/v1/ide/nodes/{nodeUid}/move` with body `{"parentUri":"..."}`. The command is dry-run by default so callers can review the target parent URI before changing the IDE tree.

```bash
bytedcli dorado node move --node-id <nodeId> --parent-uri <parentUri> -r <region> [--dry-run] [--yes]
```

**Options:**

- `--node-id <nodeId>` - Node UID, e.g. `NxyzABC` (required)
- `--parent-uri <uri>` - Target parent directory URI, e.g. `task:///f123/NdemoDir` (required). Use URIs from `dorado tree-nodes children` / `folder create`.
- `--dry-run` - Preview the request payload without calling the API (default behavior when `--yes` is absent; if both flags are present, dry-run wins)
- `--yes` - Actually submit the move
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Preview first
bytedcli dorado node move --node-id NxyzABC --parent-uri "task:///f123/NdemoDir" --region mycis

# Submit after reviewing the target URI
bytedcli dorado node move --node-id NxyzABC --parent-uri "task:///f123/NdemoDir" --region mycis --yes
```

---

### node delete

Move an IDE node to Dorado's recoverable recycle bin through
`POST /datalab/v1/ide/nodes/{nodeUid}/remove`. This is a logical deletion, not physical erasure.
The command is dry-run by default and accepts exactly one selector:

```bash
bytedcli dorado node delete --node-id <nodeId> --region <region> [--dry-run] [--yes]
bytedcli dorado node delete --task-id <taskId> --project-id <projectId> \
  --region <region> [--dry-run] [--yes]
```

**Options and safety rules:**

- `--node-id <nodeId>` - Explicit IDE node UID; the CLI resolves and verifies its task relation.
- `--task-id <taskId>` with `--project-id <projectId>` - Resolve a supported task to nodeUid.
- `--dry-run` - Preview without deleting; wins when combined with `--yes`.
- `--yes` - Move the node to recycle after target verification.
- `--skip-relation-verify` - Allow an unverified task match to be inspected in dry-run only.
- Both selectors support `hsql`, `doris_sql`, `python`, `notebook`, and `spark`.
- Formal deletion requires node-relations `verified=true`.
- JSON output uses `accepted` plus `deletion_mode: "recycle"`; it reports request acceptance, not
  physical erasure.

```bash
# Preview and then delete an explicit node
bytedcli dorado node delete --node-id <node-id> --region <region>
bytedcli dorado node delete --node-id <node-id> --region <region> --yes

# Resolve a supported task and preview the verified target
bytedcli dorado node delete \
  --task-id <task-id> \
  --project-id <project-id> \
  --region <region>
```

---

### task rename

Rename a Dorado task. Same backend as `node rename` (operates on the IDE node), exposed from the task viewpoint so callers can pass either the IDE `nodeUid` directly or the numeric `taskId` + `projectId` and let the CLI resolve `nodeUid` via `resolveNodeUidFromTask`.

```bash
# A) Pass nodeUid directly (skips resolution)
bytedcli dorado task rename --node-id <nodeId> --name <newName> -r <region>

# B) Pass numeric taskId + projectId (auto-resolves nodeUid)
bytedcli dorado task rename --task-id <taskId> --project-id <projectId> --name <newName> -r <region>
```

**Options:**

- `--name <name>` - New task display name (required, trimmed)
- `--node-id <nodeId>` - Node UID; when provided, taskId resolution is skipped
- `--task-id <taskId>` - Numeric task ID; requires `--project-id`
- `--project-id <projectId>` - Project ID; required with `--task-id`
- `--skip-relation-verify` - Skip `node-relations` verification when resolving `nodeUid`
- `-r, --region <region>` - Dorado region (default: "cn")

**Example:**

```bash
# Known nodeUid
bytedcli dorado task rename --node-id NxyzABC --name demo_renamed_task --region cn

# Only have the numeric taskId from a Dorado URL
bytedcli dorado task rename --task-id 120933017 --project-id 8026 --name demo_renamed_task --region cn
```

If resolution returns no `nodeUid` (e.g., wrong project / region), the command throws `DORADO_NODE_UID_NOT_FOUND` — verify `--region`, `--project-id`, `--task-id`, and auth.

`--node-id` and `--task-id` / `--project-id` are mutually exclusive. Mixing them raises `DORADO_INPUT_ERROR` to prevent silently renaming the wrong task when the two inputs disagree. Pass either form alone.

---

### image list

List available Docker images for a project. Use the returned `id` + `name` when configuring the node image via `node create/save --image-name/--image-id`.

```bash
bytedcli dorado image list --project-id <projectId> -r <region>
```

**Options:**

- `-p, --project-id <projectId>` - Project ID (required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `-k, --keyword <keyword>` - Filter by image name keyword

**Example:**

```bash
bytedcli dorado image list --project-id 458 --region cn -k demo_image -j
```

---

### node resolve-uid

When a DataLeap URL or workflow only provides a numeric **taskId** but you need the IDE **nodeUid** (`N...` for `dorado node get` / `node save`), call this first. It fetches the task name/type via `get-task`, then walks the project tree via `tree-nodes children` with a `name+type` filter — the backend returns only the single direct child on the path to a match, so the command drills down a single path to the matching leaf node, then verifies with `node-relations`.

```bash
bytedcli dorado node resolve-uid --project-id <projectId> --task-id <taskId> -r <region>
```

**Options:**

- `-p, --project-id <projectId>` - Project ID (required)
- `--task-id <taskId>` - Numeric task ID (required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--skip-relation-verify` - Skip node-relations verification (not recommended)

**Example:**

```bash
bytedcli dorado node resolve-uid --project-id 458 --task-id 100274211 --region boei18n -j
```

If this returns no `nodeUid`, verify `--region`, `--project-id`, `--task-id`, and auth.

---

### adhoc exec

Execute an ad-hoc SQL query via the Dorado ad-hoc query API. For Hive SQL, use a pre-existing **ad-hoc query task** (临时查询) as the execution carrier — create one in Dorado (Project > Ad-hoc Query > New Query, 即"临时查询"), and it is recommended to switch the engine to Spark on the query page before saving. For Doris SQL, use a `doris_sql` task as the execution carrier; the CLI detects that type and submits through the Doris IDE debug endpoint. The task only needs to be created once; dc/cluster/queue are inherited from the saved configuration when applicable. Default task IDs can be supplied through `DORADO_EXEC_TASK_ID` and Doris-specific `DORADO_DORIS_EXEC_TASK_ID`. In default/auto mode, ad-hoc task-id defaults use `DORADO_EXEC_TASK_ID`; `DORADO_DORIS_EXEC_TASK_ID` is used only when `--engine-type doris_sql` is explicitly set.

**Safety check:** Before executing, the command verifies that the carrier task is **not** an online production task. If the task is online, execution is blocked to prevent unintended modifications to production task state. Use `--force` to bypass this check (not recommended).

With `--wait`, polls until completion and fetches the result (first 10 rows previewed in text mode; full data in JSON mode). Failed runs also include a `note` field / `Note:` line when Dorado run logs expose detailed engine or SQL errors. With `-o`, downloads the full result as CSV.

```bash
bytedcli dorado adhoc exec [sql] [options]
```

**Arguments:**

- `sql` - SQL query (or provide via stdin)

**Options:**

- `--task-id <taskId>` - Carrier task ID. Use an ad-hoc query task for Hive SQL or a `doris_sql` task for Doris SQL. Default/auto mode reads `DORADO_EXEC_TASK_ID`; explicit `--engine-type doris_sql` reads `DORADO_DORIS_EXEC_TASK_ID` first and then falls back to `DORADO_EXEC_TASK_ID`.
- `--project-id <projectId>` - Project ID (auto-detected if omitted)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--dc <dc>` - Data center
- `--cluster <cluster>` - Cluster
- `--queue <queue>` - Queue
- `--engine-type <type>` - Engine type (default: "auto")
- `--username <username>` - Owner username (defaults to task owner)
- `--date <date>` - Schedule date in YYYYMMDD format (defaults to yesterday)
- `-o, --output <path>` - Download result CSV to file
- `--no-wait` - Submit only, do not wait for completion
- `--timeout <seconds>` - Poll timeout in seconds (default: 600)
- `--force` - Bypass online-task safety check (use with caution)

**Examples:**

```bash
# Execute and display results (default: waits for completion)
bytedcli dorado adhoc exec "SELECT count(*) FROM db.table" --task-id 100274211 --region boei18n

# SQL from stdin
echo "SELECT * FROM db.table LIMIT 10" | bytedcli dorado adhoc exec --task-id 100274211 --region boei18n

# Download full result as CSV
bytedcli dorado adhoc exec "SELECT * FROM db.table LIMIT 10" --task-id 100274211 -o result.csv

# Doris SQL using a doris_sql carrier task
DORADO_DORIS_EXEC_TASK_ID=123456789 bytedcli dorado adhoc exec "SELECT 1" --engine-type doris_sql --project-id 123 --region cn --no-wait

# Async: submit only, get debugId for later status/result queries
bytedcli dorado adhoc exec "复杂SQL" --task-id 100274211 --no-wait

# Using .dorado.env defaults (auto-loaded from ~/.local/share/bytedcli/data/.dorado.env or ./.dorado.env)
# DORADO_EXEC_TASK_ID=100274211
# DORADO_DORIS_EXEC_TASK_ID=123456789  # only used with --engine-type doris_sql
bytedcli dorado adhoc exec "SELECT 1" --region boei18n

# JSON output (includes full result data)
bytedcli dorado adhoc exec "SELECT * FROM db.table" --task-id 100274211 --json
```

When a waited execution fails, text mode prints:

```text
Note: <detailed error extracted from run log>
```

JSON mode returns the same detail in `errorMessage`.

---

### adhoc status

Get ad-hoc execution status by debug ID. Use to check whether an async `adhoc exec` has completed. Failed runs also include a `note` field / `Note:` line when Dorado run logs expose detailed engine or SQL errors.

```bash
bytedcli dorado adhoc status [options]
```

**Options:**

- `--debug-id <debugId>` - Debug ID (from `adhoc exec` output)
- `--task-id <taskId>` - Task ID (or `DORADO_EXEC_TASK_ID`)
- `--project-id <projectId>` - Project ID (auto-detected if omitted)
- `-r, --region <region>` - Dorado region (default: "cn")

**Status values:** `pending`, `running`, `succeed`, `failed`, `aborted`

**Example:**

```bash
bytedcli dorado adhoc status --debug-id 12977673 --task-id 119886373
```

When status is `failed`, JSON output includes:

```json
{
  "debugId": 12977673,
  "status": "failed",
  "statusCode": 5,
  "note": "2026-06-05T14:18:35.904 ERROR ..."
}
```

---

### adhoc result

Get ad-hoc execution result by debug ID. Displays as a table (text mode) or returns full data (JSON mode). Use `-o` to download as CSV.

```bash
bytedcli dorado adhoc result [options]
```

**Options:**

- `--debug-id <debugId>` - Debug ID (from `adhoc exec` output)
- `--task-id <taskId>` - Task ID (or `DORADO_EXEC_TASK_ID`)
- `--project-id <projectId>` - Project ID (auto-detected if omitted)
- `-r, --region <region>` - Dorado region (default: "cn")
- `-o, --output <path>` - Download result as CSV to file

**Examples:**

```bash
# Display result (first 10 rows in text mode)
bytedcli dorado adhoc result --debug-id 12977673 --task-id 119886373 --region cn

# Download as CSV
bytedcli dorado adhoc result --debug-id 12977673 --task-id 119886373 -o result.csv

# Full data in JSON
bytedcli dorado adhoc result --debug-id 12977673 --task-id 119886373 --json
```

---

### adhoc log

Get ad-hoc execution run logs by debug ID. Text mode prints the log body to stdout; JSON mode returns the log plus pagination metadata. Use `--output` to save the log body to a file.

```bash
bytedcli dorado adhoc log [options]
```

**Options:**

- `--debug-id <debugId>` - Debug ID (from `adhoc exec` output)
- `--task-id <taskId>` - Task ID (or `DORADO_EXEC_TASK_ID`); used to auto-detect projectId and nodeUid
- `--project-id <projectId>` - Project ID (auto-detected if omitted and taskId is provided)
- `--node-id <nodeId>` - Dorado IDE nodeUid; omit to auto-resolve from `--task-id`
- `-r, --region <region>` - Dorado region (default: "cn")
- `--offset <offset>` - Log offset (default: 0)
- `--length <length>` - Log page length (default: 10000)
- `-o, --output <path>` - Write log text to file

**Examples:**

```bash
# Print one page of logs
bytedcli dorado adhoc log --debug-id 12977673 --task-id 119886373 --region cn

# Continue from a previous nextOffset value
bytedcli dorado adhoc log --debug-id 12977673 --task-id 119886373 --offset 10000

# Save logs to a file
bytedcli dorado adhoc log --debug-id 12977673 --task-id 119886373 -o run.log

# Skip task-to-nodeUid resolution when nodeUid is known
bytedcli dorado adhoc log --debug-id 12977673 --project-id 123 --node-id NsampleNode
```

---

### adhoc history

List ad-hoc execution history for a task.

```bash
bytedcli dorado adhoc history [options]
```

**Options:**

- `--task-id <taskId>` - Task ID (or `DORADO_EXEC_TASK_ID`)
- `--project-id <projectId>` - Project ID (auto-detected if omitted)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--page <page>` - Page number (default: 1)
- `--page-size <size>` - Page size (default: 20)
- `--only-mine` - Show only my executions

**Examples:**

```bash
# List ad-hoc history for a task
bytedcli dorado adhoc history --task-id 119886373

# Show only my executions
bytedcli dorado adhoc history --task-id 119886373 --only-mine

# JSON output
bytedcli dorado adhoc history --task-id 119886373 --json
```

---

### flink monitor get

Get monitor URLs (Grafana metrics, ByteLake monitor, Flink Web UI, etc.) for a Dorado realtime streaming (Flink) task.

```bash
bytedcli dorado flink monitor get [options]
```

**Options:**

- `--task-id <taskId>` - Dorado task ID (positive integer, required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Text output (default)
bytedcli dorado flink monitor get --task-id 100274211 --region cn

# JSON output
bytedcli dorado flink monitor get --task-id 100274211 --region sg -j
```

The response includes `metricMonitorUrl`, `bytelakeMonitorUrl`, `customMonitorUrl`, `dtopMonitorUrl`, `yarnAppUrl` (Flink Web UI proxy), and `paimonMetricUrl`. Any field may be `null` when the underlying integration is not configured for the task.

---

### flink operation-log list

List operation logs (start / restart / stop / edit / etc.) of a Dorado realtime streaming (Flink) task. Use the `log_id` of `start` / `restart` entries with `flink operation-log get` to fetch the event timeline.

```bash
bytedcli dorado flink operation-log list [options]
```

**Options:**

- `--task-id <taskId>` - Dorado task ID (positive integer, required)
- `-r, --region <region>` - Dorado region (default: "cn")
- `--page <page>` - Page number (default: 1)
- `--page-size <size>` - Page size (default: 20)

**Examples:**

```bash
# Default page
bytedcli dorado flink operation-log list --task-id 100274211 --region cn

# Custom pagination
bytedcli dorado flink operation-log list --task-id 100274211 --region sg --page 1 --page-size 20

# JSON output
bytedcli dorado flink operation-log list --task-id 100274211 --region sg -j
```

Each log entry contains `logId`, `typeAlias` (e.g. `start`, `restart`, `stop`), `message`, `user`, `createTime`, and `version`. Total count is returned only when the backend exposes it.

---

### flink operation-log get

Get the event timeline (with the Flink Web UI link) of a single Dorado realtime task operation log. Only `start` / `restart` typed logs carry events; for other log types the response will report empty events.

```bash
bytedcli dorado flink operation-log get [options]
```

**Options:**

- `--log-id <logId>` - Operation log ID from `flink operation-log list` (positive integer, required)
- `-r, --region <region>` - Dorado region (default: "cn")

**Examples:**

```bash
# Text output (default)
bytedcli dorado flink operation-log get --log-id 83863872 --region cn

# JSON output
bytedcli dorado flink operation-log get --log-id 83863872 --region sg -j
```

The response includes `flinkWebUi` (Flink Web UI proxy URL) and an `events` array. Each event contains `message`, `type`, `createTime`, `applicationId`, `applicationUrl`, `logUrl`, and `streamInstanceId`.

---

## Task Types

| Type                | Description                                                                 | Managed via                    |
| ------------------- | --------------------------------------------------------------------------- | ------------------------------ |
| `hsql`              | Hive SQL task - runs SQL queries                                            | `task` / `task-draft` commands |
| `global_hsql`       | Global Hive SQL batch task - create shell via `/task/create`                | `task` / `task-draft` commands |
| `fsql`              | Flink SQL task - runs streaming SQL queries                                 | `task` / `task-draft` commands |
| `stream_sql`        | Stream SQL task - create shell via `/realtime/create`, then write config    | `task` / `task-draft` commands |
| `java-flink`        | Java Flink task - create shell via `/realtime/create`, then write config    | `task` commands                |
| `python`            | Python script task - runs Python code with Docker image                     | `node` commands                |
| `notebook`          | Jupyter Notebook task - interactive notebook execution                      | `node` commands                |
| `spark`             | Spark task (PySpark/Java/Scala) - runs Spark jobs with Docker image         | `node` commands                |
| `mysql->hive`       | DTS task - syncs data from MySQL to Hive                                    | `task` commands                |
| `hive->bmq`         | DTS task - syncs data from Hive to BMQ                                      | `task` commands                |
| `hive->clickhouse`  | DTS task - syncs data from Hive to ClickHouse                               | `task` commands                |
| `common-dts-batch`  | Generic DTS batch task                                                      | `task` commands                |
| `common-dts-stream` | Generic DTS streaming task (e.g. bmq->hive); created via `/realtime/create` | `task` commands                |

## Instance Status

| Status    | Description            |
| --------- | ---------------------- |
| `pending` | Waiting to run         |
| `running` | Currently executing    |
| `success` | Completed successfully |
| `failed`  | Failed execution       |

## Authentication

The CLI uses JWT authentication via SSO. Ensure you are logged in:

```bash
bytedcli auth login
```

## Global resource library & function library (UDF jars)

`dorado resource` and `dorado function` operate on the **global** resource /
function library — the same surface as the `https://data.bytedance.net/dorado/settings/resource-file`
and `…/dorado/settings/functions` pages. They are **distinct** from
`dorado tree-nodes resource` / `dorado tree-nodes function`, which target
project-internal IDE tree nodes (require `--project-id`/`--engine-id`/etc. and
only register existing hdfsPath / SCM resources).

Endpoints (cn region):

- `POST /dorado_api/function/resource` (multipart) — upload a local jar.
- `POST /dorado_api/function/resource/{id}` (multipart) — update a resource;
  send `file=null` (text part) to edit metadata only, or a real file part to
  replace the jar.
- `GET /dorado_api/function/resource[?type=0]` — list resources.
- `GET /dorado_api/function/resource/{id}` — resource detail (includes
  `fileLink` pointing to TOS).
- `POST /dorado_api/function` — create one UDF/UDTF/UDAF bound to a resource.
- `POST /dorado_api/function/{id}` — update a function (same body shape as
  create; the path `id` identifies the row).
- `GET /dorado_api/function?resourceId=…` — list functions bound to a resource.
- `GET /dorado_api/function/{id}` — function detail.

Auth: all endpoints under the `/dorado_api/function/resource` and
`/dorado_api/function` prefixes (i.e. every endpoint listed above) reject a
plain ByteCloud `x-jwt-token` (silent `code:-1, message:""`). They require a
Dataleap-issued JWT in `x-dataleap-jwt-token`, exchanged from the ByteCloud SSO
JWT via the Dorado `/user/jwt` issuer (reused from `@/api/dorado#fetchDataleapJwt`).
No browser session cookies are required — same pattern as `src/api/manta/client.ts`.

Type / enum mappings currently captured (extend after a new browser capture):

- Resource `--type`: `jar` → `0`. Other values (zip, file, scm, image, thrift)
  are reserved on the page but their numeric encoding is not yet captured.
- Function `--function-type`: `udf` → `0`, `udtf` → `1`, `udaf` → `2`.
- Function `--process-type`: `jar` → `1`. SCM resources are not yet captured.
- Function `--engine-type`: `hive` → `0`. Spark/Flink not yet captured.

End-to-end example:

```bash
# 1) Make sure the ByteCloud SSO JWT is fresh (one-time setup).
bytedcli auth login

# 2) Upload a local jar to the global resource library.
bytedcli dorado resource upload \
  --file ./demo-udf.jar \
  --name demo_udf \
  --description "demo udf" \
  -r cn

# 3) Create a UDF in the global function library, bound to the resource.
bytedcli dorado function create \
  --resource-id 100052827 \
  --name demo_udf \
  --class-name com.example.demo.HelloUDF \
  --function-type udf \
  -r cn

# 4) Verify the binding.
bytedcli dorado function list --resource-id 100052827 -r cn

# 5) Update resource metadata only (omit --file) or replace the jar (pass --file).
bytedcli dorado resource update --id 100052827 --name demo_udf --description "updated" -r cn

# 6) Update the function (same fields as create; --id locates the row).
bytedcli dorado function update --id 13333 --resource-id 100052827 \
  --name demo_udf --class-name com.example.demo.HelloUDF --function-type udf -r cn
```
