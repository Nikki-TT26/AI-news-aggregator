---
name: "aeolus-dataset-manager"
description: "管理 Aeolus 风神平台数据集：创建、复制、修改、删除、查看。支持国内（cn）和海外（sg）机房。当用户需要操作 Aeolus 数据集或提到风神平台时调用。"
---

# Aeolus Dataset Manager

自动化管理 Aeolus（风神）平台数据集，通过 `scripts/aeolus_api.py` 完成所有操作。支持创建、复制、修改、删除和查看数据集。

**支持区域**：
- **国内 (cn)**：`https://data.bytedance.net/aeolus`（默认）
- **海外 SG (sg)**：`https://aeolus-sg.tiktok-row.net`

## 前置条件

1. **Python 虚拟环境（首次使用必须执行）**：脚本依赖 `requests`、`pycookiecheat`、`pyyaml` 等非标准库，使用 `scripts/` 目录下的 venv 隔离管理。首次使用前需要初始化虚拟环境：
   ```bash
   cd scripts
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   后续所有 Python 命令都必须通过 venv 执行：
   ```bash
   scripts/.venv/bin/python scripts/aeolus_api.py detect
   ```
   或者先激活再执行：
   ```bash
   source scripts/.venv/bin/activate && python scripts/aeolus_api.py detect
   ```
2. **零配置即可使用**：大部分配置（`owner`、`app_id`、`parent_id`、`yarn_name`）都支持自动探测，无需手动配置。脚本会依次尝试：config.yaml 配置 → API 自动探测 → 代码默认值。
3. **Token 自动获取**：脚本会自动从 Chrome 浏览器获取 Cookie，然后访问 Aeolus 页面提取 `x-titan-token`（依赖 `pycookiecheat`，已包含在 `requirements.txt` 中，仅支持 macOS）。首次使用时系统可能弹出 Keychain 密码确认框，授权即可。Token 按区域分别缓存：国内 `scripts/token.txt`，海外 `scripts/token_sg.txt`。
4. **手动设置 Token（备选）**：如果自动获取失败（如非 macOS 或 Chrome 未登录），可手动将 Token 写入对应文件（国内 `scripts/token.txt`，海外 `scripts/token_sg.txt`）。获取方式：Chrome 打开对应区域的 Aeolus 页面 → F12 → Network → 任意 `/aeolus/api/` 请求 → 复制 Request Headers 中的 `x-titan-token` 值。
5. **Token 有效期**：`x-titan-token` JWT 约 7 天过期。过期后脚本会自动从 Chrome 刷新，或调用 `client.refresh_token()` 手动刷新。
6. **URL 直接使用**：用户可以直接提供 Aeolus 链接，脚本会自动从 URL 中提取 `appId`、`dataSetId` 和 `region`（根据域名判断）。支持的 URL 格式：
   - 国内：`https://data.bytedance.net/aeolus/pages/dataManage/?appId=1006036`
   - 海外：`https://aeolus-sg.tiktok-row.net/pages/dataManage/?appId=802699`

## 用户配置

SKILL 使用 `scripts/config.yaml` 文件存储用户自定义配置。**所有配置项均为可选**，留空时脚本会自动探测。

配置文件路径：`scripts/config.yaml`

**配置生效规则**：参数调用时显式传入 > config.yaml（按 region 分组） > API 自动探测 > 代码硬编码默认值

**自动探测机制**：
- **`owner`**：留空时自动调用 `current_user` API 获取当前登录用户的 `emailPrefix`
- **`app_id`**：可从用户提供的 Aeolus URL 中的 `?appId=` 参数提取，或传入 `AeolusClient(app_id=xxx)`，或从 `regions.<region>.app_id` 读取
- **`parent_id`**：优先从 `regions.<region>.parent_id` 读取，留空时自动调用 `dataSetFolderTreeV2` API 获取文件夹树第一个节点 ID
- **`yarn_name`**：优先从 `regions.<region>.yarn_name` 读取，留空时自动调用 `getUserYarnList` API 获取第一个可用 Yarn 队列

```yaml
# ===== 默认区域 =====
default_region: "cn"              # cn（国内）/ sg（海外 SG）

# ===== 用户信息（通用，不区分 region）=====
user:
  owner: "zhanfurong"             # ← 改为你的邮箱前缀（留空则自动获取）

# ===== 按区域分组的配置 =====
# 每个区域独立配置，留空的项会通过 API 自动探测。
regions:
  cn:
    app_id: 1006036               # Aeolus 应用 ID
    parent_id: 81004              # 数据集文件夹 ID
    yarn_name: "root.xxx"         # Yarn 队列
    cluster: "cn"                 # nodeConf.clusterName
    group_id: 8817                # 应用分组 ID
    group_name: "default"         # 应用分组名
  sg:
    app_id: 802699
    parent_id: 36573              # Trae看板文件夹
    yarn_name: "root.yyy"
    cluster: "sg"
    group_id: 3331
    group_name: "TRAE-Code AI"

# ===== 同步配置（通用默认值）=====
sync:
  frequency: "daily"              # 调度频率: daily / hourly
  schedule_time: "00:00"          # 调度时间
  ttl: 7                          # 数据保留天数

# ===== 数据源配置（通用）=====
datasource:
  type: "hive"                    # 数据源类型
```

