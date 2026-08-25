import json
import sys
import os
import re
import copy
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import requests

try:
    import yaml
except ImportError:
    yaml = None


_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_CACHE = None

# ── Region configuration ──
_REGION_CONF = {
    "cn": {
        "base_url": "https://data.bytedance.net",
        "page_url": "https://data.bytedance.net/aeolus",
        "aeolus_url": "https://data.bytedance.net/aeolus/pages/dataManage?appId={app_id}",
        "dataset_url": "https://data.bytedance.net/aeolus/pages/dataManage/detail/{data_set_id}?appId={app_id}&belong=1",
        "cluster": "cn",
        "default_app_id": 1006036,
    },
    "sg": {
        "base_url": "https://aeolus-sg.tiktok-row.net",
        "page_url": "https://aeolus-sg.tiktok-row.net",
        "aeolus_url": "https://aeolus-sg.tiktok-row.net/pages/dataManage?appId={app_id}",
        "dataset_url": "https://aeolus-sg.tiktok-row.net/pages/dataManage/detail/{data_set_id}?appId={app_id}&belong=1",
        "cluster": "sg",
        "default_app_id": 802699,
    },
}


def load_config(config_path=None):
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and config_path is None:
        return _CONFIG_CACHE
    if config_path is None:
        config_path = _SCRIPT_DIR / "config.yaml"
    else:
        config_path = Path(config_path)
    if not config_path.exists():
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE
    text = config_path.read_text(encoding="utf-8")
    if yaml is not None:
        _CONFIG_CACHE = yaml.safe_load(text) or {}
    else:
        _CONFIG_CACHE = _parse_simple_yaml(text)
    return _CONFIG_CACHE


def _parse_simple_yaml(text):
    result = {}
    current_section = None
    current_subsection = None
    for line in text.splitlines():
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue
        # Top-level key (no indent)
        if not stripped.startswith(" ") and ":" in stripped:
            key_part = stripped.split(":", 1)
            key = key_part[0].strip()
            val = key_part[1].strip().strip('"').strip("'") if key_part[1].strip() else None
            if val is None or val == "":
                # Section header
                current_section = key
                current_subsection = None
                result[current_section] = {}
            else:
                # Top-level scalar (like default_region: "cn")
                if val.lower() == "true": val = True
                elif val.lower() == "false": val = False
                elif val.isdigit(): val = int(val)
                result[key] = val
                current_section = None
                current_subsection = None
        elif current_section and ":" in stripped:
            indent = len(stripped) - len(stripped.lstrip())
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val == "" or val is None:
                # Subsection (e.g., "  cn:" under "regions")
                current_subsection = key
                result[current_section][current_subsection] = {}
            else:
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1]
                    val = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.isdigit():
                    val = int(val)
                if current_subsection and isinstance(result[current_section].get(current_subsection), dict):
                    result[current_section][current_subsection][key] = val
                else:
                    result[current_section][key] = val
    return result


def _cfg(section, key, default=None):
    conf = load_config()
    return conf.get(section, {}).get(key, default)


def _cfg_region(region, key, default=None):
    """Get a region-specific config value from regions.<region>.<key>."""
    conf = load_config()
    regions = conf.get("regions", {})
    region_conf = regions.get(region, {})
    if region_conf and key in region_conf:
        return region_conf[key]
    return default


def _get_region():
    """Get default region from config or default to 'cn'."""
    conf = load_config()
    return conf.get("default_region") or _cfg("app", "region") or "cn"


def _region_conf(region=None):
    """Get region configuration dict."""
    if region is None:
        region = _get_region()
    region = region.lower()
    if region not in _REGION_CONF:
        raise ValueError(f"Unsupported region '{region}'. Supported: {list(_REGION_CONF.keys())}")
    return _REGION_CONF[region]


def dataset_url(app_id, data_set_id, region=None):
    rc = _region_conf(region)
    return rc["dataset_url"].format(app_id=app_id, data_set_id=data_set_id)


def extract_dataset_id(url_or_id):
    if isinstance(url_or_id, int):
        return url_or_id
    s = str(url_or_id).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'/detail/(\d+)', s) or re.search(r'dataSetId=(\d+)', s) or re.search(r'(\d{5,})', s)
    if m:
        return int(m.group(1))
    raise ValueError(f"无法从 '{s}' 中提取 dataSetId，请提供数字 ID 或 Aeolus 数据集 URL")


def parse_aeolus_url(url):
    from urllib.parse import urlparse, parse_qs
    s = str(url).strip()
    result = {}

    # Detect region from URL domain
    parsed = urlparse(s)
    if "tiktok-row.net" in (parsed.hostname or ""):
        result["region"] = "sg"
    elif "data.bytedance.net" in (parsed.hostname or ""):
        result["region"] = "cn"

    m = re.search(r'/detail/(\d+)', s)
    if m:
        result["data_set_id"] = int(m.group(1))
    else:
        m = re.search(r'dataSetId=(\d+)', s)
        if m:
            result["data_set_id"] = int(m.group(1))
    qs = parse_qs(parsed.query)
    if "appId" in qs:
        result["app_id"] = int(qs["appId"][0])
    return result


def _gen_request_id():
    return str(uuid.uuid4())


def _gen_trace_id():
    base = str(uuid.uuid4())
    suffix = uuid.uuid4().hex[:20]
    return f"{base}.{suffix}"


