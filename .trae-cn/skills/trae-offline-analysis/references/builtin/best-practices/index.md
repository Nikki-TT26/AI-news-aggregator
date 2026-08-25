# 底层 SKILL 最佳实践 — 索引

按需加载对应的子文件，避免全量加载。

| 文件 | 内容 | 加载时机 |
|------|------|----------|
| [bytedcli-setup.md](./bytedcli-setup.md) | bytedcli 命令调用方式（npx 前缀） | 每次执行时必须加载 |
| [auth.md](./auth.md) | 认证管理（类型、预检流程、刷新方式） | 首次执行或需要预检时加载 |
| [bytedance-hive.md](./bytedance-hive.md) | Hive 表搜索、Schema 查询、建表、血缘查询 | 涉及 bytedance-hive 时加载 |
| [bytedance-dorado.md](./bytedance-dorado.md) | Dorado 任务管理、SQL 更新、项目 ID 映射 | 涉及 bytedance-dorado 时加载 |
| [bytedance-tqs.md](./bytedance-tqs.md) | TQS SQL 校验与执行、凭证管理、日期约定 | 涉及 bytedance-tqs 时加载 |
| [bytedance-aeolus.md](./bytedance-aeolus.md) | Aeolus BI 数据集与查询 | 涉及 bytedance-aeolus 时加载 |
| [bytedance-libra.md](./bytedance-libra.md) | Libra A/B 实验详情与报告 | 涉及 bytedance-libra 时加载 |
| [aeolus-dataset-manager.md](./aeolus-dataset-manager.md) | Aeolus 数据集 CRUD（Python API） | 涉及 aeolus-dataset-manager 时加载 |
| [libra-gallery-builder.md](./libra-gallery-builder.md) | Libra Gallery 指标组全流程操作（Python API） | 涉及 libra-gallery-builder 时加载 |
| [opencli-libra-metric-config.md](./opencli-libra-metric-config.md) | opencli browser 查看/配置 Libra 指标组设置（负向指标等） | 涉及指标组前端配置（负向指标）时加载 |
