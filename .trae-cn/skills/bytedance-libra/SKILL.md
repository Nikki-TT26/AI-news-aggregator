---
name: bytedance-libra
description: "Operate Libra/DataTester A/B experiments and config-center releases via bytedcli: search and inspect experiments, diagnose whether a test user hit an experiment, read raw change history and traffic-effect records, audit configuration changes around an incident time, query metric reports and significance, manage test users, handle experiment lifecycle and peer-review actions, inspect automated checks, rerun failed TikDiff tasks, create config release tickets, execute whitelist tests, create and poll reviews, deploy rollout percentages, and execute rollbacks. Use for Libra, DataTester, A/B test, experiment/flight, config release, config-path search, traffic allocation, user hit diagnosis, P-Value, metric trends, test users, peer review, review checks, TikDiff reruns, or incident-time experiment audits."
---

# bytedcli Libra

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

Libra (DataTester) A/B 实验平台 CLI，通过 SSO 认证访问，无需额外凭证。

## When to use

- 查看实验详情、流量分配、版本配置
- 查看实验报告：指标数据、P-Value、显著性判断
- 分析指标趋势：逐日累计或分段趋势
- 搜索 / 筛选实验
- 按 repo / side type 列出配置发布里的 feature flag
- 创建并操作 config-center 配置发布 ticket；轮询 review 状态、调整放量或回滚
- 管理实验测试用户
- 根据测试用户 ID 诊断是否命中实验
- 驱动实验完整生命周期：发起 review、approve、release、pause、resume、close（page API，调用者本人记入审计历史）
- 诊断 peer review 的自动化检查节点状态（TikDiff Test / Diff Test / Global Everest / 质量门禁 / i18n_QATest 等），按 check 节点维度定位 release 卡住的原因
- 列出 / 重跑某次 Libra review 关联的 TikDiff 子任务（评审页 iframe 暴露的那批），无需开浏览器

## Prerequisites

- 通用调用方式见 `references/invocation.md`
- 首次使用按目标实验所在 site 一次性 `auth login`（device login，后续自动复用）：
  - CN 实验：`bytedcli auth login`
  - TT / ROW 实验：`bytedcli --site i18n-tt auth login`

> 下面示例直接写 `bytedcli`，实际执行前缀见 `references/invocation.md`。

## Workflows

### 配置发布

处理 config-center 配置发布时，读取 `references/libra.md` 的 `libra config-release` 章节。该命令组提供原子操作，不包含 approve/reject 或一键编排；写操作默认 dry-run，显式 `--yes` 才提交。

### 创建实验

两种方式：已有合适的同类实验模板时，使用方式 1（从模板克隆）；没有模板、但已明确实验配置（名字、owner、layer、机房、filter、各组参数）时，使用方式 2（手工 minimal payload）。下面 #### 冲突决策 / #### 白名单 KEEP 等附段两种方式都适用。

#### 观测指标组前置门禁（强制）

创建实验前必须先完成指标组回看，不能创建没有显式关注指标组的裸实验：

1. 回看当前请求、相关历史对话、用户提供的文档，以及源实验 / 模板上下文，收集此前提到的指标组名称、ID 和来源 flight/template。用户说“之前关注的指标都带上”时，取相关上下文中的并集，不得只保留最后一次提到的指标组。
2. 有源 flight 时先执行 `bytedcli --json libra experiment get --flight-id <source_flight_id>`，读取其 `metrics` 完整对象；必要时再用 `libra experiment report --flight-id <source_flight_id>` 核对指标组 ID / 名称。只有名称没有 ID 时必须继续查证，不能猜 ID。
3. 按 `metric_group_id` 去重，把确认后的完整对象写入最终 payload 的 `metrics`。模板自带指标组与历史对话新增指标组取并集；禁止用 `metrics: []` 覆盖模板指标。
4. 在真正调用 create 前，向用户汇报最终指标组的 `metric_group_id`、名称和来源。`libra experiment create` 默认会以 `LIBRA_METRICS_REQUIRED` 拒绝缺失或空的 `metrics`。
5. 只有用户明确要求“仅依赖应用默认指标组，不配置关注指标组”时，才允许加 `--allow-empty-metrics`。不能把该参数当作排障或兼容性捷径。
6. 创建成功后立即执行 `libra experiment get` 回读，核对新实验中的关注指标组 ID 与创建前清单一致；不一致时报告缺失项，不能把实验视为交付完成。

#### 方式 1：从模板克隆

如果你已经有 Libra 单实验模板 ID，优先直接走模板模式。模板默认值会被转换成 create payload，再由你的 request body 覆盖实验专属字段：

```bash
# 示例：基于现有单实验模板（3139）
bytedcli --json libra experiment create --app-id 1193 --template-id 3139 --request-file ./override.json
```

模板模式当前支持 Libra 单实验模板。实际使用时，至少建议在 override 里覆盖：

- `name`
- `versions`
- `metrics`（模板指标与历史上下文指标的去重并集）
- 必要时覆盖 `description`、`filter_rule`

推荐创建方式是“找一个同 layer / 同类型的实验作为模板，修改最小必要字段，再发起 create”。直接手写 payload 容易触发 `HTTP 500 网络异常` 或 `[213] create experiment failed`，因为 Libra 对 `layer_info` / `version_resource` / `traffic_map` / `metrics` 的组合有隐性校验。

```bash
# 1) 拉模板完整结构
bytedcli --site i18n-tt --json libra experiment get --flight-id <template_flight_id> > /tmp/template.json

# 2) 基于模板改最小必要字段：至少 name，以及需要改的 versions / owners / effected_regions；
#    保留 layer_info（连同 layer_id / create_layer_auto:false / product_id / hash_strategy 等）、
#    version_resource、traffic_map、filter_rule、metrics、flight_mode、experiment_mode、
#    manage_type、strategy_category_ids。
#    剥掉派生/只读字段（id / status / start_time / end_time / create_time / modify_time /
#    truly_effected_regions / father_info / reopen_info / review_info / actions / extra /
#    small_traffic_link / large_traffic_link 等）。

# 3) 发起创建
bytedcli --site i18n-tt --json libra experiment create --app-id -1 --request-file /tmp/new_exp.json
# 成功后从返回 JSON 的 experiments[0].id 取新 flight_id，拼接链接：
# https://data.bytedance.net/libra/flight/<experiment_id>/report/main
```

`libra experiment create` 默认会复刻 GUI 在 `/batch_create_experiment` 上的两步握手：

1. 第一次 POST `only_verification:true, skip_verification:false`，让后端做 filter rule / 流量 / layer 冲突等真实校验，保留 `code=213` 时的 `messages` / `conflict_experiments` 详情。
2. 第二次 POST `only_verification:false, skip_verification:true`，真正落库。

两步握手对所有站点都生效。host 由 `--site` 和网络 profile 自动路由：cn 默认 → `data.bytedance.net`；i18n-tt 默认 → `libra-sg.tiktok-row.net`；生产网环境设置 `BYTEDCLI_NETWORK_PROFILE=prod` 后，i18n-tt 切到 `libra-sg.bytedance.net`。路径都是同一个 `/batch_create_experiment`。

因此，**请求体里不要写 `skip_verification` / `only_verification`**；CLI 会自动处理。如果确实需要保留旧的单次 POST 行为（例如 body 中已手工设置 `skip_verification:true`），加 `--no-verify`。

冲突处理：克隆 backtest / 同 layer 实验时，preflight 偶尔会回 `code=213, can_skip=true`（典型场景：新实验和老实验共用 `layer_id` + `ab_tag`）。这时默认会以 `LIBRA_CREATE_CONFLICTS` 报错并提示重试加 `--skip-conflicts`；确认无误后重试一次即可放行：

