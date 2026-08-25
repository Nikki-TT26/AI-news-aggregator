# Aeolus 数据集管理 API 参考文档

## 基本信息

- **协议**: HTTPS
- **数据格式**: JSON (`application/json`)

| 区域 | Base URL | 页面 URL | 默认集群 |
|------|----------|----------|----------|
| 国内 (cn) | `https://data.bytedance.net` | `https://data.bytedance.net/aeolus/pages/dataManage` | `cn` |
| 海外 SG (sg) | `https://aeolus-sg.tiktok-row.net` | `https://aeolus-sg.tiktok-row.net/pages/dataManage` | `sg` |

**API 路径**：所有 API 共用相同路径前缀 `/aeolus/api/v3/`，国内外完全一致。

**页面路径差异**：国内页面 URL 带 `/aeolus` 前缀（如 `/aeolus/pages/dataManage/...`），海外无此前缀（如 `/pages/dataManage/...`）。

---

## 认证方式

### x-titan-token (JWT)

所有 API 请求均需携带 `x-titan-token` 请求头进行身份认证。该 Token 为 JWT 格式，来源于页面 HTML 中嵌入的 `window.__titan_passport_token` 变量。

**获取方式**:

1. **页面提取**: 从对应区域的 Aeolus 页面 HTML 源码中解析 `window.__titan_passport_token` 的值（国内 `https://data.bytedance.net/aeolus`，海外 `https://aeolus-sg.tiktok-row.net`）
2. **自动获取**: 通过 `pycookiecheat` 库从本地 Chrome 浏览器的 Cookie 存储中自动读取对应域名的登录态 Cookie，携带 Cookie 请求页面后从 HTML 响应中提取 Token

**Token 生命周期**: Token 具有时效性，过期后需重新获取。

---

## 公共请求头

所有 API 请求需携带以下请求头：

| 请求头 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `x-titan-token` | string | 是 | JWT 认证令牌，从 `window.__titan_passport_token` 获取 |
| `x-request-id` | string | 是 | 请求唯一标识，用于链路追踪，格式 `uuid_timestamp` |
| `x-aeolus-gray-env` | string | 是 | 灰度环境标识，固定值 `aeolus-online` |
| `x-page-url` | string | 否 | 当前页面 URL（国内如 `https://data.bytedance.net/aeolus/pages/dataManage?appId=1006036`，海外如 `https://aeolus-sg.tiktok-row.net/pages/dataManage?appId=802699`） |
| `Content-Type` | string | 是 | 固定 `application/json` |
| `Accept` | string | 是 | 固定 `application/json, text/plain, */*` |

---

## API 端点

### 1. 数据集 CRUD 操作

#### 1.1 创建数据集

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetV2`
- **Query Params**: `enableSaveWithoutMigrate=true`
- **说明**: 创建一个新的数据集定义（新建或从已有数据集复制）

**请求体结构**（top-level keys）:

```json
{
  "baseConf": {},
  "nodeConf": [],
  "syncConf": {},
  "dimMetList": [],
  "dimMetCategoryList": [],
  "whereConf": {},
  "dependencyConf": {},
  "dependencyConfList": [],
  "labelConf": {},
  "dagTagConf": {},
  "dataTableConf": {},
  "linkConf": [],
  "parseEngine": 1,
  "aggExpediteConf": {"isOpen": false, "conf": []},
  "checkDimMetId": "check_dim_met_id_<uuid>"
}
```

**baseConf 关键字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `appId` | number | 是 | Aeolus 应用 ID |
| `dataSetName` / `name` | string | 是 | 数据集名称 |
| `ownerEmailPrefix` | string | 是 | 负责人邮箱前缀 |
| `parentId` | number | 是 | 所属文件夹 ID |
| `dataSetType` | number | 是 | 数据集类型，SQL 节点为 `34` |
| `originalDataSetId` | number | 否 | 复制场景时，源数据集 ID |
| `version` | string | 否 | 版本号，通常 `"v2"` |
| `dc` | string | 否 | 数据中心标识，通常为 `"cn"`（海外 SG 环境也使用 `"cn"`） |
| `belong` | number | 否 | 固定 `1` |

**dimMetList 说明**: 参见文档末尾「数据模型：dimMetList」章节

**dependencyConfList 字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `nodeId` | string | 节点 ID |
| `dependencyConf` | object | 依赖配置 |
| `obtainSuccess` | boolean | 是否成功获取依赖 |
| `tbId` | string | 表 ID |
| `tbName` | string | 表名 |

**响应体**:

```json
{
  "code": "aeolus/ok",
  "msg": "success",
  "data": {
    "dataSetId": 5429362,
    "dataSetVersionId": 12345
  }
}
```

---

#### 1.2 更新并发布数据集

- **Method**: `PUT`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetV2`
- **Query Params**: `enableSaveWithoutMigrate=true&enableDraftDataSet=false`
- **说明**: 更新数据集配置并发布上线。需要先调用 `acquireDataSetLock` 获取编辑锁。编辑场景不需要调用 `determineCluster`，也不需要传 `dataTableConf`。

**请求体**: 结构与创建接口基本一致，但不含 `dataTableConf`。`baseConf` 需包含 `dataSetId` 字段标识目标数据集。修改已有数据集时，建议先从 `allDataSetInfoV2` 获取完整配置再修改。

**注意**:
- 更新前必须调用 `acquireDataSetLock` 获取编辑锁
- 更新后无论成功失败，必须调用 `releaseDataSetLock` 释放编辑锁
- `dimMetList` 中已有字段需保留原有 `id` 值

> **区域差异**: CN 编辑发布时必须传 `dataSetVersionType=online`（或 `draft`），SG 编辑时通常不传 `dataSetVersionType` 参数。

