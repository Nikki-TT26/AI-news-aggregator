---
name: bytedance-auth
description: "Operate bytedcli authentication flows. Use when user asks to login/logout, check auth status, fetch user info, or prepare ByteCloud Auth for ByteDance internal APIs."
---

# bytedcli 认证/SSO

## 如何调用 bytedcli

推荐：先全局安装一次，后续所有命令直接调用 `bytedcli`。

```bash
# 推荐方式：先全局安装，后续直接调用 bytedcli
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npm install -g @bytedance-dev/bytedcli@latest
bytedcli <command> [options]
```

```bash
# Fallback：仅在无法全局安装时使用 npx 临时执行
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest <command> [options]
```

## When to use

- 登录/登出
- 查看登录状态或用户信息
- 获取 SSO/Bytecloud token

## 前置条件

- 使用通用调用方式：`references/invocation.md`

> 执行前缀见 `references/invocation.md`；下面示例直接写 `bytedcli`。

## Before login: 先复用，不要直接 login

`bytedcli auth login` 不是无害命令——它按当前 `--site` 触发一轮新的 OAuth/扫码/浏览器交互，**默认 `--site` 是 `cn`**。下面三种情况非常常见，直接 `auth login` 会引发不必要的重新认证：

- 用户实际工作在 i18n（`i18n-tt`、`eu-ttp` 等）站点，但没设 `BYTEDCLI_CLOUD_SITE`，也没传 `--site`。直接 `bytedcli auth login` 会把凭证写到 `cn` 那一份，下次操作 i18n 仍然提示「未认证」。
- 默认 `auth login`（不带 `--session`）其实是幂等的：本地凭证有效时直接打印 `Already authenticated as ...` 并 return。如果没意识到这一点，会把它当成「会重新弹码」的命令而提前回避或反复执行。
- 同一 SSO 群组下 `cn` 与 `i18n-bd` 共享登录态、`i18n-tt` 与 `eu-ttp` 共享登录态。已登 `cn` 的用户访问 `i18n-bd` 通常不需要重新登。

执行 login **之前**先按下面顺序排查：

```bash
# 1. 当前默认 site 是否已认证（不会触发登录）
bytedcli --json auth status

# 2. 若 status=need_login，再分别按候选 site 查一遍，找出能复用的
BYTEDCLI_CLOUD_SITE=cn bytedcli --json auth status
BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli --json auth status
BYTEDCLI_CLOUD_SITE=i18n-bd bytedcli --json auth status

# 3. 确认目标 site 真的不可用后，才执行 login，并显式带上 --site
BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login
```

i18n 员工建议把 `export BYTEDCLI_CLOUD_SITE=i18n-tt` 写进 shell rc，避免每条命令都漏带 `--site`。

## Login 失败时先区分网络与认证

`auth login` 返回 DNS 解析失败、连接超时/拒绝、代理或 TLS 错误等网络类错误时，不要视为凭证失效，也不要反复触发新的登录流程：

1. 如果命令由 Agent 在沙盒中执行，使用宿主提供的提权/本机执行机制，在沙盒外原样重试同一条命令；保留原 `--site`、`--session` 等参数。
2. 如果在本机重试仍是网络类错误，明确提示用户当前网络、代理或目标站点不可达，并在网络恢复后重试；不要执行 `auth logout`、`auth clear` 或重复 `auth login`。
3. 对 `--begin` / `--complete` 非阻塞流程，网络失败不表示 challenge 失效。网络恢复后继续使用原 `complete_token` 执行 `--complete`；只有服务明确返回 `expired` 时才重新执行 `--begin`。
4. 只有 `auth status` 或登录服务明确表明凭证无效、未认证或 challenge 已过期时，才重新触发登录。

## Quick start

