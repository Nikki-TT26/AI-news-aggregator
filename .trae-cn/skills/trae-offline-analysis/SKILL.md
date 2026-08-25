---
name: trae-offline-analysis
description: "编排层 SKILL，协调 7 个底层 SKILL（bytedance-hive、bytedance-dorado、bytedance-tqs、bytedance-aeolus、bytedance-libra、aeolus-dataset-manager、libra-gallery-builder）完成多步骤离线数据分析工作流，另依赖 bytedance-auth 提供认证支持。支持四大场景：指标组建设流水线、数据问题排查与诊断、数据查询与分析、单 SKILL 转发。维护本地 Markdown 知识库（builtin + workspace），实现资产注册和经验积累。当用户需求涉及 Libra Gallery 指标建设、Hive 建表+Dorado 调度+Gallery 指标组的端到端流水线、Aeolus 数据集或 Hive 表数据异常排查与修复、基于已有数据链路的 ad-hoc 查询分析时使用。"
---

# trae-offline-analysis

编排层 SKILL，本身不直接调用平台 API，而是协调以下 7 个底层 SKILL 完成多步骤工作流（另依赖 bytedance-auth 提供认证支持，共 8 个 SKILL 依赖）。

## 底层 SKILL 一览

| 底层 SKILL | 职责 |
|------------|------|
| bytedance-hive | Hive 表搜索、Schema 查询、建表、改表 |
| bytedance-dorado | Dorado 任务管理、SQL 更新、ad-hoc 查询 |
| bytedance-tqs | Hive SQL 校验与执行 |
| bytedance-aeolus | Aeolus 数据集与仪表盘查询 |
| bytedance-libra | Libra 实验详情与报告查询 |
| aeolus-dataset-manager | Aeolus 数据集 CRUD（Python API） |
| libra-gallery-builder | Libra Gallery 指标组全流程操作（Python API） |

## SKILL 依赖（自动安装/更新）

以下底层 SKILL **不纳入本仓库 git 管理**，由 SKILL 在每次启动时自动检查并安装/更新：

| SKILL | 来源（skills CLI source） | 说明 |
|-------|--------------------------|------|
| bytedance-hive | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包 |
| bytedance-dorado | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包 |
| bytedance-tqs | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包 |
| bytedance-aeolus | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包 |
| bytedance-libra | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包 |
| bytedance-auth | `code.byted.org/byteapi/bytedcli` | 官方 bytedcli 包（认证辅助，不参与编排） |
| aeolus-dataset-manager | `skills.byted.org/trae_strategy_agent/skills_public` | 策略团队维护（strategy-skills 仓库内已包含） |
| libra-gallery-builder | `skills.byted.org/trae_strategy_agent/skills_public` | 策略团队维护（strategy-skills 仓库内已包含） |

> bytedance-* 系列为字节官方维护；aeolus-dataset-manager、libra-gallery-builder 由策略团队维护，发布在 `skills.byted.org/trae_strategy_agent/skills_public`。
> **注意**：如果当前工作目录为 strategy-skills 仓库本身，aeolus-dataset-manager 和 libra-gallery-builder 已包含在仓库中，无需通过 skills CLI 安装/更新。仅当用户将 trae-offline-analysis 复制到其他仓库使用时，才需要通过 skills CLI 下载这两个 SKILL。
> bytedance-auth 不参与编排，仅提供 SSO 认证能力，被其他底层 SKILL 间接依赖。

## 知识库

本 SKILL 维护本地 Markdown 知识库，分为 builtin 区（只读）和 workspace 区（可读写）。

### builtin 区（只读）

SKILL 自带的稳定知识，开发者维护。按需读取：

- `references/builtin/concepts.md` — TRAE 概念介绍，包含平台架构、核心术语
- `references/builtin/assets/index.md` — Hive 表资产索引（通用知识 + 每张表的摘要信息，不含字段列表）
- `references/builtin/assets/tables/<table_name>.md` — 单张表的完整详情（元信息 + 字段明细），按需读取
- `references/builtin/best-practices/` — 底层 SKILL 最佳实践（按 SKILL 拆分，按需加载）

### workspace 区（可读写）

用户新建资产和经验积累。每次编排开始时扫描目录建立上下文，执行完成后按需更新。

采用「一条知识一个文件」的组织方式，避免多用户协作时的文件冲突。无索引文件，SKILL 通过扫描目录 + 读取文件名/首行标题来建立上下文：

- `references/workspace/assets/<table_name>.md` — 一张表一个文件，文件名即表名（如 `dwd_trae_ai_behavior_event_di.md`），文件首行 `# 表名` 作为标题
- `references/workspace/notes/<date>_<slug>.md` — 一条经验一个文件，文件名格式 `YYYY-MM-DD_简短描述.md`（如 `2026-04-15_tqs-credential-issue.md`），文件首行 `# 标题` 作为描述

**资产定位优先级**：先扫描 workspace/assets/ 目录，再查 builtin/assets/index.md。同一资产两边都存在时，以 workspace 版本为准。

## 决策流程

收到用户输入后，按以下步骤执行：

### 0. 初始化（SKILL 每次启动时自动执行）

> 每次 SKILL 被调用时自动执行，用户无感。

**步骤 0.1：SKILL 依赖检查与自动安装/更新**

检查「SKILL 依赖」表中列出的 8 个 SKILL（7 个底层 + bytedance-auth）是否已安装且为最新版本。

**strategy-skills 仓库判断**：首先检查当前工作目录是否为 strategy-skills 仓库（判断方法：执行 `git remote -v`，检查输出中是否包含 `strategy-skills`）。若是，则 aeolus-dataset-manager 和 libra-gallery-builder **跳过安装和更新检查**，仅对 bytedance-* 系列 6 个 SKILL 执行后续流程。

```
SKILL 列表：
  - 始终检查（6 个）：bytedance-hive、bytedance-dorado、bytedance-tqs、bytedance-aeolus、bytedance-libra、bytedance-auth
  - 仅非 strategy-skills 仓库时检查（2 个）：aeolus-dataset-manager、libra-gallery-builder
来源：
  - bytedance-* 系列：code.byted.org/byteapi/bytedcli
  - aeolus-dataset-manager / libra-gallery-builder：skills.byted.org/trae_strategy_agent/skills_public
安装命令模板：
  # bytedance-* 系列
  npm_config_registry="https://bnpm.byt ed.org" npx -y agentbuddy@latest add code.byt ed.org/byteapi/bytedcli --skill <skill-name> --agent trae-cn --copy -y
  # aeolus-dataset-manager / libra-gallery-builder（仅非 strategy-skills 仓库时使用）
  npm_config_registry="https://bnpm.byt ed.org" npx -y agentbuddy@latest add skills.byt ed.org/trae_strategy_agent/skills_public --skill <skill-name> --agent trae-cn --copy -y
```

