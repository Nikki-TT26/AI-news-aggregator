# dwm_trade_trae_user_order_entitlement_statistic

Trae 用户粒度商业化宽表（用户粒度，每日全量用户快照）。记录截止到当日全量用户 uid 的基本信息、会员状态、升降级变化、订阅/取消状态、订单统计等。适用场景：用户画像分析、会员升降级追踪、订阅转化分析、会员分布统计、取消订阅分析。

- **i18n 库表名**：`cloudide.dwm_trade_trae_user_order_entitlement_statistic`
- **分区字段**：`date`（yyyyMMdd）
- **TTL**：未设置（长期保留）
- **更新频率**：每日全量覆盖
- **数据粒度**：用户粒度，每个 user_id 每天一行
- **Dorado 任务（i18n）**：taskId `304712473`，项目 `sg_300004344`
- **上游表**：`cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df`（权益粒度宽表）
- **关联表**：`cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df`（同源，权益粒度 vs 用户粒度）

## 核心概念

### 数据粒度

- **主键**：`user_id`（每天每个用户一行）
- **全量快照**：每日全量覆盖，当日数据反映截止到当日 23:59 的状态快照
- **与权益粒度表的关系**：本表是 `dwm_trade_trae_entitlement_order_usage_statistic_df` 的聚合表，后者是权益粒度（每条权益一行），本表是用户粒度（每个用户一行）

### 会员体系

#### 会员类型 (member_type)

| 类型 | product_type | 等级 (member_level) | 说明 |
|------|---|---|---|
| free | 0 | 0 | 免费用户 |
| lite | 8 | 1 | Lite 轻量版 |
| pro | 1 | 2 | Pro 专业版 |
| pro_plus | 4 | 3 | Pro+ 增强版 |
| ultra | 6 | 4 | Ultra 旗舰版 |

> **特殊情况**：Pro Free Trial 虽然 `member_type='pro'`，但 **member_level=0**，与 free 相同。这是因为 Free Trial 用户可以购买任意套餐（包括 Lite），从业务角度不应视为"降级"。

#### 计费类型 (member_billing_type)

| 类型 | 等级 (billing_level) | 说明 |
|------|---|---|
| one_month | 0 | 单次购买（一个月） |
| free_trial | 0 | Pro Free Trial（首次购买 Pro 免费试用一个月） |
| monthly | 1 | 月付订阅 |
| yearly | 2 | 年付订阅 |

#### 产品 ID 与计费类型映射

| 会员类型 | monthly (月付) | yearly (年付) | one_month (单次) |
|---|---|---|---|
| Lite | 37 | 38 | 39 |
| Pro | 2 | 3 | 27 |
| Pro+ | 30 | 31 | 28 |
| Ultra | 32 | 33 | 29 |

> **Pro Free Trial**：`product_id=2` 且 `extra_info.is_trial='true'`（权益表）或 `extra_info.has_trial_first_period='true'`（订单表）时为 Pro Free Trial

### 升降级判断逻辑

- **升级**：基于当日与前一日的 `member_level` 或 `billing_level` 对比
- **会员类型升级路径**：`free/free_trial → lite → pro（不包含 free_trial） → pro_plus → ultra`
- **计费类型升级路径**：`one_month/free_trial → monthly → yearly`
- **复合升级**：会员类型 + 计费类型同时升级，`upgrade_type='both'`（如 `lite 月付 → pro 年付`）
- **Free Trial → Lite**：识别为 `is_member_upgrade=1`（因为 free_trial 的 member_level=0，lite 的 member_level=1）
- **Free Trial → Pro 月付/年付**：识别为 `is_billing_upgrade=1`（因为 free_trial 的 billing_level=0）

### 订单说明

订单为**订阅订单**，不等同支付流水单。例如连续包月 12 个月，只对应一个订阅单。

## 字段明细