```bash
bytedcli auth login
bytedcli auth login --session
bytedcli auth login --session --feishu
bytedcli auth login --session --auto
bytedcli auth login --session --session-method browser-cookie --browser vivaldi --yes
bytedcli auth login --session --session-method interactive-browser --yes
bytedcli --site i18n-bd --json auth login --session --session-method interactive-browser --yes
bytedcli auth login --session --session-method password --username demo.user
bytedcli auth login --session --session-method password --username demo.user --mfa-method email
bytedcli auth export
bytedcli auth export --out ~/sample-bytedcli-backup.json.gz
bytedcli auth import --from ~/sample-bytedcli-backup.json.gz
bytedcli auth import --from ~/sample-bytedcli-backup.json.gz --dry-run
bytedcli auth clear --dry-run
bytedcli auth clear --yes
bytedcli --json auth login --begin
bytedcli --json auth login --complete <token>
bytedcli auth login --no-terminal-qr
bytedcli auth login --qr-image
bytedcli --json auth login
bytedcli auth status
bytedcli auth userinfo
bytedcli auth logout
bytedcli --site i18n-tt auth app set --access-key-id sample-ak
bytedcli --site i18n-tt auth app status --refresh
bytedcli --site i18n-tt auth app clear --yes
bytedcli auth get-bytecloud-jwt-token
bytedcli auth get-codebase-jwt-token
```

## 单次 CLI 调用使用指定用户 JWT

当调用方已经持有另一个用户的 ByteCloud person-account JWT，并且明确要让本次命令使用
该用户的 ByteCloud RBAC 时，使用全局 `--bytecloud-user-jwt-file`。它必须放在 domain
之前，并同时显式指定 `--site`：

```bash
# 文件在 POSIX 上必须为 owner-only（例如 0600/0400），内容只能是一条 JWT
bytedcli --site cn --bytecloud-user-jwt-file ./sample-user.jwt \
  --json bits release get --ticket-id <release-ticket-id>

# `-` 表示从 stdin 读取；shell history 只记录变量名，不记录 JWT 值
printf '%s' "$BORROWED_BYTECLOUD_JWT" | bytedcli --site cn --bytecloud-user-jwt-file - \
  --json auth userinfo
```

- 不要生成或使用 `--jwt <token>`：明文 JWT 会进入 shell history 和进程参数。
- 该 JWT 只在当前命令的异步作用域中存在，不落盘、不输出；优先级高于
  `BYTEDCLI_USER_CLOUD_JWT`、JWT override 和本地 session。
- `--as app` / `BYTECLOUD_AUTH_AS=app` 与该参数互斥；site 不匹配、未知 host、过期或无效 JWT 都不会回退到本地用户。
- 该能力只替换通过 `SSOClient` 解析 ByteCloud user JWT 的请求。Browser cookie、Titan、PAT、
  平台专用 token及业务 payload 的 `username` / `operator` 不会自动切换。外部 companion 默认不继承；只有显式解析并等待 child 的受审 proxy 才会转交。
- 共享 MCP tools 不接受该参数（包括 raw `args` / `run_command`），避免 MCP 读取本地 JWT 文件或占用协议 stdin；需要借用身份时直接运行 CLI。
- 在 `auth` domain 中只允许 `status`、`userinfo` 和 token 读取；`login`、`logout`、`app`、session/override 管理仍操作本机凭据，CLI 会拒绝用 borrowed JWT 包裹这些写操作。
- 使用 stdin 时，目标命令不能同时把 stdin 用作业务输入；这种场景改用权限安全文件。

## Agent 非交互式飞书 session 登录

当目标命令要求 Feishu/People web session，且当前环境不能阻塞等待扫码时：

1. 先让用户准备好手机飞书，再执行 `bytedcli --json auth login --begin --session --feishu`。飞书二维码有效期很短，不要提前生成后长时间等待。
2. 把返回的 `qr_image_path` 图片提供给用户，明确要求用户使用**手机飞书扫码并确认**。不要把 `lark_applink_url` 当成完成 CLI 登录的入口；它只在点击方客户端打开 OAuth 页面，不会批准 CLI 正在轮询的二维码 challenge。
3. 用户扫码后，立即反复执行 `bytedcli --json auth login --complete <complete_token>`，直到 `login_status` 为 `success`。`pending` 只表示尚未批准，不能当作登录成功。
4. 若返回 `login_status: expired`，立即执行返回的 `retry_command` 生成新二维码，再让用户扫码；不要继续轮询旧 token。
5. JSON pending 输出和 `qr_image_ready` 事件中的 `required_action: scan_qr`、`required_action_app: feishu` 是 Agent 的动作依据；`lark_applink_completes_cli_login: false` 表示链接不能替代扫码，`qr_code_is_short_lived: true` 表示应立即展示并完成扫码。

