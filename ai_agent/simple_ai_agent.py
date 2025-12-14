#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import csv
import datetime
from typing import Dict, List, Optional
from google_calendar.calendar_client import CalendarClient
from dotenv import load_dotenv

load_dotenv()


class SimpleTools:
    """シンプルなツール実装（LangChain依存なし）"""
    
    def __init__(self):
        try:
            self.calendar_client = CalendarClient()
            self.calendar_available = True
        except:
            self.calendar_client = None
            self.calendar_available = False
    
    def search_calendar(self, query: str = "", time_min: Optional[str] = None, time_max: Optional[str] = None) -> str:
        """カレンダーイベントを検索"""
        if not self.calendar_available:
            return "カレンダー機能は利用できません（認証設定が必要です）"
        
        try:
            # デフォルトで今日から1週間の予定を検索
            if not time_min:
                now = datetime.datetime.now()
                time_min = now.isoformat() + '+09:00'
            if not time_max:
                week_later = datetime.datetime.now() + datetime.timedelta(days=7)
                time_max = week_later.isoformat() + '+09:00'
            
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
    
    def list_tasks(self, status_filter: Optional[str] = None) -> str:
        """CSVからタスクリストを取得"""
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


class SimpleAIAgent:
    """シンプルなAIエージェント（完全にLangChain依存なし）"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY環境変数が設定されていません")
        
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "openai/gpt-3.5-turbo"
        self.tools = SimpleTools()
    
    def process_query(self, user_input: str) -> str:
        """ユーザーの質問を処理"""
        try:
            # 1. 質問を分析して必要なアクションを特定
            analysis = self._analyze_query(user_input)
            
            # 2. 必要なツールを実行
            tool_results = self._execute_tools(analysis)
            
            # 3. 結果を統合して回答を生成
            response = self._generate_response(user_input, tool_results)
            
            return response
            
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
    
    def _analyze_query(self, query: str) -> Dict:
        """クエリを分析（簡単なキーワードマッチング）"""
        query_lower = query.lower()
        
        # カレンダー関連キーワード
        calendar_keywords = ['予定', 'スケジュール', 'カレンダー', '会議', '打ち合わせ', 'ミーティング']
        # タスク関連キーワード
        task_keywords = ['タスク', 'やること', 'todo', '未完了', '完了', '仕事']
        
        needs_calendar = any(keyword in query_lower for keyword in calendar_keywords)
        needs_tasks = any(keyword in query_lower for keyword in task_keywords)
        
        # どちらも明確でない場合は両方実行
        if not needs_calendar and not needs_tasks:
            needs_calendar = True
            needs_tasks = True
        
        # タスクのステータスフィルタを判定
        task_filter = None
        if '未完了' in query_lower or 'todo' in query_lower:
            task_filter = 'todo'
        elif '完了' in query_lower or 'done' in query_lower:
            task_filter = 'done'
        
        return {
            "needs_calendar": needs_calendar,
            "needs_tasks": needs_tasks,
            "task_filter": task_filter,
            "calendar_query": ""  # シンプルな検索のため空文字
        }
    
    def _execute_tools(self, analysis: Dict) -> Dict:
        """必要なツールを実行"""
        results = {}
        
        try:
            # カレンダー検索
            if analysis.get("needs_calendar", False):
                results["calendar"] = self.tools.search_calendar()
            
            # タスクリスト取得
            if analysis.get("needs_tasks", False):
                task_filter = analysis.get("task_filter")
                results["tasks"] = self.tools.list_tasks(task_filter)
                
        except Exception as e:
            results["error"] = f"ツール実行エラー: {str(e)}"
        
        return results
    
    def _generate_response(self, user_input: str, tool_results: Dict) -> str:
        """ツールの結果を統合して回答を生成"""
        system_prompt = """あなたはタスク管理アシスタントです。
ユーザーの質問に対して、以下のツール実行結果を使って親しみやすい口調で回答してください。

情報を整理して、ユーザーにとって分かりやすい形で提示してください。
日本語で回答し、必要に応じて絵文字も使ってください。

回答例：
- 今日のタスクと予定をまとめて表示
- 重要な情報を先に、詳細は後で
- 見やすい形にフォーマット"""

        # ツール結果をテキストにまとめる
        tool_info = ""
        if "calendar" in tool_results:
            tool_info += f"📅 **カレンダー情報**:\n{tool_results['calendar']}\n\n"
        if "tasks" in tool_results:
            tool_info += f"📋 **タスク情報**:\n{tool_results['tasks']}\n\n"
        if "error" in tool_results:
            tool_info += f"⚠️ **エラー**:\n{tool_results['error']}\n\n"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"質問: {user_input}\n\nツール実行結果:\n{tool_info}"}
                ],
                "temperature": 0.3
            }
            
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
            
        except Exception as e:
            # フォールバック: ツール結果をそのまま返す
            if tool_info:
                return f"以下の情報が見つかりました：\n\n{tool_info}"
            else:
                return "申し訳ございませんが、情報を取得できませんでした。"


def simple_ai_agent_mode() -> None:
    """シンプルAIエージェントのメイン処理"""
    print("\n=== 高機能自然言語モード ===")
    print("AIが質問に応じてカレンダーとタスクの情報を検索してお答えします。")
    print("例: '今週の予定と未完了タスクを教えて'、'明日やることは？'")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    try:
        # エージェントの初期化
        print("🤖 AIエージェントを初期化しています...")
        agent = SimpleAIAgent()
        print("✓ 初期化完了\n")
        
    except ValueError as e:
        print(f"❌ エラー: {e}")
        print("環境変数OPENROUTER_API_KEYを設定してください。")
        return
    except Exception as e:
        print(f"❌ エージェント初期化エラー: {e}")
        return
    
    # 対話ループ
    while True:
        user_input = input("💬 質問を入力してください: ").strip()
        
        # 終了条件
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit']:
            print("👋 高機能自然言語モードを終了します。")
            break
        
        if not user_input:
            print("❓ 質問を入力してください。")
            continue
        
        print("\n🔍 AIが情報を検索・分析しています...")
        
        # エージェントで処理
        response = agent.process_query(user_input)
        print(f"\n🤖 **回答**:\n{response}\n")
        print("-" * 60)


if __name__ == "__main__":
    simple_ai_agent_mode()