**安装检查**（每次执行）：

```
遍历 SKILL 依赖列表中的每个 skill：
├── .trae/skills/<skill-name>/SKILL.md 存在？
│   （⚠️ 必须使用 ls 命令或 Read 工具检查，不能使用 Glob/Grep，
│    因为 .trae 是隐藏目录，Glob 默认不匹配以 . 开头的路径）
│   ├── 否 → 标记为「待安装」
│   └── 是 → 该 skill 已安装（跳过）
└── 继续下一个

存在「待安装」的 skill？
├── 否 → 继续「定期更新检查」
└── 是 → 并行安装所有待安装的 skill：
    对每个待安装的 skill 并行执行（使用多个 RunCommand 并行调用）：
      # bytedance-* 系列
      npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add code.byted.org/byteapi/bytedcli \
        --skill <skill-name> --agent trae-cn --copy -y
      # aeolus-dataset-manager / libra-gallery-builder
      npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add skills.byted.org/trae_strategy_agent/skills_public \
        --skill <skill-name> --agent trae-cn --copy -y
    ⚠️ 注意：--skill 参数不支持逗号分隔多个 skill 名称，必须每个 skill 单独执行一条命令。
    但多条命令可以并行执行（同时发起多个 RunCommand），大幅缩短总安装时间。
    ⚠️ 注意：不同 SKILL 来源不同，安装命令中的 source 参数（add 后面的路径）必须与表格中的「来源」一致。
    ├── 全部安装成功 → 告知用户：「已自动安装 SKILL：<list>」
    ├── 部分或全部安装失败 → 诊断错误类型：
    │   ├── 错误信息包含 "EPERM" + "user.yml" 或 "operation not permitted"
    │   │   → 原因：Trae IDE 终端沙箱限制，不允许写入 ~/.aipaas/ 目录
    │   │   → 告知用户：
    │   │   「SKILL <list> 安装失败（IDE 终端沙箱限制，无法写入 ~/.aipaas/）。
    │   │    请在**系统终端**（Terminal.app / iTerm）中执行以下命令：」
    │   │   → 为每个待安装的 skill 生成完整可复制命令（注意使用对应的 source 路径）
    │   │   → 不阻塞主流程
    │   └── 其他错误（网络不通等）→ 告知用户：
    │       「SKILL <list> 安装失败，本次将尝试继续执行。
    │        如遇到相关 SKILL 不可用，请手动执行安装命令。」
    │       → 不阻塞主流程
    └── 继续「定期更新检查」
```

**定期更新检查**（每日一次，紧接安装检查之后执行）：

为避免每次启动都执行耗时的更新检查，采用「标记 + 周期」策略：

```
检查 .skills-last-updated 文件（位于项目根目录）：
（⚠️ 以 `.` 开头的隐藏文件，Glob 默认不匹配，必须使用 ls 命令或 Read 工具检查）
├── 文件不存在 或 文件内容中的日期距今 ≥ 1 天
│   → 执行更新检查（并行执行，每个 SKILL 一条命令；strategy-skills 仓库下仅 6 条，否则 8 条）：
│     # bytedance-* 系列（6 条，始终执行）
│     npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add code.byted.org/byteapi/bytedcli \
│       --skill bytedance-hive --agent trae-cn --copy -y
│     npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add code.byted.org/byteapi/bytedcli \
│       --skill bytedance-dorado --agent trae-cn --copy -y
│     ... (bytedance-tqs / bytedance-aeolus / bytedance-libra / bytedance-auth 同理)
│     # 策略团队 SKILL（2 条，仅非 strategy-skills 仓库时执行）
│     npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add skills.byted.org/trae_strategy_agent/skills_public \
│       --skill aeolus-dataset-manager --agent trae-cn --copy -y
│     npm_config_registry="https://bnpm.byted.org" npx -y agentbuddy@latest add skills.byted.org/trae_strategy_agent/skills_public \
│       --skill libra-gallery-builder --agent trae-cn --copy -y
│     ⚠️ --skill 不支持逗号分隔，必须每个 skill 单独一条命令，但可并行执行。
│     （skills CLI 的 add 命令对已安装的 skill 会覆盖更新）
│   → 更新成功后写入当前日期到 .skills-last-updated
│   → 若有更新，告知用户：「已自动更新依赖 SKILL 到最新版本」
│   → 更新失败 → 按安装检查相同的错误诊断逻辑处理（EPERM 则指引系统终端，其他错误简要提示），不阻塞
└── 文件存在且距今 < 1 天 → 跳过更新检查

以上两步完成后，进入步骤 0.2（认证预检）。
```

> `.skills-last-updated` 位于项目根目录，仅包含一个日期字符串（如 `2026-04-20`），已加入 `.gitignore`。

**步骤 0.2：认证预检（每次自动执行）**

> 在 SKILL 依赖安装/更新完成后、进入主流程之前，自动检查所有认证状态。这确保后续执行不会因认证过期中途中断。

加载 `references/builtin/best-practices/auth.md` 获取完整预检命令序列，然后**并行**执行以下 4 项检查：

```
并行执行：
├── Step 1：bytedcli SSO 认证状态（ByteCloud Auth SDK）
│   NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y @bytedance-dev/bytedcli@latest auth status
│   → 检查 ByteCloud Auth 登录状态，以及各 SSO 环境（bytedance / tiktok / test）的 session/token 状态
│   → bytedance SSO 影响：aeolus / dorado / hive(cn) / libra / tqs(cn)
│   → tiktok SSO 影响：hive(sg) / tqs(sg)
│   → 若需单独检查海外站点：BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth status
│
├── Step 2：TQS 凭证文件（必须用 ls -la，不能用 Glob，因为是隐藏文件）
│   ls -la .env.local .env.sg.local
│   → 确认文件存在后，按地区使用 source 验证变量（CN 用 .env.local，SG 用 .env.sg.local）
│
├── Step 3：aeolus-dataset-manager token
│   ls -la .trae/skills/aeolus-dataset-manager/scripts/token.txt
│   → 检查修改时间是否超过 7 天
│
└── Step 4：libra-gallery-builder cookie
    ls -la .trae/skills/libra-gallery-builder/scripts/cookie.txt
    → 检查修改时间是否超过 7 天

汇总结果：
├── 全部正常 → 静默通过，不打扰用户，直接进入 §0.3
├── 有异常项 → 向用户报告异常项及修复建议，然后继续执行（不阻塞）
│   异常类型：
│   - ByteDance SSO 过期 → 提示运行 `bytedcli auth login`（cn/i18n-bd 站点共享）
│   - TikTok SSO 过期 → 提示运行 `BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login`
│   - TQS 凭证缺失 → 提示配置 .env.local / .env.sg.local
│   - token/cookie 过期（>7天）→ 提示运行时会自动尝试刷新，需确保 Chrome 已登录对应平台
└── 若用户明确要求「检查认证」→ 即使全部正常也展示完整认证状态表
```

