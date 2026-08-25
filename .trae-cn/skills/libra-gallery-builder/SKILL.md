---
name: libra-gallery-builder
description: 自动化操作 Libra Gallery 平台的指标建设，支持中国机房和海外机房。用于建指标、更新指标、添加维度、修改数据源SQL、保存 Gallery 配置、查看指标组、克隆指标组、版本克隆（从历史快照克隆）、上线指标组等场景，支持数据源管理、指标增删改、维度增删改、指标组增删改克隆、版本/快照管理、保存校验、上线管理等全流程操作。
---

# libra-gallery-builder

自动化操作 Libra Gallery 平台的指标建设，支持中国机房和海外机房，通过 `scripts/libra_gallery_api.py` 完成所有操作。

## 环境说明

SKILL 支持两个环境，通过 `LibraGalleryClient(env=...)` 切换：

| 环境 | env 值 | 平台地址 | 默认区域 |
|------|--------|----------|---------|
| **中国机房** | `"cn"`（默认） | https://libra-gallery.bytedance.net | region=cn, dorado=cn, apps=1190 |
| **海外机房** | `"i18n"` | https://libra-gallery-us.tiktok-row.net | region=va, dorado=sg, apps=532 |

**环境判断规则（AI 自动判断，用户无需手动指定）：**
- 用户提到"海外"、"i18n"、"ROW"、"tiktok-row"、"us"、"sg"、"va" → 使用 `env="i18n"`
- 用户给出 `libra-gallery-us.tiktok-row.net` 的链接 → 使用 `env="i18n"`（通过 `detect_env_from_url(url)` 自动识别）
- 用户提到"国内"、"cn"、或给出 `libra-gallery.bytedance.net` 的链接 → 使用 `env="cn"`
- 默认使用 `env="cn"`

**推荐模式**：当用户提供 URL 时，优先使用 `detect_env_from_url(url)` 自动检测环境，再用 `extract_ticket_id(url)` 提取 ID：
```python
url = "https://libra-gallery-us.tiktok-row.net/#/metric/set/detail/37561"
env = detect_env_from_url(url)         # → "i18n"
ticket_id = extract_ticket_id(url)     # → 37561
client = LibraGalleryClient(env=env)
editor = TicketEditor(client, ticket_id)
```

**海外机房特殊配置（所有 region 值在 API 中均为全小写、下划线分隔）：**
- 指标组的部署机房（`dorado_regions`）一般选择 `sg`，也可选 `va`、`mya`、`eu_ttp`、`us_ttp`
- 数据源的 conf：海外环境默认为空对象 `{}`（后端自动处理），国内为 `{"regions": ["cn"], "regions_cn_conf": {"dorado_region": "cn"}}`。如需显式指定海外数据源 conf，可传入 `region` 参数（如 `"sg"`）
- 数据源的 Dorado 主机房（`primary_dest_region`）一般为 `sg`，也可选 `va`、`mya`
- 海外独有 API：`validate_ttp_sql(region, sql)` 用于 TTP 区域 SQL 校验，region 可选 `eu_ttp` 或 `us_ttp`

**跨环境操作：**
- 支持同时操作国内和海外机房，例如"参照国内机房的 XXX 需求，在海外机房新建类似的需求和指标组"
- 实现方式：创建两个 client 实例，一个读源（`LibraGalleryClient(env="cn")`），一个写目标（`LibraGalleryClient(env="i18n")`）
- 国内和海外的 Cookie 不通用（域名不同，SSO 系统不同），需要分别登录对应平台获取 Cookie
- 国内和海外的 API 路径完全一致（都是 `/v1/` 前缀），区别仅在域名和部分参数默认值。海外不需要额外抓包，所有 API 通用
- **跨环境克隆注意**：使用 `create_from(target_client, source_editor, ...)` 时，`target_client` 的 env 决定新需求创建在哪个环境。源需求的数据源 conf、dorado_regions 等参数会原样复制，如果源和目标环境不同，可能需要在创建后手动调整这些参数（如 `update_group()` 修改 dorado_regions）

## 前置条件

1. **Python 虚拟环境（首次使用必须执行）**：脚本依赖 `requests` 和 `pycookiecheat` 等非标准库，使用 `scripts/` 目录下的 venv 隔离管理。首次使用前需要初始化虚拟环境：
   ```bash
   cd scripts
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   后续所有 Python 命令都必须通过 venv 执行：
   ```bash
   scripts/.venv/bin/python scripts/libra_gallery_api.py detect
   ```
   或者先激活再执行：
   ```bash
   source scripts/.venv/bin/activate && python scripts/libra_gallery_api.py detect
   ```
2. **零配置即可使用**：核心配置（`owner`、`business`、`apps`、`business_id`、`business_key`）均支持自动探测，无需手动配置。脚本会依次尝试：config.yaml 配置 → API 自动探测 → 代码默认值。首次使用运行 `scripts/.venv/bin/python scripts/libra_gallery_api.py detect` 可验证自动探测结果。
3. **Cookie 自动获取**：脚本会自动从 Chrome 浏览器读取对应环境 Libra Gallery 的 Cookie（依赖 `pycookiecheat`，已包含在 `requirements.txt` 中，仅支持 macOS）。首次使用时系统可能弹出 Keychain 密码确认框，授权即可。自动获取的 Cookie 会缓存到 `scripts/cookie.txt`（中国机房）或 `scripts/cookie_i18n.txt`（海外机房）。
4. **手动设置 Cookie（备选）**：如果自动获取失败，可手动将 Cookie 写入对应文件。中国机房写入 `scripts/cookie.txt`，海外机房写入 `scripts/cookie_i18n.txt`。内容为 cURL `-b '...'` 中的完整 Cookie 字符串。获取方式：Chrome 打开对应平台 → F12 → Network → 任意请求 → 复制 Request Headers 中的 Cookie。
5. **Cookie 有效期**：`bd_sso_3b6da9` JWT 约 7 天过期。过期后脚本会自动从 Chrome 刷新，或调用 `client.refresh_cookie()` 手动刷新。
6. **URL 解析**：支持直接传入 Libra Gallery URL（如 `https://libra-gallery.bytedance.net/#/metric/set/detail/65562` 或 `https://libra-gallery-us.tiktok-row.net/#/metric/set/detail/37561`），会自动提取 `ticket_id`。传入海外 URL 时可用 `detect_env_from_url(url)` 自动识别 env。

## 平台结构

- **需求（Ticket）**：顶层容器，一个需求最多 10 个指标组。
- **数据源（VirtualTable）**：一个需求可以有多个数据源（T1、T2、T3...），每个数据源对应一段 Hive SQL。
- **指标组（Group）**：每个指标组包含任意多指标和维度。推荐每个指标组的指标和维度来源于同一个数据源。
- **指标（Metric）**：分简单指标（PV/UV）、比率指标（PV/PV）、人均指标（PV/UV 或 PV/base_user）。指标的 `left_type`/`right_type` 可选值为 `pv`（求和）、`uv`（去重计数）和 `base_user`（实验组全体用户数，仅 right_type），**没有 `pv_distinct` 选项**——去重计数统一用 `uv`。
- **维度（Dimension）**：分用户维度（USER_DIMENSION）和指标维度（METRIC_DIMENSION）。

## 统计粒度（ID 类型）

Gallery 支持两种用户统计粒度，决定了如何关联 AB 实验分流日志：

| 粒度 | `user_id_type` | `mapping_detail` key | AbLog SQL 中的用户列 | 数据源 SQL 输出列 | 适用场景 |
|------|---------------|---------------------|--------------------|--------------------|---------|
| **设备维度**（默认） | `["USER_UNIQUE_ID"]` | `"user_unique_id"` | `user_unique_id` | `user_unique_id` | 以设备为单位统计（如客户端行为指标） |
| **UID 维度** | `["USER"]` | `"user_id"` | `user_uid as user_id` | `user_id` | 以登录用户为单位统计（如商业化、订阅等指标） |