**响应体**:

```json
{
  "code": "aeolus/ok",
  "msg": "success",
  "data": {
    "dataSetId": 5429362,
    "dataSetVersionId": 12345
  }
}
```

---

### 2. 数据集信息查询

#### 2.1 获取数据集模型信息

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetModelInfo`
- **说明**: 获取数据集的模型详细信息，包含维度、指标、SQL 等完整定义

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 是 | 数据集 ID |
| `dataSetVersionId` | number | 否 | 数据集版本 ID，不传则返回最新版本 |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "dataSetId": "number",
    "dataSetVersionId": "number",
    "dataSetName": "string",
    "dataSetDisplayName": "string",
    "dataSetType": "string",
    "sql": "string",
    "dimList": ["object"],
    "metList": ["object"],
    "clusterId": "number",
    "dataSourceId": "number",
    "owners": ["string"],
    "scheduleInfo": "object",
    "paramList": ["object"]
  }
}
```

---

#### 2.2 获取数据集概览

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetOverview`
- **说明**: 获取数据集的概览信息，包含基本属性和状态

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 是 | 数据集 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "dataSetId": "number",
    "dataSetName": "string",
    "dataSetDisplayName": "string",
    "dataSetDesc": "string",
    "dataSetStatus": "string",
    "createTime": "string",
    "updateTime": "string",
    "owners": ["string"],
    "dataSetFolderId": "number"
  }
}
```

---

#### 2.3 获取数据集概览分页列表 (LLM V2)

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetOverviewPageLLMV2`
- **说明**: 分页获取数据集概览列表，支持 LLM 增强的搜索能力

**请求体**:

```json
{
  "pageNum": "number",
  "pageSize": "number",
  "keyword": "string",
  "dataSetType": "string",
  "dataSetStatus": "string",
  "owners": ["string"],
  "dataSetFolderIds": ["number"],
  "sortField": "string",
  "sortOrder": "string"
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pageNum` | number | 是 | 页码，从 1 开始 |
| `pageSize` | number | 是 | 每页数量 |
| `keyword` | string | 否 | 搜索关键词 |
| `dataSetType` | string | 否 | 数据集类型筛选 |
| `dataSetStatus` | string | 否 | 数据集状态筛选 |
| `owners` | array | 否 | 负责人筛选 |
| `dataSetFolderIds` | array | 否 | 文件夹 ID 筛选 |
| `sortField` | string | 否 | 排序字段 |
| `sortOrder` | string | 否 | 排序方向，`asc` 或 `desc` |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "total": "number",
    "pageNum": "number",
    "pageSize": "number",
    "list": ["object"]
  }
}
```

---

#### 2.4 获取所有数据集信息 V2

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/allDataSetInfoV2`
- **说明**: 获取所有数据集的基本信息列表

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | 否 | 搜索关键词 |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": ["object"]
}
```

---

### 3. SQL 与 Schema 操作

#### 3.1 从 SQL 获取表 Schema

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getTableSchemaFromSql`
- **说明**: 解析 SQL 语句并返回对应的表结构 Schema 信息

**请求体**:

```json
{
  "sql": "string",
  "clusterId": "number",
  "dataSourceId": "number"
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sql` | string | 是 | SQL 查询语句 |
| `clusterId` | number | 是 | 集群 ID |
| `dataSourceId` | number | 是 | 数据源 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "columns": [
      {
        "columnName": "string",
        "columnType": "string",
        "columnComment": "string"
      }
    ]
  }
}
```

---

#### 3.2 获取 SQL Schema 结果

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getTableSchemaFromSqlResult`
- **说明**: 获取异步 SQL Schema 解析的结果（与 `getTableSchemaFromSql` 配合使用）。轮询直到 `status` 为 `"SUCCEEDED"` 或 `"FAILED"`。

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5428964,
  "dataSetType": 34,
  "connectionMode": 0,
  "serviceType": "data_set",
  "dataSourceType": "hive",
  "clusterName": "cn",                       // 国内 "cn", 海外 SG "sg"
  "dbName": "Hive-db-1",
  "query": "SELECT ...",
  "previewId": "f42aac96-ff84-404b-8801-bc9b0a5e3a17"
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `previewId` | string | 是 | Schema 解析任务 ID，由 `getTableSchemaFromSql` 返回 |
| `dataSetId` | number | 否 | 数据集 ID（编辑已有数据集时**必传**，否则可能超时） |
| 其他字段 | - | 是 | 与 `getTableSchemaFromSql` 请求体相同 |

**成功响应** (status=SUCCEEDED):

```json
{
  "code": "aeolus/ok",
  "data": {
    "status": "SUCCEEDED",
    "containSet": false,
    "result": {
      "parse_engine": 1,
      "schemas": [
        {"name": "field_name", "type": "bigint", "prepType": "long", "is_support": 1}
      ],
      "partition_columns": [
        {"db_table_name": "db.table", "name": "date", "values": "${date}"}
      ]
    }
  }
}
```

---

#### 3.3 预览 Schema

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/previewSchema`
- **说明**: 预览数据集的 Schema 结构，用于在创建/编辑数据集时验证 SQL 和字段配置

**请求体**:

```json
{
  "sql": "string",
  "clusterId": "number",
  "dataSourceId": "number",
  "dimList": ["object"],
  "metList": ["object"]
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sql` | string | 是 | SQL 查询语句 |
| `clusterId` | number | 是 | 集群 ID |
| `dataSourceId` | number | 是 | 数据源 ID |
| `dimList` | array | 否 | 维度列表 |
| `metList` | array | 否 | 指标列表 |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "schemaList": ["object"]
  }
}
```

---

### 4. 数据集类型与验证

#### 4.1 判定数据集类型 V2

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/determineDataSetTypeV2`
- **说明**: 根据 SQL 和配置自动判定数据集类型

