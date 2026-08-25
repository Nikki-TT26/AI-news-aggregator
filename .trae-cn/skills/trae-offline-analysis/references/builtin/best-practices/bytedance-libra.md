# bytedance-libra 最佳实践

A/B 实验平台。

| 操作     | 命令                                          |
| ------ | ------------------------------------------- |
| 查看实验详情 | `bytedcli libra experiment get --flight-id <flight_id>` |
| 列出可用指标组 | `bytedcli libra experiment report --flight-id <flight_id>` |
| 获取指标组报告 | `bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id>` |
| 获取逐日趋势 | `bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --trend` |
| 获取指标组详情 | `bytedcli libra metric-group get --id <metric_group_id>` |
| 分维度报告 | `bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id> --list-dimensions`，再用 `--dimension <dimension_id>` |
| 搜索实验 | `bytedcli libra experiment list --app-id -1 --search "关键词"` |

## 从 Libra URL 解析参数

Libra 报告 URL 格式：`https://data.bytedance.net/libra/flight/<flight_id>/report/main?category=watching&group_id=<metric_group_id>`

- `flight_id`：URL 路径中的数字
- `metric_group_id`：URL query 参数 `group_id` 的值

## 报告模式

| 模式 | 参数 | 含义 |
|------|------|------|
| total（默认） | `--merge-type total` | 累计值，含 P-Value 和显著性判断 |
| sum | `--merge-type sum` | 日均汇总，仅有 Diff%，可能缺少 P-Value |
| avg | `--merge-type avg` | 平均值 |

> **注意**：当 `total` 模式下指标数据为空时，可尝试 `sum` 模式获取数据（如指标组新关注时间较短，累计数据可能未产出）。

## 报告中的显著性判断

报告中 `Sig` 列按学术惯例分级：`*` p<0.05 / `**` p<0.01 / `***` p<0.001。

## 指标验证工作流

当需要独立验证 Libra 指标的正确性时，推荐按以下流程操作：

1. **获取实验信息**：`bytedcli libra experiment get --flight-id <flight_id>`，确认 vid（版本 ID）、流量比例、实验时间
2. **获取 Libra 报告数据**：`bytedcli libra experiment report --flight-id <flight_id> --metric-group <metric_group_id>`，记录 Mean、Diff%、P-Value
3. **查看 Gallery 指标定义**：通过 `libra-gallery-builder` 的 CLI 查看指标组的数据源 SQL 和指标定义（详见 `libra-gallery-builder` 最佳实践）
4. **构造验证 SQL**：
   - 使用 Libra 标准进组口径表 `origin_log.dwd_abtest_vid_log_other_apps_df` 获取实验各组的 did 列表
   - 将进组用户与 Gallery 数据源的底表做 JOIN，按 v0/v1 分组计算指标
5. **通过 TQS 执行验证 SQL**，对比结果与 Libra 报告的 Diff%
6. **口径差异容忍度**：由于 Gallery 有 CUPED 校正、日期范围差异等因素，TQS 验证结果与 Libra 报告的 Diff% 可能有 0.1~0.5pp 的偏差，但方向应一致