def auto_get_token(domain=None, region=None):
    if domain is None:
        rc = _region_conf(region)
        domain = rc["page_url"]
    try:
        from pycookiecheat import chrome_cookies
        cookies = chrome_cookies(domain)
        if not cookies:
            return None
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        resp = requests.get(
            domain,
            headers={
                "Cookie": cookie_str,
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
            allow_redirects=True,
            timeout=15,
        )
        match = re.search(r'window\.__titan_passport_token\s*=\s*"([^"]+)"', resp.text)
        if match:
            return match.group(1)
        return None
    except ImportError:
        return None
    except Exception:
        return None


class AeolusClient:
    def __init__(self, token_file=None, token_str=None, app_id=None, region=None):
        self.region = region or _get_region()
        self._rc = _region_conf(self.region)
        self.base_url = self._rc["base_url"]

        if token_str:
            self.token = token_str
        else:
            if token_file is None:
                suffix = f"_{self.region}" if self.region != "cn" else ""
                token_file = _SCRIPT_DIR / f"token{suffix}.txt"
            token_path = Path(token_file)
            if token_path.exists() and token_path.read_text(encoding="utf-8").strip():
                self.token = token_path.read_text(encoding="utf-8").strip()
            else:
                auto_token = auto_get_token(region=self.region)
                if auto_token:
                    self.token = auto_token
                    token_path.write_text(auto_token, encoding="utf-8")
                    print(f"✓ 已从 Chrome 浏览器自动获取 x-titan-token ({self.region})")
                else:
                    raise FileNotFoundError(
                        f"Token 文件不存在或为空: {token_path}\n"
                        "请从浏览器获取 x-titan-token:\n"
                        f"  1. 打开 Chrome DevTools (F12)\n"
                        f"  2. 切换到 Network 标签\n"
                        f"  3. 访问 {self._rc['page_url']} 页面\n"
                        "  4. 找到任意 /aeolus/api/ 请求\n"
                        "  5. 复制 Request Headers 中的 x-titan-token 值\n"
                        f"  6. 写入 {token_path}\n"
                        "或安装 pycookiecheat（pip install pycookiecheat）自动获取"
                    )

        self.app_id = app_id or _cfg_region(self.region, "app_id") or _cfg("app", "app_id", self._rc["default_app_id"])
        self.session = requests.Session()
        self._cached_yarn = None
        self._cached_parent_id = None

    def _headers(self):
        rid = _gen_request_id()
        return {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "x-titan-token": self.token,
            "app-id": str(self.app_id),
            "x-aeolus-gray-env": "aeolus-online",
            "content-language": "zh-CN",
            "request-id": rid,
            "request-timestamp": str(int(time.time() * 1000)),
            "x-request-id": rid,
            "x-page-url": self._rc["aeolus_url"].format(app_id=self.app_id),
            "referer": self._rc["aeolus_url"].format(app_id=self.app_id),
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

    def _request(self, method, path, params=None, json_body=None):
        url = f"{self.base_url}{path}"
        resp = self.session.request(
            method, url,
            headers=self._headers(),
            params=params,
            json=json_body,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {method} {path}\n{resp.text[:500]}")
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"响应非 JSON: {resp.text[:500]}")
        code = data.get("code", "")
        code_str = str(code)
        if code_str not in ("aeolus/ok", "0"):
            msg = data.get("msg") or data.get("extra_msg") or str(data)
            raise RuntimeError(f"API 错误 (code={code}): {msg}")
        return data

    def _get(self, path, **params):
        params = {k: v for k, v in params.items() if v is not None}
        return self._request("GET", path, params=params)

    def _post(self, path, body, **params):
        params = {k: v for k, v in params.items() if v is not None}
        return self._request("POST", path, params=params if params else None, json_body=body)

    def _put(self, path, body, **params):
        params = {k: v for k, v in params.items() if v is not None}
        return self._request("PUT", path, params=params if params else None, json_body=body)

    def current_user(self):
        return self._get("/aeolus/api/v3/misc/current_user", withPhoneNumber="true")

    def check_can_create(self):
        return self._get("/aeolus/api/v3/authManagement/checkCanCreateDataSet", appId=str(self.app_id))

    def get_cluster_list(self):
        return self._get(
            "/aeolus/api/v3/dataFactory/allClusterList2",
            appId=str(self.app_id), taskType="-1",
            serviceType="data_set", dataSetVersion="v2",
            enableLogicalDataSet="true",
        )

    def get_data_source_by_cluster(self, data_source_type="hive", cluster_name=None):
        if cluster_name is None:
            cluster_name = _cfg_region(self.region, "cluster") or self._rc["cluster"]
        return self._get(
            "/aeolus/api/v3/dataFactory/dataSourceByCluster",
            dataSourceType=data_source_type, clusterName=cluster_name,
            appId=str(self.app_id), joinMode="",
        )

    def get_user_yarn_list(self):
        return self._get(
            "/aeolus/api/v3/dataFactory/getUserYarnList",
            appId=str(self.app_id), queueTaskTagList="routine",
        )

    def get_resource_group_list(self):
        return self._get("/aeolus/api/v3/resourceGroup/userJoinedList", appId=str(self.app_id))

    def get_folder_tree(self):
        return self._get("/aeolus/api/v3/dataFactory/dataSetFolderTreeV2", appId=str(self.app_id))

    def get_dataset_tree(self, parent_id=0, kw=""):
        return self._get(
            "/aeolus/api/v3/dataFactory/dataSetTreeViewV2",
            appId=str(self.app_id), parentId=str(parent_id),
            kw=kw, ownerOnly="0", favorOnly="0", resType="0",
            expandFolder="", refreshShareOrder="1", resTypeStrList="",
        )

    def get_dataset_overview(self, data_set_id):
        return self._get(
            "/aeolus/api/v3/dataFactory/dataSetOverview",
            appId=str(self.app_id), dataSetId=str(data_set_id),
        )

    def get_dataset_model_info(self, data_set_id):
        return self._get(
            "/aeolus/api/v3/dataFactory/dataSetModelInfo",
            appId=str(self.app_id), dataSetId=str(data_set_id),
        )

    def get_table_schema_from_sql(self, query, data_source_type="hive", cluster_name=None,
                                      db_name="Hive-db-1", data_set_id=None):
        if cluster_name is None:
            cluster_name = _cfg_region(self.region, "cluster") or self._rc["cluster"]
        body = {
            "appId": self.app_id,
            "dataSetType": 34,
            "connectionMode": 0,
            "serviceType": "data_set",
            "dataSourceType": data_source_type,
            "clusterName": cluster_name,
            "dbName": db_name,
            "query": query,
            "parseEngine": 1,
        }
        if data_set_id is not None:
            body["dataSetId"] = data_set_id
        return self._post("/aeolus/api/v3/dataFactory/getTableSchemaFromSql", body)

    def get_table_schema_from_sql_result(self, query, preview_id, data_source_type="hive",
                                          cluster_name=None, db_name="Hive-db-1", data_set_id=None):
        if cluster_name is None:
            cluster_name = _cfg_region(self.region, "cluster") or self._rc["cluster"]
        body = {
            "appId": self.app_id,
            "dataSetType": 34,
            "connectionMode": 0,
            "serviceType": "data_set",
            "dataSourceType": data_source_type,
            "clusterName": cluster_name,
            "dbName": db_name,
            "query": query,
            "previewId": preview_id,
        }
        if data_set_id is not None:
            body["dataSetId"] = data_set_id
        return self._post("/aeolus/api/v3/dataFactory/getTableSchemaFromSqlResult", body)

    def wait_for_schema(self, query, data_source_type="hive", cluster_name=None,
                        db_name="Hive-db-1", timeout=300, poll_interval=3, data_set_id=None):
        if cluster_name is None:
            cluster_name = _cfg_region(self.region, "cluster") or self._rc["cluster"]
        result = self.get_table_schema_from_sql(query, data_source_type, cluster_name, db_name, data_set_id)
        preview_id = result["data"]["previewId"]
        print(f"  SQL 解析任务已提交 (previewId={preview_id}), 最长等待 {timeout}s...")

        start = time.time()
        last_print_time = start
        while time.time() - start < timeout:
            result = self.get_table_schema_from_sql_result(
                query, preview_id, data_source_type, cluster_name, db_name, data_set_id,
            )
            status = result.get("data", {}).get("status", "")
            if status in ("FINISHED", "SUCCEEDED"):
                print("  ✓ SQL Schema 解析完成")
                return result["data"]
            if status == "FAILED":
                err_msg = result.get("data", {}).get("errorMsg", "unknown error")
                raise RuntimeError(f"SQL Schema 解析失败: {err_msg}")
            now = time.time()
            if now - last_print_time >= 30:
                elapsed = int(now - start)
                print(f"  ... 等待中 ({elapsed}s)")
                last_print_time = now
            time.sleep(poll_interval)

        raise TimeoutError(f"SQL Schema 解析超时 ({timeout}s)")

    def preview_schema(self, node_conf, data_set_type=34, is_edit=False):
        return self._post("/aeolus/api/v3/dataFactory/previewSchema", {
            "appId": self.app_id,
            "connectionMode": 0,
            "dataSetType": data_set_type,
            "nodeConf": node_conf,
            "fabricNeedAddPdate": True,
            "type": "dataSetEditV2/getSchemaAlias" if is_edit else "create",
        })

    def determine_dataset_type(self, node_conf, is_migrate=False, original_dataset_id=None):
        body = {
            "isMigrate": is_migrate,
            "nodeConf": node_conf,
            "connectionMode": 0,
        }
        if original_dataset_id:
            body["originalDataSetId"] = original_dataset_id
        return self._post("/aeolus/api/v3/dataFactory/determineDataSetTypeV2", body)

    def pre_check_dim_met_list(self, base_conf, dim_met_list, node_conf, link_conf=None, where_conf=None):
        return self._post("/aeolus/api/v3/dataFactory/preCheckDimMetList", {
            "baseConf": base_conf,
            "dimMetList": dim_met_list,
            "nodeConf": node_conf,
            "linkConf": link_conf or [],
            "whereConf": where_conf or {"requiredRowFilter": [], "nodeRowFilter": {}},
        })

    def determine_cluster(self, base_conf, node_conf, link_conf=None, data_table_conf=None, where_conf=None):
        body = {
            "baseConf": base_conf,
            "nodeConf": node_conf,
            "linkConf": link_conf or [],
            "whereConf": where_conf or {"requiredRowFilter": [], "nodeRowFilter": {}},
        }
        if data_table_conf is not None:
            body["dataTableConf"] = data_table_conf
        return self._post("/aeolus/api/v3/dataFactory/determineCluster", body)

    def check_dim_met_name(self, node_conf, dim_met_list, data_set_id=None):
        body = {
            "nodeConf": node_conf,
            "connectionMode": 0,
            "dimMetList": dim_met_list,
        }
        if data_set_id is not None:
            body["dataSetId"] = int(data_set_id)
        return self._post("/aeolus/api/v3/dataFactory/checkDimMetName", body)

    def get_sub_dependency_list(self, node_conf, data_set_id=None, where_conf=None, link_conf=None, sync_conf=None):
        body = {
            "appId": self.app_id,
            "nodeConf": node_conf,
            "whereConf": where_conf or {"requiredRowFilter": [], "nodeRowFilter": {}},
            "linkConf": link_conf or [],
            "version": "v2",
            "enableDraftDataSet": False,
            "syncConf": sync_conf or {},
            "dependencyGetConfList": [],
        }
        if data_set_id is not None:
            body["dataSetId"] = int(data_set_id)
        return self._post("/aeolus/api/v3/dataFactory/getSubDependencyList", body)

    def create_dataset(self, body, enable_save_without_migrate=True, enable_draft=False):
        return self._post(
            "/aeolus/api/v3/dataFactory/dataSetV2",
            body,
            enableSaveWithoutMigrate=str(enable_save_without_migrate).lower(),
            enableDraftDataSet=str(enable_draft).lower(),
        )

    def update_dataset(self, body, data_set_version_type=None,
                       enable_save_without_migrate=True, enable_draft=False):
        params = {
            "enableSaveWithoutMigrate": str(enable_save_without_migrate).lower(),
            "enableDraftDataSet": str(enable_draft).lower(),
        }
        if data_set_version_type is not None:
            params["dataSetVersionType"] = data_set_version_type
        return self._put("/aeolus/api/v3/dataFactory/dataSetV2", body, **params)

    def acquire_lock(self, data_set_id):
        return self._post("/aeolus/api/v3/dataFactory/acquireDataSetLock", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
        })

    def release_lock(self, data_set_id):
        return self._post("/aeolus/api/v3/dataFactory/releaseDataSetLock", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
        })

    def check_dag_impact(self, data_set_id, node_conf, dim_met_list,
                         origin_node_conf=None, sync_conf=None, link_conf=None, where_conf=None):
        return self._post("/aeolus/api/v3/dataFactory/checkDagImpact", {
            "dataSetId": int(data_set_id),
            "nodeConf": node_conf,
            "dimMetList": dim_met_list,
            "originNodeConf": origin_node_conf or node_conf,
            "syncConf": sync_conf or {},
            "linkConf": link_conf or [],
            "whereConf": where_conf or {"requiredRowFilter": [], "nodeRowFilter": {}},
        })

    def get_all_dataset_info(self, data_set_id):
        return self._get(
            "/aeolus/api/v3/dataFactory/allDataSetInfoV2",
            appId=str(self.app_id), dataSetId=str(data_set_id),
            enableDraftDataSet="true",
        )

    def get_version_list(self, data_set_id, page=1, page_size=10):
        return self._post("/aeolus/api/v3/dataFactory/getVersionList", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
            "page": page,
            "pageSize": page_size,
        })

    def get_version(self, version_id):
        return self._post("/aeolus/api/v3/dataFactory/getVersion", {
            "id": int(version_id),
        })

    def over_limit_node(self, data_set_id):
        return self._post("/aeolus/api/v3/dataFactory/overLimitNode", {
            "dataSetId": int(data_set_id),
        })

    def is_dataset_ready(self, data_set_id):
        return self._get(
            "/aeolus/api/v3/dataFactory/isDataSetReady",
            appId=str(self.app_id), dataSetId=str(data_set_id),
        )

    def list_datasets(self, owner=None, page=1, per_page=50, kw=""):
        if owner is None:
            owner = _cfg("user", "owner")
        body = {
            "page": page,
            "perPage": per_page,
            "appId": self.app_id,
            "kw": kw,
            "dbTableKw": "",
            "orderBy": "id",
            "order": "desc",
            "struct": "plain",
            "groupList": "",
            "ownerList": [owner] if owner else [],
            "monitorUserList": [],
            "enableAi": False,
            "category": None,
            "stage": None,
            "driverName": None,
            "doradoPriority": None,
            "yarnName": None,
            "frequency": None,
        }
        return self._post("/aeolus/api/v3/dataFactory/dataSetOverviewPageLLMV2", body)

    def get_dim_met_category_list(self):
        return self._get("/aeolus/api/v3/dataFactory/dimMetCategoryListV2", appId=str(self.app_id))

    def is_need_resource_group(self, data_set_type=34, storage_engine_type="ck"):
        return self._get(
            "/aeolus/api/v3/dataFactory/isNeedResourceGroup",
            appId=str(self.app_id), dataSetType=str(data_set_type),
            storageEngineType=storage_engine_type,
        )

    # ── 数据同步（回溯）相关 API ──

    def get_sync_settings_batch(self, data_set_id):
        """获取数据集同步配置（调度、监控、Yarn 队列等）。"""
        return self._get(
            "/aeolus/api/v3/dataFactory/dataSetSyncSettingsBatch",
            appId=str(self.app_id), dataSetId=str(data_set_id),
        )

    def get_sync_info_all_page_batch(self, data_set_id, start_date, end_date,
                                     node_id_list, refresh=0, filter_by_ttl=False):
        """查询数据集同步实例列表（每日分区的同步状态）。"""
        return self._post("/aeolus/api/v3/dataFactory/dataSetSyncInfoAllPageBatch", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
            "startDate": start_date,
            "endDate": end_date,
            "refresh": refresh,
            "nodeIdList": node_id_list,
            "filterByTtl": filter_by_ttl,
            "materializeNodeIdList": [],
        })

    def get_sync_partition_values_batch(self, data_set_id, node_id_list):
        """获取数据集可回溯的分区日期范围。"""
        return self._post("/aeolus/api/v3/dataFactory/getSyncPartitionValuesBatch", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
            "nodeIdList": node_id_list,
        })

    def check_show_partition_queue_batch(self, data_set_id, node_id_list):
        """检查回溯时是否可指定队列、最大并行度等信息。"""
        return self._post("/aeolus/api/v3/dataFactory/checkShowPartitionQueueBatch", {
            "dataSetId": int(data_set_id),
            "appId": self.app_id,
            "nodeIdList": node_id_list,
        })

    def get_lookback_instances_num(self, data_set_id, node_id_list, start_date, end_date,
                                   dispersed_date_list=None):
        """查询即将生成的回溯实例数量。"""
        return self._post("/aeolus/api/v3/dataFactory/getLookbackInstancesNum", {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
            "nodeIdList": node_id_list,
            "startDate": start_date,
            "endDate": end_date,
            "dispersedDateList": dispersed_date_list or [],
        })

    def get_user_yarn_list_backfill(self, data_set_id):
        """获取回溯可用的 Yarn 队列列表（queueTaskTagList=backfill）。"""
        return self._get(
            "/aeolus/api/v3/dataFactory/getUserYarnList",
            appId=str(self.app_id), dataSetId=str(data_set_id),
            queueTaskTagList="backfill",
        )

    def create_sync_job(self, data_set_id, start_date, end_date, node_id_list,
                        queue_name=None, max_parallelism=5,
                        is_specify_queue=False, is_specify_run_time=False,
                        partition_check=False, skip_check=False,
                        check_min_max=True, dispersed_date_list=None,
                        interval_start_time=None, interval_end_time=None):
        """提交回溯（数据同步）任务，返回 previewId 用于轮询结果。"""
        body = {
            "appId": self.app_id,
            "dataSetId": int(data_set_id),
            "startDate": start_date,
            "endDate": end_date,
            "dispersedDateList": dispersed_date_list or [],
            "checkMinMax": check_min_max,
            "intervalStartTime": interval_start_time,
            "intervalEndTime": interval_end_time,
            "skipCheck": skip_check,
            "isSpecifyQueue": is_specify_queue,
            "queueName": queue_name or "",
            "maxParallelism": max_parallelism,
            "isSpecifyRunTime": is_specify_run_time,
            "partitionCheck": partition_check,
            "nodeIdList": node_id_list,
            "materializeNodeIdList": [],
        }
        return self._post("/aeolus/api/v3/dataFactory/createSyncJob", body)

    def get_create_sync_job_result(self, preview_id):
        """轮询回溯任务提交结果（RUNNING → SUCCEEDED / FAILED）。"""
        return self._get(
            "/aeolus/api/v3/dataFactory/getCreateSyncJobResult",
            previewId=preview_id,
        )

    def wait_for_sync_job(self, preview_id, timeout=120, interval=3):
        """等待回溯任务提交完成。"""
        start = time.time()
        while True:
            result = self.get_create_sync_job_result(preview_id)
            status = result.get("data", {}).get("status", "")
            if status in ("SUCCEEDED", "FINISHED"):
                print("  ✓ 回溯任务提交成功")
                return result["data"]
            if status == "FAILED":
                msg = result.get("data", {}).get("errorMsg", "未知错误")
                raise RuntimeError(f"回溯任务提交失败: {msg}")
            if time.time() - start > timeout:
                raise RuntimeError(f"回溯任务提交超时 ({timeout}s)，最后状态: {status}")
            time.sleep(interval)

    def detect_performance(self, base_conf, sync_conf):
        return self._post("/aeolus/api/v3/dataFactory/detectPerformance", {
            "baseConf": base_conf,
            "syncConf": sync_conf,
        })

    def refresh_token(self, token_str=None):
        if token_str is None:
            token_str = auto_get_token(region=self.region)
            if not token_str:
                raise RuntimeError("无法自动获取 token，请手动传入或安装 pycookiecheat")
            print(f"✓ 已从 Chrome 浏览器刷新 x-titan-token ({self.region})")
        self.token = token_str
        suffix = f"_{self.region}" if self.region != "cn" else ""
        token_path = _SCRIPT_DIR / f"token{suffix}.txt"
        token_path.write_text(token_str, encoding="utf-8")
        print("Token 已更新")

    def dataset_url(self, data_set_id):
        return dataset_url(self.app_id, data_set_id, region=self.region)

    def auto_detect_yarn(self):
        if self._cached_yarn:
            return self._cached_yarn
        configured = _cfg_region(self.region, "yarn_name")
        if configured:
            self._cached_yarn = configured
            return configured
        result = self.get_user_yarn_list()
        yarn_list = result.get("data", [])
        if yarn_list:
            # SG 使用 queue 字段，CN 使用 name 或 yarnName
            item = yarn_list[0]
            self._cached_yarn = item.get("queue") or item.get("name") or item.get("yarnName", "")
            return self._cached_yarn
        return ""

    def auto_detect_parent_id(self):
        if self._cached_parent_id is not None:
            return self._cached_parent_id
        configured = _cfg_region(self.region, "parent_id")
        if configured:
            self._cached_parent_id = configured
            return configured
        result = self.get_folder_tree()
        raw = result.get("data", [])
        # SG returns {"official": [], "private": [], "public": [...]}
        # CN may return a flat list
        if isinstance(raw, dict):
            tree = raw.get("public", []) + raw.get("private", []) + raw.get("official", [])
        else:
            tree = raw
        if tree:
            self._cached_parent_id = tree[0].get("id", 0)
            return self._cached_parent_id
        self._cached_parent_id = 0
        return 0

    def check_dataset_recyclable(self, data_set_ids):
        if isinstance(data_set_ids, int):
            data_set_ids = [data_set_ids]
        return self._post("/aeolus/api/v3/dataFactory/checkDataSetRecyclable", {
            "appId": self.app_id,
            "dataSetIds": data_set_ids,
        })

    def get_dataset_lineage_statistics(self, data_set_id):
        return self._post("/aeolus/api/v3/dataFactory/dataSetLineageStatistics", {
            "appId": self.app_id,
            "dataSetId": data_set_id,
        })

    def recycle_dataset(self, data_set_ids):
        if isinstance(data_set_ids, int):
            data_set_ids = [data_set_ids]
        return self._post("/aeolus/api/v3/dataFactory/recycleDataSet", {
            "appId": self.app_id,
            "dataSetIdList": data_set_ids,
        })

    def auto_detect_owner(self):
        configured = _cfg("user", "owner")
        if configured:
            return configured
        result = self.current_user()
        return result.get("data", {}).get("emailPrefix", "")


