# trae_message_traj_map_di

消息到轨迹的映射表，记录 message_id → master traj_id 的 1:N 有序映射。仅包含 master 类型的轨迹 ID，sub 轨迹需通过 trae_traj_detail_di 表的 parent_traj_id 关联查询。

- cn: `flow_aipaas.trae_message_traj_map_di`
- i18n: `ai_application_coding.trae_message_traj_map_di`
- 分区字段: date（yyyyMMdd）
- TTL: 14天
- GUID: `7359db77-86cc-4ae9-b25a-c3ae10ce7e82`
- 上游表: `flow_aipaas.trae_agent_fornax_detail_di`
- 关联表: `flow_aipaas.trae_traj_detail_di`（通过 traj_id 关联查询轨迹详情）
- 设计背景: 提供 message_id 到 master 轨迹的快速映射，方便分析每条消息产生了多少段轨迹（traj 切分情况）。每天 T+1 刷新，SLA T+1 09:00 前

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| conversation_id | string | 会话 ID |
| message_id | string | 消息 ID |
| traj_id_list | string | 主链路轨迹 ID 列表，按顺序排列（JSON 数组） |

> 分区键: date (string, yyyyMMdd)