```bash
bytedcli --site i18n-tt libra experiment create \
  --app-id -1 \
  --request-file /tmp/new_exp.json \
  --skip-conflicts
```

#### 冲突决策：什么时候才应该用 `--skip-conflicts`

`--skip-conflicts` 不是通用放行开关；同 key 跨 layer 强行 skip 会让两个实验落到同一批用户上，互相污染指标。preflight 报 `LIBRA_CREATE_CONFLICTS` 时按下面的算法决策：

1. 取所有 `data.conflict_experiments` 的 unique `layer_id` 集合 S。注意 preflight 响应里只给 `layer_type`，要拿 `layer_id` 需要对每个冲突 `experiment_id` 调一次 `bytedcli libra experiment get`（`-j` 模式取 `data.layer_info.layer_id`）。
2. 决策：
   - `|S| == 1` 且 ≠ 当前 `layer_info.layer_id` → **colocate**：把当前 payload 的 `layer_info.layer_id` 改成那个唯一冲突 layer，重新跑一次 create。preflight 会把"在同一 layer 上的冲突"判为可接受。
   - `|S| == 1` 且 == 当前 `layer_info.layer_id` → 同层冲突（多半是 `versions[].ab_tag` / 业务 key 重叠），停下来问用户。
   - `|S| > 1` → 物理上无法 colocate，停下来问用户。
3. 撞冲突且无法 colocate 时，给用户列冲突清单 + 三个选项：放弃 / 改 keys / 明确同意 skip。**只有用户拍板说 skip，才加 `--skip-conflicts`**。

关键 payload 规则（来自 JS bundle 反编译和实测结论）：

- 创建依赖（子）实验前，读取 `references/libra.md` 的 `libra experiment child create` 章节。该流程是外部写操作，必须先确认父实验、父版本、layer、目标 region 和 traffic，再使用标准子资源命令创建并自动读回校验父子关系。

- `versions[].type` 是数字 `0`（对照）/`1`（实验组）；`versions[].config` 必须是 **JSON 字符串**（例如 `"{\"k\":true}"`），不是对象。
- `metrics` 是非空对象数组；每项至少保留已核验的 `metric_group_id` 及源对象中的名称、类型和维度等字段。CLI 默认拒绝缺失或空数组。
- **顶层 `product_id` + `app_id`**：page API 用实验**顶层**的这两个字段拉层治理配置，**缺一**就会报 `[500] 获取层治理配置失败，请稍后重试`（只补 `product_id` 不够）。clone / minimal body 容易漏掉这两个字段，因为它们在 `experiment get` 输出里位于顶层、不在 `layer_info` 里。`bytedcli` 在 POST 前会自动补齐（先看 `layer_info`，仍缺则用 `layer_id` 拉 layer detail）；显式带上更稳定。
- `layer_info` 必须是完整对象：克隆时 **复用模板的 `layer_id`** 并保持 `create_layer_auto:false`；设 `create_layer_auto:true` 会让 `batch_create_experiment` 后端抛 HTTP 500（"网络异常"）。
- `version_resource`（流量占比，backtest 常见 `0.2`）和 `traffic_map`（流量段，backtest 常见 `[{"start_time":"","pieces":[{"begin":0,"length":200}]}]`）必须保留，否则 preflight 会报 `可用流量不足，请重新设置流量分配`。
- Backtest / 自动审批型实验不需要 review；继续调用 `review create` 会收到 `[215] 无需创建review`。

#### 从模板克隆时：用白名单 KEEP，不要用黑名单 DROP

`bytedcli libra experiment get` 拉到的模板 JSON 里，不少字段嵌的是模板自己的运行时引用（不是策略元信息）。直接把完整对象用于新实验会被 `batch_create_experiment` 抛 `[500] record not found`，且报错通常无法定位到具体字段。常见的“不能照搬”的字段：

- `lane_gray_info`：嵌模板原本的灰度报告 URL、灰度时间戳、lane 名字
- `test_start_time` / `freeze_time` / `version_freeze_time` / `freeze_status`：模板实验的生命周期时间
- `is_query_experiment` / `version_freeze` / `is_version_freeze_historically_closed` / `is_favourite`：用户态字段
- `close_reason` / `reopen_reason` / `date_end_time` / `is_date_end`：关停信息
- `id` / `status` / `create_time` / `modify_time` / `truly_effected_regions` / `father_info` / `reopen_info` / `review_info` / `actions` / `extra` / `small_traffic_link` / `large_traffic_link`：派生 / 只读字段

**安全做法**：用白名单 KEEP，只从模板继承"策略元字段"，剩下的让后端补默认值。典型可继承的 11 个字段：`flight_mode` / `experiment_mode` / `reuse_type` / `scene` / `metric_scene` / `is_long_time_flight` / `enable_gradual` / `is_mab` / `transmit` / `manage_type` / `strategy_category_ids`。`layer_info` 同理只 KEEP 必要字段：`hash_strategy` / `create_layer_auto` (固定 `false`) / `purpose` / `layer_id` / `layer_name` / `layer_status` / `layer_type` / `product_id` / `layer_reusable` / `layer_priority` / `layer_hash_name` / `domain`。

业务字段（`name` / `description` / `app_id` / `product_id` / `duration` / `type` / `version_resource` / `traffic_map` / `effected_regions` / `owners` / `filter_rule` / `versions` / `metrics`）必须显式重写。顶层 `product_id` / `app_id` 不在 `layer_info` 里，白名单 KEEP 时最易漏；漏了会撞 `[500] 获取层治理配置失败`（CLI 会自动补齐，见「关键 payload 规则」）。

#### 方式 2：手工 minimal payload

不要把 `experiment get` 的 response 整段回 echo 给 `experiment create` —— get 返回的是 server 已 normalize 的 snapshot，里面有 ~130 个 metric_group 引用、`actions` / `review_info` / `truly_effected_regions` 等派生字段，回传后会被 server 隐性校验拒（典型表现：`[500] record not found`，且追溯不到具体字段）。直接 hand-craft 一份 ~20 字段的 minimal create body 反而稳（注意 minimal body 不要漏顶层 `product_id` / `app_id`，否则会撞 `[500] 获取层治理配置失败`，见上文「关键 payload 规则」；`bytedcli` 会自动补齐）：

```bash
# 1) 准备 minimal create body
cat > /tmp/new_exp.json <<'PAYLOAD'
{
  "app_id": 22,
  "product_id": <product_id>,
  "duration": 86400,
  "effected_regions": ["SG", "VA"],
  "owners": [{"name": "<your.username>"}],
  "name": "<实验名>",
  "description": "<目的，进入审计历史>",

  "manage_type": "strategy",
  "flight_mode": 1,
  "experiment_mode": 1,
  "reuse_type": 0,
  "scene": 0,
  "metric_scene": 2,
  "is_long_time_flight": 0,
  "enable_gradual": false,
  "is_mab": 0,
  "transmit": true,
  "strategy_category_ids": [<category_id>],

  "filter_type": "rule",
  "filter_rule": [],
  "version_resource": 0.001,
  "traffic_map": null,

  "versions": [
    {"name": "v0", "type": 0, "config": "{}"},
    {"name": "v1", "type": 1, "config": "{\"<key>\":\"<value>\"}"}
  ],
  "metrics": [
    {
      "type": "important",
      "metric_group_id": <metric_group_id>,
      "name": "<metric_group_name>",
      "metric_group_type": "ordinary",
      "status": 1,
      "dimensions": [],
      "non_echo": false
    }
  ],

  "layer_info": {
    "hash_strategy": "did",
    "create_layer_auto": false,
    "purpose": 6,
    "layer_id": <layer_id>,
    "layer_name": "<layer_name>",
    "layer_status": 1,
    "layer_type": "did",
    "product_id": <product_id>,
    "layer_reusable": false,
    "layer_priority": 50,
    "layer_hash_name": "<layer_hash>",
    "domain": null
  }
}
PAYLOAD

# 2) 发起 create
bytedcli --site i18n-tt --json libra experiment create --app-id 22 --request-file /tmp/new_exp.json
```