> 认证预检的目的是**早期发现问题**。即使有认证异常也不阻塞主流程（因为用户可能只使用部分 SKILL，且某些认证运行时可自动刷新）。

**步骤 0.3：运行环境检测**

默认使用「本地模式」（local mode），知识库仅本地读写，不做 git 同步和推送。

如果用户主动要求同步知识库（如"同步知识"、"sync knowledge"、"推送知识"），则进入「同步流程」（见下方「知识库同步（用户主动触发）」section）。

### 1. 读取知识库

必须读取以下知识文档：
- `references/builtin/assets/index.md` + 扫描 `references/workspace/assets/` 目录（列出文件名即可了解用户已注册哪些表）— 了解当前已有的数据资产
- 扫描 `references/workspace/notes/` 目录（列出文件名即可了解已有哪些经验笔记，按需读取具体文件）
- `references/builtin/concepts.md` — 了解平台架构与核心术语
- `references/builtin/best-practices/index.md` — 了解最佳实践目录结构，确定后续需按需加载哪些子文件
- `references/builtin/best-practices/bytedcli-setup.md` — bytedcli 命令调用方式（每次必须加载）

> **按需加载最佳实践**：在 §2 意图识别后，根据涉及的底层 SKILL 加载对应的最佳实践文件（如 `best-practices/bytedance-hive.md`、`best-practices/bytedance-tqs.md` 等）。需要认证预检时加载 `best-practices/auth.md`。不要在 §1 阶段一次性加载所有最佳实践文件。

> **按需加载表详情**：在 §4 资产定位阶段，确定涉及的具体表后，再读取 `references/builtin/assets/tables/<table_name>.md` 获取完整字段列表。不要在 §1 阶段一次性加载所有表的字段明细。

> 对于场景四（单 SKILL 转发），concepts.md 只需读取与所转发 SKILL 相关的 section，最佳实践只需加载 `bytedcli-setup.md` + 被转发 SKILL 对应的文件。

### 2. 意图识别

根据用户需求判断场景：
- 用户需要新建/修改 Gallery 指标组、Hive 建表、Dorado 调度配置 → **场景一**
- 用户描述数据异常并需要排查原因（给了 Aeolus 数据集链接/Libra 实验/Hive 表名/Dorado 任务链接 + 问题描述）→ **场景二**
- 用户需要做 ad-hoc 数据查询、下钻分析、找 bad case → **场景三**
- 用户需求仅涉及单个底层 SKILL → **场景四**：直接转发，不做编排

### 3. 环境判断

根据用户需求或涉及的表/数据，判断目标环境：
- 默认为 **cn**（国内）环境
- 若用户明确提及"海外"、"i18n"、"sg"、"国际版"等，或涉及的表在 `cloudide` / `ai_application_coding` 库下 → 使用 **i18n** 环境
- 环境不同会影响：库名（`flow_aipaas` vs `cloudide`/`ai_application_coding`）、Hive region（cn vs sg）、TQS 集群和凭证
- 详见 `references/builtin/assets/index.md` 的「cn / i18n 环境差异」section

**海外环境操作要点**（详见 `references/builtin/best-practices/bytedance-hive.md` 和 `best-practices/bytedance-tqs.md`）：
- **Hive 查询**：加 `--region sg`（需 TikTok SSO 认证，通过 `BYTEDCLI_CLOUD_SITE=i18n-tt bytedcli auth login` 登录）
- **TQS 查询**：必须显式 source 海外凭证，通过 `(source .env.sg.local && bytedcli tqs execute --sql "..." )` 执行
- **日期选择**：国内查 **T-1 及之前**，海外查 **T-2 及之前**（时差原因，海外 T-1 分区可能尚未就绪）
- **凭证管理**：`.env.local`（国内）和 `.env.sg.local`（海外）统一存放在项目根目录下，按地区 source 对应文件（国内 source `.env.local`，海外 source `.env.sg.local`），不依赖 bytedcli 自动加载

### 4. 资产定位

从知识库和用户输入中定位涉及的数据资产：
- 已在知识库中 → 直接取关联信息（表名、库名、字段、Dorado 任务 ID、上下游表等）
- 不在知识库中 → 调用 bytedance-hive 搜索表、bytedance-dorado 搜索任务等 → 注册到 workspace/assets/

**Dorado 任务定位**：
- 若用户提供了表名 → 先从知识库（workspace/assets/ + builtin/assets/）查找该表对应的 Dorado 任务 ID，直接用 `task get` 获取详情
- 若用户提供了任务名但不知道 taskId → 用 `bytedcli dorado task list --project-id <projectId> --task-name <taskName>` 按名称过滤搜索，找到 taskId 后再 `task get`
- 若用户只描述了业务场景 → 先定位相关 Hive 表，再从知识库或 `hive detail` 中获取 producerDoradoTasks

**表间依赖定位**（血缘查询）：
- 先查阅 workspace/assets/ 和 builtin/assets/ 中各表的「上游表」「一级下游表」「关联表」字段，这些是已确认的稳定依赖关系
- 若 assets 中未覆盖 → 使用 `bytedcli hive lineage <guid> --depth <N>` 查询血缘（需先通过 `hive detail` 获取 GUID）
- 若需确认实际 SQL 引用关系 → 使用 `bytedcli dorado task get` 查看 Dorado 任务 SQL 代码中的 FROM/JOIN 子句

**字段溯源**（当 DWD 层找不到目标数据时）：
- DWD 行为表中的字段（如 `agent_type`）经过 Dorado SQL 的清洗和映射，可能与上游原始值不同。当用户查找的枚举值在 DWD 层不存在时，应**通过 Dorado 任务 SQL 追溯字段来源**，逐层向上游查找
- 典型的向上追溯路径：DWD 加工表 → Dorado SQL（查看 CASE WHEN 映射逻辑）→ 上游埋点日志表（`cloudide.dwd_behavior_trae_ide_public_user_log_di` 的 `params` 字段）
- 详见 `references/builtin/assets/index.md` 的「表间关系与指标计算主入口」section

**vid / 实验命中排查**：
- 大部分 DWD 行为表（delta_di、event_di、dau_accumulate_df 等）中的 vid 是**进组 vid**——用户当天被分入该实验组即会记录，但**进组不等于生效**，某条具体消息是否真正在该实验下生效需要自行甄别
- 若需确认某条消息实际命中了哪些实验版本 → 使用 `dwd_resource_prompt_completion_di` 的 `ab_version` 虚拟列（可直接 `SELECT ab_version FROM ...`），该字段是**消息粒度**的实验命中列表，能准确反映该请求实际生效的实验版本
- 典型场景：用户反馈某条消息效果异常，需确认该消息是否命中了某个实验 → 通过 session_id（= message_id）+ user_id 定位到该条记录，查看 ab_version

