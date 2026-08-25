# Libra CLI Reference

## libra config-release

配置中心发布使用 Titan Passport Cookie，与 Libra 页面命令共享登录态。除 `get` / `review status` 外，所有命令默认 dry-run，只有显式 `--yes` 才提交。

```bash
bytedcli libra config-release create --repo-id 12345 --token demo-server --config-name demo-flag --description "Release demo flag"
bytedcli libra config-release create --repo-id 12345 --token demo-server --all-changes --description "Release reviewed changes" --yes
bytedcli libra config-release get --ticket demo-ticket
bytedcli libra config-release whitelist execute --ticket demo-ticket --white-list demo-user --yes
bytedcli libra config-release review create --ticket demo-ticket --reviewer demo.reviewer --yes
bytedcli libra config-release review status --ticket demo-ticket --wait --poll-interval-ms 5000 --wait-timeout-ms 600000
bytedcli libra config-release deploy --ticket demo-ticket --percentage 10 --yes
bytedcli libra config-release rollback execute --ticket demo-ticket --reason "Demo rollback" --yes
```

`create` 的 repo 来源为 `--repo-id` 或包含 `/libra/config-center/<repo-id>/` 的 `--url`，二者互斥。配置选择必须在 `--config-name`、`--config-detail-id`、`--all-changes` 三种模式中选择一种。`--feature-type` 当前支持 `technical-requirement`，在 API 边界映射为平台编码；`--meego-id` 可重复最多 5 次，格式为 `story` 或 `story:project:project-key`。

`review status` 不带 `--wait` 时只查询一次，即使仍在 review 中也成功返回。带 `--wait` 时，审批通过返回成功；拒绝、回滚和超时返回结构化错误。该命令不执行 approve/reject。

## libra experiment create

通过 JSON 请求体创建新实验。

```bash
# 从 JSON 文件创建（--app-id 传 -1，实际 app_id 放在 body 内）
bytedcli --json libra experiment create --app-id -1 --request-file ./experiment.json

# 内联 JSON 创建
bytedcli --json libra experiment create --app-id -1 --request-json '{"name":"demo-exp", ...}'

# 基于单实验模板创建，request body 作为 override 覆盖模板默认值
bytedcli --json libra experiment create --app-id 1193 --template-id 3139 --request-file ./override.json

# 克隆 backtest / 同 layer 实验时放行可跳过冲突（默认 cn 站点；i18n-tt 等站点请加 --site）
bytedcli libra experiment create --app-id -1 --request-file ./copy.json --skip-conflicts

# 仅当用户明确要求依赖应用默认指标组时，允许空 metrics
bytedcli libra experiment create --app-id -1 --request-file ./defaults-only.json --allow-empty-metrics
```

**选项：**

| Option                  | Description                                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| `--app-id <id>`         | Libra app ID，通常传 `-1`（实际 app_id 放在请求体内）                                                           |
| `--request-json <json>` | 内联 JSON 请求体                                                                                                |
| `--request-file <path>` | 从文件读取 JSON 请求体                                                                                          |
| `--template-id <id>`    | Libra 单实验模板 ID；CLI 会先展开模板默认值，再用 request body 覆盖                                             |
| `--skip-conflicts`      | preflight 返回 `code=213, can_skip=true` 时（典型场景：新老实验共用 `layer_id` + `ab_tag`），放行冲突继续创建   |
| `--no-verify`           | 跳过 GUI 的两步 preflight，按旧的单次 POST 方式执行；只在你已经在 body 里设置好 `skip_verification:true` 时使用 |
| `--allow-empty-metrics` | 允许最终 payload 缺失或使用空 `metrics`；仅限用户明确要求只依赖应用默认指标组的场景                             |

请求体会被自动包裹为 `{ "experiments": [body] }` 发送。

**关注指标组门禁**

- CLI 会在模板展开和 request override 合并完成后检查最终 payload。每个 experiment 的 `metrics` 必须包含至少一个带有效 `metric_group_id` 的对象，否则在发送任何 Libra 请求前返回 `LIBRA_METRICS_REQUIRED`。
- bytedcli 进程无法读取宿主 Agent 的对话历史。调用方必须先回看当前请求和相关历史对话，收集此前提到的指标组；有源实验时用 `experiment get` / `experiment report` 核对 ID，并按 `metric_group_id` 去重后写入 `metrics`。
- 模板指标与历史上下文补充指标取并集，不要用 `metrics: []` 覆盖模板默认值。创建后用 `experiment get` 回读核对。
- 只有用户明确要求依赖应用默认指标组时才能传 `--allow-empty-metrics`；该参数不会自动补指标，也不能作为创建报错的通用绕过开关。

**模板模式说明**

- 当前支持 Libra 单实验模板（single-experiment template）
- CLI 会读取模板详情，把模板默认值转换成 create payload
- `--request-json` / `--request-file` 里的字段会覆盖模板默认值
- `metrics` 是例外：模板与 request 指标组按 `metric_group_id` 合并去重，同 ID 使用 request 对象，其他模板指标会保留
- 实际使用时，至少建议覆盖 `name`、`versions`，并确认 `metrics` 已包含历史上下文要求的全部指标组

**两步握手（默认行为）**

CLI 默认按 GUI 顺序连发两次 `/datatester/experiment/api/v3/app/<app_id>/batch_create_experiment`：

1. `only_verification:true, skip_verification:false` —— 让后端跑 filter rule / 流量 / layer 冲突等真实校验；如果失败，会用 `data.messages` / `data.conflict_experiments` 拼出具体原因抛出。
2. `only_verification:false, skip_verification:true` —— 真正落库。

无论 cn（默认）还是 i18n-tt 等站点，请求都打到同一个 `/batch_create_experiment` 路径，host 由 `--site` 和网络 profile 自动路由：cn 默认 → `data.bytedance.net`；i18n-tt 默认 → `libra-sg.tiktok-row.net`；生产网环境设置 `BYTEDCLI_NETWORK_PROFILE=prod` 后，i18n-tt 切到 `libra-sg.bytedance.net`。两步握手对所有站点都生效。

因此**不要**在 payload 里手动写 `skip_verification` / `only_verification`。CLI 看到这两个字段已存在时也会自动退化为单次 POST（与 `--no-verify` 等价），但容易绕掉真实校验，不建议这么做。

**顶层 `product_id` + `app_id` 自动补齐**

clone 实验时**不用**再手动保证顶层带上 `product_id` / `app_id`——CLI 在任何 POST 前会自动补齐：先看 `layer_info.product_id` / `layer_info.app_id`，仍缺则用实验的 `layer_id` 拉一次 layer detail 取回二者。补齐是 best-effort，layer 查询失败时保持 payload 原样、让原始 create 报错透出。

背景：page API 用实验**顶层**的 `product_id` + `app_id` 拉取层治理配置，两者**缺一**就会让整个请求报 `[500] 获取层治理配置失败，请稍后重试`（只补 `product_id` 不够）。这两个字段在 `experiment get` 输出里位于顶层、不在 `layer_info` 里，clone 裁剪字段时容易漏掉；CLI 会在 POST 前自动补齐。

**request-file JSON 模板：**

```json
{
  "name": "实验名称",
  "manage_type": "strategy",
  "owners": [{ "id": 12345, "name": "demo.user" }],
  "description": "实验描述",
  "expectation": "",
  "scene": 0,
  "feature_type": 3,
  "app_id": 495,
  "is_long_time_flight": 0,
  "enable_gradual": false,
  "specified_psms": [],
  "filter_rule": [
    {
      "conditions": [
        {
          "logic": "&&",
          "condition": {
            "key": "app_id",
            "op": "==",
            "value": [8478],
            "type": "int",
            "custom_filter": false,
            "source": "libra",
            "property_type": "common_param"
          }
        },
        {
          "logic": "&&",
          "condition": {
            "key": "version_code",
            "op": ">=",
            "value": 100190000,
            "type": "int",
            "custom_filter": false,
            "source": "libra",
            "property_type": "common_param"
          }
        }
      ],
      "logic": "||"
    }
  ],
  "filter_user_list": 2,
  "transmit": true,
  "version_traffic_adjustable": false,
  "metric_scene": 2,
  "strategy_category_ids": [],
  "small_traffic_link": "",
  "large_traffic_link": "",
  "is_mab": 0,
  "duration": 2592000,
  "version_resource": 0.01,
  "book_version_resource": 0,
  "experiment_mode": 1,
  "product_id": 1538,
  "layer_info": {
    "create_layer_auto": false,
    "product_id": 1538,
    "hash_strategy": "did",
    "layer_id": 194016
  },
  "versions": [
    {
      "name": "control",
      "description": "对照组",
      "type": 0,
      "config_show_mode": 1,
      "weight": 500,
      "config": "{}"
    },
    {
      "name": "treatment",
      "description": "实验组",
      "type": 1,
      "config_show_mode": 1,
      "weight": 500,
      "config": "{\"key\":{\"param\":true}}"
    }
  ],
  "metrics": [
    {
      "type": "important",
      "metric_group_id": 10001,
      "name": "Demo core metrics",
      "metric_group_type": "ordinary",
      "status": 1,
      "dimensions": [],
      "non_echo": false
    }
  ],
  "tags": []
}
```

**关键字段说明：**

