# 常见问题与处理

## 工具版本过期

**在排查任何错误之前**，先确保 bytedcli 和已安装的技能是最新版本：

```bash
bytedcli self update
```

升级完成后重试原始命令。很多问题是由 CLI 版本和已安装技能之间的版本偏差引起的。

## 1. Missing command

- 原因：未指定子命令
- 处理：`bytedcli <group> --help`

## 2. Missing argument

- 原因：缺少必需位置参数
- 处理：使用 `--help` 查看参数

## 3. Not authenticated

- 可能原因（按出现频率排）：
  1. **当前 site 错配**：默认 `--site=cn`，但用户的凭证在另一个 site（如 `i18n-tt`）。`auth status` 会返回 `need_login`，但本地其实已有可用凭据
  2. 目标 site 的 access token 已过期且 refresh token 也失效
  3. 从未在目标 site 登录过
- 处理顺序（不要直接 login）：
  1. 先在候选 site 上各跑一次 `auth status`，找出能复用的：
     ```bash
     BYTEDCLI_CLOUD_SITE=cn       bytedcli --json auth status
     BYTEDCLI_CLOUD_SITE=i18n-tt  bytedcli --json auth status
     BYTEDCLI_CLOUD_SITE=i18n-bd  bytedcli --json auth status
     ```
  2. 若已有 site 可用，让后续命令也带上同一个 `BYTEDCLI_CLOUD_SITE` / `--site`（i18n 员工建议把 `export BYTEDCLI_CLOUD_SITE=i18n-tt` 写进 shell rc）
  3. 候选 site 全部 `need_login` 时，再对目标 site 执行 `BYTEDCLI_CLOUD_SITE=<site> bytedcli auth login`
- 补充：部分命令会按 `BYTEDCLI_USER_CLOUD_JWT -> AIME_USER_CLOUD_JWT` 或 `BYTEDCLI_USER_CODE_JWT -> AIME_USER_CODE_JWT` 自动回退；只有这些环境变量也不可用时才需要重新登录/配置

## 4. 获取字节云 JWT 失败: 401

- 原因：目标站点未认证。认证隔离按 SSO 环境生效：`i18n-tt`、`eu-ttp`（TikTok SSO）与 `cn/i18n-bd`（ByteDance SSO）隔离。即使 cn 已登录，操作 i18n-tt 仍需单独认证
- 处理：先用 `auth status` 确认目标 site 真的没有可用凭据，再决定是否 login（避免对已登录的 site 重复扫码）
  ```bash
  # 1. 先看目标 site 的当前状态
  BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli --json auth status

  # 2. 仅在 status=need_login 时，对目标 site 执行 login
  BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login
  ```
- 验证：`BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth status`

## 5. 网络/权限问题

- 确认内网访问权限
- 确认已登录且 Token 有效
