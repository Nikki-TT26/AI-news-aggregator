# Libra Gallery API Reference

## Base URL
- 中国机房：`https://libra-gallery.bytedance.net`
- 海外机房：`https://libra-gallery-us.tiktok-row.net`

Base URL 由 `LibraGalleryClient(env=...)` 自动确定。

## 鉴权
所有请求通过 Cookie 鉴权，核心 Cookie：
- `bd_sso_3b6da9` — SSO JWT Token（RS256签名，约7天有效期）
- `door_username` + `door_username.sig` — Door 网关用户身份
- `door_nickname` + `door_nickname.sig` — Door 网关昵称
- `titan_passport_id` — Titan Passport 身份标识

海外机房通过 TikTok SSO 鉴权（`sso.tiktok-intl.com`），核心 Cookie 字段与中国机房相同（`bd_sso_3b6da9`、`door_username` 等），但两个域名的 Cookie **不通用**（SSO 签发的 JWT token 的 issuer 不同），需要分别在对应平台登录获取。Cookie 域名由 env 自动确定。

## API 通用性

海外机房和中国机房的 API 路径完全一致（都是 `/v1/` 前缀），所有 CRUD 操作（创建需求、获取需求、删除需求、保存、上线等）均通用。区别仅在于：
1. 域名不同（`libra-gallery.bytedance.net` vs `libra-gallery-us.tiktok-row.net`）
2. 部分参数默认值不同（region、dorado_regions 等）
3. 海外独有 `POST /v1/sql/validation/ttp` API

所有 region 相关的值在 API 中均为**全小写、下划线分隔**格式：`cn`、`va`、`sg`、`mya`、`eu_ttp`、`us_ttp`、`i18n`。前端界面展示的大写/连字符格式（如 `EU-TTP`、`US-TTP`、`ROW`）仅用于 UI 展示，不是 API 实际使用的值。

## API 端点

### 1. GET /v1/ticket/{ticket_id}
获取 Ticket 完整数据。

**参数：**
- `ticket_id` (path) — Ticket ID
- `region` (query) — 区域，由 env 决定，cn 环境默认 `cn`，i18n 环境默认 `va`
- `snapshot_id` (query, 可选) — 版本快照 ID。不传则返回当前草稿数据，传入后返回该历史版本的完整数据（包含当时的 groups、virtual_table 等）。版本号可通过 `GET /v1/ticket/history` 获取

**响应结构：**
```json
{
  "code": 0,
  "data": {
    "ticket": {
      "id": 65562,
      "name": "Trae Libra 指标建设-效果、规模、反馈、工具",
      "owner": ["zhanfurong", "baijingjing.11"],
      "description": "",
      "meego_id": 0,
      "region": "cn",
      "business": "6278dce74031efe78e5bfc9d",
      "is_draft": 1,
      "is_edit": 1,
      "status": "offline",
      "snapshot_id": "...",
      "version_id": "...",
      "groups": [
        {
          "id": 134624,
          "name": "[Libra]AI行为_Chat_效果指标(设备维度)_分意图",
          "libra_group_id": 195339,
          "user_id_type": ["USER_UNIQUE_ID"],
          "apps": ["1190"],
          "group_type": "action_cuped",
          "is_cum": 1,
          "cum_start_time": "2025-09-15",
          "cum_type": "ENTER_ONCE_ALWAYS_COUNT",
          "dorado_regions": "cn",  // cn 环境为 "cn"，i18n 环境默认为 "sg"（可选 va/mya/eu_ttp/us_ttp）
          "owner": ["zhanfurong"],
          "ablog_config": {
            "use_type": "custom",
            "business_list": [{"business_id": 261, "business_key": "basic"}],
            "remove_app": "true",
            "abLogSqlPreview": "select CAST(version_id as BIGINT) as vid, user_unique_id, ...",
            "defaultAbLogSqlPreview": "select CAST(version_id as BIGINT) as vid, user_unique_id, ..."
          },
          "metrics": [...],
          "dimensions": [...]
        }
      ]
    },
    "virtual_table": [
      {
        "key": "7754d523b97c4a3e8f3c623211a2144c",  // GET 返回 UUID
        "name": "T1",
        "mapping_detail": {
          "user_unique_id": {
            "type": "user_unique_id",
            "name": "T1_user_unique_id",
            "sql": "SELECT ...",
            "sourceType": "customize",
            "dc": "row",
            "primary_dest_region": "cn",
            "preSqlColumns": [
              {"key": "col_uuid", "name": "column_name", "data_type": "STRING", "is_pk": "0"}
            ]
          }
        },
        "columns": [
          {"key": "col_uuid", "name": "column_name", "data_type": "STRING", "is_pk": "0"}
        ]
      }
    ]
  }
}
```