**请求体**:

```json
{
  "sql": "string",
  "clusterId": "number",
  "dataSourceId": "number"
}
```

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "dataSetType": "string"
  }
}
```

---

#### 4.2 预检查维度指标列表

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/preCheckDimMetList`
- **说明**: 在保存/发布数据集前，对维度和指标列表进行预校验

**请求体**:

```json
{
  "baseConf": {
    "appId": 802699,
    "connectionMode": 0,
    "dataSetType": 34,
    "syncMode": 0
  },
  "dimMetList": [],
  "nodeConf": [],
  "linkConf": [],
  "whereConf": {
    "requiredRowFilter": [],
    "nodeRowFilter": {}
  }
}
```

> **注意**: 编辑已有数据集时，`baseConf` 需额外包含 `"dataSetId": <id>` 字段。旧文档中的 `{dataSetId, dimList, metList}` 结构不正确，实际请求使用上述结构。

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `baseConf` | object | 是 | 基础配置，包含 `appId`, `connectionMode`, `dataSetType`, `syncMode`；编辑时额外包含 `dataSetId` |
| `dimMetList` | array | 是 | 维度指标列表 |
| `nodeConf` | array | 是 | 节点配置 |
| `linkConf` | array | 是 | 关联配置，通常为空数组 `[]` |
| `whereConf` | object | 是 | 筛选条件配置，包含 `requiredRowFilter` 和 `nodeRowFilter` |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "checkResult": "boolean",
    "errorMessages": ["string"]
  }
}
```

---

#### 4.3 检查维度指标名称

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/checkDimMetName`
- **说明**: 检查维度或指标名称是否合法且不重复

**请求体**:

```json
{
  "nodeConf": [],
  "connectionMode": 0,
  "dataSetId": 5428964,
  "dimMetList": [
    {"name": "p_date", "expr": "p_date", "dimMetMixOrder": 0, "dimMetVariety": 1},
    {"name": "model_name", "expr": "model_name", "dimMetMixOrder": 1, "dimMetVariety": 0}
  ]
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `nodeConf` | array | 是 | 节点配置 |
| `connectionMode` | number | 是 | 连接模式，固定 `0` |
| `dataSetId` | number | 否 | 数据集 ID（编辑时传入） |
| `dimMetList` | array | 是 | 维度指标列表（每项只需 `name`, `expr`, `dimMetMixOrder`, `dimMetVariety`） |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "valid": "boolean",
    "message": "string"
  }
}
```

---

### 5. 集群与数据源

#### 5.1 判定集群

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/determineCluster`
- **说明**: 根据 baseConf 和 nodeConf 自动判定适用的计算集群。仅在**创建**数据集时调用，**编辑**场景不需要调用。

**请求体**:

```json
{
  "baseConf": { "appId": 802699, "dataSetType": 34, "dc": "cn", ... },
  "nodeConf": [{ "clusterName": "sg", "dbName": "Hive-db-1", ... }],
  "linkConf": [],
  "whereConf": { "requiredRowFilter": [], "nodeRowFilter": {} },
  "dataTableConf": { "kafkaCluster": "cn" }
}
```

> 注: `dataTableConf` 为可选字段，海外 SG 环境通常不传此字段。

> **完整字段**: 实际请求中 `baseConf` 通常还包含: `enableResourceGroup`, `multiModalDataSourceType`, `modelType`, `confidentiality`, `logicalVersion`, `relationJoinType`, `joinType`, `groupId`, `groupName`, `groupType`, `isDataSetAndTableMixed`, `isPersonalDataRelated`, `aiInstructionAutoUpdate`。复制创建时还包含 `originalDataSetId`。SG 的典型 `dataSourceId` 为 `10138`（CN 为 `127`）。

**响应体**:

```json
{
  "code": "aeolus/ok",
  "msg": "成功",
  "data": {
    "dataSourceId": 127
  }
}
```

---

#### 5.2 获取所有集群列表

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/allClusterList2`
- **说明**: 获取所有可用计算集群的列表

**查询参数**: 无

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "clusterId": "number",
      "clusterName": "string",
      "clusterType": "string",
      "clusterStatus": "string"
    }
  ]
}
```

---

#### 5.3 按集群获取数据源

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dataSourceByCluster`
- **说明**: 获取指定集群下可用的数据源列表

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `clusterId` | number | 是 | 集群 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "dataSourceId": "number",
      "dataSourceName": "string",
      "dataSourceType": "string"
    }
  ]
}
```

---

### 6. 依赖与影响分析

#### 6.1 获取子依赖列表

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getSubDependencyList`
- **说明**: 获取数据集的下游依赖列表

**请求体**:

```json
{
  "dataSetId": "number",
  "dataSetVersionId": "number"
}
```

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "dependencyId": "number",
      "dependencyName": "string",
      "dependencyType": "string"
    }
  ]
}
```

---

#### 6.2 检查 DAG 影响

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/checkDagImpact`
- **说明**: 检查数据集变更对 DAG 调度任务的影响范围

**请求体**:

```json
{
  "dataSetId": 5428964,
  "nodeConf": [],
  "dimMetList": [],
  "originNodeConf": [],
  "syncConf": {},
  "linkConf": [],
  "whereConf": {}
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 是 | 数据集 ID |
| `nodeConf` | array | 是 | 当前（修改后的）节点配置 |
| `dimMetList` | array | 是 | 维度指标列表 |
| `originNodeConf` | array | 否 | 修改前的节点配置（用于对比变更影响） |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "impactList": ["object"],
    "hasImpact": "boolean"
  }
}
```

---