## 核心文件

- `scripts/aeolus_api.py` — API 封装和数据集操作逻辑
- `scripts/config.yaml` — 默认配置（app_id、yarn 队列、调度频率等）
- `scripts/requirements.txt` — Python 依赖列表（venv 初始化时使用）
- `scripts/token.txt` — 国内 x-titan-token（自动获取或手动填入，已 gitignore）
- `scripts/token_sg.txt` — 海外 SG x-titan-token（自动获取或手动填入，已 gitignore）

## SQL 日期变量

风神 SQL 中使用以下系统日期变量实现动态日期查询（**不要使用 Jinja 模板语法 `{{ ds }}`**）：

| 变量 | 格式 | 示例 |
|------|------|------|
| `${DATE}` | yyyy-MM-dd | 2025-05-17 |
| `${date}` | yyyyMMdd | 20250526 |
| `${DATE+n}` / `${DATE-n}` | yyyy-MM-dd，往后(+)/往前(-)n天 | `${DATE-1}` = 昨天 |
| `${date+n}` / `${date-n}` | yyyyMMdd，往后(+)/往前(-)n天 | `${date-1}` = 昨天 |

**示例**：
```sql
-- 分区字段为 date (yyyyMMdd 格式)
WHERE date = '${date}'

-- 分区字段为 p_date (yyyy-MM-dd 格式)
WHERE p_date = '${DATE}'
```

## 核心流程

1. 识别用户意图：创建数据集、复制数据集、修改数据集、删除数据集、查看信息等。
2. **如果用户提供了 Aeolus 链接**，使用 `parse_aeolus_url(url)` 从 URL 中提取 `data_set_id`、`app_id` 和 `region`（根据域名自动判断 cn/sg）。也可用 `extract_dataset_id(url_or_id)` 仅提取 ID。
3. 使用 `scripts/aeolus_api.py` 中的 `AeolusClient` 和 `DatasetEditor` 类完成操作。
4. **创建数据集**使用 `POST /dataSetV2`（创建后状态为"初始化"），`create_new(publish=True)` 可在创建后自动发布上线。
5. **修改已有数据集**使用 `PUT /dataSetV2`（需要先获取编辑锁）。
6. **发布上线**通过 `PUT /dataSetV2` 实现，`update(publish=True)` 会自动发布。
7. **操作完成后，将数据集链接展示给用户**。`create_new()`、`create_from()`、`update()` 会自动打印链接。

## 典型工作流

### 工作流 1: 创建新数据集

```python
import sys
sys.path.insert(0, '.trae/skills/aeolus-dataset-manager/scripts')
from aeolus_api import AeolusClient, DatasetEditor, extract_dataset_id

client = AeolusClient()                # 国内（默认 region='cn'）
# client = AeolusClient(region='sg')   # 海外 SG
editor = DatasetEditor.create_new(
    client,
    name="my_new_dataset",
    query="SELECT id, name, date FROM my_db.my_table WHERE date = '${date}'",
    publish=True,  # 创建后自动发布（会等待并自动重试）
)
print(f"新数据集 ID: {editor.data_set_id}")
```

### 工作流 2: 复制已有数据集创建新的

```python
client = AeolusClient()
source_id = extract_dataset_id("https://data.bytedance.net/aeolus/pages/dataManage/detail/5428964?appId=1006036&belong=1")
editor = DatasetEditor.create_from(
    client,
    source_dataset_id=source_id,
    new_name="my_copied_dataset",
    new_query=None,               # None=复用源 SQL；传入新 SQL 则替换
    publish=True,                 # 创建后自动发布（会自动重试）
)
print(f"新数据集 ID: {editor.data_set_id}")
```

### 工作流 3: 修改已有数据集并发布上线

```python
client = AeolusClient()
editor = DatasetEditor(client, data_set_id=5428964)
editor.update(
    new_query="SELECT id, name, status, date FROM my_db.my_table WHERE date = '${date}'",
    new_name="updated_dataset_name",
    publish=True,                 # True=修改并发布（默认），False=仅保存草稿
)
```

### 工作流 4: 仅修改不发布

```python
client = AeolusClient()
editor = DatasetEditor(client, data_set_id=5428964)
editor.update(
    new_query="SELECT ...",
    publish=False,                # 仅保存草稿，不发布
)
```