**重要：** GET 响应中的引用使用 UUID 格式：`tableUUID:columnUUID`

### 2. PUT /v1/ticket/
保存 Ticket（只保存草稿，不上线）。

**请求体：**
```json
{
  "virtual_table": [
    {
      "key": "T1",  // PUT 时使用简称
      "name": "T1",
      "mapping_detail": { ... },
      "columns": [ ... ],
      "conf": { "regions": ["cn"], "regions_cn_conf": { "dorado_region": "cn" } }
      // 海外: conf 一般为空对象 {}（后端自动处理），如需显式指定:
      // "conf": { "regions": ["sg"], "regions_sg_conf": { "dorado_region": "sg" } }
    }
  ],
  "ticket": {
    "id": 65562,
    "name": "...",
    "owner": [...],
    "groups": [
      {
        "id": 134624,
        "metrics": [
          {
            "name": "消息数",
            "description": "message_cnt",
            "sql": {
              "left": { "key": ["T1:message_cnt"], "key_sql": "T1:message_cnt", "type": "pv" },
              "right": { "key": null, "key_sql": "", "type": "" }
            },
            "conf": { ... }
          }
        ],
        "dimensions": [
          {
            "name": "意图类别",
            "dim_type": "METRIC_DIMENSION",
            "key": ["T1:intent"],
            "conf": { ... }
          }
        ]
      }
    ]
  }
}
```

**重要：** PUT 时引用使用名称格式：`T1:column_name`

**响应：**
```json
{
  "code": 0,
  "data": {
    "ticket": { ... },
    "virtual_table": [ ... ]
  }
}
```

### 3. POST /v1/ticket/save_check
保存前校验。请求体与 PUT 相同，但包裹在 `ticket_data` 中。

**请求体：**
```json
{
  "ticket_data": {
    "virtual_table": [...],
    "ticket": { ... }
  }
}
```

**响应：**
```json
{
  "code": 0,
  "data": null,
  "message": ""
}
```

### 4. POST /v1/sql/parse
解析 SQL 获取列信息。

**请求体：**
```json
{
  "sql": "SELECT did AS user_unique_id, ..."
}
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "columns": [
      {"name": "user_unique_id", "data_type": "STRING"},
      {"name": "message_cnt", "data_type": "BIGINT"}
    ]
  }
}
```

### 5. GET /v1/ticket/apply_for_edit
申请编辑权限。

**参数：**
- `ticket_id` (query) — Ticket ID
- `user` (query) — 用户名

### 6. GET /v1/access
获取当前用户权限信息。

### 7. GET /v1/ticket/group_online_set
获取各指标组的线上配置。

**参数：**
- `ticket_id` (query) — Ticket ID

### 8. GET /v1/ticket/history
获取 Ticket 的修改/上线版本历史。返回所有快照版本列表，可用于获取 `snapshot_id` 供 `GET /v1/ticket/{ticket_id}?snapshot_id=` 使用。

**参数：**
- `ticket_id` (query) — Ticket ID

**响应：**
```json
{
  "code": 200,
  "data": [
    {
      "snapshot_id": 31,
      "status": "ONLINE",
      "online_status": "draft",
      "online_time": "2026-02-09 18:54:39",
      "online_operator": "baijingjing.11",
      "online_config": {
        "group_ids": [135124],
        "flights": ["4545811", "4538005"],
        "developOwner": "baijingjing.11"
      },
      "online_groups": []
    },
    {
      "snapshot_id": 30,
      "status": "HISTORY",
      "online_status": "online",
      "online_time": "2026-01-07 13:13:22",
      "online_operator": "baijingjing.11",
      "online_config": {
        "group_ids": [139280, 138941],
        "flights": ["4545811", "4538005", "4599390", "4678165", "4660702"]
      },
      "online_groups": [138941, 139280]
    },
    {
      "snapshot_id": 0,
      "status": "DRAFT",
      "online_status": "draft",
      "online_time": "2025-11-13 20:14:12",
      "online_operator": "baijingjing.11"
    }
  ]
}
```

**字段说明：**
- `snapshot_id` — 版本号，0 为初始草稿
- `status` — 版本状态：`DRAFT`（草稿）、`HISTORY`（历史版本）、`ONLINE`（当前在线版本）
- `online_groups` — 该版本上线涉及的指标组 ID 列表
- `online_config.group_ids` — 该版本配置涉及的指标组 ID 列表

