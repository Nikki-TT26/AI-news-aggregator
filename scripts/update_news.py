import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# API Keys from environment variables
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
VOLC_API_KEY = os.environ.get("VOLC_API_KEY")
# 替换为你的豆包模型 Endpoint ID
VOLC_ENDPOINT_ID = os.environ.get("VOLC_ENDPOINT_ID", "ep-xxxxxxxx-xxx")

def search_news():
    """使用 Tavily 搜索最新 AI 资讯"""
    if not TAVILY_API_KEY:
        raise ValueError("缺少 TAVILY_API_KEY")
        
    print("[1/3] 正在使用 Tavily 搜索新闻...")
    url = "https://api.tavily.com/search"
    
    # 构建搜索请求
    data = {
        "api_key": TAVILY_API_KEY,
        "query": "最新 人工智能 AI 产品 技术 投融资 创业 消息",
        "search_depth": "basic",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": 10,
        "days": 1 # 只搜最近一天的
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("results", [])
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def process_with_llm(news_items):
    """调用火山引擎豆包模型进行内容提炼"""
    if not VOLC_API_KEY:
        raise ValueError("缺少 VOLC_API_KEY")
        
    print("[2/3] 正在调用豆包大模型提炼内容...")
    url = "https://ark.volces.com/api/v3/chat/completions"
    
    # 构造给 LLM 的输入数据
    raw_text = json.dumps(news_items, ensure_ascii=False)
    
    prompt = f"""
请扮演专业的 AI 行业分析师，阅读以下搜索到的最新新闻片段。
任务：
1. 去重并合并相似新闻。
2. 提取出最重要的新闻（最多保留 5 条）。
3. 按照指定的 JSON 数组格式输出。

输出格式要求，必须是合法的 JSON 数组，每个元素包含：
- id: 字符串（唯一标识）
- title: 字符串（精炼的标题）
- summary: 字符串（1-2句核心摘要）
- highlights: 字符串数组（2-3个重点事实，短句）
- url: 字符串（原文链接，必须从输入中选取）
- source: 字符串（如 36氪、TechCrunch等）
- category: 字符串（必须从以下中选择一个：模型发布、产品进展、投并购、前沿理论、其他）
- importance: 数字（1-5分，5为最重大）
- publishedAt: 字符串（ISO格式时间，如 2026-08-25T10:30:00Z）

输入新闻数据：
{raw_text}

请只返回 JSON 数组，不要返回任何 markdown 标记（如 ```json）或多余的文字。
"""
    
    data = {
        "model": VOLC_ENDPOINT_ID,
        "messages": [
            {"role": "system", "content": "你是一个只输出 JSON 数组的专业数据处理程序。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {VOLC_API_KEY}'
        }
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result["choices"][0]["message"]["content"].strip()
            # 简单清理可能残留的 markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content)
    except Exception as e:
        print(f"LLM 处理失败: {e}")
        return []

def main():
    print("=== 开始更新 AI 资讯 ===")
    # 1. 搜索
    raw_news = search_news()
    if not raw_news:
        print("未搜索到新闻，退出。")
        return
        
    # 2. LLM 提炼
    processed_news = process_with_llm(raw_news)
    
    if not processed_news:
        print("提炼结果为空，退出。")
        return
        
    # 3. 写入文件
    print("[3/3] 正在更新 data/news.json...")
    
    output_data = {
        "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": processed_news,
        "today": processed_news, # 演示简化：today等于latest
        "week": [],
        "month": []
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print("=== 更新完成 ===")

if __name__ == "__main__":
    main()
