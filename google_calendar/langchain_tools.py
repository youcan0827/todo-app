#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import datetime
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from .calendar_client import CalendarClient


# search_calendar_eventsツールの入力スキーマ
class CalendarSearchInput(BaseModel):
    query: str = Field(description="検索クエリ（イベント名やキーワード）")
    time_min: Optional[str] = Field(
        None, 
        description="検索開始時刻（YYYY-MM-DDTHH:MM:SS形式、デフォルトは現在時刻）"
    )
    time_max: Optional[str] = Field(
        None, 
        description="検索終了時刻（YYYY-MM-DDTHH:MM:SS形式、デフォルトは30日後）"
    )


# list_csv_tasksツールの入力スキーマ
class TaskListInput(BaseModel):
    status_filter: Optional[str] = Field(
        None, 
        description="ステータスフィルター（'todo', 'done', またはNoneで全件）"
    )


class SearchCalendarEventsTool(BaseTool):
    """Googleカレンダーでイベントを検索するLangChainツール"""
    
    name: str = "search_calendar_events"
    description: str = """日付や期間を指定してGoogleカレンダーの予定を検索する時に使用する。
    検索クエリ、開始時刻、終了時刻を指定できます。"""
    args_schema: Type[BaseModel] = CalendarSearchInput

    def __init__(self):
        super().__init__()
        self._initialize_calendar_client()
    
    def _initialize_calendar_client(self):
        """カレンダークライアントの初期化"""
        try:
            self._calendar_client = CalendarClient()
        except Exception as e:
            print(f"警告: Googleカレンダーの初期化に失敗しました: {e}")
            self._calendar_client = None
    
    @property
    def calendar_client(self):
        """カレンダークライアントのプロパティ"""
        if not hasattr(self, '_calendar_client'):
            self._initialize_calendar_client()
        return self._calendar_client

    def _run(
        self,
        query: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """カレンダーイベントを検索して結果を返す"""
        
        if not self.calendar_client:
            return "エラー: Googleカレンダーの認証情報が設定されていません。"
        
        try:
            # 日時文字列の変換（必要に応じて）
            if time_min:
                try:
                    # YYYY-MM-DDTHH:MM:SS形式をISO形式に変換
                    if 'T' in time_min and not time_min.endswith('Z'):
                        time_min = time_min + '+09:00'  # JST
                except:
                    pass
                    
            if time_max:
                try:
                    if 'T' in time_max and not time_max.endswith('Z'):
                        time_max = time_max + '+09:00'  # JST
                except:
                    pass

            events = self.calendar_client.search_events(
                query=query,
                time_min=time_min,
                time_max=time_max,
                max_results=10
            )
            
            if not events:
                return f"検索クエリ「{query}」に一致するイベントは見つかりませんでした。"
            
            result = f"検索結果（{len(events)}件）:\n"
            for i, event in enumerate(events, 1):
                start_time = event['start']
                # ISO形式の日時を読みやすい形式に変換
                try:
                    if 'T' in start_time:
                        dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        start_time = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
                
                result += f"{i}. {event['summary']} ({start_time})\n"
                if event['description']:
                    result += f"   説明: {event['description'][:100]}...\n"
            
            return result
            
        except Exception as e:
            return f"カレンダー検索でエラーが発生しました: {str(e)}"

    async def _arun(
        self,
        query: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """非同期実行（同期版を呼び出し）"""
        return self._run(query, time_min, time_max, run_manager)


class ListCSVTasksTool(BaseTool):
    """CSVファイルからタスクリストを確認するLangChainツール"""
    
    name: str = "list_csv_tasks"
    description: str = """現在登録されているタスクの一覧を確認する時に使用する。
    ステータスでフィルタリングすることも可能です。"""
    args_schema: Type[BaseModel] = TaskListInput

    def __init__(self, csv_file: str = "tasks.csv"):
        super().__init__()
        self.csv_file = csv_file

    def _run(
        self,
        status_filter: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """CSVファイルからタスクを読み込んで結果を返す"""
        
        try:
            if not os.path.exists(self.csv_file):
                return "タスクファイルが存在しません。"
            
            tasks = []
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # ステータスフィルターが指定されている場合
                    if status_filter and row.get('status', '') != status_filter:
                        continue
                    tasks.append(row)
            
            if not tasks:
                filter_msg = f"（ステータス: {status_filter}）" if status_filter else ""
                return f"タスク{filter_msg}は見つかりませんでした。"
            
            # タスクリストの表示形式を整える
            status_jp = {"todo": "未完了", "done": "完了"}
            
            result = f"タスク一覧（{len(tasks)}件）:\n"
            for i, task in enumerate(tasks, 1):
                task_name = task.get('task_name', '（名前なし）')
                due_date = task.get('due_date', '')
                status = task.get('status', 'unknown')
                created_at = task.get('created_at', '')
                calendar_event_id = task.get('calendar_event_id', '')
                
                # 期限情報
                due_info = f" (期限: {due_date})" if due_date else ""
                # カレンダー連携情報
                calendar_info = " [📅]" if calendar_event_id else ""
                # ステータス
                status_info = status_jp.get(status, status)
                
                result += f"{i}. {task_name}{due_info} - {status_info}{calendar_info}\n"
                if created_at:
                    result += f"   作成: {created_at}\n"
            
            return result
            
        except Exception as e:
            return f"タスクリスト取得でエラーが発生しました: {str(e)}"

    async def _arun(
        self,
        status_filter: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """非同期実行（同期版を呼び出し）"""
        return self._run(status_filter, run_manager)


def get_langchain_tools() -> List[BaseTool]:
    """利用可能なLangChainツールのリストを返す"""
    return [
        SearchCalendarEventsTool(),
        ListCSVTasksTool()
    ]


# テスト関数
def test_tools():
    """ツールのテスト実行"""
    tools = get_langchain_tools()
    
    print("=== LangChainツールのテスト ===")
    
    # タスクリストツールのテスト
    print("\n1. タスクリストツールのテスト:")
    task_tool = tools[1]
    result = task_tool._run()
    print(result)
    
    # カレンダー検索ツールのテスト
    print("\n2. カレンダー検索ツールのテスト:")
    calendar_tool = tools[0]
    result = calendar_tool._run(
        query="会議",
        time_min="2025-12-14T00:00:00",
        time_max="2025-12-21T23:59:59"
    )
    print(result)


if __name__ == "__main__":
    test_tools()