**Trace / Tool Call / Agent 轨迹定位**：
- 用户查询某个 log_id 的 trace → 使用 `flow_aipaas.trace_from_fornax`，**必须限定** `fornax_space_id = '7444123531090067458'`
- 用户分析 Tool Call 调用情况 → 使用 `code_evaluation.trae_cn_toolcalls`
- 用户分析意图/特征标签 → 使用 `flow_aipaas.dwd_trae_chat_intent_di` 或 `flow_aipaas.dwd_trae_message_model_bench_tags`
- 用户分析 **Agent 轨迹**（模型对比、性能、对话质量、子 Agent 调用链）→ 使用 `flow_aipaas.trae_traj_detail_di`（⭐ 每行一条完整轨迹，含 messages JSON、token 统计、finish_reason，**Agent 分析的首选表**）
- 用户需要 **Span 级深度分析** → 使用 `flow_aipaas.trae_agent_fornax_detail_di`（ODS 原始 Span 数据，含 input_json/output_json）
- 用户需要从 **Conversation → Message → Trajectory 逐层追踪** → 使用 `flow_aipaas.trae_conversation_message_map_di`（会话-消息映射）+ `flow_aipaas.trae_message_traj_map_di`（消息-轨迹映射）+ `flow_aipaas.trae_traj_detail_di`（轨迹详情）
- 用户分析 **模型调用成本**（CU 成本、单价匹配、成本趋势）→ 使用 `dwd_trae_chat_model_cost_di`（cn：`flow_aipaas`，i18n：`ai_application_coding`，含 token 消耗和 CU 成本字段，包含所有 status 的请求）
- 查询场景决策详见 `references/builtin/assets/index.md` 的「查询场景决策」section

### 5. 执行计划生成

根据识别的场景生成有序的 SKILL 调用链。计划生成后向用户展示，确认后执行。

### 6. 逐步执行

按计划调用各底层 SKILL，每步完成后汇报进展。上一步输出作为下一步输入。遇到异常时分析原因，参考 `references/builtin/best-practices/` 下对应 SKILL 的最佳实践文件。

### 7. 知识库更新

执行完成后按需更新知识库：
- 新建了 Hive 表 → 在 `references/workspace/assets/` 下新建 `<table_name>.md`
- 积累了有价值的经验 → 在 `references/workspace/notes/` 下新建 `<date>_<slug>.md`
- 如果没有产生新资产或新经验，则不更新

#### 7.1 提交推送（用户主动触发）

> 默认不执行。知识变更仅保留在本地文件。
> 用户主动要求"同步知识库"时，才执行 Git 提交和推送。详见「知识库同步（用户主动触发）」section。

### 8. 输出摘要

向用户汇报完整的执行结果，包括：产物链接、关键操作、状态确认。

## 认证管理

认证预检已集成到初始化流程（§0.2），每次 SKILL 启动时自动执行。无需用户手动触发。当用户明确要求「检查认证状态」时，即使全部正常也展示完整认证状态表。

认证方式速查表：

| 认证方式 | 适用 SKILL | 有效期 | 站点/环境 |
|----------|-----------|--------|-----------|
| ByteCloud Auth（ByteDance SSO） | bytedance-aeolus、bytedance-dorado、bytedance-hive（cn）、bytedance-libra、bytedance-tqs（cn） | ~12h | `cn` / `i18n-bd`（共享登录态） |
| ByteCloud Auth（TikTok SSO） | bytedance-hive（sg）、bytedance-tqs（sg） | ~12h | `i18n-tt` / `eu-ttp`（需单独登录） |
| TQS 凭证文件（.env.local / .env.sg.local） | bytedance-tqs（cn / sg） | 长期有效（手动配置） | — |
| Chrome Cookie + x-titan-token | aeolus-dataset-manager | ~7天 | — |
| Chrome Cookie (bd_sso_3b6da9 JWT) | libra-gallery-builder | ~7天 | — |

> **SSO 环境隔离规则**（bytedcli 基于 ByteCloud Auth SDK）：
> - SSO Token 按 SSO 环境独立缓存，共 3 组：**bytedance** / **tiktok** / **test**
> - `cn` 和 `i18n-bd`（ByteIntl 国际站）共享 ByteDance SSO 登录态，通常只需登录一次
> - `i18n-tt`（TikTok 国际站）和 `eu-ttp`（EU TTP 站）使用 TikTok SSO，需**单独执行** `auth login`
> - 通过 `--site` 参数或 `BYTEDCLI_CLOUD_SITE` 环境变量切换站点

**完整的预检命令序列、刷新方式、隐藏文件检查注意事项等详见 `references/builtin/best-practices/auth.md`。**

> **凭证管理**：`.env.local`（国内）和 `.env.sg.local`（海外）统一存放在项目根目录下，按地区 source 对应文件（国内 source `.env.local`，海外 source `.env.sg.local`，两者均自包含所有必要凭证）。不依赖 bytedcli 从 cwd 自动加载（subagent 执行时 cwd 不确定）。

## 编排场景

### 场景一：指标组建设（或修改）流水线

**触发条件**：用户需要新建或修改 Libra Gallery 指标组，可能涉及 Hive 建表和 Dorado 调度配置。

**流程**：

1. **理解需求**：参照已有需求新建 / 直接新建 / 修改已有需求的指标组
2. **Hive 建表或选表**：使用 bytedance-hive 建表，或从知识库/搜索中找到正确的 Hive 表（可能涉及多个表）
3. **Dorado 任务配置**（仅新建表时）：
   - 使用 bytedance-dorado 新建 HSQL 任务
   - 生成 Dorado SQL 代码，使用 bytedance-tqs 或 Dorado ad-hoc 验证正确性
   - 任务名固定为表名，调度时间按 `references/builtin/best-practices/bytedance-dorado.md` 中的规范配置
   - 配置好依赖关系，**向用户确认是否上线**后再执行上线
   - 如果没有新建表则跳过此步骤
4. **Gallery 指标组建设**：
   - 使用 libra-gallery-builder 操作 Gallery
   - 生成数据源 SQL，使用 bytedance-tqs 验证正确性
   - 生成需要的指标
   - 生成需要的维度值（选择正确的类型：用户维度 / 指标维度）
   - 按需求配置维度高级配置
   - 设置好后发起上线
   - 上线后 Gallery 平台会自动生成 stg_/rpt_/mds_/calc_ 等 Dorado 任务和 Hive 表（详见 `references/builtin/concepts.md`「Gallery 指标上线后自动生成的 Dorado 任务链路」），无需手动创建