| 字段                                      | 说明                                                                                                                                                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                                    | 实验名称，全局唯一，最长 200 字符                                                                                                                      |
| `manage_type`                             | `"strategy"`（服务端）或 `"product"`（客户端）                                                                                                         |
| `owners`                                  | 负责人数组，每项含 `id`（employee_id）和 `name`                                                                                                        |
| `app_id`                                  | Libra 应用 ID（即 Libra 平台的 libraKey，可在 [应用管理页](https://data.bytedance.net/libra/access?page=1&status=4) 查询，与客户端上报的 app_id 不同） |
| `product_id`                              | 产品线 ID（与 layer_info.product_id 一致）                                                                                                             |
| `duration`                                | 实验时长，秒。30 天 = 2592000                                                                                                                          |
| `version_resource`                        | 实验流量比例，0~1（0.01 = 1%）                                                                                                                         |
| `layer_info.layer_id`                     | 流量层 ID                                                                                                                                              |
| `layer_info.hash_strategy`                | 分流方式：`"did"` / `"uid"`                                                                                                                            |
| `versions[].type`                         | 0 = 对照组，1 = 实验组                                                                                                                                 |
| `versions[].weight`                       | 流量权重（千分比），按比例分配                                                                                                                         |
| `versions[].config`                       | 参数配置 JSON 字符串                                                                                                                                   |
| `filter_rule`                             | 受众过滤规则数组，每个元素是一组 AND 条件                                                                                                              |
| `filter_rule[].conditions[].condition.op` | 操作符：`"=="`、`">="` 、`"in_bundle"` 等                                                                                                              |
| `metrics`                                 | 关注指标组对象数组，默认必须非空；按 `metric_group_id` 去重并带齐历史上下文要求的指标组                                                                |
| `traffic_map`                             | 流量段配置（克隆 backtest 时常见 `[{"start_time":"","pieces":[{"begin":0,"length":200}]}]`），缺失会导致 preflight 报"可用流量不足"                    |
| `skip_verification` / `only_verification` | **不要手动设置**，CLI 会按两步握手自动注入。已经设置时 CLI 会回退到单次 POST（等价 `--no-verify`）                                                     |

可通过 `bytedcli --json libra experiment get --flight-id <id>` 导出已有实验的完整字段结构作为参考模板。

## libra experiment child create

创建依赖实验。命令会校验 parent version、layer product scope、layer 可用流量和父实验元数据，创建后再读回 parent_flight_id、parent_vid 与两个版本的 father_versions。创建成功但读回请求失败时，错误会返回已经创建的 flight ID，并明确提示不要重复创建。

这是会创建 Libra draft 的外部写操作。执行前先向用户展示父实验、父版本、layer、目标 region 和 traffic，并获得明确确认。

```bash
bytedcli --site i18n-tt libra experiment child create \
  --parent-flight-id 1001 --parent-version-id 2002 --layer-id 3003 \
  --name "[US] demo child" --description "..." \
  --treatment-description "..." --treatment-config '{"key":true}' --traffic 100%
```

| Option                             | Description                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| `--parent-flight-id <id>`          | 父实验 flight ID                                                                     |
| `--parent-version-id <id>`         | 子实验所在的父实验 version ID                                                        |
| `--layer-id <id>`                  | 与父实验相同 product scope 的 layer ID                                               |
| `--name <name>`                    | 子实验名称                                                                           |
| `--description <text>`             | 子实验描述                                                                           |
| `--control-description <text>`     | 对照组描述；默认“父实验当前配置”                                                     |
| `--control-config <json>`          | 对照组配置 JSON 字符串；默认 `{}`                                                    |
| `--treatment-description <text>`   | 实验组描述                                                                           |
| `--treatment-config <json>`        | 实验组配置 JSON 字符串                                                               |
| `--owner <names>`                  | 逗号分隔 owner；省略时继承父实验                                                     |
| `--strategy-category-ids <ids>`    | 逗号分隔 strategy_category_ids；省略时继承并验证父实验值                             |
| `--traffic <fraction\|percentage>` | 接受比例或百分比（例如 `0.5` / `50%`）；默认 `1`，执行前应显式确认                   |
| `--region <region>`                | effected_regions override，可重复或逗号分隔；省略时继承并验证父实验 effected_regions |
| `--duration-days <n>`              | 实验持续天数；默认 `3648`，对应写侧固定 `is_long_time_flight: 1`                     |
| `--skip-conflicts`                 | 仅跳过后端标为 can_skip 的冲突；使用前检查 conflict keys                             |

父实验缺失 manage_type / metric_scene、缺少至少一个带合法 metric_group_id 的关注指标组、layer 缺失 priority，或 strategy_category_ids 不是纯 number 数组时，命令会以结构化错误终止，不会猜默认值。子实验会继承父实验完整 metrics 数组。

依赖实验的读写字段不对称。照 experiment get 的字段名回写不会报错，但后端会静默丢弃父子关系；命令负责组装写侧字段并在创建后验证读侧字段。

| 项                         | experiment get 读到 | 创建时发送                                      |
| -------------------------- | ------------------- | ----------------------------------------------- |
| 父实验                     | parent_flight_id    | father_experiment_id                            |
| 依赖标记                   | experiment_mode: 14 | extend_type: 1 + experiment_mode: 1             |
| 父版本                     | 顶层 parent_vid     | versions[].father_versions: [parent version ID] |
| owner                      | 逗号分隔字符串      | owners: [{"name": "owner"}]                     |
| 分组权重                   | —                   | weight: 500（50.0%）；0 会创建不可命中的版本    |
| inherit_type / inherit_key | 2 / hash            | 不发送，由服务端根据父实验推导                  |

effected_regions、is_long_time_flight: 1、scene: 0、transmit: true 也由命令明确写入。owners、strategy_category_ids、metric_scene、manage_type 默认从父实验继承；region 仅在确需覆盖时传入。traffic 接受比例或百分比（例如 0.5 / 50%），最大值 1 / 100%。

建 layer 不要依赖 GUI：App/Token 选错会让 layer 落到不同 product_id，名称已占用但实验的 layer 选择器不可见。使用完整命令显式指定：

```bash
bytedcli libra layer create --app-id <id> --product-id <pid> \
  --name <layer-name> --owner <owner> --hash-strategy did --priority 50
```

GUI layer 搜索框也可能对已存在的 layer 返回空结果，必要时用 libra layer list/get 核对。

## libra experiment get

查看实验详情，包含名称、状态、版本配置、owner、流量比例、标签等。

```bash
bytedcli libra experiment get --flight-id <flight_id>
bytedcli --json libra experiment get --flight-id <flight_id>
bytedcli --as app --json libra experiment get --flight-id <flight_id> --app-id <app_id>
```

`--app-id` 可选；省略时保持原有 `app/-1` 查询行为。已知实验所属 App ID 时建议显式传入，应用身份必须显式传入，避免 Libra 的 `app/-1` 详情路由返回服务端错误。

## libra experiment traffic

查看实验详情中的当前流量分配和版本权重。该命令不返回流量变更历史。

```bash
bytedcli libra experiment traffic --flight-id <flight_id>
bytedcli --as app libra experiment traffic --flight-id <flight_id> --app-id <app_id>
```

## libra experiment audit list

原样返回 Libra page API 的实验审计历史。CLI 不维护 action 分类表，也不对变更内容做二次解释；需要稳定结构时使用 `--json`。

```bash
bytedcli --json libra experiment audit list \
  --app-id <actual_app_id> --flight-id <flight_id>
```

对应接口：

```text
GET /datatester/experiment/api/v3/app/{app_id}/experiment/{flight_id}/history
```

| 选项               | 说明                              |
| ------------------ | --------------------------------- |
| `--app-id <id>`    | 实验实际所属 Libra App ID（必填） |
| `--flight-id <id>` | 实验 Flight ID（必填）            |

## libra experiment traffic-effect list

原样返回 Libra 的流量生效记录。有平滑生效 / gradual traffic 数据时，返回体可包含 `last_gradual_traffic` / `traffic_record`；没有记录时保持后端原始空值语义。

```bash
bytedcli --json libra experiment traffic-effect list \
  --app-id <actual_app_id> --flight-id <flight_id>
```

对应接口：

```text
GET /datatester/experiment/api/v3/app/{app_id}/traffic_info/{flight_id}
```

不要把它与 `libra experiment traffic` 混淆：后者读取实验详情中的当前流量与版本权重。bytedcli 不集成未证实的 `/experiment/{flight_id}/traffic` 接口；实测该接口在多个实验上只返回无信息量的 `traffic_decrease`，暂不能作为流量历史来源。

## libra experiment report

查看实验报告。不带 `--metric-group` 时列出所有可用指标组。

```bash
# 列出指标组
bytedcli libra experiment report --flight-id <flight_id>

# 查看具体指标组
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id>

# 应用身份显式指定实验所属 App ID
bytedcli --as app libra experiment report --flight-id <flight_id> --app-id <app_id> \
  --metric-group <metric_group_id>

# 指定日期和合并方式
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> \
  --start 2026-03-18 --end 2026-03-25 --merge-type total

# 列出当前指标组支持的维度和值
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --list-dimensions

# 按维度拉取报告（查询该维度下全部值）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --dimension <dimension_id>

# 只看指定维度值
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> \
  --dimension <dimension_id:value_id1,value_id2>

# 自定义维度值（value_key 字符串，等价 Libra 页面的"自定义值"输入；可与数字值 ID 混用）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> \
  --dimension <dimension_id:custom_value_key,value_id1>

# 多维交叉查询
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> \
  --dimension <dimension_id:value_id1,value_id2> \
  --dimension <dimension_id:value_id3,value_id4>

# 查看逐日趋势
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --trend

# 指定单个机房（通常自动推导，不用传；只在自动推导错、或对比其它 region 时使用）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --data-region eu_ttp

# 多机房合并查询（同时覆盖 ROW + EU TTP 的实验，不传会自动推导为 other,eu_ttp）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --data-region other,eu_ttp

# 指定 Libra 报告口径（按页面抓包里的 data_caliber 值对齐普通/CUPED 等口径）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --data-caliber 1

# 指定 baseline 版本（默认为实验内 type=0 的版本；长期反转/Holdout 类报告常需要把反转组显式设为 baseline）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --baseline <vid>
```

**选项：**

| 选项                        | 说明                                                                                                                                                                                                         | 默认值                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `--flight-id <id>`          | 实验 Flight ID（必填）                                                                                                                                                                                       | -                                                                              |
| `--app-id <id>`             | 实验所属 Libra App ID；应用身份建议显式传入，避免先访问 `app/-1` 详情路由                                                                                                                                    | 省略时由实验详情自动解析                                                       |
| `--metric-group <id>`       | 指标组 ID                                                                                                                                                                                                    | 省略则列出所有                                                                 |
| `--start <YYYY-MM-DD>`      | 开始日期                                                                                                                                                                                                     | 最新有数日期                                                                   |
| `--end <YYYY-MM-DD>`        | 结束日期                                                                                                                                                                                                     | 最新有数日期                                                                   |
| `--merge-type <type>`       | `total`(累计)/`sum`(日均)/`avg`                                                                                                                                                                              | `total`                                                                        |
| `--trend`                   | 显示逐日趋势数据                                                                                                                                                                                             | 关闭                                                                           |
| `--list-dimensions`         | 列出当前 metric group 可用维度和值 ID                                                                                                                                                                        | 关闭                                                                           |
| `--dimension <spec>`        | 维度选择器，格式 `<dimension_id>` 或 `<dimension_id:value[,value...]>`；数字视为枚举值 ID，非数字先按枚举 value_key/名称解析、未命中视为自定义 value_key（等价页面"自定义值"）；重复传多个维度时执行交叉查询 | -                                                                              |
| `--data-region <region>`    | 机房路由：`sg` / `eu_ttp` / `us_ttp` / `tx` / `va` / `my` / `other`（其他机房聚合）；支持逗号分隔多个（如 `other,eu_ttp`）                                                                                   | 从实验 `truly_effected_regions` 自动推导（映射规则见下），推不出时回退 `other` |
| `--data-caliber <1\|2\|3>`  | Libra 报告口径原始值，对齐页面请求里的 `data_caliber`；用于对比普通/CUPED 等口径                                                                                                                             | 不传时保持 CLI 默认口径                                                        |
| `--force-show <0\|1>`       | 透传 Libra `force_show`；`1` 强制后端返回数据即使尚未完全就绪（与 Libra UI 行为一致）；CLI 默认 `0`（向后兼容）                                                                                              | `0`                                                                            |
| `--baseline <vid>`          | 指定 baseline 版本 ID（Libra 报告里作为参照组、diff 的分母与基准）                                                                                                                                           | 默认取实验内 `type=0` 的版本（通常即 v0 / 对照组）                             |
| `--wait-timeout-sec <sec>`  | 多维交叉查询最长等待秒数                                                                                                                                                                                     | `180`                                                                          |
| `--poll-interval-sec <sec>` | 多维交叉查询轮询间隔秒数                                                                                                                                                                                     | `5`                                                                            |

说明：`--dimension <dimension_id>` 查询该维度下全部值；`--dimension <dimension_id:value_ids>` 只查询指定值；重复传多个 `--dimension` 时执行多维交叉。多维交叉查询走异步 adhoc 计算；若超时，命令会返回当前 `async_job_id` / `progress` / `status`，提示稍后重试同一条命令。值列表里的非数字 token 先按枚举值的 value_key / 名称解析（命中则按枚举值查询，即可以直接传 value_key 代替数字 ID）；未命中的作为自定义 value_key（如 `sample_channel_tool`）透传，用于查询尚未进入枚举清单的维度值，等价 Libra 页面的"自定义值"输入。含自定义值时走 adhoc 查询，仅支持单个 `--dimension` 且不支持 `--trend`；纯数字的自定义 value_key 无法表达（数字 token 一律按枚举值 ID 解析）。`--data-caliber` 直接透传到 Libra report API，适合按浏览器抓包值复现页面上的普通/CUPED 等报告口径。

**`--baseline` 详解**：Libra 后端按 `base_vid` 决定哪个版本作为 diff 计算的参照组——所有非 baseline 版本的 `relative_diff` 与 `p_val` 都是「该版本 vs baseline」。CLI 默认取实验内 `type=0` 的版本（通常即 v0 / 对照组），与 Libra 页面默认行为一致。需要覆盖默认的典型场景：

- 长期反转 / Holdout 实验：把"反转组"显式设为 baseline，让线上组的 `relative_diff` 直接读作「线上 vs 反转」，diff 符号体现推全功能的长期效果
- 多组实验里想换一个版本做参照：例如 v0/v1/v2/v3 想看 v1 vs v3 / v2 vs v3 等

CLI 会先调 `libra experiment get` 校验传入的 vid 是否属于该 flight；不属于时会列出所有已知 version id + name 后退出。

**`--data-region` 详解**：Libra 后端按机房路由查询，传错区域会静默返回 `value=null`（接口仍返回 `code: 0`），并把 `end_date` clamp 到旧日期。

`data_region` 有两个维度的概念需要区分：

- **机房部署标签**（`truly_effected_regions`）：实验在哪些机房生效，对应 Libra 创建实验时的物理机房选项（新加坡机房 → `SG`、美东Maliva机房 → `VA`、GCP/EU-TTP机房 → `EU_TTP`、US-TTP机房组 → `US_TTP`）。
- **`data_region` 查询桶**：Libra 报表 API 的聚合分区，对应 Libra UI 里的「其他机房数据」/「EU-TTP机房数据」等筛选项。

`other` 是**"其他机房"聚合桶**（对应 Libra UI 的「其他机房数据」），包含 SG（新加坡机房）、VA（美东Maliva机房）、MY 等机房的数据聚合，不是某个具体机房的名称。

自动推导规则：将 `truly_effected_regions` 里的物理机房标签映射到对应查询桶，去重后逗号拼接：

| 实验 `truly_effected_regions` 示例 | 自动推导的 `data_region`              | 说明                                |
| ---------------------------------- | ------------------------------------- | ----------------------------------- |
| `["SG"]`                           | `other`                               | 新加坡机房 → 其他机房聚合桶         |
| `["VA"]`                           | `other`                               | 美东Maliva机房 → 其他机房聚合桶     |
| `["MY"]`                           | `other`                               | → 其他机房聚合桶                    |
| `["SG", "VA"]`                     | `other`                               | 均属其他机房，去重后单值            |
| `["EU_TTP"]`                       | `eu_ttp`                              | GCP/EU-TTP机房 → eu_ttp桶（1:1）    |
| `["US_TTP"]`                       | `us_ttp`                              | US-TTP机房组 → us_ttp桶（1:1）      |
| `["SG", "VA", "EU_TTP"]`           | `other,eu_ttp`                        | 典型跨区实验（如 i18n-tt 全球实验） |
| `["EU_TTP", "OTHER"]`              | `eu_ttp,other`                        | 多桶逗号拼接                        |
| 无法推导 / 空                      | `other`（兜底，仅查其他机房聚合数据） |                                     |

只有自动推导错、或者手工对比不同 region 表现时才需要加 `--data-region`。可通过 `bytedcli libra experiment get --flight-id <id>` 查看 `Regions` 字段确认实验生效机房。

## libra experiment report-batch

在单个 bytedcli 进程内并发跑一批 report 查询，替代外部起 N 个子进程。输入是一个 UTF-8 JSONL 文件，每个非空行是一条查询；字段与 `libra experiment report` 的 option 一一对应（snake_case），另加一个 batch 专属、批内唯一的 `request_id`。链路（merge / trend / 单维 / 单维 trend / 多维 adhoc）由 `trend` + `dimension` 项数 + 是否含自定义值隐式推导，和单条命令完全一致，没有 batch 专属的 `view` 字段。

```bash
# JSONL 输入：每行一条查询（snake_case 字段 + 唯一 request_id）
# {"request_id":"demo-gmv","flight_id":12345678,"app_id":100,"metric_group":10001}
# {"request_id":"demo-retain","flight_id":12345678,"app_id":100,"metric_group":10002,"merge_type":"avg"}
# {"request_id":"demo-dimension","flight_id":12345678,"app_id":100,"metric_group":10001,"dimension":["20001:30001"]}

# 默认并发 10，聚合 JSON envelope（含 total / succeeded / failed / items[]）
bytedcli --site i18n-tt --json libra experiment report-batch --input-file ./queries.jsonl --concurrency 10

# NDJSON：每条输入一个 envelope，按输入顺序逐行输出，便于流式消费
bytedcli --json libra experiment report-batch --input-file ./queries.jsonl --format ndjson > ./results.ndjson
```

**选项：**

| 选项                  | 说明                                                                                                                | 默认值 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- | ------ |
| `--input-file <path>` | UTF-8 JSONL 文件（必填），每个非空行是一条 report 查询                                                              | -      |
| `--concurrency <n>`   | 同时执行的查询数（1..32），限制并发查询数而非总 HTTP 请求数；建议保持在 20 以下，过高易触发后端网关限流（HTTP 429） | `10`   |
| `--format <mode>`     | `json`（单个聚合 envelope）或 `ndjson`（每行一个 envelope，按输入顺序）                                             | `json` |

说明：

- 每条 JSONL 支持的字段：`flight_id`、`metric_group`、`start`、`end`、`merge_type`、`period_type`、`trend`、`dimension[]`、`data_region`、`data_caliber`、`baseline`、`force_show`、`wait_timeout_sec`、`poll_interval_sec`、`selected_metric_ids`，外加批内唯一的 `request_id`。
- 单条查询的超时沿用既有机制：同步链路走全局 `--http-timeout-ms` / `--http-retry-*`，异步多维 adhoc 走每条记录的 `wait_timeout_sec` / `poll_interval_sec`；没有 batch 级总超时。
- 一条查询失败不会中断其它查询；失败项带稳定的 `category`（`auth` / `permission` / `rate_limit` / `timeout` / `input` / `network` / `server` / `schema` / `error`），便于上层按类别重试。`rate_limit` 对应 HTTP 429（并发过高触发后端网关限流），可据此退避重试。
- `--concurrency` 建议保持在 20 以下：并发过高不会加速整批（瓶颈是单条查询延迟），反而容易触发后端网关限流（HTTP 429）导致部分查询失败；默认 10 已在真实实验上验证稳定。
- 同一 `flight_id` 的实验上下文（`app_id` / 对照组 VID / 自动推导的 `data_region`）在批内只解析一次并复用。
- 沿用单条命令的已知限制：纯数字的自定义 value_key 无法表达（数字 token 一律按枚举值 ID 解析）。
- 输入/输出用的都是 Libra 原生 ID，不支持在 batch 里用业务名称指定指标、维度或值。

## libra experiment conclusion-report

一次性聚合 Libra "结论报告" 页：把 conclusion-report bundle 里所有指标 × 所有 treatment 在一次 `POST /conclusion/preview` 拉回来，比按指标组循环 `report` 快得多。可选 `--with-lt-exchange` 再追加一次 `POST /get_exchanged_lt_info/` 拉 "兑换 LT" 表。

```bash
# 基础用法（默认只显示 sig+/sig-，按 |Diff%| 排序，sig- 优先）
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id>

# 自定义日期窗口和机房（默认从 meta + 实验 truly_effected_regions 推导）
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> \
  --start 2026-05-18 --end 2026-05-23 --data-region other,eu_ttp

# 只看 P0 / P0+P1 优先级
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> --sla P0,P1

# 按类目筛（支持中文 display name 或英文 tag，大小写不敏感）
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> --category 护栏指标

# 只看指定 metric_group（绕过 --sla / --category）
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> --group-id <gid1>,<gid2>

# 把 not-sig / no-data 行也展示
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> \
  --include-not-sig --include-no-data

# 丢掉 |relative_diff| 太小的行（阈值为 decimal，0.001 = 0.1%）
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> \
  --include-not-sig --min-abs-diff 0.001

# 追加 "兑换 LT" 表：per-treatment lt_total + per-metric 贡献
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> --with-lt-exchange

# 多机房分别看 LT：combined + 每个机房一次额外调用，并排展示
bytedcli --site i18n-tt libra experiment conclusion-report --flight-id <flight_id> \
  --data-region other,eu_ttp --with-lt-exchange --lt-per-region

# Agent 视角：拿 raw JSON
bytedcli --site i18n-tt --json libra experiment conclusion-report --flight-id <flight_id> \
  --with-lt-exchange --lt-per-region | jq '.data.summary'
```

**选项：**

| Option                 | Description                                                                                          | Default                                             |
| ---------------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `--flight-id <id>`     | Flight ID（必填）                                                                                    | -                                                   |
| `--app-id <id>`        | Libra app ID                                                                                         | 从 flight detail 推                                 |
| `--start <YYYY-MM-DD>` | 开始日期                                                                                             | meta 的 `default_selected_start_date`               |
| `--end <YYYY-MM-DD>`   | 结束日期                                                                                             | meta 的 `default_selected_end_date`                 |
| `--data-region <r>`    | 机房路由，支持逗号拼接                                                                               | 从实验 `truly_effected_regions` 推导（同 `report`） |
| `--baseline <vid>`     | 把哪个 version 作 baseline                                                                           | 实验内 `type=0` 的 version                          |
| `--sla <list>`         | SLA 优先级筛选，逗号分隔 (`P0,P1`)                                                                   | 全部保留                                            |
| `--category <name>`    | 按类目筛（display name 或 tag，case-insensitive 完全匹配）                                           | 不筛                                                |
| `--group-id <list>`    | 显式指定 metric_group，逗号分隔；与 `--sla` / `--category` 互斥（前者优先）                          | 不筛                                                |
| `--include-not-sig`    | 把 not-sig 行也展示                                                                                  | 关                                                  |
| `--include-no-data`    | 把 no-data 行 + 灰度未投产 metrics 也展示                                                            | 关                                                  |
| `--min-abs-diff <pct>` | 丢 \|relative_diff\| < pct 的行（pct 是 decimal，例 0.001 = 0.1%）                                   | 不筛                                                |
| `--with-lt-exchange`   | 追加 LT 兑换表；失败时不阻断主报告，错误进 `lt_exchange_error`                                       | 关                                                  |
| `--lt-per-region`      | 多机房时按 region 分别拉 LT，combined + per-region 并排展示；隐含 `--with-lt-exchange`；单机房无效果 | 关                                                  |

**和 `report` 的分工**：

- `report` 单指标组深挖（趋势 / 维度 / `--data-caliber` / `--force-show`），按一个 metric_group 一次返回
- `conclusion-report` 一次拉整个 bundle 的所有 metric × 所有 treatment，适合做整体扫描 / SLA 巡检 / 兑换 LT 汇总
- 想要 `v_n` vs `v_m` 全统计（不只是 absolute / relative delta，要 p-value / 95% CI），回到 `report --baseline <vid_m>`（详见上一节）。`conclusion-report` 的 preview API 永远固定 `base_version_id`，每行只是 `v_n` vs `v_base`；要 cross-treatment delta 自己减 `TreatMean` 列即可，但 p-value / CI 必须重跑统计。

**单位约定（重要）**：

- `/conclusion/preview` 和 `/get_exchanged_lt_info/` 后端返回的 `uplift` / `margin_ratio` / `left` / `right` / `lt_total` / `metric_lt[].all` 用的是 **percentage-point 单位**：raw `-0.22` 实际意思是 `-0.22%`（不是 `-22%`）。handler 已 `/100` 归一成 decimal，所以 `--json` 输出和 text 表格里的百分号显示都和 Libra UI 一致。
- 对比一下：`/lean-data-v2`（`report` 走的那个）已经是 decimal，**两边单位不一样**，写 raw caller 时要小心。

**`data_caliber` 偏差**：

- `/conclusion/preview` 用 bundle 内 baked 的 caliber，不接受 `--data-caliber`。如果该 bundle 和 UI 选择器的 caliber 不一致，绝对值（BaseMean / TreatMean）会有微小偏差（百分号 / 显著性结论不变）。
- 想严格对齐 UI 的 caliber → 用 `report --data-caliber 2`；想做 verdict / LT 巡检 → 用 `conclusion-report`。

**最佳-effort 兼容**：

- LT 调用是 best-effort：`/get_exchanged_lt_info/` 偶尔会触发 20s HTTP timeout（实测出现过）。失败时主报告照常完成，JSON 多出 `lt_exchange_error: "Request timeout after 20000ms"` 字段、`lt_exchange` / `lt_exchange_per_region` 为空；text 模式打印 `LT exchange: skipped: <reason>` 后继续。
- Agent 消费 LT 字段前先判 `lt_exchange_error` 是否非空。想多等可加全局 `--http-timeout-ms 60000`，或直接重试同一条命令。

## libra experiment realtime

查看实验的实时监控数据。不带 `--metric-group` 时列出该实验 App 可用的实时仪表盘；带 `--metric-group` 时展示对应指标组的当前数据（默认最近 1 小时）。

```bash
# 列出实验 App 可用的实时仪表盘
bytedcli libra experiment realtime --flight-id <flight_id>

# 查看仪表盘详情（获取指标组 ID）
bytedcli libra experiment realtime --dashboard-info <dashboard_id>

# 查看仪表盘详情及各指标的 SQL 定义
bytedcli libra experiment realtime --dashboard-info <dashboard_id> --show-sql

# 列出所有可用的实时仪表盘（省略 --app-id 时为全局范围）
bytedcli libra experiment realtime --list-dashboards

# 应用身份按 App 列出实时仪表盘
bytedcli --as app libra experiment realtime --list-dashboards --app-id <app_id>

# 查看特定指标组的实时数据（最近 1 小时）
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id>

# 指定时间范围（格式 YYYY-MM-DD HH:mm:ss）
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> \
  --start "2026-04-08 10:00:00" --end "2026-04-08 11:00:00"

# 分钟级数据（默认为小时级）
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> --period-type m

# 同时展示指标说明
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> --describe
```

**选项：**

| 选项                    | 说明                                                                        | 默认值                       |
| ----------------------- | --------------------------------------------------------------------------- | ---------------------------- |
| `--flight-id <id>`      | 实验 Flight ID；`--dashboard-info` / `--list-dashboards` 模式下可省略       | -                            |
| `--app-id <id>`         | Libra App ID；应用身份建议显式传入；`--list-dashboards` 时用于按 App 查询   | 省略时自动解析或使用全局列表 |
| `--metric-group <id>`   | 指标组 ID；省略时列出该 App 可用仪表盘                                      | -                            |
| `--start <datetime>`    | 开始时间（`YYYY-MM-DD HH:mm:ss`）                                           | 当前时间 1 小时前            |
| `--end <datetime>`      | 结束时间（`YYYY-MM-DD HH:mm:ss`）                                           | 当前时间                     |
| `--period-type <type>`  | 数据粒度：`h`（小时级）/ `m`（分钟级）                                      | `h`                          |
| `--describe`            | 在结果中同时展示各指标的说明文字                                            | 关闭                         |
| `--dashboard-info <id>` | 查看指定仪表盘详情，列出其包含的指标组（可配合 `--show-sql` 显示 SQL 定义） | -                            |
| `--list-dashboards`     | 列出可用实时仪表盘；省略 `--app-id` 时为全局范围                            | 关闭                         |
| `--show-sql`            | 与 `--dashboard-info` 配合，显示各指标的 SQL 视图定义                       | 关闭                         |

**典型工作流：**

1. 列出实验可用仪表盘：`bytedcli libra experiment realtime --flight-id <id>`
2. 查看仪表盘详情获取指标组 ID：`bytedcli libra experiment realtime --dashboard-info <dashboard_id>`
3. 查询实时数据：`bytedcli libra experiment realtime --flight-id <id> --metric-group <metric_group_id>`

**时区说明：** TikTok ROW / US 站点（`--site i18n-tt` 或 `--site us-ttp`）的实时数据以 UTC 时间为基准；中国站默认使用本地时间（CST）。不传 `--start`/`--end` 时 CLI 自动按站点时区计算"最近 1 小时"范围。

## libra metric-group get

查看指标组基础信息。文本模式输出 owner / metric / virtual table 摘要；`--json` 返回完整 payload。

```bash
# 按指标组 ID 查询
bytedcli libra metric-group get --id <metric_group_id>

# i18n-tt / TikTok ROW
bytedcli --site i18n-tt libra metric-group get --id <metric_group_id>

# 生产网环境访问 i18n-tt：Gallery / Titan 自动切到 .bytedance.net 入口
BYTEDCLI_NETWORK_PROFILE=prod bytedcli --site i18n-tt libra metric-group get --id <metric_group_id>
```

**选项：**

| 选项        | 说明                    | 默认值 |
| ----------- | ----------------------- | ------ |
| `--id <id>` | Libra 指标组 ID（必填） | -      |

说明：`metric-group get` 当前仅支持 `prod` 和 `i18n-tt`。文本模式默认展示摘要；需要完整结构化结果时加 `--json`。

## libra metric-group template get

查看指标组模版（metric-group template / bundle）详情。支持直接传 `--id` 或模板页面 / API `--url`。

```bash
# 按 template id 查询
bytedcli libra metric-group template get --id <template_id>

# 已知 app 时显式传入
bytedcli libra metric-group template get --id <template_id> --app-id <app_id>

# 查看 conclusion 类型的指标组模版
bytedcli libra metric-group template get --id <template_id> --app-id <app_id> --type conclusion

# 直接传模版页面 URL
bytedcli libra metric-group template get --url <template_url>

# 直接传 API URL
bytedcli libra metric-group template get --url <metric_group_bundle_api_url>

# i18n-tt / TikTok ROW
bytedcli --site i18n-tt libra metric-group template get --url <template_url>
```

**选项：**

| 选项            | 说明                                                                                       | 默认值                                      |
| --------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- |
| `--id <id>`     | Metric group template ID；与 `--url` 二选一                                                | -                                           |
| `--url <url>`   | 模版页面 URL 或 `metric_group_bundle`/`conclusion_report_bundle` API URL；与 `--id` 二选一 | -                                           |
| `--app-id <id>` | Libra App ID；已知时建议显式传入                                                           | 自动解析 / probing                          |
| `--type <type>` | 模版类型：`normal`（metric_group_bundle）或 `conclusion`（conclusion_report_bundle）       | `normal`，403 时自动 fallback 到 conclusion |

说明：省略 `--app-id` 时，会先尝试从模版页面解析 `app_id`，再查询 `metric_group_bundle` 模块下当前用户可访问的 app，最后才回退到 `-1`。两种模版类型使用不同的后端接口：`normal` 对应 `metric_group_bundle`，`conclusion` 对应 `conclusion_report_bundle`（返回层级分类结构和 conclusion 指标组）。不指定 `--type` 时默认 normal，403 时自动 fallback 到 conclusion。文本模式默认展示摘要；需要完整结构化结果时加 `--json`。
**报告字段说明：**

| 列      | 含义                                      |
| ------- | ----------------------------------------- |
| Metric  | 指标名称                                  |
| Version | 实验组名称（对照组不显示，作为 baseline） |
| Mean    | 指标均值                                  |
| Diff%   | 相对对照组的变化百分比                    |
| P-Value | 统计显著性 p 值                           |
| CI      | 置信区间                                  |
| Sig     | `*` p<0.05 / `**` p<0.01 / `***` p<0.001  |

## libra experiment list

使用 Libra 实验列表 page API 列出和筛选实验。`--app-id` 位于请求 URL path，默认 `-1`（全部应用）。

对应接口：

```text
GET /datatester/experiment/api/v3/app/{app_id}/experiment
```

```bash
# 按 App 列出实验；省略 --app-id 时使用 -1
bytedcli libra experiment list --app-id <app_id>

# 按名称搜索
bytedcli libra experiment list --app-id <app_id> \
  --keyword "<experiment_name>" --search-type name

# 按负责人 / 创建者筛选
bytedcli libra experiment list --app-id <app_id> \
  --user "<owner>" --creator "<creator>"

# 我负责的 / 我收藏的
bytedcli libra experiment list --app-id -1 --owner-type my,favourite --page-size 50

# 按实验组配置关键词搜索
bytedcli libra experiment list --app-id -1 \
  --keyword "<config_keyword>" --search-type config

# 多状态由后端在一个请求中处理
bytedcli libra experiment list --app-id <app_id> --status running,paused

# 实验运行周期与给定时间范围相交；必须同时提供 start / end / time-type
bytedcli libra experiment list --app-id <app_id> --time-type running \
  --start '2026-07-11T21:20:00+08:00' --end '2026-07-11T21:20:59+08:00'

# APP 版本条件（shell 中需要引用包含 >= 的值）
bytedcli libra experiment list --app-id <app_id> \
  --app-version 'version_code,>=,<version>'
```

**选项：**

| 选项                              | 请求字段 / 说明                                                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--app-id <id>`                   | URL path 中的 `app_id`，默认 `-1`                                                                                                                                          |
| `--product-id <id>`               | 功能模块，query `product_id`                                                                                                                                               |
| `--layer-id <id>`                 | 实验层，query `layer_id`                                                                                                                                                   |
| `--keyword <values>`              | query `search_keyword`；支持多关键词的 search type 可传逗号分隔值                                                                                                          |
| `--search-type <type>`            | `fuzzy` / `id` / `experiment_ids` / `name` / `creator` / `config` / `tag` / `version_resource` / `debug_user` / `feature_type` / `scene` / `effect_region` / `config_path` |
| `--user <user>`                   | 负责人，query `user`                                                                                                                                                       |
| `--user-group-id <id>`            | 群组，query `user_group_id`                                                                                                                                                |
| `--creator <user>`                | 创建者，query `creator`                                                                                                                                                    |
| `--owner-type <list>`             | 关注范围，query `owner_type`；如 `my,favourite`                                                                                                                            |
| `--manage-type <type>`            | 实验类型，query `manage_type`；多值用逗号分隔                                                                                                                              |
| `--status <list>`                 | 语义实验状态；CLI 映射为 query `status` 的数字值，多值在一个请求中逗号序列化                                                                                               |
| `--time-type <type>`              | `running` / `start` / `end`；与 `--start`、`--end` 一起使用                                                                                                                |
| `--start <time>` / `--end <time>` | 完整时间范围；建议显式携带 UTC offset                                                                                                                                      |
| `--strategy-category-ids <ids>`   | 业务线，query `strategy_category_ids`                                                                                                                                      |
| `--device-platform <platform>`    | 操作系统，`iphone` / `android`                                                                                                                                             |
| `--app-version <filter>`          | `app_version`，格式 `field,operator,version`；field 为 `version_code` / `update_version_code`，operator 为 `==` / `>=`                                                     |
| `--page <n>`                      | 页码，默认 1                                                                                                                                                               |
| `--page-size <n>`                 | 每页条数，默认 20                                                                                                                                                          |

状态值：`ended`、`running`、`pending-schedule`、`debugging`、`paused`、`pending-schedule-end`、`pending-approval`、`rejected`、`draft`、`frozen`、`released`、`deleted`。CLI 会映射成 Libra 的后端数字枚举。

`config` / `tag` / `effect_region` / `experiment_ids` / `config_path` 支持逗号分隔多个关键词。CLI 将这些值原样交给 page API，不做状态拆分、合并、去重或 action 解释。

**时间筛选契约：**

- `--time-type` 只能取 `running` / `start` / `end`。传任一时间边界时必须同时传 `--time-type`；传 `--time-type` 时必须同时给出 `--start` 和 `--end`。
- `--start` / `--end` 支持 ISO 8601、Unix 秒、Unix 毫秒、`YYYY-MM-DD`，以及 `1h ago` / `30m ago` 形式的相对时间。常规 Unix 时间戳建议使用 10 位秒或 13 位毫秒形式。
- CLI 最终向 `start_time` / `end_time` 发送 Unix 秒，毫秒部分向下取整，查询精度为秒。
- 日期形式 `YYYY-MM-DD` 按运行机器的本地时区解释；`--start` 展开到当天 `00:00:00`，`--end` 展开到当天 `23:59:59`，非法日历日期会被拒绝。查询 BJT 时间时建议使用带 `+08:00` 的 ISO 8601，例如 `2026-07-11T21:20:00+08:00`。

## libra feature-flag list

按仓库查看 Libra 配置发布里的 feature flag 列表。该命令走页面侧 API，适合 agent 查询配置状态、值摘要和关联实验。

```bash
# 按 repo 列出 feature flags
bytedcli libra feature-flag list --repo-id 11681182

# 指定页码
bytedcli libra feature-flag list --repo-id 11681182 --page 3 --page-size 10

# 指定 side type 和 app_id
bytedcli libra feature-flag list --repo-id 11681182 --side-type scc_server --app-id -1

# 按 feature key 精确搜索（对齐 Libra 网页 feature_key=）
bytedcli --json libra feature-flag list --app-id -1 --side-type client --feature-key demo_feature_key

# 按参数路径前缀搜索相关子 key，并返回全部端配置
bytedcli --json libra feature-flag list --app-id -1 --side-type scc_server --prefix demo_config_prefix --all-config

# 按完整参数路径搜索（Libra 页面“参数路径”模式），未传 --prefix 时会自动取最后一段作为 prefix
bytedcli --json libra feature-flag list --repo-id 100001 --side-type scc_server --app-id 22 --config-path demo_namespace.demo_config_prefix --all-config

# 只看与某个实验关联的配置
bytedcli libra feature-flag list --repo-id 11681182 --related-experiment-id 4980416

# 核对关联实验的全量发布状态及已发布值
bytedcli --json libra feature-flag list --repo-id 11681182 --side-type scc_server --related-experiment-id 4980416

# 返回每个 feature flag 全部端（app）配置，而非只看第一个端
bytedcli --json libra feature-flag list --repo-id 11681182 --feature-name demo_feature_key --all-config
```

核对某个实验关联配置的全量发布状态及当前已发布值时，优先用 `feature-flag list --related-experiment-id`，并查看 `--json` 输出里的 `feature_flags[].released_value`。`experiment get` 的 `versions[].config` 只表示实验版本与配置值的映射；当前已发布的条件表达式和值，以 `feature-flag list` 返回的 `released_value` 为准。

按客户端 feature key 精确搜索时，使用 `--feature-key <key>`，该参数等价于 Libra 网页列表的 `feature_key=` 查询参数。按配置参数路径前缀搜索相关子 key 时，使用 `--prefix <path>`，该参数等价于 Libra 网页列表的 `prefix=` 查询参数。按页面“参数路径”模式精确搜索完整路径时，使用 `--config-path <path>`，CLI 会透传 `config_path=`；如果没有显式传 `--prefix`，CLI 会自动取完整路径最后一段补 `prefix=`，对齐页面请求。需要查看每个端（app）的全量发布情况时，同时加 `--all-config --json`，查看 `feature_flags[].configs[]` 里的 `released_value` / `release_status`。

默认每条 `feature_flags[]` 只展示第一个端的配置（顶层 `app_id` / `released_value` 等字段）。同一配置在多个端（如抖音短视频、抖音极速版、抖音直播伴侣等）都有发布时，加 `--all-config`：`--json` 模式下每条记录额外带 `feature_flags[].configs[]`（每端一项，各自的 `app_id` / `app_name` / `released_value` / `release_status` 等），文本模式按端展开成多行。顶层字段保持不变，已有调用方无需改动。

**选项：**

| 选项                           | 说明                                            |
| ------------------------------ | ----------------------------------------------- |
| `--repo-id <id>`               | 仓库 ID（必填）                                 |
| `--side-type <type>`           | 配置侧别，默认 `scc_server`                     |
| `--release-status <n>`         | 发布状态筛选，默认 `-1`                         |
| `--page <n>`                   | 页码，默认 1                                    |
| `--page-size <n>`              | 每页条数，默认 10                               |
| `--app-id <id>`                | Libra app ID，默认 `-1`                         |
| `--feature-key <key>`          | 按网页 `feature_key=` 精确搜索 feature flag     |
| `--config-path <path>`         | 按网页 `config_path=` 完整参数路径搜索          |
| `--prefix <path>`              | 按网页 `prefix=` 参数路径前缀搜索               |
| `--related-experiment-id <id>` | 只返回与指定实验关联的配置                      |
| `--all-config`                 | 返回全部端配置（`configs[]`），默认仅取第一个端 |

**输出重点字段：**

| 字段                                | 含义                                   |
| ----------------------------------- | -------------------------------------- |
| `id`                                | feature flag ID                        |
| `key`                               | 配置 key                               |
| `owner_names`                       | 配置负责人                             |
| `status`                            | 启用状态                               |
| `release_status`                    | 发布状态原始值                         |
| `released`                          | 是否已发布                             |
| `value_type`                        | 值类型                                 |
| `released_value`                    | 当前已发布值/条件表达式                |
| `experiment_id` / `experiment_name` | 关联实验                               |
| `configs[]`                         | 全部端配置，仅在 `--all-config` 时返回 |

## libra feature-flag get

读取某个 feature flag 的已发布配置值。该命令先查已发布版本列表，再用页面侧 detail API 拉取目标版本的完整配置值；不传 `--version` 时，默认选最高的已发布版本号。JSON 输出里的 `available_versions` 仅用于展示当前可选的已发布版本元数据，不代表会同时返回每个版本的配置值；实际配置值始终只在 `value` 字段里返回，对应 `selected_version`。

```bash
# 默认读取最新已发布版本
bytedcli libra feature-flag get --app-id 100 --feature-id 123456

# 显式指定发布版本号
bytedcli libra feature-flag get --app-id 100 --feature-id 123456 --version 2

# 也支持传版本记录 ID
bytedcli libra feature-flag get --app-id 100 --feature-id 123456 --version 200001

# JSON 模式返回结构化结果
bytedcli --json libra feature-flag get --app-id 100 --feature-id 123456 --product-id 0
```

**选项：**

| 选项                | 说明                                                    |
| ------------------- | ------------------------------------------------------- |
| `--app-id <id>`     | Libra app ID（必填）                                    |
| `--feature-id <id>` | feature flag ID（必填）                                 |
| `--product-id <id>` | 产品 / module ID，默认 `0`                              |
| `--version <value>` | 发布版本号或版本记录 ID；省略时默认选最高的已发布版本号 |

**输出重点字段：**

| 字段                 | 含义                           |
| -------------------- | ------------------------------ |
| `feature_flag.id`    | feature flag ID                |
| `feature_flag.key`   | 配置 key                       |
| `feature_flag.name`  | 配置名称                       |
| `selected_version`   | 实际读取的版本元数据           |
| `value`              | `configs[0].variants[0].value` |
| `available_versions` | 当前可用的已发布版本列表       |

## libra layer create

创建 Libra 实验层。该命令走 Libra 页面 API，复用 Titan Passport 登录态。

```bash
# 创建实验层
bytedcli libra layer create --app-id 123 --product-id 456 --name demo-layer --owner demo.user

# 指定分流方式和优先级
bytedcli libra layer create --app-id 123 --product-id 456 --name demo-layer --owner demo.user --hash-strategy uid_only --priority 50
```

**选项：**

| 选项                         | 说明                                                                               |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `--app-id <id>`              | Libra app ID（必填）                                                               |
| `--name <name>`              | 实验层名称，全局唯一（必填）                                                       |
| `--owner <user>`             | 实验层 owner（必填）                                                               |
| `--product-id <id>`          | 功能模块 ID（必填）                                                                |
| `--description <text>`       | 实验层描述                                                                         |
| `--hash-strategy <strategy>` | 分流参数：`uid_only`、`uid`、`did`、`rid`、`uuid`、`cdid`、`ssid`、`webid`、`pkid` |
| `--hash-type <type>`         | 实验类型，例如 `ssid` / `uid`                                                      |
| `--hash-unit <unit>`         | 流量层类型，默认 `normal`                                                          |
| `--priority <n>`             | 优先级：`1` 高优，`50` 普通，`100` Launch 层                                       |
| `--traffic-turn <n>`         | 流量流转模式，默认 `0`                                                             |
| `--reusable`                 | 创建为共享层                                                                       |
| `--domain-id <id>`           | 归属互斥域 ID                                                                      |
| `--tag <tag>`                | 标签，可重复传                                                                     |
| `--white-list <user>`        | 白名单用户，可重复传                                                               |
| `--user-group-id <id>`       | 白名单群组 ID，可重复传                                                            |

## libra layer list

查询 Libra 实验层列表。

```bash
# 按功能模块查询
bytedcli libra layer list --app-id 123 --product-id 456

# 搜索名称 / 描述 / owner
bytedcli libra layer list --app-id 123 --search demo --page 1 --page-size 50

# 按分流方式与优先级过滤
bytedcli libra layer list --app-id 123 --product-id 456 --hash-strategy uid_only --priority 50
```

**选项：**

| 选项                         | 说明                            |
| ---------------------------- | ------------------------------- |
| `--app-id <id>`              | Libra app ID（必填）            |
| `--product-id <id>`          | 功能模块 ID                     |
| `--layer-id <id>`            | 实验层 ID 过滤                  |
| `--domain-group-id <id>`     | 互斥域组 ID 过滤                |
| `--hash-strategy <strategy>` | 分流参数过滤                    |
| `--priority <n>`             | 优先级过滤                      |
| `-s, --search <keyword>`     | 模糊检索名称、描述、owner       |
| `--page <n>`                 | 页码，默认 1                    |
| `--page-size <n>`            | 每页数量，默认 20，接口最多 100 |

## libra layer get

按实验层 ID 查询详情。

```bash
bytedcli libra layer get --layer-id <layer_id>
bytedcli --json libra layer get --layer-id <layer_id>
```

**选项：**

| 选项              | 说明                                            |
| ----------------- | ----------------------------------------------- |
| `--layer-id <id>` | 实验层 ID（必填）                               |
| `--app-id <id>`   | Libra app ID（可选；传入后详情会带 app 上下文） |

## libra experiment approve

批准或驳回实验的 peer review。支持传 peer-review 页面 URL 自动解析 `flight_id` / `review_id` / `app_id`，也可手动指定。

```bash
# 推荐：直接传 peer-review URL（从 URL 中提取 flight_id 和 review_id）
bytedcli libra experiment approve --url https://libra-<region>.tiktok-row.net/libra/peer-review/<flight_id>/view/<review_id>

# 驳回 review（默认是批准）
bytedcli libra experiment approve --url <peer_review_url> --reject

# 手动指定 review 和 app ID（无 URL 时使用）
bytedcli libra experiment approve --review-id <review_id> --app-id <app_id>
```

**选项：**

| 选项               | 说明                                                            |
| ------------------ | --------------------------------------------------------------- |
| `--url <url>`      | Libra peer-review 页面 URL，自动解析 `flight_id` 和 `review_id` |
| `--review-id <id>` | Review ID；`--url` 未提供时必填                                 |
| `--flight-id <id>` | 实验 Flight ID；用于推导 `--app-id`，省略时走接口 probing       |
| `--app-id <id>`    | Libra App ID；省略时从 `--flight-id` 推导                       |
| `--reject`         | 驳回 review（默认是批准）                                       |

说明：`--url`、`--review-id` 至少提供一个；传 `--url` 时会从 URL 解析出 `flight_id` 和 `review_id`，覆盖手动传入的同名参数。`<region>` 为 peer-review 站点区域（例如 `sg` / `va` / `us` / `eu`），通常与实验所在 site 一致。

**Operate type 枚举**（`approve` 命令本身不需要传，仅用于理解 review payload 里 `operate_type` 字段的含义；通过 page API 自己 `review/create/{flightId}` 时需要按场景选）：

| 值   | 名称                    | 含义                |
| ---- | ----------------------- | ------------------- |
| `1`  | start                   | 实验开启            |
| `2`  | edit                    | 实验编辑保存        |
| `3`  | resume                  | 实验恢复运行        |
| `4`  | launch_release          | 实验 launch 层全量  |
| `5`  | pause                   | 实验暂停            |
| `6`  | stop                    | 实验关闭            |
| `7`  | close_version           | 关闭实验组          |
| `10` | holdout_start           | Holdout 开始        |
| `11` | edit_holdout_subversion | 编辑 holdout 子版本 |

`auto_launch` 字段：发起 review 时传 `1` 表示 approve 通过后服务端自动 start 实验，传 `0` 表示 approve 后实验仍停在 `paused`，需要再人工 start。`extra` 字段是另一回事（review 触发方式：`0`=manual / `1`=auto / `2`=timer），跟 `auto_launch` 无关。

## libra experiment screenshot

对实验报告页面中指定**指标组**执行两种导出：

- 不传 `--trend-mode`：产出包含组标题与完整指标数据表格的 PNG（与前端“截图”按钮一致）。
- 传 `--trend-mode segment|cumulative`：进入该组的“图表”视图并保存前端“导出图片”生成的**图表专属图片**，不会退化为整组表格截图。当前 Libra UI 生成 JPEG，因此趋势导出默认使用 `.jpeg`。

**用法：**

```bash
# 第一步：查看该实验下所有可用指标组及其 ID
bytedcli --site i18n-tt libra experiment screenshot --flight-id demo-flight-id

# 应用身份显式指定实验所属 App ID
bytedcli --site i18n-tt --as app libra experiment screenshot \
  --flight-id demo-flight-id --app-id 100

# 第二步：指定指标组 ID 直接截图
bytedcli --site i18n-tt libra experiment screenshot --flight-id demo-flight-id --metric-group demo-metric-group-id

# 指标组很宽时：用 --metric-ids 收窄到指定指标列（需与 --metric-group 一起用）
bytedcli --site i18n-tt libra experiment screenshot --flight-id demo-flight-id --metric-group demo-metric-group-id --metric-ids demo-metric-id-a,demo-metric-id-b

# 维度筛选截图：--dims 支持原始 JSON 或直接粘贴 URL 中已编码的 dims= 值
bytedcli --site i18n-tt libra experiment screenshot --flight-id demo-flight-id --metric-group demo-metric-group-id --dims '[{"dims":[{"dimension_key":"channel","id":0,"vals":[{"id":0},{"id":1}]}],"relation_type":"normal"}]'

# 指定输出路径
bytedcli --site i18n-tt libra experiment screenshot --flight-id demo-flight-id --metric-group demo-metric-group-id --output ~/section.png

# 从报告 URL 复现分段趋势；URL 中的 category、data_region、group_id、versions、
# selected_metric_ids、dim_group_id、dims、period_type 会被保留。若同时传 --flight-id，
# 它必须与 URL 中的 flight ID 匹配。
bytedcli --site i18n-tt libra experiment screenshot \
  --url 'https://<libra-host>/libra/flight/<flight_id>/report/main?category=important&data_region=other&group_id=<metric_group_id>&versions=<version_id>&versions=<version_id>' \
  --trend-mode segment \
  --experiment-version <version_id> \
  --metric-ids '<metric_id>' \
  --wait-ms 12000 \
  --output ./segmented-trend.jpeg

# 导出累计趋势
bytedcli --site i18n-tt libra experiment screenshot \
  --url 'https://<libra-host>/libra/flight/<flight_id>/report/main?category=important&data_region=other&group_id=<metric_group_id>' \
  --trend-mode cumulative \
  --wait-ms 12000 \
  --output ./cumulative-trend.jpeg
```

**选项：**

| 选项                                | 说明                                                                                                     | 默认值                                                        |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `--flight-id <id>`                  | 实验 Flight ID；与 `--url` 至少传一个；同时传入时必须与 URL 中的 Flight ID 相同                          | -                                                             |
| `--app-id <id>`                     | Libra App ID；应用身份建议显式传入，避免读取指标组或实验详情时访问 `app/-1`                              | 省略时保持原有自动解析                                        |
| `--url <report-url>`                | `/libra/flight/<id>/report/main` 报告 URL；保留受支持的报告状态                                          | -                                                             |
| `--metric-group <id>`               | 指标组 ID；不填时列出该实验所有可用指标组                                                                | -                                                             |
| `--trend-mode <mode>`               | `segment` 导出分段趋势，`cumulative` 导出累计趋势；两者均需解析到指标组                                  | -                                                             |
| `--experiment-version <id-or-name>` | 实验版本 ID 或精确显示名；可重复传入，显式值覆盖 URL 中重复的 `versions`                                 | -                                                             |
| `--metric-ids <ids>`                | 表格截图可传逗号分隔的 metric id；趋势导出只能传一个，CLI 会显式选择并核验图表指标；**需与指标组一起用** | -（不填则截整组或图表默认指标）                               |
| `--dims <json>`                     | 维度筛选 JSON；支持原始 JSON 或从 Libra URL 复制出的 URL-encoded `dims=` 值                              | -                                                             |
| `--output <path>`                   | 输出路径；表格截图使用 PNG，趋势导出应使用 `.jpeg`/`.jpg`（当前前端导出格式）                            | 表格：`libra-<id>-<timestamp>.png`；趋势：`.jpeg`（当前目录） |
| `--wait-ms <ms>`                    | 页面 networkidle2 后额外等待时间（ms）；趋势图和大型报告通常需要提高到 `12000` 或更高                    | `5000`                                                        |

**说明：** 不指定 `--metric-group` 时，直接调用 Libra 报告 API 列出指标组，无需启动浏览器。指定指标组后，CLI 通过无头浏览器（puppeteer）注入浏览器会话与 Titan Passport Cookie 加载报告页。`--url` 只保留 `category`、`data_region`、`group_id`、重复 `versions`、`selected_metric_ids`、`dim_group_id`、`dims` 和 `period_type`；显式 `--metric-group`、`--metric-ids`、`--dims`、`--experiment-version` 优先。若同时传 `--flight-id`，它必须与 URL 路径中的 Flight ID 一致；若 URL 未含 `dim_group_id`，CLI 不会自行添加该查询参数。

趋势模式会在目标指标组内依次选择“图表”和“分段趋势”或“累计趋势”，等待对应 `lean-data-v2` trend 响应后执行该图表自己的“导出图片”。当前 UI 的该操作生成 `chartSpace.jpeg`，CLI 保存相同 JPEG 字节并在 JSON 输出中返回 `image_format: "jpeg"`；不要把它当作 PNG 或仅通过改文件名转成 PNG。

**何时用 `--metric-ids`：** 指标多的指标组整组截图会渲成几千像素宽、几乎不可读。表格截图若只关心几个指标列，先用不带 `--metric-group` 的 `screenshot`（或 `metric-group get`）拿到指标 id，再传 `--metric-ids <id1>,<id2>` 把页面 `selected_metric_ids` 收窄到这些列。趋势导出只能传一个 metric ID：CLI 会打开目标图表的指标下拉框，选择并核验该指标的可见标签；无法核验时会拒绝导出，避免保存默认指标的图。该参数只对带 `--metric-group` 的截图链路生效，单独传会报 `--metric-ids` 需与 `--metric-group` 一起用的校验错误。

**前置条件（截图功能）：** 需要本机安装 Google Chrome 或 Chromium。趋势导出还需要同时具备 i18n-tt 和 ByteDance SSO 浏览器会话：

```bash
bytedcli --site i18n-tt auth login --session --session-method interactive-browser
bytedcli --auth-site bytedance auth login --session --session-method interactive-browser
```

CLI 按以下优先级查找 Chrome/Chromium：

1. 环境变量 `PUPPETEER_EXECUTABLE_PATH`（显式指定路径，优先级最高）
2. 系统标准安装路径（macOS: `/Applications/Google Chrome.app`；Linux: `/usr/bin/google-chrome` 等）

若未找到 Chrome，CLI 会给出明确提示："Chrome / Chromium not found. Install Google Chrome or set the PUPPETEER_EXECUTABLE_PATH environment variable."。

## libra experiment submit-review

发起一次实验 peer review。CLI 会先调用 UI 同源的 `POST .../check-review`，继承命中规则配置的 reviewer 及其 workflow 元数据，再调用 `POST /datatester/experiment/api/v3/app/{app_id}/review/create/{flight_id}`。因此 USDS 等合规规则会与网页弹窗一致地进入 Review；`--reviewers` 只用于追加邀请人。操作以调用者本人身份记录到实验审计历史。

```bash
# 基础：邀请 reviewer，审核通过后人工 release
# --reviewers 传 Lark / email prefix（"first.last"）；自审就传自己的 username
bytedcli --site i18n-tt libra experiment submit-review \
  --flight-id 12345678 \
  --reviewers <your.username> \
  --description "新策略权重调优"

# 审核通过后自动 release（无需再调 experiment release）
bytedcli --site i18n-tt libra experiment submit-review \
  --flight-id 12345678 \
  --reviewers <your.username>,alice.bob \
  --auto-launch-mode auto

# resume 一个已 paused 的实验（CLI 自动把 operate_type 切到 resume）
bytedcli --site i18n-tt libra experiment submit-review \
  --flight-id 12345678 \
  --reviewers <your.username> \
  --description "resume after config tweak" \
  --auto-launch-mode auto
```

**选项：**

| 选项                        | 说明                                                                                                                                                                      |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--flight-id <id>` (必填)   | 实验 Flight ID                                                                                                                                                            |
| `--reviewers <list>`        | 可选追加 reviewer，使用逗号分隔的 Lark / email prefix（`first.last`）。CLI 会自动带上 `check-review` 返回的规则 reviewer；只有规则未配置 reviewer 时才必须显式传入        |
| `--description <text>`      | 邀请说明（"邀请说明"输入框）                                                                                                                                              |
| `--auto-launch-mode <mode>` | review 通过后行为：`manual`（默认；需再调 release） / `auto`（自动 launch） / `timer`（定时启动）                                                                         |
| `--operate-type <type>`     | review 的操作类型：`launch`（草稿 → 开启）/ `resume`（paused → 恢复）。省略时根据当前 flight `status` 自动推断：`status=3`（draft）→ launch；`status=4`（paused）→ resume |
| `--app-id <id>`             | 省略时通过 `--flight-id` 反查                                                                                                                                             |
| `--extra-body <json>`       | 额外 JSON 对象 merge 到 request body —— 用于 `scheduled_start_time`、`notify_lark_groups` 等站点特有字段                                                                  |

**`--auto-launch-mode auto` 的真实触发条件**：服务端在 review 通过 _且每个 blocking automated check 都 pass/skip_ 之后才 fire release —— 仅有 peer approval 不够。Libra 自动化检查（TikDiff Test / Diff Test / Global Everest / 质量门禁 …）通常要 10–30 分钟。期间用 `experiment review-status` 监控状态；过线后实验自动转 `status=1`（running），不需要手动 `release`。

**Review 规则继承**：`check-review` 返回的 reviewer 对象会原样带入提交，包括 `from_workflow_id_list`、`pass_condition`、`can_delete` 等字段。CLI 不按 region 或审批名称硬编码规则，也不把独立的 `ttp_approve_info` 当作 USDS Review 规则。

## libra experiment release

把一个草稿（`status=3`）实验在 review 通过后正式发布。对应 peer-review 页面"开启实验"按钮，走 page API `PUT /datatester/experiment/api/v3/app/{app_id}/experiment/{flight_id}/launch`。

```bash
# 基础：基于 flight ID
bytedcli --site i18n-tt libra experiment release --flight-id 12345678

# 从 peer-review URL 提取 flight ID
bytedcli --site i18n-tt libra experiment release \
  --url https://libra-sg.tiktok-row.net/libra/peer-review/12345678/view/87654321
```

**选项：**

| 选项                  | 说明                                                                   |
| --------------------- | ---------------------------------------------------------------------- |
| `--flight-id <id>`    | 实验 Flight ID                                                         |
| `--url <url>`         | peer-review URL，自动解析 `flight_id`                                  |
| `--app-id <id>`       | 省略时通过 `--flight-id` 反查                                          |
| `--extra-body <json>` | 额外 JSON merge 到 body（如 Launch 层全量的 `effective_traffic` 字段） |

**何时用**：仅当 `submit-review --auto-launch-mode manual`（默认）时需要。`auto` / `timer` 模式下，服务端会在 review 通过后自己 fire release，不需要也不允许再手动调一次。

**注意事项**：

- **`review-status` 的 `readyForRelease` 不是硬约束**：实测过服务端在 `readyForRelease=false` + 部分 blocking check 仍 `running` 时也允许 explicit `release` 成功（节点状态推送到 client 有延迟，server 决策更宽松）。`readyForRelease=true` 只是 happy-path 信号；`=false` 时仍可尝试 explicit release，最坏返回 `[208] Only testing abtest can be launched` / `[400]`，按错误码再决定回退。
- **response.result.status 是调用前 snapshot**：`release` 接口 response 里的 status 是 _调用前_ 的值（通常是 draft / pre-launch enum），不是 release 后的权威 status。要拿到调用后的真实 status，必须再调 `experiment get`。

## libra experiment pause

暂停一个 running 中的实验。对应 Libra UI 的"暂停"按钮，走 page API `POST /datatester/experiment/api/v3/app/{app_id}/experiment/{flight_id}/pause`。状态从 running (1) → paused (4)，可以用 `experiment resume` 恢复。

```bash
bytedcli --site i18n-tt libra experiment pause --flight-id 12345678

# 附带原因
bytedcli --site i18n-tt libra experiment pause --flight-id 12345678 \
  --extra-body '{"pause_reason":"暂停采集，等待复核"}'
```

**选项：**

| 选项                      | 说明                           |
| ------------------------- | ------------------------------ |
| `--flight-id <id>` (必填) | 实验 Flight ID                 |
| `--app-id <id>`           | 省略时通过 `--flight-id` 反查  |
| `--extra-body <json>`     | 额外 JSON（如 `pause_reason`） |

**注意事项**：

- **response.result 形态不稳定**：有时 server 回 `{status: <pre-call>}` 的 snapshot，有时回 `null`。CLI 在能拿到 `status` 时回显一行 "Pre-call status: <n>"，并始终建议跑一次 `experiment get` 拿 post-call 权威值（lifecycle 端点是 eventually consistent，立即 get 也可能仍是旧值）。
- **server 接受范围跟"子状态"有关，不只看 flight.status**：纯 draft / 已 closed 的 flight 上 `pause` 一般会被 server 拒（`[400] The experiment is not started; it cannot be paused`）；review 推进过程中 server 内部子状态会变化，偶尔同一个 draft 在某些时点也会被 accept，CLI 不预判这些 edge case。要终止配置错的 draft，最干净是直接 `close`（详见 `experiment close` 段落）。

## libra experiment resume

恢复一个已 paused 的实验。对应 Libra UI 的"继续 / 启动"模态，走 page API `POST /datatester/experiment/api/v3/app/{app_id}/experiment/{flight_id}/continue`。

```bash
# 仅当已有一次新的 review 通过后才能直接 resume
bytedcli --site i18n-tt libra experiment resume --flight-id 12345678
```

**重要：pause 会让原 review 失效**，`/continue` 要求"continue/start" operate type 对应的 review 已通过；否则后端返回 `[400] must initiate an experiment review and pass it`。两种典型流程：

```bash
# 流程 A：先 submit-review，让 reviewer approve 后再 resume（无 auto-launch）
bytedcli libra experiment submit-review --flight-id 12345678 --reviewers <your.username> --description "resume" --auto-launch-mode manual
# 等 reviewer approve、blocking checks 全过 ...
bytedcli libra experiment resume --flight-id 12345678

# 流程 B：一步 submit + auto-launch（推荐自动化场景）
bytedcli libra experiment submit-review --flight-id 12345678 --reviewers <your.username> --description "resume" --auto-launch-mode auto
# review 通过且 blocking checks 全过后服务端自动 fire；无需再调 resume / release
```

**选项：**

| 选项                      | 说明                          |
| ------------------------- | ----------------------------- |
| `--flight-id <id>` (必填) | 实验 Flight ID                |
| `--app-id <id>`           | 省略时通过 `--flight-id` 反查 |
| `--extra-body <json>`     | 额外 JSON                     |

**注意事项**：

- **CLI 错误翻译**：原始 `[400] must initiate an experiment review and pass it` 被 CLI 翻译成 `LIBRA_REVIEW_REQUIRED`，并自带 3 步下一步指引（submit-review → approve → resume）。这是 post-hoc 错误翻译，**不会阻断 API 调用**——CLI 仍照常发请求、只在 server 拒绝后再翻译，便于自动化脚本捕获这个 code 进入 review 子流程。
- **draft 上调用一般无语义**：server 会拒回 `[400] The experiment is not paused; it cannot be resumed`。Draft 的 happy path 是 `submit-review` + `release`，不是 `resume`。

## libra experiment close

不可逆地关闭实验。对应 Libra UI 的"结束"按钮，走 page API `POST /datatester/experiment/api/v3/app/{app_id}/experiment/{flight_id}/stop`。状态转为 closed (0)，实验不再采集数据，**也无法重开**——只想暂时停采集请用 `pause`。

```bash
bytedcli --site i18n-tt libra experiment close \
  --flight-id 12345678 \
  --close-reason "实验结论已确认，关闭采集"

# 同时提示重启场景
bytedcli --site i18n-tt libra experiment close \
  --flight-id 12345678 \
  --close-reason "..." \
  --reopen-reason "若后续需复测对照可重启"
```

**选项：**

| 选项                           | 说明                                               |
| ------------------------------ | -------------------------------------------------- |
| `--flight-id <id>` (必填)      | 实验 Flight ID                                     |
| `--close-reason <text>` (必填) | 关闭原因，进入实验审计历史                         |
| `--reopen-reason <text>`       | 重启原因预填（"什么情况下会重新开启此实验"），可选 |
| `--app-id <id>`                | 省略时通过 `--flight-id` 反查                      |
| `--extra-body <json>`          | 额外 JSON（如 `show_close_reason` 等站点特有字段） |

**注意事项**：

- **draft / paused / running 上都生效**：`close` 是 destructive intent 的统一出口，server 不强制 status——发现配置错的 draft 可以直接 close，不必走完"review → launch → close"三步。`--close-reason` 是 server 强制必填字段，相当于一道软性提醒。
- **response.result.status 是调用前 snapshot**：同 `release` / `pause`，response 给出的 status 是 close _前_ 的值。CLI 仅以此回显 "Pre-call status"。取 close 后的权威 status，必须再调一次 `experiment get`；server eventually consistent，刚 close 完几秒内 get 可能仍看到 paused，10s 后才稳定到 closed (0)。

## libra experiment review-status

诊断一次 peer review 的两个维度：① peer review 本身的批准状态 ② 该 review 触发的所有自动化检查节点（i18n_QATest / 质量门禁 / Global Everest / TikDiff Test / Diff Test …）的 pass / fail / running 状态。

```bash
# 通过 review-id（flight-id 用来反查 app_id）
bytedcli --site i18n-tt libra experiment review-status \
  --review-id 87654321 --flight-id 12345678

# 通过 peer-review URL（一行搞定）
bytedcli --site i18n-tt libra experiment review-status \
  --url https://libra-sg.tiktok-row.net/libra/peer-review/12345678/view/87654321

# 找出"仍 blocking 且未通过"的 check 节点（脚本场景）
bytedcli --json --site i18n-tt libra experiment review-status \
  --review-id 87654321 --flight-id 12345678 | jq '.data.checks[] | select(.isBlock and .status != 2)'
```

**选项：**

| 选项               | 说明                                                |
| ------------------ | --------------------------------------------------- |
| `--url <url>`      | peer-review URL，自动解析 `flight_id` + `review_id` |
| `--review-id <id>` | Review ID（`--url` 未提供时必填）                   |
| `--flight-id <id>` | 实验 Flight ID，用来反查 `app_id`                   |
| `--app-id <id>`    | 省略时通过 `--flight-id` 反查                       |
| `--verbose`        | `--json` 模式下额外回传 raw review payload          |

**典型用途**：`submit-review` 后想知道为什么 `release` 报 `[400] There is a review of ongoing experiments`——多半是某个 blocking check 还在 running 或 failed。`is_block: true` 的节点必须达到 `status=2`（passed）或 `status=4`（skipped）才允许 `release`；`is_block: false` 的节点只是 advisory，不阻塞。

**注意事项**：

- **响应字段是 camelCase（不是 snake_case）**：顶层和 check 节点字段一律是 `nodeKey` / `nodeName` / `statusLabel` / `blockOption` / `isBlock` / `iframeUrl` / `nodeUrl` / `peerReviewStatusLabel` / `blockingFailedChecks` / `automatedStepStatus` / `readyForRelease`。`jq` 脚本读响应时按 camelCase 取值，否则全是 `null`。
- **`block_option` 是失败的权威 oracle，不是 `status` / `err_msg`**：对一个 blocking check，`block_option=2`（BLOCK）就是"该 check 当前在阻断 review"——pass 后 server 会清成 `0`，fail 时即便 `status=2`（completed）也保留 `2`。`err_msg` 在 TikDiff 失败时常为空，不能作为失败判据。已通过的 helper `inferBlockNodeFailed()` 把这些信号组合好了；脚本直接用 `blockOption === 2 && status === 2` 也能识别失败。
- **`readyForRelease` 是 hint 不是 gate**：见 `experiment release` 段注意事项——server 决策比这个聚合字段更宽松。
- **`checks[]` 节点集随实验配置而变**：不是所有 check 节点都会对所有 review 触发，TikDiff Test、Diff Test 这类 conditional check 对部分实验**根本不出现**在 `checks[]` 里。脚本判断某个特定 check 是否通过时要用 `find` 而不是按下标取——**不存在 ≠ 失败**，是 "本 review 与该 check 无关"。

## libra experiment tikdiff-status

列出某次 Libra review 关联的 TikDiff 子任务清单（"TikDiff Test"这个 check 节点下细化到 case → report 层级的明细）。本质是把 Libra peer-review 页面里 TikDiff iframe（`holmes.tiktok-row.net/tikdiff/tikdiff_libra`）调用的 `GET /api/v1/tikdiff/libra/tasks` 端点搬到 CLI 上，不需要开浏览器。鉴权复用 Titan Passport cookie，不走 BDSSO。

```bash
# 通过 peer-review URL
bytedcli --site i18n-tt libra experiment tikdiff-status \
  --url https://libra-sg.tiktok-row.net/libra/peer-review/12345678/view/87654321

# 通过 flight + review ID
bytedcli --site i18n-tt libra experiment tikdiff-status \
  --flight-id 12345678 --review-id 87654321

# 只看 flight（自动用 review_info.current_review_id 反查 review）
bytedcli --site i18n-tt libra experiment tikdiff-status --flight-id 12345678
```

**选项：**

| 选项                | 说明                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------- |
| `--url <url>`       | peer-review URL，自动解析 `flight_id` + `review_id`                                       |
| `--flight-id <id>`  | 实验 Flight ID                                                                            |
| `--review-id <id>`  | Review ID；省略时自动用 flight 的 `review_info.current_review_id`                         |
| `--app-id <id>`     | 暂未强制要求，保留 forward-compat                                                         |
| `--region <region>` | Holmes 数据 region（`sg` / `cn` / `va` / …）；省略时根据 `--site` 推断（tt→sg，byted→cn） |

**与 `bytedcli holmes tikdiff get` 的分工**：`holmes tikdiff get --task-id <id>` 是单个独立 task 视角；`libra experiment tikdiff-status` 返回一次 Libra review 下所有 case 的 task，并按 case 分组。

**输出结构**：每个 case 一行（含 `case_id` / `case_name` / `psm`），下面是该 case 的 `reportList`，每个 report 给出 `task_id` / `status`（`success` / `failed` / `running`）/ `taskStatus`（`TASK_FINISHED` / `TASK_RUNNING` 等）/ `duration` / 跳到 Holmes 的 deep link。

**注意事项**：

- **不是所有 review 都会生成 TikDiff 子任务**：是否触发 TikDiff Test 由实验配置决定，并非每个 review 都会跑。**区分方式**：先调一次 `review-status`，看 `checks[]` 里**是否存在** `nodeName="TikDiff Test"` 节点——不存在则该 review 与 TikDiff 无关，0 task 是终态，不必再轮询；存在但节点 `status` 还是 `0/1`（not_started / running），才需要等几分钟后重试 `tikdiff-status`。
- **节点出现 ≠ 会真跑 case**：`checks[]` 里出现 `TikDiff Test` 节点也不一定真生成 task。零影响实验（极小 traffic / 极短 duration / 空 config 等）会被 server fast-path 跳过重 checks 直接放行——表现为 `submit-review` 后 1–2 分钟就转 `status=1`，节点停留在 `status=0/4`，`tikdiff-status` 永远 `tasks: []`。把 "review-status 节点是否存在" 当作 **必要不充分** 条件，最终以 `tikdiff-status` 返回的 task 数为准。
- **0 task 时 schema 仍然正常**：上面两种情况下 `tasks: []` + `total: 0`，不会 throw。脚本用 `.data.tasks | length` 判断即可，不需要额外的 try/catch。
- **TikDiff Test 节点 `status=4` (skipped) 是正常态**：实验配置不需要执行 TikDiff 时，server 会把节点标为 skipped 而非 passed，`block_option` 也会清成 `0`。agent 不要把 skipped 当作异常 / 失败。

## libra experiment tikdiff-rerun

重跑某次 Libra review 下面失败的 TikDiff 子任务。对应 Libra TikDiff iframe"重跑"按钮，走 `POST /api/v1/tikdiff/libra/rerun`，body 为 `{rerun_tasks: number[]}`。服务端对已成功/正在跑的 task 静默 no-op；对失败 task 起新 attempt 并产生新 `task_id`（同 case 下 `reportList` 多一条）。

```bash
# 推荐：一键扫所有 status=failed 的 task 批量重跑
bytedcli --site i18n-tt libra experiment tikdiff-rerun \
  --flight-id 12345678 --review-id 87654321 --all-failed

# 指定具体 task_id（多次重跑同一个、或只跑其中几个）
bytedcli --site i18n-tt libra experiment tikdiff-rerun \
  --flight-id 12345678 --review-id 87654321 --task-id 1234567
bytedcli --site i18n-tt libra experiment tikdiff-rerun \
  --flight-id 12345678 --review-id 87654321 --task-id 1234567,1234568
```

**选项：**

| 选项                | 说明                                                                              |
| ------------------- | --------------------------------------------------------------------------------- |
| `--url <url>`       | peer-review URL，自动解析 `flight_id` + `review_id`                               |
| `--flight-id <id>`  | 实验 Flight ID                                                                    |
| `--review-id <id>`  | Review ID；省略时自动用 flight 的 `review_info.current_review_id`                 |
| `--app-id <id>`     | 暂未强制要求，保留 forward-compat                                                 |
| `--region <region>` | Holmes 数据 region；省略时根据 `--site` 推断                                      |
| `--task-id <ids>`   | 显式指定要重跑的 Holmes TikDiff `task_id`，可重复传或逗号分隔                     |
| `--all-failed`      | 自动扫当前 review 下所有 `status='failed'` 的 sub-task 一次性重跑（典型恢复路径） |

**重跑后**：再调 `tikdiff-status` 可以看到同一 case 下 `reportList` 多了一条新 entry（新 `task_id`）；老的失败 entry 不会消失，只是不再是该 case 的"当前"结论。

**注意事项**：

- **`--all-failed` 无失败 task 时优雅 no-op**：服务端返回 `rerun_tasks: []` + `note: "no failed sub-tasks to rerun"`，CLI 不报错、退出码为 0。自动化脚本无需预先检查 failed task。
- **`--task-id` 不强制 status=failed**：显式指定 task_id 时，server 接受已 `success` 的 task 重跑（产生新 task_id）。适用于"对结论不放心，再跑一次确认"场景；用 `--all-failed` 才会被 server 过滤到只剩 failed 子集。
- **新 task_id 在 `tikdiff-status` 的 reportList 里**：同一 case 的 `reportList` 是按时间顺序累积，最近一次重跑的 task_id 在数组**最后**。脚本判断 case 当前结论时，应该取 `reportList[-1].status` 而不是首条。

## libra experiment update（CLI 暂未实现 → page API workaround）

`bytedcli libra experiment` 当前**没有 `update` 子命令**。需要修改已存在实验的字段（`versions[].config` / `description` / `owners` / `effected_regions` ...）时，直接调 page API：

```
PUT /datatester/experiment/api/v3/app/{appId}/experiment/{flightId}
```

**Read-merge-write 模式**：先 GET 拿当前完整 payload（用 `bytedcli libra experiment get`），patch 想改的字段，整个对象 PUT 回去。**不要**像 create 那样 strip 派生字段——update 时后端容忍这些（毕竟它们就是后端自己生成的），strip 反而可能丢字段。

实测行为：

| 实验状态                                              | PUT 是否安全      | 说明                                                                                                                                                                          |
| ----------------------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `status: 3` (draft/testing)                           | ✅ 直接 PUT       | 无 review 状态可影响                                                                                                                                                          |
| `status: 4` (paused) + `review_status: 2` (in_review) | ✅ 直接 PUT       | review 不会失效，原 review 链接照常生效                                                                                                                                       |
| `status: 1` (running)                                 | ⚠️ 取决于改的字段 | 改 `versions[].config` 通常会触发新一轮 `operate_type=2` 的 edit review，要重新发 review；改纯 metadata（如 `description`）通常无副作用。**实战中要现场观察 `review_status`** |

PUT 后用 `bytedcli libra experiment get --flight-id <id>` 反查确认改动落库。

## libra experiment search

使用 Libra 实验列表 page API 搜索实验。它与 `experiment list` 共用全部筛选项；`--key-path` 会固定发送 `search_type=config_path`。

```bash
# 按完整配置路径搜索
bytedcli libra experiment search --app-id -1 --key-path "<config_path>"

# 多个配置路径
bytedcli libra experiment search --app-id <app_id> \
  --key-path "<config_path_1>,<config_path_2>"

# 使用其他页面搜索类型
bytedcli libra experiment search --app-id <app_id> \
  --keyword "<keyword>" --search-type fuzzy --status running,paused
```

`experiment search` 必须提供 `--key-path` 或 `--keyword`，其他页面筛选项用于缩窄候选；两者互斥。experiment page API 没有 `exact_match` 字段；需要精确匹配 global parameter 对象时，使用 `libra global-param search --key-path <path> --exact-match`。

## libra global-param search

调用独立的 global-parameter API，保留旧 key path 对象搜索和 `exact_match` 语义：

```text
POST /datatester/global_param/api/v3/global_param/list/
```

```bash
# 模糊匹配 global parameter key path
bytedcli libra global-param search --key-path "<config_path>"

# 精确匹配
bytedcli libra global-param search --key-path "<config_path>" --exact-match
```

**选项：**

| 选项                | 说明                                                |
| ------------------- | --------------------------------------------------- |
| `--key-path <path>` | Global parameter key path（必填）                   |
| `--app-id <id>`     | body 中的 `app_id`，默认 -1                         |
| `--exact-match`     | body 中的 `exact_match`，默认 false                 |
| `--status <list>`   | 语义状态；映射到 `status_list`，默认 running,paused |
| `--page <n>`        | 页码，默认 1                                        |
| `--page-size <n>`   | 每页条数，默认 20，最大 30；超出会 clamp            |

这个 API 与页面实验搜索不是同一个接口。通常排查“某配置路径影响过哪些实验”应先用 `experiment search --key-path`；只有明确需要 global parameter 对象或精确匹配语义时才用 `global-param search`。

## 概念辨析：业务 ab_tag vs Libra `versions[].ab_tag`

这两个 "ab_tag" 语义不同，首次处理时容易混淆。

| 名字                                       | 出处                                                                           | 类型          | 用途                                                                      |
| ------------------------------------------ | ------------------------------------------------------------------------------ | ------------- | ------------------------------------------------------------------------- |
| **Libra payload 里的 `versions[].ab_tag`** | 实验 API payload 字段                                                          | 字符串 / null | Libra 平台内部对版本的"标签"标识，绝大多数实验都是 `null`，不影响业务行为 |
| **业务代码里的 `ab_tag`**                  | 策略 params（典型形式 `ctx.params->get({"<module>", "ab_tag"}, "<default>")`） | 字符串        | 落到 metric 上报的 tagkv，让 metric 平台能按 tag 切分实验组数据           |

**实战要点**：

- 用户说"换 ab_tag"时，**99% 指业务代码侧**。要去 `versions[].config` 里塞策略 params 路径覆盖默认值。Libra 的 `versions[].ab_tag` 字段几乎用不到。
- 业务代码里的 `ab_tag` 通常都有 default 值，不显式设也能跑，metric 会落到 default tag 上。**默认不需要在 v1 config 里塞 ab_tag** —— 除非用户明确说"要按这个实验单独切分指标"。
- control 组通常不需要塞 ab_tag（control 用默认行为，相关函数链路可能根本不会被调用，没有上报）。
- 怎么知道某个 metric 用的 ab_tag 来源？grep 业务代码里 `emit_timer` / `emit_counter` 的调用，看 tagkv 里 ab_tag 是从哪条 `params->get` 拿的，再决定要不要在 config 里塞。

## libra app list

列出所有可用的 Libra App。

```bash
bytedcli libra app list
```

## libra experiment hit get

根据测试用户 ID 查询其历史请求是否命中指定实验。命令固定先调用测试用户资格校验接口；只有 `is_whitelist_user=true` 时才会继续调用命中诊断接口。

```bash
# 默认查询最近 72 小时
bytedcli --site i18n-tt libra experiment hit get \
  --flight-id <flight_id> \
  --user-id <user_id>

# 显式指定时间窗和可选 Caller PSM
bytedcli --site i18n-tt --json libra experiment hit get \
  --flight-id <flight_id> \
  --user-id <user_id> \
  --start '72h ago' \
  --end <iso_time> \
  --psm example.service \
  --timeout-ms 180000
```

未通过资格校验时，CLI 不调用命中诊断接口，并提示：`仅支持预登记的测试用户，实验配置的测试用户；添加测试用户后，预计 5 分钟后可查到结果，请耐心等待`。第二阶段诊断默认允许等待 600 秒；可用 `--timeout-ms` 显式覆盖，最大 1200000 毫秒（1200 秒）。whitelist 前置校验仍使用普通请求超时。

**选项：**

| 选项                | 说明                                                          |
| ------------------- | ------------------------------------------------------------- |
| `--flight-id <id>`  | 实验 Flight ID（必填）                                        |
| `--user-id <id>`    | 预登记或实验配置的测试用户 ID（必填，按字符串保留大整数精度） |
| `--start <time>`    | 开始时间；Unix 秒、ISO 时间或相对时间，默认结束时间前 72 小时 |
| `--end <time>`      | 结束时间；Unix 秒或 ISO 时间，默认当前时间                    |
| `--psm <psm>`       | 多条命中记录时可选的 Caller PSM 过滤条件                      |
| `--timeout-ms <ms>` | 第二阶段诊断超时；默认 600000，最大 1200000 毫秒              |

## libra test-user list

查看实验所有版本的测试用户。

```bash
bytedcli libra test-user list --flight-id <flight_id>
```

## libra test-user add

添加测试用户到实验版本。

```bash
bytedcli libra test-user add --flight-id <flight_id> --uid <uid>

# 指定版本（多实验组时需要）
bytedcli libra test-user add --flight-id <flight_id> --uid <uid> --version <vid>

# 多个 UID（逗号分隔或重复 --uid）
bytedcli libra test-user add --flight-id <flight_id> --uid uid1,uid2
```

## libra test-user delete

从实验版本中删除测试用户。

```bash
bytedcli libra test-user delete --flight-id <flight_id> --uid <uid>
bytedcli libra test-user delete --flight-id <flight_id> --uid uid1,uid2 --version <vid>
```

**test-user 选项：**

| 选项               | 说明                                       |
| ------------------ | ------------------------------------------ |
| `--flight-id <id>` | 实验 Flight ID（必填）                     |
| `--app-id <id>`    | Libra App ID；应用身份建议显式传入         |
| `--uid <uid>`      | 测试用户 UID，可逗号分隔或重复使用（必填） |
| `--version <vid>`  | 目标版本 ID 或名称（单实验组时自动选择）   |

## libra test-whitelist list

查看实验所有版本的测试白名单分群。

```bash
bytedcli libra test-whitelist list --flight-id <flight_id>
```

## libra test-whitelist add

添加测试白名单分群到实验版本。

```bash
bytedcli libra test-whitelist add --flight-id <flight_id> --group-id <group_id>

# 指定版本（多实验组时需要）
bytedcli libra test-whitelist add --flight-id <flight_id> --group-id <group_id> --version <vid>

# 多个分群 ID（逗号分隔或重复 --group-id）
bytedcli libra test-whitelist add --flight-id <flight_id> --group-id 451385,451386
```

## libra test-whitelist delete

从实验版本中删除测试白名单分群。

```bash
bytedcli libra test-whitelist delete --flight-id <flight_id> --group-id <group_id>
bytedcli libra test-whitelist delete --flight-id <flight_id> --group-id 451385,451386 --version <vid>
```

**test-whitelist 选项：**

| 选项               | 说明                                            |
| ------------------ | ----------------------------------------------- |
| `--flight-id <id>` | 实验 Flight ID（必填）                          |
| `--app-id <id>`    | Libra App ID；应用身份建议显式传入              |
| `--group-id <id>`  | 测试白名单分群 ID，可逗号分隔或重复使用（必填） |
| `--version <vid>`  | 目标版本 ID 或名称（单实验组时自动选择）        |
