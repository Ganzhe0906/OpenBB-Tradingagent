import os
import json
import httpx
from typing import Optional, List

def parse_json_safely(text: str):
    """Clean markdown backticks if present and parse text into JSON safely."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing JSON from LLM: {e}. Raw text was: {text}")
        return None

async def call_deepseek(prompt: str, system_prompt: str = "You are a professional financial assistant.", model: Optional[str] = None) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "错误：未在环境变量中配置 DEEPSEEK_API_KEY。"
        
    if not model:
        model = os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", "deepseek-chat")
        
    # Support custom API base endpoint (e.g. for proxy providers hosting deepseek-v4-flash)
    base_url = os.getenv("DEEPSEEK_API_BASE") or "https://api.deepseek.com/chat/completions"
    if not base_url.endswith("/chat/completions") and not base_url.endswith("/completions"):
        base_url = base_url.rstrip("/") + "/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(base_url, json=payload, headers=headers)
            
            # If the model is not found or unsupported (e.g. if deepseek-v4-pro is sent to deepseek.com directly),
            # fall back to the standard 'deepseek-chat' (DeepSeek-V3)
            if response.status_code == 404 or (response.status_code == 400 and "model" in response.text):
                # Fallback only if we used the default think model on official base URL
                if "api.deepseek.com" in base_url and model != "deepseek-chat":
                    payload["model"] = "deepseek-chat"
                    response = await client.post(base_url, json=payload, headers=headers)
                
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"调用 DeepSeek API 发生异常: {str(e)}"

async def score_and_classify_news_batch(news_items: list) -> list:
    """
    Given a list of raw news items, calls the LLM in a single batch to:
    1. Score each item (0 to 100) based on its significance for financial markets and macro trading.
    2. Classify each item into one of the key asset categories:
       MACRO, US_STOCKS, US_BONDS, COMMODITIES, CN_STOCKS, EM_CRYPTO, OTHER.
    """
    if not news_items:
        return []
        
    batch_data = []
    for item in news_items:
        batch_data.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "content": item.get("content")
        })
        
    system_prompt = (
        "你是一个顶尖的全球宏观量化策略分析师。你的任务是对一组金融新闻（快讯）进行【重要度评分】和【资产类别分类】。\n\n"
        "【重要度评分标准 (0-100)】:\n"
        "- 90-100: 极度重要。对全球或大国市场有决定性影响（如：中央银行超预期利率决议、地缘战争冲突爆发、系统性金融危机、重大宏观经济数据超预期断崖式偏离）。\n"
        "- 70-89: 重要。会对大盘或主要板块带来中短期剧烈波动（如：行业标杆企业财报超预期、监管政策重大变动、主要地缘局势恶化、关键商品大幅暴涨暴跌）。\n"
        "- 50-69: 一般。对个别板块或特定标的有局部影响，对整体宏观影响微弱（如：普通企业动态、例行行业数据发布、常规市场价格波澜）。\n"
        "- 0-49: 忽略。琐碎信息、日常噪音、非金融关联或与交易定价无直接关联的新闻。\n\n"
        "【资产类别分类 (Asset Category)】:\n"
        "- MACRO: 系统与全球宏观（央行决策、宏观数据、主权信用等）\n"
        "- US_STOCKS: 美股板块（美股个股、大盘指数、大型科技巨头等）\n"
        "- CN_STOCKS: 中国资产（A股、港股、中概股、中国宏观政策等）\n"
        "- US_BONDS: 美债与利率（国债收益率走势、美债发行、联邦基金利率等）\n"
        "- COMMODITIES: 大宗与黄金（原油、黄金、基本金属、农副产品等商品动态）\n"
        "- EM_CRYPTO: 加密与新兴（加密货币、Web3监管、新兴边缘市场）\n"
        "- OTHER: 地缘与前沿（常规政治外交、无直接金融冲击的自然灾害、常规地缘摩擦等）\n\n"
        "【严格输出格式要求】\n"
        "请务必输出一个合法的 JSON 数组，格式如下，绝对不要包含任何 markdown 标记、缩进、首尾前言或任何解释性文字：\n"
        '[{"id": "xxx", "score": 85, "category": "MACRO"}, ...]'
    )
    
    prompt = f"以下是需要分析的新闻列表（JSON 格式）：\n{json.dumps(batch_data, ensure_ascii=False)}"
    response_text = await call_deepseek(prompt, system_prompt)
    
    scored_results = parse_json_safely(response_text)
    if not scored_results or not isinstance(scored_results, list):
        # Fallback if LLM fails or formats incorrectly
        return [{"id": item.get("id"), "score": 50, "category": "OTHER"} for item in news_items]
        
    return scored_results

async def analyze_top_five(news_items: list, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Extract and summarize the top 5 most important news items with institutional grade macro prompts."""
    if not news_items:
        return "在选定的时间范围内没有找到可供分析的快讯。"
        
    slim_news = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "content": item.get("content"),
            "pub_date": item.get("pub_date"),
            "is_red": item.get("is_red"),
            "importance_score": item.get("importance_score", 50),
            "asset_category": item.get("asset_category", "OTHER")
        }
        for item in news_items
    ]
    
    time_context = ""
    if start_time or end_time:
        time_context = f"\n【本次报告时间范围】: {start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)"
        
    system_prompt = (
        "你是一位服务于全球顶级宏观对冲基金的首席策略师兼首席风险控制官。你的任务是从所提供的快讯列表中，"
        "自主分析并研判【对全球大宗资产定价、宏观流动性以及系统性风险最具决定性影响的 Top 5 新闻】。\n\n"
        "【特别要求：报告适用时段与市场状态】\n"
        "在报告开头，必须明确分析并输出本时段的交易市场所处状态与核心背景。请利用你的专业知识结合传入的时间区间（北京时间）：\n"
        "1. 判定在此期间，全球主要市场（如美股、A股/港股、欧洲股市、亚太股市）的开盘与交易状态。例如：是处于美股盘中交易、A股收盘后消息消化、亚太盘前等待开盘，还是处于周末双休全球停盘阶段。\n"
        "2. 提取并指出该时段内市场经历了什么，或正在观望、等待什么重大宏观事件（如：美国CPI数据发布前夜、非农数据落地后的情绪踩踏、欧央行利率决议盘中、地缘冲突突发等）。\n"
        "请将这部分内容严格编排在报告最开始的【报告适用时段与市场状态】模块中。\n\n"
        "【严格研判筛选原则】\n"
        "1. 独立打分与分类：列表中的 `importance_score` 与 `asset_category` 均为存盘默认值，不可参考！你必须对提供的新闻内容进行自主独立评估，判断其对大类资产的定价重要度（给出 0-100 的重要性得分）以及资产类别分类（MACRO, US_STOCKS, CN_STOCKS, US_BONDS, COMMODITIES, EM_CRYPTO, OTHER之一）。\n"
        "   - [90-100] 极度重要：影响全球/大国宏观底座（如主权信用风险、央行超预期基准决议、核心经济指标断崖式偏离、战争爆发）。\n"
        "   - [70-89] 重要：对主要资产板块定价产生中期趋势重估（如重大行业监管转向、标杆财报严重偏离预期、关键商品供应链冲击）。\n"
        "   - [50-69] 一般：局部/个股效应，对宏观流动性及跨资产无传染性。\n"
        "   - [0-49] 忽略：日常杂音、微弱波动、非交易定价关联信息。\n"
        "2. 宁缺毋滥：只有自评得分 >= 70 的新闻才具备入选资格。若达到此标准的快讯不足 5 条，则仅输出符合条件的几条（哪怕只有 1-2 条）；若全无重要消息，请直接简短回复：‘当前时间段内未发生具有重大市场影响力的宏观要闻。’严禁塞入平庸的日常噪音凑数！\n"
        "3. 预期差研判：核心资产定价的本质是‘预期差（Out-of-Expectation）’的重估。请重点解剖事件中‘市场共识’与‘实际发生’之间的偏离程度，避免对已完全 Price-in（被市场消化）的常规事件进行无意义的复述。\n"
        "4. 专业传导深度：请彻底抛弃泛泛而谈的陈述。分析必须体现极高的金融专业度，重点解剖流动性传导路径（包括主权国债收益率曲线、汇率锚、主要指数隐含波动率 VIX、大宗商品供给侧溢价、或特定板块估值折扣的边际改变量化分析）。\n\n"
        "【输出格式要求】\n"
        "请直接以结构化且排版精美的 Markdown 形式输出，不需包含任何前置引言或结束问候。格式如下：\n"
        "### 🕒 报告适用时段与市场状态\n"
        f"- **适用时间**：{start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)\n"
        "- **开盘状态**：[详细说明该时间段内各市场的开盘/交易/收盘状态]\n"
        "- **经历核心事件**：[精炼描述该时段内全球市场经历了什么重要事件或政策消息]\n\n"
        "---\n\n"
        "### 📌 **[序号]. [加粗新闻核心定价标题]** (发布时间: YYYY-MM-DD HH:MM | 自评类别: [类别] | 自评得分: [评分])\n"
        "- **核心事实与宏观背景**: 精炼叙述事件起因，并重点剖析超出市场预期（Out-of-Expectation）的核心矛盾点与预期差重估定位。\n"
        "- **传导链条与波动传导**: 详细推导该事件如何通过资产负债表、流动性乘数、估值折价、信用利差、或套利资金流向作用于各大资产类别（如美股成长股、新兴市场、美债长端、贵金属等）。\n"
        "- **交易启示与左侧防御**: 给出具体的战术应对（如：等待利率筑顶的买事实机会、缩短久期避险、特定估值承压板块的左侧博弈窗口）。"
    )
    
    prompt = f"以下是该时间段内的新闻快讯列表（JSON 格式）：{time_context}\n{json.dumps(slim_news, ensure_ascii=False)}"
    return await call_deepseek(prompt, system_prompt)