**默认行为**：国内和海外环境默认都使用 `user_unique_id`（设备维度）作为统计粒度。如需使用 `user_id`（UID）粒度，需要在创建指标组时显式指定 `user_id_type=["USER"]`。

**UID 粒度的 3 个核心配置差异**：

1. **指标组粒度选择**：`user_id_type=["USER"]`（而非默认的 `["USER_UNIQUE_ID"]`）
2. **AbLog SQL**：使用 `user_uid as user_id` 而非 `user_unique_id`：
   ```sql
   select CAST(version_id as BIGINT) as vid,
          user_uid as user_id,
          MIN(min_date) as min_date,
          MAX(is_active) as is_active
   from origin_log.dwd_abtest_vid_log_df
   where date = '${date}'
     and app = 'marscode_native_ide_us'
   group by vid,
            user_id;
   ```
3. **数据源配置**：`mapping_detail` 的 key 和 type 为 `"user_id"`，数据源 SQL 输出 `user_id` 列（而非 `user_unique_id`）

**在脚本中使用 UID 粒度**：

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient(env="i18n")

# 1. 创建需求
editor = TicketEditor.create_new(client, name="UID粒度指标组示例")

# 2. 添加数据源 — 指定 id_type="user_id"，SQL 必须输出 user_id 列
editor.add_data_source("T1", sql="""
SELECT
  user_id,
  country,
  user_type,
  SUM(order_amount) AS total_order_amount,
  '${date}' AS date
FROM some_table
WHERE date = '${date}'
GROUP BY user_id, country, user_type
""", id_type="user_id")

# 3. 添加指标组 — 指定 user_id_type=["USER"]（前端显示为"UID"维度）
editor.add_group(
    "[Libra]UID粒度商业化指标",
    user_id_type=["USER"],
    cum_start_time="2026-05-09",
)

# 4. 添加指标和维度（同默认粒度，引用 T1:列名）
editor.add_metric(0, "订单总金额", "T1:total_order_amount", left_type="pv")
editor.add_dimension(0, "国家", "T1:country", dim_type="METRIC_DIMENSION")

# 5. 保存
editor.save()
```

**UID 粒度注意事项**：
- 数据源 SQL 中必须输出 `user_id` 列作为主键（而非 `user_unique_id`），且建议为 BIGINT 或 STRING 类型
- `add_data_source()` 必须传 `id_type="user_id"` 参数，否则默认使用 `user_unique_id`
- `add_group()` 必须传 `user_id_type=["USER"]`，否则默认使用 `["USER_UNIQUE_ID"]`
- AbLog SQL 会自动根据 `user_id_type` 获取正确版本（脚本调用 `get_ab_log_sql(user_types="USER")` 获取 UID 粒度的 SQL）
- 如果 Gallery 对 SQL 中的 `user_id` 列名有校验问题，可以在 SQL 内部用别名（如 `AS uid`），然后在外层子查询 `SELECT uid AS user_id`

## 自动探测

脚本支持关键配置的自动探测，实现零配置即可使用。探测优先级：**显式参数 > config.yaml > API 自动探测 > 代码默认值**。

| 配置项 | config.yaml 字段 | 自动探测方式 | 对应 API |
|--------|------------------|-------------|---------|
| **owner**（需求负责人） | `user.owner` | 从 Cookie 中的 `username` 字段获取当前登录用户名 | Cookie 解析 |
| **business**（Meego 业务线） | `ticket.business` | 通过 owner 查询关联的业务列表，取第一个 | `/v1/business/list/quick_query` |
| **business_id**（AB 日志业务 ID） | `ablog.business_id` | 通过 owner 查询关联业务，获取 business ID；失败时使用环境预设（cn=261, i18n=122） | `/v1/business/list/quick_query` → profile fallback |
| **business_key**（AB 日志业务 key） | `ablog.business_key` | 从 Business 详情的 config 配置中获取；失败时使用环境预设（默认 "basic"） | `/v1/business/{id}` → profile fallback |
| **apps**（应用 ID 列表） | `group.apps` | 从 Business 详情的 basic.app_ids 中获取；失败时使用环境预设（cn=["1190"], i18n=["532"]） | `/v1/business/{id}` → profile fallback |
| **ablog SQL**（进组口径 SQL） | — | 通过 business_id + business_key + apps 自动从 API 获取，写入 `abLogSqlPreview` | `/v1/business/online/ab_log_v2` |

运行 `python scripts/libra_gallery_api.py detect` 可查看当前探测到的所有配置值。

## 用户配置

SKILL 使用 `scripts/config.yaml` 文件存储用户自定义配置。标注 `[可自动探测]` 的配置项可以留空或删除，脚本会自动获取。其他配置项有合理默认值，按需修改。

配置文件路径：`scripts/config.yaml`

**配置生效规则**：参数调用时显式传入 > config.yaml 配置 > API 自动探测 > 代码硬编码默认值

```yaml
# ===== 环境预设（通过 env 参数自动选择，一般无需修改） =====
profiles:
  cn:
    base_url: "https://libra-gallery.bytedance.net"
    cookie_domain: "https://libra-gallery.bytedance.net"
    ticket_region: "cn"
    apps_region: "cn"
    data_source_region: "cn"
    data_source_dorado_region: "cn"
    group_dorado_regions: "cn"
    group_business_tag_id: 2
    ablog_business_id: 261
    ablog_business_key: "basic"
    apps: ["1190"]
  i18n:
    base_url: "https://libra-gallery-us.tiktok-row.net"
    cookie_domain: "https://libra-gallery-us.tiktok-row.net"
    ticket_region: "va"
    apps_region: "i18n"
    data_source_dorado_region: "sg"
    group_dorado_regions: "sg"
    group_business_tag_id: 1
    ablog_business_id: 122
    ablog_business_key: "basic"
    apps: ["532"]

# ===== 用户信息（可自动探测） =====
user:
  owner: ""                        # [可自动探测] 留空则自动从 Cookie 获取
  meego_id: 0                      # Meego Story ID（工单 ID），0=待分配

# ===== 业务相关（大部分可自动探测） =====
ticket:
  description: ""                  # 默认描述
  business: ""                     # [可自动探测] Meego 业务线 ID（留空则自动获取）

group:
  apps: []                         # [可自动探测] 应用 ID（留空则自动从 Business 获取）

ablog:
  use_type: "custom"               # AB 日志使用类型
  business_id:                     # [可自动探测] AB 日志业务 ID（留空则自动获取）
  business_key:                    # [可自动探测] AB 日志业务 key（留空则自动获取）

# ===== 通用默认值（一般无需修改） =====
dimension:
  enums_update_type: "merge"       # 枚举更新: merge=合并 / force=强制同步
