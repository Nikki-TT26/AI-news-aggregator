# aeolus-dataset-manager 最佳实践

通过 Python 脚本操作 Aeolus（风神）平台数据集，支持国内（cn）和海外（sg）机房。

> 详细的工作流示例、完整功能列表和参数说明见底层 SKILL 的 `SKILL.md`。本文档仅提供编排层快速参考。

## 环境准备（首次使用）

```bash
cd .trae/skills/aeolus-dataset-manager/scripts && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## 执行命令时始终使用 venv

```bash
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py <command>
```

## 环境说明

| 区域 | region 值 | 平台地址 | 默认 app_id |
|------|-----------|----------|-------------|
| **国内** | `"cn"`（默认） | https://data.bytedance.net/aeolus | 1006036 |
| **海外 SG** | `"sg"` | https://aeolus-sg.tiktok-row.net | 802699 |

- 用户提供 Aeolus 链接时，`parse_aeolus_url(url)` 自动提取 `app_id`、`data_set_id` 和 `region`
- `extract_dataset_id(url_or_id)` 可从 URL 或纯数字提取 ID

## 核心类与自动探测

- `AeolusClient(region="cn")`：封装认证与 HTTP 请求
- `DatasetEditor`：数据集增删改操作
- **零配置**：owner、parent_id、yarn_name 均支持自动探测（显式参数 > config.yaml > API 探测 > 默认值）
- 运行 `detect` 命令可查看当前探测值

## 关键注意事项（易错点）

- **SQL 日期变量**：必须用 `${date}`(yyyyMMdd) 或 `${DATE}`(yyyy-MM-dd)，**不要用 Jinja `{{ ds }}`**
- **SQL Schema 解析非常耗时**（>300s 甚至超时），**强烈建议手动构造 `source_fields` 跳过解析**
- **prepType 类型映射**：Hive `bigint` → prepType `long`（不能直接用 `bigint`，否则报"prepare中间类型转引擎类型失败"）
- **创建后需发布**：`create_new` 创建后状态为"初始化"，需 `publish=True` 才能上线
- **`update()` 默认发布**：`publish=True` 是默认行为，`publish=False` 仅保存草稿
- **`update()` 保留已有配置**：参数为空时不会用 config.yaml 默认值覆盖已有配置
- **维度指标类型**：`mapType=0` 为维度，`mapType=1` 为指标
- **p_date 分区字段**：脚本自动添加，nodeConf.fields 中的 p_date 会自动跳过
- **同步状态码**：`syncStatus`: `1`=等待, `2`=未开始, `3`=运行中, `4`=成功, `5`=失败

## 海外 SG 注意事项

- **app_id 不同**：SG 默认 `802699`，`AeolusClient(region='sg')` 自动使用
- **parent_id 不同**：SG 和 CN 完全不同，脚本自动探测
- **海外表库名差异**：国内 `flow_aipaas.xxx` 在海外可能是 `ai_application_coding.xxx`
- **clusterName = "sg"**：脚本自动设置
- **source_dataset_id 跨区域限制**：只能引用同区域数据集

## 典型操作速查

```python
import sys
sys.path.insert(0, '.trae/skills/aeolus-dataset-manager/scripts')
from aeolus_api import AeolusClient, DatasetEditor, extract_dataset_id, parse_aeolus_url

client = AeolusClient()                # 国内
# client = AeolusClient(region='sg')   # 海外 SG

# 创建新数据集（推荐手动构造 source_fields 跳过 Schema 解析）
source_fields = [
    {"name": "user_id", "type": "string", "prepType": "string",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "cnt", "type": "bigint", "prepType": "long",  # bigint → long
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
    {"name": "date", "type": "string", "prepType": "string",
     "isSourceTableField": False, "isSelect": True, "isDynamicPartition": False},
]
editor = DatasetEditor.create_new(client, name="my_dataset",
    query="SELECT user_id, cnt, date FROM db.table WHERE date = '${date}'",
    source_fields=source_fields, publish=True)

# 复制已有数据集
editor = DatasetEditor.create_from(client, source_dataset_id=5428964,
    new_name="copied", publish=True)

# 修改已有数据集
editor = DatasetEditor(client, data_set_id=5428964)
editor.update(new_query="SELECT ...", publish=True)

# 删除
editor = DatasetEditor(client, 5429028)
editor.delete()            # 安全删除
editor.delete(force=True)  # 强制删除

# 回溯（补历史数据）
editor = DatasetEditor(client, 5492281)
editor.backfill(start_date="2026-04-20", end_date="2026-04-23")

# 查看同步状态
sync_data = editor.get_sync_status()

# 查看详情
summary = editor.get_summary()
query = editor.get_query()

# 刷新 Token
client.refresh_token()
```

## CLI 速查

```bash
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py detect
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py --region sg detect
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py info 5428964
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py list [owner]
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py backfill 5492281 2026-04-20 2026-04-23
.trae/skills/aeolus-dataset-manager/scripts/.venv/bin/python .trae/skills/aeolus-dataset-manager/scripts/aeolus_api.py sync-status 5492281
```