### 工作流 5: 参照已有数据集创建新的（非复制）

从已有数据集获取字段定义作为 `source_fields`，跳过耗时的 SQL Schema 解析，同时继承源数据集的维度/指标类型。可在获取字段时过滤掉不需要的字段。

```python
client = AeolusClient()
source = DatasetEditor(client, 5428964)
source_fields = [f for f in source.get_node_conf()[0].get("fields", []) if f["name"] != "unwanted_field"]

editor = DatasetEditor.create_new(
    client,
    name="new_dataset_based_on_source",
    query="SELECT ... (modified SQL without unwanted_field)",
    source_fields=source_fields,
    source_dataset_id=5428964,
    schedule_time="02:00",
    publish=True,
)
```

### 工作流 6: 参照国内数据集在海外创建（跨区域）

跨区域参照时，使用 `source_client` 指定源区域的客户端，脚本会用源客户端读取维度/指标信息，用目标客户端创建新数据集。注意 SQL 中必须使用海外的库名。

```python
# 1. 分别创建 CN 和 SG 客户端
cn_client = AeolusClient(region='cn')
sg_client = AeolusClient(region='sg')

# 2. 从 CN 数据集获取字段定义
source = DatasetEditor(cn_client, 5492281)
source_fields = source.get_node_conf()[0].get("fields", [])

# 3. 在 SG 创建，传入 source_client 实现跨区域参照维度/指标类型
editor = DatasetEditor.create_new(
    sg_client,
    name="trae_chat_model_cost_di_sg",
    query="SELECT ... FROM ai_application_coding.xxx WHERE ...",  # 海外库名
    source_fields=source_fields,
    source_dataset_id=5492281,        # CN 数据集 ID
    source_client=cn_client,          # 跨区域时必须指定源客户端
    dim_met_overrides={               # 可选：微调维度/指标类型
        "some_field": {"mapType": 1},
    },
    publish=True,
)
```

也可以不用 `source_dataset_id`，改为手动用 `dim_met_overrides` 设置：
```python
editor = DatasetEditor.create_new(
    sg_client,
    name="trae_chat_model_cost_di_sg",
    query="SELECT ... FROM ai_application_coding.xxx WHERE ...",
    source_fields=source_fields,       # 只传 fields，不传 source_dataset_id
    dim_met_overrides={                # 手动指定哪些字段是指标
        "tokens_cnt": {"mapType": 1},
        "cost": {"mapType": 1},
    },
    publish=True,
)
```

### 工作流 7: 手动构造 source_fields 创建数据集（推荐）

当没有现成的风神数据集可以参照时，可以手动构造 `source_fields` 来跳过 SQL Schema 解析。**这是创建全新数据集的推荐方式**，因为 SQL Schema 解析可能非常耗时（>300s 甚至超时）。

**注意**：`prepType` 必须使用风神中间类型，`type` 保留原始 Hive 类型：
- Hive `bigint` → prepType `long`，type `bigint`
- Hive `int` → prepType `int`，type `int`
- Hive `double` → prepType `double`，type `double`
- Hive `float` → prepType `float`，type `float`
- Hive `string` → prepType `string`，type `string`
- Hive `timestamp` → prepType `timestamp`，type `timestamp`

```python
client = AeolusClient()

# 手动构造字段列表（type 保留 Hive 原始类型，prepType 使用风神中间类型）
source_fields = [
    {"name": "user_id", "type": "string", "prepType": "string",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "model_name", "type": "string", "prepType": "string",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "tokens_cnt", "type": "bigint", "prepType": "long",  # type 保留 bigint，prepType 用 long
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "cost", "type": "double", "prepType": "double",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "date", "type": "string", "prepType": "string",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
]

editor = DatasetEditor.create_new(
    client,
    name="my_dataset",
    query="SELECT user_id, model_name, tokens_cnt, cost, date FROM my_db.my_table WHERE date = '${date}'",
    source_fields=source_fields,
    publish=True,
)
```

可以用 `bytedcli hive detail <db> <table> --region cn --json` 查询 Hive 表 schema 获取字段名和类型，再手动构造 source_fields。

### 工作流 8: 删除数据集

删除前会自动检查可回收性和下游依赖，如果有下游看板/报表/数据集依赖，默认会阻止删除。

```python
client = AeolusClient()
editor = DatasetEditor(client, 5429028)
editor.delete()           # 安全删除（有下游依赖时会报错）
editor.delete(force=True) # 强制删除（忽略下游依赖）
```

### 工作流 9: 发起数据同步（回溯）

对已发布的数据集发起回溯（补历史数据），自动检查可回溯范围、队列配置、实例数，然后提交回溯任务。