### 场景二：数据问题排查与诊断

**触发条件**：
- 用户给出 **Aeolus 数据集链接**并描述数据异常（如某些维度值的数据缺失、数值为 0、数据不一致等）
- 用户质疑 **Libra 实验报告**的指标数据有问题
- 用户反馈某张 **Hive 表**的数据异常，需要排查上游链路

**流程**：

1. **定位数据源**（根据用户入口不同）：
   - 用户给了 **Aeolus 数据集链接** → 使用 bytedance-aeolus 获取数据集的 model SQL，从 SQL 中识别引用的底表和 JOIN 逻辑
   - 用户给了 **Libra 实验/Gallery 指标** → 使用 libra-gallery-builder 找到 Gallery 指标组，查看数据源 SQL
   - 用户给了 **Hive 表名** → 从知识库获取表信息，使用 bytedance-dorado 获取该表的生产任务 SQL
   - 用户给了 **Dorado 任务链接** → 直接使用 bytedance-dorado 获取任务 SQL 代码
2. **理解数据链路**：分析数据源 SQL 的逻辑，梳理涉及的表、JOIN 关系、字段来源和过滤条件
3. **逐层追溯根因**：
   - 从数据源 SQL 开始，识别问题可能出现在哪一层
   - 使用 bytedance-dorado 查看底表的 Dorado 任务 HSQL 代码，分析字段加工逻辑（如 CASE WHEN 映射、过滤条件、GROUP BY 等）
   - 使用 bytedance-tqs 对各层数据做探查验证（如查询某个字段的枚举值分布、验证 JOIN 匹配率、确认数据是否存在等）
   - 若当前层找不到问题 → 继续向上游追溯，使用 bytedance-hive 查找上游表 schema，使用 bytedance-dorado 查看上游表的 Dorado SQL
   - 重复以上步骤，直到定位根因（如：上游表缺少某类数据、字段枚举值不匹配、JOIN 条件不满足、过滤条件过严等）
   - 需要查看表间依赖关系时，先查阅 `references/builtin/assets/index.md` 中记录的上下游表信息；若文档未覆盖，使用 bytedance-hive 的 `lineage` 命令查询血缘关系
   - 注意区分问题层级：Gallery 自动生成的 stg_/rpt_/mds_/calc_ 任务一般不需要手动修改（详见 `references/builtin/concepts.md`「Gallery 指标上线后自动生成的 Dorado 任务链路」），排查应优先从数据源 SQL 和 DWD 底表入手
4. **输出诊断结论**：向用户报告根因、影响范围、数据验证结果
5. **修复**（如需要）：修改数据源 SQL 和/或 Dorado HSQL 代码
6. **验证**：使用 bytedance-tqs 验证修复后的 SQL：直接 `tqs execute` 执行验证数据正确性（新版 execute 已自动包含 analyze 前置校验，失败时直接报错退出）。仅当需要精确区分权限问题类型时，才先独立运行 `tqs analyze`
7. **上线**（用户确认后）：Dorado 任务上线 + Gallery 指标组提交上线。**默认不自动上线**，修改完成后向用户展示变更 diff，等待用户明确要求后再执行上线

### 场景三：数据查询与分析

**触发条件**：用户需要基于已有数据链路做 ad-hoc 查询、下钻、对比。

**流程**：

1. **理解需求**：如用户想查指标明细、找 bad case、做下钻分析、查 log_id trace、分析 Tool Call、查意图分布、分析 Agent 轨迹/性能/模型对比、验证圈 query 结果等
2. **定位数据**：
   - 用户指定了表名 → 直接从知识库取 schema 信息
   - 用户指定了 Libra 实验或 Gallery 指标 → 使用 libra-gallery-builder 查看 Gallery 指标组设置（维度、指标、数据源 SQL），找到底表
   - 用户描述了业务场景但未指定表 → 根据 `references/builtin/assets/index.md` 的「查询场景决策」匹配最合适的表
   - 用户查某个 log_id 的 trace → 使用 `flow_aipaas.trace_from_fornax`（必须带 `fornax_space_id = '7444123531090067458'`）
   - 用户分析 Tool Call → 使用 `code_evaluation.trae_cn_toolcalls`
   - 用户分析意图/特征标签 → 使用 `dwd_trae_chat_intent_di` 或 `dwd_trae_message_model_bench_tags`
   - 用户分析 **Agent 轨迹**（性能、模型对比、对话质量、子 Agent 调用链）→ 使用 `flow_aipaas.trae_traj_detail_di`（⭐ Agent 分析首选表，每行一条完整轨迹）
   - 用户需要 **Span 级原始数据**深度分析 → 使用 `flow_aipaas.trae_agent_fornax_detail_di`
   - 用户需要从 **Conversation → Message → Trajectory 逐层追踪** → 使用 `flow_aipaas.trae_conversation_message_map_di` + `flow_aipaas.trae_message_traj_map_di` + `flow_aipaas.trae_traj_detail_di`
   - 用户分析 **模型调用成本**（CU 成本、单价匹配、成本趋势）→ 使用 `dwd_trae_chat_model_cost_di`（cn：`flow_aipaas`，i18n：`ai_application_coding`，含 token 消耗和 CU 成本字段，包含所有 status 的请求）
   - **DWD 层查不到目标数据时** → 通过 Dorado 任务 SQL 追溯字段来源，向上游表（埋点日志表、Fornax 链路追踪表）查找。详见 §4 的「字段溯源」指引
   - 用户验证 **圈 query 结果**（按维度筛选子人群后的实验指标）→ 按 `references/builtin/concepts.md` §6.4 的模式构造验证 SQL：进组表 + DWD 底表 + `dwm_trae_user_message_tags_di`（cn: `flow_aipaas`，i18n: `cloudide`）提供 message_tags 维度（`array<string>` 类型，用 `array_contains` 筛选），其他维度（如 is_new）从 Gallery 数据源 SQL 复现
3. **生成查询**：通过数据源 SQL 或底表 schema 生成分析 SQL
   - **必须加分区条件**：Hive 分区字段通常是 `date`（yyyyMMdd），务必加分区条件避免全表扫描
   - **session_id 双向查询**：当用户提到某个 session id 时，**必须同时按 `conversation_id` 和 `message_id` 两个维度查询**（不同表中 session_id 含义不同，详见 index.md「ID 跨表映射注意事项」）
