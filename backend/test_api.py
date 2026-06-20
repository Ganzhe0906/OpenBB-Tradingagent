import os
import sys
from dotenv import load_dotenv

# Load backend/.env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Loading env from: {dotenv_path}")
load_dotenv(dotenv_path)

# Verify keys are loaded
print("DEEPSEEK_API_KEY:", "Present" if os.getenv("DEEPSEEK_API_KEY") else "Missing")
print("LLM Provider:", os.getenv("TRADINGAGENTS_LLM_PROVIDER"))
print("Deep Think LLM:", os.getenv("TRADINGAGENTS_DEEP_THINK_LLM"))

# Add TradingAgents to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "TradingAgents")))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}

print("Initializing graph...")
ta = TradingAgentsGraph(debug=True, config=config)
print("Propagating for AAPL on 2026-06-05...")
state, decision = ta.propagate("AAPL", "2026-06-05")
print("\n--- DECISION ---")
print(decision)