```python
client = AeolusClient()
editor = DatasetEditor(client, data_set_id=5492281)

# 回溯指定日期范围（日期格式: yyyy-MM-dd）
editor.backfill(
    start_date="2026-04-20",
    end_date="2026-04-23",
)
```

高级用法：
```python
editor.backfill(
    start_date="2026-04-20",
    end_date="2026-04-23",
    queue_name="root.xxx",       # 可选：指定 Yarn 队列（默认用数据集配置的）
    max_parallelism=5,           # 可选：最大并行度（默认 5）
    skip_check=False,            # 可选：跳过检查
    wait=True,                   # True=等待提交完成（默认），False=异步返回 previewId
)
```

### 工作流 10: 查看数据集同步状态

```python
client = AeolusClient()
editor = DatasetEditor(client, data_set_id=5492281)

# 查看最近 30 天同步状态
sync_data = editor.get_sync_status()
for inst in sync_data.get("instanceList", []):
    print(f"{inst['bizTimePage']}  status={inst['syncStatus']}  rows={inst.get('tableSize', '-')}")

# 查看指定日期范围
sync_data = editor.get_sync_status(start_date="2026-04-01", end_date="2026-04-23")
```

## 主要功能

### 数据集创建

#### 创建新数据集
```python
editor = DatasetEditor.create_new(
    client,
    name="dataset_name",
    query="SELECT ...",
    owner="zhanfurong",          # 可选，默认读 config.yaml
    parent_id=81004,             # 可选，默认读 config.yaml
    yarn_name="root.xxx",        # 可选，默认读 config.yaml
    frequency="daily",           # 可选：daily / hourly
    schedule_time="00:00",       # 可选
    ttl=7,                       # 可选
    backtrack_start="2026-04-08",# 可选，默认昨天
    backtrack_end="2026-04-08",  # 可选
    publish=False,               # 可选，True=创建后自动发布
    source_dataset_id=None,      # 可选，源数据集 ID（配合 source_fields 使用）
    source_fields=None,          # 可选，源字段列表（跳过 SQL Schema 解析）
    dim_met_overrides=None,      # 可选，修改维度指标属性 {"字段名": {"mapType": 0或1}}
    source_client=None,          # 可选，跨区域参照时指定源区域的 AeolusClient
)
```

#### 从已有数据集复制
```python
editor = DatasetEditor.create_from(
    client,
    source_dataset_id=5428964,
    new_name="new_dataset_name",
    new_query=None,               # None=复用源 SQL
    owner="zhanfurong",
    parent_id=81004,
    schedule_time="01:00",        # 可选，调度时间
    dim_met_overrides={           # 可选，修改维度指标属性
        "field_name": {"mapType": 1},  # 0=维度, 1=指标
    },
    publish=True,                 # 可选，创建后自动发布（会自动重试）
)
```

### 数据集修改与发布

#### 修改并发布上线（默认）
```python
editor = DatasetEditor(client, data_set_id=5428964)
editor.update(
    new_query="SELECT ...",       # 可选：新 SQL
    new_name="new_name",          # 可选：新名称
    owner="new_owner",            # 可选
    yarn_name="root.xxx",         # 可选
    frequency="daily",            # 可选
    schedule_time="01:00",        # 可选（不传则保留已有配置）
    publish=True,                 # True=发布上线（默认），False=仅草稿
    source_fields=None,           # 可选：手动构造字段列表（跳过 SQL Schema 解析）
    dim_met_overrides={           # 可选：修改字段的维度/指标属性
        "field_name": {"mapType": 0},  # 0=维度, 1=指标
    },
)
```

### 数据集删除

```python
editor = DatasetEditor(client, data_set_id=5429028)
editor.delete()           # 安全删除（有下游依赖时报错）
editor.delete(force=True) # 强制删除（忽略下游依赖检查）
```

### 数据集查询

#### 列出数据集
```python
result = client.list_datasets(owner="zhanfurong")
```

#### 查看数据集详情
```python
editor = DatasetEditor(client, 5428964)
summary = editor.get_summary()
status = editor.get_status()
query = editor.get_query()
```

#### 辅助查询
```python
clusters = client.get_cluster_list()       # 可用集群
yarns = client.get_user_yarn_list()        # Yarn 队列
folders = client.get_folder_tree()          # 文件夹树
groups = client.get_resource_group_list()   # 资源组
```

### 刷新 Token
```python
client.refresh_token()                      # 从 Chrome 自动刷新
client.refresh_token(token_str="eyJ...")    # 手动传入新 token
```

## CLI 用法

> 所有命令必须通过 venv 执行。如果 venv 尚未创建，请先按"前置条件"初始化。

