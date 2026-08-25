import json
import sys
import os
import re
import copy
import difflib
from pathlib import Path

import requests

try:
    import yaml
except ImportError:
    yaml = None


_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_CACHE = None

_DEFAULT_PROFILES = {
    "cn": {
        "base_url": "https://libra-gallery.bytedance.net",
        "cookie_domain": "https://libra-gallery.bytedance.net",
        "ticket_region": "cn",
        "apps_region": "cn",
        "data_source_region": "cn",
        "data_source_dorado_region": "cn",
        "group_dorado_regions": "cn",
        "group_business_tag_id": 2,
        "ablog_business_id": 261,
        "ablog_business_key": "basic",
        "apps": ["1190"],
    },
    "i18n": {
        "base_url": "https://libra-gallery-us.tiktok-row.net",
        "cookie_domain": "https://libra-gallery-us.tiktok-row.net",
        "ticket_region": "va",
        "apps_region": "i18n",
        "data_source_dorado_region": "sg",
        "group_dorado_regions": "sg",
        "group_business_tag_id": 1,
        "ablog_business_id": 122,
        "ablog_business_key": "basic",
        "apps": ["532"],
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
    for line in text.splitlines():
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue
        if not stripped.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1].strip()
            result[current_section] = {}
        elif current_section and ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                val = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val.isdigit():
                val = int(val)
            result[current_section][key] = val
    return result


def _cfg(section, key, default=None):
    conf = load_config()
    return conf.get(section, {}).get(key, default)


def _warn_sql_tx_prefix(sql, ds_key=""):
    """检查数据源 SQL 中是否误写了 Tx: 前缀（如 T1:col_name），并发出警告。"""
    matches = re.findall(r'\bT\d+:[a-zA-Z_]\w*', sql)
    if matches:
        label = f" (数据源 {ds_key})" if ds_key else ""
        print(f"⚠️  警告{label}: 数据源 SQL 中检测到 Tx:column 格式的引用: {matches}")
        print(f"   数据源 SQL 应为纯 Hive SQL，不应包含 Tx: 前缀。")
        print(f"   Tx:column_name 格式仅用于 add_metric/add_dimension 的列引用参数。")
        print(f"   如果这是 SQL 表名的一部分（如 T1.col），请忽略此警告。")


def _resolve_sql(sql):
    """如果 sql 是一个已存在的 .sql 文件路径，读取文件内容返回；否则直接返回原字符串。
    文件查找顺序：绝对路径/CWD相对路径 → 脚本目录相对路径。读取后不删除文件。"""
    if sql and sql.strip().endswith('.sql'):
        name = sql.strip()
        candidates = [
            os.path.abspath(name),
            os.path.join(str(_SCRIPT_DIR), name),
        ]
        for path in candidates:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                print(f"📄 从文件读取 SQL: {path}")
                return content
        print(f"⚠️  SQL 文件未找到: {name}（尝试路径: {candidates}），将作为 SQL 字符串处理")
    return sql


def _get_profile(env="cn"):
    conf = load_config()
    profiles = conf.get("profiles", {})
    merged = dict(_DEFAULT_PROFILES.get(env, _DEFAULT_PROFILES["cn"]))
    merged.update(profiles.get(env, {}))
    return merged


def _profile_val(env, key, fallback=None):
    return _get_profile(env).get(key, fallback)


def gallery_url(ticket_id, env="cn"):
    base = _profile_val(env, "base_url", "https://libra-gallery.bytedance.net")
    return f"{base}/#/metric/set/detail/{ticket_id}"


def extract_ticket_id(url_or_id):
    if isinstance(url_or_id, int):
        return url_or_id
    s = str(url_or_id).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'/detail/(\d+)', s) or re.search(r'/ticket/(\d+)', s) or re.search(r'(\d{4,})', s)
    if m:
        return int(m.group(1))
    raise ValueError(f"无法从 '{s}' 中提取 ticket_id，请提供数字 ID 或 Libra Gallery URL")


def detect_env_from_url(url_or_id):
    s = str(url_or_id).strip()
    if "tiktok-row.net" in s:
        return "i18n"
    return "cn"


def auto_get_cookie(domain=None, env="cn"):
    if domain is None:
        domain = _profile_val(env, "cookie_domain", "https://libra-gallery.bytedance.net")
    try:
        from pycookiecheat import chrome_cookies
        cookies = chrome_cookies(domain)
        if not cookies:
            return None
        return "; ".join(f"{k}={v}" for k, v in cookies.items())
    except ImportError:
        return None
    except Exception:
        return None


def make_default_metric_conf(group_type=None, days_range=None):
    if group_type is None:
        group_type = _cfg("group", "group_type", "action_cuped")
    if days_range is None:
        days_range = _cfg("metric", "days_range", "1,7,14")
    return {
        "type": group_type,
        "date_list": [],
        "date_picker_type": "collection",
        "extra_conf": "",
        "exposure": {
            "action_shift_days": 0,
            "days_picker_type": "first_n_days",
            "days_range": days_range,
            "key_sql_list": "",
            "type": "pv",
        },
    }


def make_default_dimension_conf(use_types=None, update_type=None, enums_update_type=None):
    if use_types is None:
        use_types = _cfg("dimension", "use_types", "RPT")
    if update_type is None:
        update_type = _cfg("dimension", "update_type", "first")
    if enums_update_type is None:
        enums_update_type = _cfg("dimension", "enums_update_type", "merge")
    return {
        "backward_days": "-1",
        "base_user_type": "",
        "buffer_days": None,
        "combine_fields": [],
        "custom_sql": "",
        "decc_type": "",
        "default_value": "",
        "enums": [{"description": "", "name": ""}],
        "enums_filter": False,
        "enums_update_type": enums_update_type,
        "fallback_value": "",
        "is_ablog_dim": False,
        "is_query": False,
        "libra_key": "",
        "overlapping_dim_total_enum": "",
        "split_suffix": "",
        "update_type": update_type,
        "use_base_user": False,
        "use_combine": False,
        "use_conf": False,
        "use_custom": False,
        "use_libra_key": False,
        "use_num": False,
        "use_split": False,
        "use_types": use_types,
        "valid_custom_sql_pass": False,
    }


def make_metric(name, left_key_sql, left_type="pv", right_key_sql=None, right_type=None,
                description="", name_en="", conf=None):
    left_keys = [left_key_sql] if left_key_sql else []
    right_keys = [right_key_sql] if right_key_sql else None

    metric = {
        "name": name,
        "name_en": name_en,
        "description": description,
        "sql": {
            "left": {
                "key": left_keys,
                "key_sql": left_key_sql,
                "type": left_type,
            },
            "right": {
                "key": right_keys,
                "key_sql": right_key_sql or "",
                "type": right_type or "",
            },
        },
        "conf": conf if conf is not None else make_default_metric_conf(),
    }
    return metric


def make_dimension(name, key, dim_type="METRIC_DIMENSION", description="", name_en="", conf=None):
    key_list = [key] if isinstance(key, str) else key
    return {
        "name": name,
        "name_en": name_en,
        "description": description,
        "dim_type": dim_type,
        "key": key_list,
        "key_sql": "",
        "conf": conf if conf is not None else make_default_dimension_conf(),
        "pub_dim_id": None,
        "decc_type": "",
    }


