# bytedcli 命令调用方式

`bytedcli` 未安装在系统 PATH 中，**不能直接执行 `bytedcli ...`**。必须通过 `npx` 调用：

```bash
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest <command> [options]
```

> **重要**：本知识库所有文档中的 `bytedcli` 均为简写。实际执行时，必须替换为上述 `npx` 完整调用方式。在转发给底层 SKILL（bytedance-hive、bytedance-dorado、bytedance-tqs 等）时，底层 SKILL 会自行处理 `bytedcli` 的调用方式，无需在转发指令中特别说明。但若由编排层直接执行 shell 命令（如 TQS 查询），则必须使用 `npx` 方式。

## 站点切换

通过 `--site` 参数或 `BYTEDCLI_CLOUD_SITE` 环境变量切换 ByteCloud 站点：

| 站点值 | 说明 | SSO | 备注 |
|--------|------|-----|------|
| `cn` | 国内生产（默认） | `sso.bytedance.com` | |
| `i18n-bd` | ByteIntl 国际站 | `sso.bytedance.com` | 通常复用 cn 登录态 |
| `i18n-tt` | TikTok 国际站 | `sso.tiktok-intl.com` | 需单独登录 |
| `eu-ttp` | EU TTP 站 | `sso.tiktok-intl.com` | 需单独登录 |
| `boe` | BOE 测试 | `test-sso.bytedance.net` | |

> **认证隔离按 SSO 环境生效**：`cn`/`i18n-bd`（ByteDance SSO）共享登录态；`i18n-tt`/`eu-ttp`（TikTok SSO）需单独 `auth login`。

切换站点示例：

```bash
# 使用 --site 参数
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest --site i18n-tt auth status

# 使用 BYTEDCLI_CLOUD_SITE 环境变量（推荐）
BYTEDCLI_CLOUD_SITE=i18n-tt NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth status
BYTEDCLI_CLOUD_SITE=i18n-tt NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth login
```

> **推荐使用 `BYTEDCLI_CLOUD_SITE` 环境变量**：避免 `--site` 参数位置问题（`--site` 是全局参数，必须放在 `<command>` 前面）。

## TQS 查询的完整命令示例

注意 npx 替换：

```bash
# 国内查询
(source .env.local && NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest tqs execute --sql "SELECT ...")

# 海外查询
(source .env.sg.local && NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest tqs execute --sql "SELECT ...")
```

## JSON 输出

```bash
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest --json <command> [options]
```

注意：`--json` 是全局参数，必须放在 `<command>` 前面，例如 `--json auth status`，不能写成 `auth status --json`。