```bash
scripts/.venv/bin/python scripts/aeolus_api.py whoami                 # 查看当前用户
scripts/.venv/bin/python scripts/aeolus_api.py --region sg whoami     # 查看海外 SG 用户
scripts/.venv/bin/python scripts/aeolus_api.py list                   # 列出数据集
scripts/.venv/bin/python scripts/aeolus_api.py list zhanfurong        # 按 owner 筛选
scripts/.venv/bin/python scripts/aeolus_api.py info 5428964           # 数据集详情（支持 ID）
scripts/.venv/bin/python scripts/aeolus_api.py info "https://data.bytedance.net/aeolus/pages/dataManage/detail/5428964?appId=1006036&belong=1"  # 也支持 URL
scripts/.venv/bin/python scripts/aeolus_api.py status 5428964         # 数据集状态
scripts/.venv/bin/python scripts/aeolus_api.py detect                 # 自动探测当前用户的配置（owner, parent_id, yarn_name）
scripts/.venv/bin/python scripts/aeolus_api.py detect "https://data.bytedance.net/aeolus/pages/dataManage/?appId=1006036"  # 从 URL 探测配置
scripts/.venv/bin/python scripts/aeolus_api.py delete 5429028          # 删除数据集（支持 ID）
scripts/.venv/bin/python scripts/aeolus_api.py delete "https://data.bytedance.net/aeolus/pages/dataManage/detail/5429028?appId=1006036&belong=1"  # 也支持 URL
scripts/.venv/bin/python scripts/aeolus_api.py backfill 5492281 2026-04-20 2026-04-23  # 发起回溯
scripts/.venv/bin/python scripts/aeolus_api.py sync-status 5492281     # 查看同步状态
scripts/.venv/bin/python scripts/aeolus_api.py detect "https://aeolus-sg.tiktok-row.net/pages/dataManage/?appId=802699"  # 从海外 URL 探测配置
scripts/.venv/bin/python scripts/aeolus_api.py --region sg info 1451417  # 查看海外数据集
```

## 完整功能列表

### AeolusClient（底层 API）

- `AeolusClient(token_file, token_str, app_id, region)` - 构造函数，`region` 支持 `"cn"`（默认）和 `"sg"`，`app_id` 可从 URL 提取后传入
- `current_user()` - 获取当前用户信息
- `check_can_create()` - 检查创建权限
- `get_cluster_list()` - 获取可用集群列表
- `get_data_source_by_cluster(data_source_type, cluster_name)` - 获取集群下数据源
- `get_user_yarn_list()` - 获取 Yarn 队列列表
- `get_resource_group_list()` - 获取资源组列表
- `get_folder_tree()` - 获取文件夹树
- `get_dataset_tree(parent_id, kw)` - 获取数据集树
- `get_dataset_overview(data_set_id)` - 获取数据集概览
- `get_dataset_model_info(data_set_id)` - 获取数据集完整配置
- `get_all_dataset_info(data_set_id)` - 获取数据集全部信息（含版本）
- `get_table_schema_from_sql(query, ...)` - 提交 SQL 解析任务
- `get_table_schema_from_sql_result(query, preview_id, ...)` - 轮询解析结果
- `wait_for_schema(query, ...)` - 等待 SQL Schema 解析完成（封装上面两个）
- `preview_schema(node_conf, ...)` - 预览 Schema
- `determine_dataset_type(node_conf, ...)` - 确定数据集类型
- `pre_check_dim_met_list(base_conf, dim_met_list, node_conf, ...)` - 维度指标预检查
- `determine_cluster(base_conf, node_conf, ...)` - 确定目标集群
- `check_dim_met_name(node_conf, dim_met_list, data_set_id=None)` - 校验维度指标名称
- `get_sub_dependency_list(node_conf, data_set_id=None, ...)` - 获取上游依赖
- `create_dataset(body, ...)` - 创建数据集（POST）
- `update_dataset(body, data_set_version_type, ...)` - 更新数据集（PUT）
- `acquire_lock(data_set_id)` - 获取编辑锁
- `release_lock(data_set_id)` - 释放编辑锁
- `check_dataset_recyclable(data_set_ids)` - 检查数据集是否可回收删除
- `get_dataset_lineage_statistics(data_set_id)` - 获取数据集血缘统计（下游依赖数量）
- `recycle_dataset(data_set_ids)` - 回收删除数据集
- `check_dag_impact(data_set_id, node_conf, dim_met_list, ...)` - DAG 影响检查
- `get_version_list(data_set_id, ...)` - 获取版本列表
- `get_version(version_id)` - 获取指定版本详情
- `over_limit_node(data_set_id)` - 超限节点检查
- `is_dataset_ready(data_set_id)` - 数据集就绪状态
- `list_datasets(owner, page, per_page, kw)` - 数据集列表搜索
- `detect_performance(base_conf, sync_conf)` - 性能检测
- `is_need_resource_group(...)` - 是否需要资源组
- `get_dim_met_category_list()` - 获取维度指标分类列表
- `get_sync_settings_batch(data_set_id)` - 获取同步配置（调度、监控、队列等）
- `get_sync_info_all_page_batch(data_set_id, start_date, end_date, node_id_list, ...)` - 查询同步实例列表
- `get_sync_partition_values_batch(data_set_id, node_id_list)` - 获取可回溯分区日期范围
- `check_show_partition_queue_batch(data_set_id, node_id_list)` - 检查队列和并行度配置
- `get_lookback_instances_num(data_set_id, node_id_list, start_date, end_date, ...)` - 查询回溯实例数
- `get_user_yarn_list_backfill(data_set_id)` - 获取回溯可用 Yarn 队列
- `create_sync_job(data_set_id, start_date, end_date, node_id_list, ...)` - 提交回溯任务
- `get_create_sync_job_result(preview_id)` - 轮询回溯任务提交结果
- `wait_for_sync_job(preview_id, timeout, interval)` - 等待回溯任务提交完成
- `refresh_token(token_str)` - 刷新 Token（无参数则自动从 Chrome 获取）
- `auto_detect_owner()` - 自动探测 owner（config.yaml → current_user API）
- `auto_detect_parent_id()` - 自动探测文件夹 ID（config.yaml → folder_tree API）
- `auto_detect_yarn()` - 自动探测 Yarn 队列（config.yaml → getUserYarnList API）
- `dataset_url(data_set_id)` - 生成数据集详情页链接（根据 region 自动选择域名）