class LibraGalleryClient:
    def __init__(self, env="cn", cookie_file=None, cookie_str=None):
        self.env = env
        self.profile = _get_profile(env)
        self.base_url = self.profile["base_url"]
        if cookie_str:
            self.cookie_str = cookie_str
        else:
            if cookie_file is None:
                suffix = "" if env == "cn" else f"_{env}"
                cookie_file = _SCRIPT_DIR / f"cookie{suffix}.txt"
            cookie_path = Path(cookie_file)
            cookie_content = cookie_path.read_text(encoding="utf-8").strip() if cookie_path.exists() else ""
            if cookie_content:
                self.cookie_str = cookie_content
            else:
                auto_cookie = auto_get_cookie(env=env)
                if auto_cookie:
                    self.cookie_str = auto_cookie
                    cookie_path.write_text(auto_cookie, encoding="utf-8")
                else:
                    raise FileNotFoundError(
                        f"Cookie 文件不存在或为空: {cookie_path}\n"
                        "请从浏览器获取 Cookie（Chrome DevTools → Network → 右键请求 → Copy as cURL → 提取 -b 后的内容），"
                        "或安装 pycookiecheat（pip install pycookiecheat）自动获取"
                    )
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": self.cookie_str,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": self.base_url,
        })
        self._cached_owner = None
        self._cached_business = None
        self._cached_ablog = None

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code != 200:
            raise RuntimeError(f"请求失败 [{resp.status_code}]: {method} {path}\n{resp.text}")
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"响应非 JSON: {resp.text[:500]}")
        if isinstance(data, dict) and data.get("code") not in (None, 0, 200):
            msg = data.get("message") or data.get("msg") or str(data)
            raise RuntimeError(f"API 返回错误 (code={data.get('code')}): {msg}")
        return data

    def get_ticket(self, ticket_id, region=None, snapshot_id=None):
        if region is None:
            region = self.profile.get("ticket_region", _cfg("ticket", "region", "cn"))
        params = {"region": region}
        if snapshot_id is not None:
            params["snapshot_id"] = snapshot_id
        return self._request("GET", f"/v1/ticket/{ticket_id}", params=params)

    def parse_sql(self, sql):
        return self._request("POST", "/v1/sql/parse", json={"sql": sql})

    def validate_ttp_sql(self, region, sql=""):
        return self._request("POST", "/v1/sql/validation/ttp", json={"region": region, "sql": sql})

    def save_check(self, virtual_table, ticket):
        return self._request("POST", "/v1/ticket/save_check", json={
            "ticket_data": {"virtual_table": virtual_table, "ticket": ticket}
        })

    def save_ticket(self, virtual_table, ticket):
        return self._request("PUT", "/v1/ticket/", json={
            "virtual_table": virtual_table,
            "ticket": ticket,
        })

    def apply_for_edit(self, ticket_id, user):
        return self._request("GET", "/v1/ticket/apply_for_edit", params={
            "ticket_id": ticket_id, "user": user,
        })

    def get_access(self):
        return self._request("GET", "/v1/access")

    def get_group_online_set(self, ticket_id):
        return self._request("GET", "/v1/ticket/group_online_set", params={"ticket_id": ticket_id})

    def refresh_cookie(self):
        auto_cookie = auto_get_cookie(env=self.env)
        if auto_cookie:
            self.cookie_str = auto_cookie
            self.session.headers["Cookie"] = auto_cookie
            suffix = "" if self.env == "cn" else f"_{self.env}"
            cookie_path = _SCRIPT_DIR / f"cookie{suffix}.txt"
            cookie_path.write_text(auto_cookie, encoding="utf-8")
            return True
        return False

    def auto_detect_owner(self):
        if self._cached_owner:
            return self._cached_owner
        configured = _cfg("user", "owner")
        if configured and configured != "your_username":
            self._cached_owner = configured
            return configured
        try:
            cookie_str = self.session.headers.get("Cookie", "")
            if cookie_str:
                for part in cookie_str.split("; "):
                    if part.startswith("username="):
                        username = part.split("=", 1)[1].strip()
                        if username:
                            self._cached_owner = username
                            return username
                for part in cookie_str.split("; "):
                    if part.startswith("email="):
                        import urllib.parse
                        email = urllib.parse.unquote(part.split("=", 1)[1].strip())
                        username = email.split("@")[0]
                        if username:
                            self._cached_owner = username
                            return username
        except Exception:
            pass
        return ""

    def auto_detect_business(self):
        if self._cached_business:
            return self._cached_business
        configured = _cfg("ticket", "business")
        if configured:
            self._cached_business = configured
            return configured
        try:
            owner = self.auto_detect_owner()
            if owner:
                result = self.get_quick_query_business(owner)
                biz_list = result.get("data", [])
                if isinstance(biz_list, list) and biz_list:
                    bid = biz_list[0].get("id") or biz_list[0].get("business_id")
                    if bid:
                        self._cached_business = str(bid)
                        return str(bid)
        except Exception:
            pass
        return ""

    def auto_detect_ablog(self):
        if self._cached_ablog:
            return self._cached_ablog
        configured_id = _cfg("ablog", "business_id")
        configured_key = _cfg("ablog", "business_key")
        configured_apps = _cfg("group", "apps")
        if configured_id and configured_key and configured_apps:
            self._cached_ablog = {
                "business_id": configured_id,
                "business_key": configured_key,
                "apps": configured_apps,
            }
            return self._cached_ablog
        try:
            owner = self.auto_detect_owner()
            if owner:
                biz_result = self.get_quick_query_business(owner)
                biz_list = biz_result.get("data", [])
                if isinstance(biz_list, list) and biz_list:
                    bid = biz_list[0].get("id") or biz_list[0].get("business_id")
                    if bid:
                        detail = self.get_business_detail(bid)
                        detail_data = detail.get("data") or detail
                        if isinstance(detail_data, dict):
                            basic = detail_data.get("basic", {})
                            apps = basic.get("app_ids", [])
                            config = detail_data.get("config", {})
                            bkey = next(iter(config), "basic") if config else "basic"
                            result = {
                                "business_id": int(bid) if str(bid).isdigit() else bid,
                                "business_key": configured_key or bkey,
                                "apps": configured_apps or apps,
                            }
                            self._cached_ablog = result
                            return result
        except Exception:
            pass
        # Fall back to profile defaults for the current environment
        profile_bid = self.profile.get("ablog_business_id")
        profile_bkey = self.profile.get("ablog_business_key")
        profile_apps = self.profile.get("apps")
        fallback = {
            "business_id": configured_id or profile_bid or "",
            "business_key": configured_key or profile_bkey or "",
            "apps": configured_apps or profile_apps or [],
        }
        if any(fallback.values()):
            self._cached_ablog = fallback
        return fallback

    def create_ticket(self, name, owner=None, meego_id=None, virtual_table=None, groups=None,
                      description=None, business=None, region=None):
        if owner is None:
            owner = self.auto_detect_owner()
            if not owner:
                raise ValueError(
                    "无法自动获取用户名。请在 scripts/config.yaml 中设置 user.owner，"
                    "或确保浏览器已登录 Libra Gallery 后重试（脚本会自动从 Cookie 获取）"
                )
        if meego_id is None:
            meego_id = _cfg("user", "meego_id", 0)
        if description is None:
            description = _cfg("ticket", "description", "")
        if business is None:
            business = self.auto_detect_business()
        if region is None:
            region = self.profile.get("ticket_region", _cfg("ticket", "region", "cn"))
        if isinstance(owner, str):
            owner = [o.strip() for o in owner.split(",")]
        if isinstance(meego_id, str) and meego_id.isdigit():
            meego_id = int(meego_id)
        ticket_body = {
            "name": name,
            "owner": owner if isinstance(owner, list) else [owner],
            "meego_id": meego_id,
            "description": description,
            "region": region,
            "groups": groups or [],
        }
        if business:
            ticket_body["business"] = business
        body = {
            "virtual_table": virtual_table or [],
            "ticket": ticket_body,
        }
        return self._request("POST", "/v1/ticket/", json=body)

    def delete_ticket(self, ticket_id, region=None):
        if region is None:
            region = self.profile.get("ticket_region", _cfg("ticket", "region", "cn"))
        result = self._request("DELETE", f"/v1/ticket/{ticket_id}", params={"region": region})
        print(f"需求 {ticket_id} 已删除")
        return result

    def list_tickets(self, owner=None, page=1, page_size=20, region=None):
        if region is None:
            region = self.profile.get("ticket_region", _cfg("ticket", "region", "cn"))
        if owner is None:
            owner = self.auto_detect_owner()
        if isinstance(owner, list):
            owner = owner[0] if owner else None
        params = {
            "pageNumber": page,
            "pageSize": page_size,
            "sort_key": "update_time",
            "region": region,
            "is_ad": 0,
        }
        if owner:
            params["owner"] = owner
        return self._request("GET", "/v1/ticket/list", params=params)

    def get_business_list(self):
        return self._request("GET", "/v1/business/list", params={"is_official": "false"})

    def get_business_tags(self):
        return self._request("GET", "/v1/libra/group/business_tag")

    def get_apps(self, region=None):
        if region is None:
            region = self.profile.get("apps_region", _cfg("ticket", "region", "cn"))
        return self._request("GET", "/v1/apps", params={"region": region})

    def get_meego_info(self, meego_id):
        return self._request("GET", f"/v1/meego/{meego_id}")

    def get_meego_business(self, item_id=0, business_id=None):
        if business_id is None:
            business_id = _cfg("ticket", "business", "")
        return self._request("POST", "/v1/meego/business", json={
            "item_id": item_id,
            "business_id": business_id,
        })

    def get_business_detail(self, business_id):
        return self._request("GET", f"/v1/business/{business_id}")

    def get_ab_log_sql(self, business_id=None, business_key=None, user_types=None, app_ids=None):
        ablog = self.auto_detect_ablog()
        if business_id is None:
            business_id = ablog.get("business_id", _cfg("ablog", "business_id", 261))
        if business_key is None:
            business_key = ablog.get("business_key", _cfg("ablog", "business_key", "basic"))
        if user_types is None:
            user_types = "USER_UNIQUE_ID"
        if app_ids is None:
            app_ids = ablog.get("apps", _cfg("group", "apps", []))
        return self._request("POST", "/v1/business/online/ab_log_v2", json={
            "business_id": business_id,
            "business_key": business_key,
            "user_types": user_types,
            "app_ids": app_ids,
        })

    def get_certification_config(self):
        return self._request("GET", "/v1/libra/certification_center_config")

    def get_dim_tags(self):
        return self._request("GET", "/v1/dim/tag_list")

    def get_cm_config(self):
        return self._request("GET", "/v1/cm/config")

    def get_follow_flights(self):
        return self._request("GET", "/v1/follow_flights")

    def get_users(self):
        return self._request("GET", "/v1/users_v2")

    def online_check(self, group_ids, deploy_mode="normal"):
        return self._request("POST", "/v1/ticket/online/check", json={
            "group_list": group_ids if isinstance(group_ids, list) else [group_ids],
            "deploy_mode": deploy_mode,
        })

    def llm_online_prechecks(self, group_ids, develop_owner=None, deploy_mode="normal", backfill=False):
        if develop_owner is None:
            develop_owner = self.auto_detect_owner()
            if isinstance(develop_owner, list):
                develop_owner = develop_owner[0] if develop_owner else ""
        gids = group_ids if isinstance(group_ids, list) else [group_ids]
        return self._request("POST", "/v1/llm/online_prechecks", json={
            "group_ids": gids,
            "user_form": {
                "flights": [],
                "developOwner": develop_owner,
                "expected_backfill_date_range": [],
                "group_ids": gids,
                "backfill": backfill,
                "ttp_list": [],
                "deploy_mode": deploy_mode,
            },
        })

    def create_online_state(self, ticket_id, group_ids, creator=None, develop_owner=None,
                            meego_id=0, deploy_mode="normal", backfill=False):
        if creator is None:
            creator = self.auto_detect_owner()
            if isinstance(creator, list):
                creator = creator[0] if creator else ""
        if develop_owner is None:
            develop_owner = creator
        gids = group_ids if isinstance(group_ids, list) else [group_ids]
        return self._request("POST", "/v1/state/", json={
            "creator": creator,
            "flights": [],
            "developOwner": develop_owner,
            "expected_backfill_date_range": [],
            "group_ids": gids,
            "backfill": backfill,
            "ttp_list": [],
            "deploy_mode": deploy_mode,
            "meego_id": meego_id,
            "ticket_id": str(ticket_id),
        })

    def trigger_state_event(self, event, ticket_id, group_ids, operator=None, develop_owner=None,
                            meego_id=0, deploy_mode="normal", backfill=False,
                            whitelist_auto_running=True):
        if operator is None:
            operator = self.auto_detect_owner()
            if not operator:
                operator = _cfg("user", "owner", "")
                if isinstance(operator, list):
                    operator = operator[0] if operator else ""
        if develop_owner is None:
            develop_owner = operator
        gids = group_ids if isinstance(group_ids, list) else [group_ids]
        return self._request("PUT", "/v1/state/event", json={
            "event": event,
            "meego_id": meego_id,
            "flights": [],
            "developOwner": develop_owner,
            "expected_backfill_date_range": [],
            "group_ids": gids,
            "backfill": backfill,
            "ttp_list": [],
            "deploy_mode": deploy_mode,
            "operator": operator,
            "ticket_id": str(ticket_id),
            "whitelist_auto_running": whitelist_auto_running,
        })

    def cancel_online(self, ticket_id, group_ids, operator=None, develop_owner=None,
                      meego_id=0, deploy_mode="normal"):
        return self.trigger_state_event(
            "CANCEL_ALL", ticket_id, group_ids,
            operator=operator, develop_owner=develop_owner,
            meego_id=meego_id, deploy_mode=deploy_mode,
        )

    def get_mark_list(self):
        return self._request("GET", "/v1/ticket/mark_list")

    def get_quick_query_business(self, username=None):
        if username is None:
            username = self.auto_detect_owner()
            if isinstance(username, list):
                username = username[0] if username else ""
        return self._request("GET", "/v1/business/list/quick_query", params={"username": username})

    def get_cm_users(self):
        return self._request("GET", "/v1/cm_users")

    def list_all_groups(self, owner=None, name=None, status=None):
        """查询某个 owner 的所有指标组（自动分页遍历所有需求）。

        Args:
            owner: 需求负责人，默认自动探测当前用户
            name: 按需求名称过滤（模糊匹配）
            status: 按指标组开发状态过滤，如 "ONLINE"、"OFFLINE"

        Returns:
            list: 所有指标组信息列表，每项包含 ticket_id, ticket_name, group 详情等
        """
        if owner is None:
            owner = self.auto_detect_owner()
        region = self.profile.get("ticket_region", _cfg("ticket", "region", "cn"))

        all_groups = []
        page = 1
        page_size = 50
        while True:
            params = {
                "pageNumber": page,
                "pageSize": page_size,
                "sort_key": "update_time",
                "region": region,
                "is_ad": 0,
            }
            if owner:
                params["owner"] = owner
            if name:
                params["name"] = name
            result = self._request("GET", "/v1/ticket/list", params=params)
            data = result.get("data", {})
            tickets = data.get("tickets", [])
            total = data.get("total", 0)

            for t in tickets:
                ticket_id = t.get("id")
                ticket_name = t.get("name", "")
                ticket_status = t.get("status", "")
                for g in t.get("groups", []):
                    group_status = g.get("develop_status", "")
                    if status and group_status != status:
                        continue
                    all_groups.append({
                        "ticket_id": ticket_id,
                        "ticket_name": ticket_name,
                        "ticket_status": ticket_status,
                        "group_id": g.get("id"),
                        "group_name": g.get("name", ""),
                        "libra_group_id": g.get("libra_group_id") or g.get("sg_libra_group_id"),
                        "owner": g.get("owner", []),
                        "develop_status": group_status,
                        "apps": g.get("apps", []),
                        "dorado_regions": g.get("dorado_regions", ""),
                        "metrics_count": len(g.get("metrics", [])),
                        "dimensions_count": len(g.get("dimensions", [])),
                        "cum_start_time": g.get("cum_start_time", ""),
                        "url": gallery_url(ticket_id, self.env),
                    })

            if page * page_size >= total or not tickets:
                break
            page += 1

        return all_groups

    def get_ticket_history(self, ticket_id):
        return self._request("GET", "/v1/ticket/history", params={"ticket_id": ticket_id})

    def get_ticket_online_history(self, ticket_id):
        return self._request("GET", "/v1/ticket/ticket_online_history", params={"ticket_id": ticket_id})

    def get_ticket_state(self, ticket_id, group_ids=None):
        path = f"/v1/state/{ticket_id}"
        params = {}
        if group_ids:
            if isinstance(group_ids, list):
                params["group_ids"] = [str(g) for g in group_ids]
            else:
                params["group_ids"] = str(group_ids)
        return self._request("GET", path, params=params)

    def get_all_tags(self):
        return self._request("GET", "/v1/ticket/group/get_all_tags")

    def get_decc_dims(self):
        return self._request("GET", "/v1/decc/dim")

    def get_dim_versions(self, dim_id):
        return self._request("GET", "/v1/dim/versions", params={"dim_id": dim_id})


