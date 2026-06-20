import os
import sys
import threading
import datetime
import shutil
import re
import asyncio
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add TradingAgents repo and workspace root to sys.path so we can import packages correctly
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

TRADING_AGENTS_PATH = os.path.join(WORKSPACE_ROOT, "TradingAgents")
if TRADING_AGENTS_PATH not in sys.path:
    sys.path.insert(0, TRADING_AGENTS_PATH)

# Load environment variables before importing TradingAgents to ensure overrides apply
from dotenv import load_dotenv
load_dotenv()

# Set default results directory if not set (pointing to reports folder at workspace root)
reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
os.environ.setdefault("TRADINGAGENTS_RESULTS_DIR", reports_dir)

try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
except ImportError:
    print("WARNING: Could not import TradingAgents. Make sure dependencies are installed.")

app = FastAPI(title="OpenBB + TradingAgents Backend")

@app.on_event("startup")
async def startup_event():
    try:
        from backend.db import init_db
        init_db()
        print(">>>> SQL news database initialized successfully.")
    except Exception as e:
        print(f">>>> SQL news database initialization failed: {e}")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory status tracking
status_lock = threading.Lock()
current_status = {
    "is_running": False,
    "current_ticker": None,
    "last_run_time": None,
    "last_run_ticker": None,
    "last_run_status": None,
    "error_message": None,
    "logs": [],
    
    # Individual stock debate stages
    "current_stage": "",
    "stages_progress": [
        {"id": "market", "name": "个股技术面与技术指标分析", "status": "pending"},
        {"id": "social", "name": "社交舆情与市场情绪分析", "status": "pending"},
        {"id": "news", "name": "核心新闻与重大事件分析", "status": "pending"},
        {"id": "fundamentals", "name": "公司财务报表基本面分析", "status": "pending"},
        {"id": "debate", "name": "投研团队多空对抗辩论", "status": "pending"},
        {"id": "trader", "name": "交易计划制定与执行方案", "status": "pending"},
        {"id": "risk", "name": "风控小组会商与PM最终裁决", "status": "pending"}
    ],
    
    # Macro/FinClaw engine status tracking
    "is_running_macro": False,
    "last_macro_run_time": None,
    "last_macro_run_status": None,
    "macro_error_message": None,
    "macro_logs": [],
    
    # Macro/FinClaw stages
    "macro_stage": "",
    "macro_stages_progress": [
        {"id": "init", "name": "初始化全球宏观分析环境", "status": "pending"},
        {"id": "fetch", "name": "跨市场资讯检索与 FRED 数据抓取", "status": "pending"},
        {"id": "reasoning", "name": "AI 推理与全球宏观综合判定", "status": "pending"},
        {"id": "report", "name": "保存并生成宏观研判报告", "status": "pending"}
    ]
}

class AnalysisRequest(BaseModel):
    ticker: str
    date: Optional[str] = None  # Format: YYYY-MM-DD

# Save original stdout
original_stdout = sys.stdout