4. **语法与权限校验**：新版 `tqs execute` 已自动包含 analyze 前置校验（失败时直接报错退出，不会提交任务），因此可以直接执行步骤 5。仅当需要精确解读 analyze 错误信息时，才先独立运行 `tqs analyze`：
   - **cn 环境**：`(source .env.local && bytedcli tqs analyze --sql "...")`
   - **i18n 环境**：`(source .env.sg.local && bytedcli tqs analyze --sql "...")`
   - analyze 错误类型处理：
     - `SqlParseException`（如 `Encountered ... at line X, column Y`）→ SQL 语法错误，根据报错中的行号/列号修正后重新校验
     - `NoPrivilegeException`（`User ... does not have privileges for QUERY`）→ 权限不足，错误信息会精确列出缺少权限的字段（如 `Columns=[content_raw]->action=select`）。若列出所有字段 → 无表级权限；若仅列出部分字段 → 有表权限但缺少这些敏感列的权限。提示用户申请对应权限
     - `Object '...' not found` → 表名拼写错误或 TQS APP 对该库无元数据可见性。应先确认表名拼写正确、检查 APP 权限配置，不要使用 `--skip-analyze` 跳过校验
5. **执行查询**：
   - **cn 环境**：通过 `(source .env.local && bytedcli tqs execute --sql "...")` 执行，查询 **T-1 及之前**的分区
   - **i18n 环境**：通过 `(source .env.sg.local && bytedcli tqs execute --sql "...")` 执行，查询 **T-2 及之前**的分区（时差原因，海外 T-1 可能尚未就绪）
   - 将结果返回给用户
6. **验证数据**：查到轨迹数据后再进行深入分析；如果查询结果为空（0 行数据），**不要继续猜测分析**，应立即报告给用户确认（可能是 ID 有误、日期范围不对、或需要换表查询）

### 场景四：简单场景（转发给单个底层 SKILL）

**触发条件**：用户需求仅涉及单个底层 SKILL 的能力。

直接转发给对应的底层 SKILL 处理，不做编排。可转发的底层 SKILL：bytedance-aeolus、bytedance-dorado、bytedance-hive、bytedance-libra、bytedance-tqs、aeolus-dataset-manager、libra-gallery-builder。

**转发注意事项**：
- 转发给 **bytedance-dorado** 时，必须在转发指令中包含：
  1. **项目 ID**：国内 `11253`，海外 `300004344` 或 `300004442`（根据表所属项目决定，详见知识库中对应表的资产文件）。注意资产文件和 Dorado URL 中使用 `cn_11253`、`sg_300004442` 等带前缀格式，前缀是 region，下划线后的数字才是 `--project-id` 参数值（如 `cn_11253` → `--project-id 11253`，`sg_300004442` → `--project-id 300004442 --region sg`）
  2. **region**：国内无需指定（默认 cn），海外需加 `--region sg`
  3. **任务定位方式**：若用户给了任务名但无 taskId，指导 subagent 先用 `task list --project-id <projectId> --task-name <taskName>` 搜索，再用 `task get <taskId>` 获取详情
  4. **已知资产快捷路径**：若任务对应的表在知识库中有记录，直接提供 taskId，无需搜索
  5. **默认不上线**：修改 SQL 后默认只提交草稿，**不自动执行 `task online`**。向用户展示 `task diff` 结果后，等待用户明确要求再上线
- 转发给 **bytedance-tqs** 时，必须在转发指令中包含：
  1. **凭证加载方式**：国内用 `source .env.local`，海外用 `source .env.sg.local`（`.env.sg.local` 自包含所有必要凭证，无需先 source CN）
  2. **日期约定**：国内查 T-1 及之前，海外查 T-2 及之前
  3. **环境判断**：根据用户指定的库名或表名判断是国内还是海外环境
  4. **权限异常处理**：若查询报 `Permission denied` / `Table not found` / `User does not have privilege` / `Access denied for column` 等权限错误，按以下顺序排查并告知用户：
     - 先检查凭证是否正确加载（.env.local vs .env.sg.local 混用是最常见原因）
     - 凭证正确但仍无权限 → 引导用户到 Coral 数据地图查看并申请表权限：
       - 国内：`https://data.bytedance.net/coral/datamap/detail?groupName=default&qualifiedName=HiveTable%3A%2F%2F%2F{db}%2F{table}%400`
       - 海外：`https://dataleap-sg.tiktok-row.net/coral/datamap/detail?groupName=alisg&qualifiedName=HiveTable%3A%2F%2F%2F{db}%2F{table}%406#group=alisg`
     - 若是字段级权限问题（表可查但特定字段报错）→ 在 Coral 表详情页申请「列级权限」
     - 详细排查流程参见 `references/builtin/best-practices/bytedance-tqs.md` 的「权限不足排查与申请」section
  5. **Auto analyze 说明**：新版 `tqs submit` 和 `tqs execute` 已自动在提交前执行 analyze，analyze 失败直接报错退出。Agent 无需手动先 `tqs analyze` 再 `tqs execute`。**禁止使用 `--skip-analyze`**——如果 analyze 报错，应根据错误信息修正 SQL 或解决权限问题，而不是跳过校验
- 转发给 **bytedance-hive** 查询海外表时，需带上 `--region sg`
- 转发给 **bytedance-hive** 查询血缘时，需在转发指令中说明：
  1. `lineage` 命令需要 GUID 而非表名，需先通过 `hive detail <db> <table>` 获取表的 GUID
  2. `lineage` 不支持 `--direction` 参数，返回的是双向完整血缘图（上游+下游混合）
  3. `--depth` 控制追溯层数，一般 1-2 层即可
  4. 血缘结果中包含 DoradoTask 等中间节点，需从中筛选 HiveTable 类型的节点

## 知识库读写规则

| 时机 | 读 | 写 |
|------|:--:|:--:|
| 每次编排开始 | 读 builtin/assets/index.md + 扫描 workspace/assets/ 和 workspace/notes/ 目录建立上下文，按需读取其他知识文档 | - |
| 资产定位阶段 | 按需读取 builtin/assets/tables/<table_name>.md 或 workspace/assets/<table_name>.md 获取字段详情 | 发现新资产时在 workspace/assets/ 下新建文件 |
| 执行完成后 | - | 按需在 workspace/assets/ 下新建文件 + 按需在 workspace/notes/ 下新建文件 |
| 执行失败后 | - | 仅在 workspace/notes/ 下新建笔记（标注失败原因） |
| 纯查询，无副作用时 | 读 | 不写 |

### workspace/assets/ 写入规则

一张表一个文件，文件名为表名（如 `dwd_trae_ai_behavior_event_di.md`）。

新建资产时，直接在 `workspace/assets/` 下创建 `<table_name>.md`，确保文件首行为 `# 表名`。格式如下：