class TicketEditor:
    def __init__(self, client, ticket_id, snapshot_id=None):
        self.client = client
        self.ticket_id = ticket_id
        self.snapshot_id = snapshot_id
        self.data = None
        self.original_data = None
        self.virtual_table = None
        self.ticket = None
        self._uuid_to_name = {}
        self._table_uuid_to_key = {}
        self.load()

    @classmethod
    def create_new(cls, client, name, owner=None, meego_id=None, description=None, business=None, region=None):
        result = client.create_ticket(name, owner, meego_id, description=description, business=business, region=region)
        data = result.get("data", result)
        new_ticket_id = data.get("ticket", {}).get("id")
        if not new_ticket_id:
            raise RuntimeError(f"创建需求失败，未返回 ticket_id: {result}")
        print(f"需求创建成功 → {gallery_url(new_ticket_id, client.env)}")
        editor = cls(client, new_ticket_id)
        return editor

    @classmethod
    def create_from(cls, client, source_editor, source_group_names=None, new_ticket_name=None, owner=None, meego_id=None,
                    rename_map=None, description=None, business=None, copy_data_sources=True, region=None):
        # source_group_names=None 表示复制所有指标组
        if source_group_names is None:
            source_group_names = [g["name"] for g in source_editor.list_groups()]
        elif isinstance(source_group_names, str):
            source_group_names = [source_group_names]

        if new_ticket_name is None:
            new_ticket_name = source_editor.ticket.get("name", "复制的需求")

        vt_copy = copy.deepcopy(source_editor.virtual_table) if copy_data_sources else []

        # 浏览器复制时会清洗 group 的服务端只读字段
        GROUP_COPY_REMOVE = {
            "id", "libra_group_id", "sg_libra_group_id", "ticket_id",
            "develop_status", "develop_owner",
            "ab_log_sql", "business_tag_id", "conf", "status", "version_id", "draft_id",
            "is_draft", "is_stable", "workflow_id", "state", "online_status",
            "created_at", "updated_at", "create_time", "update_time",
        }
        groups_copy = []
        for gn in source_group_names:
            source_group = source_editor._resolve_group(gn)
            cloned = copy.deepcopy(source_group)
            if rename_map and gn in rename_map:
                cloned["name"] = rename_map[gn]
            for k in GROUP_COPY_REMOVE:
                cloned.pop(k, None)
            groups_copy.append(cloned)

        result = client.create_ticket(
            name=new_ticket_name,
            owner=owner,
            meego_id=meego_id,
            virtual_table=vt_copy,
            groups=groups_copy,
            description=description,
            business=business,
            region=region,
        )
        data = result.get("data", result)
        new_ticket_id = data.get("ticket", {}).get("id")
        if not new_ticket_id:
            raise RuntimeError(f"创建需求失败，未返回 ticket_id: {result}")
        print(f"需求创建成功 → {gallery_url(new_ticket_id, client.env)}")
        editor = cls(client, new_ticket_id)
        return editor

    @classmethod
    def create_from_snapshot(cls, client, source_ticket_id, snapshot_id, source_group_names=None,
                             new_ticket_name=None, owner=None, meego_id=None, rename_map=None,
                             description=None, business=None, copy_data_sources=True, region=None):
        """从指定版本（snapshot）的需求中克隆指标组到新需求。

        Args:
            client: LibraGalleryClient 实例
            source_ticket_id: 源需求 ID
            snapshot_id: 源需求的版本号（snapshot_id）
            source_group_names: 要克隆的指标组名称列表，None 表示克隆该版本的所有指标组
            new_ticket_name: 新需求名称，默认自动生成
            owner: 新需求负责人，默认自动探测
            meego_id: Meego 工单 ID
            rename_map: 指标组重命名映射 {"旧名称": "新名称"}
            description: 新需求描述
            business: 业务线 ID
            copy_data_sources: 是否复制数据源，默认 True
            region: 区域

        Returns:
            TicketEditor: 新需求的编辑器实例
        """
        source_editor = cls(client, source_ticket_id, snapshot_id=snapshot_id)

        source_groups = source_editor.ticket.get("groups", [])
        if not source_groups:
            raise RuntimeError(f"版本 {snapshot_id} 中没有指标组")

        if source_group_names is None:
            source_group_names = [g["name"] for g in source_groups]
        elif isinstance(source_group_names, str):
            source_group_names = [source_group_names]

        if new_ticket_name is None:
            source_name = source_editor.ticket.get("name", "")
            new_ticket_name = f"{source_name} (从版本{snapshot_id}复制)"

        print(f"从需求 {source_ticket_id} 版本 {snapshot_id} 克隆 {len(source_group_names)} 个指标组...")
        for gn in source_group_names:
            print(f"  - {gn}")

        return cls.create_from(
            client, source_editor, source_group_names,
            new_ticket_name=new_ticket_name, owner=owner, meego_id=meego_id,
            rename_map=rename_map, description=description, business=business,
            copy_data_sources=copy_data_sources, region=region,
        )

    def load(self):
        raw = self.client.get_ticket(self.ticket_id, snapshot_id=self.snapshot_id)
        data = raw.get("data") or raw
        self._build_uuid_mapping(data.get("virtual_table", []))
        self._convert_uuid_to_name(data)
        self.original_data = copy.deepcopy(data)
        self.data = data
        self.virtual_table = data.get("virtual_table", [])
        self.ticket = data.get("ticket", {})

    def _build_uuid_mapping(self, virtual_tables):
        self._uuid_to_name = {}
        self._table_uuid_to_key = {}
        for vt in virtual_tables:
            vt_key = vt.get("key", "")
            vt_name = vt.get("name", "")
            is_uuid = len(vt_key) == 32 and all(c in "0123456789abcdef" for c in vt_key)

            if not vt_name:
                continue

            columns = vt.get("columns") or []

            if is_uuid:
                self._table_uuid_to_key[vt_key] = vt_name
                for col in columns:
                    col_key = col.get("key", "")
                    col_name = col.get("name", col_key)
                    if col_key:
                        ref = f"{vt_key}:{col_key}"
                        self._uuid_to_name[ref] = col_name

        idx = 1
        key_remap = {}
        for vt in virtual_tables:
            vt_key = vt.get("key", "")
            vt_name = vt.get("name", "")
            is_uuid = len(vt_key) == 32 and all(c in "0123456789abcdef" for c in vt_key)
            if is_uuid:
                key_remap[vt_key] = vt_name if vt_name else f"T{idx}"
                idx += 1
            else:
                key_remap[vt_key] = vt_key

        self._key_remap = key_remap

        full_mapping = {}
        for ref, col_name in self._uuid_to_name.items():
            table_uuid, _ = ref.split(":", 1)
            new_table_key = key_remap.get(table_uuid, table_uuid)
            full_mapping[ref] = f"{new_table_key}:{col_name}"

        self._full_ref_mapping = full_mapping

    def _convert_uuid_to_name(self, data):
        for vt in data.get("virtual_table", []):
            old_key = vt.get("key", "")
            if old_key in self._key_remap:
                vt["key"] = self._key_remap[old_key]
            for col in vt.get("columns") or []:
                col_key = col.get("key", "")
                col_name = col.get("name", col_key)
                if col_key and col_key != col_name:
                    col["key"] = col_name
                col.pop("id", None)

        groups = data.get("ticket", {}).get("groups", [])
        if not groups:
            return

        for group in groups:
            for metric in group.get("metrics", []):
                self._convert_sql_refs(metric.get("sql", {}))
            for dim in group.get("dimensions", []):
                self._convert_key_refs(dim)

    def _convert_sql_refs(self, sql_obj):
        if not sql_obj:
            return
        for side in ("left", "right"):
            part = sql_obj.get(side, {})
            if not part:
                continue
            if part.get("key"):
                part["key"] = [self._full_ref_mapping.get(k, k) for k in part["key"]]
            if part.get("key_sql"):
                ks = part["key_sql"]
                for old_ref, new_ref in self._full_ref_mapping.items():
                    ks = ks.replace(old_ref, new_ref)
                part["key_sql"] = ks

    def _convert_key_refs(self, dim):
        if dim.get("key"):
            dim["key"] = [self._full_ref_mapping.get(k, k) for k in dim["key"]]
        if dim.get("key_sql"):
            ks = dim["key_sql"]
            for old_ref, new_ref in self._full_ref_mapping.items():
                ks = ks.replace(old_ref, new_ref)
            dim["key_sql"] = ks

    def _resolve_group(self, group_index_or_name):
        groups = self.ticket.get("groups", [])
        if not groups:
            raise ValueError("Ticket 中没有指标组")

        if isinstance(group_index_or_name, int):
            if 0 <= group_index_or_name < len(groups):
                return groups[group_index_or_name]
            raise IndexError(f"指标组索引 {group_index_or_name} 超出范围 (共 {len(groups)} 个)")

        name = str(group_index_or_name).strip()
        for g in groups:
            if g.get("name", "").strip() == name:
                return g
            if str(g.get("id")) == name or str(g.get("libra_group_id")) == name:
                return g

        available = [g.get("name", "未命名") for g in groups]
        raise ValueError(f"未找到指标组 '{name}'，可用的指标组: {available}")

    def _resolve_all_groups(self, group_index_or_name):
        """返回所有匹配的指标组（包括服务端 merge 产生的重复副本）。
        对于编辑操作，需要同步修改所有副本以保持数据一致性。"""
        groups = self.ticket.get("groups", [])
        if not groups:
            raise ValueError("Ticket 中没有指标组")

        if isinstance(group_index_or_name, int):
            # 按索引时，找到该 group 的 id，然后返回所有同 id 的 group
            if 0 <= group_index_or_name < len(groups):
                target = groups[group_index_or_name]
                tid = target.get("id")
                if tid:
                    return [g for g in groups if g.get("id") == tid]
                return [target]
            raise IndexError(f"指标组索引 {group_index_or_name} 超出范围 (共 {len(groups)} 个)")

        name = str(group_index_or_name).strip()
        matched = []
        for g in groups:
            if g.get("name", "").strip() == name:
                matched.append(g)
            elif str(g.get("id")) == name or str(g.get("libra_group_id")) == name:
                matched.append(g)
        if not matched:
            available = [g.get("name", "未命名") for g in groups]
            raise ValueError(f"未找到指标组 '{name}'，可用的指标组: {available}")
        return matched

    def find_group(self, name=None, group_id=None):
        groups = self.ticket.get("groups", [])
        search_name = name.strip() if isinstance(name, str) else name
        for g in groups:
            if search_name is not None and g.get("name", "").strip() == search_name:
                return g
            if group_id is not None and (g.get("id") == group_id or g.get("libra_group_id") == group_id):
                return g
        return None

    def list_data_sources(self):
        result = []
        seen_keys = set()
        for vt in self.virtual_table:
            k = vt.get("key", "")
            if k and k in seen_keys:
                continue
            if k:
                seen_keys.add(k)
            mapping = vt.get("mapping_detail") or {}
            id_type_key = next(iter(mapping), None) if mapping else None
            sql_preview = ""
            if id_type_key and isinstance(mapping.get(id_type_key), dict):
                sql_preview = mapping[id_type_key].get("sql", "")[:80]
            cols = vt.get("columns") or []
            result.append({
                "key": k,
                "name": vt.get("name", ""),
                "column_count": len(cols),
                "columns": [c.get("name", c.get("key", "")) for c in cols],
                "sql_preview": sql_preview,
            })
        return result

    def get_data_source_sql(self, vt_name):
        for vt in self.virtual_table:
            if vt.get("key") == vt_name or vt.get("name") == vt_name:
                mapping = vt.get("mapping_detail") or {}
                id_type_key = next(iter(mapping), None) if mapping else None
                if id_type_key and isinstance(mapping.get(id_type_key), dict):
                    return mapping[id_type_key].get("sql", "")
                return mapping.get("sql", "")
        raise ValueError(f"未找到数据源 '{vt_name}'，可用: {[v.get('key') for v in self.virtual_table]}")

    def list_groups(self):
        groups = self.ticket.get("groups", [])
        result = []
        seen_ids = set()
        for i, g in enumerate(groups):
            gid = g.get("id")
            if gid and gid in seen_ids:
                continue
            if gid:
                seen_ids.add(gid)
            result.append({
                "index": i,
                "id": gid,
                "name": g.get("name", ""),
                "libra_group_id": g.get("libra_group_id"),
                "group_type": g.get("group_type", ""),
                "metrics_count": len(g.get("metrics", [])),
                "dimensions_count": len(g.get("dimensions", [])),
            })
        return result

    def list_metrics(self, group_index_or_name):
        group = self._resolve_group(group_index_or_name)
        result = []
        for i, m in enumerate(group.get("metrics", [])):
            sql = m.get("sql", {})
            left = sql.get("left", {})
            right = sql.get("right", {})
            result.append({
                "index": i,
                "name": m.get("name", ""),
                "description": m.get("description", ""),
                "left_key_sql": left.get("key_sql", ""),
                "left_type": left.get("type", ""),
                "right_key_sql": right.get("key_sql", ""),
                "right_type": right.get("type", ""),
            })
        return result

    def list_dimensions(self, group_index_or_name):
        group = self._resolve_group(group_index_or_name)
        result = []
        for i, d in enumerate(group.get("dimensions", [])):
            conf = d.get("conf", {})
            entry = {
                "index": i,
                "name": d.get("name", ""),
                "description": d.get("description", ""),
                "dim_type": d.get("dim_type", ""),
                "key": d.get("key", []),
                "use_conf": conf.get("use_conf", False),
            }
            if conf.get("use_conf"):
                entry["use_types"] = conf.get("use_types", "RPT")
                entry["update_type"] = conf.get("update_type", "first")
                entry["enums_update_type"] = conf.get("enums_update_type", "merge")
                enabled = [k for k in ("use_custom", "use_num", "use_split", "use_combine",
                                        "use_base_user", "is_ablog_dim", "use_libra_key",
                                        "is_query", "enums_filter") if conf.get(k)]
                if enabled:
                    entry["enabled_options"] = enabled
            result.append(entry)
        return result

    def add_metric(self, group_index_or_name, name, left_key_sql, left_type="pv",
                   right_key_sql=None, right_type=None, description="", name_en="", conf=None):
        result = None
        for group in self._resolve_all_groups(group_index_or_name):
            metric = make_metric(name, left_key_sql, left_type, right_key_sql, right_type,
                                 description, name_en, conf)
            group.setdefault("metrics", []).append(metric)
            if result is None:
                result = metric
        return result

    def remove_metric(self, group_index_or_name, metric_name):
        removed = None
        for group in self._resolve_all_groups(group_index_or_name):
            metrics = group.get("metrics", [])
            for i, m in enumerate(metrics):
                if m.get("name") == metric_name:
                    removed = metrics.pop(i)
                    break
        if removed is None:
            raise ValueError(f"未找到指标 '{metric_name}'")
        return removed

    def update_metric(self, group_index_or_name, metric_name, **kwargs):
        updated = None
        for group in self._resolve_all_groups(group_index_or_name):
            for m in group.get("metrics", []):
                if m.get("name") == metric_name:
                    for k, v in kwargs.items():
                        if k in ("left_key_sql", "left_type", "right_key_sql", "right_type"):
                            sql = m.setdefault("sql", {})
                            if k.startswith("left"):
                                side = sql.setdefault("left", {})
                                field = k.replace("left_", "")
                                if field == "key_sql":
                                    side["key_sql"] = v
                                    side["key"] = [v] if v else []
                                else:
                                    side[field] = v
                            else:
                                side = sql.setdefault("right", {})
                                field = k.replace("right_", "")
                                if field == "key_sql":
                                    side["key_sql"] = v or ""
                                    side["key"] = [v] if v else None
                                elif field == "type":
                                    side["type"] = v or ""
                                    # base_user 类型不需要 key/key_sql，确保结构完整
                                    if v == "base_user":
                                        side.setdefault("key", None)
                                        side.setdefault("key_sql", "")
                                    elif v in ("pv", "uv") and "key_sql" not in side:
                                        # pv/uv 类型需要 key_sql，如果未设置则初始化为空
                                        side.setdefault("key_sql", "")
                                        side.setdefault("key", None)
                                else:
                                    side[field] = v or ""
                        else:
                            m[k] = v
                    if updated is None:
                        updated = m
                    # 更新名称后需要用新名称匹配后续副本中的同名指标
                    if "name" in kwargs:
                        metric_name = kwargs["name"]
                    break
        if updated is None:
            raise ValueError(f"未找到指标 '{metric_name}'")
        return updated

    def add_dimension(self, group_index_or_name, name, key, dim_type="METRIC_DIMENSION",
                      description="", name_en="", conf=None):
        result = None
        for group in self._resolve_all_groups(group_index_or_name):
            dim = make_dimension(name, key, dim_type, description, name_en, conf)
            group.setdefault("dimensions", []).append(dim)
            if result is None:
                result = dim
        return result

    def remove_dimension(self, group_index_or_name, dim_name):
        removed = None
        for group in self._resolve_all_groups(group_index_or_name):
            dims = group.get("dimensions", [])
            for i, d in enumerate(dims):
                if d.get("name") == dim_name:
                    removed = dims.pop(i)
                    break
        if removed is None:
            raise ValueError(f"未找到维度 '{dim_name}'")
        return removed

    def update_dimension(self, group_index_or_name, dim_name, **kwargs):
        updated = None
        for group in self._resolve_all_groups(group_index_or_name):
            for d in group.get("dimensions", []):
                if d.get("name") == dim_name:
                    for k, v in kwargs.items():
                        if k == "key":
                            d["key"] = [v] if isinstance(v, str) else v
                        elif k == "conf":
                            d.setdefault("conf", {}).update(v)
                        else:
                            d[k] = v
                    if updated is None:
                        updated = d
                    if "name" in kwargs:
                        dim_name = kwargs["name"]
                    break
        if updated is None:
            raise ValueError(f"未找到维度 '{dim_name}'")
        return updated

    def reset_dimension_conf(self, group_index_or_name, dim_name):
        reset = None
        for group in self._resolve_all_groups(group_index_or_name):
            for d in group.get("dimensions", []):
                if d.get("name") == dim_name:
                    d["conf"] = make_default_dimension_conf()
                    if reset is None:
                        reset = d
                    break
        if reset is None:
            raise ValueError(f"未找到维度 '{dim_name}'")
        return reset

    def reset_dimensions_conf(self, group_index_or_name, dim_names):
        results = []
        for name in dim_names:
            results.append(self.reset_dimension_conf(group_index_or_name, name))
        return results

    def get_dimension_conf(self, group_index_or_name, dim_name):
        group = self._resolve_group(group_index_or_name)
        for d in group.get("dimensions", []):
            if d.get("name") == dim_name:
                return d.get("conf", {})
        raise ValueError(f"未找到维度 '{dim_name}'")

    def update_data_source_sql(self, vt_name, sql, column_remap=None):
        """更新数据源 SQL。

        Args:
            vt_name: 数据源名称（如 "T1"）
            sql: 新的 SQL 字符串或 .sql 文件路径
            column_remap: 可选，列名映射字典，如 {"old_col": "new_col"}。
                          当 SQL 中列名发生变化时，自动更新指标和维度中引用旧列名的 key。
        """
        sql = _resolve_sql(sql)
        _warn_sql_tx_prefix(sql, vt_name)

        target_vt = None
        for vt in self.virtual_table:
            if vt.get("key") == vt_name or vt.get("name") == vt_name:
                target_vt = vt
                break

        if target_vt is None:
            raise ValueError(f"未找到数据源 '{vt_name}'，可用: {[v.get('key') for v in self.virtual_table]}")

        # 记录旧列名用于变化检测
        old_col_names = set()
        for col in (target_vt.get("columns") or []):
            old_col_names.add(col.get("name", ""))

        parse_result = self.client.parse_sql(sql)
        parsed_data = parse_result.get("data") or parse_result

        mapping = target_vt.setdefault("mapping_detail", {})
        id_type_key = next(iter(mapping), None) if mapping else None
        if id_type_key and isinstance(mapping[id_type_key], dict):
            mapping[id_type_key]["sql"] = sql
            if "columns" in parsed_data:
                new_cols = []
                for c in parsed_data["columns"]:
                    new_cols.append({
                        "data_type": c.get("data_type", "STRING"),
                        "description": c.get("description", ""),
                        "id": c.get("id", 0),
                        "is_pk": c.get("is_pk", "0"),
                        "key": c.get("name", ""),
                        "name": c.get("name", ""),
                    })
                mapping[id_type_key]["preSqlColumns"] = new_cols
                target_vt["columns"] = [
                    {"key": c["name"], "name": c["name"], "data_type": c.get("data_type", "STRING"),
                     "is_pk": c.get("is_pk", "0"), "description": ""}
                    for c in parsed_data["columns"]
                ]
        else:
            # mapping_detail 为空或非嵌套结构，创建标准嵌套结构
            mapping["user_unique_id"] = {"type": "user_unique_id", "sql": sql}
            if "columns" in parsed_data:
                new_cols = []
                for c in parsed_data["columns"]:
                    new_cols.append({
                        "data_type": c.get("data_type", "STRING"),
                        "description": c.get("description", ""),
                        "id": c.get("id", 0),
                        "is_pk": c.get("is_pk", "0"),
                        "key": c.get("name", ""),
                        "name": c.get("name", ""),
                    })
                mapping["user_unique_id"]["preSqlColumns"] = new_cols
                target_vt["columns"] = [
                    {"key": c["name"], "name": c["name"], "data_type": c.get("data_type", "STRING"),
                     "is_pk": c.get("is_pk", "0"), "description": ""}
                    for c in parsed_data["columns"]
                ]

        # 检测列名变化并应用 column_remap
        new_col_names = set()
        for col in (target_vt.get("columns") or []):
            new_col_names.add(col.get("name", ""))

        removed_cols = old_col_names - new_col_names
        added_cols = new_col_names - old_col_names

        if removed_cols or added_cols:
            if removed_cols:
                print(f"⚠️  数据源 {vt_name} 列名变化 - 移除: {sorted(removed_cols)}")
            if added_cols:
                print(f"⚠️  数据源 {vt_name} 列名变化 - 新增: {sorted(added_cols)}")

        if column_remap:
            vt_key = target_vt.get("key", vt_name)
            remap_count = self._apply_column_remap(vt_key, column_remap)
            if remap_count:
                print(f"✅ 已自动更新 {remap_count} 处指标/维度列引用: {column_remap}")
        elif removed_cols:
            # 检查是否有指标/维度引用了被移除的列
            vt_key = target_vt.get("key", vt_name)
            affected = self._find_affected_refs(vt_key, removed_cols)
            if affected:
                print(f"⚠️  以下指标/维度引用了已移除的列，保存后可能丢失:")
                for item in affected:
                    print(f"     {item}")
                print(f"   建议: 使用 column_remap 参数自动更新引用，如:")
                suggestion = {col: "?" for col in sorted(removed_cols)}
                print(f"     editor.update_data_source_sql(\"{vt_name}\", sql, column_remap={suggestion})")

        return target_vt

    def _apply_column_remap(self, vt_key, column_remap):
        """将指标和维度中引用旧列名的 key 替换为新列名。返回替换次数。"""
        count = 0
        for group in self.ticket.get("groups", []):
            for metric in group.get("metrics", []):
                count += self._remap_metric_refs(metric, vt_key, column_remap)
            for dim in group.get("dimensions", []):
                count += self._remap_dim_refs(dim, vt_key, column_remap)
        return count

    def _remap_metric_refs(self, metric, vt_key, column_remap):
        """替换指标中引用旧列名的 key。使用占位符避免链式重命名冲突。"""
        count = 0
        sql_obj = metric.get("sql", {})
        if not sql_obj:
            return 0
        # 构建 old_ref → placeholder → new_ref 映射，避免链式冲突
        # 例如 {a→b, b→c} 时，先把 a→__PH_0__、b→__PH_1__，再把占位符替换为最终值
        placeholders = {}
        for i, (old_col, new_col) in enumerate(column_remap.items()):
            old_ref = f"{vt_key}:{old_col}"
            new_ref = f"{vt_key}:{new_col}"
            ph = f"__REMAP_PH_{i}__"
            placeholders[old_ref] = (ph, new_ref)
        for side in ("left", "right"):
            part = sql_obj.get(side, {})
            if not part:
                continue
            # 第一遍：old_ref → placeholder
            if part.get("key_sql"):
                for old_ref, (ph, _) in placeholders.items():
                    if old_ref in part["key_sql"]:
                        part["key_sql"] = part["key_sql"].replace(old_ref, ph)
                        count += 1
            if part.get("key"):
                new_keys = [placeholders[k][0] if k in placeholders else k for k in part["key"]]
                if new_keys != part["key"]:
                    count += sum(1 for old, new in zip(part["key"], new_keys) if old != new)
                part["key"] = new_keys
            # 第二遍：placeholder → new_ref
            if part.get("key_sql"):
                for _, (ph, new_ref) in placeholders.items():
                    part["key_sql"] = part["key_sql"].replace(ph, new_ref)
            if part.get("key"):
                ph_to_new = {ph: new_ref for _, (ph, new_ref) in placeholders.items()}
                part["key"] = [ph_to_new.get(k, k) for k in part["key"]]
        return count

    def _remap_dim_refs(self, dim, vt_key, column_remap):
        """替换维度中引用旧列名的 key。使用占位符避免链式重命名冲突。"""
        count = 0
        placeholders = {}
        for i, (old_col, new_col) in enumerate(column_remap.items()):
            old_ref = f"{vt_key}:{old_col}"
            new_ref = f"{vt_key}:{new_col}"
            ph = f"__REMAP_PH_{i}__"
            placeholders[old_ref] = (ph, new_ref)
        # 第一遍：old_ref → placeholder
        if dim.get("key_sql"):
            for old_ref, (ph, _) in placeholders.items():
                if old_ref in dim["key_sql"]:
                    dim["key_sql"] = dim["key_sql"].replace(old_ref, ph)
                    count += 1
        if dim.get("key"):
            new_keys = [placeholders[k][0] if k in placeholders else k for k in dim["key"]]
            if new_keys != dim["key"]:
                count += sum(1 for old, new in zip(dim["key"], new_keys) if old != new)
            dim["key"] = new_keys
        # 第二遍：placeholder → new_ref
        if dim.get("key_sql"):
            for _, (ph, new_ref) in placeholders.items():
                dim["key_sql"] = dim["key_sql"].replace(ph, new_ref)
        if dim.get("key"):
            ph_to_new = {ph: new_ref for _, (ph, new_ref) in placeholders.items()}
            dim["key"] = [ph_to_new.get(k, k) for k in dim["key"]]
        return count

    def _find_affected_refs(self, vt_key, removed_cols):
        """查找引用了已移除列的指标和维度名称。"""
        affected = []
        removed_refs = {f"{vt_key}:{col}" for col in removed_cols}
        for group in self.ticket.get("groups", []):
            group_name = group.get("name", "?")
            for metric in group.get("metrics", []):
                sql_obj = metric.get("sql", {})
                if not sql_obj:
                    continue
                for side in ("left", "right"):
                    part = sql_obj.get(side, {})
                    if not part:
                        continue
                    ks = part.get("key_sql", "")
                    if any(ref in ks for ref in removed_refs):
                        affected.append(f"指标 [{group_name}] {metric.get('name')} ({side}: {ks})")
            for dim in group.get("dimensions", []):
                ks = dim.get("key_sql", "")
                if any(ref in ks for ref in removed_refs):
                    affected.append(f"维度 [{group_name}] {dim.get('name')} (key: {ks})")
                elif dim.get("key"):
                    for k in dim["key"]:
                        if k in removed_refs:
                            affected.append(f"维度 [{group_name}] {dim.get('name')} (key: {k})")
                            break
        return affected

    def add_data_source(self, key, sql=None, source_type=None, region=None, dorado_region=None, id_type=None):
        """添加新数据源。

        Args:
            id_type: 统计粒度，可选 "user_unique_id"（默认，设备维度）或 "user_id"（UID 维度）。
                     UID 维度时 mapping_detail 使用 "user_id" 作为 key，数据源 SQL 应输出 user_id 列。
        """
        if source_type is None:
            source_type = _cfg("data_source", "source_type", "customize")
        if dorado_region is None:
            dorado_region = self.client.profile.get("data_source_dorado_region", "cn")
        if region is None:
            region = self.client.profile.get("data_source_region", None)
        if id_type is None:
            id_type = "user_unique_id"
        for vt in self.virtual_table:
            if vt.get("key") == key:
                raise ValueError(f"数据源 '{key}' 已存在")

        if sql:
            sql = _resolve_sql(sql)
            _warn_sql_tx_prefix(sql, key)

        if region:
            conf = {
                "regions": [region],
                f"regions_{region}_conf": {"dorado_region": dorado_region},
            }
        else:
            conf = {}

        # mapping_detail key 由 id_type 决定：
        # - "user_unique_id" → key="user_unique_id", type="user_unique_id", name="Tx_user_unique_id"
        # - "user_id"        → key="user_id",        type="user_id",        name="Tx_user_id"
        mapping_key = id_type  # "user_unique_id" or "user_id"
        mapping_name = f"{key}_{id_type}"

        vt = {
            "key": key,
            "name": key,
            "mapping_detail": {
                mapping_key: {
                    "type": id_type,
                    "name": mapping_name,
                    "sql": sql or "",
                    "sourceType": source_type,
                    "dc": "row",
                    "primary_dest_region": dorado_region,
                    "preSqlColumns": [],
                }
            },
            "columns": [],
            "conf": conf,
        }

        if sql:
            try:
                parse_result = self.client.parse_sql(sql)
                parsed_data = parse_result.get("data") or parse_result
                if "columns" in parsed_data:
                    cols = []
                    for c in parsed_data["columns"]:
                        cols.append({
                            "data_type": c.get("data_type", "STRING"),
                            "description": "",
                            "id": 0,
                            "is_pk": c.get("is_pk", "0"),
                            "key": c.get("name", ""),
                            "name": c.get("name", ""),
                        })
                    vt["mapping_detail"][mapping_key]["preSqlColumns"] = cols
                    vt["columns"] = [
                        {"key": c["name"], "name": c["name"], "data_type": c.get("data_type", "STRING"),
                         "is_pk": "0", "description": ""}
                        for c in parsed_data["columns"]
                    ]
            except Exception as e:
                print(f"⚠️  解析数据源 {key} 的 SQL 失败: {e}（列信息为空，指标/维度引用可能受影响）")

        self.virtual_table.append(vt)
        return vt

    def remove_data_source(self, key):
        for i, vt in enumerate(self.virtual_table):
            if vt.get("key") == key or vt.get("name") == key:
                return self.virtual_table.pop(i)
        raise ValueError(f"未找到数据源 '{key}'，可用: {[v.get('key') for v in self.virtual_table]}")

    def rename_data_source(self, old_key, new_key):
        """重命名数据源 key，并自动更新所有指标和维度中的引用。

        典型场景：删除 T1 后将 T2 改名为 T1，使指标组只保留一个数据源且引用统一。

        Args:
            old_key: 当前数据源 key（如 "T2"）
            new_key: 新 key（如 "T1"）

        Returns:
            替换引用的总次数
        """
        # 1. 查找并修改 virtual_table 中的 key 和 name
        target_vt = None
        for vt in self.virtual_table:
            if vt.get("key") == old_key or vt.get("name") == old_key:
                target_vt = vt
                break
        if target_vt is None:
            raise ValueError(f"未找到数据源 '{old_key}'，可用: {[v.get('key') for v in self.virtual_table]}")

        # 检查新 key 是否已被占用
        for vt in self.virtual_table:
            if vt is not target_vt and (vt.get("key") == new_key or vt.get("name") == new_key):
                raise ValueError(f"数据源 key '{new_key}' 已被占用，请先删除或重命名现有的 '{new_key}' 数据源")

        target_vt["key"] = new_key
        target_vt["name"] = new_key

        # 2. 更新 mapping_detail 中的 name 前缀（如 "T2_user_id" → "T1_user_id"）
        md = target_vt.get("mapping_detail", {})
        if isinstance(md, dict):
            for field_key, field_val in md.items():
                if isinstance(field_val, dict):
                    n = field_val.get("name", "")
                    if n.startswith(f"{old_key}_"):
                        field_val["name"] = f"{new_key}_" + n[len(old_key) + 1:]

        # 3. 使用 JSON 序列化全局替换 ticket 中的引用（最安全的全局替换方式）
        old_prefix = f"{old_key}:"
        new_prefix = f"{new_key}:"
        ticket_json = json.dumps(self.ticket, ensure_ascii=False)
        count = ticket_json.count(f'"{old_prefix}')
        ticket_json = ticket_json.replace(f'"{old_prefix}', f'"{new_prefix}')
        self.ticket = json.loads(ticket_json)

        if count > 0:
            print(f"✅ 数据源 '{old_key}' → '{new_key}'：已更新 {count} 处指标/维度引用")
        else:
            print(f"✅ 数据源 '{old_key}' → '{new_key}'：无需更新引用（指标/维度中未引用该数据源）")

        return count

    def add_group(self, name, **kwargs):
        gc = lambda key, default: _cfg("group", key, default)
        owner_default = self.client.auto_detect_owner()
        if isinstance(owner_default, str) and "," in owner_default:
            owner_list = [o.strip() for o in owner_default.split(",")]
        elif owner_default:
            owner_list = [owner_default]
        else:
            owner_list = []

        ablog_detected = self.client.auto_detect_ablog()

        # 确定 user_id_type 以决定 AbLog SQL 的 user_types 参数
        user_id_type_val = kwargs.get("user_id_type", gc("user_id_type", ["USER_UNIQUE_ID"]))

        ablog_config = kwargs.get("ablog_config")
        if ablog_config is None:
            ab_use_type = _cfg("ablog", "use_type", "custom")
            ab_business_id = ablog_detected.get("business_id", _cfg("ablog", "business_id", ""))
            ab_business_key = ablog_detected.get("business_key", _cfg("ablog", "business_key", ""))
            ab_apps = ablog_detected.get("apps", gc("apps", []))

            # Fetch AB log SQL preview from API if we have the needed config
            # UID 粒度时使用 user_types="USER"，设备维度使用 "USER_UNIQUE_ID"
            ab_log_sql_preview = ""
            if ab_business_id and ab_business_key and ab_apps:
                try:
                    ab_user_types = "USER" if "USER" in user_id_type_val and "USER_UNIQUE_ID" not in user_id_type_val else "USER_UNIQUE_ID"
                    ab_log_result = self.client.get_ab_log_sql(
                        business_id=ab_business_id,
                        business_key=ab_business_key,
                        app_ids=ab_apps,
                        user_types=ab_user_types,
                    )
                    ab_log_data = ab_log_result.get("data") or ab_log_result
                    ab_log_sql_preview = ab_log_data.get("ablog_sql", "")
                except Exception:
                    pass

            ablog_config = {
                "use_type": ab_use_type,
                "business_list": [{
                    "business_id": ab_business_id,
                    "business_key": ab_business_key,
                }],
                "remove_app": _cfg("ablog", "remove_app", "true"),
            }
            if ab_log_sql_preview:
                ablog_config["abLogSqlPreview"] = ab_log_sql_preview
                ablog_config["defaultAbLogSqlPreview"] = ab_log_sql_preview

        detected_apps = ablog_detected.get("apps", gc("apps", self.client.profile.get("apps", [])))

        template = {
            "name": name,
            "name_en": "",
            "user_id_type": user_id_type_val,
            "id_type_scope": kwargs.get("id_type_scope", gc("id_type_scope", "all")),
            "apps": kwargs.get("apps", detected_apps),
            "description": kwargs.get("description", ""),
            "group_type": kwargs.get("group_type", gc("group_type", "action_cuped")),
            "is_cum": kwargs.get("is_cum", gc("is_cum", 1)),
            "cum_start_time": kwargs.get("cum_start_time", gc("cum_start_time", "")),
            "cum_type": kwargs.get("cum_type", gc("cum_type", "ENTER_ONCE_ALWAYS_COUNT")),
            "support_flexible_dim": kwargs.get("support_flexible_dim", gc("support_flexible_dim", 1)),
            "support_flexible_range": kwargs.get("support_flexible_range", gc("support_flexible_range", 1)),
            "dorado_regions": kwargs.get("dorado_regions", gc("dorado_regions", self.client.profile.get("group_dorado_regions", "cn"))),
            "conf": kwargs.get("conf", {}),
            "owner": kwargs.get("owner", owner_list),
            "tag": kwargs.get("tag", []),
            "business_tag_id": kwargs.get("business_tag_id", gc("business_tag_id", self.client.profile.get("group_business_tag_id", 2))),
            "visibility": kwargs.get("visibility", gc("visibility", 3)),
            "ablog_config": ablog_config,
            "m_m2_merge_unique": kwargs.get("m_m2_merge_unique", 0),
            "metrics": kwargs.get("metrics", []),
            "dimensions": kwargs.get("dimensions", []),
        }
        self.ticket.setdefault("groups", []).append(template)
        return template

    def clone_group(self, source_group_name, new_name, vt_name=None):
        source = self._resolve_group(source_group_name)
        return self._do_clone_group(source, new_name, vt_name)

    def clone_group_from(self, source_editor, source_group_name, new_name, vt_name=None, copy_data_sources=False):
        source = source_editor._resolve_group(source_group_name)
        if copy_data_sources:
            existing_keys = {vt.get("key") for vt in self.virtual_table}
            for vt in source_editor.virtual_table:
                if vt.get("key") not in existing_keys:
                    self.virtual_table.append(copy.deepcopy(vt))
        return self._do_clone_group(source, new_name, vt_name)

    def _do_clone_group(self, source, new_name, vt_name=None):
        cloned = copy.deepcopy(source)
        cloned["name"] = new_name
        cloned.pop("id", None)
        cloned.pop("libra_group_id", None)
        cloned.pop("sg_libra_group_id", None)

        if vt_name:
            for metric in cloned.get("metrics", []):
                sql = metric.get("sql", {})
                for side in ("left", "right"):
                    part = sql.get(side, {})
                    if not part:
                        continue
                    if part.get("key"):
                        part["key"] = [self._replace_vt_key(k, vt_name) for k in part["key"]]
                    if part.get("key_sql"):
                        part["key_sql"] = self._replace_vt_key(part["key_sql"], vt_name)
            for dim in cloned.get("dimensions", []):
                if dim.get("key"):
                    dim["key"] = [self._replace_vt_key(k, vt_name) for k in dim["key"]]
                if dim.get("key_sql"):
                    dim["key_sql"] = self._replace_vt_key(dim["key_sql"], vt_name)

        self.ticket.setdefault("groups", []).append(cloned)
        return cloned

    def update_group(self, group_name_or_index, **kwargs):
        result = None
        for group in self._resolve_all_groups(group_name_or_index):
            for k, v in kwargs.items():
                if k == "metrics" or k == "dimensions":
                    continue
                group[k] = v
            if result is None:
                result = group
        return result

    def remove_group(self, group_name_or_index):
        all_groups = self._resolve_all_groups(group_name_or_index)
        groups = self.ticket.get("groups", [])
        removed = None
        for g in all_groups:
            if g in groups:
                groups.remove(g)
                if removed is None:
                    removed = g
        return removed

    def _replace_vt_key(self, ref, new_vt):
        if ":" in ref:
            _, col = ref.split(":", 1)
            return f"{new_vt}:{col}"
        return ref

    def _prepare_for_save(self):
        """构建符合浏览器 PUT 格式的提交数据，剥离服务端只读字段。"""
        TICKET_FIELDS = {"id", "name", "owner", "description", "meego_id", "business", "groups"}
        GROUP_FIELDS = {
            "id", "name", "name_en", "user_id_type", "id_type_scope", "apps",
            "description", "group_type", "libra_group_id", "is_cum", "cum_start_time",
            "cum_type", "support_flexible_dim", "support_flexible_range",
            "dorado_regions", "conf", "owner", "tag", "business_tag_id",
            "visibility", "ablog_config", "m_m2_merge_unique", "metrics", "dimensions",
        }
        METRIC_FIELDS = {"name", "name_en", "description", "sql", "conf"}
        DIMENSION_FIELDS = {
            "name", "name_en", "description", "dim_type", "key", "key_sql",
            "conf", "pub_dim_id", "decc_type",
        }
        COLUMN_FIELDS = {"key", "name", "data_type", "is_pk", "description"}

        clean_vt = []
        for vt in self.virtual_table:
            cvt = {k: v for k, v in vt.items() if k != "columns"}
            cols = vt.get("columns") or []
            cvt["columns"] = [{k: v for k, v in c.items() if k in COLUMN_FIELDS} for c in cols]
            clean_vt.append(cvt)

        clean_ticket = {k: v for k, v in self.ticket.items() if k in TICKET_FIELDS and k != "groups"}
        # 始终使用构造时的原始 ticket_id，上线后 GET 返回的 ticket.id 可能是版本 ticket
        clean_ticket["id"] = self.ticket_id
        if "business" not in clean_ticket:
            biz = self.ticket.get("meego_business")
            if biz:
                clean_ticket["business"] = biz
        clean_groups = []
        for g in self.ticket.get("groups", []):
            cg = {k: v for k, v in g.items() if k in GROUP_FIELDS and k not in ("metrics", "dimensions")}
            cg["metrics"] = [{k: v for k, v in m.items() if k in METRIC_FIELDS} for m in g.get("metrics", [])]
            dims = []
            for d in g.get("dimensions", []):
                cd = {k: v for k, v in d.items() if k in DIMENSION_FIELDS}
                # 引用公共维度的"圈query"维度需要携带 draft_id 和 version_id
                if d.get("pub_dim_id"):
                    cd["draft_id"] = d.get("draft_id") or d.get("pub_dim_id") or ""
                    cd["version_id"] = d.get("version_id") or 0
                dims.append(cd)
            cg["dimensions"] = dims
            clean_groups.append(cg)
        clean_ticket["groups"] = clean_groups

        return clean_vt, clean_ticket

    def save(self, dry_run=False):

        clean_vt, clean_ticket = self._prepare_for_save()

        # 安全检查：防止意外清空指标或维度
        # Gallery 的 PUT 接口是全量替换，如果提交空 metrics/dimensions 会清空服务端数据
        original_groups = (self.original_data or {}).get("ticket", {}).get("groups", [])
        submit_groups = clean_ticket.get("groups", [])
        for i, sg in enumerate(submit_groups):
            og = original_groups[i] if i < len(original_groups) else {}
            orig_metrics_count = len(og.get("metrics", []))
            orig_dims_count = len(og.get("dimensions", []))
            submit_metrics_count = len(sg.get("metrics", []))
            submit_dims_count = len(sg.get("dimensions", []))
            group_name = sg.get("name", f"group[{i}]")

            if orig_metrics_count > 0 and submit_metrics_count == 0:
                raise RuntimeError(
                    f"⛔ 安全中止：指标组 '{group_name}' 原有 {orig_metrics_count} 个指标，"
                    f"当前提交数据中为 0 个。这会清空服务端所有指标！"
                    f"\n如果确实要清空，请先调用 remove_metric() 逐个删除后再 save()。"
                )
            if orig_dims_count > 0 and submit_dims_count == 0:
                raise RuntimeError(
                    f"⛔ 安全中止：指标组 '{group_name}' 原有 {orig_dims_count} 个维度，"
                    f"当前提交数据中为 0 个。这会清空服务端所有维度！"
                    f"\n如果确实要清空，请先调用 remove_dimension() 逐个删除后再 save()。"
                )

        check_result = self.client.save_check(clean_vt, clean_ticket)
        check_data = check_result.get("data") or check_result
        has_errors = False
        if isinstance(check_data, dict):
            errors = check_data.get("errors") or check_data.get("error_list") or []
            if errors:
                has_errors = True
                print(f"❌ 校验发现 {len(errors)} 个问题:")
                for err in errors:
                    print(f"  - {err}")
            else:
                print("✅ 校验通过，无问题")

        if dry_run:
            if has_errors:
                print("Dry run 模式（有校验问题，建议修复后再保存）")
            else:
                print("Dry run 模式，校验通过，可以正式保存")
            return check_result

        if has_errors:
            raise RuntimeError(f"校验未通过，已中止保存。请修复问题后重试，或使用 save(dry_run=True) 查看详情。")

        save_result = self.client.save_ticket(clean_vt, clean_ticket)
        print(f"保存成功 → {gallery_url(self.ticket_id, self.client.env)}")

        # 保存后重新加载，确保本地状态与服务端一致
        try:
            self.load()
        except Exception as e:
            print(f"⚠️  保存成功但重新加载失败: {e}（本地状态可能与服务端不一致，建议重新创建 TicketEditor）")

        return save_result

    def diff(self):
        original_comparable = {
            "virtual_table": self.original_data.get("virtual_table", []),
            "ticket": self.original_data.get("ticket", {}),
        }
        original_str = json.dumps(original_comparable, indent=2, ensure_ascii=False).splitlines()
        current_data = {"virtual_table": self.virtual_table, "ticket": self.ticket}
        current_str = json.dumps(current_data, indent=2, ensure_ascii=False).splitlines()

        diff_lines = difflib.unified_diff(
            original_str, current_str,
            fromfile="原始数据", tofile="当前数据", lineterm=""
        )
        result = "\n".join(diff_lines)
        if not result:
            return "没有变更"
        return result

    def submit_online(self, group_names=None, develop_owner=None, deploy_mode="normal", backfill=False):
        groups = self.ticket.get("groups", [])
        if group_names:
            selected = []
            for name in (group_names if isinstance(group_names, list) else [group_names]):
                g = self.find_group(name)
                if g and g.get("id"):
                    selected.append(g)
                else:
                    raise ValueError(f"指标组 '{name}' 不存在或没有 id（新建的指标组需要先 save）")
        else:
            selected = [g for g in groups if g.get("id")]
        if not selected:
            raise ValueError("没有可上线的指标组（指标组需要先 save 才有 id）")

        group_ids = [g["id"] for g in selected]
        group_names_str = ", ".join(g.get("name", str(g["id"])) for g in selected)

        meego_id = self.ticket.get("meego_id", 0) or 0
        owner = self.client.auto_detect_owner()
        if isinstance(owner, list):
            owner = owner[0] if owner else ""

        print(f"上线检查: {group_names_str} ...")
        check = self.client.online_check(group_ids, deploy_mode=deploy_mode)
        check_data = check.get("data", {})
        if isinstance(check_data, dict) and not check_data.get("is_pass", True):
            msg = check_data.get("message", "")
            raise RuntimeError(f"上线检查未通过: {msg}")
        print("  ✓ 上线检查通过")

        state = self.client.get_ticket_state(self.ticket_id, group_ids=group_ids)
        existing = state.get("data", [])
        if existing:
            raise RuntimeError(f"指标组已有进行中的上线流程 (instance_id={existing[0].get('instance_id')})")

        print("LLM 预检查...")
        self.client.llm_online_prechecks(group_ids, develop_owner=develop_owner or owner,
                                         deploy_mode=deploy_mode, backfill=backfill)
        print("  ✓ LLM 预检查通过")

        print("创建上线状态机...")
        state_result = self.client.create_online_state(
            self.ticket_id, group_ids, creator=owner, develop_owner=develop_owner or owner,
            meego_id=meego_id, deploy_mode=deploy_mode, backfill=backfill,
        )
        state_data = state_result.get("data", [])
        instance_id = None
        if isinstance(state_data, list) and state_data and isinstance(state_data[0], dict):
            instance_id = state_data[0].get("instance_id")
        if not instance_id:
            raise RuntimeError(f"创建状态机失败: {state_result}")
        print(f"  ✓ 状态机实例: {instance_id}")

        print("触发 CREATE_REQUEST 事件...")
        event_result = self.client.trigger_state_event(
            "CREATE_REQUEST", self.ticket_id, group_ids,
            operator=owner, develop_owner=develop_owner or owner,
            meego_id=meego_id, deploy_mode=deploy_mode, backfill=backfill,
        )
        event_data = event_result.get("data", {})
        result_status = event_data.get("result", "UNKNOWN")
        print(f"  ✓ 上线已发起 (status={result_status})")
        print(f"上线流程已启动 → {gallery_url(self.ticket_id, self.client.env)}")
        print(f"后续状态流转请在 Gallery 页面操作或使用 get_online_status() 查看")

        return {
            "instance_id": instance_id,
            "group_ids": group_ids,
            "result": result_status,
            "url": gallery_url(self.ticket_id, self.client.env),
        }

    def cancel_online(self, group_names=None, develop_owner=None, deploy_mode="normal"):
        groups = self.ticket.get("groups", [])
        if group_names:
            selected = []
            for name in (group_names if isinstance(group_names, list) else [group_names]):
                g = self.find_group(name)
                if g and g.get("id"):
                    selected.append(g)
                else:
                    raise ValueError(f"找不到指标组: {name}")
        else:
            selected = [g for g in groups if g.get("id")]
        if not selected:
            raise ValueError("没有可取消上线的指标组（所有指标组均无 id，可能尚未保存）")
        group_ids = [g["id"] for g in selected]
        meego_id = self.ticket.get("meego_id", 0) or 0
        result = self.client.cancel_online(
            self.ticket_id, group_ids,
            develop_owner=develop_owner,
            meego_id=meego_id, deploy_mode=deploy_mode,
        )
        print(f"已取消上线 → {gallery_url(self.ticket_id, self.client.env)}")
        return result

    def get_online_status(self):
        state = self.client.get_ticket_state(self.ticket_id)
        data = state.get("data", [])
        if not data:
            return {"status": "无上线流程", "instances": []}

        instances = []
        for item in data:
            sm = item.get("state_machine", {})
            states = sm.get("states", [])
            current = None
            for s in states:
                if s.get("status") == "WAITING":
                    current = s.get("state")
                    break
                if s.get("status") == "RUNNING":
                    current = s.get("state")
                    break

            config = sm.get("config", [])
            current_name = current
            for c in config:
                if c.get("state") == current:
                    current_name = c.get("name", current)
                    break

            all_finished = all(s.get("status") == "SUCCESS" for s in states)
            instances.append({
                "instance_id": item.get("instance_id"),
                "group_ids": item.get("group_ids", []),
                "current_state": current,
                "current_state_name": current_name,
                "finished": all_finished,
                "states": [{
                    "state": s.get("state"),
                    "status": s.get("status"),
                } for s in states],
            })
        return {"status": "有上线流程", "instances": instances}

    def get_summary(self):
        ticket = self.ticket
        groups = ticket.get("groups", [])
        vt_list = self.virtual_table
        # 始终使用构造时传入的 ticket_id，避免 API 返回的版本 ticket ID 造成混淆
        tid = self.ticket_id

        summary = {
            "ticket_id": tid,
            "ticket_name": ticket.get("name") or f"(未命名需求 {tid})",
            "url": gallery_url(tid, self.client.env),
            "owner": ticket.get("owner", ""),
            "description": ticket.get("description", ""),
            "meego_id": ticket.get("meego_id", ""),
            "virtual_tables": [],
            "groups": [],
        }

        seen_vt_keys = set()
        for vt in vt_list:
            k = vt.get("key", "")
            if k and k in seen_vt_keys:
                continue
            if k:
                seen_vt_keys.add(k)
            mapping = vt.get("mapping_detail") or {}
            cols = mapping.get("columns") or vt.get("columns") or []
            summary["virtual_tables"].append({
                "key": k,
                "name": vt.get("name", ""),
                "column_count": len(cols),
            })

        seen_gids = set()
        for g in groups:
            gid = g.get("id")
            if gid and gid in seen_gids:
                continue
            if gid:
                seen_gids.add(gid)
            summary["groups"].append({
                "id": gid,
                "name": g.get("name", ""),
                "libra_group_id": g.get("libra_group_id"),
                "metrics_count": len(g.get("metrics", [])),
                "dimensions_count": len(g.get("dimensions", [])),
            })

        return summary

    def list_snapshots(self):
        """列出需求的所有版本/快照历史。"""
        result = self.client.get_ticket_history(self.ticket_id)
        data = result.get("data", [])
        if not isinstance(data, list):
            return []
        snapshots = []
        for item in data:
            sid = item.get("snapshot_id")
            if sid is None:
                continue
            entry = {
                "snapshot_id": sid,
                "status": item.get("status", ""),
                "online_status": item.get("online_status", ""),
                "online_time": item.get("online_time", ""),
                "online_operator": item.get("online_operator", ""),
            }
            og = item.get("online_groups", [])
            if og:
                entry["online_groups"] = og
            oc = item.get("online_config") or {}
            if oc.get("group_ids"):
                entry["group_ids"] = oc["group_ids"]
            snapshots.append(entry)
        return snapshots


