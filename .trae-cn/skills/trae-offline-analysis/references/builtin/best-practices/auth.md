# 认证管理

本系统涉及几种认证方式，不同 SKILL 依赖不同的认证机制：

| 认证类型 | 适用 SKILL | 有效期 | 站点/环境 | 刷新方式 |
|----------|-----------|--------|-----------|---------|
| ByteCloud Auth（ByteDance SSO） | aeolus / dorado / hive(cn) / libra / tqs(cn) | ~12h | `cn` / `i18n-bd`（共享） | `bytedcli auth login` |
| ByteCloud Auth（TikTok SSO） | hive(sg) / tqs(sg) | ~12h | `i18n-tt` / `eu-ttp`（需单独登录） | `BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login` |
| TQS 凭证文件（.env.local / .env.sg.local） | tqs(cn / sg) | 长期有效 | — | 手动配置到项目根目录 |
| Chrome Cookie + x-titan-token | aeolus-dataset-manager | ~7天 | — | `client.refresh_token()` 或自动从 Chrome 读取 |
| Chrome Cookie (bd_sso_3b6da9 JWT) | libra-gallery-builder | ~7天 | — | `client.refresh_cookie()` 或自动从 Chrome 读取 |

- aeolus-dataset-manager 脚本路径：`.trae/skills/aeolus-dataset-manager/scripts/`
- libra-gallery-builder 脚本路径：`.trae/skills/libra-gallery-builder/scripts/`

## SSO 环境隔离规则

bytedcli 基于 **ByteCloud Auth SDK** 管理认证，SSO Token 按 SSO 环境独立缓存（共 3 组）：

| SSO 环境 | 对应站点 | SSO 域名 | 说明 |
|----------|---------|---------|------|
| **bytedance** | `cn`、`i18n-bd` | `sso.bytedance.com` | 国内 + ByteIntl 国际站，共享登录态 |
| **tiktok** | `i18n-tt`、`eu-ttp` | `sso.tiktok-intl.com` | TikTok 国际站 + EU TTP，需单独登录 |
| **test** | `boe` | `test-sso.bytedance.net` | BOE 测试环境 |

**关键点**：
- `cn` 和 `i18n-bd` 通常只需登录一次（共享 ByteDance SSO）
- `i18n-tt` 需要**单独**执行 `auth login`（使用 TikTok SSO）
- 通过 `--site` 参数或 `BYTEDCLI_CLOUD_SITE` 环境变量切换站点
- 操作目标站点前，应先检查该站点的认证状态

## 站点切换方式

两种等价方式：

```bash
# 方式 1：--site 参数
bytedcli --site i18n-tt auth status
bytedcli --site i18n-tt auth login

# 方式 2：BYTEDCLI_CLOUD_SITE 环境变量（推荐，避免参数位置问题）
BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth status
BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login
```

可用站点值：`cn`（默认）、`i18n-bd`、`i18n-tt`、`eu-ttp`、`boe`

## 预检流程

在执行跨 SKILL 工作流之前、或用户要求检查认证状态时，应一次性检查所有认证，避免中途因认证过期导致流程中断。

> **⚠️ 工具使用注意事项**：
> - `.env.local`、`.env.sg.local` 位于项目根目录，但仍以 `.` 开头（dotfile），**Glob 工具默认不匹配以 `.` 开头的文件**，因此必须使用 `ls -la` 命令（通过 RunCommand 工具执行）检查。`token.txt`、`cookie.txt` 同样建议使用 `ls -la` 检查（可一并查看文件修改时间以判断是否过期）。
> - `bytedcli` 未安装在系统 PATH 中，预检命令中的 `bytedcli` 均为简写，实际执行时必须替换为 `NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest`（详见 `bytedcli-setup.md`）。

**完整预检命令序列**（Step 2/3/4 可并行执行）：

**Step 1 — bytedcli SSO 认证**（ByteCloud Auth SDK，一次性检查所有 SSO 环境）：

```bash
# 检查 ByteCloud Auth 登录状态 + 所有 SSO 环境的 session/token 状态
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth status
```

