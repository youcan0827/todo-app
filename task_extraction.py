#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
import json
from typing import Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

def extract_task_details_with_llm(task_description: str) -> Tuple[str, str]:
    """LLMを使ってタスク名と時間情報を正確に抽出"""
    
    try:
        llm = ChatOpenAI(
            temperature=0.3,
            model="openai/gpt-3.5-turbo", 
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        extraction_prompt = f"""
以下の文章からタスク名と時間情報を抽出してください。

文章: "{task_description}"

以下のJSON形式で回答してください:
{{
    "task_name": "純粋なタスク名・イベント名のみ",
    "time_info": "日時・時間情報（具体的に抽出）"
}}

抽出ルール:
- task_name: 余計な文言（「Google」「追加してほしい」「という予定を」等）は除去
- time_info: 「明日13時-14時」のように具体的に

例:
「明日までにレポートを書く」→ {{"task_name": "レポートを書く", "time_info": "明日まで"}}
「Google明日の13時から14時までMTGという予定を追加してほしい」→ {{"task_name": "MTG", "time_info": "明日13時-14時"}}
「来週の火曜日15時から会議をカレンダーに入れて」→ {{"task_name": "会議", "time_info": "来週火曜日15時"}}
「12月25日の17時からパーティー」→ {{"task_name": "パーティー", "time_info": "12月25日17時"}}

JSON形式のみで回答:
"""
        
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        
        try:
            result = json.loads(response.content.strip())
            if 'task_name' in result and 'time_info' in result:
                task_name = result['task_name'].strip()
                time_info = result['time_info'].strip()
                
                # 空の場合は元の文章を使用
                if not task_name:
                    task_name = task_description
                
                return task_name, time_info
                
        except json.JSONDecodeError:
            pass
            
    except Exception as e:
        print(f"LLMタスク抽出エラー: {e}")
    
    # LLM失敗時はフォールバック
    return fallback_task_extraction(task_description)


def fallback_task_extraction(task_description: str) -> Tuple[str, str]:
    """フォールバック用タスク抽出（文字列処理）"""
    
    task_name = task_description
    time_info = ""
    
    # 時間情報を先に抽出
    time_patterns = [
        r'明日.*?(\d{1,2}時.*?\d{1,2}時)',
        r'(\d{1,2}時.*?から.*?\d{1,2}時)',
        r'(明日|今日|来週|再来週|来月)',
        r'(\d{1,2}月\d{1,2}日)',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, task_description)
        if match:
            time_info = match.group(1) if match.groups() else match.group(0)
            break
    
    # カレンダー関連表現をクリーンに
    clean_expressions = [
        "Google", "をカレンダーに追加", "をスケジュールに入れる", "を予定に入れる",
        "カレンダーに", "スケジュールに", "予定に", "してほしい", "という予定を追加",
        "を入れておいて", "と入れておいて", "googleカレンダーに", "Googleカレンダーに"
    ]
    
    for expr in clean_expressions:
        task_name = task_name.replace(expr, "")
    
    # 時期表現を除去
    time_expressions = ["明日の", "明日", "今日", "来週", "再来週", "2週間後", "来月"]
    for expr in time_expressions:
        task_name = task_name.replace(expr, "")
    
    # 時間表現を除去
    task_name = re.sub(r'\d{1,2}時.*?から.*?\d{1,2}時.*?まで', '', task_name)
    task_name = re.sub(r'\d{1,2}時.*?\d{1,2}時', '', task_name)
    task_name = re.sub(r'\d{1,2}:\d{2}.*?\d{1,2}:\d{2}', '', task_name)
    
    # 日付表現を除去
    task_name = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '', task_name)
    task_name = re.sub(r'\d{1,2}月\d{1,2}日', '', task_name)
    task_name = re.sub(r'\d{4}-\d{2}-\d{2}', '', task_name)
    task_name = re.sub(r'\d{1,2}/\d{1,2}', '', task_name)
    
    task_name = task_name.strip()
    if not task_name:
        task_name = task_description
        
    return task_name, time_info


def parse_time_info_to_date(time_info: str) -> str:
    """時間情報を日付形式に変換"""
    if not time_info:
        return ""
    
    time_lower = time_info.lower()
    
    try:
        if "明日" in time_lower:
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")
        elif "今日" in time_lower:
            return datetime.datetime.now().strftime("%Y-%m-%d")
        elif "来週" in time_lower:
            next_week = datetime.datetime.now() + datetime.timedelta(days=7)
            return next_week.strftime("%Y-%m-%d")
        elif "再来週" in time_lower or "2週間後" in time_lower:
            two_weeks = datetime.datetime.now() + datetime.timedelta(days=14)
            return two_weeks.strftime("%Y-%m-%d")
        elif "来月" in time_lower:
            next_month = datetime.datetime.now() + datetime.timedelta(days=30)
            return next_month.strftime("%Y-%m-%d")
        
        # 具体的な日付パターン
        date_match = re.search(r'(\d{1,2})月(\d{1,2})日', time_info)
        if date_match:
            month, day = date_match.groups()
            current_year = datetime.datetime.now().year
            return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # YYYY-MM-DD形式
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_info)
        if date_match:
            return date_match.group(1)
            
    except Exception as e:
        print(f"日付解析エラー: {e}")
    
    return ""


if __name__ == "__main__":
    # テスト
    test_cases = [
        "Google明日の13時から14時までMTGという予定を追加してほしい",
        "来週の火曜日15時から会議をカレンダーに入れて",
        "明日までにレポートを書く",
        "12月25日17時からパーティー"
    ]
    
    for test in test_cases:
        task_name, time_info = extract_task_details_with_llm(test)
        due_date = parse_time_info_to_date(time_info)
        print(f"入力: {test}")
        print(f"タスク名: {task_name}")
        print(f"時間情報: {time_info}")
        print(f"期限: {due_date}")
        print("-" * 50)