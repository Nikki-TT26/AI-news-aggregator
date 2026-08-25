# trae_conversation_message_map_di

Trae Conversation-Message 映射表，建立 conversation_id 到 message_id 的 1:N 有序映射。除基本映射信息外，还包含每条 message 的 Span 统计、模型列表、经验召回、意图识别、代码语言/框架等汇总信息。

- cn: `flow_aipaas.trae_conversation_message_map_di`
- i18n: `ai_application_coding.trae_conversation_message_map_di`
- 分区字段: date（yyyyMMdd）
- TTL: 14天
- Dorado 任务 (cn): taskId `124834483`
- GUID: `76e7106d-7489-4e91-b165-3db6516f9a33`
- 上游表: `flow_aipaas.trae_agent_fornax_detail_di`
- 设计背景: 从 ODS Span 数据中按 conversation_id+message_id 聚合，建立会话到消息的有序映射，方便从会话维度追踪分析。每天 T+1 刷新，SLA T+1 09:00 前

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| conversation_id | string | 会话 ID |
| message_id | string | 消息 ID |
| message_seq | int | 消息在会话内的顺序号（从 1 开始，按最早出现时间排序） |
| first_span_time | bigint | 该 message 下最早 Span 的 start_time（微秒） |
| last_span_time | bigint | 该 message 下最晚 Span 的 start_time（微秒） |
| span_count | int | 该 message 下的 Span 总数 |
| llm_call_count | int | 该 message 下 LLMCallSpan 的数量 |
| model_names | string | 涉及的模型名称列表（去重，逗号分隔） |
| experience_id | string | 经验 ID |
| experience_content | string | 经验内容 |
| intent | string | 意图标签 |
| code_lang | string | 代码语言 |
| code_framework | string | 代码框架 |
| code_comp_feedback_click | string | Code completion feedback click result |
| log_id | string | 日志 ID，与 message_id 一一对应 |

> 分区键: date (string, yyyyMMdd)

## 常用查询模式

### 查找会话下所有 message
```sql
SELECT conversation_id, message_id, message_seq,
       llm_call_count, model_names, intent, code_lang
FROM flow_aipaas.trae_conversation_message_map_di
WHERE date = '${date}' AND conversation_id = '${conversation_id}'
ORDER BY message_seq
```