def _make_node_conf_sql(query, cluster_name=None, data_source_type="hive", fields=None, node_id=None,
                        partition_conf_list=None, source_table_list=None):
    if cluster_name is None:
        cluster_name = _region_conf().get("cluster", "cn")
    if node_id is None:
        node_id = str(uuid.uuid4())
    node = {
        "tbId": f"{cluster_name}//Hive-db-1//Hive-sql-1",
        "nodeType": "sql",
        "dataSourceType": data_source_type,
        "clusterName": cluster_name,
        "dbName": "Hive-db-1",
        "tbName": "Hive-sql-1",
        "tableAlias": "Hive-sql-1",
        "displayDbName": "Hive-db-1",
        "schemaName": "Hive-table-1",
        "schemaNameAlias": "Hive-table-1",
        "query": query,
        "fullOption": True,
        "replaceTable": False,
        "fields": fields or [],
        "id": node_id,
        "relationTableType": 1,
        "factTableConf": {"enableBizDate": False, "lastDataRule": "common"},
        "dimTableConf": {},
        "tableRowFilter": {},
        "dc": cluster_name,
        "x": 310,
        "y": 280,
    }
    if partition_conf_list is not None:
        node["partitionConfList"] = partition_conf_list
    if source_table_list is not None:
        node["sourceTableList"] = source_table_list
    return node


