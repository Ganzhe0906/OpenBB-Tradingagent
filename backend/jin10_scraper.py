import time
import json
import random
import httpx
import asyncio
import re
from datetime import datetime, timezone, timedelta

# Beijing Timezone
BEIJING_TZ = timezone(timedelta(hours=8))

API_URL = "https://flash-api.jin10.com/get_flash_list"
HEADERS = {
    "x-app-id": "bVBF4FyRTn5NJF5n",
    "x-version": "1.0.0",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.jin10.com",
    "Referer": "https://www.jin10.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def clean_html(text):
    """Remove HTML tags from string using regex."""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()

def generate_title(content):
    """Generate title by taking first 40 characters."""
    if not content:
        return "无标题"
    text = clean_html(content)
    match = re.search(r'【(.*?)】', text)
    if match:
        return match.group(1)
    return text[:40].strip() + ("..." if len(text) > 40 else "")

def normalize_item(item):
    """Convert Jin10 item to unified schema."""
    original_id = item.get('id')
    data_payload = item.get('data', {})
    
    if isinstance(data_payload, str):
        raw_content = data_payload
        pic = ""
    else:
        raw_content = data_payload.get('content', "")
        pic = data_payload.get('pic', "")
        
    content = clean_html(raw_content)
    
    return {
        "id": f"jin10_{original_id}",
        "source": "jin10",
        "title": generate_title(raw_content),
        "content": content,
        "pub_date": item.get('time', ""),
        "is_red": item.get('important') == 1,
        "url": f"https://flash.jin10.com/detail/{original_id}",
        "pic": pic
    }

async def fetch_news_page(client: httpx.AsyncClient, max_time: str = None):
    """Core fetch function with multi-path probe and required headers."""
    target_channels = ["-2", "1"]
    
    for channel in target_channels:
        params = {
            "channel": channel,
            "vip": "1",
            "source": "web",
            "category": "quotation",
            "_": int(time.time() * 1000)
        }
        if max_time:
            params["max_time"] = max_time
            
        try:
            print(f">>>> [Jin10] Requesting channel {channel} (max_time={max_time})...")
            response = await client.get(API_URL, params=params, headers=HEADERS, timeout=2.5)
            
            if response.status_code != 200:
                print(f">>>> [Jin10 Debug] HTTP {response.status_code}: {response.text[:200]}")
                continue
                
            result = response.json()
            data = result.get('data') if isinstance(result, dict) else result
            
            if isinstance(data, list) and len(data) > 0:
                print(f">>>> [Jin10] SUCCESS: Found {len(data)} items in channel {channel}")
                return {"data": data}
            else:
                print(f">>>> [Jin10] Channel {channel} returned 0 items.")
        except Exception as e:
            print(f"[金十数据(JIN10)] 请求异常 (Channel {channel}): {e}")
            
    return None

async def get_latest_news(limit: int = 20):
    print("开始抓取 [金十数据(JIN10)]...")
    async with httpx.AsyncClient(trust_env=False, timeout=4.0) as client:
        data = await fetch_news_page(client)
        if data and 'data' in data:
            items = [normalize_item(item) for item in data['data'][:limit]]
            print(f"[金十数据(JIN10)] 成功获取 {len(items)} 条数据")
            return items
    print("[金十数据(JIN10)] 抓取失败或无数据")
    return []

async def get_history_news_generator(hours: int = 4):
    seen_ids, current_cursor, page_index = set(), None, 0
    cutoff = (datetime.now(BEIJING_TZ) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    async with httpx.AsyncClient(trust_env=False, timeout=4.0) as client:
        while True:
            page_index += 1
            yield json.dumps({"type": "progress", "status": "requesting", "page": page_index, "cursor": current_cursor or "Latest"}) + "\n"
            
            data = await fetch_news_page(client, current_cursor)
            if not data or not data.get('data'): 
                yield json.dumps({"type": "progress", "status": "finished", "message": "No more data or error"}) + "\n"
                break
            
            items = data['data']
            items_to_yield = []
            reached_limit = False
            
            for item in items:
                item_time = item.get('time', "")
                if item_time < cutoff:
                    reached_limit = True
                    break
                if item.get('id') not in seen_ids:
                    seen_ids.add(item.get('id'))
                    items_to_yield.append(normalize_item(item))
            
            if items_to_yield:
                yield json.dumps({"type": "data", "items": items_to_yield}) + "\n"
            
            if reached_limit:
                break
            
            last_time = items[-1].get('time')
            if not last_time or (current_cursor and last_time >= current_cursor):
                break
            current_cursor = last_time
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
        yield json.dumps({"type": "done"}) + "\n"
