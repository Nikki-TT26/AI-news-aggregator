# opencli browser — Libra 指标组查看与配置

通过 opencli browser 驱动 Chrome 浏览器访问 Libra 指标组页面，提取和修改指标配置（如负向指标）。适用于 `bytedcli libra metric-group get` 无法获取的前端展示型配置项。

## 安装与前置条件

```bash
# 1. 安装 opencli（需要 Node.js >= 20）
npm install -g @jackwener/opencli

# 2. 创建工作目录（首次使用如遇权限问题）
mkdir -p ~/.opencli/clis ~/.opencli/cache

# 3. 安装 Chrome 浏览器扩展（二选一）
#    - 推荐：Chrome Web Store 搜索 "OpenCLI" 安装
#      https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
#    - 或：从 GitHub Releases 下载 zip，chrome://extensions 开发者模式加载

# 4. 验证连通性
opencli doctor
```

**doctor 正常输出：**
```
[OK] Daemon: running on port 19825
[OK] Extension: connected (v1.0.18)
```

> **注意**：`opencli browser` 命令依赖 Chrome 扩展连接。`bytedcli` 命令（PUBLIC 策略）不需要扩展。

## 核心工作流

### 绑定已有 Chrome tab（推荐）

直接 `open` 新 tab 可能因 SSO 认证超时，推荐先 `bind` 再 `open` 导航：

```bash
# 绑定当前 Chrome 活动 tab
opencli browser libra bind

# 导航到目标指标组页面
opencli browser libra open "<url>"

# 等待页面加载完成
opencli browser libra wait text "负向指标" --timeout 15000

# 执行 JS 提取数据
opencli browser libra eval "<js>"

# 完成后解绑
opencli browser libra unbind
```

### URL 格式

| 场景 | URL |
|------|-----|
| 查看指标组 | `https://data.bytedance.net/libra/metric-group/ordinary/view/{group_id}?type=libra&app_id=1190&mode=view` |
| 编辑指标组 | `https://data.bytedance.net/libra/metric-group/ordinary/edit/{group_id}?type=libra&app_id=1190&mode=edit` |
| 指标组模版 | `https://data.bytedance.net/libra/metric-group-template/view/{template_id}?type=normal&app_id=1190` |

## 查看负向指标

负向指标（指标越低越好）在 `bytedcli libra metric-group get` 的返回中**不包含**，只能通过页面中"指标设置"tab 的表格获取。

### 提取脚本

```bash
opencli browser libra eval "(() => {
  const table = document.querySelector('table');
  const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim());
  const negIdx = headers.indexOf('负向指标');
  const nameIdx = headers.indexOf('指标名称');
  const rows = table.querySelectorAll('tbody tr');
  const results = [];
  for (const row of rows) {
    const cells = row.querySelectorAll('td');
    const name = cells[nameIdx] ? cells[nameIdx].innerText.trim() : '';
    const negCell = cells[negIdx];
    const sw = negCell ? negCell.querySelector('[role=switch], .arco-switch') : null;
    const isNeg = sw ? (sw.classList.contains('arco-switch-checked') || sw.getAttribute('aria-checked') === 'true') : false;
    if (isNeg) results.push(name);
  }
  return JSON.stringify({total: rows.length, negativeCount: results.length, negativeMetrics: results});
})()"
```

**输出示例：**
```json
{"total":34,"negativeCount":20,"negativeMetrics":["问答总token消耗(B)","人均问答总token消耗(M)",...]}
```

### 完整示例：查看资源指标的负向指标

```bash
opencli browser libra bind
opencli browser libra open "https://data.bytedance.net/libra/metric-group/ordinary/view/212095?type=libra&app_id=1190&mode=view"
opencli browser libra wait text "负向指标" --timeout 15000
opencli browser libra eval "(() => { const table = document.querySelector('table'); const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim()); const negIdx = headers.indexOf('负向指标'); const nameIdx = headers.indexOf('指标名称'); const rows = table.querySelectorAll('tbody tr'); const results = []; for (const row of rows) { const cells = row.querySelectorAll('td'); const name = cells[nameIdx] ? cells[nameIdx].innerText.trim() : ''; const negCell = cells[negIdx]; const sw = negCell ? negCell.querySelector('[role=switch], .arco-switch') : null; const isNeg = sw ? (sw.classList.contains('arco-switch-checked') || sw.getAttribute('aria-checked') === 'true') : false; if (isNeg) results.push(name); } return JSON.stringify({total: rows.length, negativeCount: results.length, negativeMetrics: results}); })()"
opencli browser libra unbind
```