def _schema_to_fields(schema_data):
    fields = []
    for item in schema_data.get("schema", []):
        fields.append({
            "name": item["name"],
            "type": item.get("type", item.get("prepType", "string")),
            "isSourceTableField": False,
            "prepType": item.get("prepType", "string"),
            "isSelect": True,
            "isDynamicPartition": False,
        })
    return fields


def _enrich_fields_for_save(fields):
    """为 PUT 保存请求补充 alias 和 isSupport 字段。
    previewSchema 请求不需要这两个字段，但 PUT dataSetV2 保存时需要。
    """
    enriched = []
    for f in fields:
        ef = dict(f)
        if "alias" not in ef:
            ef["alias"] = f"`{ef['name']}`"
        if "isSupport" not in ef:
            ef["isSupport"] = True
        enriched.append(ef)
    return enriched


def _schema_to_dim_met_list(schema_data):
    dim_met_list = []
    type_mapping = {
        "timestamp": ("datetime", "datetime"),
        "date": ("date", "date"),
        "string": ("string", "string"),
        "long": ("int", "float"),
        "int": ("int", "float"),
        "bigint": ("int", "float"),
        "double": ("float", "float"),
        "float": ("float", "float"),
    }
    order = 0

    p_date = {
        "tempId": int(time.time() * 1000000),
        "name": "p_date",
        "displayName": "p_date",
        "expr": "p_date",
        "descr": "p_date",
        "defaultType": "date",
        "dataTypeName": "date",
        "filterType": "date",
        "mapType": 0,
        "castDataTypeName": None,
        "dimMetCategoryId": None,
        "dimMetCategoryType": None,
        "dimMetMixOrder": order,
        "geoInfo": None,
        "visible": 1,
        "dimMetVariety": 1,
        "showExpr": 1,
        "isAutoAdd": 1,
        "autoAddType": 1,
        "editable": 0,
        "dimMetOrder": 0,
        "groupType": 0,
        "isUpstreamField": False,
    }
    dim_met_list.append(p_date)
    order += 1

    numeric_types = {"long", "int", "bigint", "double", "float"}

    for item in schema_data.get("schema", []):
        name = item["name"]
        if name == "p_date":
            continue
        prep_type = item.get("prepType", "string")
        dim_met_type, filter_type = type_mapping.get(prep_type, ("string", "string"))
        default_map_type = 1 if prep_type in numeric_types else 0

        dm = {
            "tempId": int(time.time() * 1000000) + order,
            "name": name,
            "expr": name,
            "defaultType": dim_met_type,
            "dataTypeName": dim_met_type,
            "mapType": default_map_type,
            "castDataTypeName": None,
            "dimMetCategoryId": None,
            "dimMetCategoryType": None,
            "dimMetMixOrder": order,
            "geoInfo": None,
            "visible": 1,
            "dimMetVariety": 2 if prep_type == "timestamp" else 0,
            "showExpr": 1,
            "dimMetType": dim_met_type,
            "filterType": filter_type,
            "editable": 1,
            "isUpstreamField": True,
            "dimMetOrder": order,
            "groupType": 0,
        }
        dim_met_list.append(dm)
        order += 1

    return dim_met_list


def _make_base_conf(name, app_id=None, data_set_type=34, owner=None, parent_id=None, original_dataset_id=None, region=None):
    if region is None:
        region = _get_region()
    if app_id is None:
        app_id = _cfg_region(region, "app_id") or _cfg("app", "app_id", _region_conf(region)["default_app_id"])
    if owner is None:
        owner = _cfg("user", "owner")
    if parent_id is None:
        parent_id = _cfg_region(region, "parent_id", 0)

    conf = {
        "dataSetName": name,
        "appId": app_id,
        "dataSetType": data_set_type,
        "ownerEmailPrefix": owner,
        "demoUrl": "",
        "demoUrlName": "",
        "isAuthEnabled": 0,
        "isIntelligentSyncEnable": 1,
        "connectionMode": _cfg("dataset", "connection_mode", 0),
        "syncMode": _cfg("dataset", "sync_mode", 0),
        "parentId": parent_id,
        "belong": 1,
        "enableCopilot": 0,
        "enableDimMetDescrCustomizable": 1,
        "dc": _cfg("dataset", "dc", "cn"),
        "isCISComplianceFormCompleted": False,
        "multiModalDataSourceType": _cfg("datasource", "type", "hive"),
        "version": _cfg("dataset", "version", "v2"),
        "enableResourceGroup": True,
        "joinType": 0,
        "isDataSetAndTableMixed": False,
        "modelType": _cfg("dataset", "model_type", 1),
        "confidentiality": _cfg("dataset", "confidentiality", "L3"),
        "groupId": _cfg_region(region, "group_id", 8817),
        "groupName": _cfg_region(region, "group_name", "default"),
        "groupType": 0,
        "isPersonalDataRelated": False,
        "aiInstructionAutoUpdate": True,
        "enableDimMetCategoryUnfold": 1,
        "dimMetCategoryDisplayMethod": 2,
    }

    if original_dataset_id:
        conf["originalDataSetId"] = str(original_dataset_id)
        conf["isGlobal"] = False
        conf["logicalVersion"] = 0
        conf["relationJoinType"] = _cfg("datasource", "type", "hive")
        conf["dimMetCategoryDisplayMethod"] = 1
    else:
        conf["tempDataSetId"] = int(time.time() * 1000000)

    return conf


def _make_sync_conf(owner=None, yarn_name=None, frequency=None, schedule_time=None,
                    ttl=None, backtrack_start=None, backtrack_end=None,
                    data_source_id=0, retry_num=None, retry_interval=None):
    if owner is None:
        owner = _cfg("user", "owner")
    if yarn_name is None:
        yarn_name = ""
    if frequency is None:
        frequency = _cfg("sync", "frequency", "daily")
    if schedule_time is None:
        schedule_time = _cfg("sync", "schedule_time", "00:00")
    if ttl is None:
        ttl = _cfg("sync", "ttl", 7)
    if retry_num is None:
        retry_num = _cfg("sync", "retry_num", 1)
    if retry_interval is None:
        retry_interval = _cfg("sync", "retry_interval", 5)

    if backtrack_start is None:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        backtrack_start = yesterday
    if backtrack_end is None:
        backtrack_end = backtrack_start

    return {
        "doradoPriority": "normal",
        "yarnName": yarn_name,
        "performanceSettings": {
            "dataSourceId": data_source_id,
            "chQueryParams": {"openStrongConsistencyCheck": False},
            "performanceSettingsByNode": [],
        },
        "monitorConf": {
            "alarmRules": [{
                "failedAlarmItems": [{"item": "retry_failed"}],
                "timeoutAlarmItems": [],
                "resultAlarmItems": [],
                "normalNoticeConf": [{"noticeChannel": "lark", "users": [owner]}],
                "selectAll": True,
                "isBaseline": False,
            }],
        },
        "syncScheduleConf": [{
            "groupId": "default",
            "nodeIdList": [],
            "syncType": 1,
            "writePartition": 0,
            "ttl": ttl,
            "ttlType": 1,
            "scheduleConf": {
                "frequency": frequency,
                "scheduleDay": "0",
                "scheduleTime": schedule_time,
                "scheduleDurations": [],
            },
            "backtrackingConf": {
                "enable": 1,
                "dateRange": {
                    "startDate": backtrack_start,
                    "endDate": backtrack_end,
                },
            },
        }],
        "doradoAutoDdl": 0,
        "autoFollowSyncFabric": [{"enable": False}],
        "retryNum": retry_num,
        "retryInterval": retry_interval,
        "paramsConfList": [{"name": "tqs.query.auto.retry.enable", "value": "true"}],
        "upstreamSettings": {},
    }


