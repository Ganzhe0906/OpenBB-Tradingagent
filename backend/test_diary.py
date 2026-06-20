import os
import sys

# Ensure backend folder is in path
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, save_diary, get_diary, list_diaries, delete_diary

def run_tests():
    print("Initializing database...")
    init_db()
    
    date_str = "2026-06-07"
    raw_input = "今天我要投资韩国股市，因为KOSPI指数在左侧具有极强的估值优势。我买入了100股KOSPI ETF。同时我也持有一些美股科技股，比如苹果，今天苹果公布了新的AI策略，我觉得非常具有确定性，但目前估值不便宜，所以继续持有不动。"
    structured = """[
        {"subject": "韩国股市投资", "considerations": "KOSPI指数在左侧具有极强的估值优势", "operations": "买入100股KOSPI ETF", "ai_feedback": "韩元持续疲软对KOSPI略有压制，但左侧安全边际较厚。", "observations": "关注外资买入额度及韩元企稳信号"},
        {"subject": "美股科技股 (苹果)", "considerations": "苹果公布新AI策略确定性强但估值不便宜", "operations": "继续持有不动", "ai_feedback": "AI功能升级有望提振换机潮，需关注是否已price in。", "observations": "观察换机销售数据与下季度指引"}
    ]"""
    
    print("\n--- Test 1: Saving a diary entry ---")
    success = save_diary(date_str, raw_input, structured)
    print(f"Save successful: {success}")
    
    print("\n--- Test 2: Getting the diary entry ---")
    entry = get_diary(date_str)
    if entry:
        print("Diary retrieved successfully!")
        print(f"Date: {entry['diary_date']}")
        print(f"Raw Input: {entry['raw_input']}")
        print(f"Structured: {entry['structured_content']}")
    else:
        print("Failed to retrieve diary entry!")
        
    print("\n--- Test 3: Listing diary entries ---")
    diaries = list_diaries()
    print(f"Total entries in list: {len(diaries)}")
    for d in diaries:
        print(f"- Date: {d['diary_date']}, Raw length: {len(d['raw_input'])}")
        
    print("\n--- Test 4: Deleting test entry ---")
    del_success = delete_diary(date_str)
    print(f"Delete successful: {del_success}")
    
    entry_after_del = get_diary(date_str)
    print(f"Retrieve after delete (should be None): {entry_after_del}")

if __name__ == "__main__":
    run_tests()