def log_message(msg: str):
    original_stdout.write(msg + "\n")
    original_stdout.flush()
    with status_lock:
        current_status["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
        if len(current_status["logs"]) > 200:
            current_status["logs"].pop(0)

class StdoutRedirector:
    def __init__(self, orig_stdout):
        self.orig_stdout = orig_stdout
        
    def write(self, message):
        self.orig_stdout.write(message)
        self.orig_stdout.flush()
        cleaned = message.strip()
        if cleaned:
            # Filter out HTTP polling logs to avoid cluttering the UI
            if "GET /api/status" in cleaned or "WebSocket" in cleaned or "connection closed" in cleaned or "connection rejected" in cleaned:
                return
            with status_lock:
                if cleaned.startswith("[") or cleaned.startswith("=") or cleaned.startswith("-") or cleaned.startswith("Name:") or cleaned.startswith("Error:"):
                    current_status["logs"].append(cleaned)
                else:
                    current_status["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {cleaned}")
                if len(current_status["logs"]) > 200:
                    current_status["logs"].pop(0)
                    
    def flush(self):
        self.orig_stdout.flush()

    def isatty(self):
        return self.orig_stdout.isatty()

    @property
    def encoding(self):
        return self.orig_stdout.encoding

sys.stdout = StdoutRedirector(original_stdout)



def generate_consolidated_report(ticker: str, date_str: str, state: dict, decision_signal: str) -> str:
    """
    Constructs a beautiful consolidated markdown report from the final state of TradingAgents.
    """
    gen_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = []
    report.append(f"# 🍎 AI 交易决策报告: {ticker} ({date_str}) (生成时间: {gen_time_str})")
    report.append(f"\n* **生成时间**：{gen_time_str}")
    report.append(f"\n本报告由 OpenBB 金融数据源支撑，并由 TradingAgents 多智能体系统（包括技术、新闻、基本面分析师，多方辩论共识大脑，及风控系统）共识研判生成。")
    report.append(f"\n---\n")
    
    # 1. Executive Summary
    report.append(f"## 1. 投资决策概要 (Executive Summary)")
    report.append(f"\n* **标的物**：{ticker}")
    report.append(f"* **分析日期**：{date_str}")
    report.append(f"* **建议方向**：**{decision_signal.upper()}**")
    
    report.append(f"\n### ⚖️ 投资组合经理最终裁决与逻辑 (Portfolio Manager Decision)")
    pm_decision = state.get("final_trade_decision") or "暂无详细逻辑"
    report.append(f"\n{pm_decision}")
    report.append(f"\n---\n")
    
    # 2. Analyst Reports
    report.append(f"## 2. 智能体分析报告 (Analyst Team Reports)")
    
    if state.get("market_report"):
        report.append(f"\n### 📈 市场与技术面分析观点 (Market Analyst)")
        report.append(f"\n{state['market_report']}")
        
    if state.get("news_report"):
        report.append(f"\n### 📰 新闻与宏观分析观点 (News Analyst)")
        report.append(f"\n{state['news_report']}")
        
    if state.get("sentiment_report"):
        report.append(f"\n### 👥 社交舆情分析观点 (Sentiment Analyst)")
        report.append(f"\n{state['sentiment_report']}")
        
    if state.get("fundamentals_report"):
        report.append(f"\n### 💼 基本面分析观点 (Fundamentals Analyst)")
        report.append(f"\n{state['fundamentals_report']}")
        
    report.append(f"\n---\n")
    
    # 3. Research Debate
    debate = state.get("investment_debate_state", {})
    if debate:
        report.append(f"## 3. 多空辩论与共识大脑 (Research Team Debate)")
        if debate.get("bull_history"):
            report.append(f"\n### 🐂 多头方观点 (Bull Researcher)")
            report.append(f"\n{debate['bull_history']}")
        if debate.get("bear_history"):
            report.append(f"\n### 🐻 空头方观点 (Bear Researcher)")
            report.append(f"\n{debate['bear_history']}")
        if debate.get("judge_decision"):
            report.append(f"\n### ⚖️ 研究经理终审裁决 (Research Manager Judgment)")
            report.append(f"\n{debate['judge_decision']}")
        report.append(f"\n---\n")
        
    # 4. Trading Plan
    if state.get("trader_investment_plan"):
        report.append(f"## 4. 交易计划与执行方案 (Trading Team Plan)")
        report.append(f"\n{state['trader_investment_plan']}")
        report.append(f"\n---\n")
        
    # 5. Risk Management Debate
    risk = state.get("risk_debate_state", {})
    if risk:
        report.append(f"## 5. 风险控制与仓位管理 (Risk Management & Sizing)")
        if risk.get("aggressive_history"):
            report.append(f"\n### 🎯 积极派风控意见 (Aggressive Analyst)")
            report.append(f"\n{risk['aggressive_history']}")
        if risk.get("conservative_history"):
            report.append(f"\n### 🛡️ 保守派风控意见 (Conservative Analyst)")
            report.append(f"\n{risk['conservative_history']}")
        if risk.get("neutral_history"):
            report.append(f"\n### ⚖️ 中性派风控意见 (Neutral Analyst)")
            report.append(f"\n{risk['neutral_history']}")
        if risk.get("judge_decision"):
            report.append(f"\n### ⚖️ 风控大脑终裁仓位 (Risk Manager Judgment)")
            report.append(f"\n{risk['judge_decision']}")
            
    return "\n".join(report)


def run_agent_pipeline(ticker: str, date_str: str):
    global current_status
    
    def on_node_start(node_name: str):
        stage_id = None
        current_desc = ""
        if node_name in ["Market Analyst", "tools_market", "Msg Clear Market"]:
            stage_id = "market"
            current_desc = "正在分析量化指标与技术面走势..."
        elif node_name in ["Sentiment Analyst", "tools_social", "Msg Clear Sentiment"]:
            stage_id = "social"
            current_desc = "正在获取社交舆情与情绪数据..."
        elif node_name in ["News Analyst", "tools_news", "Msg Clear News"]:
            stage_id = "news"
            current_desc = "正在整理重特大新闻与行业动态..."
        elif node_name in ["Fundamentals Analyst", "tools_fundamentals", "Msg Clear Fundamentals"]:
            stage_id = "fundamentals"
            current_desc = "正在加载财务报表与经营成果..."
        elif node_name in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
            stage_id = "debate"
            current_desc = f"投研团队多空对抗辩论中: {node_name}..."
        elif node_name == "Trader":
            stage_id = "trader"
            current_desc = "交易员正在撰写投资执行计划..."
        elif node_name in ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst", "Portfolio Manager"]:
            stage_id = "risk"
            current_desc = f"风控研判会商中: {node_name}..."

        with status_lock:
            if current_desc:
                current_status["current_stage"] = current_desc
            if stage_id:
                found_current = False
                for step in current_status["stages_progress"]:
                    if step["id"] == stage_id:
                        step["status"] = "running"
                        found_current = True
                    elif not found_current:
                        step["status"] = "completed"
                    else:
                        step["status"] = "pending"

    try:
        log_message(f"Starting Multi-Agent analysis for {ticker} on date {date_str}...")
        
        # 1. Initialize configuration with environmental overrides
        config = DEFAULT_CONFIG.copy()
        
        # Force yfinance for local free testing if no API key exists
        if not os.getenv("ALPHA_VANTAGE_API_KEY"):
            log_message("No ALPHA_VANTAGE_API_KEY found, using free yfinance for all data feeds.")
            config["data_vendors"] = {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
            }
        
        # 2. Run TradingAgentsGraph
        log_message("Initializing TradingAgentsGraph...")
        ta = TradingAgentsGraph(debug=True, config=config)
        
        log_message(f"Propagating graph for {ticker}...")
        # propagate returns (state, decision_signal)
        state, decision = ta.propagate(ticker, date_str, on_node_start=on_node_start)
        
        log_message("Analysis completed successfully!")
        
        # Generate consolidated Markdown report
        log_message("Generating consolidated Markdown report...")
        report_markdown = generate_consolidated_report(ticker, date_str, state, decision)
        
        # 3. Write report to reports folder
        reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
        os.makedirs(reports_dir, exist_ok=True)
        
        # Filename format: YYYY-MM-DD-TICKER.md
        report_filename = f"{date_str}-{ticker}.md"
        report_path = os.path.join(reports_dir, report_filename)
        
        log_message(f"Saving Markdown report to: {report_path}")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
            
        with status_lock:
            current_status["is_running"] = False
            current_status["last_run_time"] = datetime.datetime.now().isoformat()
            current_status["last_run_ticker"] = ticker
            current_status["last_run_status"] = "success"
            current_status["current_stage"] = "分析已完成！"
            current_status["current_ticker"] = None
            for step in current_status["stages_progress"]:
                step["status"] = "completed"
            
    except Exception as e:
        error_msg = str(e)
        log_message(f"Error during agent pipeline run: {error_msg}")
        with status_lock:
            current_status["is_running"] = False
            current_status["last_run_status"] = "error"
            current_status["error_message"] = error_msg
            current_status["current_ticker"] = None
            current_status["current_stage"] = f"研判执行失败: {error_msg}"
            for step in current_status["stages_progress"]:
                if step["status"] == "running":
                    step["status"] = "failed"

@app.get("/api/status")
def get_status():
    with status_lock:
        return current_status

@app.post("/api/run-analysis")
def trigger_analysis(req: AnalysisRequest, background_tasks: BackgroundTasks):
    global current_status
    
    # Check if a model key is configured
    provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER", "google")
    api_key_env = "GOOGLE_API_KEY" if provider == "google" else "DEEPSEEK_API_KEY" if provider == "deepseek" else "OPENAI_API_KEY"
    if not os.getenv(api_key_env) and provider != "ollama":
        raise HTTPException(
            status_code=400, 
            detail=f"LLM API Key missing. Please set {api_key_env} in your backend/.env file."
        )

    with status_lock:
        if current_status["is_running"]:
            raise HTTPException(status_code=400, detail="An analysis is already in progress.")
        
        ticker = req.ticker.upper().strip()
        date_str = req.date or datetime.date.today().strftime("%Y-%m-%d")
        
        current_status["is_running"] = True
        current_status["current_ticker"] = ticker
        current_status["error_message"] = None
        current_status["current_stage"] = "初始化工作流并启动多智能体大脑..."
        current_status["logs"] = []
        current_status["stages_progress"] = [
            {"id": "market", "name": "个股技术面与技术指标分析", "status": "pending"},
            {"id": "social", "name": "社交舆情与市场情绪分析", "status": "pending"},
            {"id": "news", "name": "核心新闻与重大事件分析", "status": "pending"},
            {"id": "fundamentals", "name": "公司财务报表基本面分析", "status": "pending"},
            {"id": "debate", "name": "投研团队多空对抗辩论", "status": "pending"},
            {"id": "trader", "name": "交易计划制定与执行方案", "status": "pending"},
            {"id": "risk", "name": "风控小组会商与PM最终裁决", "status": "pending"}
        ]
        
    background_tasks.add_task(run_agent_pipeline, ticker, date_str)
    return {"status": "started", "ticker": ticker, "date": date_str}

@app.get("/api/stock-info/{ticker}")
def get_stock_info(ticker: str):
    """
    Fetches basic stock information using OpenBB Platform.
    Falls back to simple yfinance if OpenBB is not fully configured.
    """
    ticker = ticker.upper().strip()
    try:
        # Try to import and run OpenBB Platform
        from openbb import obb
        log_message(f"Fetching {ticker} info via OpenBB...")
        
        # Get historical price (last 30 days) and standard company profile
        # Note: OpenBB endpoints can vary depending on provider. Using yfinance provider.
        res = obb.equity.price.historical(ticker, provider="yfinance")
        df = res.to_dataframe()
        
        if df.empty:
            raise Exception("No data returned from OpenBB")
            
        latest_price = float(df['close'].iloc[-1])
        change = float(df['close'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0.0
        change_percent = (change / float(df['close'].iloc[-2])) * 100 if len(df) > 1 else 0.0
        
        return {
            "ticker": ticker,
            "price": round(latest_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "source": "OpenBB (yfinance)"
        }
    except Exception as obb_err:
        log_message(f"OpenBB fetch failed ({str(obb_err)}). Falling back to direct yfinance...")
        try:
            import yfinance as yf
            ticker_obj = yf.Ticker(ticker)
            history = ticker_obj.history(period="5d")
            if history.empty:
                raise Exception(f"No price data found for {ticker}")
            latest_price = float(history['Close'].iloc[-1])
            prev_price = float(history['Close'].iloc[-2]) if len(history) > 1 else latest_price
            change = latest_price - prev_price
            change_percent = (change / prev_price) * 100 if prev_price > 0 else 0.0
            
            return {
                "ticker": ticker,
                "price": round(latest_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "source": "Direct yfinance (Fallback)"
            }
        except Exception as yf_err:
            raise HTTPException(status_code=404, detail=f"Failed to fetch stock data: {str(yf_err)}")

@app.get("/api/reports")
def list_reports():
    """
    List all reports in TRADINGAGENTS_RESULTS_DIR.
    Filename expected format: YYYY-MM-DD-TICKER.md or similar.
    Returns sorted list by file modification time (newest first).
    """
    reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
    if not os.path.exists(reports_dir):
        return []
    
    files = os.listdir(reports_dir)
    report_list = []
    for f in files:
        if f.endswith(".md"):
            file_path = os.path.join(reports_dir, f)
            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0
            
            # Try to parse date and ticker from YYYY-MM-DD-TICKER.md
            match = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", f)
            if match:
                date_str, ticker = match.groups()
                report_list.append({
                    "filename": f,
                    "date": date_str,
                    "ticker": ticker.upper(),
                    "mtime": mtime
                })
            else:
                report_list.append({
                    "filename": f,
                    "date": "unknown",
                    "ticker": f.replace(".md", ""),
                    "mtime": mtime
                })
                
    # Sort by file modification time descending
    report_list.sort(key=lambda x: x["mtime"], reverse=True)
    return report_list

@app.get("/api/reports/{filename}")
def get_report_content(filename: str):
    """
    Safely retrieves the content of a specific report.
    """
    # Validate filename to prevent path traversal
    if not re.match(r"^[a-zA-Z0-9_\-\.]+\.md$", filename):
        raise HTTPException(status_code=400, detail="Invalid report filename")
        
    reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
    file_path = os.path.join(reports_dir, filename)
    
    # Ensure the path is actually inside the reports directory
    real_reports_dir = os.path.realpath(reports_dir)
    real_file_path = os.path.realpath(file_path)
    if not real_file_path.startswith(real_reports_dir):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "filename": filename,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {str(e)}")

@app.delete("/api/reports/{filename}")
def delete_report(filename: str):
    """
    Safely deletes a report file from the reports directory.
    """
    # Validate filename to prevent path traversal
    if not re.match(r"^[a-zA-Z0-9_\-\.]+\.md$", filename):
        raise HTTPException(status_code=400, detail="Invalid report filename")
        
    reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
    file_path = os.path.join(reports_dir, filename)
    
    # Ensure the path is actually inside the reports directory
    real_reports_dir = os.path.realpath(reports_dir)
    real_file_path = os.path.realpath(file_path)
    if not real_file_path.startswith(real_reports_dir):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"Report {filename} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


# Macro Analysis Models & Routes
class MacroRequest(BaseModel):
    template_type: str  # "weekly_flow", "daily_review", "risk_quant", "custom"
    custom_query: Optional[str] = None

def log_macro_message(msg: str):
    original_stdout.write(f"[MACRO] {msg}\n")
    original_stdout.flush()
    
    # Simple log parsing to detect current macro stage
    detected_stage = None
    stage_id = None
    
    if "tavily_search" in msg or "brave_search" in msg or "web_search" in msg or "WebSearch" in msg:
        stage_id = "fetch"
        detected_stage = "正在通过 Tavily/Brave 检索最新宏观舆情与行业动态..."
    elif "economics_data" in msg or "economics_router" in msg:
        stage_id = "fetch"
        detected_stage = "正在抓取 FRED 宏观经济数据指标..."
    elif "prediction_market" in msg:
        stage_id = "fetch"
        detected_stage = "正在获取预测市场大选/赔率数据..."
    elif "financial_news" in msg:
        stage_id = "fetch"
        detected_stage = "正在抓取主流媒体金融新闻快讯..."
    elif "equity_valuation" in msg:
        stage_id = "fetch"
        detected_stage = "正在检索核心资产历史估值水位..."
    elif "meme_router" in msg:
        stage_id = "fetch"
        detected_stage = "正在扫描链上资金与社交情绪数据..."
    elif "→ tool:" in msg or "calling tool" in msg:
        stage_id = "fetch"
        tool_name = "未知工具"
        try:
            tool_name = msg.split("tool:")[-1].split("args:")[0].strip()
        except:
            pass
        detected_stage = f"正在调用数据抓取工具: {tool_name}..."
    elif "LLM" in msg or "reasoning" in msg or "Reasoning" in msg or "Thinking" in msg or "thinking" in msg:
        stage_id = "reasoning"
        detected_stage = "AI 正在对全球宏观多源信息进行综合研判与推理..."
    elif "completed successfully" in msg:
        stage_id = "report"
        detected_stage = "研判已完成，正在生成终审报告..."
        
    with status_lock:
        current_status["macro_logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
        if len(current_status["macro_logs"]) > 200:
            current_status["macro_logs"].pop(0)
            
        if detected_stage:
            current_status["macro_stage"] = detected_stage
            
        if stage_id:
            found_current = False
            for step in current_status["macro_stages_progress"]:
                if step["id"] == stage_id:
                    step["status"] = "running"
                    found_current = True
                elif not found_current:
                    step["status"] = "completed"
                else:
                    step["status"] = "pending"

def run_macro_pipeline(template_type: str, custom_query: Optional[str]):
    global current_status
    try:
        with status_lock:
            current_status["macro_stage"] = "正在初始化全球宏观数据分析流..."
            current_status["macro_stages_progress"][0]["status"] = "completed"
            current_status["macro_stages_progress"][1]["status"] = "running"
        # Map template types to actual prompts
        if template_type == "weekly_flow":
            prompt = """[AUTOMATED BATCH TASK - DO NOT CHAT, DO NOT GREET, DO NOT ASK QUESTIONS. GO STRAIGHT TO TOOL CALLS AND WRITE THE FINAL REPORT DIRECTLY.]
请分析过去5个交易日（近一周内）全球大类资产的价格变动与资金流向状况：
1. 权益类：美股(S&P 500、纳斯达克、道琼斯)、日股(日经225)、韩股(韩国KOSPI)、A股(沪深300)、港股(恒生指数)的近一周表现与涨跌幅。
2. 利率类：十年期美债收益率、二年期美债收益率及2s10s利差的走势与变化。
3. 商品与加密：黄金(GC=F)、原油(CL=F)及比特币(BTC-USD)的最新表现。请务必使用工具拉取5天前的收盘价，并计算出这一周内黄金、原油的具体涨跌幅（%）。
请获取上述数据后，构建一份《全球大类资产跨市场资金流向矩阵表》，详尽归纳并推演这一周内资金变动。

特别注意（防幻觉指令）：
- 必须在报告的第一部分以清晰的表格列出所有权益、美债、商品（黄金/原油）及比特币的本周具体价格变动与涨跌幅（%），不得遗漏或使用“—”代替。
- 必须保持客观！如果股票下跌的同时黄金也出现了下跌（例如本周因非农数据超预期、美联储紧缩预期升温而导致的全球“现金为王、股债金三杀”），必须在报告中如实陈述黄金下跌的事实，并分析其背后的流动性紧缩逻辑，绝对不允许为了迎合“避险资产”的定义而强行拼凑“资金流向黄金导致黄金上涨”的虚假叙事。"""
        elif template_type == "daily_review":
            prompt = """[AUTOMATED BATCH TASK - DO NOT CHAT, DO NOT GREET, DO NOT ASK QUESTIONS. GO STRAIGHT TO TOOL CALLS AND WRITE THE FINAL REPORT DIRECTLY.]
请分析过去24小时内全球金融大势，确保对“欧美市场”、“中国及港股市场”、“日韩市场”三大核心区域进行深度覆盖。
为了获取最接地气、最高精度的行业分析与观点，请务必生成并执行多源检索词：
- 英文检索（针对欧美宏观与AI板块）：Fed policy path, non-farm payrolls, stock market selloff, Goldman Sachs/JPMorgan analyst report.
- 中文检索（针对中国/港股宏观与核心企业）：A股 港股 宏观政策 经济数据, 中金公司 研报 观点, 中信证券 降准 降息 A股走势, 恒生指数 估值。
- 亚洲英文检索（针对日韩与汇率）：BOJ interest rate hike expectation, Yen Won depreciation, KOSPI Short selling, Nomura Japan market outlook.

请将最终报告结构化地拆分为以下三大模块：

### 模块一：欧美市场与美联储路径 (US & Europe)
1. 梳理过去24小时最核心的重大宏观事件/数据发布（如就业数据、通胀指数、地缘政治）。
2. 提炼全球主流大行（高盛、摩根大通、摩根士丹利、花旗、美银等）最新的辩论交锋。保持高度的精细度与深度。

### 模块二：中国及港股市场 (China & HK)
1. 梳理过去24小时最核心的中国本土政策动态、宏观经济数据发布或市场行情（如LPR基准利率、国家队资金动向、房地产/地方债政策）。
2. 提炼国内顶尖投行及券商（中金公司(CICC)、中信证券、国泰君安、申万宏源等）最新的宏观研判与博弈观点辩论表。

### 模块三：日韩股市与货币政策 (Japan & South Korea)
1. 梳理过去24小时日经225和韩国KOSPI市场的变动及核心推手（如芯片板块波动、日元/韩元贬值、官方汇率干预口径）。
2. 提炼野村证券、大和证券、三星证券及央行决策层的交锋观点辩论表。

请在每个模块下，均输出：
- 24小时重磅新闻动态简表。
- 机构与大行分析师观点博弈辩论表，提取针锋相对的论点并客观做合理性评估。"""
        elif template_type == "risk_quant":
            prompt = """[AUTOMATED BATCH TASK - DO NOT CHAT, DO NOT GREET, DO NOT ASK QUESTIONS. GO STRAIGHT TO TOOL CALLS AND WRITE THE FINAL REPORT DIRECTLY.]
请对当前市场情绪、信用、流动性以及核心大类资产进行统计量化，以评估此时此刻全球各大资产的风险性跟整体的一个风险倾向：
1. 情绪指标：美股VIX恐慌指数(^VIX)的最新数值及历史水位。
2. 信用与债市：美国高收益债信用利差(FRED ID: BAMLH0A0HYM2，可在Tavily搜索或FRED直接拉取)及10年期美债收益率的变化。
3. 全球流动性：美元指数(DXY)所处水位。
4. 实物避险与能源：黄金价格(GC=F)与原油价格(CL=F)的历史水位。
5. 加密货币风险：比特币(BTC-USD)的历史价格与情绪水位。
请计算这些关键指数过去5年的历史百分位数（Percentile）和偏离度(Z-score)，说明各大类资产目前是处于“极度高估/拥挤”、“极度恐慌/贪婪”还是“流动性紧张”的绝对水位，并输出整体市场系统性风险倾向评估。"""
        elif template_type == "watchlist_monitor":
            prompt = """[AUTOMATED BATCH TASK - DO NOT CHAT, DO NOT GREET, DO NOT ASK QUESTIONS. GO STRAIGHT TO TOOL CALLS AND WRITE THE FINAL REPORT DIRECTLY.]
你是一个顶尖的全球宏观与半导体/AI产业链研究专家。请针对用户重点关注的以下资产清单，通过检索与数据工具（如 yfinance_tool 获取价格、Tavily/Brave 获取最新新闻）获取【当天最新收盘价/实时价格】、【过去24小时（或最近一个交易日）的变动幅度】以及【过去24小时内最值得关注的 TOP 3 核心新闻与异动成因】：

1. 核心科技与AI硬件板块：
   - 纳斯达克指数 / QQQ / NAS100 
   - NVDA (英伟达)
   - AMD (超威半导体)
   - MU (美光科技)
   - AVGO (博通)
   - MRVL (迈威尔科技)
   - 半导体板块指数/ETF：SMH / SOXX / SOX
   - 美股 AI 概念股整体动向 (如 MSFT, GOOG, META 等核心领涨/领跌股)

2. 全球其他核心权益与产业链市场：
   - 韩国股市 (KOSPI指数，以及核心半导体巨头三星电子、SK海力士的异动)
   - 中国股市 (A股 沪深300、港股 恒生指数表现)
   - 中国半导体/芯片/存储芯片板块 (如中芯国际、北方华创，及长鑫存储/长江存储等产业端最新进展与政策消息)

3. 大势与避险/商品资产：
   - 黄金 (GC=F) 与 白银 (SI=F) 
   - 国际原油 (CL=F)
   - 比特币 (BTC-USD)

对于上述资产，请务必执行以下专业的分析产出：
1. **最新价格与24h变动数据矩阵**：
   请使用表格列出每个资产的最新价格（标明获取的时间或数据截止日期）、24小时内涨跌幅（%）以及短期技术趋势（如突破、整理、回调等）。不允许使用“待获取”或虚假的占位符，必须用工具检索真实数据，价格必须最新。
2. **24小时最值得关注的重磅新闻 TOP 3**：
   梳理这组资产过去24小时内最关键的3条新闻事件（如芯片五巨头财报预测/大行评级调增、半导体代工端定价、宏观政策地缘动向等），并详细陈述其对于整个板块的影响路径。
3. **AI与半导体产业链异动透视**：
   重点分析美股芯片五巨头（NVDA, AMD, MU, AVGO, MRVL）及存储、代工端在过去24小时内是否有重大消息，以及这些消息如何传导至韩国半导体（三星、海力士）和中国半导体板块。
4. **宏观避险与大宗商品博弈**：
   分析黄金、白银、原油以及比特币在过去24小时的变动主因（如美联储官员鹰鸽讲话、通胀预期、流动性变化或地缘政治突发事件）。
5. **全球资金流向与市场情绪总结**：
   判断目前市场资金在“AI硬科技 - 避险资产 - 亚太权益（中韩）”之间的轮动状态。

请保持极高的专业度，分析应深入到产业逻辑（如“美光存储芯片HBM产能”、“博通ASIC芯片订单”、“存储晶圆报价走势”、“光刻机/设备国产化率”等），不要流于表面。"""
        else:
            prompt = custom_query or "分析当前全球宏观经济和金融市场的整体风险状况。"

        if custom_query and template_type != "custom":
            prompt = f"{prompt}\n用户补充提问: {custom_query}"

        log_macro_message(f"Starting Macro Analysis for template {template_type}...")
        
        # Load finclaw wrapper
        from backend.finclaw_wrapper import run_finclaw_macro_analysis
        
        # Run inside a clean event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report_markdown = loop.run_until_complete(
                run_finclaw_macro_analysis(prompt, log_macro_message)
            )
        finally:
            loop.close()
            
        log_macro_message("Macro analysis completed successfully!")
        
        # Prepare title
        report_title = {
            "weekly_flow": "全球大类资产周度资金流向",
            "daily_review": "24小时全球大势锐评",
            "risk_quant": "核心大类资产风险水位量化",
            "watchlist_monitor": "核心关注资产异动监测"
        }.get(template_type, "全球宏观共识研判")

        date_str = datetime.date.today().strftime("%Y-%m-%d")
        gen_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_report = f"""# 🌐 AI 宏观研判报告: {report_title} ({date_str}) (生成时间: {gen_time_str})

本报告由 FRED 宏观经济数据源与 Tavily 金融搜索引擎提供支撑，并由 FinClaw 金融智能体系统自主分析与研判生成。

* **生成时间**：{gen_time_str}

---

{report_markdown}

---
*注：本报告仅供学术及模拟测试研究使用，不构成任何实质投资建议。*
"""
        
        # Write report to reports folder
        reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
        os.makedirs(reports_dir, exist_ok=True)
        
        report_filename = f"{date_str}-MACRO-{template_type}.md"
        report_path = os.path.join(reports_dir, report_filename)
        
        log_macro_message(f"Saving Macro report to: {report_path}")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report)
            
        with status_lock:
            current_status["is_running_macro"] = False
            current_status["last_macro_run_time"] = datetime.datetime.now().isoformat()
            current_status["last_macro_run_status"] = "success"
            current_status["macro_stage"] = "全球宏观分析已完成！"
            for step in current_status["macro_stages_progress"]:
                step["status"] = "completed"
            
    except Exception as e:
        error_msg = str(e)
        log_macro_message(f"Error during macro analysis pipeline run: {error_msg}")
        with status_lock:
            current_status["is_running_macro"] = False
            current_status["last_macro_run_status"] = "error"
            current_status["macro_error_message"] = error_msg
            current_status["macro_stage"] = f"分析发生错误: {error_msg}"
            for step in current_status["macro_stages_progress"]:
                if step["status"] == "running":
                    step["status"] = "failed"

@app.post("/api/run-macro-analysis")
def trigger_macro_analysis(req: MacroRequest, background_tasks: BackgroundTasks):
    global current_status
    
    # Check if DEEPSEEK_API_KEY is configured
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise HTTPException(
            status_code=400, 
            detail="DeepSeek API Key missing. Please set DEEPSEEK_API_KEY in your backend/.env file."
        )

    with status_lock:
        if current_status["is_running_macro"]:
            raise HTTPException(status_code=400, detail="A macro analysis is already in progress.")
        
        current_status["is_running_macro"] = True
        current_status["macro_error_message"] = None
        current_status["macro_stage"] = "配置就绪，启动 FinClaw 引擎..."
        current_status["macro_logs"] = []
        current_status["macro_stages_progress"] = [
            {"id": "init", "name": "初始化全球宏观分析环境", "status": "running"},
            {"id": "fetch", "name": "跨市场资讯检索与 FRED 数据抓取", "status": "pending"},
            {"id": "reasoning", "name": "AI 推理与全球宏观综合判定", "status": "pending"},
            {"id": "report", "name": "保存并生成宏观研判报告", "status": "pending"}
        ]
        
    background_tasks.add_task(run_macro_pipeline, req.template_type, req.custom_query)
    return {"status": "started", "template_type": req.template_type}

# ==============================================================================
# 财联社新闻接口 (Cailianpress News APIs)
# ==============================================================================

class NewsAnalyzeRequest(BaseModel):
    start_time: str
    end_time: str
    analysis_type: str  # "top5", "extreme", "custom", "global_assets"
    custom_query: Optional[str] = None

@app.post("/api/news/cls/sync")
async def sync_cls_news():
    """同时抓取最新财联社电报与TradingView新闻快讯并存盘 (合并进程设计)"""
    try:
        from backend import cls_scraper, tv_scraper, db
        
        # 1. 抓取与保存财联社电报 (最新30条)
        cls_items = await cls_scraper.get_latest_news(30)
        saved_cls = 0
        if cls_items:
            saved_cls = db.save_news_items(cls_items)
            
        # 2. 抓取与保存TradingView新闻快讯 (最新30条，自动本地过滤并抓取正文)
        tv_items = await tv_scraper.get_latest_news(30)
        saved_tv = 0
        if tv_items:
            saved_tv = db.save_tv_news_items(tv_items)
            
        return {
            "status": "success", 
            "saved_count": saved_cls,
            "saved_tv_count": saved_tv,
            "message": f"Synced {saved_cls} Cailianpress items and {saved_tv} TradingView items."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync news: {str(e)}")

@app.get("/api/news/cls/list")
async def list_cls_news(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """筛选时间范围内的已保存新闻列表"""
    try:
        from backend import db
        results = db.query_news(
            start_time=start_time,
            end_time=end_time,
            category=category,
            min_score=min_score,
            limit=limit,
            offset=offset
        )
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query news: {str(e)}")

@app.post("/api/news/cls/analyze")
async def analyze_cls_news(req: NewsAnalyzeRequest):
    """利用 DeepSeek 大模型对时间范围内的快讯执行分析，并自动生成报告持久化至决策报告文件夹"""
    try:
        import datetime
        from backend import db, ai_analyzer
        # 获取筛选区间内的所有新闻快讯
        news_items = db.query_news(start_time=req.start_time, end_time=req.end_time, limit=500)
        if not news_items:
            return {"status": "success", "result": "在选定时间段内暂无可用快讯，无法进行 AI 分析。"}
            
        if req.analysis_type == "top5":
            result = await ai_analyzer.analyze_top_five(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "Top 5 核心快讯总结"
        elif req.analysis_type == "extreme":
            result = await ai_analyzer.analyze_extreme_movements(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "极端行情研判"
        elif req.analysis_type == "global_assets":
            result = await ai_analyzer.analyze_global_assets(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "全球资产波动简报"
        elif req.analysis_type == "custom":
            if not req.custom_query or not req.custom_query.strip():
                raise HTTPException(status_code=400, detail="Custom query is required for custom analysis.")
            result = await ai_analyzer.analyze_custom_query(news_items, req.custom_query, start_time=req.start_time, end_time=req.end_time)
            type_desc = f"自定义提问: {req.custom_query[:25]}"
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis_type. Must be 'top5', 'extreme', 'global_assets', or 'custom'.")
            
        # 1. 生成报告标题与当前生成时间
        now = datetime.datetime.now()
        gen_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        gen_date_str = now.strftime("%Y-%m-%d")
        gen_timestamp_str = now.strftime("%H%M%S")
        
        full_report = f"""# 📰 财联社 AI 决策研判报告 ({gen_time_str})
        
本报告由财联社实时快讯数据源支撑，并通过 DeepSeek 大模型自主分析与研判生成。

* **生成时间**：{gen_time_str}
* **快讯时间范围**：{req.start_time} 至 {req.end_time}
* **研判类型**：{type_desc}
* **快讯样本数**：{len(news_items)} 条

---

{result}

---
*注：本报告仅供学术及模拟测试研究使用，不构成任何实质性投资决策。*
"""
        
        # 2. 写入报告至决策报告目录 (TRADINGAGENTS_RESULTS_DIR)
        reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
        os.makedirs(reports_dir, exist_ok=True)
        
        # 文件名格式需符合 YYYY-MM-DD-TICKER.md
        # 此处将 CLS_分析类型_时分秒 作为“TICKER/标题”，以确保列表解析成功并显示生成时间
        report_filename = f"{gen_date_str}-CLS_{req.analysis_type}_{gen_timestamp_str}.md"
        report_path = os.path.join(reports_dir, report_filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report)
            
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

# ==============================================================================
# TradingView 新闻接口 (TradingView News APIs)
# ==============================================================================

@app.get("/api/news/tv/list")
async def list_tv_news(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """筛选时间范围内的已保存TradingView新闻快讯列表"""
    try:
        from backend import db
        results = db.query_tv_news(
            start_time=start_time,
            end_time=end_time,
            category=category,
            min_score=min_score,
            limit=limit,
            offset=offset
        )
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query TradingView news: {str(e)}")

@app.post("/api/news/tv/analyze")
async def analyze_tv_news(req: NewsAnalyzeRequest):
    """利用 DeepSeek 大模型对时间范围内的TradingView快讯执行分析，并自动生成报告"""
    try:
        import datetime
        from backend import db, ai_analyzer
        # 获取筛选区间内的所有 TradingView 新闻快讯
        news_items = db.query_tv_news(start_time=req.start_time, end_time=req.end_time, limit=500)
        if not news_items:
            return {"status": "success", "result": "在选定时间段内暂无可用快讯，无法进行 AI 分析。"}
            
        if req.analysis_type == "top5":
            result = await ai_analyzer.analyze_top_five(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "Top 5 核心快讯总结"
        elif req.analysis_type == "extreme":
            result = await ai_analyzer.analyze_extreme_movements(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "极端行情研判"
        elif req.analysis_type == "global_assets":
            result = await ai_analyzer.analyze_global_assets(news_items, start_time=req.start_time, end_time=req.end_time)
            type_desc = "全球资产波动简报"
        elif req.analysis_type == "custom":
            if not req.custom_query or not req.custom_query.strip():
                raise HTTPException(status_code=400, detail="Custom query is required for custom analysis.")
            result = await ai_analyzer.analyze_custom_query(news_items, req.custom_query, start_time=req.start_time, end_time=req.end_time)
            type_desc = f"自定义提问: {req.custom_query[:25]}"
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis_type. Must be 'top5', 'extreme', 'global_assets', or 'custom'.")
            
        # 1. 生成报告标题与当前生成时间
        now = datetime.datetime.now()
        gen_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        gen_date_str = now.strftime("%Y-%m-%d")
        gen_timestamp_str = now.strftime("%H%M%S")
        
        full_report = f"""# 🌐 TradingView AI 决策研判报告 ({gen_time_str})
        
本报告由 TradingView 实时快讯数据源支撑，并通过 DeepSeek 大模型自主分析与研判生成。

* **生成时间**：{gen_time_str}
* **快讯时间范围**：{req.start_time} 至 {req.end_time}
* **研判类型**：{type_desc}
* **快讯样本数**：{len(news_items)} 条

---

{result}

---
*注：本报告仅供学术及模拟测试研究使用，不构成任何实质性投资决策。*
"""
        
        # 2. 写入报告至决策报告目录 (TRADINGAGENTS_RESULTS_DIR)
        reports_dir = os.environ.get("TRADINGAGENTS_RESULTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports")))
        os.makedirs(reports_dir, exist_ok=True)
        
        # 文件名格式需符合 YYYY-MM-DD-TICKER.md
        report_filename = f"{gen_date_str}-TV_{req.analysis_type}_{gen_timestamp_str}.md"
        report_path = os.path.join(reports_dir, report_filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report)
            
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

# ==============================================================================
# 投资日记接口 (Investment Diary APIs)
# ==============================================================================

class DiaryGenerateRequest(BaseModel):
    raw_input: str
    date: Optional[str] = None
    suggestion: Optional[str] = None
    previous_structured_content: Optional[str] = None

class DiarySaveRequest(BaseModel):
    diary_date: str
    raw_input: str
    structured_content: str

@app.get("/api/diaries")
def list_investment_diaries(limit: int = 100, offset: int = 0):
    try:
        from backend import db
        diaries = db.list_diaries(limit=limit, offset=offset)
        return {"status": "success", "data": diaries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list diaries: {str(e)}")

@app.get("/api/diaries/{date}")
def get_investment_diary(date: str):
    try:
        from backend import db
        diary = db.get_diary(date)
        if not diary:
            raise HTTPException(status_code=404, detail=f"Diary for {date} not found.")
        return {"status": "success", "data": diary}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get diary: {str(e)}")

@app.post("/api/diaries/generate")
async def generate_diary_report(req: DiaryGenerateRequest):
    try:
        from backend import ai_analyzer
        import datetime
        
        diary_date = req.date or datetime.date.today().strftime("%Y-%m-%d")
        
        # Check if DEEPSEEK_API_KEY is configured
        if not os.getenv("DEEPSEEK_API_KEY"):
            raise HTTPException(
                status_code=400, 
                detail="DeepSeek API Key missing. Please set DEEPSEEK_API_KEY in your backend/.env file."
            )
            
        result = await ai_analyzer.generate_structured_diary(
            raw_input=req.raw_input,
            diary_date=diary_date,
            suggestion=req.suggestion,
            previous_structured_content=req.previous_structured_content
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

@app.post("/api/diaries/save")
def save_investment_diary(req: DiarySaveRequest):
    try:
        from backend import db
        success = db.save_diary(
            diary_date=req.diary_date,
            raw_input=req.raw_input,
            structured_content=req.structured_content
        )
        if success:
            return {"status": "success", "message": f"Diary for {req.diary_date} saved successfully."}
        else:
            raise HTTPException(status_code=500, detail="Database save failed.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save diary: {str(e)}")

@app.delete("/api/diaries/{date}")
def delete_investment_diary(date: str):
    try:
        from backend import db
        success = db.delete_diary(date)
        if success:
            return {"status": "success", "message": f"Diary for {date} deleted successfully."}
        else:
            raise HTTPException(status_code=404, detail=f"Diary for {date} not found or failed to delete.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete diary: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
