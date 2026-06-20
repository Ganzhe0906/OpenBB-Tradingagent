import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cls_news (
        unique_id TEXT PRIMARY KEY,
        id TEXT NOT NULL,
        source TEXT NOT NULL,
        title TEXT,
        content TEXT,
        pub_date TEXT NOT NULL,
        is_red INTEGER DEFAULT 0,
        url TEXT,
        importance_score INTEGER DEFAULT 50,
        asset_category TEXT DEFAULT 'OTHER',
        process_status TEXT DEFAULT 'RAW'
    )
    """)
    # Indexes for fast querying and sorting
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cls_news_pub_date ON cls_news (pub_date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cls_news_category ON cls_news (asset_category)")
    
    # Initialize investment_diaries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investment_diaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        diary_date TEXT UNIQUE NOT NULL,
        raw_input TEXT NOT NULL,
        structured_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investment_diaries_date ON investment_diaries (diary_date DESC)")
    
    # Initialize tv_news table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tv_news (
        unique_id TEXT PRIMARY KEY,
        id TEXT NOT NULL,
        source TEXT NOT NULL,
        title TEXT,
        content TEXT,
        pub_date TEXT NOT NULL,
        is_flash INTEGER DEFAULT 0,
        urgency INTEGER DEFAULT 2,
        provider TEXT,
        url TEXT,
        importance_score INTEGER DEFAULT 50,
        asset_category TEXT DEFAULT 'OTHER',
        process_status TEXT DEFAULT 'RAW'
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tv_news_pub_date ON tv_news (pub_date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tv_news_category ON tv_news (asset_category)")
    
    conn.commit()
    conn.close()
    print("SQLite database initialized at:", DB_PATH)

def save_news_items(items):
    conn = get_connection()
    cursor = conn.cursor()
    saved_count = 0
    for item in items:
        uid = f"{item['source']}:{item['id']}"
        cursor.execute("""
        INSERT OR IGNORE INTO cls_news (
            unique_id, id, source, title, content, pub_date, is_red, url, importance_score, asset_category, process_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            str(item['id']),
            item['source'],
            item.get('title', ''),
            item.get('content', ''),
            item['pub_date'], # Stored as standard "YYYY-MM-DD HH:MM:SS"
            1 if item.get('is_red') else 0,
            item.get('url', ''),
            item.get('importance_score', 50),
            item.get('asset_category', 'OTHER'),
            item.get('process_status', 'RAW')
        ))
        if cursor.rowcount > 0:
            saved_count += 1
    conn.commit()
    conn.close()
    return saved_count

def save_tv_news_items(items):
    conn = get_connection()
    cursor = conn.cursor()
    saved_count = 0
    for item in items:
        uid = f"tv:{item['id']}"
        cursor.execute("""
        INSERT OR IGNORE INTO tv_news (
            unique_id, id, source, title, content, pub_date, is_flash, urgency, provider, url, importance_score, asset_category, process_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            str(item['id']),
            item['source'],
            item.get('title', ''),
            item.get('content', ''),
            item['pub_date'],
            1 if item.get('is_flash') else 0,
            item.get('urgency', 2),
            item.get('provider', ''),
            item.get('url', ''),
            item.get('importance_score', 50),
            item.get('asset_category', 'OTHER'),
            item.get('process_status', 'RAW')
        ))
        if cursor.rowcount > 0:
            saved_count += 1
    conn.commit()
    conn.close()
    return saved_count

def query_news(start_time=None, end_time=None, category=None, min_score=None, limit=100, offset=0):
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT unique_id, id, source, title, content, pub_date, is_red, url, importance_score, asset_category, process_status FROM cls_news WHERE 1=1"
    params = []
    
    if start_time:
        sql += " AND pub_date >= ?"
        params.append(start_time)
    if end_time:
        sql += " AND pub_date <= ?"
        params.append(end_time)
    if category:
        sql += " AND asset_category = ?"
        params.append(category)
    if min_score is not None:
        sql += " AND importance_score >= ?"
        params.append(int(min_score))
        
    sql += " ORDER BY pub_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        results.append({
            "unique_id": row["unique_id"],
            "id": row["id"],
            "source": row["source"],
            "title": row["title"],
            "content": row["content"],
            "pub_date": row["pub_date"],
            "is_red": bool(row["is_red"]),
            "url": row["url"],
            "importance_score": row["importance_score"],
            "asset_category": row["asset_category"],
            "process_status": row["process_status"]
        })
    conn.close()
    return results

def update_news_ai_enrichment(unique_id, score, category, process_status="SCORED"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE cls_news
    SET importance_score = ?, asset_category = ?, process_status = ?
    WHERE unique_id = ?
    """, (score, category, process_status, unique_id))
    conn.commit()
    conn.close()

def query_tv_news(start_time=None, end_time=None, category=None, min_score=None, limit=100, offset=0):
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """SELECT unique_id, id, source, title, content, pub_date, is_flash, urgency, provider, url, importance_score, asset_category, process_status 
             FROM tv_news WHERE 1=1"""
    params = []
    
    if start_time:
        sql += " AND pub_date >= ?"
        params.append(start_time)
    if end_time:
        sql += " AND pub_date <= ?"
        params.append(end_time)
    if category:
        sql += " AND asset_category = ?"
        params.append(category)
    if min_score is not None:
        sql += " AND importance_score >= ?"
        params.append(int(min_score))
        
    sql += " ORDER BY pub_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        results.append({
            "unique_id": row["unique_id"],
            "id": row["id"],
            "source": row["source"],
            "title": row["title"],
            "content": row["content"],
            "pub_date": row["pub_date"],
            "is_flash": bool(row["is_flash"]),
            "urgency": row["urgency"],
            "provider": row["provider"],
            "url": row["url"],
            "importance_score": row["importance_score"],
            "asset_category": row["asset_category"],
            "process_status": row["process_status"]
        })
    conn.close()
    return results

def update_tv_news_ai_enrichment(unique_id, score, category, process_status="SCORED"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tv_news
    SET importance_score = ?, asset_category = ?, process_status = ?
    WHERE unique_id = ?
    """, (score, category, process_status, unique_id))
    conn.commit()
    conn.close()

def get_existing_uids(uids: list) -> set:
    if not uids:
        return set()
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(uids))
    cursor.execute(f"SELECT unique_id FROM cls_news WHERE unique_id IN ({placeholders})", uids)
    rows = cursor.fetchall()
    conn.close()
    return {row["unique_id"] for row in rows}

def save_diary(diary_date: str, raw_input: str, structured_content: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO investment_diaries (diary_date, raw_input, structured_content, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(diary_date) DO UPDATE SET
            raw_input=excluded.raw_input,
            structured_content=excluded.structured_content,
            updated_at=CURRENT_TIMESTAMP
        """, (diary_date, raw_input, structured_content))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving investment diary: {e}")
        return False
    finally:
        conn.close()

def get_diary(diary_date: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT diary_date, raw_input, structured_content, created_at, updated_at
    FROM investment_diaries
    WHERE diary_date = ?
    """, (diary_date,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "diary_date": row["diary_date"],
            "raw_input": row["raw_input"],
            "structured_content": row["structured_content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None

def list_diaries(limit: int = 100, offset: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT diary_date, raw_input, structured_content, created_at, updated_at
    FROM investment_diaries
    ORDER BY diary_date DESC
    LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            "diary_date": row["diary_date"],
            "raw_input": row["raw_input"],
            "structured_content": row["structured_content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })
    return results

def delete_diary(diary_date: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM investment_diaries WHERE diary_date = ?", (diary_date,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting investment diary: {e}")
        return False
    finally:
        conn.close()

