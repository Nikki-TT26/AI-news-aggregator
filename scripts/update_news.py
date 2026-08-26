import os
import sys
import json
import re
import html as html_module
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, quote

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
VOLC_API_KEY = os.environ.get("VOLC_API_KEY")
VOLC_ENDPOINT_ID = os.environ.get("VOLC_ENDPOINT_ID")

DATA_FILE = "data/news.json"

SEARCH_QUERIES = [
    "AI 大模型 发布 最新",
    "AI 芯片 GPU 自研 算力 最新",
    "AI Agent 智能体 产品 发布 上线",
    "人工智能 融资 并购 IPO 投资",
    "具身智能 人形机器人 自动驾驶 最新",
    "AI 前沿研究 突破 论文",
    "OpenAI Anthropic Google AI chip model latest",
    "AI startup funding acquisition 2026",
]

WECHAT_QUERIES = [
    "AI 大模型 最新消息",
    "AI 芯片 英伟达 OpenAI",
    "AI Agent 智能体 产品",
    "人工智能 融资 并购",
    "具身智能 机器人 自动驾驶",
]

SOGOU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CATEGORIES = ["模型发布", "芯片硬件", "产品进展", "投并购", "具身智能", "前沿理论", "行业话题", "其他"]

CATEGORY_KEYWORDS = {
    "芯片硬件": ["芯片", "gpu", "cpu", "npu", "tpu", "算力", "自研芯片", "chip", "nvidia", "英伟达", "半导体", "晶圆", "台积电", "sambanova", "groq", "cerebras", "jalapeño", "blackwell", "gb200", "gb300", "光互连", "光模块"],
    "具身智能": ["具身", "机器人", "robot", "humanoid", "人形", "自动驾驶", "autonomous", "无人车", "机械臂", "宇树", "梅卡曼德", "figure", "tesla optimus", "灵巧手"],
    "模型发布": ["发布", "推出", "release", "launch", "model", "大模型", "gpt", "claude", "gemini", "llama", "豆包", "deepseek", "开源模型", "nemotron", "ssi", "ilya", "kimi", "通义", "文心"],
    "投并购": ["融资", "并购", "收购", "投资", "funding", "acquisition", "investment", "raise", "估值", "上市", "ipo", "轮", "招股", "基石"],
    "前沿理论": ["研究", "论文", "paper", "research", "突破", "理论", "theory", "arxiv", "科学家", "发现", "agi", "对齐", "scaling"],
    "产品进展": ["产品", "上线", "功能", "更新", "product", "feature", "上新", "app", "应用", "工具", "agent", "智能体", "飞书", "扣子", "coze", "工作", "公众号", "小程序"],
    "行业话题": ["政策", "法规", "监管", "伦理", "安全", "争议", "趋势", "报告", "白皮书", "标准", "合作", "联盟", "开源社区"],
}


def tavily_search(query, days=2, max_results=10):
    url = "https://api.tavily.com/search"
    data = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "topic": "news",
        "search_depth": "basic",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": max_results,
        "days": days,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("results", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"  [WARN] Tavily 搜索失败 ({query}): HTTP {e.code} - {body}")
        return []
    except Exception as e:
        print(f"  [WARN] Tavily 搜索失败 ({query}): {e}")
        return []