#### 6.3 检查数据集可回收性

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/checkDataSetRecyclable`
- **说明**: 检查数据集是否可以被回收删除

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetIds": [5429028]
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `appId` | number | 是 | 应用 ID |
| `dataSetIds` | number[] | 是 | 要检查的数据集 ID 列表 |

**响应体**:

```json
{
  "code": "aeolus/ok",
  "data": [],
  "msg": "成功"
}
```

`data` 为空数组表示可以回收，非空则包含阻碍信息。

---

#### 6.4 获取数据集血缘统计

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetLineageStatistics`
- **说明**: 获取数据集的下游依赖统计（下游数据集、看板、报表数量及访问量）

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5429028
}
```

**响应体**:

```json
{
  "code": "aeolus/ok",
  "data": {
    "belong": 1,
    "name": "dataset_name",
    "downstreamDataSetNum": 0,
    "downstreamDataSetHasUvNum": 0,
    "downstreamDashboardNum": 0,
    "downstreamDashboardHasUvNum": 0,
    "downstreamReportNum": 0,
    "downstreamReportHasUvNum": 0,
    "downstreamLargeScreenNum": 0,
    "downstreamPrepTaskNum": 0,
    "dimMetLevelAnalyze": false,
    "pv": 0,
    "uv": 0
  },
  "msg": "成功"
}
```

**响应体字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `downstreamDataSetNum` | number | 下游数据集数量 |
| `downstreamDashboardNum` | number | 下游看板数量 |
| `downstreamReportNum` | number | 下游报表数量 |
| `downstreamLargeScreenNum` | number | 下游大屏数量 |
| `downstreamPrepTaskNum` | number | 下游预处理任务数量 |
| `pv` | number | 访问量 |
| `uv` | number | 独立访问用户数 |

---

#### 6.5 回收删除数据集

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/recycleDataSet`
- **说明**: 回收（删除）指定数据集，建议先调用 `checkDataSetRecyclable` 和 `dataSetLineageStatistics` 确认安全

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetIdList": [5429028]
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `appId` | number | 是 | 应用 ID |
| `dataSetIdList` | number[] | 是 | 要删除的数据集 ID 列表 |

**响应体**:

```json
{
  "code": "aeolus/ok",
  "data": [],
  "msg": "成功"
}
```

> **注意**: `checkDataSetRecyclable` 使用 `dataSetIds` 字段，而 `recycleDataSet` 使用 `dataSetIdList` 字段，两者名称不同。

---

### 7. 锁操作

#### 7.1 获取数据集锁

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/acquireDataSetLock`
- **说明**: 获取数据集的编辑锁，防止并发编辑冲突

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5428964
}
```

**响应体**:

```json
{
  "code": "aeolus/ok",
  "data": {
    "canAcquireDataSetLock": true,
    "holder": "username",
    "expireTime": "2026-04-24T11:07:50"
  }
}
```

---

#### 7.2 释放数据集锁

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/releaseDataSetLock`
- **说明**: 释放数据集的编辑锁

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5428964
}
```

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "released": "boolean"
  }
}
```

---

### 8. 用户与权限

#### 8.1 获取当前用户

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/misc/current_user`
- **说明**: 获取当前登录用户的信息

**查询参数**: 无

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "userId": "string",
    "userName": "string",
    "displayName": "string",
    "email": "string"
  }
}
```

---

#### 8.2 检查是否可以创建数据集

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/authManagement/checkCanCreateDataSet`
- **说明**: 检查当前用户是否有创建数据集的权限

**查询参数**: 无

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "canCreate": "boolean",
    "reason": "string"
  }
}
```

---

### 9. 资源管理

#### 9.1 获取用户 YARN 队列列表

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/getUserYarnList`
- **说明**: 获取当前用户可用的 YARN 队列列表

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `clusterId` | number | 否 | 集群 ID，按集群筛选 |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "queueName": "string",
      "queuePath": "string"
    }
  ]
}
```

---

#### 9.2 获取用户加入的资源组列表

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/resourceGroup/userJoinedList`
- **说明**: 获取当前用户已加入的资源组列表

**查询参数**: 无

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "resourceGroupId": "number",
      "resourceGroupName": "string",
      "resourceGroupDesc": "string"
    }
  ]
}
```

---

### 10. 文件夹与分类

#### 10.1 获取数据集文件夹树 V2

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetFolderTreeV2`
- **说明**: 获取数据集文件夹的树形结构

**查询参数**: 无

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "folderId": "number",
      "folderName": "string",
      "parentFolderId": "number",
      "children": ["object"]
    }
  ]
}
```

> **区域差异**: SG 返回的 `data` 为分组字典 `{"official": [], "private": [], "public": [...]}`, CN 可能返回扁平列表 `[{...}]`。代码需要兼容两种格式。

---

#### 10.2 获取维度指标分类列表 V2

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dimMetCategoryListV2`
- **说明**: 获取维度和指标的分类列表

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 否 | 数据集 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "categoryId": "number",
      "categoryName": "string",
      "categoryType": "string",
      "children": ["object"]
    }
  ]
}
```

---

### 11. 状态与版本

#### 11.1 检查数据集是否就绪

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/isDataSetReady`
- **说明**: 检查数据集是否已就绪可用

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 是 | 数据集 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "ready": "boolean",
    "status": "string"
  }
}
```

---

#### 11.2 获取版本列表

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getVersionList`
- **说明**: 获取数据集的历史版本列表

**请求体**:

```json
{
  "dataSetId": "number",
  "pageNum": "number",
  "pageSize": "number"
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 是 | 数据集 ID |
| `pageNum` | number | 否 | 页码 |
| `pageSize` | number | 否 | 每页数量 |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "total": "number",
    "list": [
      {
        "dataSetVersionId": "number",
        "dataSetVersionType": "string",
        "createTime": "string",
        "creator": "string",
        "changeLog": "string"
      }
    ]
  }
}
```