```

**使用场景**：
- **创建新需求** `create_ticket(name="xx")` → 自动探测 `owner`、`business`，从 config 读取 `meego_id`
- **添加新指标组** `add_group(name="xx")` → 自动探测 `owner`、`apps`、`ablog_config`（business_id/business_key/apps），自动通过 API 获取 AB 日志 SQL（`abLogSqlPreview`）并写入指标组配置
- **复制/修改已有指标** → 不受 config 影响，保持原有配置

## 核心流程

1. 识别用户意图：创建需求、查看指标组、添加指标、修改数据源、克隆指标组、保存配置等。
2. 使用 `scripts/libra_gallery_api.py` 中的 `LibraGalleryClient` 和 `TicketEditor` 类完成操作。
3. **所有修改操作最后必须调用 `save()` 才会生效，save 只保存草稿不会上线。**
4. 保存前建议先调用 `diff()` 查看变更，用 `save(dry_run=True)` 做校验。
5. **`save()` 成功后会自动从服务端重新加载数据**，确保本地状态与服务端一致。
6. **操作完成后，将 Gallery 链接展示给用户**。`create_new()`、`create_from()`、`save()` 会自动打印链接，也可通过 `gallery_url(ticket_id, env)` 或 `editor.get_summary()["url"]` 获取。
7. **打印行为**：`create_new()`、`create_from()`、`save()`、`delete_ticket()` 等操作方法均会自动打印操作结果。AI 调用这些方法后**不要在外部重复打印相同信息**。
8. **上线功能默认不执行**。只有用户明确说"上线"时才调用 `submit_online()`。上线后状态机会自动推进，后续需在 Gallery 页面完成审批流程。

## 典型工作流

### 工作流 1: 从零新建指标组（全新创建）

最基础的场景——创建全新的需求、数据源、指标组、指标和维度。

> **关键规则：数据源 SQL 是纯 Hive SQL，不包含 `Tx:` 前缀。`Tx:column_name` 格式仅用于指标和维度定义中引用数据源的列。**

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient()  # 或 LibraGalleryClient(env="i18n")

# 1. 创建新需求（owner 自动探测）
editor = TicketEditor.create_new(client, name="新需求名称")

# 2. 添加数据源 — SQL 是纯 Hive SQL，列名直接用字段名或别名
#    ✅ 正确: SELECT did AS user_unique_id, agent_type, SUM(cnt) AS cnt ...
#    ❌ 错误: SELECT did AS T1:user_unique_id, agent_type AS T1:agent_type ...
editor.add_data_source("T1", sql="""
SELECT
  did AS user_unique_id,
  agent_type,
  is_new,
  SUM(COALESCE(accepted_cnt, 0)) AS accepted_cnt,
  SUM(COALESCE(block_show_cnt, 0)) AS block_show_cnt,
  '${date}' AS date
FROM flow_aipaas.dwd_trae_ai_behavior_event_di
WHERE date = '${date}'
  AND behavior_type = 'ai_chat'
  AND block_show_cnt > 0
  AND did IS NOT NULL AND did <> '0'
GROUP BY did, agent_type, is_new
""")

# 3. 添加指标组
editor.add_group(
    "[Libra]各Agent类型代码块接受率",
    cum_start_time="2025-09-15",  # 必须使用 yyyy-MM-dd 格式，不能用 yyyyMMdd
)

# 4. 添加指标 — 这里用 Tx:column_name 引用数据源列
#    比率指标: accepted_cnt / block_show_cnt
editor.add_metric(0, "代码块接受率", "T1:accepted_cnt", left_type="pv",
                  right_key_sql="T1:block_show_cnt", right_type="pv",
                  description="accepted_cnt/block_show_cnt")

# 5. 添加维度 — 同样用 Tx:column_name 引用
editor.add_dimension(0, "agent类型", "T1:agent_type", dim_type="METRIC_DIMENSION")
editor.add_dimension(0, "新老用户", "T1:is_new", dim_type="USER_DIMENSION")

# 6. 保存草稿
editor.save()
```

**数据源 SQL 编写要点：**
- **默认（设备维度）**：SQL 中必须包含 `did AS user_unique_id`（或其他用户 ID 列 AS `user_unique_id`），这是 Gallery 用于关联 AB 实验日志的主键
- **UID 维度**：SQL 中必须输出 `user_id` 列（如 `user_id` 或 `xxx AS user_id`），作为与 AB 实验日志的关联主键。使用 `add_data_source("T1", sql=..., id_type="user_id")` 创建数据源
- SQL 中使用 `${date}` 作为日期占位符（Dorado 调度时自动替换为当天日期）
- **SQL 必须输出 `date` 字段**（如 `'${date}' AS date`），否则保存校验会报错"原始 SQL 中未输出 date 字段"
- SQL 中 SELECT 出的列名就是后续指标/维度用 `Tx:column_name` 引用时的 `column_name`
- 建议对可能为 NULL 的指标字段使用 `COALESCE(field, 0)` 处理
- 按用户维度 `GROUP BY`，确保每个用户在每个维度组合下只有一行

**数据源 SQL 常见校验问题及解决方案：**

| 报错信息 | 原因 | 解决方案 |
|---------|------|---------|
| SQL的列中不要包含(device_id, user_id) | Gallery 校验可能对 `device_id`、`user_id` 等列名有特殊处理 | 如遇到此报错，尝试用子查询包裹：内层 `SELECT c.device_id AS user_unique_id, ...`，外层只 `SELECT user_unique_id, ...` |
| SQL中不允许出现未包裹在单引号内的双引号 | SQL 中使用了双引号包裹字符串值（如 `"${date}"`、`"success"`） | 所有字符串值必须使用**单引号**：`'${date}'`、`'success'` |
| 原始 SQL 中未输出 date 字段 | 数据源 SQL 的外层 SELECT 缺少 `date` 列 | 在 SQL 中确保输出 `date` 字段，例如在子查询中 `'${date}' AS date`，外层 SELECT 包含 `date` |
| user_id 建议设置为 BigInt 类型 | `user_id` 字段类型为 STRING | 在 SQL 中使用 `CAST(user_id AS BIGINT)` 或直接不输出 `user_id`（仅通过 `user_unique_id` 关联） |

**子查询包裹模式（推荐用于 device_id/user_id 来源的数据源）：**
```sql
SELECT
    user_unique_id,
    is_new,
    model_name,
    total_cost,
    1 AS request_cnt,
    date
FROM (
    SELECT
        c.device_id AS user_unique_id,
        COALESCE(d.is_new, 0) AS is_new,
        c.model_name,
        c.total_cost,
        '${date}' AS date
    FROM some_table c
    LEFT JOIN user_table d ON c.device_id = d.user_unique_id
    WHERE c.date = '${date}'
) t
```

### 工作流 2: 复制整个需求（一键克隆所有指标组和数据源）

最简单的场景——将一个已有需求完整复制到新需求，等价于 Gallery 页面上的"复制需求"按钮。

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient()

# 1. 读取源需求
source = TicketEditor(client, 82449)

# 2. 一键复制整个需求（source_group_names 不传或传 None 表示复制全部指标组）
new_editor = TicketEditor.create_from(client, source, new_ticket_name="新需求名称")
print(f"新需求 ID: {new_editor.ticket_id}")

# 3. 可选：修改后保存
new_editor.save()
```

### 工作流 3: 从已有需求克隆部分指标组到新需求（跨需求克隆）

参照一个已有指标组，在新需求中创建类似的指标组，并做局部修改。

`create_from` 会创建新需求并克隆指标组，返回的 editor 已从服务端加载最新数据，可以直接修改后一次性 `save()`。

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

# 中国机房（默认）
client = LibraGalleryClient()
# 海外机房
# client = LibraGalleryClient(env="i18n")

# 1. 读取源需求
source = TicketEditor(client, 82449)

# 2. 一步创建新需求并克隆指标组（owner 自动探测，meego_id 从 config.yaml 读取）
new_editor = TicketEditor.create_from(
    client,
    source,
    "[Libra]源指标组名称",                           # 要克隆的指标组
    new_ticket_name="新需求名称",
    rename_map={"[Libra]源指标组名称": "[Libra]新指标组名称"},  # 可选重命名
    copy_data_sources=True,                           # 自动复制源需求的数据源
)
print(f"新需求 ID: {new_editor.ticket_id}")

# 3. 修改克隆后的指标组（create_from 返回的 editor 可直接修改）
# 单个重置
new_editor.reset_dimension_conf(0, "维度名称")
# 批量重置多个维度的高级配置
new_editor.reset_dimensions_conf(0, ["维度A", "维度B", "维度C"])

# 4. 保存（create_from + 修改 + save 一步到位，无需重新构建 editor）
new_editor.save()
```

### 工作流 4: 从指定版本克隆到新需求（版本克隆）

