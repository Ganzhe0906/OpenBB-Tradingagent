import time
import hashlib
import urllib.parse
import httpx
from datetime import datetime, timezone, timedelta

API_URL = "https://www.cls.cn/v1/roll/get_roll_list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cls.cn/telegraph",
    "Connection": "keep-alive"
}

BEIJING_TZ = timezone(timedelta(hours=8))

def normalize_item(item):
    """Convert Cailianpress API item to standardized news dict."""
    original_id = item.get('id')
    ctime = item.get('ctime', 0)
    
    # Convert timestamp to YYYY-MM-DD HH:MM:SS Beijing time
    dt = datetime.fromtimestamp(ctime, BEIJING_TZ)
    pub_date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # is_red logic
    is_red = False
    if (item.get('level') == 'A' or 
        item.get('recommend') == 1 or 
        item.get('is_red') == 1 or 
        item.get('color') == 'red'):
        is_red = True
        
    title = item.get('title') or ""
    content = item.get('content') or ""
    
    # If title is empty, generate from content
    if not title and content:
        title = content[:30] + "..." if len(content) > 30 else content
        
    return {
        "id": str(original_id),
        "source": "cls",
        "title": title,
        "content": content,
        "pub_date": pub_date_str,
        "is_red": is_red,
        "url": f"https://www.cls.cn/detail/{original_id}"
    }

def get_search_params(last_time: int, limit: int = 20):
    """Generates query parameters with double hashed signature."""
    params = {
        "appName": "CailianpressWeb",
        "os": "web",
        "sv": "8.7.9",
        "rn": limit,
        "refresh_type": 1,
        "last_time": last_time
    }
    # Filter out None values and sort by key
    filtered = {k: str(v) for k, v in params.items() if v is not None}
    sorted_items = sorted(filtered.items())
    
    # URL encode parameters
    encoded_str = urllib.parse.urlencode(sorted_items)
    
    # Double hashing: MD5(SHA1(sorted_query_string))
    sha1_val = hashlib.sha1(encoded_str.encode('utf-8')).hexdigest()
    sign = hashlib.md5(sha1_val.encode('utf-8')).hexdigest()
    
    filtered["sign"] = sign
    return filtered

async def fetch_news_page(client: httpx.AsyncClient, last_time: int, limit: int = 20):
    params = get_search_params(last_time, limit)
    try:
        response = await client.get(API_URL, params=params, headers=HEADERS, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching CLS news: {e}")
        return None

async def get_latest_news(limit: int = 20):
    """Fetches latest news from Cailianpress API."""
    current_time = int(time.time())
    async with httpx.AsyncClient(trust_env=False, timeout=8.0) as client:
        data = await fetch_news_page(client, current_time, limit)
        if data and 'data' in data and 'roll_data' in data['data']:
            roll_data = data['data']['roll_data']
            items = [normalize_item(item) for item in roll_data[:limit]]
            return items
    return []