### 用户基础信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_id | string | 用户 ID |
| country | string | 用户注册国家 |
| create_date | string | 用户注册日期 |
| utm_source | string | 投放渠道（utm 一级） |
| utm_medium | string | utm 二级渠道 |
| utm_campaign | string | utm 三级渠道 |
| activity_name | string | 活动名称 |
| activity_id | string | 直播间 ID |
| login_channel | string | 注册方式 |

### 用户活跃状态

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_new | int | 是否当天注册（1=是，0=否） |
| is_active | int | 当天是否活跃（1=是，0=否） |
| is_week_active | int | 本自然周是否活跃（1=是，0=否） |
| is_month_active | int | 本自然月是否活跃（1=是，0=否） |
| is_history_active | int | 历史是否有活跃记录，含当天（1=是，0=否） |

### 当前会员状态（基于权益表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_pro | int | 当天是否 Pro 会员（1=是，0=否） |
| is_m_pro | int | 当天是否月付 Pro 会员 |
| is_y_pro | int | 当天是否年付 Pro 会员 |
| is_free_trial_pro | int | 是否 Pro Free Trial 用户（首次购买 Pro 免费试用） |
| member_type | string | 当前会员类型（free/lite/pro/pro_plus/ultra）⭐推荐 |
| member_billing_type | string | 当前计费类型（monthly/yearly/one_month/free_trial）⭐推荐 |
| member_level | int | 当前会员等级（0=Free，1=Lite，2=Pro，3=Pro+，4=Ultra） |
| billing_level | int | 当前计费等级（0=one_month，1=monthly，2=yearly） |

### 前一天会员状态（用于升降级判断）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| previous_member_type | string | 前一天会员类型 |
| previous_member_billing_type | string | 前一天计费类型 |
| previous_member_level | int | 前一天会员等级 |
| previous_billing_level | int | 前一天计费等级 |

### 升降级判断字段

| 字段名 | 类型 | 说明 | 判断逻辑 |
|--------|------|------|----------|
| is_member_upgrade | int | 是否会员类型升级 | 今日 member_level > 昨日 member_level |
| is_billing_upgrade | int | 是否计费类型升级 | 今日 billing_level > 昨日 billing_level |
| is_upgrade | int | 是否有任何升级 | is_member_upgrade=1 OR is_billing_upgrade=1 |
| is_member_downgrade | int | 是否会员类型降级 | 今日 member_level < 昨日 member_level |
| is_billing_downgrade | int | 是否计费类型降级 | 今日 billing_level < 昨日 billing_level（且今日有会员） |
| is_downgrade | int | 是否有任何降级 | is_member_downgrade=1 OR is_billing_downgrade=1 |
| upgrade_type | string | 升级类型 | member/billing/both/NULL |
| upgrade_from_member_type | string | 升级前会员类型 | 仅当 is_member_upgrade=1 时有值 |
| upgrade_to_member_type | string | 升级后会员类型 | 仅当 is_member_upgrade=1 时有值 |
| upgrade_from_billing_type | string | 升级前计费类型 | 仅当 is_billing_upgrade=1 时有值 |
| upgrade_to_billing_type | string | 升级后计费类型 | 仅当 is_billing_upgrade=1 时有值 |

### 订阅状态

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_subscribe_pro | int | Pro 是否订阅中 |
| is_subscribe_m_pro | int | 月付 Pro 是否订阅中 |
| is_subscribe_y_pro | int | 年付 Pro 是否订阅中 |
| is_subscribe | int | 是否有任何会员订阅中 ⭐推荐 |
| subscribe_type | string | 订阅中的会员类型（lite/pro/pro_plus/ultra）⭐推荐 |
| subscribe_billing_type | string | 订阅的计费周期（monthly/yearly）⭐推荐 |

