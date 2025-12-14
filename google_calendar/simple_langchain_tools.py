#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import datetime
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool

# カレンダー検索関数
@tool("search_calendar_events")
def search_calendar_events(query: str = "") -> str:
    """Googleカレンダーから予定を検索する
    
    Args:
        query: 検索クエリ
        
    Returns:
        検索結果の文字列
    """
    try:
        # 実際にエラーの詳細を確認するため
        import sys
        sys.path.append('/Users/yoshinomukanou/todo_app')
        from google_calendar.calendar_client import CalendarClient
        
        calendar_client = CalendarClient()
        
        # 今週の予定を検索
        now = datetime.datetime.now()
        time_min = now.isoformat() + '+09:00'
        week_later = now + datetime.timedelta(days=7)
        time_max = week_later.isoformat() + '+09:00'
        
        events = calendar_client.search_events(
            query=query,
            time_min=time_min,
            time_max=time_max,
            max_results=10
        )
        
        if not events:
            return "今週の予定は見つかりませんでした。"
        
        result = f"今週の予定（{len(events)}件）:\n"
        for i, event in enumerate(events, 1):
            start_time = event['start']
            try:
                if 'T' in start_time:
                    dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
            
            result += f"{i}. {event['summary']} ({start_time})\n"
        
        return result
        
    except Exception as e:
        return f"カレンダー検索でエラーが発生しました: {str(e)}"


# タスク一覧取得関数
@tool("list_csv_tasks")
def list_csv_tasks(status_filter: str = None) -> str:
    """CSVファイルからタスクリストを取得する
    
    Args:
        status_filter: ステータスフィルター ('todo', 'done', または None)
        
    Returns:
        タスクリストの文字列
    """
    try:
        csv_file = "tasks.csv"
        if not os.path.exists(csv_file):
            return "タスクファイルが存在しません。"
        
        tasks = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if status_filter and row.get('status', '') != status_filter:
                    continue
                tasks.append(row)
        
        if not tasks:
            filter_msg = f"（ステータス: {status_filter}）" if status_filter else ""
            return f"タスク{filter_msg}は見つかりませんでした。"
        
        status_jp = {"todo": "未完了", "done": "完了"}
        
        result = f"タスク一覧（{len(tasks)}件）:\n"
        for i, task in enumerate(tasks, 1):
            task_name = task.get('task_name', '（名前なし）')
            due_date = task.get('due_date', '')
            status = task.get('status', 'unknown')
            calendar_event_id = task.get('calendar_event_id', '')
            
            due_info = f" (期限: {due_date})" if due_date else ""
            calendar_info = " [📅]" if calendar_event_id else ""
            status_info = status_jp.get(status, status)
            
            result += f"{i}. {task_name}{due_info} - {status_info}{calendar_info}\n"
        
        return result
        
    except Exception as e:
        return f"タスクリスト取得でエラーが発生しました: {str(e)}"


def get_simple_langchain_tools() -> List[Any]:
    """利用可能なLangChainツールのリストを返す"""
    return [search_calendar_events, list_csv_tasks]


# テスト関数
def test_tools():
    """ツールのテスト実行"""
    print("=== シンプルLangChainツールのテスト ===")
    
    # タスクリストツールのテスト
    print("\n1. タスクリストツールのテスト:")
    result = list_csv_tasks()
    print(result)
    
    # カレンダー検索ツールのテスト
    print("\n2. カレンダー検索ツールのテスト:")
    result = search_calendar_events("")
    print(result)


if __name__ == "__main__":
    test_tools()