### 9. GET /v1/ticket/ticket_online_history
获取 Ticket 的上线历史。

**参数：**
- `ticket_id` (query) — Ticket ID

### 10. GET /v1/ticket/group/stable/{libra_group_id}
检查指标组稳定性。

**参数：**
- `libra_group_id` (path) — Libra 指标组 ID
- `gallery_id` (query) — Gallery Ticket ID

### 11. GET /v1/state/{ticket_id}
获取上线状态机信息。

### 12. POST /v1/ticket/
创建新 Ticket。

**请求体：**
```json
{
  "virtual_table": [
    {
      "key": "T1",
      "name": "T1",
      "mapping_detail": {
        "user_unique_id": {
          "type": "user_unique_id",
          "dc": "row",
          "primary_dest_region": "cn",
          "sql": "SELECT ...",
          "keep_consistant_in_multi_dc": true,
          "preSqlColumns": [...]
        }
      },
      "columns": [...],
      "conf": { "regions": ["cn"], "regions_cn_conf": { "dorado_region": "cn" } }
      // 海外: conf 一般为空对象 {}（后端自动处理），如需显式指定:
      // "conf": { "regions": ["sg"], "regions_sg_conf": { "dorado_region": "sg" } }
    }
  ],
  "ticket": {
    "name": "需求名称",
    "owner": ["zhanfurong"],
    "meego_id": 0,
    "description": "",
    "region": "cn",
    "business": "6278dce74031efe78e5bfc9d",
    "groups": [...]
  }
}
```

**字段说明：**
- `meego_id`: Meego 工单 ID。`0` = 待分配（不关联 Meego 工单），非零整数 = 关联指定 Meego Story
- `business`: Meego 业务线 ID。`"6278dce74031efe78e5bfc9d"` = "待分配"业务线。可通过 `POST /v1/meego/business` 查询
- `region`: 区域，由 env 决定默认值。cn 环境默认 `"cn"`，i18n 环境默认 `"va"`

**响应：**
```json
{
  "code": 200,
  "data": {
    "ticket": {
      "id": 90474,
      "name": "...",
      "meego_business": "6278dce74031efe78e5bfc9d",
      "meego_story_id": "7074960265",
      "owner": "zhanfurong",
      "region": "cn",
      "groups": [{ "id": 176056, ... }]
    }
  }
}
```

**注意：** 响应中 `meego_business` 和 `meego_story_id` 是拆分后的字段，对应请求中的 `business` 和 `meego_id`。

### 13. DELETE /v1/ticket/{ticket_id}
删除 Ticket。

**参数：**
- `ticket_id` (path) — Ticket ID
- `region` (query) — 区域，由 env 决定，cn 环境默认 `cn`，i18n 环境默认 `va`

### 14. GET /v1/ticket/list
列出 Ticket。

**参数：**
- `pageNumber` (query) — 页码，默认 1
- `pageSize` (query) — 每页数量，默认 20
- `owner` (query) — 按负责人过滤
- `name` (query) — 按名称过滤
- `sort_key` (query) — 排序字段，默认 `update_time`
- `meego_business` (query) — 按 Meego 业务过滤
- `region` (query) — 区域
- `is_ad` (query) — 是否广告，默认 0