```markdown
# <表名>

- **cn 库表名**：`<db>.<table>`
- **i18n 库表名**：`<db>.<table>`（如无则省略）
- **分区字段**：`<partition_field>`
- **TTL**：<N> 天
- **Dorado 任务**：taskId `<id>`，项目 `<project>`
- **上游表**：<上游表列表>（可选）
- **一级下游表**：<下游表列表>（可选）
- **关联表**：<关联表列表>（可选）
- **设计背景**：<一句话说明>（可选）

## 字段明细

| 字段名 | 类型 | 说明 |
|--------|------|------|
| ... | ... | ... |
```

> **可选元信息字段**：除 cn/i18n 库表名、分区字段、TTL、Dorado 任务等基础字段外，还可按需记录：
> - `上游表`：该表的 Dorado SQL 直接引用的源表列表
> - `一级下游表`：直接消费该表的下游表（仅 dwd 层，stg/mds/rpt 等报表层不记录）
> - `关联表`：与该表在功能上有对应关系但不存在直接上下游依赖的表（如 `delta_di` 与 `event_di`）
> - `设计背景`：建表原因、与同类表的关系等业务上下文

### workspace/notes/ 写入规则

一条经验一个文件，文件名格式 `YYYY-MM-DD_简短描述.md`（如 `2026-04-15_tqs-credential-issue.md`）。

新建笔记时，直接在 `workspace/notes/` 下创建 `<date>_<slug>.md`，确保文件首行为 `# 标题`。格式如下：

```markdown
# <标题>

**日期**：YYYY-MM-DD
**作者**：@<用户名>

## 现象

<问题描述>

## 根因

<原因分析>

## 修复方案

<解决方法>

## 经验总结

- <要点>
```

在以下情况新建笔记：
- 执行过程中发现非预期的坑（如某个 API 行为与文档不一致）
- 用户提供了有价值的业务背景信息
- 执行失败的原因和最终解决方案
- 用户主动要求记录

## 知识库同步（用户主动触发）

> 仅当用户主动要求时执行（如"同步知识库"、"sync knowledge"、"推送知识"、"提交知识"等关键词）。常规执行流程中不涉及 Git 操作。

当用户触发同步时，按以下步骤执行：

### 1. 环境检测

检测当前工作目录是否为本 SKILL 所属的 git 仓库：

```
当前目录存在 .git/ 目录？
├── 否 → 告知用户：「当前目录不是 git 仓库，无法同步。如需团队协作，请 clone 完整仓库。」
│   → 终止同步流程
└── 是 → 检查是否为本 SKILL 所属仓库：
    git remote -v 的输出中包含 "code.byted.org/stone/strategy-skills" 或
    "code.byted.org:stone/strategy-skills"？
    ├── 是 → 继续步骤 2
    └── 否 → 告知用户：「当前 git 仓库不是本 SKILL 所属仓库，无法同步。」
        → 终止同步流程
```

### 2. Git 健康检查

检测仓库是否处于异常的中间状态（上次 merge/rebase 未完成），如果是则先恢复：

```bash
if [ -f .git/MERGE_HEAD ] || [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    git merge --abort 2>/dev/null || git rebase --abort 2>/dev/null
fi
```

### 3. 分支切换与拉取

```
当前在 knowledge/trae-offline-analysis 分支？
├── 是 → 直接 git pull origin knowledge/trae-offline-analysis（merge 模式）
└── 否 → 检查工作区是否有未提交修改（git status --porcelain）
    ├── 有未提交修改 → 告知用户：
    │   "当前不在 knowledge 分支且有未提交修改，
    │    请先处理当前修改后再同步知识库。"
    │   → 终止同步流程
    └── 无未提交修改 → git checkout knowledge/trae-offline-analysis
        ├── 本地有该分支 → git pull origin knowledge/trae-offline-analysis
        └── 本地无该分支 → git fetch origin
            ├── 远程有该分支 → git checkout -b knowledge/trae-offline-analysis origin/knowledge/trae-offline-analysis
            └── 远程也没有该分支 → git checkout -b knowledge/trae-offline-analysis
                → 基于当前 HEAD 创建新分支
```

- **pull 成功** → 继续步骤 4
- **pull 冲突** → SKILL 自动解决（见「冲突处理策略」section）
- **网络不通** → 告知用户网络异常，终止同步流程

> 使用 merge 模式（不用 rebase），原因：
> 1. rebase 会改写本地 commit 历史，多人协作下可能导致需要 force push
> 2. rebase 中断时仓库处于中间状态，SKILL 自动恢复困难
> 3. merge 冲突一次性解决，对自动化更友好

### 4. 合并 master 更新

```bash
git fetch origin master
```

比较本地 knowledge 分支中的 `references/builtin/` 和 `SKILL.md` 与 `origin/master` 的差异：
- **无差异** → 继续步骤 5
- **有差异（knowledge 分支落后 master）** → 自动合并：

```bash
git merge origin/master -m "sync: merge master updates into knowledge"
```

- 合并成功 → 继续步骤 5
- 合并冲突 → SKILL 自动解决：builtin 和 SKILL 代码文件以 master 版本为准

> 这一步确保用户始终使用最新的 SKILL 代码和 builtin 知识。

### 5. 提交推送 workspace 变更

```bash
# 1. 仅提交 workspace 目录的变更
git add references/workspace/

# 2. 检查 workspace 是否有变更
git diff --cached --quiet -- references/workspace/
# 无变更则跳过后续步骤

# 3. 提交（限定只提交 workspace 目录）
git commit references/workspace/ -m "knowledge: <描述>"

# 4. 推送
git push origin knowledge/trae-offline-analysis
```

**commit message 约定**：

| 变更类型 | 格式 | 示例 |
|---------|------|------|
| 新建 asset | `knowledge: add asset <table_name>` | `knowledge: add asset dwd_trae_block_detail_di` |
| 更新 asset | `knowledge: update asset <table_name>` | `knowledge: update asset dwd_trae_ai_behavior_event_di` |
| 新建 note | `knowledge: add note <slug>` | `knowledge: add note tqs-credential-issue` |

**push 失败处理**：

```bash
# 远程有新提交导致 push 失败
git pull origin knowledge/trae-offline-analysis  # merge 模式
# 冲突则 SKILL 自动解决（见「冲突处理策略」section）
git push origin knowledge/trae-offline-analysis  # 重试（最多 1 次）
# 仍失败 → 提示用户手动处理
```

**同步完成后**向用户报告结果：已提交的文件列表、push 是否成功、是否有冲突合并。

> **冲突告知**：如果推送过程中发生了冲突合并（push 失败 → pull → 冲突自动解决 → 重试），须告知用户："本次知识更新与远程版本冲突，已按冲突处理策略解决（远程版本优先），你的版本已追加为注释供参考。"

## 多人协作 Git 同步机制

> 以下同步机制仅在用户主动触发「同步知识库」时生效。常规执行流程中，知识库为纯本地读写模式。

### 分支策略