字段分四组：

- **业务字段**：`app_id` / `product_id` (顶层，层治理校验要用；漏了报 `[500] 获取层治理配置失败`，CLI 会自动补齐) / `name` / `description` / `duration` (秒) / `effected_regions` / `owners` / `version_resource` (流量占比) / `versions` (对照 + 实验组配置，`config` 是 JSON 字符串而非对象)
  - `effected_regions` 取值要跟实验目标 region 对得上：**ROW 实验**写 `["SG", "VA"]`（两个机房一起开）；**EU 实验**写 `["EU_TTP"]`；**US 实验**写 `["US_TTP"]`。写错 region 不会被 server 当面拒绝，但 release 后实际并不会在期望机房生效。
- **平台 / 治理字段**：`manage_type` (一般 `strategy`) / `flight_mode` / `experiment_mode` / `metric_scene` / `strategy_category_ids` (取 app 内合法 id)
- **`layer_info`**：复用现有共享层时，从同 layer 一个老实验的 `experiment get` 拿 `layer_id` / `layer_name` / `layer_hash_name` / `product_id` 等照搬，并保持 `create_layer_auto: false`。新建独立层用 `create_layer_auto: true` + 让 `layer_id: -1`，但要注意此时其他治理字段（`purpose` / `hash_strategy` 等）会有强校验
- **`metrics`**：必须包含历史上下文和源实验 / 模板里已确认关注的指标组并按 `metric_group_id` 去重。创建前显式带齐，不能依赖创建后再补。

其他规则（两步握手、`versions[].config` 是 JSON 字符串、`--no-verify` / `--skip-conflicts` 含义等）与方式 1 共享，见上文。

### 判断实验是否显著

这是最常见的场景：用户想知道某个实验的指标是否有统计显著的提升。

```bash
# 0. 创建实验（通过 JSON 文件传入完整请求体；CLI 自动做 preflight + create 两步）
bytedcli --json libra experiment create --app-id -1 --request-file ./experiment.json

# 0.1 基于单实验模板创建；override body 会覆盖模板默认值
bytedcli --json libra experiment create --app-id 1193 --template-id 3139 --request-file ./override.json
# 创建成功后，从返回的 JSON 中提取实验 ID，拼接实验链接给用户：
# https://data.bytedance.net/libra/flight/<experiment_id>/report/main

# 1. 查看实验基本信息
bytedcli libra experiment get --flight-id <flight_id>

# 2. 列出可用指标组（找到目标指标组 ID）
bytedcli libra experiment report --flight-id <flight_id>

# 3. 查看指标组报告（含 P-Value 和显著性标记）
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id>

# 4. 如需看趋势变化
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --trend

# 5. 如需按页面报告口径复现（例如普通/CUPED 口径），传抓包里的 data_caliber
bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --data-caliber 1

# 6. 需要一次拉多个指标组/维度时，用 report-batch 在单进程内并发跑一批查询
bytedcli --json libra experiment report-batch --input-file ./queries.jsonl --concurrency 10
```

报告中 `Sig` 列按学术惯例分级：`*` p<0.05 / `**` p<0.01 / `***` p<0.001。

### 跨机房实验报告（data_region）

Libra 后端按机房路由查询；`lean-data-v2` 接口必须传正确的 `data_region`，否则会"静默"返回全空数据（所有 metric 的 `value=null`，且 `end_date` 被 clamp 到旧日期）。CLI 会自动从实验的 `truly_effected_regions` 推导 `data_region`，大多数时候无需手动指定；只有当自动推导结果与实际不符时才用 `--data-region` 覆盖。

```bash
# 自动推导（EU_TTP flight 会自动用 eu_ttp，无需额外参数）
bytedcli --site i18n-tt libra experiment report --flight-id <flight_id> --metric-group <metric_group_id>

# 手动指定（强制某个 region）
bytedcli --site i18n-tt libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --data-region eu_ttp
```

支持的 `data_region` 取值与实验 `truly_effected_regions` 的映射：

| `truly_effected_regions` | `data_region` | 说明                           |
| ------------------------ | ------------- | ------------------------------ |
| `SG`                     | `sg`          | Singapore (TTP-SG)             |
| `VA`                     | `va`          | Virginia / US（老 US 机房）    |
| `US_TTP`                 | `us_ttp`      | US-TTP（对应 `tx` 别名也接受） |
| `EU_TTP`                 | `eu_ttp`      | EU-TTP（GCP 欧洲机房）         |
| `MY`                     | `my`          | My-Compliance                  |
| 多区域 / 无明确区域      | `other`       | 默认值                         |

**典型排查**：如果 report 全 `-`，先 `bytedcli libra experiment get --flight-id <id>` 看 `truly_effected_regions`，再确认 `--data-region` 的取值匹配。手动传 `--data-region other` 可以快速复现老行为（作为对照）。

### 读取广告报告（ad-report）

`libra ad-report get` 用于读取广告看板 / ROI 看板数据，支持完整页面 URL，也支持结构化参数。

```bash
# 1) 直接传完整广告报告 URL：自动解析 flight_id / report_id / 已知 query 参数 / 动态过滤条件
bytedcli libra ad-report get \
  --url 'https://example.bytedance.net/libra/flight/<flight_id>/report/ad/<report_id>?start_date=<start_date>&end_date=<end_date>&<dimension_name>=<value_id_1>@<value_id_2>&<known_query_key>=<known_query_value>'

# 2) 只看报告头和有哪些表，不拉全量明细
bytedcli libra ad-report get --url 'https://example.bytedance.net/libra/flight/<flight_id>/report/ad/<report_id>?<query_params>' --summary-only

# 3) 不改 URL，直接在 CLI 上追加/覆盖动态过滤
bytedcli libra ad-report get \
  --flight-id <flight_id> \
  --report-id <report_id> \
  --dimension <dimension_name>=<value_id_1>@<value_id_2> \
  --dimension <another_dimension_name>=<value_id>

# 4) 只拉某个表下的某个指标
bytedcli libra ad-report get \
  --flight-id <flight_id> \
  --report-id <report_id> \
  --table-name '<table_name>' \
  --metric-name '<metric_name>'

# 5) 指定 base_vid，让文本模式里的 Base Value 对齐到目标版本
bytedcli libra ad-report get \
  --flight-id <flight_id> \
  --report-id <report_id> \
  --base-vid <base_vid>

# 6) 直接按原始 ad-report group / metric ID 拉数据，并传字符串 filters
bytedcli libra ad-report get \
  --flight-id <flight_id> \
  --report-id <report_id> \
  --group-id <group_id> \
  --metric-id <metric_id> \
  --filter psm=<psm_1>@<psm_2> \
  --filter dc=<dc_1>@<dc_2> \
  --start-date <start_date> \
  --end-date <end_date>
```

使用约定：

