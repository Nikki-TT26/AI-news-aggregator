# bytedance-hive 最佳实践

数据资产搜索与管理入口。

| 操作             | 命令                                                            |
| -------------- | ------------------------------------------------------------- |
| 搜索表            | `bytedcli hive search --query "<keyword>" --type HiveTable`   |
| 获取表结构          | `bytedcli hive detail <db> <table>`                           |
| 按 GUID 获取实体    | `bytedcli hive get <guid>`                                    |
| 查看分区行数         | `bytedcli hive rows <db> <table>`                             |
| 查找 Dorado 生产任务 | `bytedcli hive detail <db> <table>`（返回中含 producerDoradoTasks） |
| 查看数据血缘         | `bytedcli hive lineage <guid> --depth <N>`（需先通过 `detail` 或 `get` 获取表的 GUID） |
| 建表             | `bytedcli hive create --database <db> --table <table>`        |

- `detail` 命令返回字段名、类型、注释等完整 schema 信息，以及上游 Dorado 生产任务 ID
- **海外查询**：加 `--region sg`，需 TikTok SSO 认证（`bytedcli --site i18n-tt auth login`）
- **注意**：sg region 部分库（如 `ai_application_coding`）的 `detail`/`get` 可能不返回字段列表（字段嵌套在 `attributes.fields` 中而非顶层 `fields`），此时可通过 `hive search` 看到部分字段信息，或直接用 TQS `DESCRIBE` 查看表结构
- **血缘查询**：`lineage` 命令不支持 `--direction` 参数，返回的是双向完整血缘图（上游+下游）。`--depth` 控制追溯层数，一般 1-2 层即可。血缘结果中会包含 DoradoTask 等中间节点，需要从中筛选 HiveTable 类型的节点来分析表间依赖

## HiveQL LIKE 通配符注意事项

在 Hive 的 `LIKE` 操作符中，有两个通配符：

| 通配符 | 含义 | 等价于 shell 中的 |
|--------|------|-------------------|
| `%`    | 匹配任意数量字符（含零个） | `*` |
| `_`    | 匹配任意**单个**字符 | `?` |

### 失败案例（trace: 129caad32bbd14e3de474c617d1bc49b）

**问题**：Agent 想在 Hive 表中模糊匹配包含 `c_o`（字面下划线）的字符串，使用了：

```sql
WHERE col LIKE '%c_o%'
```

**实际结果**：匹配到了 `cloude` 等不含下划线的字符串，因为 `_` 被 Hive 解释为单字符通配符，`c_o` 匹配了 `clo`（`_` 匹配了 `l`）。

**正确写法**：需要用反斜杠转义下划线，使其作为字面字符匹配：

```sql
WHERE col LIKE '%c\_o%'
```

**规则总结**：
- 在 HiveQL `LIKE` 中，若需匹配字面下划线 `_`，必须写成 `\_`
- 同理，若需匹配字面百分号 `%`，必须写成 `\%`
- 这与 shell glob 的 `*`/`?` 通配符不同，编写 SQL 时切勿混淆