本地 TTY 场景继续直接使用 `bytedcli auth login --session --feishu`，CLI 会显示终端二维码并阻塞等待，无需改走非阻塞流程。

## Notes

- 未登录会提示 `Not authenticated`
- 需要结构化输出加 `--json`（全局选项，放在子命令之前，如 `bytedcli --json auth status`）
- `auth login --session` 在未显式传入 `--session-method` 或 `--browser` 时，会先通过 CAS 换票探活，并只复用确实签发 service ticket 的本地 SSO browser session；登录页跳转或明确 4xx 会视为失效，网络错误、5xx 与异常协议响应会直接报错且不会清理本地 session。显式传入 `--session-method` 或 `--browser` 会跳过旧 session 复用，按指定方式重新获取 session；`--begin --session --session-method qr` 同样会创建新的二维码 challenge
- `auth login --session --feishu` 只在 `cn` 站点可用，会切到飞书二维码 / OAuth 路径；阻塞式二维码路径会复用同一次飞书扫码，同时准备 SSO browser session 和额外的 Feishu web session。JSON 模式下，非 `qr` 的 session method 可以复用已有 Feishu web session，但不能新建 Feishu web session；需要新建时改用 `--session-method qr`，或去掉 `--json` 以展示额外的飞书二维码。已有 Feishu web session 探活只有在明确 4xx 或登录跳转时才判为失效；网络错误、5xx 与异常协议响应会报错并保留本地 session
- 普通 SSO 二维码链路可能包含 `lark_applink_url`，用于在 PC 飞书打开同一个二维码页面；`--session --feishu` 的 applink 只会在点击方客户端打开 OAuth 页面，不能批准 CLI challenge。Agent 必须以 `qr_image_path` / `required_action` 为准，引导用户用手机飞书扫码
- 默认执行 `auth login --session` 且没有通过 CAS 校验的可复用 session 时，CLI 会使用 `qr` 获取新 session；如果当前站点不支持 QR，交互终端下会弹出 `qr`/`browser-cookie`/`interactive-browser`/`password` 菜单让用户临时选一个，并提示下次加 `--auto` 让 CLI 自动挑一条可用路径；`qr` 在所有 site 上都可以显式尝试，但它是否可用取决于具体账号/环境，部分用户可能失败
- 显式加上 `--auto` 后，CLI 才会自动选择一条 session 登录路径：若检测到本机浏览器 cookie store，会优先尝试 `browser-cookie`；否则回退到 `qr`。在 `cn` 站点，browser-cookie miss 后会直接回退到普通 SSO `qr`；只有显式加 `--feishu` 才会走飞书扫码路径。其他站点的 `--auto` 才会继续回退到 `interactive-browser`。但在 macOS 的 JSON/非交互环境中，如果没有显式 `--yes`，CLI 会避免无提示触发 Keychain 访问，改为回退到 `qr`
- 显式选择 `browser-cookie` 时，CLI 会检测本机支持的浏览器 cookie store；如果发现多个，会继续让用户选择具体浏览器；如果只有一个，则直接使用该浏览器。显式 `browser-cookie` 失败时不会再自动回退到 `interactive-browser`；若需要这种兜底行为，请改用 `--auto`，或显式切到 `--session-method interactive-browser`。显式选择 `browser-cookie` 或 `interactive-browser` 时，CLI 会先说明即将执行的动作，再要求二次确认；在 JSON/非交互环境中，需要显式追加 `--session-method` 或 `--auto`，其中显式 `browser-cookie` / `interactive-browser` 都需要 `--yes`，而 `--browser` 只在可能同时检测到多个支持浏览器时才需要
- Linux 上同时没有 `DISPLAY` 与 `WAYLAND_DISPLAY` 时，`interactive-browser` 只会为 ByteDance SSO 自动使用 headless Chrome；必要时用 `BYTEDCLI_BROWSER_EXECUTABLE_PATH` 指向可执行的 Chrome/Chromium。CLI 只会把未登录的 SSO 页面写入权限为 `0600` 的 PNG，不会截取登录后的业务页面；`--qr-image [path]` 可指定路径。JSON 模式会立即在 stderr 发出 `qr_image_ready` 事件，成功结果也会返回 `qr_image_path`。TikTok SSO 是账号密码登录页，静态截图无法安全完成登录：无 GUI 时会立即报 `AUTH_INTERACTIVE_BROWSER_GUI_REQUIRED`，不会启动浏览器或生成截图；请在有 `DISPLAY`/`WAYLAND_DISPLAY` 的机器上登录后用 `auth export-session` / `auth import-session` 迁移会话
- 显式选择 `password` 时，支持 ByteDance SSO（`cn` / `i18n-bd`）与 TikTok SSO（i18n TikTok 站点，如 `i18n-tt`）；`--username` 可传邮箱前缀或完整邮箱，密码和多因子验证码从终端读取且不会存储，只保存最终 SSO browser session
- 账号存在多个多因子方式时，用 `--mfa-method <method>`（如 `email` / `sms` / `otp`）显式指定；省略且有多个可用方式时会提示选择。注意 `otp` 是 TOTP 认证器（不下发验证码，需从认证器 App 读取），`email` / `sms` 会下发一次性验证码
- 如果当前环境无法直接访问本机浏览器 cookie（例如开发机、OpenClaw），可先在个人电脑导出全量数据：`auth export --out <path>`，再在目标环境导入：`auth import --from <path>`
- `auth export` 导出 bytedcli 数据目录（`~/.local/share/bytedcli/data/`）中的 auth、session、config 类文件为 gzip 压缩归档；cache 与临时文件不包含在内
- `auth export` 不带 `--out` 时自动写入系统临时目录。`--dry-run` 仅预览。`auth import --from <path>` 从归档还原，不做远端验证
- `auth clear` 清空本机所有 bytedcli 本地授权文件（与 `auth export` 涵盖的类别一致：SSO/浏览器 session、JWT override、per-site token、ByteCloud Auth SDK state 等），默认拒绝执行，必须显式带 `--yes` 或 `--dry-run`；cache 和临时文件不受影响；用于换机或彻底重置，之后需要重新 `auth login`
- 对 agent/脚本，优先使用 `--json auth login --begin` 启动 ByteCloud Auth 非阻塞登录，再用 `--json auth login --complete <token>` 轮询完成；`--complete` 未授权时会返回 pending 并立即退出
- `--json auth login --begin` 可选加 `--session` 用于 browser session 场景；它不会像阻塞式 `auth login --session` 一样继续等待并自动补完整个登录流程。session 非阻塞链路支持 `--feishu`（仅 `--site cn`）：`--json auth login --begin --session --feishu` 返回 `complete_token`，随后用 `--json auth login --complete <token>` 轮询扫码结果并落地 SSO + Feishu web session。不支持 `--session-method browser-cookie|interactive-browser|password` 或 `--browser`
- `auth login --no-terminal-qr` 会关闭终端二维码，并在未显式传入 `--qr-image` 时自动生成临时 PNG 路径
- `auth login --qr-image [path]` 可额外把二维码保存为 PNG；省略 path 时会自动写入系统临时目录，适合异步扫码登录流程
- 在 macOS 的非 TTY 人类交互场景下，如需自动用 Preview 打开刚生成的二维码 PNG，可显式设置 `BYTEDCLI_OPEN_QR_IMAGE=1`；默认仍只打印保存路径，避免无提示触发本地 GUI 副作用
- `--json auth login` 会自动关闭终端二维码，并默认生成临时二维码图片，便于 agent/脚本消费 `qr_image_ready`
- `auth logout` 默认清理 ByteCloud Auth SDK 登录态并保留本机应用账号 AK/SK；需要同时清理时显式追加 `--reset-app`。旧参数 `--reset-service-account` 仅作为兼容别名保留
- 无状态服务可以直接按控制面设置以下环境变量，无需先执行 `auth app set`。每个站点的 AK 与 SK 必须成对非空；当前 `--site` 对应的站点变量优先于 SDK 原生的单账号 `BYTECLOUD_AUTH_ACCESS_KEY_ID` / `BYTECLOUD_AUTH_SECRET_ACCESS_KEY`，但不会改变显式用户 JWT、JWT override 或 `--as user` 的既有优先级：