- 支持两种入口：`--url <url>`，或 `--flight-id + --report-id`。
- `--url` 识别 `/libra/flight/<flight_id>/report/ad/<report_id>` 这类页面链接；显式 CLI 参数会覆盖 URL 里解析出的同名字段。
- **默认行为是拉该 report 下所有 metric group 的全量明细**；如果只想快速确认报告标题和有哪些表，使用 `--summary-only`。
- `--summary-only` 不能与 `--table-name` / `--metric-name` 或 `--group-id` / `--metric-id` 同时使用；摘要模式与单表/单指标模式二选一。
- URL query 中**未知的 key** 会自动当成动态过滤维度，映射为 `dimensions.<key> = number[]`；值必须是数字 ID，多个值用 `@` 连接，例如 `campaign_bucket=90@91@92`。
- `--dimension <name=value[@value...]>` 可重复传入，并与 URL query 里的动态过滤合并；同名时以 CLI 显式参数为准。
- `--filter <name=value[@value...]>` 直传 ad-report group-data API 的 `filters` 字段，支持字符串值，适合 `psm=example.psm`、`dc=useast5@useast8` 这类过滤。
- `--table-name` + `--metric-name` 用于只拉单个表 / 单个指标；`--group-id` + `--metric-id` 用于按原始 ID 直接拉指定 group / metric；不传时按默认行为返回全部明细。
- `--base-vid` 只影响**文本模式**里 `Base Value` 选取哪一行：优先匹配指定 vid，否则回退到对照组，再回退到第一行；`--json` 输出仍保留原始 rows。
- 常见已知 query 参数可直接用结构化 flag 覆盖：`--start-date`、`--end-date`、`--balance-unequal-traffic`、`--data-group-style`、`--multi-compare`、`--versions-merge`。

### 查看指标组信息

```bash
# 先从实验报告里拿到 metric group ID
bytedcli libra experiment report --flight-id <flight_id>

# 再查看指标组基础信息
bytedcli libra metric-group get --id <metric_group_id>
```

### 查看指标组模版

```bash
# 查看指标组模版（默认 normal 类型）
bytedcli libra metric-group template get --id <template_id> --app-id <app_id>

# 查看 conclusion 类型的指标组模版
bytedcli libra metric-group template get --id <template_id> --app-id <app_id> --type conclusion

# 直接传模版页面 URL
bytedcli libra metric-group template get --url <template_url>
```

### 查看实时指标

查看实验的实时监控数据（默认最近 1 小时）。

```bash
# 1. 列出实验可用的实时仪表盘
bytedcli libra experiment realtime --flight-id <flight_id>

# 2. 查看仪表盘详情（获取指标组 ID）
bytedcli libra experiment realtime --dashboard-info <dashboard_id>

# 3. 查看特定指标组的实时数据
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id>

# 指定时间范围
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> \
  --start "2026-04-08 10:00:00" --end "2026-04-08 11:00:00"

# 分钟级数据
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> --period-type m

# 查看指标含义（显示指标描述）
bytedcli libra experiment realtime --flight-id <flight_id> --metric-group <metric_group_id> --describe

# 列出所有可用的实时仪表盘
bytedcli libra experiment realtime --list-dashboards

# 查看仪表盘详情及 SQL 定义（帮助理解指标计算逻辑）
bytedcli libra experiment realtime --dashboard-info <dashboard_id> --show-sql
```

### 搜索并查看实验

```bash
# 列出可用 App
bytedcli libra app list

# 按名称搜索实验；app-id 默认 -1（全部应用）
bytedcli libra experiment search --app-id <app_id> --keyword "<experiment_name>" --search-type name

# 按完整参数路径搜索（跨全部应用）
bytedcli libra experiment search --app-id -1 --key-path "<config_path>"

# 多个参数路径；Libra page API 按逗号序列化数组
bytedcli libra experiment search --app-id -1 \
  --key-path "<config_path_1>,<config_path_2>"

# 按负责人 / 创建者 / 状态等条件组合筛选
bytedcli libra experiment list --app-id <app_id> \
  --user "<owner>" --creator "<creator>" --status running,paused

# 搜索实验组配置中的关键词（不要求完整路径）
bytedcli libra experiment search --app-id -1 \
  --keyword "<config_keyword>" --search-type config
```

`experiment list` 与 `experiment search` 都调用 Libra 实验列表页面的同一个原子接口：

```text
GET /datatester/experiment/api/v3/app/{app_id}/experiment
```

其中 `app_id` 位于 URL path，默认 `-1`；应用 / 功能模块 / 实验层分别映射为 `--app-id` / `--product-id` / `--layer-id`。`experiment search` 必须提供 `--key-path` 或 `--keyword`，其他页面筛选项用于缩窄候选；`--key-path` 会发送 `search_type=config_path`，不要把它与 `--keyword` 同时使用。

页面标准筛选项与 CLI 的映射：

| 页面条件                 | CLI 参数                                   | 请求参数                                        |
| ------------------------ | ------------------------------------------ | ----------------------------------------------- |
| 应用 / 功能模块 / 实验层 | `--app-id` / `--product-id` / `--layer-id` | path `app_id` + query `product_id` / `layer_id` |
| 负责人 / 群组 / 创建者   | `--user` / `--user-group-id` / `--creator` | `user` / `user_group_id` / `creator`            |
| 搜索类型 + 关键词        | `--search-type` + `--keyword`              | `search_type` + `search_keyword`                |
| 参数路径                 | `--key-path`                               | `search_type=config_path` + `search_keyword`    |
| 实验类型                 | `--manage-type`                            | `manage_type`                                   |
| 实验状态                 | `--status`                                 | `status`                                        |
| 运行 / 开始 / 结束时间   | `--time-type` + `--start` + `--end`        | `time_type` + `start_time` + `end_time`         |
| 业务线                   | `--strategy-category-ids`                  | `strategy_category_ids`                         |
| 操作系统                 | `--device-platform`                        | `device_platform`                               |
| APP 版本                 | `--app-version`                            | `app_version`                                   |
| 我负责的 / 我收藏的      | `--owner-type my,favourite`                | `owner_type`                                    |

时间筛选遵循以下约束：

- `--time-type` 只能取 `running` / `start` / `end`。只要传了 `--start` 或 `--end` 就必须同时传 `--time-type`；传了 `--time-type` 则 `--start` 和 `--end` 必须成对提供。
- `--start` / `--end` 支持 ISO 8601（推荐显式携带 UTC offset）、Unix 秒、Unix 毫秒、`YYYY-MM-DD` 和 `1h ago` / `30m ago` 这类相对时间。常规 Unix 时间戳建议使用 10 位秒或 13 位毫秒形式。
- CLI 会把输入统一转换为 Unix 秒后发送到 page API 的 `start_time` / `end_time`，毫秒部分向下取整，因此查询精度为秒。
- `YYYY-MM-DD` 按运行机器的本地时区解释：`--start` 取当天 `00:00:00`，`--end` 取当天 `23:59:59`；非法日历日期会直接报错。排查 BJT 异动时不要依赖机器时区，显式使用 `+08:00`。

```bash
# 精确查询 BJT 2026-07-11 21:20:00 至 21:20:59 期间处于运行周期的实验
bytedcli --site i18n-tt --json libra experiment search \
  --app-id -1 \
  --key-path "<config_path>" \
  --time-type running \
  --start '2026-07-11T21:20:00+08:00' \
  --end '2026-07-11T21:20:59+08:00'
```

搜索类型包括 `fuzzy`、`id`、`experiment_ids`、`name`、`creator`、`config`、`tag`、`version_resource`、`debug_user`、`feature_type`、`scene`、`effect_region`、`config_path`。其中 `config` / `tag` / `effect_region` / `experiment_ids` / `config_path` 支持逗号分隔多个关键词。APP 版本格式为 `field,operator,version`，例如 `--app-version 'version_code,>=,12345'`。

公开状态值使用语义名称：`ended`、`running`、`pending-schedule`、`debugging`、`paused`、`pending-schedule-end`、`pending-approval`、`rejected`、`draft`、`frozen`、`released`、`deleted`。CLI 映射为 Libra 后端数字枚举，多状态仍在一次请求中发送，不做客户端合并。

旧的 global-parameter API 仍保留为独立命令，只在明确需要 `exact_match` / global parameter 对象语义时使用：

```bash
bytedcli libra global-param search --key-path "<config_path>" --exact-match
```

它调用 `POST /datatester/global_param/api/v3/global_param/list/`，不是页面实验搜索接口；不要用它代替 `experiment search --key-path`。