def _print_table(rows, headers):
    if not rows:
        print("  (空)")
        return
    col_widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        str_row = [str(row.get(h, "")) for h in headers]
        str_rows.append(str_row)
        for i, v in enumerate(str_row):
            col_widths[i] = max(col_widths[i], len(v))

    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for sr in str_rows:
        print(fmt.format(*sr))


def cmd_info(client, ticket_id):
    editor = TicketEditor(client, ticket_id)
    summary = editor.get_summary()
    print(f"Ticket ID: {summary['ticket_id']}")
    print(f"名称: {summary['ticket_name']}")
    print(f"链接: {summary['url']}")
    print(f"负责人: {summary['owner']}")
    print(f"描述: {summary['description']}")
    print(f"Meego ID: {summary['meego_id']}")
    print(f"\n数据源 ({len(summary['virtual_tables'])} 个):")
    for vt in summary["virtual_tables"]:
        print(f"  [{vt['key']}] {vt['name']} ({vt['column_count']} 列)")
    print(f"\n指标组 ({len(summary['groups'])} 个):")
    for g in summary["groups"]:
        print(f"  [{g['id']}] {g['name']} - {g['metrics_count']} 指标, {g['dimensions_count']} 维度")


def cmd_datasources(client, ticket_id):
    editor = TicketEditor(client, ticket_id)
    sources = editor.list_data_sources()
    print(f"Ticket {ticket_id} 的数据源列表:\n")
    for ds in sources:
        print(f"  [{ds['key']}] {ds['name']} ({ds['column_count']} 列)")
        print(f"    列: {', '.join(ds['columns'][:10])}{'...' if len(ds['columns']) > 10 else ''}")
        if ds['sql_preview']:
            print(f"    SQL: {ds['sql_preview']}...")
        print()


