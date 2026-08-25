# dwm_trade_trae_entitlement_order_usage_statistic_df

Trae 权益订单粒度商业化宽表（权益粒度，每条权益记录一行）。记录用户的每一期权益信息，包含订单关联、AI 功能使用量、退款信息等。适用场景：权益明细分析、付费用户使用量分析、退款分析、订阅续费追踪。

- **i18n 库表名**：`cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df`
- **分区字段**：`date`（yyyyMMdd）
- **TTL**：750 天
- **更新频率**：每日全量覆盖
- **Dorado 任务（i18n）**：taskId `304709904`，项目 `sg_300004344`
- **上游表**：`cloudide.dwd_trade_trae_user_entitlement_hf`（权益明细）、`cloudide.dwd_trade_trae_order_hf`（订单）、`cloudide.dwd_trade_trae_ai_usage_df`（AI 使用量）、`cloudide.dwd_trade_trae_refund_df` / `dwd_trade_trae_refund_v2_df`（退款）

## 核心概念

- **数据粒度**：权益粒度。每条权益记录一行权益单记录
  - **月付续订场景**：每月续订月 Pro，则每月生成一条新的权益记录
  - **年付场景**：用户订阅一年套餐（年付），则每月生成一条新权益记录，12 个月共 12 条记录，这些记录的 `order_id` 相同，`entitlement_id` 不同
- **一次性付费场景**：年付套餐一次性付费时，只有第一条权益记录（`entitlement_order_seq = 1`）的 `charge_amount > 0`，后续月份的权益记录 `charge_amount = 0`
- **主键**：`entitlement_id`
- **有效权益判断**：需同时满足 `status = 0` 且 `start_timestamp <= 当前时间 <= end_timestamp`
- **状态判断**：
  - `status = 0`：权益正常
  - `status = -1`：权益已删除或过期
  - `status` 非 0：退款
- **生产数据起点**：`create_timestamp >= 1748345640000` 之前为测试数据
- **金额单位**：`charge_amount`、`refund_amount`、`order_total_pay_amount` 均以最小货币单位存储（如美分）

## 产品体系

