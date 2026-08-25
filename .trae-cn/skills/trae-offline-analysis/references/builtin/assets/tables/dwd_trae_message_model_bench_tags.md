# dwd_trae_message_model_bench_tags

AI 对话消息特征打标表，记录每条用户消息的模型评估结果（如辱骂、称赞等特征标签）。`model_pred` 字段为 JSON 格式，包含模型返回的特征打标结果。适用场景：用户消息特征分析（辱骂/称赞/情感分析）、模型评估质量监控。

- cn: `flow_aipaas.dwd_trae_message_model_bench_tags`
- i18n: `ai_application_coding.dwd_trae_message_model_bench_tags`
- 分区字段: date（yyyyMMdd）
- TTL: 无限期（未设置）
- Dorado 任务 (cn): taskId `124027407`
- GUID: `870488d9-45f8-4ca9-a877-9b127ca032c8`
- 关联表: `flow_aipaas.dwd_trae_chat_input_hi`（通过 user_message_id + chat_session_id 关联）
- 设计背景: 专门的特征打标表，通过模型对用户消息进行多维度评估打标。注意 `chat_session_id` 对应的是 `conversation_id`

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_message_id | string | 用户消息唯一标识符 |
| user_source | string | 内外场（internal/public） |
| app_id | string | App ID |
| chat_session_id | string | 聊天会话标识（= conversation_id） |
| model_pred | string | 模型返回结果（JSON 格式），包含情感分析和对话流转评估两个维度的打标结果，详见下方 schema |

> 分区键: date (string, yyyyMMdd)

## model_pred JSON Schema

`model_pred` 是一个 JSON 字符串，包含两个独立的评估维度：

### 1. 情感分析（sentiment）

评估用户消息的情感倾向（辱骂/称赞/其他）。

| JSON 路径 | 类型 | 说明 |
|-----------|------|------|
| `$.sentiment_label` | string | 情感分类标签，取值：`辱骂` / `称赞` / `其他` |
| `$.sentiment_scores.辱骂` | float | 辱骂概率分数（0~1） |
| `$.sentiment_scores.称赞` | float | 称赞概率分数（0~1） |
| `$.sentiment_scores.其他` | float | 其他概率分数（0~1） |

> `sentiment_label` 取概率最高的标签。典型情况下 `其他` 占绝大多数（>98%），辱骂和称赞为低概率事件。

### 2. 对话流转评估（conv_flow）

评估 AI 的对话质量和解决问题的效率。

| JSON 路径 | 类型 | 说明 |
|-----------|------|------|
| `$.conv_flow_label` | string | 对话流转标签，取值：`原地踏步` / `打补丁` / `流畅` / `其他` |
| `$.conv_flow_scores.原地踏步` | float | 原地踏步概率分数（0~1） |
| `$.conv_flow_scores.打补丁` | float | 打补丁概率分数（0~1） |
| `$.conv_flow_scores.流畅` | float | 流畅概率分数（0~1） |
| `$.conv_flow_scores.其他` | float | 其他概率分数（0~1） |

**对话流转标签含义**：

| conv_flow_label | 含义 |
|-----------------|------|
| `原地踏步` | Agent 反复执行相同或相似的操作，没有实质性进展（如循环修改同一段代码、反复运行失败的命令） |
| `打补丁` | Agent 在不断修复问题，但方式是打补丁式的，未从根本上解决（如修了 A 引发 B，再修 B 又引发 C） |
| `流畅` | Agent 的对话和操作流畅，能高效解决问题 |
| `其他` | 不属于以上明确类别 |

### 样本数据

```json
{
  "sentiment_label": "其他",
  "sentiment_scores": {
    "其他": 0.9878,
    "称赞": 0.0113,
    "辱骂": 0.0007
  },
  "conv_flow_label": "打补丁",
  "conv_flow_scores": {
    "原地踏步": 0.1240,
    "打补丁": 0.7896,
    "流畅": 0.0369,
    "其他": 0.0498
  }
}
```

### 常用查询方式

```sql
-- 查询辱骂消息
SELECT user_message_id, chat_session_id,
       get_json_object(model_pred, '$.sentiment_label') AS sentiment,
       get_json_object(model_pred, '$.sentiment_scores.辱骂') AS abuse_score
FROM flow_aipaas.dwd_trae_message_model_bench_tags
WHERE date = '20260510'
  AND get_json_object(model_pred, '$.sentiment_label') = '辱骂'

-- 查询原地踏步消息
SELECT user_message_id, chat_session_id,
       get_json_object(model_pred, '$.conv_flow_label') AS conv_flow,
       get_json_object(model_pred, '$.conv_flow_scores.原地踏步') AS stuck_score
FROM flow_aipaas.dwd_trae_message_model_bench_tags
WHERE date = '20260510'
  AND get_json_object(model_pred, '$.conv_flow_label') = '原地踏步'

-- 统计各标签分布
SELECT get_json_object(model_pred, '$.conv_flow_label') AS conv_flow_label,
       COUNT(*) AS cnt
FROM flow_aipaas.dwd_trae_message_model_bench_tags
WHERE date = '20260510'
GROUP BY get_json_object(model_pred, '$.conv_flow_label')
ORDER BY cnt DESC
```

> **注意**：
> - `chat_session_id` 的语义是 `conversation_id`（会话 ID）。与 DWD 行为表（event_di、delta_di 等）JOIN 时，应使用 `chat_session_id = event_di.session_id`（因为 event_di 的 `session_id` 语义也是 conversation_id，详见 index.md 的 session_id 语义映射表）
> - `user_message_id` 对应其他表的 `message_id`，JOIN 条件：`user_message_id = event_di.message_id`
> - ⚠️ 不要与 `dwd_resource_prompt_completion_di` 的字段名混淆 — 该表的 `session_id` 实际含义是 message_id（语义反转）