def cmd_datasource_sql(client, ticket_id, vt_name):
    editor = TicketEditor(client, ticket_id)
    sql = editor.get_data_source_sql(vt_name)
    print(f"数据源 [{vt_name}] 的 SQL:\n")
    print(sql)


def cmd_groups(client, ticket_id):
    editor = TicketEditor(client, ticket_id)
    groups = editor.list_groups()
    print(f"Ticket {ticket_id} 的指标组列表:\n")
    headers = ["index", "id", "name", "group_type", "metrics_count", "dimensions_count"]
    _print_table(groups, headers)


def cmd_metrics(client, ticket_id, group_name_or_id):
    editor = TicketEditor(client, ticket_id)
    try:
        group_ref = int(group_name_or_id)
    except ValueError:
        group_ref = group_name_or_id
    metrics = editor.list_metrics(group_ref)
    group = editor._resolve_group(group_ref)
    print(f"指标组 [{group.get('name')}] 的指标列表:\n")
    headers = ["index", "name", "description", "left_key_sql", "left_type", "right_key_sql", "right_type"]
    _print_table(metrics, headers)


def cmd_dims(client, ticket_id, group_name_or_id):
    editor = TicketEditor(client, ticket_id)
    try:
        group_ref = int(group_name_or_id)
    except ValueError:
        group_ref = group_name_or_id
    dims = editor.list_dimensions(group_ref)
    group = editor._resolve_group(group_ref)
    print(f"指标组 [{group.get('name')}] 的维度列表:\n")
    headers = ["index", "name", "description", "dim_type", "key", "use_conf"]
    _print_table(dims, headers)
    advanced_dims = [d for d in dims if d.get("use_conf")]
    if advanced_dims:
        print(f"\n高级配置详情:")
        for d in advanced_dims:
            parts = [f"use_types={d.get('use_types', '')}", f"update_type={d.get('update_type', '')}", f"enums_update_type={d.get('enums_update_type', '')}"]
            if d.get("enabled_options"):
                parts.append(f"enabled: {', '.join(d['enabled_options'])}")
            print(f"  {d['name']}: {', '.join(parts)}")


