# 认证/SSO

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
bytedcli auth export --out ~/sample-bytedcli-backup.json.gz
bytedcli auth import --from ~/sample-bytedcli-backup.json.gz
bytedcli auth export-session --out ./sample-sso-session.json
bytedcli auth import-session --from ./sample-sso-session.json
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
```

单次以指定 ByteCloud 用户身份执行命令时，不把 JWT 直接放进 argv。使用 POSIX
owner-only（例如 `0600` / `0400`）的单行文件，或用 `-` 从非 TTY stdin 读取；两个全局参数都放在 domain 前：

```bash
bytedcli --site cn --bytecloud-user-jwt-file ./sample-user.jwt \
  --json bits release get --ticket-id <release-ticket-id>
printf '%s' "$BORROWED_BYTECLOUD_JWT" | bytedcli --site cn --bytecloud-user-jwt-file - --json auth userinfo
```

该 override 只在当前命令内存中有效，优先于 JWT 环境变量、持久化 override 与本地
session；它与 `--as app` / `BYTECLOUD_AUTH_AS=app` 互斥，site/host 不匹配时 fail closed。它只覆盖经
`SSOClient` 获取 ByteCloud user JWT 的进程内请求，不替换 cookie、Titan、PAT、平台
token，也不自动改写 `username` / `operator` 等业务字段。外部 companion 默认不继承；只有显式解析并等待 child 的受审 proxy 才会转交。
共享 MCP tools 会拒绝该参数；借用身份只能直接运行 CLI。
`auth` domain 只允许借用身份执行 `status`、`userinfo` 和 token 读取；本地 login/logout/app/session/override 管理会拒绝该参数。

`auth login --session` 会先通过 CAS 换票探活，只有 CAS 确实签发 service ticket 时才复用本地 SSO browser session；登录页跳转或明确 4xx 会视为失效，网络错误、5xx 与异常协议响应会直接报错且不会清理本地 session。只有本地 session 不可用时才会按当前站点的默认 session method 继续获取新的浏览器态 session。显式传入 `--session-method` 或 `--browser` 会跳过旧 session 复用，按指定方式重新获取 session；这也是旧会话异常时的推荐恢复方式。
`auth login --session --feishu` 只在 `cn` 站点可用，会切到飞书二维码 / OAuth 路径；阻塞式二维码路径会复用同一次飞书扫码，同时准备 SSO browser session 和额外的 Feishu web session。JSON 模式下，非 `qr` 的 session method 可以复用已有 Feishu web session，但不能新建 Feishu web session；需要新建时改用 `--session-method qr`，或去掉 `--json` 以展示额外的飞书二维码。已有 Feishu web session 探活只有在明确 4xx 或登录跳转时才判为失效；网络错误、5xx 与异常协议响应会报错并保留本地 session。
普通 SSO 二维码链路可能包含 `lark_applink_url`，用于在 PC 飞书打开同一个二维码页面。`--session --feishu` 的 applink 只会在点击方客户端打开 OAuth 页面，不能批准 CLI 正在轮询的二维码 challenge；Agent 必须展示 `qr_image_path` 并让用户用手机飞书扫码。
默认执行 `auth login --session` 且没有通过 CAS 校验的可复用 session 时，CLI 会使用 `qr` 获取新 session；如果当前站点不支持 QR，交互终端下会弹出 `qr`/`browser-cookie`/`interactive-browser`/`password` 菜单让用户临时选一个，并提示下次加 `--auto` 让 CLI 自动挑一条可用路径。`qr` 在所有 site 上都可以显式尝试，但它是否可用取决于具体账号/环境，部分用户可能失败。
显式加上 `--auto` 后，CLI 才会自动选择一条 session 登录路径：若检测到本机浏览器 cookie store，会优先尝试 `browser-cookie`；否则回退到 `qr`。在 `cn` 站点，browser-cookie miss 后会直接回退到普通 SSO `qr`；只有显式加 `--feishu` 才会走飞书扫码路径。其他站点的 `--auto` 才会继续回退到 `interactive-browser`。但在 macOS 的 JSON/非交互环境中，如果没有显式 `--yes`，CLI 会避免无提示触发 Keychain 访问，改为回退到 `qr`。
显式选择 `browser-cookie` 时，CLI 会检测本机支持的浏览器 cookie store；如果发现多个，会继续让用户选择具体浏览器；如果只有一个，则直接使用该浏览器。显式 `browser-cookie` 失败时不会再自动回退到 `interactive-browser`；若需要这种兜底行为，请改用 `--auto`，或显式切到 `--session-method interactive-browser`。显式选择 `browser-cookie` 或 `interactive-browser` 时，CLI 会先说明即将执行的动作，再要求二次确认；在 JSON/非交互环境中，需要显式追加 `--session-method` 或 `--auto`，其中显式 `browser-cookie` / `interactive-browser` 都需要 `--yes`，而 `--browser` 只在可能同时检测到多个支持浏览器时才需要。
Linux 上同时没有 `DISPLAY` 与 `WAYLAND_DISPLAY` 时，`interactive-browser` 只会为 ByteDance SSO 自动使用 headless Chrome；必要时用 `BYTEDCLI_BROWSER_EXECUTABLE_PATH` 指向可执行的 Chrome/Chromium。CLI 只会把未登录的 SSO 页面写入权限为 `0600` 的 PNG，不会截取登录后的业务页面；`--qr-image [path]` 可指定路径。JSON 模式会立即在 stderr 发出 `qr_image_ready` 事件，成功结果也会返回 `qr_image_path`。TikTok SSO 是账号密码登录页，静态截图无法安全完成登录：无 GUI 时会立即报 `AUTH_INTERACTIVE_BROWSER_GUI_REQUIRED`，不会启动浏览器或生成截图；请在有 `DISPLAY`/`WAYLAND_DISPLAY` 的机器上登录后用 `auth export-session` / `auth import-session` 迁移会话。
显式选择 `password` 时，支持 ByteDance SSO（`cn` / `i18n-bd`）与 TikTok SSO（i18n TikTok 站点，如 `i18n-tt`）；`--username` 可传邮箱前缀或完整邮箱，密码和多因子验证码从终端读取且不会存储，只保存最终 SSO browser session。账号存在多个多因子方式时，用 `--mfa-method <method>`（如 `email` / `sms` / `otp`）显式指定；省略且有多个可用方式时会提示选择。注意 `otp` 是 TOTP 认证器（不下发验证码，需从认证器 App 读取），`email` / `sms` 会下发一次性验证码。
在开发机或 OpenClaw 等无法直接读取本机浏览器 cookie 的环境，可先在个人电脑执行 `auth export --out <path>`，再在目标环境执行 `auth import --from <path>` 导入全量认证归档。归档包含 bytedcli 数据目录（`~/.local/share/bytedcli/data/`）中的 auth、session、config 类文件；cache 与临时文件不包含在内。
`auth export-session --out <path>` 和 `auth import-session --from <path>` 用于迁移单站点 SSO browser session。`export-session` 依赖当前站点已有一个可复用的本地 browser session，`import-session` 会先校验导入文件与当前站点是否匹配且是否仍可用。
`auth clear` 用于把本机 bytedcli 数据目录里的授权文件全部删掉（auth/session/config 三类，与 `auth export` 一致；cache 不动），默认拒绝执行，必须显式带 `--yes` 或 `--dry-run`；执行后需要重新 `auth login`。适用于换机、账号权限出问题需要彻底重置，或验证登录链路时。`auth logout` 只会清 ByteCloud Auth SDK 当前登录态，不会像 `auth clear` 那样把所有本地授权都拿掉。
应用账号使用 `auth app set --access-key-id <ak>` 配置。SK 不作为命令参数；交互终端会隐藏输入，非交互场景从 stdin 读取，也可通过 `--secret-file` 提供。SDK 按 `--site` 存储 AK/SK，并自动获取、缓存和刷新短期 JWT。
对 agent/脚本，优先使用 `--json auth login --begin` + `--json auth login --complete <token>`，避免阻塞等待人工授权。`--begin` 可选加 `--session`，session 非阻塞链路支持 `--feishu`（仅 `--site cn`）：`--json auth login --begin --session --feishu` 返回 `complete_token`，随后用 `--json auth login --complete <token>` 轮询扫码结果并落地 SSO + Feishu web session。不支持 `--session-method browser-cookie|interactive-browser|password` 或 `--browser`。飞书二维码有效期很短，只在用户准备扫码后执行 `--begin`；将 `qr_image_path` 提供给用户并要求使用手机飞书扫码，随后立即轮询 `--complete`。pending 输出和 `qr_image_ready` 事件里的 `required_action: scan_qr`、`required_action_app: feishu` 是动作依据，`lark_applink_completes_cli_login: false` 表示 applink 不能代替扫码。若返回 `login_status: expired`，执行返回的 `retry_command` 重新生成二维码。