---

### 12. 性能检测

#### 12.1 性能检测

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/detectPerformance`
- **说明**: 对数据集的 SQL 查询进行性能检测和分析

**请求体**:

```json
{
  "dataSetId": "number",
  "sql": "string",
  "clusterId": "number",
  "dataSourceId": "number"
}
```

**请求体字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dataSetId` | number | 否 | 数据集 ID |
| `sql` | string | 是 | 待检测的 SQL 语句 |
| `clusterId` | number | 是 | 集群 ID |
| `dataSourceId` | number | 是 | 数据源 ID |

**响应体**:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "performanceLevel": "string",
    "suggestions": ["string"],
    "details": "object"
  }
}
```

---

### 13. nodeConf 关键字段

`nodeConf` 是数据集配置中描述画布节点的核心结构，每个元素代表一个 SQL 节点。以下为关键字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `relationTableType` | number | 表类型，`1`=事实表（必填），不设置会报"画布中必须存在事实表" |
| `factTableConf` | object | 事实表配置，如 `{"enableBizDate": false, "lastDataRule": "common"}` |
| `partitionConfList` | array | 分区配置列表 |
| `sourceTableList` | array | 源表列表 |
| `fields` | array | 字段列表（来自 SQL schema 解析） |
| `tbId` | string | 表 ID |
| `nodeType` | string | 节点类型 |
| `dataSourceType` | string | 数据源类型 |
| `clusterName` | string | 集群名称（国内 `"cn"`，海外 SG `"sg"`） |
| `dbName` | string | 数据库名称 |
| `tbName` | string | 表名 |
| `query` | string | SQL 查询语句 |
| `id` | string | 节点 ID |

---

### 14. 数据同步（回溯）

#### 14.1 获取同步配置

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetSyncSettingsBatch?appId={appId}&dataSetId={dataSetId}`
- **说明**: 获取数据集的同步调度配置（频率、TTL、分区配置、监控告警等）

**响应**:

```json
{
  "code": "aeolus/ok",
  "data": {
    "syncScheduleConf": [
      {
        "scheduleConf": { "frequency": "daily", "scheduleTime": "00:00" },
        "ttl": 7,
        "ttlType": 1,
        "backtrackingConf": { "enable": 1, "dateRange": { "startDate": "2026-04-23", "endDate": "2026-04-23" } }
      }
    ],
    "upstreamSettings": {
      "partitionConfList": [
        { "partitionKey": "date", "partitionValue": "${date}", "operator": "=" }
      ]
    },
    "monitorConf": { "alarmRules": [] }
  }
}
```

#### 14.2 查询同步实例列表

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/dataSetSyncInfoAllPageBatch`
- **说明**: 查询指定日期范围内各分区的同步状态

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5492281,
  "startDate": "2026-03-25",
  "endDate": "2026-04-24",
  "refresh": 0,
  "nodeIdList": ["cn//Hive-db-1//Hive-sql-1"],
  "filterByTtl": false,
  "materializeNodeIdList": []
}
```

**响应**（`syncStatus`: `1`=等待中, `2`=未开始, `3`=运行中, `4`=成功, `5`=失败）:

```json
{
  "code": "aeolus/ok",
  "data": {
    "hasValidInstance": true,
    "instanceList": [
      {
        "bizTimePage": "2026-04-23",
        "syncStatus": 4,
        "tableSize": "6,276,977",
        "instanceId": 6343852938,
        "taskId": 125476132,
        "nodeId": "cn//Hive-db-1//Hive-sql-1"
      }
    ]
  }
}
```

#### 14.3 获取可回溯分区日期范围

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getSyncPartitionValuesBatch`
- **说明**: 获取数据集各节点可回溯的分区日期范围

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5492281,
  "nodeIdList": ["cn//Hive-db-1//Hive-sql-1"]
}
```

**响应**:

```json
{
  "code": "aeolus/ok",
  "data": {
    "startDate": "2026-04-17",
    "endDate": "2026-04-23",
    "syncPartitionValues": [
      {
        "nodeId": "cn//Hive-db-1//Hive-sql-1",
        "startDate": "2026-04-17",
        "endDate": "2026-04-23",
        "hasForeverTtl": false
      }
    ]
  }
}
```

> **nodeId 格式差异**: CN 使用 `"cn//Hive-db-1//Hive-sql-1"` 格式的 tbId 作为 nodeId，SG 使用 UUID 格式的 nodeId（如 `"32205cb5-4eba-4d7d-9735-87471d2eae70"`）。SG 的 nodeId 需要从 `dataSetOverview` API 响应的 `subDataSetStatusMap` 中获取对应节点的 key。

#### 14.4 检查队列和并行度

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/checkShowPartitionQueueBatch`
- **说明**: 检查回溯时的队列配置、最大并行度、是否允许指定队列等

**请求体**:

```json
{
  "dataSetId": 5492281,
  "appId": 1006036,
  "nodeIdList": ["cn//Hive-db-1//Hive-sql-1"]
}
```

**响应**:

```json
{
  "code": "aeolus/ok",
  "data": {
    "showSpecifyQueue": true,
    "maxParallelism": 5,
    "forbiddenIgnoreDependency": false,
    "showPartitionCheck": false,
    "dataSetQueueInfo": {
      "queue": "root.millipede4_stone_ai_application_coding",
      "clusterId": "millipede4-lf",
      "queueStatus": "busy",
      "isDefault": true
    }
  }
}
```

#### 14.5 查询回溯实例数

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/getLookbackInstancesNum`
- **说明**: 查询指定日期范围内将生成的回溯实例数量

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5492281,
  "nodeIdList": ["cn//Hive-db-1//Hive-sql-1"],
  "startDate": "2026-04-22",
  "endDate": "2026-04-23",
  "dispersedDateList": []
}
```

**响应**:

```json
{
  "code": "aeolus/ok",
  "data": { "instancesNum": 1 }
}
```

#### 14.6 获取回溯可用 Yarn 队列

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/getUserYarnList?appId={appId}&dataSetId={dataSetId}&queueTaskTagList=backfill`
- **说明**: 获取回溯专用的 Yarn 队列列表（与普通 getUserYarnList 的区别是带 `queueTaskTagList=backfill` 参数）