def cmd_save(client, ticket_id):
    editor = TicketEditor(client, ticket_id)
    print("当前变更差异:")
    print(editor.diff())
    print()
    editor.save(dry_run=False)


def cmd_history(client, ticket_id):
    editor = TicketEditor(client, ticket_id)
    snapshots = editor.list_snapshots()
    print(f"Ticket {ticket_id} 的版本历史 (共 {len(snapshots)} 个):\n")
    headers = ["snapshot_id", "status", "online_status", "online_time", "online_operator"]
    _print_table(snapshots, headers)


def cmd_snapshot_info(client, ticket_id, snapshot_id):
    editor = TicketEditor(client, ticket_id, snapshot_id=int(snapshot_id))
    summary = editor.get_summary()
    print(f"Ticket {ticket_id} 版本 {snapshot_id} 的概要:\n")
    print(f"名称: {summary['ticket_name']}")
    print(f"负责人: {summary['owner']}")
    print(f"\n数据源 ({len(summary['virtual_tables'])} 个):")
    for vt in summary["virtual_tables"]:
        print(f"  [{vt['key']}] {vt['name']} ({vt['column_count']} 列)")
    print(f"\n指标组 ({len(summary['groups'])} 个):")
    for g in summary["groups"]:
        print(f"  [{g['id']}] {g['name']} - {g['metrics_count']} 指标, {g['dimensions_count']} 维度")