当需求经过多次上线后，当前草稿可能已经被修改。如果想基于某个历史版本（snapshot）的指标组配置创建新需求，可以使用 `create_from_snapshot`。

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient()

# 1. 查看需求的版本历史，找到目标版本号
editor = TicketEditor(client, 65933)
snapshots = editor.list_snapshots()
# 每个 snapshot 包含 snapshot_id, status, online_time 等

# 2. 查看指定版本的指标组（可选，确认内容）
snapshot_editor = TicketEditor(client, 65933, snapshot_id=30)
groups = snapshot_editor.list_groups()

# 3. 从版本 30 克隆所有指标组到新需求
new_editor = TicketEditor.create_from_snapshot(
    client,
    source_ticket_id=65933,
    snapshot_id=30,
    # source_group_names=None 表示克隆该版本的所有指标组
    new_ticket_name="新需求名称",
)

# 也可以只克隆指定的指标组，并重命名
new_editor = TicketEditor.create_from_snapshot(
    client,
    source_ticket_id=65933,
    snapshot_id=30,
    source_group_names=["trae_libra_ai_chat_resource"],
    new_ticket_name="新需求名称",
    rename_map={"trae_libra_ai_chat_resource": "新指标组名称"},
    copy_data_sources=True,
)

# 4. 修改后保存
new_editor.save()
```

### 工作流 5: 在已有需求中添加新指标组（同需求克隆）

直接在已有需求中克隆一个指标组，修改后保存即可。

```python
client = LibraGalleryClient()
editor = TicketEditor(client, 82449)

# 同需求内克隆
editor.clone_group("[Libra]源指标组", "[Libra]新指标组")

# 修改新指标组的维度配置
editor.update_dimension("[Libra]新指标组", "维度名称", conf={"use_conf": True, "enums_update_type": "force"})

# 保存
editor.save()
```

### 工作流 6: 跨需求克隆到已有需求

```python
client = LibraGalleryClient()
source = TicketEditor(client, 82449)
target = TicketEditor(client, 65562)

# 从源需求克隆到目标需求
target.clone_group_from(source, "[Libra]源指标组", "[Libra]新指标组", copy_data_sources=True)
target.save()
```

### 工作流 7: 编辑已有需求的指标和维度

```python
client = LibraGalleryClient()
editor = TicketEditor(client, 82449)

# 查看现有指标组和维度
groups = editor.list_groups()
dims = editor.list_dimensions(0)  # use_conf 列显示高级配置状态

# 修改维度类型
editor.update_dimension(0, "维度名称", dim_type="USER_DIMENSION")

# 重置维度高级配置为默认值
editor.reset_dimension_conf(0, "维度名称")

# 保存
editor.save()
```

### 工作流 8: 跨环境操作（参照国内需求在海外新建）

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

cn_client = LibraGalleryClient(env="cn")
i18n_client = LibraGalleryClient(env="i18n")

source = TicketEditor(cn_client, 82449)

new_editor = TicketEditor.create_from(
    i18n_client,
    source,
    "[Libra]源指标组名称",
    new_ticket_name="海外-新需求名称",
    rename_map={"[Libra]源指标组名称": "[Libra]海外指标组名称"},
    copy_data_sources=True,
)

# 跨环境克隆后，源需求的 dorado_regions/conf 等参数会原样复制
# 如需调整海外指标组的部署机房，可在保存前修改：
# new_editor.update_group(0, dorado_regions="sg")

new_editor.save()
```

### 工作流 9: 修改数据源 SQL 列名（字段重命名）

当上游表字段重命名后，需要同步更新数据源 SQL 和指标/维度的列引用。使用 `column_remap` 参数可以一步完成。

> **关键注意事项**：更新数据源 SQL 后如果列名发生变化，已有指标和维度中引用旧列名的 key 会在保存时失效（被清空或报错）。必须使用 `column_remap` 参数同步更新引用，或分两步操作。

**方式 1（推荐）：使用 column_remap 一步完成**

```python
client = LibraGalleryClient()
editor = TicketEditor(client, 93126)

# 更新 SQL 的同时，自动将引用旧列名的指标/维度更新为新列名
new_sql = """
SELECT
    user_unique_id,
    session_id,
    message_id,
    ...
FROM ...
"""
editor.update_data_source_sql("T1", new_sql, column_remap={
    "conversation_id": "session_id",  # 旧列名 → 新列名
    "session_id": "message_id",
})

# 一次保存即可
editor.save()
```

**方式 2：分两步操作（不推荐，但可用于无法预先确定映射的场景）**

```python
client = LibraGalleryClient()

# 第一步：更新 SQL 并保存（会打印列名变化警告和受影响的引用列表）
editor = TicketEditor(client, 93126)
editor.update_data_source_sql("T1", new_sql)
editor.save()

# 第二步：重新加载，补充丢失的指标和维度引用
editor2 = TicketEditor(client, 93126)
editor2.add_metric(0, "指标名", "T1:new_col", ...)
editor2.update_dimension(0, "维度名", key="T1:new_col")
editor2.save()
```

### 工作流 10: 删除数据源并重命名（T1 删除、T2 改 T1）

克隆需求后可能带了多余的数据源。典型场景：源需求有 T1 和 T2 两个数据源，指标只用了 T2，克隆后需要删除 T1 并将 T2 改名为 T1（统一引用）。

> **关键注意事项**：
> - 必须先删除要移除的数据源，再重命名另一个数据源（否则 `rename_data_source` 会报 key 冲突）
> - `rename_data_source` 会自动更新所有指标和维度中的 `Tx:column` 引用（包括 `key` 数组和 `key_sql` 字符串），内部使用 JSON 序列化全局替换，安全可靠
> - **切勿**手动逐字段替换或使用递归函数替换，极易遗漏字段或破坏数据结构

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient(env="i18n")
editor = TicketEditor(client, 44079)

# 1. 删除不需要的数据源
editor.remove_data_source("T1")

# 2. 将 T2 重命名为 T1（自动更新所有引用 T2:xxx → T1:xxx）
editor.rename_data_source("T2", "T1")

# 3. 保存
editor.save()
```

也可以用于更复杂的场景（如 T1→T3, T2→T1, T3→T2 交换）：
```python
# 多步重命名（需避免中间 key 冲突，可用临时名称过渡）
editor.rename_data_source("T1", "T_TEMP")
editor.rename_data_source("T2", "T1")
editor.rename_data_source("T_TEMP", "T2")
editor.save()
```

## 主要功能

### 需求级操作

#### 创建新需求
```python
from libra_gallery_api import LibraGalleryClient, TicketEditor

client = LibraGalleryClient()  # 或 LibraGalleryClient(env="i18n") 用于海外

# 方式 1: 创建并直接进入编辑模式（推荐，owner 自动探测，其他从 config.yaml 读取）
editor = TicketEditor.create_new(client, name="需求名称")
print(f"新需求 ID: {editor.ticket_id}")

# 方式 2: 显式指定参数（覆盖自动探测和 config 默认值）
editor = TicketEditor.create_new(
    client,
    name="需求名称",
    owner="another_user",
    meego_id="9999999999",
    description="需求描述",
)

# 方式 3: 仅创建，后续手动构建 editor
result = client.create_ticket(name="需求名称")
new_ticket_id = result["data"]["ticket"]["id"]
```

#### 列出需求
```python
result = client.list_tickets(owner="zhanfurong")
```

#### 列出某个 owner 的所有指标组
```python
# 自动分页遍历所有需求，提取其中的指标组
groups = client.list_all_groups(owner="zhanfurong")
# 可选按 develop_status 过滤
groups = client.list_all_groups(owner="zhanfurong", status="ONLINE")
# owner 不传时自动探测当前登录用户
groups = client.list_all_groups()
```

#### 删除需求
```python
client.delete_ticket(ticket_id)
```

#### 查看需求概要
```python
from libra_gallery_api import LibraGalleryClient, TicketEditor, extract_ticket_id, detect_env_from_url