### 取消订阅状态

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_cancel_pro | int | 当天是否取消 Pro 订阅（今日 vs 昨日对比，从 Pro 会员变成非 Pro，含取消、终止、到期等） |
| is_cancel_m_pro | int | 当天是否取消月付 Pro 订阅（今日 vs 昨日对比） |
| is_cancel_y_pro | int | 当天是否取消年付 Pro 订阅（今日 vs 昨日对比） |
| is_cancel | int | 是否取消任何会员订阅 ⭐推荐 |
| cancel_from_type | string | 取消订阅的会员类型 ⭐推荐 |

### 订单统计 - Pro

| 字段名 | 类型 | 说明 |
|--------|------|------|
| history_paid_pro_order_cnt | bigint | 历史累计付费 Pro 订阅订单数 |
| history_paid_m_pro_order_cnt | bigint | 历史累计付费月付 Pro 订阅订单数 |
| history_paid_y_pro_order_cnt | bigint | 历史累计付费年付 Pro 订阅订单数 |
| pro_order_cnt | bigint | 当天发起 Pro 订阅订单量（含未付款，不含自动续费） |
| m_pro_order_cnt | bigint | 当天发起月付 Pro 订阅订单量（含未付款，不含自动续费） |
| y_pro_order_cnt | bigint | 当天发起年付 Pro 订阅订单量（含未付款，不含自动续费） |
| paid_pro_order_cnt | bigint | 当天完成 Pro 订阅订单量（最大为 1，不含自动续费） |
| week_paid_pro_order_cnt | bigint | 本周完成 Pro 订阅订单量 |
| month_paid_pro_order_cnt | bigint | 本月完成 Pro 订阅订单量 |
| paid_m_pro_order_cnt | bigint | 当天完成月付 Pro 订阅订单量（最大为 1） |
| paid_y_pro_order_cnt | bigint | 当天完成年付 Pro 订阅订单量（最大为 1） |

### 订单统计 - 其他会员类型

| 字段名 | 类型 | 说明 |
|--------|------|------|
| history_paid_lite_order_cnt | bigint | 历史累计付费 Lite 订阅订单数 |
| history_paid_pro_plus_order_cnt | bigint | 历史累计付费 Pro+ 订阅订单数 |
| history_paid_ultra_order_cnt | bigint | 历史累计付费 Ultra 订阅订单数 |
| lite_order_cnt | bigint | 当日 Lite 订阅订单数 |
| pro_plus_order_cnt | bigint | 当日 Pro+ 订阅订单数 |
| ultra_order_cnt | bigint | 当日 Ultra 订阅订单数 |
| paid_lite_order_cnt | bigint | 当日付费 Lite 订阅订单数 |
| paid_pro_plus_order_cnt | bigint | 当日付费 Pro+ 订阅订单数 |
| paid_ultra_order_cnt | bigint | 当日付费 Ultra 订阅订单数 |

### 订单统计 - 套餐包

| 字段名 | 类型 | 说明 |
|--------|------|------|
| history_paid_package_order_cnt | bigint | 历史累计付费套餐包订单数 |
| package_order_cnt | bigint | 当日套餐包订单数 |
| paid_package_order_cnt | bigint | 当日付费套餐包订单数 |
| week_paid_package_order_cnt | bigint | 本周付费套餐包订单数 |
| month_paid_package_order_cnt | bigint | 本月付费套餐包订单数 |

### 权益生效统计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| first_paid_pro_date | string | 首次付费 Pro 日期 |
| first_paid_m_pro_date | string | 首次付费月付 Pro 日期 |
| first_paid_y_pro_date | string | 首次付费年付 Pro 日期 |
| first_paid_lite_date | string | 首次付费 Lite 日期 |
| first_paid_pro_plus_date | string | 首次付费 Pro+ 日期 |
| first_paid_ultra_date | string | 首次付费 Ultra 日期 |
| pro_effective_cnt | bigint | Pro 权益累计生效次数 |
| m_pro_effective_cnt | bigint | 月付 Pro 权益累计生效次数 |
| y_pro_effective_cnt | bigint | 年付 Pro 权益累计生效次数 |
| lite_effective_cnt | bigint | Lite 权益生效次数 |
| pro_plus_effective_cnt | bigint | Pro+ 权益生效次数 |
| ultra_effective_cnt | bigint | Ultra 权益生效次数 |