### DatasetEditor（高级操作）

- `create_new(client, name, query, ..., publish, source_dataset_id, source_fields, dim_met_overrides, source_client)` - 类方法，创建新数据集。`source_client` 支持跨区域参照（如用 CN 客户端读取源数据集的维度/指标信息）
- `create_from(client, source_dataset_id, new_name, ..., dim_met_overrides, publish)` - 类方法，从已有数据集复制创建
- `load()` - 加载数据集配置（自动从 allDataSetInfoV2 补充 dimMetList）
- `get_overview()` - 获取数据集概览
- `get_base_conf()` - 获取基础配置
- `get_node_conf()` - 获取节点配置
- `get_sync_conf()` - 获取同步配置
- `get_query(node_index)` - 获取 SQL
- `get_dim_met_list()` - 获取维度指标列表
- `update(new_query, new_name, ..., publish, dim_met_overrides, source_fields)` - 更新数据集（支持修改维度指标属性，source_fields 可跳过 SQL Schema 解析）
- `delete(force=False)` - 删除数据集（检查可回收性和下游依赖后回收，force=True 强制删除）
- `backfill(start_date, end_date, queue_name, max_parallelism, skip_check, wait)` - 发起数据同步/回溯（自动检查分区范围、队列、实例数后提交）
- `get_sync_status(start_date, end_date)` - 查询同步实例状态（默认最近 30 天）
- `get_status()` - 获取状态信息
- `get_summary()` - 获取概要信息（含 url）

### 辅助函数

- `auto_get_token(domain, region)` - 从 Chrome Cookie + HTML 自动获取 x-titan-token（根据 region 选择对应域名）
- `extract_dataset_id(url_or_id)` - 从 URL 或字符串中提取数据集 ID（支持 Aeolus URL、纯数字 ID）
- `parse_aeolus_url(url)` - 从 Aeolus URL 中提取 `app_id`、`data_set_id` 和 `region`（根据域名判断 cn/sg，返回 dict）
- `dataset_url(app_id, data_set_id, region)` - 生成数据集详情页链接（根据 region 选择对应域名）
- `load_config(config_path)` - 加载 YAML 配置文件

## 鉴权说明

Aeolus 使用 **x-titan-token**（RS256 JWT）鉴权。Token 来源于字节 SSO 登录后嵌入在 HTML 页面的 `window.__titan_passport_token` 变量中。

**自动获取流程**（需 `pycookiecheat`）：
1. 从 Chrome 浏览器 Keychain 读取对应域名的 Cookie（国内 `data.bytedance.net`，海外 `aeolus-sg.tiktok-row.net`）
2. 使用 Cookie 请求对应区域的 Aeolus 页面（国内 `https://data.bytedance.net/aeolus`，海外 `https://aeolus-sg.tiktok-row.net`）
3. 从 HTML 响应中提取 `window.__titan_passport_token = "..."` 的值
4. 缓存到对应文件（国内 `scripts/token.txt`，海外 `scripts/token_sg.txt`）供后续使用

Token Payload 示例：
```json
{
  "tenant": "bytedance",
  "email": "user@bytedance.com",
  "username": "user",
  "expires": "2026-04-16T08:55:27.994Z",
  "exp": 1776329727
}
```

## 海外 SG 机房注意事项

在 SG 机房创建数据集时，有以下关键差异需要注意：

