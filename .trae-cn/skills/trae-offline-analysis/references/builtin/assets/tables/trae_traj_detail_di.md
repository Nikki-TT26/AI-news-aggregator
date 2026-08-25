# trae_traj_detail_di

Trae Agent 轨迹详情表（Trajectory Detail），每行为一条完整的 Agent 轨迹记录。从 Fornax Trace 数据中提取加工，包含 Agent 元信息、完整消息序列（messages JSON）、时间和 Token 统计、finish_reason 等。是分析 Agent 行为、模型调用效率、工具使用模式、对话质量的**核心数据源**。一次用户消息（message）可产生多个 Trajectory，形成树形结构（master + sub 轨迹）。

- cn: `flow_aipaas.trae_traj_detail_di`
- i18n: `ai_application_coding.trae_traj_detail_di`
- 分区字段: date（yyyyMMdd）
- TTL: 30天
- Dorado 任务 (cn): taskId `124838472`
- GUID: `7d083ab7-dd58-41c8-a456-edfb03220e54`
- 上游表: `flow_aipaas.trae_agent_fornax_detail_di`
- 设计背景: Trae Agent 轨迹数据离线表体系的核心表。数据链路：Fornax 在线 Trace → trae_agent_fornax_detail_di（ODS）→ trae_traj_detail_di。每天 T+1 刷新，SLA T+1 09:00 前

## 核心概念

### Trajectory（轨迹）类型

| traj_type | 含义 | 触发条件 |
|-----------|------|----------|
| `master` | 主 Agent 轨迹 | 新一轮对话、或因消息内容变化（如 compact/summary）而切分 |
| `sub` | 子 Agent 轨迹 | 存在 parent_agent_run_id 的 Span，如 Search Agent |

### traj_tag 含义

- `traj_tag = 0`：正常轨迹（最后一条 LLMCallSpan 输出不含 tool_calls）
- `traj_tag = 1`：异常轨迹（最后一条 LLMCallSpan 输出仍含 tool_calls，表示还有后续处理）

### finish_reason 常见取值

| 值 | 含义 |
|----|------|
| `stop` | 正常结束 |
| `tool_calls` | LLM 请求调用工具 |
| `length` | 达到最大 token 限制 |
| `engine_overloaded` | 引擎过载 |
| `sensitive` | 命中敏感内容审核 |
| `content_filter` | 内容过滤 |
| `network_error` | 网络错误 |

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| conversation_id | string | 会话 ID |
| message_id | string | 消息 ID |
| traj_id | string | 轨迹唯一 ID，格式 `{message_id}_{traj_type}_{uuid}` |
| traj_type | string | 轨迹类型：`master` / `sub` |
| parent_traj_id | string | 父轨迹 ID，sub 轨迹指向触发它的 master 轨迹 |
| trigger_tool_call_id | string | 触发子 Agent 的 tool_call_id |
| trigger_span_id | string | 触发子 Agent 的 span_id |
| model_name_list | string | 使用的模型名称列表 |
| agent_name | string | Agent 名称（Builder / SOLO Coder / Search Agent 等） |
| agent_id | string | Agent 实例 UUID |
| first_span_time | bigint | 第一条 Span 的 start_time（微秒时间戳） |
| last_span_time | bigint | 最后一条 Span 的 start_time（微秒时间戳） |
| total_duration | bigint | 总耗时（微秒）= last_span.start_time + duration - first_span.start_time |
| llm_call_count | int | LLMCallSpan 数量 |
| total_input_tokens | bigint | 总输入 token 数 |
| total_output_tokens | bigint | 总输出 token 数 |
| total_tokens | bigint | 总 token 数 |
| finish_reason | string | 最后一条 LLMCallSpan 的结束原因（stop / tool_calls / length 等） |
| messages | string | 完整 messages JSON 数组（取最后一条 LLMCallSpan 的 input + output） |
| call_options_json | string | 最后一条 LLMCallSpan 的调用参数（temperature / max_tokens / top_p） |
| traj_tag | int | 轨迹标签（0=正常, 1=最后一条 LLMCallSpan 输出含 tool_calls） |
| tools_json | string | 该轨迹可用的工具定义列表（OpenAI function calling 格式） |
| span_ids | string | 该 traj 内所有 LLMCallSpan 的 span_id 有序列表（JSON 数组） |
| agent_type | string | Agent 类型（如 builder_v3、chat_v3、solo_coder 等） |
| main_agent_type | string | 主 Agent 类型 |

> 分区键: date (string, yyyyMMdd)

## messages 字段结构

`messages` 字段为 JSON Array，取最后一条 LLMCallSpan 的 input messages + output message：

```json
[
  {
    "role": "system|user|assistant|tool",
    "content": "消息内容",
    "reasoning_content": "模型推理过程（思维链）",
    "tool_calls": [
      {
        "id": "call_xxx",
        "type": "function",
        "function": { "name": "Edit", "arguments": "{...}" }
      }
    ],
    "_span_id": "对应的 span ID"
  }
]
```

## 主轨迹切分规则

同一个 message_id 下的主链路 Span 按 start_time 排序，逐对比较相邻 Span 的 input messages。如果 S(i) 的完整 input **不是** S(i+1).input 的前缀（例如 compact/summary 导致历史消息被压缩），则切分为新的 Trajectory。

## 常用查询模式

### 查看某条 message 的所有轨迹
```sql
SELECT traj_id, traj_type, agent_name, model_name_list,
       llm_call_count, total_tokens, finish_reason, traj_tag
FROM flow_aipaas.trae_traj_detail_di
WHERE date = '${date}' AND message_id = '${message_id}'
ORDER BY first_span_time
```

### 模型性能对比
```sql
SELECT model_name_list,
       COUNT(*) AS traj_count,
       AVG(llm_call_count) AS avg_llm_calls,
       AVG(total_tokens) AS avg_tokens,
       AVG(total_duration / 1000000.0) AS avg_duration_sec,
       SUM(CASE WHEN finish_reason = 'stop' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS stop_rate_pct
FROM flow_aipaas.trae_traj_detail_di
WHERE date = '${date}' AND traj_type = 'master'
GROUP BY model_name_list
ORDER BY traj_count DESC
```

### 子 Agent 调用分析
```sql
SELECT agent_name, model_name_list,
       COUNT(*) AS sub_traj_count,
       AVG(llm_call_count) AS avg_calls,
       AVG(total_tokens) AS avg_tokens
FROM flow_aipaas.trae_traj_detail_di
WHERE date = '${date}' AND traj_type = 'sub'
GROUP BY agent_name, model_name_list
ORDER BY sub_traj_count DESC
```

### 异常轨迹分析
```sql
SELECT finish_reason, traj_tag,
       COUNT(*) AS cnt
FROM flow_aipaas.trae_traj_detail_di
WHERE date = '${date}'
GROUP BY finish_reason, traj_tag
ORDER BY cnt DESC
```