async def analyze_extreme_movements(news_items: list, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Analyze if there are any extreme market anomalies or events."""
    if not news_items:
        return "在选定的时间范围内没有找到可供分析的快讯。"
        
    slim_news = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "content": item.get("content"),
            "pub_date": item.get("pub_date"),
            "is_red": item.get("is_red"),
            "importance_score": item.get("importance_score", 50),
            "asset_category": item.get("asset_category", "OTHER")
        }
        for item in news_items
    ]
    
    time_context = ""
    if start_time or end_time:
        time_context = f"\n【本次报告时间范围】: {start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)"
        
    system_prompt = (
        "你是一位服务于全球顶级宏观对自动对冲基金的量化风险总监兼跨资产策略师。请仔细审阅提供的新闻列表，"
        "深度评估过去这段时间内，全球金融市场是否发生了任何【异常偏离或极端行情/方向性冲击事件】"
        "（即：显著超出市场基准预期、破坏均值回归轨道、触发市场微观结构巨震或多空方向失衡的异常事件）。\n\n"
        "【特别要求：报告适用时段与市场状态】\n"
        "在报告开头，必须明确分析并输出本时段的交易市场所处状态与核心背景。请利用你的专业知识结合传入的时间区间（北京时间）：\n"
        "1. 判定在此期间，全球主要市场（如美股、A股/港股、欧洲股市、亚太股市）的开盘与交易状态。例如：是处于美股盘中交易、A股收盘后消息消化、亚太盘前等待开盘，还是处于周末双休全球停盘阶段。\n"
        "2. 提取并指出该时段内市场经历了什么，或正在观望、等待什么重大宏观事件（如：美国CPI数据发布前夜、非农数据落地后的情绪踩踏、欧央行利率决议盘中、地缘冲突突发等）。\n"
        "请将这部分内容严格编排在报告最开始的【报告适用时段与市场状态】模块中。\n\n"
        "【极端行情的判定维度（双向覆盖）】\n"
        "1. 下行异常/系统性风险：主权/企业债务爆雷、突发流动性枯竭（Basis Spread拉宽）、金融机构挤兑、市场资产闪崩、跨市场系统性强制平仓（Margin Call）连锁反应。\n"
        "2. 上行异常/空头踩踏：核心资产/单边市场指数大幅暴涨（如主要国家基准指数单日大涨或飙升超3%-5%、触发熔断/Circuit Breakers机制）、历史性空头挤压（Short Squeeze）、大宗商品多头逼仓（Short Corner）等。\n"
        "3. 政策与结构突变：非预期的央行紧急降息/加息、汇率脱钩（Peg Breaking）、政府紧急资本管制或历史性干预市场政策颁布。\n\n"
        "【硬性纪律约束】\n"
        "1. 严格过滤噪音：若所提供的快讯列表中仅包含常规的正态分布内涨跌（如普通板块1%-2%的跟随性波动，且无重大政策基准逆转），【务必】输出以下格式，说明未观测到极端事件，绝对不允许强行拼凑常规波动以充当极端行情：\n"
        "### 🕒 报告适用时段与市场状态\n"
        f"- **适用时间**：{start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)\n"
        "- **开盘状态**：[详细说明该时间段内各市场的开盘/交易/收盘状态]\n"
        "- **经历核心事件**：[精炼描述该时段内全球市场经历了什么重要事件或政策消息]\n\n"
        "---\n\n"
        "经评估，当前时间段内市场主要资产波动处于常规正态分布区间内，未观测到显著偏离基准的极端上行或下行事件。\n\n"
        "2. 深度结构化推演：如果识别出符合标准的极端行情，请以专业严谨的 Markdown 报告形式输出。必须详细罗列该异常行情（需指出具体数据，如涨跌幅、熔断情况等），并深度剖析其跨市场风险传染链条（如流动性乘数收缩、溢价重新定价、汇率贬值传导或资产负债表受损渠道）。格式如下：\n"
        "### 🕒 报告适用时段与市场状态\n"
        f"- **适用时间**：{start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)\n"
        "- **开盘状态**：[详细说明该时间段内各市场的开盘/交易/收盘状态]\n"
        "- **经历核心事件**：[精炼描述该时间段内全球市场经历了什么重要事件或政策消息]\n\n"
        "---\n\n"
        "### 🚨 极端行情/异常事件研判报告\n"
        "[此处编写具体的分析、异常资产、影响数据及传导链条分析]"
    )
    
    prompt = f"以下是该时间段内的新闻快讯列表（JSON 格式）：{time_context}\n{json.dumps(slim_news, ensure_ascii=False)}"
    return await call_deepseek(prompt, system_prompt)

async def analyze_custom_query(news_items: list, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Answer a custom query based on the news items in the selected time range."""
    if not news_items:
        return "在选定的时间范围内没有找到可供分析的快讯，无法回答自定义提问。"
        
    slim_news = [
        {
            "title": item.get("title"),
            "content": item.get("content"),
            "pub_date": item.get("pub_date"),
            "importance_score": item.get("importance_score", 50),
            "asset_category": item.get("asset_category", "OTHER")
        }
        for item in news_items
    ]
    
    time_context = ""
    if start_time or end_time:
        time_context = f"\n【本次报告时间范围】: {start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)"
        
    system_prompt = (
        "你是一位顶尖的全球宏观量化策略研究员。请结合所提供时间范围内的快讯上下文，"
        "精准地、客观地回答用户提出的提问。\n\n"
        "【特别要求：报告适用时段与市场状态】\n"
        "在回答的开头，必须明确分析并输出本时段的交易市场所处状态与核心背景。请利用你的专业知识结合传入的时间区间（北京时间）：\n"
        "1. 判定在此期间，全球主要市场（如美股、A股/港股、欧洲股市、亚太股市）的开盘与交易状态。例如：是处于美股盘中交易、A股收盘后消息消化、亚太盘前等待开盘，还是处于周末双休全球停盘阶段。\n"
        "2. 提取并指出该时段内市场经历了什么，或正在观望、等待什么重大宏观事件（如：美国CPI数据发布前夜、非农数据落地后的情绪踩踏、欧央行利率决议盘中、地缘冲突突发等）。\n"
        "请将这部分内容严格编排在回答最开始的【报告适用时段与市场状态】模块中，之后再开始作答。\n\n"
        "【执纪要求】\n"
        "1. 严禁无中生有！只能根据快讯中明确提及的信息进行回答，不可强行加入快讯中没有提到的宏观数据或市场事实。\n"
        "2. 如果所提供的新闻上下文不足以支撑全面回答用户的问题，请明确而诚实地告知用户：'根据当前时间范围内的快讯数据，无法完整回答此问题，缺失相关事实。' 并指明已知的边缘线索。\n\n"
        "【输出格式要求】\n"
        "请以结构化且排版精美的 Markdown 形式输出：\n"
        "### 🕒 报告适用时段与市场状态\n"
        f"- **适用时间**：{start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)\n"
        "- **开盘状态**：[详细说明该时间段内各市场的开盘/交易/收盘状态]\n"
        "- **经历核心事件**：[精炼描述该时段内全球市场经历了什么重要事件或政策消息]\n\n"
        "---\n\n"
        "### 💬 针对用户提问的专业研判\n"
        "[此处详细回答用户的提问内容]"
    )
    
    prompt = (
        f"【新闻快讯上下文 (JSON)】:{time_context}\n{json.dumps(slim_news, ensure_ascii=False)}\n\n"
        f"【用户提问】: {query}"
    )
    return await call_deepseek(prompt, system_prompt)

async def generate_structured_diary(
    raw_input: str,
    diary_date: str,
    suggestion: Optional[str] = None,
    previous_structured_content: Optional[str] = None
) -> dict:
    """
    Calls DeepSeek with the cheap model 'deepseek-v4-flash' to structure raw diary entries.
    If suggestion is provided, regenerates/refines the previous structured content.
    Returns a dict with status ('success' or 'error') and data (list of structured objects).
    """
    # 1. System Prompt
    system_prompt = (
        "你是一个顶尖的全球宏观与多资产配置交易助理。你的任务是分析用户乱序输入的个人投资思考与操作日志，"
        "【自动按不同的投资动作/领域/标的（例如“韩国股市”、“美股芯片股”）拆分成多个独立的模块】。\n\n"
        "每个模块提取并包含以下五个关键属性：\n"
        "1. `subject`: 投资动作/领域/标的名称（如：韩国股市投资、美股半导体，需简练醒目）\n"
        "2. `considerations`: 该动作的建模思考、背景及投资逻辑（提取用户所写，若无则根据输入合理提炼）\n"
        "3. `operations`: 实际操作细节（提取用户动作）\n"
        "4. `ai_feedback`: 针对该领域的 AI 反馈、判断力与专业研判（由你基于当前全球宏观环境和交易理论自主生成，必须有深度、专业，指出潜在机会或风险点）\n"
        "5. `observations`: 后续关注重点、点评与观察指标（例如对核心汇率、Fred 数据、某核心财报或价格支撑位的观察）\n\n"
        "【输出格式要求】\n"
        "请务必输出一个合法的 JSON 数组，绝对不要包含任何 markdown 标记、缩进、首尾前言或任何解释性文字。\n"
        "如果未能识别出任何具体的投资动作，也要把整篇日记作为单个主题（如“综合投资分析”）并提取结构。格式如下：\n"
        '[{"subject": "...", "considerations": "...", "operations": "...", "ai_feedback": "...", "observations": "..."}, ...]'
    )

    # 2. Craft the user prompt
    if suggestion and previous_structured_content:
        prompt = (
            f"日期: {diary_date}\n"
            f"原始输入文本:\n{raw_input}\n\n"
            f"前一次生成的结构化日记内容:\n{previous_structured_content}\n\n"
            f"用户的不满意点/修改建议:\n{suggestion}\n\n"
            "请结合用户的修改建议对原有结构化日记内容进行调整、修改和重构。确保输出格式仍为相同的 JSON 数组，不带任何 Markdown 包裹标记。"
        )
    else:
        prompt = (
            f"日期: {diary_date}\n"
            f"用户输入的原始混合文本:\n{raw_input}\n\n"
            "请识别其中不同的投资领域或动作，并将其整理为结构化的 JSON 数组。"
        )

    # 3. Call DeepSeek with the cheap model "deepseek-v4-flash"
    # We allow the user to override this model name via environment variable TRADINGAGENTS_DIARY_LLM
    diary_model = os.getenv("TRADINGAGENTS_DIARY_LLM", "deepseek-v4-flash")
    
    response_text = await call_deepseek(prompt, system_prompt=system_prompt, model=diary_model)
    
    # Clean and parse JSON
    parsed = parse_json_safely(response_text)
    if not parsed or not isinstance(parsed, list):
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()
            try:
                parsed = json.loads(cleaned_text)
            except Exception:
                pass
                
    if parsed and isinstance(parsed, list):
        return {"status": "success", "data": parsed}
    else:
        fallback_data = [
            {
                "subject": "综合投资分析",
                "considerations": "解析 AI 结果失败，请查看原始内容。",
                "operations": "无",
                "ai_feedback": f"AI 原始响应如下：\n{response_text}",
                "observations": "无"
            }
        ]
        return {"status": "error", "message": "AI 返回格式解析失败", "data": fallback_data, "raw_response": response_text}

async def analyze_global_assets(news_items: list, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Classify and summarize news items into major global asset classes."""
    if not news_items:
        return "在选定的时间范围内没有找到可供分析的快讯。"
        
    slim_news = [
        {
            "title": item.get("title"),
            "content": item.get("content"),
            "pub_date": item.get("pub_date"),
            "importance_score": item.get("importance_score", 50),
            "asset_category": item.get("asset_category", "OTHER")
        }
        for item in news_items
    ]
    
    time_context = ""
    if start_time or end_time:
        time_context = f"\n【本次报告时间范围】: {start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)"
        
    system_prompt = (
        "你是一位服务于全球顶级宏观对冲基金的全球宏观多资产交易台分析师（Global Macro Multi-Asset Desk Analyst）。\n"
        "你的任务是根据提供的新闻列表以及时间范围，按照主要大类资产板块进行精确过滤与专业归类，形成一份简明、高信息密度的【全球资产波动简报】。\n\n"
        "【特别要求：报告适用时段与市场状态】\n"
        "在报告开头，必须明确分析并输出本时段的交易市场所处状态与核心背景。请利用你的专业知识结合传入的时间区间（北京时间）：\n"
        "1. 判定在此期间，全球主要市场（如美股、A股/港股、欧洲股市、亚太股市）的开盘与交易状态。例如：是处于美股盘中交易、A股收盘后消息消化、亚太盘前等待开盘，还是处于周末双休全球停盘阶段。\n"
        "2. 提取并指出该时段内市场经历了什么，或正在观望、等待什么重大宏观事件（如：美国CPI数据发布前夜、非农数据落地后的情绪踩踏、欧央行利率决议盘中、地缘冲突突发等）。\n"
        "请将这部分内容严格编排在报告最开始的【报告适用时段与市场状态】模块中。\n\n"
        "【资产归类与汇报要求】\n"
        "请将快讯内容精炼后整理到以下五个核心板块中（若某板块在快讯中没有任何相关动态，请【务必】写：*该时段内无显著公开市场动态。*，绝对不要无中生有凭空捏造）：\n"
        "1. **中国资产 (A股/港股/中概股/中国宏观)**: 汇集中国宏观政策、A股/港股大盘指数波动、中概股重要动态等。\n"
        "2. **美股市场 (标普/纳指/美股个股/大型科技股)**: 汇集美国三大股指、美股龙头企业财报、美股个股异动等。\n"
        "3. **日韩及欧洲股市 (日经225/韩国KOSPI/欧洲主要指数)**: 汇集亚太及欧洲核心市场波动、当地货币政策与地缘冲击等。\n"
        "4. **大宗商品与期货 (原油/黄金/白银/基本金属等)**: 汇集国际油价、金银价格震荡、大宗供给冲击及关键期约交割情况。\n"
        "5. **加密货币 (比特币/以太坊/加密监管)**: 汇集加密货币资产价格异动、重要链上异动及主权国家对于加密资产的监管政策等。\n\n"
        "【专业撰写要求】\n"
        "- **言简意赅，逻辑严密**：抛弃繁琐多余的背景叙述，直接给出“事件+边际影响”；\n"
        "- **体现专业投研思维**：多使用专业金融术语（如：再通胀、流动性折价、贝塔系数、避险溢价、基差套利等）；\n"
        "- **禁止生拉硬扯**：只根据快讯中真实出现的市场异动或数据公告进行汇总，保持客观求实。\n\n"
        "【输出格式要求】\n"
        "请直接以结构化且排版精美的 Markdown 形式输出，不需包含任何前置引言或结束问候。格式如下：\n"
        "## 🌐 全球多资产波动简报\n\n"
        "### 🕒 报告适用时段与市场状态\n"
        f"- **适用时间**：{start_time or '未指定'} 至 {end_time or '未指定'} (北京时间)\n"
        "- **开盘状态**：[详细说明该时间段内各市场的开盘/交易/收盘状态]\n"
        "- **经历核心事件**：[精炼描述该时段内全球市场经历了什么重要事件或政策消息]\n\n"
        "---\n\n"
        "### 🇨🇳 1. 中国资产 (A股/港股/中概股/中国宏观)\n"
        "- [简明要点1]: 阐述事实及价格传导边际影响。\n"
        "- [简明要点2]...\n\n"
        "### 🇺🇸 2. 美股市场 (标普/纳指/美股个股/大型科技股)\n"
        "- ...\n\n"
        "### 🇯🇵🇰🇷🇪🇺 3. 日韩及欧洲股市 (日经225/韩国KOSPI/欧洲主要指数)\n"
        "- ...\n\n"
        "### 🛢️🪙 4. 大宗商品与期货 (原油/黄金/白银/基本金属等)\n"
        "- ...\n\n"
        "### 🪙 5. 加密货币 (比特币/以太坊/加密监管)\n"
        "- ..."
    )
    
    prompt = f"以下是该时间段内的快讯列表（JSON 格式）：{time_context}\n{json.dumps(slim_news, ensure_ascii=False)}"
    return await call_deepseek(prompt, system_prompt)