**响应结构：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "total": 5,
    "tickets": [
      {
        "id": 65562,
        "name": "需求名称",
        "status": "DEVELOPING",
        "owner": "zhanfurong",
        "create_time": "2024-12-01 10:00:00",
        "update_time": "2025-01-15 14:30:00",
        "meego_id": "...",
        "groups": [
          {
            "id": 123,
            "name": "指标组名称",
            "libra_group_id": 456,
            "sg_libra_group_id": 789,
            "owner": ["zhanfurong"],
            "develop_status": "ONLINE",
            "user_id_type": "...",
            "apps": ["1190"],
            "group_type": "normal",
            "is_cum": false,
            "cum_start_time": "",
            "cum_type": "",
            "dorado_regions": "cn",
            "ablog_config": {...},
            "metrics": [
              {
                "id": 1001,
                "name": "metric_name",
                "display_name": "指标显示名",
                "type": "bigint",
                "expression": "count(1)",
                "cuped_metric": ""
              }
            ],
            "dimensions": [
              {
                "id": 2001,
                "name": "dim_name",
                "display_name": "维度显示名",
                "type": "string"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**响应字段说明：**
- `data.total` — 满足过滤条件的 ticket 总数（用于分页计算）
- `data.tickets[].groups` — 该需求下的所有指标组，每个 group 包含完整的指标组配置
- `groups[].id` — Gallery 内部指标组 ID
- `groups[].libra_group_id` — 国内环境对应的 Libra 指标组 ID
- `groups[].sg_libra_group_id` — 海外环境对应的 Libra 指标组 ID（与 `libra_group_id` 互斥，取决于 env）
- `groups[].develop_status` — 指标组开发状态：`DEVELOPING`（开发中）、`ONLINE`（已上线）、`OFFLINE`（已下线）
- `groups[].owner` — 指标组负责人列表
- `groups[].apps` — 关联应用 ID 列表
- `groups[].dorado_regions` — Dorado 调度区域
- `groups[].metrics` — 指标定义列表
- `groups[].dimensions` — 维度定义列表

### 15. POST /v1/meego/business
查询 Meego 业务线列表（树形结构）。

**请求体：**
```json
{
  "item_id": 0,
  "business_id": "6278dce74031efe78e5bfc9d"
}
```

**响应（部分）：**
```json
{
  "code": 200,
  "data": [
    {"children": [], "id": "60c2cba5da03b4339a72ec5c", "name": "Tiktok(不包含直播/电商)"},
    {"children": [...], "id": "621754338f8ed924fd64f19b", "name": "抖音"},
    {"children": [], "id": "6278dce74031efe78e5bfc9d", "name": "待分配"},
    ...
  ]
}
```

**说明：** `"待分配"` 对应 `id: "6278dce74031efe78e5bfc9d"`，是创建需求时 `business` 字段的默认值。

### 16. POST /v1/business/online/ab_log_v2
获取 AB 实验日志 SQL 配置。

**请求体：**
```json
{
  "business_id": 261,
  "business_key": "basic",
  "user_types": "USER_UNIQUE_ID",
  "app_ids": ["1190"]
}
```

`user_types` 可选值：
- `"USER_UNIQUE_ID"` — 设备维度（默认），返回的 SQL 中使用 `user_unique_id` 列
- `"USER"` — UID 维度，返回的 SQL 中使用 `user_uid as user_id` 列

**响应：**
```json
{
  "code": 200,
  "data": {
    "ab_log_backfill_sql": "",
    "ablog_oeac_sql": "",
    "ablog_pks": [],
    "ablog_sql": "select CAST(version_id as BIGINT) as vid, ...",
    "keep_consistant_in_multi_dc": true
  }
}
```

### 17. GET /v1/business/{business_id}
获取单个 Business 配置详情。

**参数：**
- `business_id` (path) — Business ID（如 261）

**响应（部分）：**
```json
{
  "code": 200,
  "data": {
    "basic": {
      "app_ids": ["1190"],
      "name": "Trae CN",
      "metric_dim_threshold": "30",
      "metric_threshold": "10000"
    },
    "config": {
      "basic": {
        "ab_log": { ... }
      }
    }
  }
}
```

### 18. GET /v1/libra/certification_center_config
获取认证中心配置规则。

### 19. GET /v1/dim/tag_list
获取维度标签列表。

**响应：**
```json
{
  "code": 200,
  "data": {
    "tags": ["tea", "Libra官方配置", "测试", "电商推荐", ...]
  }
}
```

### 20. GET /v1/cm/config
获取 Column Mapping 配置元数据。

### 21. GET /v1/follow_flights
获取关注的实验列表。

### 22. GET /v1/users_v2
获取用户列表。

### 23. POST /v1/ticket/online/check
上线前校验。

**请求体：**
```json
{
  "group_list": [176056],
  "deploy_mode": "normal"
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "is_pass": true,
    "message": ""
  }
}
```

**说明：** 传入待上线的指标组 ID 列表和部署模式。`is_pass: true` 表示检查通过。

### 24. POST /v1/llm/online_prechecks
LLM 上线预检查。

**请求体：**
```json
{
  "group_ids": [176056],
  "user_form": {
    "flights": [],
    "developOwner": "jinrubin",
    "expected_backfill_date_range": [],
    "group_ids": [176056],
    "backfill": false,
    "ttp_list": [],
    "deploy_mode": "normal"
  }
}
```

**响应：**
```json
{
  "code": 200,
  "data": {},
  "message": "",
  "status": "success"
}
```

### 25. POST /v1/state/
创建上线状态机实例。

**请求体：**
```json
{
  "creator": "zhanfurong",
  "flights": [],
  "developOwner": "jinrubin",
  "expected_backfill_date_range": [],
  "group_ids": [176056],
  "backfill": false,
  "ttp_list": [],
  "deploy_mode": "normal",
  "meego_id": 7074960265,
  "ticket_id": "90474"
}
```

**响应：**
```json
{
  "code": 200,
  "data": [
    {
      "group_ids": [176056],
      "instance_id": 71256,
      "meego_id": 7074960265,
      "snapshot": 1,
      "state_machine": {
        "config": [...],
        "cur_machine_idx": 0,
        "model_id": 71256,
        "name": "normal",
        "select_idx": 0,
        "states": [
          {"id": 498831, "state": "EDIT", "status": "NOT_TRIGGERED"},
          {"id": 498832, "state": "FILLIN", "status": "NOT_TRIGGERED"},
          {"id": 498833, "state": "AUTH_CHECK", "status": "NOT_TRIGGERED"},
          {"id": 498834, "state": "PRE_CHECK", "status": "NOT_TRIGGERED"},
          {"id": 498835, "state": "IN_PROGRESS", "status": "NOT_TRIGGERED"},
          {"id": 498836, "state": "BACK_FILL0", "status": "NOT_TRIGGERED"},
          {"id": 498837, "state": "FINISHED", "status": "NOT_TRIGGERED"}
        ]
      }
    }
  ]
}
```

**状态机 7 个阶段：**
| 状态 | 名称 | 事件 |
|------|------|------|
| EDIT | Gallery 初始化 | CREATE_REQUEST → FILLIN |
| FILLIN | 填写上线工单中 | PARSE_REQUEST → AUTH_CHECK / CANCEL_ALL → EDIT |
| AUTH_CHECK | 权限校验 | AUTH_PASS → PRE_CHECK / AUTH_SKIP → PRE_CHECK |
| PRE_CHECK | 预校验 | FINISH_PRE_CHECK → IN_PROGRESS |
| IN_PROGRESS | 管理员上线中 | COMPLETE → BACK_FILL0 |
| BACK_FILL0 | 发起回溯 | BACK_FILL0_COMPLETE → FINISHED |
| FINISHED | 结束 | (终态) |

### 26. PUT /v1/state/event
触发状态机事件，推进上线流程。

**请求体：**
```json
{
  "event": "CREATE_REQUEST",
  "meego_id": 7074960265,
  "flights": [],
  "developOwner": "jinrubin",
  "expected_backfill_date_range": [],
  "group_ids": [176056],
  "backfill": false,
  "ttp_list": [],
  "deploy_mode": "normal",
  "operator": "zhanfurong",
  "ticket_id": "90474",
  "whitelist_auto_running": true
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "info": [],
    "output": null,
    "result": "WAITING"
  }
}
```

**可用事件：**
- `CREATE_REQUEST` - 发起上线 (EDIT → FILLIN)
- `PARSE_REQUEST` - 下一步 (FILLIN → AUTH_CHECK)
- `AUTH_PASS` / `AUTH_SKIP` - 权限校验通过/跳过 (AUTH_CHECK → PRE_CHECK)
- `FINISH_PRE_CHECK` - 预校验完成 (PRE_CHECK → IN_PROGRESS)
- `COMPLETE` - 上线完成 (IN_PROGRESS → BACK_FILL0)
- `BACK_FILL0_COMPLETE` - 回溯完成 (BACK_FILL0 → FINISHED)
- `CANCEL_ALL` - 取消上线 (任意状态 → EDIT)
- `REJECT_REQUEST` - 拒绝上线 (FILLIN → EDIT)

### 27. GET /v1/ticket/mark_list
获取标记列表。

### 28. GET /v1/business/list/quick_query
快速查询用户关联的 Business。

**参数：**
- `username` (query) — 用户名

### 29. GET /v1/cm_users
获取 CM 用户列表。

### 30. GET /v1/dim/versions
获取公共维度的版本列表。

**参数：**
- `dim_id` (query) — 公共维度 ID

**响应：**
返回该公共维度的版本列表，每个版本包含 conf、apps、attribute、business_id 等信息。

### 31. POST /v1/sql/validation/ttp
TTP 区域 SQL 校验（海外机房独有）。

**请求体：**
```json
{
  "region": "eu_ttp",
  "sql": "SELECT ..."
}
```

**参数：**
- `region` — TTP 区域：`eu_ttp` 或 `us_ttp`
- `sql` — 待校验的 SQL 语句

**响应：**
```json
{
  "code": 200,
  "data": null,
  "message": ""
}
```

## 数据模型

### VirtualTable（数据源）

数据源的 SQL 是**纯 Hive SQL**，不包含 `Tx:` 前缀。`Tx:column_name` 格式仅在 Metric 和 Dimension 的引用字段中使用。

SQL 中 SELECT 出的列名（或别名）就是后续 Metric/Dimension 用 `Tx:column_name` 引用的 `column_name` 部分。SQL 必须包含用户关联主键列：
- **设备维度**（`user_id_type=["USER_UNIQUE_ID"]`）：输出 `user_unique_id` 列（通常为 `did AS user_unique_id`）
- **UID 维度**（`user_id_type=["USER"]`）：输出 `user_id` 列（通常为 `user_id` 或 `xxx AS user_id`）

`mapping_detail` 结构根据 ID 粒度不同而不同：

**设备维度（默认）：**
```json
{
  "mapping_detail": {
    "user_unique_id": {
      "type": "user_unique_id",
      "name": "T1_user_unique_id",
      "sql": "SELECT did AS user_unique_id, ... FROM table WHERE date='${date}'",
      "sourceType": "customize",
      "dc": "row",
      "primary_dest_region": "cn",
      "preSqlColumns": [...]
    }
  }
}
```

**UID 维度：**
```json
{
  "mapping_detail": {
    "user_id": {
      "type": "user_id",
      "name": "T1_user_id",
      "sql": "SELECT user_id, ... FROM table WHERE date='${date}'",
      "sourceType": "customize",
      "dc": "row",
      "primary_dest_region": "sg",
      "preSqlColumns": [...]
    }
  }
}
```

```
数据源 SQL（纯 Hive SQL）                  指标/维度引用
─────────────────────────                ──────────────
SELECT                                   add_metric(0, "接受率",
  did AS user_unique_id,                     "T1:accepted_cnt",     ← 引用 SQL 中的 accepted_cnt 列
  agent_type,                                left_type="pv",
  SUM(accepted_cnt) AS accepted_cnt,         right_key_sql="T1:block_show_cnt",  ← 引用 SQL 中的 block_show_cnt 列
  SUM(block_show_cnt) AS block_show_cnt      right_type="pv")
FROM table
WHERE date = '${date}'                   add_dimension(0, "agent类型",
GROUP BY did, agent_type                     "T1:agent_type",       ← 引用 SQL 中的 agent_type 列
                                             dim_type="METRIC_DIMENSION")
```

### Metric（指标）

#### 简单指标（PV 类型）
```json
{
  "name": "消息数",
  "name_en": "",
  "description": "message_cnt",
  "sql": {
    "left": {
      "key": ["T1:message_cnt"],
      "key_sql": "T1:message_cnt",
      "type": "pv"
    },
    "right": {
      "key": null,
      "key_sql": "",
      "type": ""
    }
  },
  "conf": {
    "type": "action_cuped",
    "date_list": [],
    "date_picker_type": "collection",
    "extra_conf": "",
    "exposure": {
      "action_shift_days": 0,
      "days_picker_type": "first_n_days",
      "days_range": "1,7,14",
      "key_sql_list": "",
      "type": "pv"
    }
  }
}
```

#### 比率指标
```json
{
  "name": "代码建议可应用率",
  "description": "applicable_cnt/suggest_code_cnt",
  "sql": {
    "left": {
      "key": ["T1:applicable_block_cnt"],
      "key_sql": "T1:applicable_block_cnt",
      "type": "pv"
    },
    "right": {
      "key": ["T1:suggest_code_block_cnt"],
      "key_sql": "T1:suggest_code_block_cnt",
      "type": "pv"
    }
  }
}
```

#### 人均指标
```json
{
  "name": "人均代码建议数",
  "sql": {
    "left": {
      "key": ["T1:suggest_code_block_cnt"],
      "key_sql": "T1:suggest_code_block_cnt",
      "type": "pv"
    },
    "right": {
      "key": ["T1:suggest_code_block_cnt"],
      "key_sql": "T1:suggest_code_block_cnt",
      "type": "uv"
    }
  }
}
```

### Dimension（维度）
```json
{
  "name": "意图类别",
  "name_en": "",
  "description": "用户具体的意图类别",
  "dim_type": "METRIC_DIMENSION",
  "key": ["T1:intent"],
  "key_sql": "",
  "conf": {
    "backward_days": "-1",
    "base_user_type": "",
    "buffer_days": null,
    "combine_fields": [],
    "custom_sql": "",
    "decc_type": "",
    "default_value": "",
    "enums": [{"description": "", "name": ""}],
    "enums_filter": false,
    "enums_update_type": "merge",
    "fallback_value": "",
    "is_ablog_dim": false,
    "is_query": false,
    "libra_key": "",
    "overlapping_dim_total_enum": "",
    "split_suffix": "",
    "update_type": "first",
    "use_base_user": false,
    "use_combine": false,
    "use_conf": false,
    "use_custom": false,
    "use_libra_key": false,
    "use_num": false,
    "use_split": false,
    "use_types": "RPT",
    "valid_custom_sql_pass": false
  },
  "pub_dim_id": null,
  "decc_type": ""
}
```

### Dimension 高级配置（conf 字段详解）

当 `use_conf=true` 时，维度的 `conf` 对象支持以下高级配置选项。这些选项彼此独立，可以根据实际需求自由组合，并非固定搭配。

默认不开启高级配置（`use_conf=false`），只有有额外需求时才按需开启并设置对应字段。

| 字段 | 类型 | 默认值 | 可选值 | 说明 |
|------|------|--------|--------|------|
| `use_conf` | bool | `false` | `true`/`false` | 高级配置总开关。`false` 时使用默认简单模式，其他高级选项不生效 |
| `use_types` | string | `"RPT"` | `"RPT"`, `"MDS"`, `"EXTERNAL"`, `"RPT_ONLY"` | 维度使用方式。RPT=预刷+现查（默认），MDS=仅现查，EXTERNAL=外部数据现查，RPT_ONLY=仅预刷 |
| `update_type` | string | `"first"` | `"first"`, `"last"`, `"t1"`, `"GREATEST"` | 维度值更新策略。first=按首次进组取值（默认），last=按最新取值，t1=固定进组前N天值（如前一天），GREATEST=取最大值 |
| `enums_update_type` | string | `"merge"` | `"merge"`, `"force"`, `"init"` | 枚举值更新逻辑。merge=合并所有枚举值（默认），force=强制同步最新，init=仅首次初始化 |
| `enums` | list | `[{"name":"","description":""}]` | — | 枚举值列表，每项包含 name 和 description |
| `enums_filter` | bool | `false` | `true`/`false` | 是否启用枚举过滤，只统计枚举列表内的值 |
| `use_custom` | bool | `false` | `true`/`false` | 是否使用自定义 SQL 定义维度值 |
| `custom_sql` | string | `""` | — | 自定义 SQL（当 use_custom=true 时填写） |
| `valid_custom_sql_pass` | bool | `false` | `true`/`false` | 自定义 SQL 是否已通过校验 |
| `use_num` | bool | `false` | `true`/`false` | 是否为数值维度（维度值为数值类型） |
| `use_split` | bool | `false` | `true`/`false` | 是否启用维度拆分 |
| `split_suffix` | string | `""` | — | 拆分后缀（当 use_split=true 时填写） |
| `use_combine` | bool | `false` | `true`/`false` | 是否使用组合字段（多字段组合成一个维度） |
| `combine_fields` | list | `[]` | — | 组合字段列表（当 use_combine=true 时填写） |
| `use_base_user` | bool | `false` | `true`/`false` | 是否使用基准用户（用于用户维度的基准对齐） |
| `base_user_type` | string | `""` | — | 基准用户类型（当 use_base_user=true 时填写） |
| `is_ablog_dim` | bool | `false` | `true`/`false` | 是否从 AB 日志中取维度值 |
| `use_libra_key` | bool | `false` | `true`/`false` | 是否使用 Libra Key（引用公共维度） |
| `libra_key` | string | `""` | — | Libra Key 值（当 use_libra_key=true 时填写） |
| `is_query` | bool | `false` | `true`/`false` | 是否为圈选 Query 维度（特殊维度类型，dim_type 为空，key 为空） |
| `backward_days` | string | `"-1"` | — | 回溯天数，"-1" 表示不限制 |
| `buffer_days` | null | `null` | — | 缓冲天数 |
| `default_value` | string | `""` | — | 维度默认值（维度值缺失时使用） |
| `fallback_value` | string | `""` | — | 维度兜底值 |
| `decc_type` | string | `""` | — | DECC 维度类型 |
| `overlapping_dim_total_enum` | string | `""` | — | 重叠维度总枚举 |

#### 圈 Query 维度

当 `is_query=true` 时，这是一个特殊的"圈选 Query"维度，通常关联公共维度（`pub_dim_id` 不为 null）。此维度的 `dim_type` 为空字符串，`key` 为空列表，不引用数据源列。

### Group（指标组）
```json
{
  "id": 134624,
  "name": "[Libra]AI行为_Chat_效果指标(设备维度)_分意图",
  "name_en": "",
  "user_id_type": ["USER_UNIQUE_ID"],
  "id_type_scope": "all",
  "apps": ["1190"],
  "description": "",
  "group_type": "action_cuped",
  "libra_group_id": 195339,
  "is_cum": 1,
  "cum_start_time": "2025-09-15",
  "cum_type": "ENTER_ONCE_ALWAYS_COUNT",
  "support_flexible_dim": 1,
  "support_flexible_range": 1,
  "dorado_regions": "cn",  // cn 环境为 "cn"，i18n 环境默认为 "sg"（可选 va/mya/eu_ttp/us_ttp）
  "conf": {},
  "owner": ["zhanfurong", "baijingjing.11"],
  "tag": [],
  "business_tag_id": 2,
  "visibility": 3,
  "m_m2_merge_unique": 0,
  "ablog_config": {
    "use_type": "custom",
    "business_list": [{"business_id": 261, "business_key": "basic"}],
    "remove_app": "true",
    "abLogSqlPreview": "select CAST(version_id as BIGINT) as vid, user_unique_id, ...",
    "defaultAbLogSqlPreview": "select CAST(version_id as BIGINT) as vid, user_unique_id, ..."
  },
  "metrics": [...],
  "dimensions": [...]
}
```

**UID 维度指标组示例**（`user_id_type=["USER"]`）：
```json
{
  "name": "订阅效果指标(UID维度)",
  "user_id_type": ["USER"],
  "id_type_scope": "all",
  "apps": ["532"],
  "ablog_config": {
    "use_type": "custom",
    "business_list": [{"business_id": 122, "business_key": "basic"}],
    "remove_app": "true",
    "abLogSqlPreview": "select CAST(version_id as BIGINT) as vid, user_uid as user_id, MIN(min_date) as min_date, MAX(is_active) as is_active from origin_log.dwd_abtest_vid_log_df where date = '${date}' and app = 'marscode_native_ide_us' group by vid, user_id;",
    "defaultAbLogSqlPreview": "..."
  }
}
```

> **说明**：`user_id_type` 决定了 AB 日志关联方式。`["USER"]` 时 `abLogSqlPreview` 中使用 `user_uid as user_id` 而非 `user_unique_id`。

## 完整 API 调用流程

### 保存指标配置（不上线）

```
1. GET /v1/ticket/{ticket_id}?region=<由env决定>     → 获取现有数据
2. [可选] POST /v1/sql/parse                → 解析新 SQL
3. 修改数据（metrics/dimensions/virtual_table）
4. POST /v1/ticket/save_check               → 校验
5. PUT /v1/ticket/                           → 保存草稿
```

### UUID → 名称映射

GET 响应中 virtual_table.key 是 UUID，columns.key 也是 UUID，metrics/dimensions 中的引用格式是 `tableUUID:columnUUID`。
PUT 请求中需要转为 `Tx:column_name` 格式。

映射方法：
1. 从 GET 响应的 virtual_table 中提取 `key`（UUID）和 `name`（如 T1）
2. 从 columns 中提取 `key`（UUID）和 `name`（列名）
3. 将所有 metrics/dimensions 中的 `tableUUID:columnUUID` 替换为 `Tx:column_name`

### 创建新需求

```
1. POST /v1/meego/business                  → 查询业务线列表（获取 business ID）
2. POST /v1/business/online/ab_log_v2       → 获取 AB 日志 SQL（可选）
3. POST /v1/sql/parse                       → 解析数据源 SQL
4. POST /v1/ticket/                         → 创建新需求（含指标组和数据源）
5. GET /v1/ticket/{ticket_id}?region=<由env决定>     → 重新加载确认
```

### 发起上线

```
1. POST /v1/ticket/online/check              → 上线前校验
2. GET  /v1/state/{ticket_id}?group_ids=...   → 确认无进行中的上线流程
3. POST /v1/llm/online_prechecks              → LLM 预检查
4. POST /v1/state/                            → 创建状态机实例
5. PUT  /v1/state/event                       → 触发 CREATE_REQUEST 事件
6. GET  /v1/state/{ticket_id}                 → 轮询状态
```