| 分支 | 用途 | 权限 |
|------|------|------|
| `master` | SKILL 代码 + builtin 知识 | 受保护，变更走 MR review |
| `knowledge/trae-offline-analysis` | master 的超集 = SKILL 代码 + builtin + workspace 知识 | 开放 push，多人协作 |

**核心关系**：`knowledge/trae-offline-analysis ⊇ master`。knowledge 分支始终包含 master 的全部内容，加上 workspace 知识。用户日常在 knowledge 分支上工作。

### 冲突处理策略

#### 为什么冲突概率很低

1. **一条知识一个文件** — 两人同时新建不同文件：零冲突
2. **文件名按表名/日期命名** — 两人创建同名文件的概率极低
3. **用户主动同步时先 pull 再 push** — 冲突窗口只有单次同步操作时间（几秒）

#### 冲突场景与处理方式

| 冲突场景 | 处理方式 | 执行者 |
|---------|---------|--------|
| workspace/ 下不同文件 | 无冲突（一条知识一个文件） | — |
| workspace/assets/ 同一文件 | **以远程版本为准（先 push 成功者优先）**（last-write-wins），不做行级合并 | SKILL |
| workspace/notes/ 同一文件 | 极罕见，保留双方版本，给其中一个加序号后缀 | SKILL |
| builtin/ 下文件 | 远程版本优先（builtin 以维护者为准） | SKILL |
| SKILL 代码文件（SKILL.md 等） | 远程版本优先 | SKILL |
| 自动解决失败 | 提示用户手动处理 | 用户 |

> 为什么 asset 文件用远程版本优先而不是行级合并？
> asset 文件通常是 SKILL 整体替换生成的（每次获取最新 schema 后重新写入完整内容），不适合行级合并。冲突时保留远程版本（即先 push 成功的那份），本地版本的内容追加为注释供用户参考。

#### SKILL 自动解决流程

```
1. git pull origin knowledge/trae-offline-analysis
2. 检测冲突文件：
   a. workspace/assets/ 文件冲突：
      - 采用 last-write-wins：保留远程版本
        （因为远程版本是更早 push 成功的，本地版本是后生成的）
      - 将本地版本的内容追加为注释供用户参考
   b. workspace/notes/ 文件冲突：
      - 极罕见，给本地版本文件名加 -2 后缀另存
   c. builtin/ 文件冲突：
      - 用远程版本覆盖本地
   d. SKILL 代码文件冲突：
      - 用远程版本覆盖本地
3. git add <冲突文件>
4. git commit（完成 merge）
```

### 边界情况处理

| 场景 | 处理 |
|------|------|
| 两人新建同名 note 文件 | 极罕见（需同日 + 同 slug），SKILL 给其中一个加序号后缀 |
| 整理 SKILL 删了 workspace 文件但 MR 未合入 | 知识短暂不可见（几天），MR 合入后恢复，可接受 |
| 依赖 SKILL 未安装（首次使用） | §0.1 自动检测并安装缺失的依赖 SKILL |
| 依赖 SKILL 有新版本 | §0.1 每日自动更新（通过 .skills-last-updated 标记控制频率） |
| 依赖 SKILL 安装/更新失败（网络问题） | 不阻塞主流程，提示用户手动安装；已安装的旧版本仍可用 |
| 依赖 SKILL 安装失败（EPERM/沙箱限制） | IDE 终端沙箱不允许写入 ~/.aipaas/，输出系统终端可复制命令指引用户手动安装 |
| npx / npm 不可用 | §0.1 跳过，提示用户安装 Node.js；已安装的 skill 不受影响 |
| 用户主动触发同步但不在 git 仓库 | 告知用户无法同步，需 clone 完整仓库 |
| 用户主动触发同步但 remote 不匹配 | 告知用户当前仓库非本 SKILL 所属仓库，无法同步 |
| 用户主动触发同步，本地无 knowledge 分支 | 同步流程步骤 3 自动 checkout 远程分支或创建新分支 |
| 用户主动触发同步，不在 knowledge 分支且有未提交修改 | 告知用户先处理当前修改后再同步 |
| 用户主动触发同步，网络不通 | 告知用户网络异常，终止同步流程 |
| 维护者直接在 master 更新了 builtin | 用户主动同步时自动 merge origin/master 到本地 knowledge |
| knowledge 分支长期未同步 master | 用户主动同步时自动检测并合并 master 更新 |

### 完整时序图

```
常规执行：
用户发起请求
  │
  ▼
§0.1 SKILL 依赖检查
  ├── 检查依赖 SKILL 是否已安装
  │   └── 缺失 → 并行安装（每个 skill 单独一条命令，同时执行）
  ├── 检查 .skills-last-updated 标记
  │   └── 距今 ≥ 1 天 → 并行更新全部依赖 SKILL
  └── 安装/更新失败 → 不阻塞，提示用户
  │
  ▼
§0.2 认证预检（并行检查 4 项认证）
  ├── bytedcli SSO 状态（ByteDance + TikTok）
  ├── TQS 凭证文件（.env.local / .env.sg.local）
  ├── aeolus-dataset-manager token（有效期 7 天）
  ├── libra-gallery-builder cookie（有效期 7 天）
  ├── 全部正常 → 静默通过
  └── 有异常 → 报告并建议修复，不阻塞
  │
  ▼
§1 读取知识库（本地）
  │
  ▼
§2 ~ §6 意图识别 → 环境判断 → 资产定位 → 执行计划 → 逐步执行
  │
  ▼
§7 知识库更新（写入本地文件）
  │
  ▼
§8 输出摘要

用户主动触发同步：
用户说"同步知识库"
  │
  ▼
环境检测 → Git 健康检查 → 分支切换 → pull → merge master → commit → push → 报告结果
```

### 设计原则

1. **对用户无侵入** — 默认纯本地模式，不操作 Git，不切换分支，不自动 commit/push
2. **安全优先** — 使用 merge 而非 rebase，不改写历史；检测工作区状态，不打断用户工作
3. **冲突最小化** — 一条知识一个文件 + 即时 push 缩小冲突窗口
4. **智能合并** — asset 文件 last-write-wins，builtin 远程优先，notes 保留双方
5. **质量把关** — workspace 自由写入，builtin 走 review 流程
6. **流程简洁** — 整理时直接删除 workspace 文件，容许 MR review 期间短暂不可见，换取流程简单
7. **按需同步** — 知识库同步由用户主动触发，同步时检查 knowledge 和 master 分支更新，确保 SKILL 代码和知识都是最新的
8. **依赖自治** — 依赖 SKILL 不纳入仓库管理，由 §0.1 自动检查安装和定期更新，避免版本滞后
9. **环境自适应** — 默认本地模式，用户主动触发同步时才检测 git 环境，不影响核心功能