### 按异动时间点排查相关实验变更

输入通常是一个异动时间点和一组可配置的候选条件。候选条件可以很粗（配置关键词、owner、creator、状态、业务线），也可以很精（完整参数路径、app / module / layer）。CLI 不提供聚合命令；agent 在 Skill 层组合原子命令。

1. 先按已知条件找候选实验。精确到配置路径时优先 `--key-path`；只有关键词时用 `--keyword ... --search-type config`；也可以叠加 owner / creator / app / product / layer / status / time 条件。若 app 未知，从 `--app-id -1` 开始。
2. 搜索结果中的每个实验都保留实际 `app_id`。对候选逐个调用 `experiment audit list`，先查审计记录，再决定是否需要其他详情。并发应有界（建议 3–5），单次调用设置合理超时；超时或鉴权失败不等于“没有变更”。
3. 在原始 history 中围绕异动时间窗口检查准确时间点、后端 action 和变更内容。不要维护固定 action 分类表，也不要把某个 action 名机械等价成暂停 / 修改 / 关闭 / 放缩量 / 灰度；以返回字段和语义逐条判断。
4. 如果审计记录暗示放缩量、平滑生效或需要补充流量生效上下文，再调用 `traffic-effect list`。它是补充证据，不替代审计记录。
5. 汇总时明确区分：命中时间窗口的事实、仅时间接近的候选、查询失败或证据不足的实验。

```bash
# 1) 精筛候选；BJT 时间用显式 +08:00，避免运行机器时区歧义
bytedcli --site i18n-tt --json libra experiment search \
  --app-id -1 \
  --key-path "<config_path>" \
  --time-type running \
  --start "<start_time_with_utc_offset>" \
  --end "<end_time_with_utc_offset>"

# 2) 对每个候选使用其真实 app_id 查询完整审计历史
bytedcli --site i18n-tt --json libra experiment audit list \
  --app-id <actual_app_id> --flight-id <flight_id>

# 3) 仅在需要流量生效记录时补查
bytedcli --site i18n-tt --json libra experiment traffic-effect list \
  --app-id <actual_app_id> --flight-id <flight_id>
```

`experiment audit list` 与 `traffic-effect list` 都原样转发 Libra 返回值。审计记录中的 action / change detail 由后端定义；流量生效记录在有数据时可包含 `last_gradual_traffic` / `traffic_record`。不要依赖未证实的 `/experiment/{flight_id}/traffic` 页面接口：实测它在多个实验上只返回无信息量的 `traffic_decrease`，因此 bytedcli 不集成该接口。`experiment traffic` 读取的是实验详情里的当前流量与版本权重，不是流量变更历史。

### 查看配置发布里的 feature flag

```bash
# 按 repo 查看配置发布列表（默认走 scc_server）
bytedcli libra feature-flag list --repo-id 11681182

# client 模式下按 app + key 搜索
bytedcli libra feature-flag list --app-id 22 --feature-name clear_upload_cache_after_create_aweme

# 按 feature key 精确搜索（对齐 Libra 网页 feature_key=）
bytedcli --json libra feature-flag list --app-id -1 --side-type client --feature-key demo_feature_key

# 按参数路径前缀搜索相关子 key，并返回全部端配置
bytedcli --json libra feature-flag list --app-id -1 --side-type scc_server --prefix demo_config_prefix --all-config

# 按完整参数路径搜索（Libra 页面“参数路径”模式），未传 --prefix 时会自动取最后一段作为 prefix
bytedcli --json libra feature-flag list --repo-id 100001 --side-type scc_server --app-id 22 --config-path demo_namespace.demo_config_prefix --all-config

# 指定页码和每页条数
bytedcli libra feature-flag list --repo-id 11681182 --page 3 --page-size 10

# 显式指定 side type
bytedcli libra feature-flag list --repo-id 11681182 --side-type scc_server
bytedcli libra feature-flag list --app-id 22 --side-type client

# 返回某个 feature flag 在所有端（app）下的配置，而非只看第一个端
bytedcli --json libra feature-flag list --repo-id 11681182 --feature-name demo_feature_key --all-config

# 读取某个 feature flag 的 detail（默认选最新全量版本）
bytedcli libra feature-flag get --app-id 22 --feature-id 123456

# 显式指定版本号或版本记录 ID
bytedcli libra feature-flag get --app-id 22 --feature-id 123456 --version 2
bytedcli libra feature-flag get --app-id 22 --feature-id 123456 --version 200001

# 查看全部历史版本
bytedcli libra feature-flag versions --feature-id 123456 --app-id 22

# 查看关联实验
bytedcli libra feature-flag related-experiments --feature-id 123456 --app-id 22 --version 2
```

核对某个实验关联配置的全量发布状态及当前已发布值时，优先用 `feature-flag list` 按实验过滤，并查看 `--json` 输出里的 `feature_flags[].released_value`：

```bash
bytedcli --json libra feature-flag list --repo-id 11681182 --side-type scc_server --related-experiment-id 4980416
```

按客户端 feature key 精确搜索时，使用 `feature-flag list --feature-key <key>`，该参数等价于 Libra 网页列表的 `feature_key=` 查询参数。按配置参数路径前缀搜索相关子 key 时，使用 `feature-flag list --prefix <path>`，该参数等价于 Libra 网页列表的 `prefix=` 查询参数。按页面“参数路径”模式精确搜索完整路径时，使用 `--config-path <path>`，CLI 会透传 `config_path=`；如果没有显式传 `--prefix`，CLI 会自动取完整路径最后一段补 `prefix=`，对齐页面请求。需要查看每个端（app）的全量发布情况时，同时加 `--all-config --json`，查看 `feature_flags[].configs[]` 里的 `released_value` / `release_status`。

`feature-flag list` 同时支持 repo/server 模式与 client/app 模式：

- 传 `--repo-id` 且未显式指定 `--side-type` 时，默认按 `scc_server` 查询
- 使用 `--app-id` 时，默认按 `client` 查询
- `--app-id -1` 表示未指定 / all apps

默认情况下，`feature-flag list` 的每条 `feature_flags[]` 只展示该配置**第一个端（app）**的发布信息（`app_id` / `released_value` 等顶层字段）。当同一个配置在多个端都有发布（例如抖音短视频、抖音极速版、抖音直播伴侣等）时，加 `--all-config` 可返回全部端：`--json` 模式下每条记录额外带 `feature_flags[].configs[]`（每端一项，含各自的 `app_id` / `app_name` / `released_value` / `release_status` 等）；文本模式下同一 feature 会按端展开成多行。顶层字段保持不变，方便已有调用方无缝兼容。

`experiment get` 的 `versions[].config` 只表示实验版本与配置值的映射；当前已发布的条件表达式和值，以 `feature-flag list` 返回的 `released_value` 为准。

`feature-flag get` 走 Libra 页面侧 detail API；不传 `--version` 时，CLI 会先拉版本列表，并默认选**最新全量版本**。如果存在高于最新全量版本的非全量版本，文本模式会额外提示。`--json` 返回 `selected_version`、`selected_config`、`available_versions`、`latest_version`、`latest_full_release_version` 等结构化字段。

### 管理实验层

实验层命令走 Libra 页面 API，复用 Titan Passport 登录态；不需要 DataOpen app credential。

```bash
# 创建实验层
bytedcli libra layer create --app-id 123 --product-id 456 --name demo-layer --owner demo.user

# 查询实验层列表
bytedcli libra layer list --app-id 123 --product-id 456 --search demo --page-size 50

# 查询实验层详情
bytedcli libra layer get --layer-id <layer_id>
```

### 管理测试用户