```bash
export BYTEDCLI_SERVICE_ACCOUNT_I18N_TT_ACCESS_KEY_ID='<i18n-tt-access-key-id>'
export BYTEDCLI_SERVICE_ACCOUNT_I18N_TT_SECRET_ACCESS_KEY='<i18n-tt-secret-access-key>'
export BYTEDCLI_SERVICE_ACCOUNT_EU_TTP_ACCESS_KEY_ID='<eu-ttp-access-key-id>'
export BYTEDCLI_SERVICE_ACCOUNT_EU_TTP_SECRET_ACCESS_KEY='<eu-ttp-secret-access-key>'
export BYTEDCLI_SERVICE_ACCOUNT_US_TTP_ACCESS_KEY_ID='<us-ttp-access-key-id>'
export BYTEDCLI_SERVICE_ACCOUNT_US_TTP_SECRET_ACCESS_KEY='<us-ttp-secret-access-key>'

bytedcli --site i18n-tt auth app status --refresh
bytedcli --site eu-ttp auth app status --refresh
bytedcli --site us-ttp auth app status --refresh
```

- 完整站点前缀为 `CN`、`I18N_BD`、`I18N_TT`、`US_TTP`、`EU_TTP`。`boe` 复用 `CN`，`i18n` 复用 `I18N_BD`，`us-ttp-bdee` / `us-ttp-usts` 复用 `US_TTP`。bytedcli 只把当前站点的一组环境变量映射给 ByteCloud Auth SDK，不修改父进程环境，也不把环境变量中的长期 SK 保存到本地。
- 应用账号使用 `auth app set` 配置：`--access-key-id` 传 AK，SK 不提供命令行参数；交互终端会隐藏输入，非交互场景从 stdin 读取，也可用 `--secret-file`
- AK/SK 由 ByteCloud Auth SDK 按 `--site` 分区存储；业务命令按目标 host/site 获取短期 JWT，SDK 会复用未过期 JWT 并在需要时自动刷新。`auth app status --refresh` 只显示配置来源与 JWT 过期时间，不输出 SK 或 JWT
- 不同控制面的应用账号 AK/SK 相互独立。分别用 `--site cn`、`--site i18n-bd`、`--site i18n-tt`、`--site us-ttp` 配置；`us-ttp-bdee` / `us-ttp-usts` 复用 `us-ttp` 凭据分区
- `BYTEDCLI_USER_CLOUD_JWT` 和显式 ByteCloud JWT override 保持更高优先级，适合临时覆盖；`auto` 模式下仅配置 AK/SK 时使用应用身份，仅登录个人身份时使用个人身份，同时存在两种身份时使用个人身份。需要强制选择时使用全局 `--as user|app`
- `--bytecloud-user-jwt-file` 是比上述环境变量和持久化来源更高优先级的单次 user override；必须与显式 `--site` 一起使用，且不能和 `--as app` 混用
- **SSO Token 按 SSO 环境缓存**（bytedance / tiktok / test 三组独立存储）
- **登录阶段**：`auth login` 默认使用 ByteCloud Auth；`auth login --session` 根据 `--site` 推导默认 SSO（`cn`/`i18n-bd` → ByteDance；`i18n-tt` → TikTok；`boe` → BOE）。可用 `--auth-site bytedance|tiktok|test` 显式覆盖 session 使用的 SSO
- **API 调用阶段**：需要 ByteCloud JWT 的服务优先使用显式 JWT override / 环境变量，其次从 ByteCloud Auth SDK 读取当前 site 的凭据；browser session 能力仍使用 `auth login --session` 保存的 SSO session/cookie
- `auth status` 显示 ByteCloud Auth 登录状态，并保留所有 3 个 SSO 环境的 session/token 状态
- 跨 site 调用时，CLI 会按目标 site 向 ByteCloud Auth SDK 请求对应凭据；某个 site 不可用时，先按 [Before login](#before-login-先复用不要直接-login) 流程在候选 site 上 `auth status` 排查可复用凭据，再决定是否对该 site 执行 `auth login`
- 若显式 JWT override 不可用，`auth get-bytecloud-jwt-token` 会按 `BYTEDCLI_USER_CLOUD_JWT -> AIME_USER_CLOUD_JWT` 自动回退读取环境变量，再尝试 ByteCloud Auth 凭据
- 操作目标站点前，按 [Before login](#before-login-先复用不要直接-login) 流程先用 `auth status` 排查再决定是否 `auth login`

## References

- `references/auth.md`