1. **app_id 不同**：SG 机房的默认 `app_id` 为 `802699`（国内为 `1006036`）。使用 `AeolusClient(region='sg')` 会自动使用正确的 app_id，也可通过 `AeolusClient(region='sg', app_id=802699)` 显式指定。

2. **parent_id 不同**：SG 和 CN 的文件夹 ID 完全不同。不能将国内的 `parent_id`（如 `81004`）用于 SG。脚本会自动探测 SG 的 `parent_id`，或者可以通过 `detect` 命令查看：
   ```bash
   scripts/.venv/bin/python scripts/aeolus_api.py --region sg detect
   ```

3. **config.yaml 按 region 分组**：`config.yaml` 中的 `app_id`、`parent_id`、`yarn_name`、`cluster`、`group_id`、`group_name` 等区域特有配置已按 `regions.cn` / `regions.sg` 分组，脚本通过 `_cfg_region(region, key)` 自动读取对应区域的值。通用配置（`user`、`sync`、`datasource`、`dataset`）保持顶级，不区分 region。

4. **海外表库名差异**：海外 Hive 表的库名通常与国内不同。例如国内的 `flow_aipaas.xxx` 表在海外可能是 `ai_application_coding.xxx`。创建海外数据集时，SQL 中必须使用海外的库名。可以通过 `bytedcli hive search` 搜索海外表：
   ```bash
   bytedcli hive search --query "表名关键词" --type HiveTable --region sg
   ```

5. **baseConf.dc 仍为 "cn"**：即使在 SG 机房，`baseConf.dc` 字段通常仍为 `"cn"`，这是正常的。

6. **groupId / groupName**：SG 的应用分组信息（`groupId`、`groupName`）与国内不同。脚本的 `_make_base_conf` 从 `regions.<region>.group_id` 和 `regions.<region>.group_name` 读取（通过 `_cfg_region`）。如果操作 SG 时 `determineCluster` 报 "资源已被删除"，请检查 config.yaml 中 `regions.sg` 下的 `groupId`、`parent_id` 是否正确。

7. **clusterName = "sg"**：SG 数据集的 `nodeConf.clusterName` 必须为 `"sg"`（国内为 `"cn"`）。使用 `AeolusClient(region='sg')` 时会自动设置为 `"sg"`。

8. **跨区域参照创建**：`create_from()` 只能在同区域内复制，不支持跨区域。跨区域参照请使用 `create_new()` + `source_client` 参数：
   ```python
   cn_client = AeolusClient(region='cn')
   sg_client = AeolusClient(region='sg')
   source = DatasetEditor(cn_client, 5492281)
   source_fields = source.get_node_conf()[0].get("fields", [])
   editor = DatasetEditor.create_new(
       sg_client, name="...", query="SELECT ... FROM 海外库名.表名 ...",
       source_fields=source_fields,
       source_dataset_id=5492281, source_client=cn_client,
       publish=True,
   )
   ```

9. **Yarn 队列字段名差异**：SG 的 `getUserYarnList` API 返回的队列名字段为 `queue`（如 `root.byodel28_stone_ai_application_coding`），而 CN 为 `name` 或 `yarnName`。脚本已兼容所有字段名。

10. **backfill 的 nodeId 格式差异**：SG 回溯时 `nodeIdList` 使用 UUID 格式的 nodeId（如 `32205cb5-4eba-4d7d-9735-87471d2eae70`），CN 使用 `cn//Hive-db-1//Hive-sql-1` 格式。脚本的 `backfill()` 方法会自动从数据集配置中获取正确的 nodeId，无需手动处理。

11. **编辑发布流程差异**：SG 编辑（PUT dataSetV2）时不传 `dataSetVersionType` 参数，CN 必须传（值为 `online` 或 `draft`）。使用 `update(publish=True)` 时脚本会自动处理此差异。

## 使用约束与注意事项

