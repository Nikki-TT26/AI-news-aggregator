# libra-gallery-builder 最佳实践

通过 Python 脚本操作 Libra Gallery 指标平台，支持中国机房和海外机房。

> 详细的工作流示例、完整功能列表和参数说明见底层 SKILL 的 `SKILL.md`。本文档仅提供编排层快速参考。

## 环境准备（首次使用）

```bash
cd .trae/skills/libra-gallery-builder/scripts && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## 执行命令时始终使用 venv

```bash
.trae/skills/libra-gallery-builder/scripts/.venv/bin/python .trae/skills/libra-gallery-builder/scripts/libra_gallery_api.py <command>
```

## 环境说明

| 环境 | env 值 | 平台地址 |
|------|--------|----------|
| **中国机房** | `"cn"`（默认） | https://libra-gallery.bytedance.net |
| **海外机房** | `"i18n"` | https://libra-gallery-us.tiktok-row.net |

- 用户提到"海外"/"i18n"/"sg"/"va" 或给出 `libra-gallery-us.tiktok-row.net` 链接 → `env="i18n"`
- 当用户提供 URL 时用 `detect_env_from_url(url)` 自动检测环境，`extract_ticket_id(url)` 提取 ID

## 核心类与自动探测

- `LibraGalleryClient(env="cn")`：封装认证与 HTTP 请求
- `TicketEditor`：指标组增删改操作
- **零配置**：owner、business、apps 等均支持自动探测（显式参数 > config.yaml > API 探测 > 默认值）
- 运行 `detect` 命令可查看当前探测值

## 平台结构

- **需求（Ticket）**→ 数据源（T1/T2/T3...，纯 Hive SQL）→ 指标组（Group）→ 指标 + 维度
- 指标类型：`pv`（求和）和 `uv`（去重计数），**没有 `pv_distinct`**
- 维度类型：`USER_DIMENSION`（用户维度）/ `METRIC_DIMENSION`（指标维度）
- 每个需求最多 10 个指标组

## CLI 查看指标组详情（指标验证场景常用）

| 命令 | 用途 |
|------|------|
| `info <ticket_id_or_url>` | 需求概要和指标组列表 |
| `groups <ticket_id>` | 列出所有指标组 |
| `metrics <ticket_id> <group_index>` | 查看指标的 left/right key_sql 和类型 |
| `dims <ticket_id> <group_index>` | 查看维度定义 |
| `datasources <ticket_id>` | 列出数据源 |
| `datasource-sql <ticket_id> <vt_name>` | 查看数据源完整 SQL |

> **指标验证**：先 `datasource-sql` 理解数据来源，再 `metrics` 看聚合方式。

## 关键注意事项（易错点）

- **数据源 SQL 是纯 Hive SQL**，不带 `Tx:` 前缀；指标/维度引用列时才用 `Tx:column_name`
- **数据源 SQL 必须输出 `date` 字段**（如 `'${date}' AS date`）
- **字符串值必须用单引号**（不能双引号）
- **`cum_start_time` 必须用 `yyyy-MM-dd` 格式**
- **多行 SQL 不要通过 `python -c` 传递**，推荐写入 `.sql` 文件后传路径
- **`save()` 仅保存草稿**，不会上线；保存后自动从服务端重新加载数据
- **`submit_online()` 仅在用户明确说"上线"时调用**
- **列名重命名时必须用 `column_remap` 参数**：`update_data_source_sql("T1", new_sql, column_remap={"old": "new"})`
- **海外机房 Cookie 与国内不通用**，需分别登录
- **save() 有防清空保护**：如果提交数据中 metrics 或 dimensions 为空（但原有数据不为空），`save()` 会自动中止并报错，避免 PUT 全量替换导致数据丢失
- **指标类型 `right_type` 支持 `base_user`**：用于人均指标（PV/base_user），分母为实验组全体用户数，不需要 `right_key_sql`
- **批量修改指标类型前先 dry_run**：修改大量指标的 `right_type` 后建议先 `save(dry_run=True)` 预检查，确认无误后再正式保存
- **Gallery user_unique_id 校验**：数据源 SQL 最终 SELECT 的输出列名中不能包含 `user_id`、`device_id` 字面量（大小写不敏感），需改为 `AS user_unique_id` 或用子查询包裹
- **数据源重命名必须用 `rename_data_source`**：删除一个数据源后将另一个改名（如删 T1、T2→T1），必须调用 `rename_data_source("T2", "T1")`，它会自动更新所有指标/维度中的 `T2:xxx` → `T1:xxx` 引用（包括 `key` 数组和 `key_sql` 字符串字段）。**切勿手动替换**——指标内部有 `sql.left.key`（数组）和 `sql.left.key_sql`（字符串）两套引用，维度有顶层 `key`（数组）和 `key_sql`（字符串），遗漏任一处都会导致 API 保存失败
- **重命名前必须先删除同名数据源**：如果目标 key 已存在（如要把 T2 改成 T1 但 T1 还在），必须先 `remove_data_source("T1")` 再 `rename_data_source("T2", "T1")`，否则报 key 冲突

## 数据源删除+重命名典型流程

```python
# 场景：克隆后只需保留 T2（指标引用 T2:xxx），删除 T1 并把 T2 改成 T1
editor.remove_data_source("T1")         # 先删除
editor.rename_data_source("T2", "T1")   # 再重命名（自动更新所有引用）
editor.save()
```

## 人均指标（PV / base_user）

商业化等场景常用的人均指标，分母为实验组全体用户数（含无行为的用户）：

```python
# 添加新的人均指标
editor.add_metric(0, "人均订单金额", "T1:order_amount", left_type="pv",
                  right_type="base_user",
                  description="SUM(order_amount)/实验组用户数")