def cmd_snapshot_groups(client, ticket_id, snapshot_id):
    editor = TicketEditor(client, ticket_id, snapshot_id=int(snapshot_id))
    groups = editor.list_groups()
    print(f"Ticket {ticket_id} 版本 {snapshot_id} 的指标组列表:\n")
    headers = ["index", "id", "name", "group_type", "metrics_count", "dimensions_count"]
    _print_table(groups, headers)


def cmd_list_groups(client, owner=None, status=None):
    groups = client.list_all_groups(owner=owner, status=status)
    if not owner:
        owner = client.auto_detect_owner()
    print(f"{'=' * 60}")
    print(f"  {owner} 的所有指标组 (共 {len(groups)} 个)")
    print(f"{'=' * 60}\n")
    if not groups:
        print("  (无指标组)")
        return

    # 按需求分组展示
    ticket_groups = {}
    for g in groups:
        tid = g["ticket_id"]
        if tid not in ticket_groups:
            ticket_groups[tid] = {"ticket_name": g["ticket_name"], "ticket_status": g["ticket_status"], "groups": []}
        ticket_groups[tid]["groups"].append(g)

    for tid, info in ticket_groups.items():
        print(f"📋 [{tid}] {info['ticket_name']}  (status={info['ticket_status']})")
        print(f"   链接: {gallery_url(tid, client.env)}")
        for g in info["groups"]:
            status_icon = "🟢" if g["develop_status"] == "ONLINE" else "⚪"
            print(f"   {status_icon} [{g['group_id']}] {g['group_name']}")
            print(f"      libra_group_id={g['libra_group_id']}  status={g['develop_status']}  "
                  f"metrics={g['metrics_count']}  dims={g['dimensions_count']}")
            if g['cum_start_time']:
                print(f"      cum_start={g['cum_start_time']}  dorado={g['dorado_regions']}  apps={g['apps']}")
        print()