> 详细商品说明参考：[trae商品说明](https://bytedance.larkoffice.com/docx/T9N2dpuY3oGqvjxLWjNcd3Zangg)

### 产品类型 (product_type)

| product_type | 会员类型 | 说明 |
|---|---|---|
| 0 | Free | 免费用户 |
| 1 | Pro | Pro 专业版 |
| 2 | Package | 套餐包/容量包 |
| 4 | Pro+ | Pro+ 增强版 |
| 6 | Ultra | Ultra 旗舰版 |
| 8 | Lite | Lite 轻量版 |

### 产品 ID 与计费类型映射 (product_id)

| 会员类型 | monthly (月付) | yearly (年付) | one_month (单次) |
|---|---|---|---|
| Lite | 37 | 38 | 39 |
| Pro | 2 | 3 | 27 |
| Pro+ | 30 | 31 | 28 |
| Ultra | 32 | 33 | 29 |

> **Pro Free Trial**：`product_id = 2` 且 `get_json_object(extra_info, '$.is_trial') = 'true'` 时为免费试用

### 订阅周期 (subscription_period)

| 值 | 说明 |
|---|---|
| 0 | 月付 |
| 1 | 年付 |

## 字段明细

### 权益基础信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| entitlement_id | bigint | 权益 ID（主键） |
| user_id | string | 用户 ID |
| product_id | bigint | 产品 ID，详见产品 ID 映射表 |
| product_type | bigint | 产品类型（0=Free, 1=Pro, 2=Package, 4=Pro+, 6=Ultra, 8=Lite） |
| product_name | string | 产品名称 |
| order_id | bigint | 关联订单 ID（年付套餐 12 条权益共享同一 order_id） |
| status | bigint | 权益状态（0=正常，-1=删除/过期） |
| extra_info | string | 附加信息（JSON 格式，含 is_trial、channel_order_id 等） |

### 权益时间信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| start_timestamp | bigint | 权益开始时间（毫秒时间戳） |
| start_time | string | 权益开始时间（字符串格式） |
| end_timestamp | bigint | 权益结束时间（毫秒时间戳） |
| end_time | string | 权益结束时间（字符串格式） |
| create_timestamp | bigint | 权益创建时间（毫秒时间戳） |
| create_time | string | 权益创建时间（字符串格式） |
| update_timestamp | bigint | 最后更新时间（毫秒时间戳） |
| update_time | string | 最后更新时间（字符串格式） |
| next_bill_timestamp | bigint | 下次扣费时间戳（订阅用） |
| next_bill_time | string | 下次扣费时间（订阅用） |

### 订阅与支付信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| subscription_payment_id | string | 订阅单支付单号 |
| is_last_period | bigint | 是否是最后一期（1=是，0=否） |
| charge_amount | bigint | 扣费金额（单位：美分）。年付套餐仅第一条权益记录 > 0 |
| region | string | 区域标识（VA/SG） |
| channel_order_id | string | PIPO 订单 ID |
| entitlement_order_seq | bigint | 该权益在对应订单下的发放序号，按权益创建时间升序排列 |

### 订单关联信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| order_create_time | string | 关联订单创建时间 |
| order_total_pay_amount | bigint | 关联订单总金额（单位：美分） |
| order_country | string | 订单国家 |
| user_country | string | 用户注册国家 |
| order_subscription_status | bigint | 订单订阅状态 |
| subscription_period | string | 订阅周期（0=月付，1=年付） |
| sku_id | string | SKU ID |
| pipo_sku_id | string | PIPO SKU ID |
| pay_date | string | 支付日期（yyyyMMdd 格式） |

### AI 功能使用量 - 累计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| auto_completion_used_cnt | double | 代码补全累计使用次数 |
| advanced_model_used_cnt | double | 基础模型累计使用次数 |
| premium_model_fast_used_cnt | double | 高级模型（快队列）累计使用次数 |
| premium_model_slow_used_cnt | double | 高级模型（慢队列）累计使用次数 |
| basic_balance_used_cnt | double | basic 累计消耗金额 |
| bonus_balance_used_cnt | double | bonus 累计消耗金额 |

### AI 功能使用量 - 当日增量

> 计算方式：今日累计 - 昨日累计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| auto_completion_used_cnt_1d | double | 当日代码补全使用次数 |
| advanced_model_used_cnt_1d | double | 当日基础模型使用次数 |
| premium_model_fast_used_cnt_1d | double | 当日高级模型（快队列）使用次数 |
| premium_model_slow_used_cnt_1d | double | 当日高级模型（慢队列）使用次数 |
| basic_balance_used_cnt_1d | double | 当日 basic 消耗金额 |
| bonus_balance_used_cnt_1d | double | 当日 bonus 消耗金额 |

### AI 功能使用量 - 分平台累计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| basic_balance_used_cnt_ide | double | IDE 桌面端 basic_balance 累计用量 |
| basic_balance_used_cnt_lite | double | Lite 端 basic_balance 累计用量 |
| basic_balance_used_cnt_web | double | Web 端 basic_balance 累计用量 |
| bonus_balance_used_cnt_ide | double | IDE 桌面端 bonus_balance 累计用量 |
| bonus_balance_used_cnt_lite | double | Lite 端 bonus_balance 累计用量 |
| bonus_balance_used_cnt_web | double | Web 端 bonus_balance 累计用量 |

### AI 功能使用量 - 分平台当日增量

| 字段名 | 类型 | 说明 |
|--------|------|------|
| basic_balance_used_cnt_ide_1d | double | IDE 桌面端 basic_balance 昨日增量 |
| basic_balance_used_cnt_lite_1d | double | Lite 端 basic_balance 昨日增量 |
| basic_balance_used_cnt_web_1d | double | Web 端 basic_balance 昨日增量 |
| bonus_balance_used_cnt_ide_1d | double | IDE 桌面端 bonus_balance 昨日增量 |
| bonus_balance_used_cnt_lite_1d | double | Lite 端 bonus_balance 昨日增量 |
| bonus_balance_used_cnt_web_1d | double | Web 端 bonus_balance 昨日增量 |

### AI 功能额度限制（2.0 已废弃）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| auto_completion_limit | bigint | 代码补全额度上限 |
| advanced_model_request_limit | bigint | 基础模型请求额度上限 |
| premium_model_fast_request_limit | bigint | 高级模型（快队列）额度上限 |
| premium_model_slow_request_limit | bigint | 高级模型（慢队列）额度上限 |

### PayGo 用量

| 字段名 | 类型 | 说明 |
|--------|------|------|
| paygo_paid_amount | double | 该权益周期 PayGo 金额。当用户开通月/年会员后，PayGo 使用时会生成一条与当前会员权益周期相同（30 天）的记录，该字段表示此权益上通过 PayGo 付款的美金金额 |

### 退款信息

| 字段名 | 类型 | 说明 |
|--------|------|------|
| is_refund | int | 是否已退款（1=是，0=否） |
| refund_date | string | 退款日期（yyyyMMdd 格式） |
| refund_time | string | 退款时间 |
| refund_timestamp | bigint | 退款时间戳 |
| refund_amount | bigint | 退款金额（单位：美分） |
| refund_order_id | string | 退款订单 ID |
| refund_extra_info | string | 退款附加信息 |

> 分区键：`date`（string，yyyyMMdd 格式）

## 常用查询示例

### 查询用户当前有效权益

```sql
SELECT *
FROM cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df
WHERE date = '${date}'
  AND user_id = 'xxx'
  AND status = 0
  AND start_timestamp <= unix_timestamp('${date+1}', 'yyyyMMdd') * 1000
  AND end_timestamp >= unix_timestamp('${date+1}', 'yyyyMMdd') * 1000
```

### 查询各产品类型的权益分布

```sql
SELECT 
    product_type,
    CASE 
        WHEN product_type = 0 THEN 'Free'
        WHEN product_type = 1 THEN 'Pro'
        WHEN product_type = 2 THEN 'Package'
        WHEN product_type = 4 THEN 'Pro+'
        WHEN product_type = 6 THEN 'Ultra'
        WHEN product_type = 8 THEN 'Lite'
        ELSE 'Unknown'
    END AS product_type_name,
    COUNT(DISTINCT entitlement_id) AS entitlement_cnt,
    COUNT(DISTINCT user_id) AS user_cnt
FROM cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df
WHERE date = '${date}'
  AND status = 0
GROUP BY product_type
```

### 查询 Pro Free Trial 用户

```sql
SELECT *
FROM cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df
WHERE date = '${date}'
  AND product_id = 2
  AND get_json_object(extra_info, '$.is_trial') = 'true'
```

### 查询退款订单

```sql
SELECT *
FROM cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df
WHERE date = '${date}'
  AND is_refund = 1
```

### 查询即将到期的权益（7天内）

```sql
SELECT 
    user_id,
    entitlement_id,
    product_name,
    end_time,
    DATEDIFF(
        from_unixtime(end_timestamp / 1000, 'yyyy-MM-dd'),
        from_unixtime(unix_timestamp('${date}', 'yyyyMMdd'), 'yyyy-MM-dd')
    ) AS days_until_expire
FROM cloudide.dwm_trade_trae_entitlement_order_usage_statistic_df
WHERE date = '${date}'
  AND status = 0
  AND end_timestamp >= unix_timestamp('${date}', 'yyyyMMdd') * 1000
  AND end_timestamp <= unix_timestamp('${date}', 'yyyyMMdd') * 1000 + 7 * 24 * 60 * 60 * 1000
```

## 与用户粒度表的关系

本表是用户粒度表（`dwm_trade_trae_user_order_entitlement_statistic`）的上游数据源之一。

| 维度 | 本表（权益粒度） | 用户粒度表 |
|------|-----------------|-----------|
| 粒度 | 每条权益一行 | 每个用户一行 |
| 主键 | entitlement_id | user_id |
| 用途 | 权益明细、使用量分析 | 用户画像、升降级分析 |
| 关系 | 源表 | 聚合后的宽表 |