- **Token 安全**：`scripts/token.txt`（国内）和 `scripts/token_sg.txt`（海外）包含敏感凭证，已通过 `scripts/.gitignore` 忽略，不会提交到代码仓库。
- **编辑锁机制**：修改数据集时会自动获取/释放编辑锁（`acquireDataSetLock`/`releaseDataSetLock`），避免并发冲突。
- **创建 vs 更新**：创建使用 `POST /dataSetV2`，更新使用 `PUT /dataSetV2`。编辑场景不需要调用 `determineCluster`（`data_source_id` 从已有 syncConf 获取），也不需要传 `dataTableConf`。
- **Token 有效期**：约 7 天。过期后脚本会尝试自动从 Chrome 重新获取，或调用 `client.refresh_token()` 手动刷新。
- **维度指标类型**：`mapType=0` 为维度，`mapType=1` 为指标。`dimMetVariety`: `0`=普通字段, `1`=分区字段(p_date), `2`=时间字段(datetime)。
- **维度指标数据类型**：API 同时接受 `defaultType` 和 `dataTypeName`，脚本会同时设置两者确保正确。这是 dimMetList 层面的类型映射（不同于 nodeConf.fields 的 prepType）：`timestamp→datetime`, `bigint→int`, `double→float`, `string→string`, `date→date`。
- **p_date 分区字段**：脚本会自动添加 `p_date` 作为日期分区字段（`dimMetVariety=1`, `isAutoAdd=1`），nodeConf.fields 中的 `p_date` 会自动跳过避免重复。
- **update 保留已有配置**：`update()` 方法在参数为空时会保留数据集已有的调度时间、频率等配置，不会使用 config.yaml 默认值覆盖。
- **dim_met_overrides**：`create_new()`、`create_from()` 和 `update()` 都支持通过 `dim_met_overrides` 参数修改字段属性，格式为 `{"字段名": {"mapType": 0或1, ...}}`。
- **SQL Schema 解析耗时**：SQL Schema 解析可能耗时较长（>300s 甚至超时）。**编辑已有数据集时**脚本会自动传入 `dataSetId` 加速解析；创建新数据集时无 dataSetId，**强烈建议手动构造 `source_fields` 跳过解析**（参见工作流 7）。可通过 `bytedcli hive detail <db> <table>` 获取表 schema 后手动构造。`update()` 方法也支持 `source_fields` 参数。
- **prepType 类型映射**：`source_fields` 中的 `prepType` 必须使用风神中间类型，Hive 的 `bigint` 需映射为 `long`（不能直接用 `bigint`，否则报 "prepare中间类型转引擎类型失败"）。
- **SQL 日期变量**：必须使用 `${date}` (yyyyMMdd) 或 `${DATE}` (yyyy-MM-dd)，**不要使用 Jinja 模板语法** `{{ ds }}`。
- **创建后需发布**：`create_new` 创建后的数据集状态为"初始化"，需要 `publish=True` 或后续调用 `update(publish=True)` 才能上线。
- **SG 编辑不传 dataSetVersionType**：SG 的 `PUT /dataSetV2` 不需要 `dataSetVersionType` 查询参数，CN 必须传 `online`（发布）或 `draft`（草稿）。脚本内部已处理此差异。
- **发布自动重试**：刚创建的数据集 ClickHouse 表需要时间生成，`create_new(publish=True)` 和 `create_from(publish=True)` 会自动等待并重试最多 3 次。
- **删除后重名**：删除的数据集名称可能仍然被占用，如需同名重建请更换名称。
- **事实表标记**：nodeConf 中必须包含 `relationTableType=1` 和 `factTableConf` 标记事实表，否则创建会报错"画布中必须存在事实表"。
- **fields 格式差异**：`nodeConf.fields` 在不同 API 中有不同格式要求。`previewSchema` 请求只需 6 个属性（`name`, `type`, `prepType`, `isSourceTableField`, `isSelect`, `isDynamicPartition`）；`PUT/POST dataSetV2` 保存时需要额外的 `alias`（如 `` `field_name` ``）和 `isSupport`（`true`）。脚本内部通过 `_enrich_fields_for_save()` 自动补充，调用方无需关心。
- **SQL Schema 解析成功状态**：API 返回 `status` 可能为 `"FINISHED"` 或 `"SUCCEEDED"`，脚本兼容两种值。
- **数据同步（回溯）**：`backfill()` 方法自动完成完整的回溯流程：获取可回溯分区范围 → 检查队列配置 → 查询实例数 → 提交回溯任务 → 等待完成。回溯日期格式为 `yyyy-MM-dd`。回溯提交是异步的（`createSyncJob` 返回 `previewId`，通过 `getCreateSyncJobResult` 轮询），`wait=True` 时会自动等待。
- **同步状态码**：`syncStatus` 字段含义：`1`=等待中, `2`=未开始, `3`=运行中, `4`=成功, `5`=失败。
- **海外区域支持**：通过 `region` 参数（`"cn"` 或 `"sg"`）切换国内/海外。区域影响：域名（`data.bytedance.net` vs `aeolus-sg.tiktok-row.net`）、页面路径（国内有 `/aeolus` 前缀，海外无）、默认集群名 `nodeConf.clusterName`（`cn` vs `sg`）、默认 `app_id`（国内 `1006036` vs 海外 `802699`）、Token 缓存文件（`token.txt` vs `token_sg.txt`）。注意 `baseConf.dc` 与 region 无关，海外也通常为 `"cn"`。API 路径 `/aeolus/api/v3/` 和请求头格式在国内外完全一致。**详见上方"海外 SG 机房注意事项"章节。**

## References

按需读取：
- `references/api-reference.md`：完整的 API 端点说明、请求/响应格式、数据模型。