def cmd_list_tickets(client, owner=None):
    result = client.list_tickets(owner=owner)
    data = result.get("data", {})
    tickets = data.get("tickets", [])
    total = data.get("total", 0)
    print(f"需求列表 (共 {total} 个):\n")
    for t in tickets:
        status = t.get("status", "")
        draft = " [草稿]" if t.get("is_draft") else ""
        tid = t.get('id')
        print(f"  [{tid}] {t.get('name', '')}{draft}  status={status}")
        print(f"    负责人: {t.get('owner', [])}")
        print(f"    链接: {gallery_url(tid, client.env)}")
        print()


def main():
    env = "cn"
    args = list(sys.argv[1:])
    for i, a in enumerate(args):
        if a == "--env" and i + 1 < len(args):
            env = args[i + 1]
            args = args[:i] + args[i + 2:]
            break
        if a.startswith("--env="):
            env = a.split("=", 1)[1]
            args = args[:i] + args[i + 1:]
            break

    if not args:
        print("用法:")
        print(f"  python {sys.argv[0]} [--env cn|i18n] list-tickets [owner]")
        print(f"  python {sys.argv[0]} [--env cn|i18n] list-groups [owner] [--status ONLINE|OFFLINE]")
        print(f"  python {sys.argv[0]} [--env cn|i18n] info <ticket_id_or_url>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] groups <ticket_id_or_url>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] metrics <ticket_id_or_url> <group_name_or_id>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] dims <ticket_id_or_url> <group_name_or_id>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] datasources <ticket_id_or_url>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] datasource-sql <ticket_id_or_url> <vt_name>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] save <ticket_id_or_url>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] history <ticket_id_or_url>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] snapshot-info <ticket_id_or_url> <snapshot_id>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] snapshot-groups <ticket_id_or_url> <snapshot_id>")
        print(f"  python {sys.argv[0]} [--env cn|i18n] detect")
        print()
        print("ticket_id_or_url 可以是数字 ID 或完整 URL，如:")
        print("  65562")
        print("  https://libra-gallery.bytedance.net/#/metric/set/detail/65562")
        print("  https://libra-gallery-us.tiktok-row.net/#/metric/set/detail/37561")
        print()
        print("传入海外 URL 时会自动检测 env，无需手动指定 --env")
        sys.exit(1)

    command = args[0]

    if len(args) >= 2 and command not in ("list-tickets", "list-groups", "detect"):
        detected = detect_env_from_url(args[1])
        if detected != "cn":
            env = detected

    client = LibraGalleryClient(env=env)

    try:
        if command == "list-tickets":
            owner = args[1] if len(args) > 1 else None
            cmd_list_tickets(client, owner)
            return

        if command == "list-groups":
            owner = None
            status = None
            remaining = args[1:]
            i = 0
            while i < len(remaining):
                if remaining[i] == "--status" and i + 1 < len(remaining):
                    status = remaining[i + 1]
                    i += 2
                elif not remaining[i].startswith("--"):
                    owner = remaining[i]
                    i += 1
                else:
                    i += 1
            cmd_list_groups(client, owner, status)
            return

        if command == "detect":
            print(f"\n--- 自动探测配置 (env={env}) ---")
            owner = client.auto_detect_owner()
            print(f"owner:        {owner or '(未能获取)'}")
            business = client.auto_detect_business()
            print(f"business:     {business or '(未能获取)'}")
            ablog = client.auto_detect_ablog()
            if ablog:
                print(f"business_id:  {ablog.get('business_id', '(未能获取)')}")
                print(f"business_key: {ablog.get('business_key', '(未能获取)')}")
                print(f"apps:         {ablog.get('apps', '(未能获取)')}")
            else:
                print("business_id:  (未能获取)")
                print("business_key: (未能获取)")
                print("apps:         (未能获取)")
            try:
                apps_result = client.get_apps()
                apps = apps_result.get("data", [])
                app_names = [f"{a.get('id')}({a.get('name','')})" for a in apps[:10]] if isinstance(apps, list) else []
                print(f"\n可用 apps:    {', '.join(app_names) if app_names else '(无)'}")
            except Exception:
                print("\n可用 apps:    (查询失败)")
            try:
                biz_result = client.get_quick_query_business(owner)
                biz_list = biz_result.get("data", [])
                if isinstance(biz_list, list) and biz_list:
                    print("关联业务:")
                    for b in biz_list[:5]:
                        bid = b.get("id") or b.get("business_id", "")
                        bname = b.get("name") or b.get("business_name", "")
                        print(f"  [{bid}] {bname}")
                else:
                    print("关联业务:    (无)")
            except Exception:
                print("关联业务:    (查询失败)")
            print(f"\n配置文件: {_SCRIPT_DIR / 'config.yaml'}")
            print("提示: 以上探测到的值会在创建需求、添加指标组时自动使用（若 config.yaml 中未配置）")
            return

        if len(args) < 2:
            print(f"错误: '{command}' 命令需要提供 ticket_id_or_url 参数")
            sys.exit(1)

        ticket_id = extract_ticket_id(args[1])

        if command == "info":
            cmd_info(client, ticket_id)
        elif command == "groups":
            cmd_groups(client, ticket_id)
        elif command == "metrics":
            if len(args) < 3:
                print("错误: metrics 命令需要提供 group_name_or_id 参数")
                sys.exit(1)
            cmd_metrics(client, ticket_id, args[2])
        elif command == "dims":
            if len(args) < 3:
                print("错误: dims 命令需要提供 group_name_or_id 参数")
                sys.exit(1)
            cmd_dims(client, ticket_id, args[2])
        elif command == "datasources":
            cmd_datasources(client, ticket_id)
        elif command == "datasource-sql":
            if len(args) < 3:
                print("错误: datasource-sql 命令需要提供 vt_name 参数 (如 T1)")
                sys.exit(1)
            cmd_datasource_sql(client, ticket_id, args[2])
        elif command == "save":
            cmd_save(client, ticket_id)
        elif command == "history":
            cmd_history(client, ticket_id)
        elif command == "snapshot-info":
            if len(args) < 3:
                print("错误: snapshot-info 命令需要提供 snapshot_id 参数")
                sys.exit(1)
            cmd_snapshot_info(client, ticket_id, args[2])
        elif command == "snapshot-groups":
            if len(args) < 3:
                print("错误: snapshot-groups 命令需要提供 snapshot_id 参数")
                sys.exit(1)
            cmd_snapshot_groups(client, ticket_id, args[2])
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