# 将已有指标改为人均（通过 update_metric）
editor.update_metric(0, "指标名", right_type="base_user")

# 批量修改建议先 dry_run
editor.save(dry_run=True)  # 确认无误
editor.save()              # 正式保存
```

> **PV/UV vs PV/base_user**：
> - `right_type="uv"` + `right_key_sql`：分母 = 列有值的去重用户数
> - `right_type="base_user"`：分母 = 实验组全体进组用户数

## 维度高级配置速查

```python
editor.update_dimension(0, "维度名称", conf={
    "use_conf": True,
    "use_types": "MDS",          # RPT / MDS / EXTERNAL / RPT_ONLY
    "update_type": "first",      # first / last / t1 / GREATEST
    "enums_update_type": "force", # merge / force / init
})
# 重置: editor.reset_dimension_conf(0, "维度名称")
# 批量重置: editor.reset_dimensions_conf(0, ["维度A", "维度B"])
```

## 典型操作速查

```python
from libra_gallery_api import LibraGalleryClient, TicketEditor, detect_env_from_url, extract_ticket_id

client = LibraGalleryClient()  # 或 LibraGalleryClient(env="i18n")

# 创建新需求
editor = TicketEditor.create_new(client, name="需求名称")

# 加载已有需求
editor = TicketEditor(client, ticket_id)

# 添加数据源（纯 Hive SQL，不带 Tx:）
editor.add_data_source("T1", sql="T1.sql")  # 推荐传 .sql 文件路径

# 添加指标组
editor.add_group("指标组名称", cum_start_time="2025-09-15")

# 添加指标（用 Tx: 引用数据源列）
editor.add_metric(0, "指标名", "T1:col", left_type="pv", right_key_sql="T1:col2", right_type="pv")

# 添加维度
editor.add_dimension(0, "维度名", "T1:col", dim_type="METRIC_DIMENSION")

# 克隆：复制整个需求 / 克隆部分指标组 / 同需求内克隆 / 跨需求克隆 / 版本克隆
TicketEditor.create_from(client, source, new_ticket_name="xx")
TicketEditor.create_from(client, source, "源指标组", new_ticket_name="xx", copy_data_sources=True)
TicketEditor.create_from_snapshot(client, source_ticket_id=id, snapshot_id=30, new_ticket_name="xx")
editor.clone_group("源名", "新名")
target.clone_group_from(source, "源名", "新名", copy_data_sources=True)

# 数据源删除与重命名（克隆后精简数据源）
editor.remove_data_source("T1")
editor.rename_data_source("T2", "T1")  # 自动更新所有 T2:xxx → T1:xxx 引用

# 保存（仅草稿）
editor.save()

# 上线（仅用户明确要求时）
editor.submit_online()
```
