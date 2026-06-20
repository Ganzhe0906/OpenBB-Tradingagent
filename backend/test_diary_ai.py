import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure backend folder is in path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

from ai_analyzer import generate_structured_diary

async def run_ai_test():
    print("Testing AI structured diary generation...")
    print(f"DEEPSEEK_API_KEY set: {bool(os.getenv('DEEPSEEK_API_KEY'))}")
    print(f"TRADINGAGENTS_DIARY_LLM: {os.getenv('TRADINGAGENTS_DIARY_LLM', 'deepseek-v4-flash')}")
    
    raw_input = (
        "今天英伟达大涨，因为它的财报完全击碎了看空机构的质疑，我决定继续持有我的半导体底仓。 "
        "另外我昨天把手里所有的韩国KOSPI指数基金全部清仓了，因为我觉得韩国宏观面临外资出逃的风险，并且韩元汇率贬值压力实在太大。"
    )
    
    print("\n--- Sending request to AI (First Generation) ---")
    result = await generate_structured_diary(raw_input, "2026-06-07")
    
    print(f"Result Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data')
        print("Successfully generated segments:")
        for idx, seg in enumerate(data):
            print(f"\n[Segment {idx+1}] Subject: {seg.get('subject')}")
            print(f"Considerations: {seg.get('considerations')}")
            print(f"Operations: {seg.get('operations')}")
            print(f"AI Feedback: {seg.get('ai_feedback')[:100]}...")
            print(f"Observations: {seg.get('observations')}")
            
        # Let's test regeneration (Revision)
        previous_structured = result.get('data')
        suggestion = "把关于英伟达的部分，AI反馈写得更加关注估值泡沫一些，提醒我注意半导体的估值高位风险。"
        
        print("\n--- Sending request to AI (Regeneration with Suggestion) ---")
        regen_result = await generate_structured_diary(
            raw_input=raw_input,
            diary_date="2026-06-07",
            suggestion=suggestion,
            previous_structured_content=str(previous_structured)
        )
        
        print(f"Regen Status: {regen_result.get('status')}")
        if regen_result.get('status') == 'success':
            print("Successfully regenerated segments:")
            for idx, seg in enumerate(regen_result.get('data')):
                print(f"\n[Regen Segment {idx+1}] Subject: {seg.get('subject')}")
                print(f"Considerations: {seg.get('considerations')}")
                print(f"Operations: {seg.get('operations')}")
                print(f"AI Feedback: {seg.get('ai_feedback')}")
                print(f"Observations: {seg.get('observations')}")
        else:
            print(f"Regen failed: {regen_result.get('message')}")
            print(f"Raw response: {regen_result.get('raw_response')}")
    else:
        print(f"First generation failed: {result.get('message')}")
        print(f"Raw response: {result.get('raw_response')}")

if __name__ == "__main__":
    asyncio.run(run_ai_test())