url = "https://libra-gallery.bytedance.net/#/metric/set/detail/65562"
# 或海外 URL: url = "https://libra-gallery-us.tiktok-row.net/#/metric/set/detail/37561"
env = detect_env_from_url(url)          # 自动识别: cn 或 i18n
ticket_id = extract_ticket_id(url)
client = LibraGalleryClient(env=env)
editor = TicketEditor(client, ticket_id=ticket_id)
summary = editor.get_summary()
```

### 数据源操作

> **重要**：数据源 SQL 是**纯 Hive SQL**，不包含 `Tx:` 前缀。SQL 中 SELECT 出的列名（或别名）就是后续指标/维度用 `Tx:column_name` 引用的 `column_name` 部分。

#### 添加新数据源
```python
# 数据源 SQL 必须包含用户 ID 列（用于关联 AB 实验日志）
# 默认粒度(user_unique_id): SQL 输出 user_unique_id 列
# UID 粒度(user_id): SQL 输出 user_id 列，需传 id_type="user_id"
# SQL 是纯 Hive SQL，不带 Tx: 前缀

# 方式 1（推荐）：传 .sql 文件路径，脚本自动读取文件内容（保持多行格式）
editor.add_data_source("T1", sql="T1.sql")

# 方式 2：直接传 SQL 字符串（仅在 .py 脚本文件中使用三引号时可行，不要在 python -c 中使用）
sql = """
SELECT
  did AS user_unique_id,
  agent_type,
  is_new,
  SUM(COALESCE(accepted_cnt, 0)) AS accepted_cnt,
  SUM(block_show_cnt) AS block_show_cnt,
  '${date}' AS date
FROM flow_aipaas.dwd_trae_ai_behavior_event_di
WHERE date = '${date}'
  AND did IS NOT NULL AND did <> '0'
GROUP BY did, agent_type, is_new
"""
editor.add_data_source("T5", sql=sql)

# UID 粒度数据源（指定 id_type="user_id"）
uid_sql = """
SELECT
  user_id,
  country,
  user_type,
  SUM(order_amount) AS total_order_amount,
  '${date}' AS date
FROM some_table
WHERE date = '${date}'
GROUP BY user_id, country, user_type
"""
editor.add_data_source("T1", sql=uid_sql, id_type="user_id")

# 国内 env: 自动构建 conf（regions/regions_cn_conf），dorado_region 由 profile 决定
# 海外 env: conf 默认为空对象（后端自动处理），dorado_region 默认 sg
# 海外示例：显式指定 region 和 dorado_region（可选，一般不需要）
# editor.add_data_source("T5", sql=sql, region="sg", dorado_region="va")
```

#### 查看数据源列表和 SQL
```python
sources = editor.list_data_sources()
sql = editor.get_data_source_sql("T1")
```

#### 修改数据源 SQL
```python
# 支持传 .sql 文件路径或直接传 SQL 字符串
editor.update_data_source_sql("T1", "T1.sql")
# 或
editor.update_data_source_sql("T1", new_sql)

# 列名重命名时，使用 column_remap 自动更新指标/维度引用
editor.update_data_source_sql("T1", new_sql, column_remap={
    "old_column": "new_column",
})
```

#### 删除数据源
```python
editor.remove_data_source("T5")
```

#### 重命名数据源（自动更新所有引用）
```python
# 将 T2 重命名为 T1，所有 T2:xxx 引用自动变为 T1:xxx
editor.rename_data_source("T2", "T1")
```

### 指标组操作

#### 列出指标组
```python
groups = editor.list_groups()
```

#### 添加新指标组
```python
editor.add_group(
    "[Libra]新指标组名称",
    apps=["1190"],
    owner=["zhanfurong"],
    cum_start_time="2025-09-15",  # 必须使用 yyyy-MM-dd 格式（如 "2025-09-15"），不能用 yyyyMMdd
)
```

#### 克隆指标组（复制指标和维度，可选更换数据源）
```python
# 同需求内克隆
editor.clone_group("源指标组名称", "新指标组名称", vt_name="T2")

# 跨需求克隆（从另一个需求复制指标组过来）
source_editor = TicketEditor(client, 82449)
editor.clone_group_from(
    source_editor,
    "源指标组名称",
    "新指标组名称",
    copy_data_sources=True,  # 同时复制源需求的数据源
)
```

#### 更新指标组属性
```python
editor.update_group(0, name="新名称", description="新描述")
editor.update_group("指标组名称", owner=["user1"], apps=["1190"])
```
注意：`update_group` 不会修改 `metrics` 和 `dimensions`，请使用对应的 add/remove/update 方法操作指标和维度。

#### 删除指标组
```python
editor.remove_group(0)  # 按索引
editor.remove_group("指标组名称")  # 按名称
```

### 指标操作

#### 列出指标
```python
metrics = editor.list_metrics(0)  # 按索引
metrics = editor.list_metrics("指标组名称")  # 按名称
```

#### 添加简单指标
```python
editor.add_metric(0, "新消息数", "T1:new_message_cnt", description="新的消息计数")
```

#### 添加比率指标
```python
editor.add_metric(0, "新应用率", "T1:applied_cnt", left_type="pv",
                  right_key_sql="T1:suggest_cnt", right_type="pv",
                  description="applied/suggest")
```

#### 添加人均指标
```python
# 方式 1: PV / UV（按指标自身列去重用户数计算人均）
editor.add_metric(0, "人均新消息数", "T1:new_message_cnt", left_type="pv",
                  right_key_sql="T1:new_message_cnt", right_type="uv",
                  description="人均消息数")

# 方式 2: PV / base_user（按实验组全体用户数计算人均，推荐用于商业化等指标）
# right_type="base_user" 时不需要 right_key_sql，分母自动为实验组全部进组用户数
editor.add_metric(0, "人均订单金额", "T1:order_amount", left_type="pv",
                  right_type="base_user",
                  description="每用户平均订单金额，SUM(order_amount)/实验组用户数")
```

> **PV/UV vs PV/base_user 区别**：
> - `right_type="uv"` + `right_key_sql="T1:col"`：分母 = 该列有值的去重用户数（仅有行为的用户）
> - `right_type="base_user"`：分母 = 实验组全体进组用户数（含无行为的用户），适用于"整体人均"场景

#### 更新指标
```python
editor.update_metric(0, "消息数", name="消息总数", description="更新后的描述")
editor.update_metric(0, "消息数", left_key_sql="T1:new_col")
```

#### 删除指标
```python
editor.remove_metric(0, "旧指标名称")
```

### 维度操作

#### 列出维度
```python
dims = editor.list_dimensions(0)
```

#### 添加维度
```python
editor.add_dimension(0, "新维度", "T1:new_dim_col",
                     dim_type="METRIC_DIMENSION", description="新增维度")