```bash
# 查看测试用户
bytedcli libra test-user list --flight-id <flight_id>

# 添加测试用户
bytedcli libra test-user add --flight-id <flight_id> --uid <uid>

# 删除测试用户
bytedcli libra test-user delete --flight-id <flight_id> --uid <uid>

# 指定版本（多实验组时需要）
bytedcli libra test-user add --flight-id <flight_id> --uid <uid> --version <vid>
```

### 诊断测试用户是否命中实验

```bash
# 默认查询最近 72 小时
bytedcli --site i18n-tt libra experiment hit get \
  --flight-id <flight_id> \
  --user-id <user_id>

# 显式指定时间窗；支持 Unix 秒、ISO 时间或相对时间
bytedcli --site i18n-tt --json libra experiment hit get \
  --flight-id <flight_id> \
  --user-id <user_id> \
  --start '72h ago' \
  --end <iso_time> \
  --timeout-ms 180000
```

命令会先校验用户是否属于可诊断的测试用户；未通过时不会调用命中诊断接口，并提示：`仅支持预登记的测试用户，实验配置的测试用户；添加测试用户后，预计 5 分钟后可查到结果，请耐心等待`。第二阶段诊断默认超时为 600 秒；可用 `--timeout-ms` 显式覆盖，最大 1200000 毫秒（1200 秒）。该选项不影响前置 whitelist 请求。

### 管理测试白名单分群

```bash
# 查看测试白名单分群
bytedcli libra test-whitelist list --flight-id <flight_id>

# 添加测试白名单分群到实验组
bytedcli libra test-whitelist add --flight-id <flight_id> --group-id <group_id>

# 删除测试白名单分群
bytedcli libra test-whitelist delete --flight-id <flight_id> --group-id <group_id>

# 指定版本（多实验组时需要）
bytedcli libra test-whitelist add --flight-id <flight_id> --group-id <group_id> --version <vid>
```

### 批准 / 驳回实验 peer review

```bash
# 推荐：直接传 peer-review 页面 URL，自动解析 flight/review/app ID
bytedcli libra experiment approve --url https://libra-<region>.tiktok-row.net/libra/peer-review/<flight_id>/view/<review_id>

# 驳回（默认是批准）
bytedcli libra experiment approve --url <peer_review_url> --reject

# 手动传 review 和 app ID（无 URL 时）
bytedcli libra experiment approve --review-id <review_id> --app-id <app_id>
```

### 驱动实验完整生命周期（submit-review → release / pause / resume / close）

`approve` 是 reviewer 端；下面这组是 submitter 端 + 状态机迁移。整套都走 page API，操作以调用者本人身份进入实验审计历史。典型端到端流水线：

```bash
# 0) 已经 create 好的 draft 实验，flight_id=12345678
#    （create 部分见上文"创建实验"章节）

# 1) 发起 review；CLI 自动继承 check-review 命中规则的 reviewer
#    --reviewers 仅追加邀请人（规则未配置 reviewer 时才必填）
bytedcli --site i18n-tt libra experiment submit-review \
  --flight-id 12345678 \
  --reviewers <your.username>,alice.bob \
  --description "新策略权重调优" \
  --auto-launch-mode auto

# 2) （reviewer 端，可以是另外一个人，用 approve；自审同人可以接着用 self review）
bytedcli --site i18n-tt libra experiment approve --review-id <review_id> --flight-id 12345678

# 3) 等待自动化检查全过；过线后服务端会自动 fire release，实验转 running
#    人工监控用 review-status（看 §"诊断 review 自动化检查"）；不要急着调 release

# 4) 想随时暂停采集
bytedcli --site i18n-tt libra experiment pause --flight-id 12345678

# 5) 恢复（pause 会让 review 失效，必须重发一次 review + approve；用 auto-launch-mode auto 一步完成）
bytedcli --site i18n-tt libra experiment submit-review \
  --flight-id 12345678 --reviewers <your.username> --description "resume after pause" --auto-launch-mode auto

# 6) 实验结论已确认，不可逆关闭
bytedcli --site i18n-tt libra experiment close \
  --flight-id 12345678 \
  --close-reason "实验结论已确认，关闭采集"
```

**`--auto-launch-mode` 三档**：

| 值       | 行为                                                                              |
| -------- | --------------------------------------------------------------------------------- |
| `manual` | review 通过后实验仍停在 paused，需要手动 `experiment release`                     |
| `auto`   | review 通过 _且每个 blocking automated check pass/skip_ 后服务端自动 fire release |
| `timer`  | 定时启动；同时传 `--extra-body '{"scheduled_start_time":<unix_ts>}'`              |

`submit-review` 会先执行 Libra UI 同源的 `check-review`，并原样保留规则 reviewer 的 `from_workflow_id_list`、`pass_condition` 等 workflow 元数据。不要按 region 硬编码审批规则，也不要用独立的 `ttp_approve_info` 替代 Review 规则。

**关键易错点**：`pause` 之后想 `resume`，**必须重新发一次 review 并通过**——`/continue` 端点要求 "continue/start" operate type 对应的 review 是 fresh 的。直接调 `experiment resume` 会报 `[400] must initiate an experiment review and pass it`。推荐用 `submit-review --auto-launch-mode auto` 一步完成 resume。

**CLI 行为约定**：

- CLI 不在调用 server 前按客户端规则拦截用户的显式 intent，只在 server 拒绝后把原始错误翻译成可操作的下一步提示（典型例子：`resume` 的 `LIBRA_REVIEW_REQUIRED`）。后果：
  - `close` 在 draft / paused / running 上**都生效**——发现 draft 配置错了，直接 `close` 不必走完"review → launch → close"三步。
  - `pause` / `resume` 在 draft / closed 上一般被 server 拒（`[400] not started / not paused`）；review 推进过程中 server 内部子状态会变化，偶尔同一个 draft flight 也会被 accept，CLI 不预判这些 edge case。任何 lifecycle 调用之后都用 `experiment get` 看真实 status。
  - 任何 destructive 操作的 dry-run / 二次确认由调用方负责；CLI 只保证错误信息可读。
- **lifecycle 接口的 `response.result.status` 是调用前 snapshot**：`release` / `pause` / `close` 的返回里 `result.status` 是调用 _前_ 的值，不是调用后的权威 status；CLI 仅以此回显 "Pre-call status"，并提示用户再调一次 `experiment get` 拿权威 post-call status（server 是 eventually consistent，刚执行完几秒内 get 可能仍看到旧值）。

### 诊断 review 自动化检查节点 + 重跑失败的 TikDiff 子任务

`review-status` 按 check 节点维度展示 review 卡在哪个环节；`tikdiff-status` 进一步展开 TikDiff Test 节点内部按 case → task 维度的明细；`tikdiff-rerun` 用于重跑失败的 TikDiff 子任务。

**前提：不是所有 review 都会跑 TikDiff**。TikDiff Test 是 conditional check，按实验配置触发，部分实验的 review 里**不会出现** `TikDiff Test` 节点；这种情况下 `tikdiff-status` / `tikdiff-rerun` 用不上。先用 `review-status` 看 `checks[]` 里有没有 `nodeName="TikDiff Test"`，没有就跳过下面这套子流程。

**另一种"节点在但不跑 case"的情况**：`checks[]` 里出现 `TikDiff Test` 节点 ≠ server 会真的跑 TikDiff cases。零影响实验（极小 traffic / 极短 duration / 空 config 等）会被 server fast-path 跳过重 checks 自动 release——表现为 `submit-review` 后 1–2 分钟就直接进 `status=1`（running），`TikDiff Test` 节点停留在 `status=0`（not_started）或 `4`（skipped），`tikdiff-status` 永远返回 `tasks: []`。**以 `tikdiff-status` 返回的 task 数为准**，不要单看 review-status 的节点列表预判。

