import os
import sys
import json
import asyncio
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Mock heavy math libraries to prevent source compilation/import issues on Python 3.14
from unittest.mock import MagicMock
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.optimize'] = MagicMock()
sys.modules['scipy.stats'] = MagicMock()

sys.modules['statsmodels'] = MagicMock()
sys.modules['statsmodels.tsa'] = MagicMock()
sys.modules['statsmodels.tsa.stattools'] = MagicMock()
sys.modules['statsmodels.tsa.seasonal'] = MagicMock()
sys.modules['statsmodels.tsa.holtwinters'] = MagicMock()
sys.modules['statsmodels.tsa.arima'] = MagicMock()
sys.modules['statsmodels.tsa.arima.model'] = MagicMock()

sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.linear_model'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()

sys.modules['seaborn'] = MagicMock()

# Ensure we can load dotenv
load_dotenv()

# We need to add the FinClaw project path to sys.path to ensure we can import it
FINCLAW_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FinClaw"))
if FINCLAW_PATH not in sys.path:
    sys.path.insert(0, FINCLAW_PATH)

def initialize_finclaw_config():
    """
    Initializes or updates ~/.finclaw/config.json with keys from backend/.env.
    """
    # 1. Resolve API Keys from environment
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    fred_api_key = os.getenv("FRED_API_KEY")

    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing from environment variables.")

    # 2. Get ~/.finclaw/config.json path
    config_dir = Path.home() / ".finclaw"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    # 3. Define the workspace path inside our project folder
    project_workspace = Path(__file__).resolve().parent.parent / "cache" / "finclaw_workspace"
    project_workspace.mkdir(parents=True, exist_ok=True)

    # 4. Load existing config or build default
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Failed to read existing config: {e}. Rewriting with default.")

    # 5. Populate keys programmatically using camelCase formatting
    if "agents" not in config_data:
        config_data["agents"] = {}
    if "defaults" not in config_data["agents"]:
        config_data["agents"]["defaults"] = {}
    
    config_data["agents"]["defaults"]["model"] = "deepseek/deepseek-v4-pro"
    config_data["agents"]["defaults"]["workspace"] = str(project_workspace)
    config_data["agents"]["defaults"]["maxToolIterations"] = 20

    if "providers" not in config_data:
        config_data["providers"] = {}
    if "deepseek" not in config_data["providers"]:
        config_data["providers"]["deepseek"] = {}
    config_data["providers"]["deepseek"]["apiKey"] = deepseek_api_key

    if "tools" not in config_data:
        config_data["tools"] = {}
    if "web" not in config_data["tools"]:
        config_data["tools"]["web"] = {}
    if "search" not in config_data["tools"]["web"]:
        config_data["tools"]["web"]["search"] = {}
    config_data["tools"]["web"]["search"]["provider"] = "tavily"
    config_data["tools"]["web"]["search"]["apiKey"] = tavily_api_key

    if "financial" not in config_data["tools"]:
        config_data["tools"]["financial"] = {}
    config_data["tools"]["financial"]["fredApiKey"] = fred_api_key

    config_data["tools"]["restrictToWorkspace"] = False

    # 6. Save configuration
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    print(f"FinClaw configuration initialized/updated at {config_file}")

    # 7. Initialize/Onboard workspace files programmatically
    try:
        from finclaw.cli.commands import _create_workspace_templates
        _create_workspace_templates(project_workspace, force=False)
        print(f"FinClaw workspace templates initialized at {project_workspace}")
    except Exception as e:
        print(f"Failed to initialize templates via python import: {e}. We will proceed.")

async def run_finclaw_macro_analysis(prompt: str, log_callback: callable) -> str:
    """
    Runs FinClaw agent loop in-process with a specific prompt, capturing logs via loguru.
    """
    initialize_finclaw_config()

    from finclaw.config.loader import load_config
    from finclaw.bus.queue import MessageBus
    from finclaw.agent.loop import AgentLoop
    from finclaw.cli.commands import _make_provider, _make_inner_provider

    config = load_config()
    bus = MessageBus()
    provider = _make_provider(config)
    inner_provider = _make_inner_provider(config)

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        inner_model=config.agents.defaults.inner_model,
        inner_provider=inner_provider,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        search_api_key=config.tools.web.search.api_key or None,
        search_provider=config.tools.web.search.provider,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
    )

    # Add loguru sink to capture logs and pass them to log_callback
    sink_id = logger.add(
        lambda msg: log_callback(msg.record["message"]),
        format="{message}",
        level="INFO",
        filter=lambda record: "finclaw" in record["name"] or record["name"] == "root"
    )

    try:
        log_callback(f"[系统] 启动 FinClaw 宏观研判引擎，配置就绪...")
        # Run process_direct to run the loop with the prompt
        response = await agent_loop.process_direct(prompt, session_key="macro_analysis_session")
        return response
    finally:
        logger.remove(sink_id)
        await agent_loop.close_mcp()

if __name__ == "__main__":
    # Test initialization
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    initialize_finclaw_config()
