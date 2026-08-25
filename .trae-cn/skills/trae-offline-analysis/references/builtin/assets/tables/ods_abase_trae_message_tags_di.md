# ods_abase_trae_message_tags_di

Abase 数据源中 Trae 的消息标签表（每日增量），记录每条 AI 对话消息的 query tag（message_tags）。数据由 Abase2Hive 同步任务自动写入，是**消息维度圈 Query** 的核心数据源。

> **圈 Query 概念**：圈 Query 是指通过 query tag（消息标签）筛选特定子人群或子消息集合，在 Libra Gallery 实验指标中按标签维度切分数据进行分析的机制。query tag 由在线服务在每条消息处理过程中打标并写入 Abase，标识该消息使用的模型名称和触发的行为/功能特征。圈 Query 分为两种维度：
> - **消息维度圈 Query**：在 Gallery 指标组中配置为"指标维度"，数据源为本表（`ods_abase_trae_message_tags_di`），直接按消息粒度的 query tag 筛选。适用于需要精确到消息级别的指标分析（如某个 tag 下的消息反馈率、工具调用率等）
> - **用户维度圈 Query**：在 Gallery 指标组中配置为"公共维度"（uuid 下其他维度细分后唯一），数据源为 `dwm_trae_user_message_tags_di`，按 did 聚合当日所有消息的 query tag 去重集合。适用于用户级别的指标分析（如某个 tag 下的用户活跃天、session 数等）
>
> 参考：[Trae Libra圈Query指标建设](https://bytedance.larkoffice.com/wiki/BA2JwEb7eiqdNPkrxB0cow5QnBb)

abase_key 有两种格式：绝大多数（99.99%）为纯 message_id（24位十六进制字符串，如 `0d821d3a9807c460a6047a04`），极少量（~0.01%）为 `sess_<session_id>` 格式（session 级别标签）。abase_value 为 JSON 字符串（仅包含 `$.tags` 字段）。平台配置了两个虚拟列（message_id 和 message_tags），方便直接查询。

- cn: `flow_aipaas.ods_abase_trae_message_tags_di`
- i18n: `cloudide.ods_abase_trae_message_tags_di`（schema 与 cn 一致）
- 分区字段: date（yyyyMMdd）
- TTL: 365天
- 主键: abase_key
- Dorado 任务 (cn): [ods_abase_trae_message_tags_di](https://data.bytedance.net/dorado/development/node/122975512?project=cn_11253) (projectId: 11253, taskId: 122975512)
- Dorado 任务 (sg): [ods_abase_trae_message_tags_di](https://dataleap-sg.tiktok-row.net/dorado/development/node/305449525?project=sg_300004442) (projectId: 300004442, taskId: 305449525)
- Hive URL (cn): https://data.bytedance.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fflow_aipaas%2Fods_abase_trae_message_tags_di%400#group=default
- Hive URL (sg): https://dataleap-sg.tiktok-row.net/coral/datamap/detail?from=coral_copy_link&groupName=default&qualifiedName=HiveTable%3A%2F%2F%2Fcloudide%2Fods_abase_trae_message_tags_di%406#group=default
- 一级下游表: `flow_aipaas.dwm_trae_user_message_tags_di`（通过 message_id 关联，按 did 聚合标签）
- 关联表: `flow_aipaas.dwd_trae_ai_behavior_info_message_delta_di`（dwm 加工时通过 message_id JOIN 获取 did）
- 数据来源: Abase2Hive 自动同步（非 Dorado SQL 加工），Abase 中的数据由在线服务写入

## 物理字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| abase_key | string | Abase 存储中 key 字段。两种格式：① 纯 message_id（24位十六进制，占 99.99%，如 `0d821d3a9807c460a6047a04`）；② `sess_<session_id>`（占 ~0.01%，session 级别标签）。虚拟列 `message_id` 通过 `substring_index(abase_key, '_', -1)` 提取——对无下划线的 key 返回原值（即 message_id 本身），对 `sess_` 前缀的 key 返回 session_id |
| abase_value | string | Abase 存储中 value 字段，JSON 格式，仅包含 `{"tags": [...]}` 一个字段。详见下方 abase_value JSON 结构 |
| dimer_meta | struct\<expire_ms:bigint\> | 系统字段，Abase2Hive 任务元数据（expire_ms 为过期时间戳，单位毫秒） |

> 分区键: date (string, yyyyMMdd)

## 虚拟列（平台配置）

平台已配置以下虚拟列，可在 ByteQuery / TQS 中直接使用，无需手动解析：

| 虚拟列名 | 类型 | 表达式 | 描述 |
|----------|------|--------|------|
| message_id | string | `substring_index(abase_key, '_', -1)` | 消息 ID，从 abase_key 中提取 |
| message_tags | array\<string\> | `from_json(get_json_object(abase_value, '$.tags'), 'array<string>')` | 消息标签数组，从 abase_value JSON 的 `$.tags` 字段解析 |

## abase_value JSON 结构

`abase_value` 是一个 JSON 字符串，结构为 `{"tags": ["tag1", "tag2", ...]}` ：

| JSON 路径 | 类型 | 描述 |
|-----------|------|------|
| `$.tags` | array\<string\> | 消息标签数组，包含模型名称标签和行为/特征标签（标签值详见 `dwm_trae_user_message_tags_di.md` 的标签值说明） |

样本示例：
```json
{"tags":["Doubao-Seed-2.0-Code","doubao_dev"]}
{"tags":["run_command_tool_called","trigger_micro_compact","doubao-for-auto","doubao_dev"]}
{"tags":["deepseek-V3.1"]}
```

## 常见查询模式

### 按 message_id 查询标签

```sql
-- abase_key 绝大多数情况下就是 message_id 本身
SELECT
    abase_key AS message_id,
    from_json(get_json_object(abase_value, '$.tags'), 'array<string>') AS message_tags
FROM flow_aipaas.ods_abase_trae_message_tags_di
WHERE date = '20260414'
    AND abase_key = '<message_id>'
LIMIT 10
```

### 按标签过滤消息

```sql
SELECT
    abase_key AS message_id,
    from_json(get_json_object(abase_value, '$.tags'), 'array<string>') AS message_tags
FROM flow_aipaas.ods_abase_trae_message_tags_di
WHERE date BETWEEN '20260410' AND '20260414'
    AND instr(abase_key, '_') = 0  -- 排除 sess_ 前缀的 session 级记录，只保留 message 级
    AND array_contains(
        from_json(get_json_object(abase_value, '$.tags'), 'array<string>'),
        '<target_tag>'
    )
```

### 与 toolcalls / prompt_completion 联合查询

该表常与 `code_evaluation.trae_cn_toolcalls` 或 `cloudide.dwd_resource_prompt_completion_di` 通过 message_id 进行 JOIN，用于圈选特定标签的消息后分析其工具调用或模型调用详情。