```bash
# 1) 看 review 整体状态：peer approval + 每个 blocking automated check 的 pass/fail/running
bytedcli --site i18n-tt libra experiment review-status \
  --review-id 87654321 --flight-id 12345678

# 2) 用脚本筛出"仍 blocking 且未通过"的 check 节点（自动化场景）
bytedcli --json --site i18n-tt libra experiment review-status \
  --review-id 87654321 --flight-id 12345678 | jq '.data.checks[] | select(.isBlock and .status != 2)'

# 3) TikDiff Test 这个节点显示 failed 时，进去看具体哪几个 case / task 红了
bytedcli --site i18n-tt libra experiment tikdiff-status \
  --flight-id 12345678 --review-id 87654321

# 4) 一键重跑全部失败的 TikDiff 子任务
bytedcli --site i18n-tt libra experiment tikdiff-rerun \
  --flight-id 12345678 --review-id 87654321 --all-failed

# 5) 等几分钟再看一次 review-status / tikdiff-status，确认绿了
bytedcli --site i18n-tt libra experiment review-status \
  --review-id 87654321 --flight-id 12345678
```

**`libra experiment tikdiff-status` / `tikdiff-rerun` 与 `holmes tikdiff create|get` 的分工**：

| 命令                                                  | 操作粒度                           | 用途                                          |
| ----------------------------------------------------- | ---------------------------------- | --------------------------------------------- |
| `holmes tikdiff create / get`（holmes skill）         | 单个独立 TikDiff task              | 自己起一个 task、按 task_id 查报告            |
| `libra experiment tikdiff-status / rerun`（本 skill） | 某次 Libra review 关联的整组子任务 | Libra 评审流水线里诊断 TikDiff Test、批量重跑 |

两者底层都是 Holmes，但暴露的是不同 endpoint（`holmes tikdiff get` 走通用 task API；本 skill 的 tikdiff 命令走 Holmes 给 Libra iframe 暴露的 `/api/v1/tikdiff/libra/*` bridge），鉴权方式也不同（前者要 BDSSO，后者只要 Titan Passport cookie）。两者互补，不可替代。

## Command overview

| Command                                                                                                                      | Description                                                                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `libra config-release create ... [--yes]`                                                                                    | 从 pending diff 预览或创建配置发布 ticket                                                                                                                                                      |
| `libra config-release get --ticket <ticket>`                                                                                 | 获取配置发布详情                                                                                                                                                                               |
| `libra config-release whitelist execute --ticket <ticket> --white-list <ids> [--yes]`                                        | 预览或执行白名单测试                                                                                                                                                                           |
| `libra config-release review create --ticket <ticket> --reviewer <name> [--yes]`                                             | 预览或邀请 review                                                                                                                                                                              |
| `libra config-release review status --ticket <ticket> [--wait]`                                                              | 单次读取或轮询 review 状态                                                                                                                                                                     |
| `libra config-release deploy --ticket <ticket> --percentage <pct> [--yes]`                                                   | 预览或增加配置放量比例                                                                                                                                                                         |
| `libra config-release rollback execute --ticket <ticket> --reason <text> [--yes]`                                            | 预览或回滚配置发布                                                                                                                                                                             |
| `libra experiment create --app-id <id> --request-file <path> [--template-id <id>] [--skip-conflicts] [--no-verify]`          | 创建实验（默认要求显式关注指标组；支持单实验模板默认值 + override，默认走 preflight + create 两步；仅在用户明确要求时用 `--allow-empty-metrics`）                                               |
| `libra experiment child create --parent-flight-id <id> --parent-version-id <id> --layer-id <id> ...`                         | 创建依赖实验，继承并校验父实验元数据，创建后读回校验父子关系                                                                                                                                   |
| `libra experiment get --flight-id <id>`                                                                                      | 实验详情（版本、流量、owner）                                                                                                                                                                  |
| `libra experiment hit get --flight-id <id> --user-id <id> [--start <time>] [--end <time>] [--psm <psm>] [--timeout-ms <ms>]` | 先校验测试用户资格，再以默认 600 秒超时诊断该用户是否命中实验                                                                                                                                  |
| `libra experiment traffic --flight-id <id>`                                                                                  | 流量分配和版本权重                                                                                                                                                                             |
| `libra experiment update --flight-id <id> --traffic <pct> [--gradual-duration <minutes>] [--yes]`                            | 原地更新已存在实验的流量（仅扩量，目标流量必须严格大于当前流量），`--traffic` 接受 `0.5` 或 `50%`；带 `--gradual-duration`（分钟，0 < x ≤ 1440）即平滑放量，省略则立即生效（读-改-写全量对象） |
| `libra experiment audit list --app-id <id> --flight-id <id>`                                                                 | 原样返回实验审计历史（后端 action + 变更内容）                                                                                                                                                 |
| `libra experiment traffic-effect list --app-id <id> --flight-id <id>`                                                        | 原样返回流量生效记录（含后端提供的平滑生效信息）                                                                                                                                               |
| `libra experiment report --flight-id <id>`                                                                                   | 实验报告（指标、P-Value、趋势）；`--baseline <vid>` 切 cross-treatment                                                                                                                         |
| `libra experiment report-batch --input-file <path.jsonl>`                                                                    | 单进程内并发批量跑 report 查询（JSONL 输入镜像 `report` option + 唯一 `request_id`；`--concurrency` / `--format json\|ndjson`）                                                                |
| `libra ad-report get --url <url> [--dimension <k=v[@v...]>] [--summary-only]`                                                | 广告报告 / ROI 看板；默认拉全量明细，支持完整 URL 和动态过滤                                                                                                                                   |
| `libra experiment conclusion-report --flight-id <id>`                                                                        | 结论报告聚合（一次拉所有指标 × 所有版本，含 LT 兑换；SLA/分类/指标组筛选）                                                                                                                     |
| `libra experiment realtime --flight-id <id>`                                                                                 | 实时指标（最近 1 小时监控数据）                                                                                                                                                                |
| `libra metric-group get --id <id>`                                                                                           | 指标组基础信息（文本摘要；`--json` 返回完整 payload）                                                                                                                                          |
| `libra metric-group template get --id <id> --app-id <id>`                                                                    | 指标组模版信息（支持 `--type normal\|conclusion`，默认 normal，403 自动 fallback）                                                                                                             |
| `libra experiment list [page filters]`                                                                                       | 对齐 Libra 页面条件列出 / 筛选实验                                                                                                                                                             |
| `libra experiment search --key-path <path> [page filters]`                                                                   | 使用 page API 的 `config_path` 模式搜索实验                                                                                                                                                    |
| `libra global-param search --key-path <path> [--exact-match]`                                                                | 独立 global-parameter API 搜索                                                                                                                                                                 |
| `libra feature-flag list --repo-id <id>`                                                                                     | 按 repo/server 模式列出配置发布 feature flags                                                                                                                                                  |
| `libra feature-flag list --app-id <id> [--feature-name <key>]`                                                               | 按 client/app 模式列出或搜索 feature flags                                                                                                                                                     |
| `libra feature-flag list ... --feature-key <key>`                                                                            | 按网页 `feature_key=` 精确搜索 feature flag                                                                                                                                                    |
| `libra feature-flag list ... --config-path <path>`                                                                           | 按网页 `config_path=` 完整参数路径搜索                                                                                                                                                         |
| `libra feature-flag list ... --prefix <path>`                                                                                | 按网页 `prefix=` 参数路径前缀搜索相关子 key                                                                                                                                                    |
| `libra feature-flag list ... --all-config`                                                                                   | 返回每个 feature flag 全部端配置（`feature_flags[].configs[]`），默认仅取第一个端                                                                                                              |
| `libra feature-flag get --app-id <id> --feature-id <id>`                                                                     | 读取某个 feature flag 的 rich detail，默认选最新全量版本                                                                                                                                       |
| `libra feature-flag versions --feature-id <id> --app-id <id>`                                                                | 查看 feature flag 历史版本                                                                                                                                                                     |
| `libra feature-flag related-experiments --feature-id <id> --app-id <id> [--version <n>]`                                     | 查看 feature flag 关联实验                                                                                                                                                                     |
| `libra layer create --app-id <id> --product-id <id> --name <name> --owner <user>`                                            | 创建实验层（页面 API / Titan Passport 鉴权）                                                                                                                                                   |
| `libra layer list --app-id <id> [--product-id <id>]`                                                                         | 查询实验层列表                                                                                                                                                                                 |
| `libra layer get --layer-id <id>`                                                                                            | 查询实验层信息                                                                                                                                                                                 |
| `libra experiment approve --url <url>`                                                                                       | 批准或驳回实验 peer review（reviewer 端）                                                                                                                                                      |
| `libra experiment submit-review --flight-id <id> --reviewers <list>`                                                         | 发起 peer review（submitter 端），可选 `--auto-launch-mode <manual\|auto\|timer>`                                                                                                              |
| `libra experiment release --flight-id <id>`                                                                                  | 草稿实验在 review 通过后发布（仅 `auto-launch-mode=manual` 需要）                                                                                                                              |
| `libra experiment pause --flight-id <id>`                                                                                    | 暂停 running 实验（可 resume）                                                                                                                                                                 |
| `libra experiment resume --flight-id <id>`                                                                                   | 恢复 paused 实验（前提：已有新 review 通过）                                                                                                                                                   |
| `libra experiment close --flight-id <id> --close-reason <text>`                                                              | 不可逆关闭实验                                                                                                                                                                                 |
| `libra experiment review-status --review-id <id> --flight-id <id>`                                                           | 看 peer review 批准状态 + 各 automated check 节点 pass/fail/running                                                                                                                            |
| `libra experiment tikdiff-status --flight-id <id> [--review-id <id>]`                                                        | 列出该 review 关联的 TikDiff 子任务清单（按 case 分组）                                                                                                                                        |
| `libra experiment tikdiff-rerun --flight-id <id> --all-failed`                                                               | 重跑失败的 TikDiff 子任务（或用 `--task-id <ids>` 指定）                                                                                                                                       |
| `libra app list`                                                                                                             | 列出所有可用 App                                                                                                                                                                               |
| `libra test-user list --flight-id <id>`                                                                                      | 查看测试用户                                                                                                                                                                                   |
| `libra test-user add --flight-id <id> --uid <uid>`                                                                           | 添加测试用户                                                                                                                                                                                   |
| `libra test-user delete --flight-id <id> --uid <uid>`                                                                        | 删除测试用户                                                                                                                                                                                   |
| `libra test-whitelist list --flight-id <id>`                                                                                 | 查看测试白名单分群                                                                                                                                                                             |
| `libra test-whitelist add --flight-id <id> --group-id <id>`                                                                  | 添加测试白名单分群                                                                                                                                                                             |
| `libra test-whitelist delete --flight-id <id> --group-id <id>`                                                               | 删除测试白名单分群                                                                                                                                                                             |