def sogou_wechat_search(query, max_results=8):
    search_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(query)}&ie=utf8"
    req = urllib.request.Request(search_url, headers=SOGOU_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] 搜狗微信请求失败 ({query}): {e}")
        return []

    if "antispider" in html or "请输入验证码" in html or "验证码" in html:
        print(f"  [WARN] 搜狗微信触发验证码，跳过 ({query})")
        return []

    results = []
    blocks = re.findall(r'<div class="txt-box">(.*?)</div>\s*(?:</div>|<div class="s-pd")', html, re.DOTALL)
    if not blocks:
        blocks = re.findall(r'<div class="txt-box">(.*?)(?=<div class="txt-box">|<div id="pagebar")', html, re.DOTALL)

    for block in blocks[:max_results]:
        title_match = re.search(r'<h3>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not title_match:
            continue
        raw_url = title_match.group(1)
        title = html_module.unescape(re.sub(r"<[^>]+>", "", title_match.group(2)).strip())

        if raw_url.startswith("/link?"):
            article_url = "https://weixin.sogou.com" + raw_url
        elif raw_url.startswith("http"):
            article_url = raw_url
        else:
            continue

        summary_match = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', block, re.DOTALL)
        summary = ""
        if summary_match:
            summary = html_module.unescape(re.sub(r"<[^>]+>", "", summary_match.group(1)).strip())

        account_match = re.search(r'class="account"[^>]*>(.*?)</a>', block, re.DOTALL)
        account = ""
        if account_match:
            account = html_module.unescape(re.sub(r"<[^>]+>", "", account_match.group(1)).strip())

        date_match = re.search(r"timeConvert\('(\d+)'\)", block)
        pub_date = ""
        if date_match:
            try:
                ts = int(date_match.group(1))
                pub_date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
            except Exception:
                pass

        source_name = f"微信公众号·{account}" if account else "微信公众号"
        results.append({
            "title": title,
            "url": article_url,
            "content": summary,
            "published_date": pub_date,
            "source": source_name,
            "_is_wechat": True,
        })
    return results


def collect_all_news(days=2):
    print(f"[1/4] 正在搜索最近 {days} 天的 AI 资讯...")
    all_results = []
    seen_urls = set()

    print(f"  --- Tavily 搜索 ({len(SEARCH_QUERIES)} 个 query) ---")
    for q in SEARCH_QUERIES:
        results = tavily_search(q, days=days, max_results=10)
        for r in results:
            u = r.get("url", "")
            if u and u not in seen_urls:
                seen_urls.add(u)
                all_results.append(r)
        print(f"  完成 Tavily query: {q} -> 累计 {len(all_results)} 条")

    print(f"  --- 搜狗微信搜索 ({len(WECHAT_QUERIES)} 个 query) ---")
    for q in WECHAT_QUERIES:
        results = sogou_wechat_search(q, max_results=8)
        for r in results:
            u = r.get("url", "")
            if u and u not in seen_urls:
                seen_urls.add(u)
                all_results.append(r)
        print(f"  完成微信 query: {q} -> 累计 {len(all_results)} 条")

    print(f"  搜索完成，共 {len(all_results)} 条去重结果")
    return all_results


def guess_category(title, content):
    text = (title + " " + content).lower()
    best_cat = "行业话题"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def guess_importance(title, content):
    text = (title + " " + content).lower()
    high_signals = [
        "重大", "突破", "首次", "发布", "融资", "收购", "ipo", "上市", "billion", "亿",
        "launch", "release", "gpt", "claude", "openai", "anthropic", "google", "nvidia",
        "英伟达", "芯片", "chip", "gpu", "自研", "104倍", "超越", "beat", "outperform",
        "机器人", "humanoid", "自动驾驶", "agent", "智能体", "开源", "open source",
        "ilya", "sutskever", "ssi", "jalapeño", "nemotron",
    ]
    score = sum(1 for s in high_signals if s in text)
    if score >= 5:
        return 5
    if score >= 3:
        return 4
    if score >= 2:
        return 3
    return 2


def process_raw_fallback(raw_results):
    print("  [FALLBACK] LLM 不可用，使用规则化方式处理搜索结果...")
    processed = []
    for r in raw_results:
        url = r.get("url", "")
        if not url or "example.com" in url:
            continue
        title = r.get("title", "").strip()
        content = (r.get("content", "") or "").strip()
        if not title:
            continue
        summary = content[:200] + ("..." if len(content) > 200 else "")
        sentences = re.split(r'[。！？\n]', content)
        highlights = [s.strip() for s in sentences if len(s.strip()) > 10][:3]
        if not highlights:
            highlights = [summary[:80]]
        pub_date = r.get("published_date", "")
        if not pub_date:
            pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            try:
                dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
        source = r.get("source", "") or extract_source(url)
        processed.append({
            "id": hashlib.md5(url.encode()).hexdigest()[:12],
            "title": title,
            "summary": summary,
            "highlights": highlights,
            "url": url,
            "source": source,
            "category": guess_category(title, content),
            "importance": guess_importance(title, content),
            "publishedAt": pub_date,
        })
    print(f"  [FALLBACK] 规则化处理完成，有效新闻 {len(processed)} 条")
    return processed


def call_llm(prompt):
    url = "https://ark.volces.com/api/v3/chat/completions"
    data = {
        "model": VOLC_ENDPOINT_ID,
        "messages": [
            {"role": "system", "content": "你是一个只输出合法 JSON 的专业数据处理程序，不要输出任何 markdown 标记或多余文字。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VOLC_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:800]
        print(f"  [ERROR] 火山 API HTTP {e.code}: {body}")
        raise
    except Exception as e:
        print(f"  [ERROR] 火山 API 调用失败: {type(e).__name__}: {e}")
        raise


def process_with_llm(raw_results):
    print(f"[2/4] 正在调用豆包大模型提炼 {len(raw_results)} 条资讯...")
    indexed = []
    for i, r in enumerate(raw_results):
        indexed.append({
            "index": i,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": (r.get("content", "") or "")[:600],
            "published_date": r.get("published_date", ""),
        })

    url_map = {i: r.get("url", "") for i, r in enumerate(raw_results)}
    source_map = {i: (r.get("source", "") or extract_source(r.get("url", ""))) for i, r in enumerate(raw_results)}
    date_map = {i: r.get("published_date", "") for i, r in enumerate(raw_results)}

    prompt = f"""
你是一位资深 AI 行业分析师。请阅读以下带编号的搜索结果，完成以下任务：

1. 筛选出真正有价值的 AI 行业新闻（剔除无关内容、广告、纯导航页）。
2. 对相似/重复新闻进行合并，只保留信息最完整的一条。
3. 为每条新闻提炼核心摘要和重点。
4. 给出分类和重要性评分。

输出要求：返回一个 JSON 数组，每个元素包含：
- "index": 数字，对应输入中的编号（必须是输入中真实存在的编号，不要编造）
- "title": 字符串，精炼的中文标题（如果原文是英文，翻译成中文）
- "summary": 字符串，1-2句中文核心摘要
- "highlights": 字符串数组，2-3个重点事实（中文短句）
- "category": 字符串，必须从以下中选一个：{json.dumps(CATEGORIES, ensure_ascii=False)}
- "importance": 数字，1-5分（5=行业级重大新闻，4=重要进展，3=值得关注，2=一般动态，1=边缘信息）

注意：
- index 必须来自输入数据，不要编造编号。
- 不要输出 url 字段，url 由程序根据 index 自动映射。
- 至少返回 8 条有价值的新闻，如果搜索结果质量够高最多返回 20 条。
- 只返回 JSON 数组本身。

输入数据：
{json.dumps(indexed, ensure_ascii=False, indent=2)}
"""
    try:
        content = call_llm(prompt)
        items = json.loads(content)
    except Exception as e:
        print(f"  [WARN] LLM 调用或解析失败，将使用降级方案: {e}")
        return None

    processed = []
    for item in items:
        idx = item.get("index")
        if idx not in url_map:
            print(f"  [WARN] LLM 返回了无效 index: {idx}，跳过")
            continue
        real_url = url_map[idx]
        if not real_url or "example.com" in real_url:
            continue
        pub_date = date_map.get(idx, "")
        if not pub_date:
            pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            try:
                dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
        processed.append({
            "id": hashlib.md5(real_url.encode()).hexdigest()[:12],
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "highlights": item.get("highlights", []),
            "url": real_url,
            "source": source_map.get(idx, ""),
            "category": item.get("category", "其他"),
            "importance": item.get("importance", 3),
            "publishedAt": pub_date,
        })
    print(f"  LLM 提炼完成，有效新闻 {len(processed)} 条")
    return processed


def extract_source(url):
    try:
        host = urlparse(url).netloc
        return host.replace("www.", "")
    except Exception:
        return ""


def load_existing():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"latest": [], "today": [], "week": [], "month": []}


def parse_date(s):
    try:
        s = s.replace("Z", "+00:00")
        if "+" not in s and "T" in s:
            s += "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now(timezone.utc)


def classify_by_time(items):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    latest = []
    today = []
    week = []
    month = []

    for item in items:
        pub = parse_date(item.get("publishedAt", ""))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub >= now - timedelta(hours=48):
            latest.append(item)
        if pub >= today_start:
            today.append(item)
        if pub >= week_start:
            week.append(item)
        if pub >= month_start:
            month.append(item)

    latest.sort(key=lambda x: x.get("importance", 0), reverse=True)
    today.sort(key=lambda x: x.get("importance", 0), reverse=True)
    week.sort(key=lambda x: x.get("importance", 0), reverse=True)
    month.sort(key=lambda x: x.get("importance", 0), reverse=True)

    week = week[:15]
    month = month[:10]

    return latest, today, week, month


def deduplicate(items):
    seen = set()
    result = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
    return result


def main():
    print("=== 开始更新 AI 资讯 ===")
    if not TAVILY_API_KEY:
        print("[ERROR] 缺少 TAVILY_API_KEY")
        sys.exit(1)

    raw_results = collect_all_news(days=2)
    if not raw_results:
        print("[ERROR] 未搜索到任何结果，请检查 Tavily API Key 和网络连接。")
        sys.exit(1)

    if VOLC_API_KEY and VOLC_ENDPOINT_ID:
        new_items = process_with_llm(raw_results)
        if new_items is None or len(new_items) == 0:
            print("  [WARN] LLM 处理失败或无结果，降级到规则化处理...")
            new_items = process_raw_fallback(raw_results)
    else:
        print("[WARN] 未配置 VOLC_API_KEY 或 VOLC_ENDPOINT_ID，使用规则化处理...")
        new_items = process_raw_fallback(raw_results)

    if not new_items:
        print("[ERROR] 未能生成任何新闻数据。")
        sys.exit(1)

    print("[3/4] 合并历史数据并去重...")
    existing = load_existing()
    all_items = existing.get("latest", []) + existing.get("today", []) + \
                existing.get("week", []) + existing.get("month", []) + new_items
    all_items = deduplicate(all_items)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=35)
    all_items = [
        item for item in all_items
        if parse_date(item.get("publishedAt", "")) >= cutoff
    ]
    print(f"  合并后共 {len(all_items)} 条有效新闻")

    latest, today, week, month = classify_by_time(all_items)

    if len(week) < 5 or len(month) < 5:
        print("  [BACKFILL] 周/月数据不足，执行历史回溯搜索...")
        backfill_results = collect_all_news(days=30)
        if VOLC_API_KEY and VOLC_ENDPOINT_ID:
            backfill_items = process_with_llm(backfill_results)
            if backfill_items is None or len(backfill_items) == 0:
                backfill_items = process_raw_fallback(backfill_results)
        else:
            backfill_items = process_raw_fallback(backfill_results)
        all_items = deduplicate(all_items + backfill_items)
        all_items = [
            item for item in all_items
            if parse_date(item.get("publishedAt", "")) >= cutoff
        ]
        latest, today, week, month = classify_by_time(all_items)

    print("[4/4] 写入 data/news.json...")
    output = {
        "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": latest[:30],
        "today": today,
        "week": week,
        "month": month,
    }
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== 更新完成 ===")
    print(f"  最新: {len(output['latest'])} 条")
    print(f"  今日: {len(output['today'])} 条")
    print(f"  本周: {len(output['week'])} 条")
    print(f"  本月: {len(output['month'])} 条")


if __name__ == "__main__":
    main()