## 设置负向指标（编辑模式）

需要导航到编辑模式 URL（`mode=edit`），找到对应开关并点击，然后保存。

### 批量开启负向指标开关

```bash
# 导航到编辑模式
opencli browser libra open "https://data.bytedance.net/libra/metric-group/ordinary/edit/{group_id}?type=libra&app_id=1190&mode=edit"
opencli browser libra wait text "负向指标" --timeout 15000

# 批量开启指定指标的负向开关并保存
opencli browser libra eval "(() => {
  const negativeNames = ['问答总token消耗(B)', '人均问答总token消耗(M)', ...]; // 填入目标指标名
  const table = document.querySelector('table');
  const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim());
  const negIdx = headers.indexOf('负向指标');
  const nameIdx = headers.indexOf('指标名称');
  const rows = table.querySelectorAll('tbody tr');
  let clicked = [];
  for (const row of rows) {
    const cells = row.querySelectorAll('td');
    const nameCell = cells[nameIdx];
    const nameInput = nameCell ? nameCell.querySelector('input') : null;
    const name = nameInput ? nameInput.value : (nameCell ? nameCell.innerText.trim() : '');
    if (!negativeNames.includes(name)) continue;
    const negCell = cells[negIdx];
    const sw = negCell ? negCell.querySelector('[role=switch], .arco-switch') : null;
    if (sw) {
      const isNeg = sw.classList.contains('arco-switch-checked') || sw.getAttribute('aria-checked') === 'true';
      if (!isNeg) { sw.click(); clicked.push(name); }
    }
  }
  const saveBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === '保存');
  if (saveBtn) saveBtn.click();
  return JSON.stringify({clicked: clicked.length, names: clicked});
})()"
```

## 技术细节

### 页面 DOM 结构

- 指标组页面使用 Arco Design 组件库
- 负向指标开关：`<button role="switch" class="arco-switch">` 或 `<div class="arco-switch">`
- 开启状态：具有 `arco-switch-checked` class 或 `aria-checked="true"` 属性
- 编辑模式下指标名称在 `<input>` 元素中，查看模式下为纯文本

### 与 integrated_browser (MCP) 的对比

| 维度 | opencli browser | integrated_browser (MCP) |
|------|----------------|--------------------------|
| 调用方式 | shell 命令，可脚本化 | IDE 内 MCP tool call |
| 适用场景 | 自动化脚本、可复现操作 | IDE Agent 会话内交互 |
| subagent 支持 | 可在 subagent 中执行 | 仅主 agent 可用 |
| 前置条件 | npm 包 + Chrome 扩展 | Trae IDE 自带 |

### 已知问题

- `opencli browser <session> open <url>` 直接打开新 tab 可能因 SSO 超时，需先 `bind` 再 `open` 导航
- `opencli doctor` 的 Connectivity 测试偶尔报 "This operation was aborted"，不影响实际使用
- 页面 SSO 认证：首次打开 `data.bytedance.net` 可能需要用户在 Chrome 中先手动登录一次

## Trae 指标组负向指标参考配置

以下为设备维度指标组模版 (12042) 中已确认的负向指标配置，可作为新指标组配置的参考：

| 指标组 ID | 名称 | 负向指标数/总数 | 负向指标类别 |
|-----------|------|----------------|-------------|
| 212260 | 性能指标 | 5/5 | 全部（首token耗时、回复完整耗时、每Token输出时长） |
| 195337 | 反馈指标 | 16/16 | 全部（打断、回退、重试、点踩的消息数/用户占比/人均次数/消息率） |
| 195336 | 效果指标 | 6/14 | 代码建议拒绝相关（主动拒绝数/人均拒绝数/消息均拒绝数/拒绝率/部分拒绝率/批量拒绝率） |
| 212095 | 资源指标 | 20/34 | Token消耗类(16) + 理论成本类(4) |
| 212137 | 资源指标_意图 | 16/30 | Token消耗类(16)，不含理论成本 |
| 204767 | 问答特征指标 | 11/20 | 辱骂/继续/思考过长/原地踏步/打补丁的用户占比+消息率 + 负反馈率 |
| 195340 | 工具指标 | 0/10 | 无 |
| 195335 | 规模指标 | 0/10 | 无 |
| 195055 | 活跃天 | 0/6 | 无 |