各命令的完整参数、选项和 `request-file` 格式说明见 `references/libra.md`。

## Key notes

- `--json` 是全局选项，放在子命令前：`bytedcli --json libra experiment get --flight-id <flight_id>`
- 用户提到 `ROW`、`i18n`、`US` 或 `TTP` 场景时，默认加 `--site i18n-tt`（例如：`bytedcli --site i18n-tt libra app list`）
- 任何需要 `--app-id` 的 Libra 命令，默认使用 `--app-id -1`，除非用户明确指定其他 app_id。
- `test-user` 更新的是 `versions[].user_list` 里的 `type=id` 条目；`test-whitelist` 更新的是 `versions[].user_list` 里的 `type=group` 条目
- `test-whitelist --group-id` 只接受数字分群 ID，不接受分群名称
- `layer` 命令使用 Libra 页面 API 鉴权，复用 Titan Passport；create/list 需要 `--app-id`，create 还需要 `--product-id`
- report 默认 `--merge-type total`（累计，含 P-Value），可选 `sum`（日均）或 `avg`
- report `--trend` 显示逐日趋势，`total` 为累计趋势，`avg` 为分段趋势
- report `--data-caliber <1|2|3>` 透传 Libra API 的 `data_caliber`，用于按页面抓包值对齐普通/CUPED 等报告口径；不传时保持 CLI 默认口径
- report `--force-show <0|1>` 透传 Libra API 的 `force_show`；默认 `0`（向后兼容），设为 `1` 可强制后端返回数据即使尚未完全就绪（与 Libra UI 行为一致）；当报告返回空数据但 UI 有数据时，尝试 `--force-show 1`
- report `--data-region` 控制机房路由，默认从实验 `truly_effected_regions` 自动推导（EU_TTP→`eu_ttp` / SG→`sg` / VA→`va` / US_TTP→`us_ttp` / MY→`my` / 其它→`other`）；传错值会静默返回全空数据，排查空报告时首先检查这个
- ad-report `get` 支持完整广告报告 URL；`--url` 里的未知 query key 会自动转成动态过滤维度，等价于重复传 `--dimension <name=value[@value...]>`
- ad-report `get` 默认拉完整 report 的全部明细；`--summary-only` 只返回报告头和 metric-group 名称，适合先探测页面结构
- ad-report `get --table-name <name> --metric-name <name>` 只拉指定表 / 指标；`--base-vid <vid>` 仅影响文本模式 `Base Value` 的选择，不改变原始 rows 数据
- `conclusion-report` 和 `report` 互补：`report` 单指标组深挖（趋势 / 维度 / 多机房），`conclusion-report` 一次拉整个结论报告 bundle（所有指标 × 所有版本，含 `--with-lt-exchange` 兑换 LT）；要看 `v_n` vs `v_m` 全统计（p-value / CI）回到 `report --baseline <vid_m>`
- `conclusion-report` / `--with-lt-exchange` / report `--baseline` cross-treatment 用法详情见 `references/libra.md`
- 需要分维度报表时，先执行 `libra experiment report --flight-id <id> --metric-group <metric_group_id> --list-dimensions`，再用 `--dimension <dimension_id>` 或 `--dimension <dimension_id:value[,value...]>` 拉取维度数据；值支持数字枚举 ID、枚举 value_key 字符串，以及自定义 value_key（等价页面"自定义值"输入，适合尚未进枚举清单的新维度值）
- 需要多维交叉时，重复传 `--dimension`；若只是分别查看两个维度，请各跑一条命令
- 多维交叉查询走异步 adhoc 计算，若超时就提示稍后重试同一条命令
- `metric-group get` 当前仅支持 `prod` 和 `i18n-tt`
- 访问 `i18n-tt` 时，请显式使用 `--site i18n-tt`
- 在生产网环境访问 i18n-tt 时，设置 `BYTEDCLI_NETWORK_PROFILE=prod`；Libra Page API / Gallery / Titan 会从默认 `.tiktok-row.net` 入口切到生产网可达的 `.bytedance.net` 入口。

## Troubleshooting

常见错误和处理方式见 `references/troubleshooting.md`。典型问题：

- **metric-group get 需要完整结构化结果**：加 `--json`，文本模式默认只展示摘要
- **报告数据为空**：先确认 `truly_effected_regions` 与自动推导的 `--data-region` 匹配；若匹配但仍空，尝试 `--force-show 1`（Libra UI 默认 `force_show=1`，CLI 默认 `0`）；若仍空，再考虑实验数据 T+1/T+2 延迟，或用 `libra experiment report --flight-id <id>` 检查可用指标组

## References

- `references/libra.md` — 各命令完整参数和选项
- `references/troubleshooting.md` — 常见错误和处理
- `references/invocation.md` — 通用调用方式和站点切换