### 有效权益详情（已废弃）

> 新计费方式按照金额计算，不再按照次数计算

| 字段名 | 类型 | 说明 |
|--------|------|------|
| effective_paid_entitlement_list | array&lt;string&gt; | 生效中付费权益列表（格式：product_id&&product_name） |
| effective_paid_entitlement_use_cnt | map&lt;string,string&gt; | 生效中付费权益使用量统计 |
| effective_paid_entitlement_limit | map&lt;string,string&gt; | 生效中付费权益额度限制 |
| effective_paid_entitlement_use_cnt_1d | map&lt;string,string&gt; | 当天生效中付费权益使用量 |

> 分区键：`date`（string，yyyyMMdd 格式）

## 常用查询示例

### 查询当日所有升级用户

```sql
SELECT *
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND is_upgrade = 1
```

### 查询会员类型升级分布

```sql
SELECT 
    upgrade_from_member_type,
    upgrade_to_member_type,
    COUNT(DISTINCT user_id) AS upgrade_user_cnt
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND is_member_upgrade = 1
GROUP BY upgrade_from_member_type, upgrade_to_member_type
```

### 查询各会员类型的用户分布

```sql
SELECT 
    member_type,
    member_billing_type,
    COUNT(DISTINCT user_id) AS user_cnt
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
GROUP BY member_type, member_billing_type
```

### 查询 Pro Free Trial 用户

```sql
SELECT *
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND is_free_trial_pro = 1
```

### 查询取消订阅的用户

```sql
SELECT *
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND is_cancel = 1
```

### 查询计费类型升级（月付 → 年付）

```sql
SELECT *
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND is_billing_upgrade = 1
  AND upgrade_from_billing_type = 'monthly'
  AND upgrade_to_billing_type = 'yearly'
```

### 查询复合升级用户

```sql
SELECT *
FROM cloudide.dwm_trade_trae_user_order_entitlement_statistic
WHERE date = '${date}'
  AND upgrade_type = 'both'
```

## 注意事项

1. **升降级判断逻辑**：基于当日与前一日的权益状态对比，需确保前一日数据已产出
2. **Free Trial 特殊处理**：`member_level=0`（与 free 相同），这样 Free Trial → Lite 会被正确识别为升级
3. **Free Trial 判断 SQL**：
   - 权益表：`get_json_object(extra_info, '$.is_trial') = 'true'`
   - 订单表：`get_json_object(extra_info, '$.has_trial_first_period') = 'true'`
4. **数据时效性**：数据为每日全量覆盖，当日数据反映截止到当日 23:59 的快照状态
5. **订单 vs 支付流水**：本表的订单为订阅订单（如连续包月 12 个月只算 1 个订阅单），不等同支付流水单
6. **取消订阅判断**：`is_cancel_pro` 等字段是通过今日 vs 昨日对比判定的，即昨日有 Pro 会员而今日无 Pro 会员则 `is_cancel_pro=1`
7. **订阅状态 vs 会员状态**：`is_subscribe` 表示当前仍在订阅中（未取消自动续费），`is_pro` 表示当前有有效 Pro 权益。用户可以取消订阅但权益仍在有效期内（`is_subscribe=0` 且 `is_pro=1`）

## 与权益粒度表的关系

本表是 `dwm_trade_trae_entitlement_order_usage_statistic_df`（权益粒度表）的聚合下游。

| 维度 | 本表（用户粒度） | 权益粒度表 |
|------|-----------------|-----------|
| 粒度 | 每个用户一行 | 每条权益一行 |
| 主键 | user_id | entitlement_id |
| 用途 | 用户画像、升降级分析、会员分布 | 权益明细、使用量分析、退款分析 |
| 关系 | 聚合后的宽表 | 源表 |
