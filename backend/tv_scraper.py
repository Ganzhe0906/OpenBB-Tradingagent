import httpx
import time
from datetime import datetime, timezone, timedelta

API_URL = "https://news-headlines.tradingview.com/v2/headlines"
STORY_URL = "https://news-headlines.tradingview.com/v2/story"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.tradingview.com/news-flow/?priority=flash,important,top_stories,key_facts",
    "Origin": "https://www.tradingview.com"
}

BEIJING_TZ = timezone(timedelta(hours=8))

def ast_to_text(node):
    if isinstance(node, str):
        return node
    elif isinstance(node, list):
        return "".join(ast_to_text(child) for child in node)
    elif isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "symbol":
            return node.get("params", {}).get("text", "")
        
        children = node.get("children", [])
        if isinstance(children, list):
            text = "".join(ast_to_text(child) for child in children)
            if node_type in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
                return text.strip() + "\n\n"
            return text
        elif isinstance(children, str):
            if node_type in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
                return children.strip() + "\n\n"
            return children
    return ""

async def fetch_story_content(client: httpx.AsyncClient, story_id: str) -> str:
    try:
        r = await client.get(STORY_URL, params={"client": "web", "lang": "en", "id": story_id}, timeout=8.0)
        if r.status_code == 200:
            data = r.json()
            ast = data.get("astDescription", {})
            return ast_to_text(ast).strip()
        else:
            return ""
    except Exception as e:
        print(f"Error fetching story content for {story_id}: {e}")
        return ""

def normalize_item(item, detail_content=""):
    """Convert TradingView news item to standardized dict for DB."""
    original_id = item.get('id')
    pub_ts = item.get('published', 0)
    
    # Convert timestamp to YYYY-MM-DD HH:MM:SS Beijing time
    dt = datetime.fromtimestamp(pub_ts, BEIJING_TZ)
    pub_date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    
    is_flash = item.get("is_flash") is True
    urgency = item.get("urgency", 2)
    provider = item.get("provider", "")
    
    title = item.get('title') or ""
    
    # Build a story URL if possible
    story_path = item.get("storyPath")
    url = f"https://www.tradingview.com{story_path}" if story_path else item.get("link") or ""
    
    return {
        "id": str(original_id),
        "source": item.get("source", "TradingView"),
        "title": title,
        "content": detail_content if detail_content else title,
        "pub_date": pub_date_str,
        "is_flash": is_flash,
        "urgency": urgency,
        "provider": provider,
        "url": url,
        "importance_score": 50,
        "asset_category": "OTHER",
        "process_status": "RAW"
    }

async def get_latest_news(limit: int = 100):
    """
    Fetches latest news from TradingView, filters them locally, 
    and pulls details for the filtered subset.
    """
    async with httpx.AsyncClient(trust_env=False, headers=HEADERS, timeout=12.0) as client:
        try:
            r = await client.get(API_URL, params={"lang": "en", "client": "web"})
            if r.status_code != 200:
                print(f"TradingView API returned {r.status_code}")
                return []
                
            data = r.json()
            items = data.get("items", [])
            
            # 1. Apply local filter matching formatting selections
            filtered_raw = []
            for item in items:
                is_flash = item.get("is_flash") is True
                is_important = item.get("urgency") == 1
                is_key_fact = item.get("provider") == "tradingview"
                
                if is_flash or is_important or is_key_fact:
                    filtered_raw.append(item)
            
            # Enforce limits if any
            filtered_raw = filtered_raw[:limit]
            
            # 2. Fetch detailed content for each filtered item
            normalized_items = []
            for item in filtered_raw:
                story_id = item.get("id")
                # Pull details (in real-time or fall back to title if failed)
                detail_text = await fetch_story_content(client, story_id)
                normalized_items.append(normalize_item(item, detail_text))
                
            return normalized_items
            
        except Exception as e:
            print(f"Error during TradingView scraping: {e}")
            return []