class DatasetEditor:
    def __init__(self, client, data_set_id=None):
        self.client = client
        self.data_set_id = data_set_id
        self.model_info = None
        if data_set_id:
            self.load()

    def load(self):
        result = self.client.get_dataset_model_info(self.data_set_id)
        self.model_info = result.get("data", {})
        if not self.model_info.get("dimMetList"):
            all_info = self.client.get_all_dataset_info(self.data_set_id)
            all_data = all_info.get("data", {})
            if all_data.get("dimMetList"):
                self.model_info["dimMetList"] = all_data["dimMetList"]
            if all_data.get("dimMetCategoryList"):
                self.model_info["dimMetCategoryList"] = all_data["dimMetCategoryList"]
        return self.model_info

    def get_overview(self):
        result = self.client.get_dataset_overview(self.data_set_id)
        return result.get("data", {})

    def get_base_conf(self):
        return self.model_info.get("baseConf", {})

    def get_node_conf(self):
        return self.model_info.get("nodeConf", [])

    def get_sync_conf(self):
        return self.model_info.get("syncConf", {})

    def get_query(self, node_index=0):
        nodes = self.get_node_conf()
        if node_index < len(nodes):
            return nodes[node_index].get("query", "")
        return ""

    def get_dim_met_list(self):
        return self.model_info.get("dimMetList", [])

    @classmethod
    def create_new(cls, client, name, query, owner=None, parent_id=None,
                   yarn_name=None, frequency=None, schedule_time=None,
                   ttl=None, backtrack_start=None, backtrack_end=None,
                   cluster_name=None, data_source_type=None,
                   publish=False, source_dataset_id=None, source_fields=None,
                   dim_met_overrides=None, source_client=None):
        if cluster_name is None:
            cluster_name = _cfg_region(client.region, "cluster") or client._rc["cluster"]
        if data_source_type is None:
            data_source_type = _cfg("datasource", "type", "hive")
        if owner is None:
            owner = client.auto_detect_owner()
        if parent_id is None:
            parent_id = client.auto_detect_parent_id()
        if yarn_name is None:
            yarn_name = client.auto_detect_yarn()

        print(f"正在创建数据集: {name}")

        if source_fields is not None:
            print("1. 使用提供的 fields (跳过 SQL Schema 解析)...")
            fields = source_fields
        else:
            print("1. 解析 SQL Schema...")
            schema_data = client.wait_for_schema(query, data_source_type, cluster_name)
            fields = _schema_to_fields(schema_data)

        node_id = str(uuid.uuid4())
        node_conf = [_make_node_conf_sql(query, cluster_name, data_source_type, fields, node_id)]

        print("2. 预览 Schema...")
        client.preview_schema(node_conf)

        print("3. 确定数据集类型...")
        client.determine_dataset_type(node_conf)

        dim_met_list = _schema_to_dim_met_list(
            {"schema": [{"name": f["name"], "prepType": f.get("prepType", f.get("type", "string"))}
                        for f in fields]}
        )

        if source_dataset_id is not None:
            # source_client 允许跨区域参照（用 CN client 读取源数据集，SG client 创建新数据集）
            ref_client = source_client or client
            try:
                source_editor = cls(ref_client, source_dataset_id)
            except RuntimeError as e:
                if source_client is None and ref_client.region != client.region:
                    raise
                raise ValueError(
                    f"无法在 {ref_client.region} 区域加载数据集 {source_dataset_id}。"
                    f"如果是跨区域参照，请传入 source_client 参数指定源区域的 AeolusClient，"
                    f"例如: create_new(sg_client, ..., source_dataset_id=xxx, source_client=cn_client)"
                ) from e
            source_dim_met = source_editor.get_dim_met_list()
            source_map = {dm.get("name"): dm for dm in source_dim_met}
            for dm in dim_met_list:
                src = source_map.get(dm["name"])
                if src:
                    dm["mapType"] = src.get("mapType", dm.get("mapType", 0))
                    if src.get("filterType"):
                        dm["filterType"] = src["filterType"]
                    src_type = src.get("defaultDataTypeName") or src.get("dataTypeName")
                    if src_type:
                        dm["defaultType"] = src_type
                        dm["dataTypeName"] = src_type

        if dim_met_overrides:
            for dm in dim_met_list:
                overrides = dim_met_overrides.get(dm["name"])
                if overrides:
                    dm.update(overrides)

        base_conf = _make_base_conf(name, app_id=client.app_id, owner=owner, parent_id=parent_id, region=client.region)

        print("4. 预检查维度指标...")
        check_base = {
            "appId": base_conf["appId"],
            "connectionMode": base_conf["connectionMode"],
            "dataSetType": base_conf["dataSetType"],
            "syncMode": base_conf["syncMode"],
        }
        pre_check = client.pre_check_dim_met_list(check_base, dim_met_list, node_conf)
        check_dim_met_id = pre_check.get("data", {}).get("checkDimMetId", "")

        print("5. 确定目标集群...")
        cluster_result = client.determine_cluster(base_conf, node_conf)
        data_source_id = cluster_result.get("data", {}).get("dataSourceId", 0)

        print("6. 获取上游依赖...")
        dep_result = client.get_sub_dependency_list(node_conf)
        dep_list = dep_result.get("data", [])
        dependency_conf_list = []
        if dep_list:
            for dep in dep_list:
                dependency_conf_list.append({
                    "nodeId": dep.get("nodeId", node_id),
                    "dependencyConf": dep.get("dependencyConf", {}),
                    "obtainSuccess": dep.get("obtainSuccess", True),
                    "tbId": dep.get("tbId", ""),
                    "tbName": dep.get("nodeName", dep.get("tbName", "")),
                })

        sync_conf = _make_sync_conf(
            owner=owner, yarn_name=yarn_name, frequency=frequency,
            schedule_time=schedule_time, ttl=ttl,
            backtrack_start=backtrack_start, backtrack_end=backtrack_end,
            data_source_id=data_source_id,
        )

        # POST 创建时 fields 也需要 alias 和 isSupport
        save_node_conf = copy.deepcopy(node_conf)
        if save_node_conf and save_node_conf[0].get("fields"):
            save_node_conf[0]["fields"] = _enrich_fields_for_save(save_node_conf[0]["fields"])

        body = {
            "baseConf": base_conf,
            "nodeConf": save_node_conf,
            "linkConf": [],
            "dimMetList": dim_met_list,
            "dimMetCategoryList": [],
            "dataTableConf": {"kafkaCluster": cluster_name},
            "syncConf": sync_conf,
            "whereConf": {"requiredRowFilter": [], "nodeRowFilter": {}},
            "labelConf": {},
            "parseEngine": 1,
            "dependencyConf": None,
            "dependencyConfList": dependency_conf_list,
            "dagTagConf": {"dimTbNodes": []},
            "aggExpediteConf": {"isOpen": False, "conf": []},
            "checkDimMetId": check_dim_met_id,
        }

        print("7. 创建数据集...")
        result = client.create_dataset(body)
        new_id = result.get("data", {}).get("dataSetId")
        url = client.dataset_url(new_id)
        print(f"  ✓ 数据集创建成功!")
        print(f"  ID: {new_id}")
        print(f"  链接: {url}")

        editor = cls(client, new_id)

        if publish:
            # ClickHouse 表创建需要时间，首次发布可能失败，自动重试
            max_retries = 3
            for attempt in range(max_retries):
                wait_secs = 10 * (attempt + 1)  # 10s, 20s, 30s
                print(f"  等待 {wait_secs}s 后发布数据集 (尝试 {attempt + 1}/{max_retries})...")
                time.sleep(wait_secs)
                try:
                    editor.update(publish=True)
                    break
                except RuntimeError as e:
                    if "getTableSchemaFailed" in str(e) and attempt < max_retries - 1:
                        print(f"  ClickHouse 表尚未就绪，将重试...")
                        continue
                    raise

        return editor

    @classmethod
    def create_from(cls, client, source_dataset_id, new_name, owner=None, parent_id=None,
                    new_query=None, yarn_name=None, frequency=None, schedule_time=None,
                    ttl=None, backtrack_start=None, backtrack_end=None,
                    dim_met_overrides=None, publish=False):
        if owner is None:
            owner = client.auto_detect_owner()
        if parent_id is None:
            parent_id = client.auto_detect_parent_id()
        if yarn_name is None:
            yarn_name = client.auto_detect_yarn()

        print(f"正在从数据集 {source_dataset_id} 复制创建: {new_name}")

        try:
            source = cls(client, source_dataset_id)
        except RuntimeError as e:
            raise ValueError(
                f"无法在 {client.region} 区域加载源数据集 {source_dataset_id}。"
                f"create_from() 只能在同区域内复制。跨区域参照请使用 create_new() + source_fields + source_client 参数。"
            ) from e
        source_model = copy.deepcopy(source.model_info)

        base_conf = source_model.get("baseConf", {})
        base_conf["dataSetName"] = new_name
        base_conf["originalDataSetId"] = str(source_dataset_id)
        base_conf["isGlobal"] = False
        base_conf["logicalVersion"] = 0
        base_conf["relationJoinType"] = _cfg("datasource", "type", "hive")
        base_conf.pop("dataSetId", None)
        base_conf.pop("dataSetSource", None)
        base_conf.pop("descr", None)
        base_conf.pop("fabricHasSnowFlakeChart", None)
        base_conf.pop("fabricNeedAddPdate", None)
        base_conf.pop("generalTags", None)
        base_conf.pop("lineOfBusiness", None)
        base_conf.pop("dataRegion", None)
        base_conf.pop("enableUpstreamMention", None)

        if owner:
            base_conf["ownerEmailPrefix"] = owner
        if parent_id is not None:
            base_conf["parentId"] = parent_id

        base_conf.setdefault("enableResourceGroup", True)
        base_conf.setdefault("aiInstructionAutoUpdate", True)
        base_conf.setdefault("enableDimMetCategoryUnfold", 1)
        base_conf["dimMetCategoryDisplayMethod"] = 1
        base_conf["isCISComplianceFormCompleted"] = False

        node_conf = source_model.get("nodeConf", [])
        if new_query and node_conf:
            cluster_name = node_conf[0].get("clusterName") or client._rc["cluster"]
            ds_type = node_conf[0].get("dataSourceType", "hive")

            print("1. 解析新 SQL Schema...")
            schema_data = client.wait_for_schema(new_query, ds_type, cluster_name)
            fields = _schema_to_fields(schema_data)
            node_conf[0]["query"] = new_query
            node_conf[0]["fields"] = fields
        else:
            print("1. 使用源数据集的 SQL...")

        print("2. 确定数据集类型...")
        client.determine_dataset_type(node_conf, original_dataset_id=source_dataset_id)

        source_dim_met = source_model.get("dimMetList", [])
        source_map = {dm.get("name"): dm for dm in source_dim_met}

        if new_query:
            dim_met_list = _schema_to_dim_met_list(
                {"schema": [{"name": f["name"], "prepType": f.get("prepType", f.get("type", "string"))}
                            for f in (node_conf[0].get("fields") or [])]}
            )
        else:
            dim_met_list = _schema_to_dim_met_list(
                {"schema": [{"name": f["name"], "prepType": f.get("prepType", f.get("type", "string"))}
                            for f in (node_conf[0].get("fields") or [])]}
            )
            for dm in dim_met_list:
                src = source_map.get(dm["name"])
                if src:
                    dm["mapType"] = src.get("mapType", dm.get("mapType", 0))
                    if src.get("dimMetVariety") is not None:
                        dm["dimMetVariety"] = src["dimMetVariety"]
                    if src.get("filterType"):
                        dm["filterType"] = src["filterType"]
                    src_type = src.get("defaultDataTypeName") or src.get("dataTypeName")
                    if src_type:
                        dm["defaultType"] = src_type
                        dm["dataTypeName"] = src_type

        if dim_met_overrides:
            for dm in dim_met_list:
                overrides = dim_met_overrides.get(dm["name"])
                if overrides:
                    dm.update(overrides)

        print("3. 预检查维度指标...")
        check_base = {
            "appId": base_conf["appId"],
            "connectionMode": base_conf.get("connectionMode", 0),
            "dataSetType": base_conf.get("dataSetType", 34),
            "syncMode": base_conf.get("syncMode", 0),
        }
        pre_check = client.pre_check_dim_met_list(check_base, dim_met_list, node_conf)
        check_dim_met_id = pre_check.get("data", {}).get("checkDimMetId", "")

        print("4. 确定目标集群...")
        cluster_result = client.determine_cluster(base_conf, node_conf)
        data_source_id = cluster_result.get("data", {}).get("dataSourceId", 0)

        print("5. 获取上游依赖...")
        dep_result = client.get_sub_dependency_list(node_conf)
        dep_list = dep_result.get("data", [])
        dependency_conf_list = []
        node_id = node_conf[0].get("id", str(uuid.uuid4())) if node_conf else str(uuid.uuid4())
        if dep_list:
            for dep in dep_list:
                dependency_conf_list.append({
                    "nodeId": dep.get("nodeId", node_id),
                    "dependencyConf": dep.get("dependencyConf", {}),
                    "obtainSuccess": dep.get("obtainSuccess", True),
                    "tbId": dep.get("tbId", ""),
                    "tbName": dep.get("nodeName", dep.get("tbName", "")),
                })

        sync_conf = _make_sync_conf(
            owner=owner or base_conf.get("ownerEmailPrefix"),
            yarn_name=yarn_name or source_model.get("syncConf", {}).get("yarnName") or _cfg_region(client.region, "yarn_name"),
            frequency=frequency, schedule_time=schedule_time, ttl=ttl,
            backtrack_start=backtrack_start, backtrack_end=backtrack_end,
            data_source_id=data_source_id,
        )

        where_conf = source_model.get("whereConf", {"requiredRowFilter": [], "nodeRowFilter": {}})
        link_conf = source_model.get("linkConf", [])

        # POST 创建时 fields 也需要 alias 和 isSupport
        save_node_conf = copy.deepcopy(node_conf)
        if save_node_conf and save_node_conf[0].get("fields"):
            save_node_conf[0]["fields"] = _enrich_fields_for_save(save_node_conf[0]["fields"])

        body = {
            "baseConf": base_conf,
            "nodeConf": save_node_conf,
            "linkConf": link_conf,
            "dimMetList": dim_met_list,
            "dimMetCategoryList": source_model.get("dimMetCategoryList", []),
            "dataTableConf": source_model.get("dataTableConf") or {"kafkaCluster": node_conf[0].get("clusterName", client._rc["cluster"]) if node_conf else client._rc["cluster"]},
            "syncConf": sync_conf,
            "whereConf": where_conf,
            "labelConf": source_model.get("labelConf", {}),
            "dependencyConf": None,
            "dependencyConfList": dependency_conf_list,
            "dagTagConf": source_model.get("dagTagConf", {"dimTbNodes": []}),
            "aggExpediteConf": source_model.get("aggExpediteConf", {"isOpen": False, "conf": []}),
            "checkDimMetId": check_dim_met_id,
            "dataDomainConf": source_model.get("dataDomainConf", []),
        }

        print("6. 创建数据集...")
        result = client.create_dataset(body, enable_draft=False)
        new_id = result.get("data", {}).get("dataSetId")
        url = client.dataset_url(new_id)
        print(f"  ✓ 数据集复制创建成功!")
        print(f"  源数据集: {source_dataset_id}")
        print(f"  新数据集 ID: {new_id}")
        print(f"  链接: {url}")

        editor = cls(client, new_id)

        if publish:
            # ClickHouse 表创建需要时间，首次发布可能失败，自动重试
            max_retries = 3
            for attempt in range(max_retries):
                wait_secs = 10 * (attempt + 1)  # 10s, 20s, 30s
                print(f"  等待 {wait_secs}s 后发布数据集 (尝试 {attempt + 1}/{max_retries})...")
                time.sleep(wait_secs)
                try:
                    editor.update(publish=True)
                    break
                except RuntimeError as e:
                    if "getTableSchemaFailed" in str(e) and attempt < max_retries - 1:
                        print(f"  ClickHouse 表尚未就绪，将重试...")
                        continue
                    raise

        return editor

    def update(self, new_query=None, new_name=None, owner=None,
               yarn_name=None, frequency=None, schedule_time=None,
               ttl=None, backtrack_start=None, backtrack_end=None,
               publish=True, dim_met_overrides=None, source_fields=None):
        if not self.model_info:
            self.load()

        model = copy.deepcopy(self.model_info)
        base_conf = model.get("baseConf", {})
        node_conf = model.get("nodeConf", [])
        origin_node_conf = copy.deepcopy(node_conf)

        print(f"正在更新数据集: {self.data_set_id} ({base_conf.get('dataSetName', '')})")

        if new_name:
            base_conf["dataSetName"] = new_name

        if owner:
            base_conf["ownerEmailPrefix"] = owner

        if new_query and node_conf:
            cluster_name = node_conf[0].get("clusterName") or self.client._rc["cluster"]
            ds_type = node_conf[0].get("dataSourceType", "hive")

            if source_fields is not None:
                print("1. 使用提供的 source_fields (跳过 SQL Schema 解析)...")
                fields = source_fields
            else:
                print("1. 解析新 SQL Schema...")
                schema_data = self.client.wait_for_schema(
                    new_query, ds_type, cluster_name, data_set_id=self.data_set_id,
                )
                fields = _schema_to_fields(schema_data)
            node_conf[0]["query"] = new_query
            node_conf[0]["fields"] = fields

            dim_met_list = _schema_to_dim_met_list(
                {"schema": [{"name": f["name"], "prepType": f.get("prepType", f.get("type", "string"))}
                            for f in fields]}
            )
        else:
            print("1. 保持原有 SQL...")
            fields = node_conf[0].get("fields") or [] if node_conf else []
            existing_dim_met = model.get("dimMetList", [])
            existing_map = {dm.get("name"): dm for dm in existing_dim_met}
            dim_met_list = _schema_to_dim_met_list(
                {"schema": [{"name": f["name"], "prepType": f.get("prepType", f.get("type", "string"))}
                            for f in fields]}
            )
            for dm in dim_met_list:
                src = existing_map.get(dm["name"])
                if src:
                    dm["mapType"] = src.get("mapType", dm.get("mapType", 0))
                    if src.get("dimMetVariety") is not None:
                        dm["dimMetVariety"] = src["dimMetVariety"]
                    if src.get("filterType"):
                        dm["filterType"] = src["filterType"]
                    src_type = src.get("defaultDataTypeName") or src.get("dataTypeName")
                    if src_type:
                        dm["defaultType"] = src_type
                        dm["dataTypeName"] = src_type
                    if src.get("id"):
                        dm["id"] = src["id"]

        if dim_met_overrides:
            for dm in dim_met_list:
                overrides = dim_met_overrides.get(dm["name"])
                if overrides:
                    dm.update(overrides)

        base_conf["dataSetId"] = self.data_set_id
        base_conf.setdefault("enableResourceGroup", True)
        base_conf.setdefault("aiInstructionAutoUpdate", True)
        base_conf["isCISComplianceFormCompleted"] = False

        if new_query and node_conf:
            print("2. 预览 Schema...")
            self.client.preview_schema(node_conf, is_edit=True)

        print("3. 获取编辑锁...")
        try:
            self.client.acquire_lock(self.data_set_id)
        except RuntimeError:
            pass

        print("4. 检查 DAG 影响...")
        try:
            self.client.check_dag_impact(self.data_set_id, node_conf, dim_met_list,
                                         origin_node_conf=origin_node_conf)
        except RuntimeError:
            pass

        print("5. 预检查维度指标...")
        check_base = {
            "appId": base_conf["appId"],
            "dataSetId": self.data_set_id,
            "connectionMode": base_conf.get("connectionMode", 0),
            "dataSetType": base_conf.get("dataSetType", 34),
            "syncMode": base_conf.get("syncMode", 0),
        }
        pre_check = self.client.pre_check_dim_met_list(check_base, dim_met_list, node_conf)
        check_dim_met_id = pre_check.get("data", {}).get("checkDimMetId", "")

        print("6. 校验维度指标名称...")
        self.client.check_dim_met_name(node_conf, dim_met_list, data_set_id=self.data_set_id)

        # 编辑时不需要调用 determineCluster (浏览器编辑流程不调用此 API)
        # data_source_id 从已有 syncConf 中获取
        existing_sync = model.get("syncConf", {})
        data_source_id = existing_sync.get("performanceSettings", {}).get("dataSourceId", 0)
        existing_sched = {}
        existing_ssc = existing_sync.get("syncScheduleConf", [])
        if existing_ssc:
            existing_sched = existing_ssc[0].get("scheduleConf", {})
        sync_conf = _make_sync_conf(
            owner=owner or base_conf.get("ownerEmailPrefix"),
            yarn_name=yarn_name or existing_sync.get("yarnName") or _cfg_region(self.client.region, "yarn_name"),
            frequency=frequency or existing_sched.get("frequency"),
            schedule_time=schedule_time or existing_sched.get("scheduleTime"),
            ttl=ttl or (existing_ssc[0].get("ttl") if existing_ssc else None),
            backtrack_start=backtrack_start, backtrack_end=backtrack_end,
            data_source_id=data_source_id,
            retry_num=existing_sync.get("retryNum"),
            retry_interval=existing_sync.get("retryInterval"),
        )

        print("7. 获取上游依赖...")
        dep_result = self.client.get_sub_dependency_list(node_conf, data_set_id=self.data_set_id)
        dep_list = dep_result.get("data", [])
        dependency_conf_list = []
        node_id = node_conf[0].get("id", str(uuid.uuid4())) if node_conf else str(uuid.uuid4())
        if dep_list:
            for dep in dep_list:
                dependency_conf_list.append({
                    "nodeId": dep.get("nodeId", node_id),
                    "dependencyConf": dep.get("dependencyConf", {}),
                    "obtainSuccess": dep.get("obtainSuccess", True),
                    "tbId": dep.get("tbId", ""),
                    "tbName": dep.get("nodeName", dep.get("tbName", "")),
                })

        # PUT 保存时 fields 需要 alias 和 isSupport
        save_node_conf = copy.deepcopy(node_conf)
        if save_node_conf and save_node_conf[0].get("fields"):
            save_node_conf[0]["fields"] = _enrich_fields_for_save(save_node_conf[0]["fields"])

        body = {
            "baseConf": base_conf,
            "nodeConf": save_node_conf,
            "linkConf": model.get("linkConf", []),
            "dimMetList": dim_met_list,
            "dimMetCategoryList": model.get("dimMetCategoryList", []),
            "syncConf": sync_conf,
            "whereConf": model.get("whereConf", {"requiredRowFilter": [], "nodeRowFilter": {}}),
            "labelConf": model.get("labelConf", {}),
            "parseEngine": model.get("parseEngine", 1),
            "dependencyConf": None,
            "dependencyConfList": dependency_conf_list,
            "dagTagConf": model.get("dagTagConf", {"dimTbNodes": []}),
            "aggExpediteConf": model.get("aggExpediteConf", {"isOpen": False, "conf": []}),
            "checkDimMetId": check_dim_met_id,
            "dataDomainConf": model.get("dataDomainConf", []),
        }

        # SG 编辑不传 dataSetVersionType；CN 必须传 online/draft
        if self.client.region == "sg":
            version_type = None
        else:
            version_type = "online" if publish else "draft"
        print(f"8. 提交更新 (mode={'publish' if publish else 'draft'})...")
        try:
            result = self.client.update_dataset(body, data_set_version_type=version_type)
        finally:
            try:
                self.client.release_lock(self.data_set_id)
            except RuntimeError:
                pass

        new_id = result.get("data", {}).get("dataSetId", self.data_set_id)
        url = self.client.dataset_url(new_id)
        action = "更新并发布" if publish else "更新（草稿）"
        print(f"  ✓ 数据集{action}成功!")
        print(f"  ID: {new_id}")
        print(f"  链接: {url}")

        self.data_set_id = new_id
        self.load()
        return self

    def get_status(self):
        overview = self.get_overview()
        return {
            "id": overview.get("id"),
            "name": overview.get("name"),
            "status": overview.get("status"),
            "statusDesc": overview.get("statusDesc"),
            "syncType": overview.get("syncType"),
            "editable": overview.get("editable"),
            "version": overview.get("version"),
            "lastSyncTime": overview.get("lastSyncTime"),
            "url": self.client.dataset_url(self.data_set_id),
        }

    def get_summary(self):
        if not self.model_info:
            self.load()
        bc = self.get_base_conf()
        nc = self.get_node_conf()
        query = nc[0].get("query", "")[:200] if nc else ""
        overview = self.get_overview()
        return {
            "id": self.data_set_id,
            "name": bc.get("dataSetName", ""),
            "owner": bc.get("ownerEmailPrefix", ""),
            "type": bc.get("dataSetType"),
            "status": overview.get("status"),
            "statusDesc": overview.get("statusDesc"),
            "query_preview": query + ("..." if len(nc[0].get("query", "")) > 200 else "") if nc else "",
            "url": self.client.dataset_url(self.data_set_id),
        }

    def delete(self, force=False):
        url = self.client.dataset_url(self.data_set_id)
        print(f"正在删除数据集: {self.data_set_id}")

        print("1. 检查数据集是否可回收...")
        check_result = self.client.check_dataset_recyclable(self.data_set_id)
        blockers = check_result.get("data", [])
        if blockers:
            msg = "; ".join(str(b) for b in blockers)
            if not force:
                raise RuntimeError(f"数据集无法回收: {msg}")
            print(f"  ⚠ 存在阻碍但强制删除: {msg}")

        print("2. 查询血缘统计...")
        lineage = self.client.get_dataset_lineage_statistics(self.data_set_id)
        lineage_data = lineage.get("data", {})
        downstream_ds = lineage_data.get("downstreamDataSetNum", 0)
        downstream_db = lineage_data.get("downstreamDashboardNum", 0)
        downstream_rpt = lineage_data.get("downstreamReportNum", 0)
        if downstream_ds or downstream_db or downstream_rpt:
            print(f"  ⚠ 下游依赖: 数据集={downstream_ds}, 看板={downstream_db}, 报表={downstream_rpt}")
            if not force:
                raise RuntimeError(
                    f"数据集有下游依赖 (数据集={downstream_ds}, 看板={downstream_db}, 报表={downstream_rpt})，"
                    "如需强制删除请使用 force=True"
                )

        print("3. 执行回收删除...")
        self.client.recycle_dataset(self.data_set_id)
        print(f"  ✓ 数据集已删除!")
        print(f"  ID: {self.data_set_id}")
        print(f"  链接: {url}")

    def _get_node_id_list(self):
        """从 nodeConf 中提取 nodeId 列表。
        CN 使用 tbId（如 'cn//Hive-db-1//Hive-sql-1'），SG 使用 nodeId（UUID 格式）。
        """
        node_conf = self.get_node_conf()
        result = []
        for n in node_conf:
            nid = n.get("nodeId") or n.get("tbId")
            if nid:
                result.append(nid)
        return result

    def get_sync_status(self, start_date=None, end_date=None):
        """查询数据集同步实例状态列表。
        start_date/end_date 格式: yyyy-MM-dd，默认最近 30 天。
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        node_id_list = self._get_node_id_list()
        result = self.client.get_sync_info_all_page_batch(
            self.data_set_id, start_date, end_date, node_id_list,
        )
        return result.get("data", {})

    def backfill(self, start_date, end_date, queue_name=None, max_parallelism=5,
                 skip_check=False, wait=True):
        """发起数据同步（回溯）。

        参数:
            start_date: 回溯开始日期，格式 yyyy-MM-dd
            end_date: 回溯结束日期，格式 yyyy-MM-dd
            queue_name: 指定 Yarn 队列（可选，默认使用数据集配置的队列）
            max_parallelism: 最大并行度（默认 5）
            skip_check: 是否跳过检查（默认 False）
            wait: 是否等待任务提交完成（默认 True）

        返回:
            previewId（wait=False 时）或提交结果（wait=True 时）
        """
        url = self.client.dataset_url(self.data_set_id)
        print(f"正在发起回溯: {self.data_set_id}")
        print(f"  日期范围: {start_date} ~ {end_date}")

        node_id_list = self._get_node_id_list()
        if not node_id_list:
            raise RuntimeError("无法获取 nodeIdList，请确认数据集已正确加载")

        # 1. 获取可回溯分区范围
        print("1. 获取可回溯分区范围...")
        partition_result = self.client.get_sync_partition_values_batch(
            self.data_set_id, node_id_list,
        )
        partition_data = partition_result.get("data", {})
        avail_start = partition_data.get("startDate", "")
        avail_end = partition_data.get("endDate", "")
        if avail_start and avail_end:
            print(f"  可回溯范围: {avail_start} ~ {avail_end}")

        # 2. 检查队列和并行度信息
        print("2. 检查队列配置...")
        queue_info_result = self.client.check_show_partition_queue_batch(
            self.data_set_id, node_id_list,
        )
        queue_data = queue_info_result.get("data", {})
        show_specify_queue = queue_data.get("showSpecifyQueue", False)
        default_max_parallelism = queue_data.get("maxParallelism", 5)
        ds_queue_info = queue_data.get("dataSetQueueInfo", {})
        default_queue = ds_queue_info.get("queue", "")
        if not queue_name and default_queue:
            queue_name = default_queue
        if max_parallelism is None:
            max_parallelism = default_max_parallelism
        print(f"  队列: {queue_name}")
        print(f"  最大并行度: {max_parallelism}")

        # 3. 查询即将生成的实例数
        print("3. 查询回溯实例数...")
        num_result = self.client.get_lookback_instances_num(
            self.data_set_id, node_id_list, start_date, end_date,
        )
        instances_num = num_result.get("data", {}).get("instancesNum", 0)
        print(f"  将生成 {instances_num} 个实例")

        # 4. 提交回溯任务
        print("4. 提交回溯任务...")
        is_specify_queue = bool(queue_name) and show_specify_queue
        create_result = self.client.create_sync_job(
            self.data_set_id, start_date, end_date, node_id_list,
            queue_name=queue_name,
            max_parallelism=max_parallelism,
            is_specify_queue=is_specify_queue,
            skip_check=skip_check,
        )
        preview_id = create_result.get("data", {}).get("previewId")
        if not preview_id:
            raise RuntimeError(f"提交回溯任务失败，未获取到 previewId: {create_result}")

        # 5. 等待任务提交完成
        if wait:
            print("5. 等待任务提交完成...")
            job_result = self.client.wait_for_sync_job(preview_id)
            print(f"\n✓ 回溯已提交!")
            print(f"  数据集 ID: {self.data_set_id}")
            print(f"  日期范围: {start_date} ~ {end_date}")
            print(f"  实例数: {instances_num}")
            print(f"  链接: {url}")
            return job_result
        else:
            print(f"  ✓ 已提交，previewId: {preview_id}")
            print(f"  链接: {url}")
            return preview_id


def _print_table(rows, headers):
    if not rows:
        print("  (空)")
        return
    col_widths = [len(str(h)) for h in headers]
    str_rows = []
    for row in rows:
        str_row = [str(row.get(h, ""))[:60] for h in headers]
        str_rows.append(str_row)
        for i, v in enumerate(str_row):
            col_widths[i] = max(col_widths[i], len(v))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*[str(h) for h in headers]))
    print(fmt.format(*["-" * w for w in col_widths]))
    for sr in str_rows:
        print(fmt.format(*sr))


def cmd_list(client, owner=None):
    result = client.list_datasets(owner=owner)
    data = result.get("data", {})
    datasets = data.get("dataSetList", data.get("list", []))
    total = data.get("total", 0)
    print(f"数据集列表 (共 {total} 个):\n")
    rows = []
    for ds in datasets:
        status_code = ds.get("status", "")
        status_map = {0: "正常", 10: "初始化", 20: "修改中", 30: "已下线"}
        status_desc = status_map.get(status_code, str(status_code))
        rows.append({
            "id": ds.get("id", ""),
            "name": ds.get("name", ""),
            "status": status_desc,
            "owner": ds.get("ownerEmailPrefix", ""),
            "frequency": ds.get("frequency", ""),
        })
    _print_table(rows, ["id", "name", "status", "owner", "frequency"])


def cmd_info(client, data_set_id):
    editor = DatasetEditor(client, data_set_id)
    summary = editor.get_summary()
    print(f"数据集 ID: {summary['id']}")
    print(f"名称: {summary['name']}")
    print(f"Owner: {summary['owner']}")
    print(f"类型: {summary['type']}")
    print(f"状态: {summary['statusDesc']} (code={summary['status']})")
    print(f"链接: {summary['url']}")
    if summary.get("query_preview"):
        print(f"\nSQL 预览:\n{summary['query_preview']}")


def cmd_status(client, data_set_id):
    editor = DatasetEditor(client, data_set_id)
    status = editor.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} [--region cn|sg] whoami")
        print(f"  python {sys.argv[0]} [--region cn|sg] list [owner]")
        print(f"  python {sys.argv[0]} [--region cn|sg] info <dataSetId | URL>")
        print(f"  python {sys.argv[0]} [--region cn|sg] status <dataSetId | URL>")
        print(f"  python {sys.argv[0]} [--region cn|sg] detect [aeolus_url]       # 自动探测配置")
        print(f"  python {sys.argv[0]} [--region cn|sg] delete <dataSetId | URL>  # 删除数据集")
        print(f"  python {sys.argv[0]} [--region cn|sg] backfill <dataSetId | URL> <startDate> <endDate>  # 发起回溯")
        print(f"  python {sys.argv[0]} [--region cn|sg] sync-status <dataSetId | URL>  # 查看同步状态")
        print()
        print("Python API 示例:")
        print("  from aeolus_api import AeolusClient, DatasetEditor, extract_dataset_id, parse_aeolus_url")
        print("  client = AeolusClient()                       # 默认 region='cn'")
        print("  client = AeolusClient(region='sg')            # 海外 SG 区域")
        print("  editor = DatasetEditor.create_new(client, '数据集名', 'SELECT ...')")
        print("  editor = DatasetEditor.create_from(client, 5428964, '新名称')")
        print("  editor = DatasetEditor(client, 5428964)")
        print("  editor.update(new_query='SELECT ...')")
        sys.exit(1)

    # Parse --region flag from argv
    region = None
    filtered_argv = [sys.argv[0]]
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--region" and i + 1 < len(sys.argv):
            region = sys.argv[i + 1]
            i += 2
        else:
            filtered_argv.append(sys.argv[i])
            i += 1

    if len(filtered_argv) < 2:
        print("错误: 缺少命令参数")
        sys.exit(1)

    command = filtered_argv[1]
    remaining_args = filtered_argv[2:]

    try:
        if command == "detect":
            url = remaining_args[0] if remaining_args else None
            app_id = None
            detect_region = region
            if url:
                parsed = parse_aeolus_url(url)
                app_id = parsed.get("app_id")
                if app_id:
                    print(f"从 URL 解析 app_id: {app_id}")
                url_region = parsed.get("region")
                if url_region:
                    print(f"从 URL 解析 region: {url_region}")
                    if detect_region is None:
                        detect_region = url_region
                ds_id = parsed.get("data_set_id")
                if ds_id:
                    print(f"从 URL 解析 data_set_id: {ds_id}")
            client = AeolusClient(app_id=app_id, region=detect_region)
            print(f"\n--- 自动探测配置 ---")
            print(f"region:    {client.region}")
            print(f"app_id:    {client.app_id}")
            owner = client.auto_detect_owner()
            print(f"owner:     {owner}")
            parent_id = client.auto_detect_parent_id()
            print(f"parent_id: {parent_id}")
            yarn_name = client.auto_detect_yarn()
            print(f"yarn_name: {yarn_name}")
            print(f"\n将以上值写入 config.yaml 即可使用，或者不配置也会自动探测。")
            return

        client = AeolusClient(region=region)

        if command == "whoami":
            result = client.current_user()
            data = result.get("data", {})
            print(f"用户: {data.get('name')} ({data.get('emailPrefix')})")
            print(f"邮箱: {data.get('email')}")
            print(f"部门: {data.get('departmentName')}")
            return

        if command == "list":
            owner = remaining_args[0] if remaining_args else None
            cmd_list(client, owner)
            return

        if not remaining_args:
            print(f"错误: '{command}' 命令需要提供 dataSetId 或 Aeolus URL 参数")
            sys.exit(1)

        data_set_id = extract_dataset_id(remaining_args[0])

        if command == "info":
            cmd_info(client, data_set_id)
        elif command == "status":
            cmd_status(client, data_set_id)
        elif command == "delete":
            editor = DatasetEditor(client, data_set_id)
            editor.delete()
        elif command == "backfill":
            if len(remaining_args) < 3:
                print("用法: aeolus_api.py backfill <dataSetId|URL> <startDate> <endDate>")
                print("  日期格式: yyyy-MM-dd，如 2026-04-20 2026-04-23")
                sys.exit(1)
            start_date = remaining_args[1]
            end_date = remaining_args[2]
            editor = DatasetEditor(client, data_set_id)
            editor.backfill(start_date, end_date)
        elif command == "sync-status":
            editor = DatasetEditor(client, data_set_id)
            sync_data = editor.get_sync_status()
            instances = sync_data.get("instanceList", [])
            status_map = {1: "等待中", 2: "未开始", 3: "运行中", 4: "成功", 5: "失败"}
            print(f"同步状态 (共 {len(instances)} 条):")
            for inst in instances[:10]:
                s = status_map.get(inst.get("syncStatus"), str(inst.get("syncStatus")))
                biz = inst.get("bizTimePage", "")
                size = inst.get("tableSize", "-")
                print(f"  {biz}  {s}  行数={size}")
        else:
            print(f"错误: 未知命令 '{command}'")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"API 错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
