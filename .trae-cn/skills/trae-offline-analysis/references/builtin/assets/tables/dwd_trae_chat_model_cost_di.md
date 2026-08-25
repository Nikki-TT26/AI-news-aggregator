# dwd_trae_chat_model_cost_di

- **cn 库表名**：`flow_aipaas.dwd_trae_chat_model_cost_di`
- **i18n 库表名**：`ai_application_coding.dwd_trae_chat_model_cost_di`
- **分区字段**：`date`（yyyyMMdd）
- **TTL**：730 天
- **Dorado 任务（cn）**：taskId `125408856`（HSQL），项目 `cn_11253`
- **Dorado 任务（i18n）**：taskId `306346852`（HSQL），项目 `sg_300004442`
- **上游表（cn）**：`cloudide.dwd_resource_prompt_completion_di`、`flow_aipaas.ods_trae_model_price`（通过 DTS 任务 `125407473` 从飞书电子表格同步）
- **上游表（i18n）**：`cloudide.dwd_resource_prompt_completion_di`、`ai_application_coding.ods_trae_model_price`（通过 DTS 任务 `306341171` 从飞书电子表格同步）
- **设计背景**：AI Chat 模型调用成本明细表，将 completion 表的每条请求关联单价表计算出 CU 成本。包含所有 status 的请求（含 fail），因为失败请求也消耗了 token 产生了真实成本；排除 `request_type = 'custom'` 的请求（只统计内置模型的成本）。用于 Gallery 指标组「AI行为_Chat_资源指标(设备维度)」的数据源。采用最长前缀匹配 + 家族兜底 + ark 兜底的三层匹配策略关联单价表。

> **字段语义映射**：上游表 `dwd_resource_prompt_completion_di` 中的 `session_id` 实际含义是 message_id，`conversation_id` 实际含义是 session_id。本表在 Dorado SQL 中通过 `conversation_id AS session_id, session_id AS message_id` 进行了语义修正，使字段名与实际含义一致。
>
> **虚拟列说明**：上游表 `dwd_resource_prompt_completion_di` 的 `request_metadata` JSON 字段已配置虚拟列（device_id, config_name, agent_type, access_type, request_type 等），Dorado SQL 中直接使用虚拟列名，无需 `get_json_object()`。
>
> **海外（SG）差异说明**：
> - 上游表 `cloudide.dwd_resource_prompt_completion_di`（SG）暂缺 `conversation_id` 列，海外 SQL 中 `session_id` 字段暂填 `CAST(NULL AS STRING)`，`message_id` 来自上游 `session_id`（语义与国内一致）。待海外表补齐 `conversation_id` 后需修正为 `conversation_id AS session_id`
> - `device_id`、`config_name`、`agent_type`、`access_type`、`request_type` 均使用海外虚拟列（与国内一致）
> - 上游单价表为 `ai_application_coding.ods_trae_model_price`（通过 DTS 任务 `306341171` 从飞书电子表格同步）

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_id | string | 用户ID |
| device_id | string | 设备ID，从request_metadata中提取。⚠️ 继承上游表覆盖率问题：非桌面端（Mobile/SoloWeb/SoloLite）几乎不上报，**不可用于 DAU 统计**，应使用 `user_id`（详见 `dwd_resource_prompt_completion_di` 的「DAU 统计口径建议」） |
| model_name | string | 实际调用的模型名称 |
| config_name | string | 模型配置名称，从request_metadata中提取 |
| session_id | string | 会话ID（对应completion表的conversation_id） |
| message_id | string | 消息ID（对应completion表的session_id） |
| type | string | 对话类型 |
| agent_type | string | Agent类型，从request_metadata中提取 |
| access_type | string | 访问类型(如Default)，从request_metadata中提取 |
| request_type | string | 请求类型(如dev/custom)，从request_metadata中提取 |
| region | string | 数据来源region |
| status | string | 请求状态success/fail |
| prompt_tokens_cnt | bigint | prompt token消耗 |
| completion_tokens_cnt | bigint | completion token消耗 |
| cache_read_tokens_cnt | bigint | 命中缓存的prompt token数 |
| reasoning_tokens_cnt | bigint | 模型思考过程token数 |
| total_tokens_cnt | bigint | 总token消耗 |
| price_model_name | string | 匹配到的单价表模型名称 |
| input_normal_price | double | 正常输入单价（平均后的） |
| output_price | double | 输出单价（平均后的） |
| input_cache_read_price | double | 缓存输入读取单价（平均后的） |
| discount | double | 折扣系数 |
| input_normal_cost | double | 正常输入成本 |
| input_cache_read_cost | double | 缓存输入成本 |
| output_cost | double | 输出成本 |
| reasoning_cost | double | 推理成本(国内不计费为0) |
| total_cost | double | 总成本=各项成本之和*折扣 |

## Token 字段与 dwd_resource_prompt_completion_di 的口径差异

本表和 `dwd_resource_prompt_completion_di` 都包含 token 消耗字段（`total_tokens_cnt`、`prompt_tokens_cnt`、`completion_tokens_cnt`、`reasoning_tokens_cnt`、`cache_read_tokens_cnt` 等），口径已基本对齐但仍有差异：

| 维度 | dwd_trae_chat_model_cost_di（本表） | dwd_resource_prompt_completion_di |
|------|-----------------------------------|-----------------------------------|
| status 过滤 | **无**（包含所有 status，含 fail） | 无（包含 fail 请求的 token） |
| request_type 过滤 | 排除 `request_type = 'custom'`（Dorado SQL 中已过滤） | 无 |
| model_usage 过滤 | 无 | 在 Gallery SQL 中通常用 `model_usage = 'chat_completion'` 过滤（通过虚拟列） |
| app_id 过滤 | 无 | 在 Gallery SQL 中通常用 `app_id = '6eefa01c-1036-4c7e-9ca5-d891f63bfcd8'` 过滤 |

**剩余差异影响**：
- 本表仍排除 `request_type = 'custom'` 的请求，而 `dwd_resource_prompt_completion_di` 不过滤 request_type
- `dwd_resource_prompt_completion_di` 在 Gallery SQL 中通常按 `app_id = '6eefa01c-1036-4c7e-9ca5-d891f63bfcd8'` 过滤，而本表不过滤 app_id（但上游 completion_di 已按 app_id 过滤，因此影响较小）
- Gallery 指标组中的 token 消耗指标（如"消息均总token消耗"）的 `llm_call_cnt` 来自 `dwd_resource_prompt_completion_di`（额外按 `model_usage = 'chat_completion'` 过滤），而成本指标的 `cost_request_cnt` 来自本表（不过滤 model_usage），**两者分母仍可能不同**
- 用本表替代 `dwd_resource_prompt_completion_di` 做 token 验证时，由于 `request_type`、`model_usage` 和 `app_id` 过滤差异，绝对值仍可能有偏差，但 Diff%（实验组间变化率）通常方向一致

> **提示**：`dwd_resource_prompt_completion_di` 的 `request_metadata` 列是敏感列，TQS 查询可能因字段级权限不足而失败。如遇此问题，可改用本表的 token 字段做近似验证（status 口径已对齐，主要差异仅在 request_type 过滤）。