- 输出中查看 `bytedance (sso.bytedance.com)` 状态 → 影响 aeolus / dorado / hive(cn) / libra / tqs(cn)
- 输出中查看 `tiktok (sso.tiktok-intl.com)` 状态 → 影响 hive(sg) / tqs(sg)
- 若需单独确认海外站点认证：`BYTEDCLI_CLOUD_SITE=i18n-tt NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth status`
- 若某个 SSO 显示 `✗`，需运行对应的 login 命令刷新：
  - ByteDance SSO（cn / i18n-bd）：`NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth login`
  - TikTok SSO（i18n-tt / eu-ttp）：`BYTEDCLI_CLOUD_SITE=i18n-tt NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth login`

> **登录方式选择**：
> - 默认 `auth login` 使用 ByteCloud Auth 二维码登录
> - `auth login --session` 会优先复用本地已有的 SSO browser session；本地 session 不可用时按站点默认方式获取新 session
> - `auth login --session --auto` 自动选择最佳登录路径（优先 browser-cookie，回退到 qr）
> - Agent/脚本场景推荐 `--json auth login --begin` + `--json auth login --complete <token>` 非阻塞登录

**Step 2 — TQS 凭证文件**（可与 Step 3、4 并行）：

```bash
# 检查文件是否存在（必须用 ls -la，不能用 Glob）
ls -la .env.local .env.sg.local
```

确认文件存在后，验证变量是否正确加载：

```bash
# 验证国内凭证
(source .env.local && echo "TQS_APP_ID=$TQS_APP_ID" && echo "TQS_APP_KEY=${TQS_APP_KEY:+已配置}")

# 验证海外凭证
(source .env.sg.local && echo "TQS_APP_ID=$TQS_APP_ID" && echo "TQS_APP_KEY=${TQS_APP_KEY:+已配置}" && echo "TQS_CLUSTER=$TQS_CLUSTER")
```

- `.env.local` 缺失 → 国内 TQS 查询不可用，需配置 `TQS_APP_ID` 和 `TQS_APP_KEY`
- `.env.sg.local` 缺失 → 海外 TQS 查询不可用，需配置 `TQS_APP_ID`、`TQS_APP_KEY`、`TQS_CLUSTER=sg`

**Step 3 — aeolus-dataset-manager 认证**（可与 Step 2、4 并行）：

```bash
# 检查 token.txt 是否存在及修改时间（有效期约 7 天）
ls -la .trae/skills/aeolus-dataset-manager/scripts/token.txt
```

- 文件存在且修改时间在 7 天内 → ✅ 正常
- 文件不存在 → 运行时脚本会自动从 Chrome 浏览器读取（需确保 Chrome 已登录 Aeolus）
- 文件超过 7 天 → 可能过期，运行时会自动尝试从 Chrome 刷新

**Step 4 — libra-gallery-builder 认证**（可与 Step 2、3 并行）：

```bash
# 检查 cookie.txt 是否存在及修改时间（有效期约 7 天）
ls -la .trae/skills/libra-gallery-builder/scripts/cookie.txt
```

- 文件存在且修改时间在 7 天内 → ✅ 正常
- 文件不存在 → 运行时脚本会自动从 Chrome 浏览器读取（需确保 Chrome 已登录 Libra Gallery）
- 文件超过 7 天 → 可能过期，运行时会自动尝试从 Chrome 刷新

> **路径说明**：`.env.local` / `.env.sg.local` 位于项目根目录；`token.txt` 位于 `.trae/skills/aeolus-dataset-manager/scripts/` 下；`cookie.txt` 位于 `.trae/skills/libra-gallery-builder/scripts/` 下。查询时必须通过 `source` 显式加载凭证文件，不依赖 bytedcli 从 cwd 自动加载（subagent 执行时 cwd 不确定，自动加载不可靠）。

## 常见认证问题

| 问题 | 原因 | 解决方式 |
|------|------|---------|
| `Not authenticated` | ByteCloud Auth 未登录 | `bytedcli auth login` |
| 海外 Hive 查询 401 | TikTok SSO 未登录 | `BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login` |
| `auth status` 正常但 API 报 401 | 站点不匹配（如用 cn token 访问 sg 服务） | 确认操作的 `--site` / `--region` 与登录站点一致 |
| Session 过期频繁 | ByteCloud Auth token 有效期 ~12h | 可用 `auth login --session` 保存浏览器 session 延长复用 |
| 开发机/远程环境无法登录 | 无法访问本机浏览器 cookie | 本地 `auth export-session --out <path>`，远程 `auth import-session --from <path>` |