```
`dim_type` 可选值：`"METRIC_DIMENSION"`（指标维度）或 `"USER_DIMENSION"`（用户维度）。

#### 更新维度
```python
editor.update_dimension(0, "维度名称", dim_type="USER_DIMENSION")
editor.update_dimension(0, "维度名称", name="新名称", key="T1:new_col")
```

#### 查看维度高级配置
```python
conf = editor.get_dimension_conf(0, "维度名称")
```

#### 设置维度高级配置
维度的 `conf` 包含高级配置选项，通过 `update_dimension` 的 `conf` 参数增量更新。`use_conf=True` 是总开关，各选项之间相互独立，可自由组合。

默认不开启高级配置（`use_conf=False`），只有有额外需求时才按需开启。例如，需要改为仅现查 + 按首次进组取值 + 强制同步最新：

```python
editor.update_dimension(0, "维度名称", conf={
    "use_conf": True,
    "use_types": "MDS",
    "update_type": "first",
    "enums_update_type": "force",
})
```

**`use_types`（维度使用方式）可选值：**
| 值 | 说明 |
|-----|------|
| `"RPT"` | 预刷+现查（默认） |
| `"MDS"` | 仅现查 |
| `"EXTERNAL"` | 外部数据现查 |
| `"RPT_ONLY"` | 仅预刷 |

**`update_type`（维度值更新策略）可选值：**
| 值 | 说明 |
|-----|------|
| `"first"` | 按首次进组取值（默认） |
| `"last"` | 按最新取值 |
| `"t1"` | 固定进组前 N 天值（如 t1 = 前一天） |
| `"GREATEST"` | 取最大值 |

**`enums_update_type`（枚举值更新逻辑）可选值：**
| 值 | 说明 |
|-----|------|
| `"merge"` | 合并所有枚举值（默认） |
| `"force"` | 强制同步最新 |
| `"init"` | 仅首次初始化 |

**其他高级选项（布尔开关，各自独立）：**
| 选项 | 说明 | 相关字段 |
|------|------|---------|
| `use_custom` | 自定义 SQL 维度 | `custom_sql`（SQL 内容） |
| `use_num` | 数值维度 | — |
| `use_split` | 维度拆分 | `split_suffix`（拆分后缀） |
| `use_combine` | 组合字段维度 | `combine_fields`（字段列表） |
| `use_base_user` | 基准用户 | `base_user_type`（用户类型） |
| `is_ablog_dim` | 从 AB 日志取维度 | — |
| `use_libra_key` | 使用 Libra Key | `libra_key`（Key 值） |
| `enums_filter` | 枚举过滤 | `enums`（枚举列表） |
| `is_query` | 圈选 Query 维度 | 特殊维度，`dim_type` 和 `key` 均为空 |

示例：设置自定义 SQL 维度
```python
editor.update_dimension(0, "维度名称", conf={
    "use_conf": True,
    "use_custom": True,
    "custom_sql": "SELECT ... FROM ...",
})
```

示例：设置枚举过滤
```python
editor.update_dimension(0, "维度名称", conf={
    "use_conf": True,
    "enums_filter": True,
    "enums": [{"name": "value1", "description": "描述1"}, {"name": "value2", "description": "描述2"}],
    "enums_update_type": "force",
})
```

#### 重置维度高级配置
```python
# 单个重置
editor.reset_dimension_conf(0, "维度名称")

# 批量重置多个维度
editor.reset_dimensions_conf(0, ["维度A", "维度B", "维度C"])
```

#### 删除维度
```python
editor.remove_dimension(0, "旧维度名称")
```

### 保存和校验

```python
print(editor.diff())
editor.save(dry_run=True)
editor.save()
# save() 成功后会自动从服务端重新加载数据，确保本地状态与服务端一致
# save() 保存后自动 reload，无需手动刷新
```

### 上线管理

**重要：上线功能默认不执行，只有用户明确要求"上线"时才调用。**

#### 发起上线
```python
result = editor.submit_online()  # 上线需求中的所有指标组
# 或指定指标组
result = editor.submit_online(group_names=["指标组名称"])
# 指定开发负责人
result = editor.submit_online(develop_owner="jinrubin")
# 启用回刷
result = editor.submit_online(backfill=True)
```

上线流程会自动执行 5 个步骤：上线检查 → 检查已有上线流程 → LLM 预检查 → 创建状态机 → 触发 CREATE_REQUEST。指标组必须先 `save()` 才有 `id`，才能上线。

参数说明：
- `group_names`：要上线的指标组名称列表，不传则上线所有指标组
- `develop_owner`：开发负责人，不传则自动探测当前用户
- `deploy_mode`：部署模式，默认 `"normal"`
- `backfill`：是否启用回刷，默认 `False`

#### 查看上线状态
```python
status = editor.get_online_status()
# 返回 dict，包含: instance_id, group_ids, current_state, finished 等
# 状态机典型进度: EDIT → FILLIN → AUTH_CHECK → PRE_CHECK → IN_PROGRESS → BACK_FILL0 → FINISHED
```

#### 取消上线
```python
editor.cancel_online()
```

### 辅助查询

#### 自动探测当前配置
```python
owner = client.auto_detect_owner()       # 自动获取当前登录用户名
business = client.auto_detect_business()  # 自动获取关联业务线 ID
ablog = client.auto_detect_ablog()        # 自动获取 business_id, business_key, apps
# ablog 返回: {"business_id": 261, "business_key": "basic", "apps": ["1190"]}
```

#### 获取应用列表（创建指标组时需要 app_id）
```python
apps = client.get_apps()
```

#### 查询 Meego 业务线（获取 business ID）
```python
biz_list = client.get_meego_business()
```

#### 查询 Meego 工单信息
```python
meego = client.get_meego_info("6879875156")
```

#### 获取 AB 日志 SQL
```python
ab_log = client.get_ab_log_sql()  # 参数从 config.yaml 自动读取
```

#### 获取 Business 配置详情
```python
detail = client.get_business_detail(261)  # 查看 AB 日志配置、app_ids 等
```

#### 查看需求修改历史和状态
```python
history = client.get_ticket_history(ticket_id)
state = client.get_ticket_state(ticket_id)
```

#### 查看版本/快照
```python
# 列出所有版本
editor = TicketEditor(client, ticket_id)
snapshots = editor.list_snapshots()
# 返回: [{"snapshot_id": 30, "status": "HISTORY", "online_time": "...", ...}, ...]

# 加载指定版本的数据（只读）
snapshot_editor = TicketEditor(client, ticket_id, snapshot_id=30)
groups = snapshot_editor.list_groups()
summary = snapshot_editor.get_summary()
```

#### 获取标签和公共维度
```python
tags = client.get_all_tags()
decc_dims = client.get_decc_dims()
```

### 刷新 Cookie
```python
client.refresh_cookie()
```

## CLI 用法

> 所有命令必须通过 venv 执行。如果 venv 尚未创建，请先按"前置条件"初始化。
> 支持 `--env cn|i18n` 参数切换环境，传入海外 URL 时会自动检测环境。

```bash
scripts/.venv/bin/python scripts/libra_gallery_api.py detect
scripts/.venv/bin/python scripts/libra_gallery_api.py --env i18n detect
scripts/.venv/bin/python scripts/libra_gallery_api.py list-tickets [owner]
scripts/.venv/bin/python scripts/libra_gallery_api.py --env i18n list-tickets [owner]
scripts/.venv/bin/python scripts/libra_gallery_api.py list-groups [owner] [--status ONLINE|OFFLINE]
scripts/.venv/bin/python scripts/libra_gallery_api.py --env i18n list-groups [owner] [--status ONLINE]
scripts/.venv/bin/python scripts/libra_gallery_api.py info 65562
scripts/.venv/bin/python scripts/libra_gallery_api.py info 'https://libra-gallery.bytedance.net/#/metric/set/detail/65562'
scripts/.venv/bin/python scripts/libra_gallery_api.py info 'https://libra-gallery-us.tiktok-row.net/#/metric/set/detail/37561'
scripts/.venv/bin/python scripts/libra_gallery_api.py groups 65562
scripts/.venv/bin/python scripts/libra_gallery_api.py metrics 65562 0
scripts/.venv/bin/python scripts/libra_gallery_api.py dims 65562 0
scripts/.venv/bin/python scripts/libra_gallery_api.py datasources 65562
scripts/.venv/bin/python scripts/libra_gallery_api.py datasource-sql 65562 T1
scripts/.venv/bin/python scripts/libra_gallery_api.py save 65562
scripts/.venv/bin/python scripts/libra_gallery_api.py history 65562
scripts/.venv/bin/python scripts/libra_gallery_api.py snapshot-info 65562 30
scripts/.venv/bin/python scripts/libra_gallery_api.py snapshot-groups 65562 30
```

### 指标验证场景的推荐 CLI 流程

当需要验证 Libra 指标的数据正确性时，推荐按以下顺序使用 CLI：

```bash
# 1. 查看需求概要和指标组列表
scripts/.venv/bin/python scripts/libra_gallery_api.py info <ticket_id_or_url>
scripts/.venv/bin/python scripts/libra_gallery_api.py groups <ticket_id>

