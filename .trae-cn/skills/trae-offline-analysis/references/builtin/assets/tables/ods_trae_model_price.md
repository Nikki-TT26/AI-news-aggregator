# ods_trae_model_price

- **cn 库表名**：`flow_aipaas.ods_trae_model_price`
- **i18n 库表名**：`ai_application_coding.ods_trae_model_price`
- **分区字段**：`date`（yyyyMMdd）
- **TTL**：365 天
- **Dorado 任务（cn）**：taskId `125407473`（DTS larksheet2hive），项目 `cn_11253`
- **Dorado 任务（i18n）**：taskId `306341171`（DTS larksheet2hive），项目 `sg_300004442`
- **一级下游表**：`dwd_trae_chat_model_cost_di`
- **设计背景**：模型单价配置表，数据源为飞书电子表格，通过 Dorado DTS（larksheet2hive）任务每日同步。包含各模型的阶梯定价信息（不同 token 区间对应不同单价），供 `dwd_trae_chat_model_cost_di` 关联计算成本。

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| model_name | string | 模型名称（用于最长前缀匹配） |
| token_min | string | 阶梯 token 下限（含） |
| token_max | string | 阶梯 token 上限（不含） |
| input_normal_price | string | 输入正常单价 |
| output_price | string | 输出单价 |
| input_cache_read_price | string | 输入缓存读取单价 |
| discount | string | 折扣系数 |

> **注意**：所有价格和 token 字段在 ODS 层均为 string 类型（飞书表格同步原始值），下游 `dwd_trae_chat_model_cost_di` 的 Dorado SQL 中会 CAST 为 BIGINT/DOUBLE 使用。
>
> **阶梯定价说明**：同一个 model_name 可以有多行（对应不同 token 区间），形成阶梯计价。例如 0-100K tokens 一个单价，100K-1M tokens 另一个单价。`ark` 作为兜底模型，当请求的 model_name 无法匹配到任何价格模型时使用。