#### 14.7 提交回溯任务

- **Method**: `POST`
- **Path**: `/aeolus/api/v3/dataFactory/createSyncJob`
- **说明**: 提交回溯（数据同步）任务，异步执行，返回 `previewId` 用于轮询结果

**请求体**:

```json
{
  "appId": 1006036,
  "dataSetId": 5492281,
  "startDate": "2026-04-22",
  "endDate": "2026-04-23",
  "dispersedDateList": [],
  "checkMinMax": true,
  "intervalStartTime": null,
  "intervalEndTime": null,
  "skipCheck": false,
  "isSpecifyQueue": false,
  "queueName": "root.millipede4_stone_ai_application_coding",
  "maxParallelism": 5,
  "isSpecifyRunTime": false,
  "partitionCheck": false,
  "nodeIdList": ["cn//Hive-db-1//Hive-sql-1"],
  "materializeNodeIdList": []
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `appId` | number | 是 | 应用 ID |
| `dataSetId` | number | 是 | 数据集 ID |
| `startDate` | string | 是 | 回溯开始日期 (yyyy-MM-dd) |
| `endDate` | string | 是 | 回溯结束日期 (yyyy-MM-dd) |
| `nodeIdList` | array | 是 | 节点 ID 列表 |
| `queueName` | string | 否 | Yarn 队列名称 |
| `maxParallelism` | number | 否 | 最大并行度（默认 5） |
| `isSpecifyQueue` | boolean | 否 | 是否指定队列 |
| `skipCheck` | boolean | 否 | 是否跳过检查 |
| `checkMinMax` | boolean | 否 | 是否检查日期边界 |
| `partitionCheck` | boolean | 否 | 是否进行分区检查 |
| `dispersedDateList` | array | 否 | 离散日期列表 |

> **nodeId 格式差异**: CN 使用 `"cn//Hive-db-1//Hive-sql-1"` 格式的 tbId 作为 nodeId，SG 使用 UUID 格式的 nodeId（如 `"32205cb5-4eba-4d7d-9735-87471d2eae70"`）。SG 的 nodeId 需要从 `dataSetOverview` API 响应的 `subDataSetStatusMap` 中获取对应节点的 key。

> **CN vs SG 字段差异**: CN 使用精简字段集（含 `refresh:0`, `filterByTtl:false`），SG 使用完整字段集（含 `dispersedDateList`, `checkMinMax`, `isSpecifyQueue`, `queueName`, `maxParallelism` 等）。

**响应**:

```json
{
  "code": "aeolus/ok",
  "data": { "previewId": "094721ea-8848-4687-a49d-ed1ed7dbd755" }
}
```

#### 14.8 轮询回溯任务结果

- **Method**: `GET`
- **Path**: `/aeolus/api/v3/dataFactory/getCreateSyncJobResult?previewId={previewId}`
- **说明**: 轮询回溯任务的提交状态

**响应**（运行中）:

```json
{
  "code": "aeolus/ok",
  "data": { "startTime": 1777011683.231583, "status": "RUNNING" }
}
```

**响应**（成功）:

```json
{
  "code": "aeolus/ok",
  "data": { "status": "SUCCEEDED" }
}
```

### 回溯（数据同步）的完整 API 调用流程

从 HAR 抓包分析，浏览器发起回溯的完整 API 调用顺序：

1. `GET dataSetModelInfo` — 获取数据集配置（提取 nodeIdList）
2. `GET dataSetSyncSettingsBatch` — 获取同步配置
3. `POST dataSetSyncInfoAllPageBatch` — 查询当前同步实例状态
4. `POST getSyncPartitionValuesBatch` — 获取可回溯分区范围
5. `POST checkShowPartitionQueueBatch` — 检查队列和并行度
6. `POST getLookbackInstancesNum` — 查询回溯实例数（用户选择日期后）
7. `GET getUserYarnList?queueTaskTagList=backfill` — 获取回溯可用队列（可选）
8. `POST createSyncJob` — 提交回溯任务
9. `GET getCreateSyncJobResult` — 轮询任务提交状态（RUNNING → SUCCEEDED）
10. `POST dataSetSyncInfoAllPageBatch` — 刷新同步状态（确认回溯已生效）

脚本中 `DatasetEditor.backfill()` 方法封装了步骤 4-9，自动从 nodeConf 提取 nodeIdList。

---

## 通用响应格式

所有 API 响应均遵循统一格式：

```json
{
  "code": "string | number",
  "msg": "string",
  "data": "object | array | null"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string/number | 状态码，成功时为 `"aeolus/ok"` 或 `0`，失败时为错误码字符串如 `"aeolus/dag/dagAbnormal"` |
| `msg` | string | 响应消息，成功时为 `success`，失败时为错误描述 |
| `data` | any | 响应数据，具体结构因接口而异 |

## 常见错误码

| 错误码 | 说明 |
|--------|------|
| `aeolus/ok` 或 `0` | 成功 |
| `3` | 请求参数错误（如字段重复、类型缺失等） |
| `aeolus/dag/dagAbnormal` | DAG 异常（如画布中缺少事实表） |
| `aeolus/dataSet/saveForbidden` | 数据集禁止保存（如刚创建后立即更新） |

## 请求示例

### cURL 示例

```bash
# 国内
curl -X POST 'https://data.bytedance.net/aeolus/api/v3/dataFactory/dataSetV2' \
# 海外 SG
# curl -X POST 'https://aeolus-sg.tiktok-row.net/aeolus/api/v3/dataFactory/dataSetV2' \
  -H 'Content-Type: application/json' \
  -H 'x-titan-token: <your_jwt_token>' \
  -H 'app-id: <your_app_id>' \
  -H 'request-id: 550e8400-e29b-41d4-a716-446655440000' \
  -H 'request-timestamp: 1712649600000' \
  -H 'content-language: zh-CN' \
  -d '{
    "dataSetName": "example_dataset",
    "dataSetDisplayName": "示例数据集",
    "dataSetType": "offline",
    "clusterId": 1,
    "dataSourceId": 100,
    "sql": "SELECT * FROM example_table",
    "owners": ["user@bytedance.com"]
  }'
```

### Python 示例

```python
import requests
import uuid
import time

BASE_URL = "https://data.bytedance.net"  # 国内; 海外 SG: "https://aeolus-sg.tiktok-row.net"

headers = {
    "Content-Type": "application/json",
    "x-titan-token": "<your_jwt_token>",
    "app-id": "<your_app_id>",
    "request-id": str(uuid.uuid4()),
    "request-timestamp": str(int(time.time() * 1000)),
    "content-language": "zh-CN",
}

response = requests.post(
    f"{BASE_URL}/aeolus/api/v3/dataFactory/dataSetV2",
    headers=headers,
    json={
        "dataSetName": "example_dataset",
        "dataSetDisplayName": "示例数据集",
        "dataSetType": "offline",
        "clusterId": 1,
        "dataSourceId": 100,
        "sql": "SELECT * FROM example_table",
        "owners": ["user@bytedance.com"],
    },
)

print(response.json())
```

---

## 数据模型：dimMetList（维度指标列表）

创建和更新数据集时，`dimMetList` 是核心字段，定义了数据集的维度和指标。

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 字段名（对应 SQL SELECT 中的列名） |
| `expr` | string | 表达式（通常等于 name） |
| `defaultType` | string | 数据类型：`date`, `datetime`, `string`, `int`, `float` |
| `dataTypeName` | string | 数据类型名（与 defaultType 相同，API 同时接受两者） |
| `mapType` | int | 0=维度, 1=指标 |
| `dimMetVariety` | int | 0=普通字段, 1=分区字段(p_date), 2=时间字段(datetime) |
| `filterType` | string | 筛选类型：`date`, `datetime`, `string`, `float` |
| `dimMetMixOrder` | int | 排序序号 |
| `dimMetOrder` | int | 排序序号 |
| `visible` | int | 是否可见：1=可见 |
| `showExpr` | int | 是否显示表达式：1=显示 |
| `editable` | int | 是否可编辑：0=不可编辑(p_date), 1=可编辑 |
| `isAutoAdd` | int | 是否自动添加：1=自动添加(p_date) |
| `groupType` | int | 分组类型：0=默认 |
| `id` | int | 字段 ID（更新已有数据集时需要传入已有字段的 ID） |
| `tempId` | int | 临时 ID（创建新字段时使用，毫秒级时间戳） |
| `isUpstreamField` | bool | 是否为上游字段：普通字段为 `true`，`p_date` 为 `false` |
| `originType` | string | 原始 SQL 类型（如 `string`、`bigint`，编辑已有数据集时保留） |
| `castDataTypeName` | null | 类型转换（一般为 null） |
| `dimMetCategoryId` | null | 分类 ID（一般为 null） |
| `dimMetCategoryType` | null | 分类类型（一般为 null） |
| `geoInfo` | null | 地理信息（一般为 null） |

### 类型映射

nodeConf.fields 的 `prepType` 到 dimMetList 类型的映射：

| prepType (nodeConf) | defaultType (dimMet) | filterType | dimMetVariety |
|---------------------|---------------------|------------|---------------|
| `timestamp` | `datetime` | `datetime` | `2` (时间字段) |
| `date` | `date` | `date` | `0` |
| `string` | `string` | `string` | `0` |
| `long` / `int` / `bigint` | `int` | `float` | `0` |
| `double` / `float` | `float` | `float` | `0` |

### p_date 分区字段

`p_date` 是自动添加的日期分区字段，格式固定：

```json
{
  "name": "p_date",
  "expr": "p_date",
  "defaultType": "date",
  "dataTypeName": "date",
  "filterType": "date",
  "mapType": 0,
  "dimMetVariety": 1,
  "isAutoAdd": 1,
  "autoAddType": 1,
  "editable": 0,
  "isUpstreamField": false
}
```

### 关键注意事项

1. **同时设置 `defaultType` 和 `dataTypeName`**：API 在不同场景下可能读取不同字段名，同时设置两者可确保类型正确识别。
2. **`p_date` 不在 nodeConf.fields 中**：SQL schema 解析结果（nodeConf.fields）不包含 `p_date`，需要在 dimMetList 中手动添加。同时，如果 SQL 中 SELECT 了 `p_date`，schema 中会出现，需要跳过避免重复。
3. **更新时保留字段 ID**：修改已有数据集时，dimMetList 中的已有字段需要保留原有的 `id` 值（从 `allDataSetInfoV2` 获取）。
4. **`allDataSetInfoV2` vs `dataSetModelInfo`**：`dataSetModelInfo` API 返回的 `dimMetList` 可能为空，需要从 `allDataSetInfoV2` 补充获取完整的维度指标列表。

### SQL 日期变量

风神 SQL 中使用以下系统日期变量实现动态日期查询（**不要使用 Jinja 模板语法 `{{ ds }}`**）：

| 变量 | 格式 | 示例 |
|------|------|------|
| `${DATE}` | yyyy-MM-dd | 2025-05-17 |
| `${date}` | yyyyMMdd | 20250526 |
| `${DATE+n}` / `${DATE-n}` | yyyy-MM-dd，往后(+)/往前(-)n天 | `${DATE-1}` = 昨天 |
| `${date+n}` / `${date-n}` | yyyyMMdd，往后(+)/往前(-)n天 | `${date-1}` = 昨天 |

### prepType 与 Hive 类型映射

`nodeConf.fields` 中有两个类型字段：
- **`type`**：保留原始 Hive 类型（如 `bigint`、`timestamp`）
- **`prepType`**：风神中间类型，用于类型转换和维度指标判定

手动构造 `nodeConf.fields` 时，两者都需要提供。**不需要** `alias` 和 `isSupport` 属性。

| Hive 类型 | type (原始) | prepType (中间) | dimMetList.defaultType | 说明 |
|-----------|------------|----------------|----------------------|------|
| `string` | `string` | `string` | `string` | 直接对应 |
| `bigint` | `bigint` | `long` | `int` | **type 保留 bigint，prepType 用 long** |
| `int` / `tinyint` / `smallint` | 原始值 | `int` | `int` | 整数类型 prepType 统一用 `int` |
| `double` | `double` | `double` | `float` | dimMetList 中为 float |
| `float` | `float` | `float` | `float` | 直接对应 |
| `timestamp` | `timestamp` | `timestamp` | `datetime` | dimMetList 中为 datetime |
| `date` | `date` | `date` | `date` | 直接对应 |
| `boolean` | `boolean` | `string` | `string` | 风神无 boolean 类型 |

### 创建后发布注意事项

- 新建数据集后 ClickHouse 表需要时间创建（通常 10-30s），发布时可能报 `getTableSchemaFailed` 错误。
- 脚本 `create_new(publish=True)` 和 `create_from(publish=True)` 已内置自动重试逻辑（最多 3 次，间隔递增 10s/20s/30s）。
- 删除的数据集名称可能仍被占用（回收站机制），如需同名重建请更换名称。

### 修改数据集的完整 API 调用流程（从 HAR 抓包分析）

编辑已有数据集并发布上线的完整 API 调用时序：

```
1. allDataSetInfoV2 (GET, enableDraftDataSet=true)  — 获取数据集完整配置
2. acquireDataSetLock (POST, 含 appId)              — 获取编辑锁（之后每 ~10s 续期）
3. getTableSchemaFromSql (POST)                     — 提交 SQL 异步解析（⚠️ 编辑时须传 dataSetId）
4. getTableSchemaFromSqlResult (POST × N)           — 轮询解析结果（~2s 间隔，成功状态为 SUCCEEDED）
5. previewSchema (POST)                             — 预览 Schema（编辑时 type="dataSetEditV2/getSchemaAlias"）
6. determineDataSetTypeV2 (POST)                    — 判定数据集类型
7. checkDagImpact (POST)                            — DAG 影响检查（传 dataSetId + originNodeConf）
8. preCheckDimMetList (POST)                        — 预检查维度指标（返回 checkDimMetId）
9. getSubDependencyList (POST)                      — 获取上游依赖
10. checkDimMetName (POST)                          — 校验维度指标名称唯一性（传 dataSetId）
11. dataSetV2 (PUT)                                  — 保存并发布（fields 含 alias + isSupport）
12. releaseDataSetLock (POST, 含 appId)             — 释放编辑锁
```

**关键细节**：
- `getTableSchemaFromSql` 和 `getTableSchemaFromSqlResult` 在**编辑已有数据集时**必须传 `dataSetId` 参数，否则可能导致解析超时。浏览器实际解析仅需 ~4 秒。
- `getTableSchemaFromSqlResult` 成功状态为 `"SUCCEEDED"`（脚本同时兼容 `"FINISHED"`）。
- `previewSchema` 的 `type` 参数：创建时为 `"create"`，编辑时为 `"dataSetEditV2/getSchemaAlias"`。

> **注意**: HAR 分析显示，SG 的创建（复制）和编辑流程中 `type` 均使用 `"dataSetEditV2/getSchemaAlias"` 而非 `"create"`。全新创建场景中的 `type` 值可能因区域而异。

- `acquireDataSetLock` 和 `releaseDataSetLock` 请求体需包含 `appId`。
- `checkDagImpact` 需传入 `dataSetId` 和 `originNodeConf`（修改前的节点配置，用于对比变更影响）。
- PUT body 中 `parseEngine` 字段值通常为 `1`。
- **编辑场景不需要调用 `determineCluster`**，也不需要在 PUT body 中传 `dataTableConf`。`data_source_id` 从已有 `syncConf.performanceSettings.dataSourceId` 获取。
- PUT body 中 `nodeConf.fields` 需包含 `alias`（如 `` `field_name` ``）和 `isSupport`（`true`），但 `previewSchema` 请求中不需要这两个字段。
- `MAX(CASE WHEN ... THEN 1 ELSE 0 END)` 聚合表达式的返回类型为 `int`（prepType），不是 `long`。

### nodeConf.fields 在不同 API 中的格式

| API | 字段属性 |
|-----|---------|
| `previewSchema` 请求 | `name`, `type`, `prepType`, `isSourceTableField`, `isSelect`, `isDynamicPartition`（6个） |
| `POST/PUT dataSetV2` 保存 | 上述 6 个 + `alias`（如 `` `name` ``）、`isSupport`（`true`）（8个） |
| `allDataSetInfoV2` 响应 | 上述 8 个 + `status` 等服务端附加字段 |