# 2. 查看目标指标组的指标定义（了解 left/right key_sql、PV/UV 类型）
scripts/.venv/bin/python scripts/libra_gallery_api.py metrics <ticket_id> <group_index>

# 3. 查看维度定义（了解指标的分组维度逻辑）
scripts/.venv/bin/python scripts/libra_gallery_api.py dims <ticket_id> <group_index>

# 4. 查看数据源 SQL（理解数据来自哪些上游表、JOIN 逻辑、过滤条件）
scripts/.venv/bin/python scripts/libra_gallery_api.py datasources <ticket_id>
scripts/.venv/bin/python scripts/libra_gallery_api.py datasource-sql <ticket_id> T1

# 5. 查看 AB 进组口径 SQL（了解 Libra 如何获取实验进组用户）
# 在 Python 中：
#   from libra_gallery_api import LibraGalleryClient
#   client = LibraGalleryClient()
#   ab_log = client.get_ab_log_sql()
```

> **关键发现指标计算逻辑的方法**：`datasource-sql` 输出完整 SQL，其中的 JOIN 条件和 WHERE 过滤揭示了数据口径；`metrics` 输出的 `left_key_sql` / `right_key_sql` / `left_type` / `right_type` 定义了指标的聚合方式。两者结合即可完整理解指标计算逻辑。

## 完整功能列表

### LibraGalleryClient（底层 API）
- `LibraGalleryClient(env="cn")` - 构造函数，`env` 可选 `"cn"` 或 `"i18n"`，自动确定 API 地址和默认区域
- `auto_detect_owner()` - 自动探测当前用户名（config.yaml → Cookie 解析）
- `auto_detect_business()` - 自动探测关联业务线 ID（config.yaml → quick_query API）
- `auto_detect_ablog()` - 自动探测 AB 日志配置：business_id、business_key、apps（config.yaml → quick_query + business detail API）
- `get_ticket(ticket_id, region, snapshot_id)` - 获取 Ticket 完整数据，`snapshot_id` 可选，指定后返回该版本的数据
- `create_ticket(name, owner, meego_id, virtual_table, groups, description, business, region)` - 创建新需求，`virtual_table` 和 `groups` 用于从模板初始化
- `delete_ticket(ticket_id, region)` - 删除需求，自动打印结果（region 由 env profile 自动确定）
- `list_tickets(owner, page, page_size, region)` - 列出需求
- `list_all_groups(owner, name, status)` - 查询某个 owner 的所有指标组（自动分页遍历所有需求并提取 groups），可按 develop_status 过滤
- `parse_sql(sql)` - 解析 SQL 获取列信息
- `validate_ttp_sql(region, sql)` - TTP 区域 SQL 校验（海外独有，region 可选 `"eu_ttp"` 或 `"us_ttp"`）
- `save_check(virtual_table, ticket)` - 保存前校验
- `save_ticket(virtual_table, ticket)` - 保存 Ticket
- `apply_for_edit(ticket_id, user)` - 申请编辑权
- `get_access()` - 获取权限信息
- `get_group_online_set(ticket_id)` - 获取线上配置
- `get_business_list()` - 获取业务线列表
- `get_business_tags()` - 获取业务标签列表
- `get_apps(region)` - 获取应用列表（创建指标组时需要 app_id）
- `get_meego_info(meego_id)` - 获取 Meego 工单详情
- `get_meego_business(item_id, business_id)` - 查询 Meego 业务线列表（POST，树形结构）
- `get_business_detail(business_id)` - 获取单个 Business 配置详情（AB日志配置、阈值等）
- `get_ab_log_sql(business_id, business_key, user_types, app_ids)` - 获取 AB 实验日志 SQL
- `get_certification_config()` - 获取认证中心配置规则
- `get_dim_tags()` - 获取维度标签列表
- `get_cm_config()` - 获取 Column Mapping 配置元数据
- `get_follow_flights()` - 获取关注的实验列表
- `get_users()` - 获取用户列表
- `get_ticket_history(ticket_id)` - 获取需求修改历史
- `get_ticket_online_history(ticket_id)` - 获取需求上线历史
- `get_ticket_state(ticket_id, group_ids)` - 获取需求/指标组状态
- `get_all_tags()` - 获取所有指标组标签
- `get_decc_dims()` - 获取 DECC 公共维度列表
- `get_dim_versions(dim_id)` - 获取公共维度的版本列表
- `refresh_cookie()` - 从 Chrome 刷新 Cookie
- `online_check(group_ids, deploy_mode)` - 上线前校验
- `llm_online_prechecks(group_ids, develop_owner, ...)` - LLM 上线预检查
- `create_online_state(ticket_id, group_ids, ...)` - 创建上线状态机实例
- `trigger_state_event(event, ticket_id, group_ids, ...)` - 触发状态机事件
- `cancel_online(ticket_id, group_ids, ...)` - 取消上线
- `get_mark_list()` - 获取标记列表
- `get_quick_query_business(username)` - 快速查询 business
- `get_cm_users()` - 获取 CM 用户列表

### TicketEditor（高级操作）
- `TicketEditor(client, ticket_id, snapshot_id=None)` - 构造函数，`snapshot_id` 可选，指定后加载该版本的数据（只读快照）
- `create_new(client, name, owner, meego_id, description, business, region)` - 类方法，创建空需求并返回 TicketEditor
- `create_from(client, source_editor, source_group_names=None, new_ticket_name=None, owner, meego_id, rename_map, description, business, copy_data_sources, region)` - 类方法，从源需求克隆指标组到新需求。`source_group_names=None` 时复制所有指标组（等价于"复制整个需求"），`new_ticket_name=None` 时沿用源需求名称
- `create_from_snapshot(client, source_ticket_id, snapshot_id, source_group_names, ...)` - 类方法，从指定版本克隆指标组到新需求
- `load()` - 加载 Ticket 数据
- `find_group(name, group_id)` - 查找指标组
- `list_groups()` - 列出所有指标组
- `list_metrics(group)` - 列出指标
- `list_dimensions(group)` - 列出维度（包含高级配置状态，启用时显示 use_types/update_type/enums_update_type 和已启用选项）
- `list_data_sources()` - 列出所有数据源及其列信息
- `list_snapshots()` - 列出需求的所有版本/快照历史
- `get_data_source_sql(vt_name)` - 获取数据源 SQL
- `add_data_source(key, sql, source_type, region, dorado_region, id_type)` - 添加新数据源。`id_type` 可选 `"user_unique_id"`（默认）或 `"user_id"`（UID 粒度）；国内 env 会自动构建 conf（`regions`/`regions_cn_conf`），海外 env 默认 conf 为空（后端自动处理），也可传 region 显式指定
- `remove_data_source(key)` - 删除数据源
- `rename_data_source(old_key, new_key)` - 重命名数据源 key 并自动更新所有指标/维度引用
- `add_metric(group, ...)` - 添加指标
- `remove_metric(group, name)` - 删除指标
- `update_metric(group, name, ...)` - 更新指标
- `add_dimension(group, ...)` - 添加维度
- `remove_dimension(group, name)` - 删除维度
- `update_dimension(group, name, ...)` - 更新维度（修改 dim_type/名称/key/高级配置等）
- `reset_dimension_conf(group, name)` - 重置单个维度高级配置为默认值
- `reset_dimensions_conf(group, dim_names)` - 批量重置多个维度的高级配置为默认值
- `get_dimension_conf(group, name)` - 获取维度的完整高级配置
- `update_data_source_sql(vt_name, sql, column_remap=None)` - 更新数据源 SQL。`column_remap` 可选，传入 `{"old_col": "new_col"}` 可自动更新指标/维度中引用旧列名的 key；不传时若检测到列名变化会打印警告
- `add_group(name, ...)` - 添加新指标组。支持 `user_id_type=["USER"]` 指定 UID 粒度（默认 `["USER_UNIQUE_ID"]`），UID 粒度时自动调用 `get_ab_log_sql(user_types="USER")` 获取对应的 AbLog SQL
- `update_group(group, ...)` - 更新指标组属性（名称/owner/apps/描述等）
- `remove_group(group)` - 删除指标组
- `clone_group(source_group_name, new_name, vt_name)` - 同需求内克隆指标组
- `clone_group_from(source_editor, source_group_name, new_name, vt_name, copy_data_sources)` - 跨需求克隆指标组
- `save(dry_run)` - 保存（校验未通过时抛出 `RuntimeError` 中止保存；成功后自动打印 Gallery 链接，自动从服务端重新加载数据确保一致性）
- `diff()` - 查看变更差异
- `get_summary()` - 获取概要信息（含 `url` 字段）
- `submit_online(group_names, develop_owner, deploy_mode, backfill)` - 发起上线（**仅用户要求时调用**）
- `cancel_online(group_names, develop_owner, deploy_mode)` - 取消上线
- `get_online_status()` - 查看上线状态

### 辅助函数
- `gallery_url(ticket_id, env)` - 生成 Gallery 详情页链接
- `extract_ticket_id(url_or_id)` - 从 URL 或数字中提取 ticket_id
- `detect_env_from_url(url_or_id)` - 从 URL 自动判断环境（返回 `"cn"` 或 `"i18n"`）
- `auto_get_cookie(domain, env)` - 自动从 Chrome 获取 Cookie
- `make_metric(...)` - 创建指标数据结构
- `make_dimension(...)` - 创建维度数据结构
- `make_default_metric_conf(...)` - 创建默认指标配置
- `make_default_dimension_conf(...)` - 创建默认维度配置

## 使用约束与注意事项

- **Cookie 安全**：`scripts/cookie.txt` 和 `scripts/cookie_i18n.txt` 包含敏感凭证，已通过 `scripts/.gitignore` 忽略，不会提交到代码仓库。
- **多行 SQL 保持格式**：数据源 SQL 应保持多行缩进格式（包含 `\n` 换行符），这样在 Gallery 页面上才能正常阅读。**不要通过 `python -c "..."` 命令行传递多行 SQL**——shell 会将换行符吞掉，导致 SQL 变成一行。推荐做法：先用 Write 工具将 SQL 写入 `.sql` 文件（如 `T1.sql`），然后在代码中传文件路径 `editor.add_data_source("T1", sql="T1.sql")`，脚本会自动检测 `.sql` 后缀并读取文件内容。`.sql` 文件查找顺序：当前工作目录 → 脚本所在目录（`scripts/`）。
- **数据源 SQL 列名变更会导致指标/维度引用丢失**：如果 `update_data_source_sql` 后外层 SELECT 的列名发生变化（如字段重命名），已有指标和维度中引用旧列名的 key 会在保存时失效。正确做法是使用 `column_remap` 参数：`editor.update_data_source_sql("T1", new_sql, column_remap={"old_col": "new_col"})`，这会自动更新指标和维度中的列引用。如果不传 `column_remap`，脚本会打印警告并列出受影响的指标/维度，提示你添加映射。详见工作流 9。
- **保存不上线**：`save()` 只保存草稿，不会触发上线流程。校验不通过时会抛出 `RuntimeError` 中止保存，可先用 `save(dry_run=True)` 预检查。
- **保存后自动重载**：`save()` 成功后会自动调用 `load()` 从服务端重新加载数据，确保本地状态与服务端一致。因此 save 后可以继续用 editor 做后续操作，无需重新创建 TicketEditor。
- **保存时自动清洗数据**：`save()` 提交前会通过 `_prepare_for_save()` 自动清洗数据，确保提交格式与浏览器行为一致。具体包括：ticket/group/metric/dimension 按字段白名单过滤，剥离服务端只读字段（如 `is_draft`、`status`、`create_time` 等）；`columns[].key` 在 `load()` 阶段已从 UUID 转换为可读列名并移除 `columns[].id`；`ticket.id` 始终使用构造时的原始 ID（避免上线后版本 ticket id 被误用）；引用公共维度的维度（如"圈query"，`pub_dim_id` 非空）会自动补充 `draft_id` 和 `version_id`。
- **完整数据提交**：PUT 请求需要提交完整的 Ticket 数据（所有 groups、所有 metrics、所有 dimensions），不能只提交增量。
- **新指标组 id 处理**：向已有需求添加新指标组时，新 group 不能有 `id` 字段（完全不包含，而非设为 `None`/`null`）。`clone_group`、`clone_group_from`、`add_group` 已正确处理。
- **数据源 SQL 与列引用格式的区别**（易混淆，务必注意）：
  - **数据源 SQL**（`add_data_source` / `update_data_source_sql` 的 `sql` 参数）：是**纯 Hive SQL**，SELECT 中的列名/别名**不带** `Tx:` 前缀。例如 `SELECT did AS user_unique_id, agent_type, SUM(cnt) AS cnt FROM table WHERE date='${date}' GROUP BY ...`
  - **指标和维度中的列引用**（`add_metric` 的 `left_key_sql`/`right_key_sql`、`add_dimension` 的 `key`）：使用 `Tx:column_name` 格式引用数据源 SQL 中 SELECT 出的列。例如 `T1:agent_type`、`T2:message_cnt`
  - 简单记忆：**SQL 里不写 `Tx:`，引用列时才写 `Tx:`**
- **指标组上限**：每个需求最多 10 个指标组。
- **累计开始时间格式**：`cum_start_time` 必须使用 `yyyy-MM-dd` 格式（如 `"2026-04-01"`），不能用 `yyyyMMdd`（如 `"20260401"`），否则 Gallery 校验不通过。
- **指标类型可选值**：`left_type`/`right_type` 可选 `pv`（求和）、`uv`（去重计数）和 `base_user`（实验组全体用户数，仅 right_type 可用），**没有 `pv_distinct`**。需要对某列去重计数时使用 `uv`。`right_type="base_user"` 时不需要 `right_key_sql`，分母自动为实验组全部进组用户数。
- **save() 安全保护（防清空）**：`save()` 方法在提交前会自动检测是否会意外清空指标或维度。如果原有指标/维度数量 > 0 但待提交数据中为 0，会立即抛出 `RuntimeError` 中止保存，避免 PUT 全量替换导致数据丢失。如确实需要清空，应使用 `remove_metric()` / `remove_dimension()` 逐个删除后再 save。
- **批量修改指标类型时的注意事项**：通过 `update_metric()` 修改 `right_type` 为 `base_user` 时，脚本会自动确保 `sql.right` 结构完整（`key=None, key_sql="", type="base_user"`）。但由于 Gallery PUT 接口的全量替换特性，**强烈建议在批量修改前先 `save(dry_run=True)` 预检查**，确认没有校验问题后再正式保存。
- **数据源 SQL 列名注意**：如遇到 `device_id`/`user_id` 相关的校验报错，可尝试用子查询包裹（详见"数据源 SQL 常见校验问题及解决方案"）。
- **数据源 SQL 必须输出 date 字段**：外层 SELECT 必须包含 `date` 列，否则保存时报"原始 SQL 中未输出 date 字段"。
- **数据源 SQL 字符串引号**：SQL 中所有字符串值必须使用单引号（`'${date}'`、`'success'`），不能使用双引号。
- **上线需用户明确要求**：`submit_online()` 只在用户明确说"上线"时才调用，默认操作仅保存草稿。

## References

按需读取：
- `references/api-reference.md`：完整的 API 端点说明、请求/响应格式、数据模型。
