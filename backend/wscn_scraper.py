import time
import json
import random
import httpx
import asyncio
from datetime import datetime, timezone, timedelta

# Beijing Timezone
BEIJING_TZ = timezone(timedelta(hours=8))

API_URL = "https://api-one.wallstcn.com/apiv1/content/lives"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def normalize_item(item):
    """Convert WSCN item to unified schema."""
    original_id = item.get('id')
    
    # Handle timestamp
    # 'display_time' is usually seconds timestamp
    display_time = item.get('display_time', 0)
    dt = datetime.fromtimestamp(display_time, BEIJING_TZ)
    pub_date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # is_red logic: importance >= 2 or score >= 2 or specific style flags
    is_red = False
    importance = item.get('importance', 1)
    score = item.get('score', 0)
    if (importance >= 2 or 
        score >= 2 or
        item.get('is_red') is True or 
        item.get('display_style') == 'important'):
        is_red = True
        
    title = item.get('title')
    content = item.get('content_text', "")
    if not title:
        title = content[:30] + "..." if content else "No Title"
        
    return {
        "id": f"wscn_{original_id}",
        "source": "wscn",
        "title": title,
        "content": content,
        "pub_date": pub_date_str,
        "is_red": is_red,
        "url": item.get('uri') or "" 
    }

async def fetch_news_page(client: httpx.AsyncClient, cursor: str = None):
    params = {
        "channel": "global-channel",
        "client": "pc",
        "limit": 20
    }
    if cursor:
        params["cursor"] = cursor
        
    try:
        response = await client.get(API_URL, params=params, headers=HEADERS, timeout=2.5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[华尔街见闻(WSCN)] 请求异常: {e}")
        return None

async def get_latest_news(limit: int = 20):
    """Fetch the latest page of news."""
    print("开始抓取 [华尔街见闻(WSCN)]...")
    async with httpx.AsyncClient(trust_env=False, timeout=4.0) as client:
        data = await fetch_news_page(client, cursor=None)
        if data and 'data' in data and 'items' in data['data']:
            items = data['data']['items']
            items = [normalize_item(item) for item in items[:limit]]
            print(f"[华尔街见闻(WSCN)] 成功获取 {len(items)} 条数据")
            return items
    print("[华尔街见闻(WSCN)] 抓取失败或无数据")
    return []

async def get_history_news_generator(hours: int = 4):
    seen_ids = set()
    current_cursor = None
    
    now_ts = int(time.time())
    start_time_limit = now_ts - (hours * 3600)
    print(f"---- [WSCN] Target Cutoff: {datetime.fromtimestamp(start_time_limit, BEIJING_TZ)} ----")
    
    page_index = 0
    
    async with httpx.AsyncClient(trust_env=False, timeout=4.0) as client:
        while True:
            page_index += 1
            yield json.dumps({
                "type": "progress", 
                "status": "requesting", 
                "page": page_index,
                "cursor": current_cursor or "Latest"
            }) + "\n"
            
            data = await fetch_news_page(client, current_cursor)
            
            if not data or 'data' not in data or 'items' not in data['data']:
                print(f">>>> [WSCN] API response error on page {page_index}")
                yield json.dumps({"type": "error", "message": "WSCN API Error or End"}) + "\n"
                break
                
            items = data['data']['items']
            if not items:
                print(f">>>> [WSCN] No items returned on page {page_index}")
                yield json.dumps({"type": "progress", "status": "finished", "message": "No more data"}) + "\n"
                break
            
            print(f">>>> [WSCN] Page {page_index}: fetched {len(items)} items")
            
            items_to_yield = []
            reached_limit = False
            
            for item in items:
                item_id = item.get('id')
                display_time = item.get('display_time', 0)
                
                if display_time < start_time_limit:
                    reached_limit = True
                    break
                    
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    items_to_yield.append(normalize_item(item))
            
            if items_to_yield:
                yield json.dumps({"type": "data", "items": items_to_yield}) + "\n"
            
            if reached_limit:
                print(">>>> [WSCN] Reached time limit")
                break
                
            last_item = items[-1]
            last_cursor_val = last_item.get('display_time') or last_item.get('score')
            
            if not last_cursor_val:
                print("!!!! [WSCN Warning] No valid cursor found in last item, stopping !!!!")
                break

            if current_cursor and str(last_cursor_val) == str(current_cursor):
                 print("!!!! [WSCN Warning] Cursor did not move, stopping !!!!")
                 break
                 
            current_cursor = str(last_cursor_val)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        yield json.dumps({"type": "done"}) + "\n"
