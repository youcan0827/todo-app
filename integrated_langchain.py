#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import csv
import datetime
import json
import pickle
import re
from typing import Any, Dict, List, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

# ひろゆき風応答システム
class HiroyukiResponseSystem:
    def __init__(self):
        self.system_prompt = self._load_hiroyuki_prompt()
        
    def _load_hiroyuki_prompt(self) -> str:
        """ひろゆき風システムプロンプトを読み込み（統合版）"""
        # 統合プロンプトファイルから読み込み
        prompt_file = "/Users/yoshinomukanou/todo_app/hiroyuki_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            # フォールバック用の基本プロンプト
            return """
あなたはひろゆき（西村博之）として回答してください。以下の特徴を持って応答してください：

基本的な口調と態度：
- 一人称は必ず「おいら」を使用
- 冷静で論理的だが、時々皮肉っぽい
- 「〜っぽいですけど」「〜ですよね」などの語尾を使う
- 相手の前提や常識を疑う質問をする
- データや根拠を重視する発言をする

典型的な表現パターン：
- 「それ、根拠ありますか？」
- 「普通の人はそう思わないと思うんですけど」
- 「〜って意味不明じゃないですか？」
- 「論理的に考えて〜」
- 「感情論じゃなくて〜」
- 「おいらとしては〜」

現在の文脈：タスク管理システムでユーザーがタスクを溜め込んでいる状況で怒っている
"""

    def get_hiroyuki_response(self, user_message: str, task_count: int) -> str:
        """ひろゆき風の応答を生成"""
        try:
            llm = ChatOpenAI(temperature=0.7)
            
            context_prompt = f"""
ユーザーが{task_count}個ものタスクを溜め込んでいます。
ユーザーメッセージ: {user_message}

ひろゆき風にタスク管理について説得力のある指摘をしてください。
150文字以内で、ひろゆきらしい論理的に回答してください。
"""
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=context_prompt)
            ]
            
            response = llm.invoke(messages)
            return response.content
            
        except Exception as e:
            return f"それって、システムエラーってことですよね？ {task_count}個もタスク溜めてるのに、さらにエラーとか意味不明じゃないですか？"
    
    def update_prompt_with_feedback(self, feedback: str):
        """フィードバックを基にシステムプロンプトを更新"""
        try:
            # フィードバック内容を解析してプロンプト改善
            llm = ChatOpenAI(temperature=0.3)
            
            improvement_prompt = f"""
現在のひろゆき風システムプロンプト:
{self.system_prompt}

ユーザーフィードバック: {feedback}

このフィードバックを基に、より「ひろゆきらしさ」を改善したシステムプロンプトを作成してください。
元のプロンプトの構造を保ちながら、具体的な表現や口調を改善してください。
"""
            
            messages = [
                SystemMessage(content="あなたはシステムプロンプトの改善専門家です。"),
                HumanMessage(content=improvement_prompt)
            ]
            
            response = llm.invoke(messages)
            self.system_prompt = response.content
            
        except Exception as e:
            print(f"プロンプト更新エラー: {e}")

# グローバルインスタンス
hiroyuki_system = HiroyukiResponseSystem()


# Google Calendarスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Googleカレンダーから予定を検索するツール
@tool("search_calendar_events")
def search_calendar_events(query: str = "") -> str:
    """Googleカレンダーから予定を検索する"""
    try:
        # 簡易認証とサービス作成
        creds = None
        token_file = "config/token.pickle"
        credentials_file = "config/credentials.json"
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_file):
                    return "Google Calendar認証ファイルが見つかりません。"
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        service = build('calendar', 'v3', credentials=creds)
        
        # 今週の予定を検索
        now = datetime.datetime.now()
        time_min = now.isoformat() + '+09:00'
        week_later = now + datetime.timedelta(days=7)
        time_max = week_later.isoformat() + '+09:00'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
            q=query
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "今週の予定は見つかりませんでした。"
        
        result = f"今週の予定（{len(events)}件）:\n"
        for i, event in enumerate(events, 1):
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            try:
                if 'T' in start_time:
                    dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.strftime('%m月%d日 %H:%M')
            except:
                pass
            
            result += f"{i}. {event.get('summary', '（タイトルなし）')} ({start_time})\n"
        
        return result
        
    except Exception as e:
        return f"カレンダー検索でエラーが発生しました: {str(e)}"

# csvファイルからタスクを取得するツール
@tool("list_csv_tasks")
def list_csv_tasks(status_filter: str = None) -> str:
    """CSVファイルからタスクリストを取得する"""
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

def _add_to_calendar_simple(task_name: str, due_date: str) -> Optional[str]:
    """シンプルなGoogleカレンダー追加関数"""
    try:
        # 認証情報の取得
        creds = None
        token_file = "config/token.pickle"
        credentials_file = "config/credentials.json"
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_file):
                    print("Google Calendar認証ファイルが見つかりません。")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            os.makedirs("config", exist_ok=True)
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # カレンダーサービス作成
        service = build('calendar', 'v3', credentials=creds)
        
        # イベント作成
        event = {
            'summary': f"📋 {task_name}",
            'start': {'date': due_date},
            'end': {'date': due_date},
            'description': f"TODOアプリから作成されたタスク\n作成日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        # カレンダーに追加
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return event_result.get('id')
        
    except Exception as e:
        print(f"カレンダー追加エラー: {e}")
        return None

# 自然言語でタスク操作するツール
@tool("add_task_naturally")
def add_task_naturally(task_description: str) -> str:
    """自然言語でタスクを追加する"""
    try:
        import re
        
        # 期限を抽出
        due_date = ""
        if "明日" in task_description:
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            due_date = tomorrow.strftime("%Y-%m-%d")
        elif "今日" in task_description:
            due_date = datetime.datetime.now().strftime("%Y-%m-%d")
        elif "来週" in task_description:
            next_week = datetime.datetime.now() + datetime.timedelta(days=7)
            due_date = next_week.strftime("%Y-%m-%d")
        elif "再来週" in task_description or "2週間後" in task_description:
            two_weeks = datetime.datetime.now() + datetime.timedelta(days=14)
            due_date = two_weeks.strftime("%Y-%m-%d")
        elif "来月" in task_description:
            next_month = datetime.datetime.now() + datetime.timedelta(days=30)
            due_date = next_month.strftime("%Y-%m-%d")
        elif re.search(r'\d{4}年\d{1,2}月\d{1,2}日', task_description):
            # 「2025年12月24日」形式
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', task_description)
            if date_match:
                year, month, day = date_match.groups()
                due_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        elif re.search(r'\d{4}-\d{2}-\d{2}', task_description):
            # 「2025-12-24」形式
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', task_description)
            due_date = date_match.group()
        elif re.search(r'\d{1,2}/\d{1,2}', task_description):
            # 「12/24」形式
            date_match = re.search(r'(\d{1,2})/(\d{1,2})', task_description)
            if date_match:
                month, day = date_match.groups()
                current_year = datetime.datetime.now().year
                due_date = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # LLMでタスク詳細を抽出
        from task_extraction import extract_task_details_with_llm, parse_time_info_to_date
        
        task_name, time_info = extract_task_details_with_llm(task_description)
        
        # 抽出された時間情報から期限を設定（元の due_date より優先）
        llm_due_date = parse_time_info_to_date(time_info)
        if llm_due_date:
            due_date = llm_due_date
        
        # タスク名が空の場合は元の文章を使用
        if not task_name.strip():
            task_name = task_description
        
        # カレンダー連携の必要性を判定
        calendar_keywords = ["カレンダー", "スケジュール", "予定", "calendar"]
        needs_calendar = any(keyword in task_description.lower() for keyword in calendar_keywords)
            
        # CSVに追加
        csv_file = "tasks.csv"
        csv_headers = ["task_name", "due_date", "status", "created_at", "calendar_event_id"]
        
        # ファイル存在確認
        if not os.path.exists(csv_file):
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(csv_headers)
        
        # 既存タスク読み込み
        tasks = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            tasks = list(reader)
        
        # Googleカレンダー連携処理
        calendar_event_id = ""
        calendar_result = ""
        
        if needs_calendar and due_date:
            calendar_event_id = _add_to_calendar_simple(task_name, due_date)
            if calendar_event_id:
                calendar_result = " 📅 Googleカレンダーにも追加しました！"
            else:
                calendar_result = " ⚠️ カレンダー追加に失敗しました"
        elif needs_calendar and not due_date:
            calendar_result = " ⚠️ 期限がないためカレンダー追加をスキップしました"
        
        # 新タスク追加
        new_task = {
            "task_name": task_name,
            "due_date": due_date,
            "status": "todo",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "calendar_event_id": calendar_event_id
        }
        tasks.append(new_task)
        
        # CSV書き込み
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(tasks)
        
        due_info = f"（期限: {due_date}）" if due_date else ""
        return f"✅ タスク「{task_name}」を追加しました{due_info}{calendar_result}"
        
    except Exception as e:
        return f"タスク追加エラー: {str(e)}"

@tool("complete_task_naturally") 
def complete_task_naturally(task_hint: str) -> str:
    """自然言語でタスクを完了する"""
    try:
        csv_file = "tasks.csv"
        if not os.path.exists(csv_file):
            return "タスクファイルが見つかりません。"
            
        # 既存タスク読み込み
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            tasks = list(reader)
        
        # 未完了タスクを検索
        incomplete_tasks = [(i, task) for i, task in enumerate(tasks) if task["status"] == "todo"]
        
        if not incomplete_tasks:
            return "完了可能なタスクがありません。"
        
        # タスク名で部分一致検索
        task_hint_clean = task_hint.lower().replace("完了", "").replace("やった", "").replace("できた", "").replace("済んだ", "").replace("終わった", "").strip()
        
        best_match = None
        best_score = 0
        
        for idx, task in incomplete_tasks:
            task_name = task['task_name'].lower()
            if task_hint_clean in task_name or task_name in task_hint_clean:
                score = len(set(task_hint_clean) & set(task_name)) / len(set(task_hint_clean) | set(task_name)) if task_hint_clean and task_name else 0
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = idx
        
        if best_match is not None:
            completed_task_name = tasks[best_match]['task_name']
            tasks[best_match]["status"] = "done"
            
            # CSV更新
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=["task_name", "due_date", "status", "created_at", "calendar_event_id"])
                writer.writeheader()
                writer.writerows(tasks)
            
            return f"🎉 タスク「{completed_task_name}」を完了しました！お疲れ様でした！"
        else:
            # 候補を表示
            result = "完了するタスクが特定できませんでした。未完了タスク一覧:\n"
            for i, (_, task) in enumerate(incomplete_tasks[:5], 1):
                due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
                result += f"{i}. {task['task_name']}{due_info}\n"
            result += "\nより具体的なタスク名で指定してください。"
            return result
            
    except Exception as e:
        return f"タスク完了エラー: {str(e)}"

@tool
def delete_task_naturally(task_hint: str) -> str:
    """自然言語でタスクを削除する"""
    try:
        csv_file = "tasks.csv"
        
        # CSVファイル確認
        if not os.path.exists(csv_file):
            return "タスクファイルが見つかりません。"
        
        # 既存タスクを読み込み
        tasks = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            tasks = list(reader)
        
        if not tasks:
            return "削除可能なタスクがありません。"
        
        # 削除対象のタスクを検索（あいまい検索）
        task_hint_clean = task_hint.lower().replace("削除", "").replace("消す", "").replace("消して", "").replace("とって", "").replace("除く", "").strip()
        
        best_match = None
        best_score = 0
        
        for idx, task in enumerate(tasks):
            task_name = task['task_name'].lower()
            if task_hint_clean in task_name or task_name in task_hint_clean:
                score = len(set(task_hint_clean) & set(task_name)) / len(set(task_hint_clean) | set(task_name)) if task_hint_clean and task_name else 0
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = idx
        
        if best_match is not None:
            deleted_task = tasks[best_match]
            deleted_task_name = deleted_task['task_name']
            
            # Googleカレンダーからも削除
            calendar_result = ""
            if deleted_task.get('calendar_event_id'):
                try:
                    # カレンダー削除処理
                    credentials = get_calendar_credentials()
                    if credentials:
                        service = build('calendar', 'v3', credentials=credentials)
                        service.events().delete(calendarId='primary', eventId=deleted_task['calendar_event_id']).execute()
                        calendar_result = " 📅 Googleカレンダーからも削除しました！"
                except Exception as e:
                    calendar_result = f" (カレンダー削除エラー: {e})"
            
            # CSVから削除
            tasks.pop(best_match)
            
            # CSV更新
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=["task_name", "due_date", "status", "created_at", "calendar_event_id"])
                writer.writeheader()
                writer.writerows(tasks)
            
            return f"🗑️ タスク「{deleted_task_name}」を削除しました！{calendar_result}"
        else:
            # 候補を表示
            result = "削除するタスクが特定できませんでした。現在のタスク一覧:\n"
            for i, task in enumerate(tasks[:5], 1):
                due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
                status_info = "✅ 完了" if task['status'] == "done" else "📋 未完了"
                result += f"{i}. {task['task_name']}{due_info} - {status_info}\n"
            result += "\nより具体的なタスク名で指定してください。"
            return result
            
    except Exception as e:
        return f"タスク削除エラー: {str(e)}"

class IntegratedLangChainAgent:
    """統合LangChainエージェント（全機能内包版）"""
    
    def __init__(self):
        # OpenRouter APIの設定
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        # LLMの設定（APIキーがなくても基本機能は動作）
        if api_key:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1
            )
            self.llm_available = True
        else:
            self.llm = None
            self.llm_available = False
        
        # 利用可能なツールを統合（自然言語タスク管理を追加）
        self.tools = [search_calendar_events, list_csv_tasks, add_task_naturally, complete_task_naturally, delete_task_naturally]
        
        # 対話履歴記録（統合）
        
        # 簡易怒りシステム（統合）
        self.anger_stats_file = "anger_stats.json"
        self.anger_patterns = {
            "gentle": "うーん...{count}個もタスクが残ってるね😅 どれか終わったのある？",
            "direct": "おい！{count}個もタスク残ってるじゃん！😤 本気でやる気ある？"
        }
        self.anger_stats = {"gentle": {"success": 0, "total": 0}, "direct": {"success": 0, "total": 0}}
        self._load_anger_stats()
        
        # システムプロンプト
        self.system_prompt = """あなたは高機能なタスク管理アシスタントです。
ユーザーの質問に応じて、以下のツールを使用して情報を取得し、回答してください：

利用可能なツール:
1. search_calendar_events: Googleカレンダーから予定を検索
2. list_csv_tasks: CSVファイルからタスクリストを取得
3. add_task_naturally: 自然言語でタスクを追加
4. complete_task_naturally: 自然言語でタスクを完了
5. delete_task_naturally: 自然言語でタスクを削除

ユーザーの質問を分析して、必要なツールを実行し、結果を統合してわかりやすく回答してください。
- タスクを追加したい場合：add_task_naturallyを使用
- タスクを完了したい場合：complete_task_naturallyを使用
- タスクを削除したい場合：delete_task_naturallyを使用
- タスク一覧を見たい場合：list_csv_tasksを使用
- 予定を確認したい場合：search_calendar_eventsを使用

日本語で親しみやすい口調で回答してください。"""
    
    def process_query(self, user_input: str) -> str:
        """ユーザーの質問を処理"""
        start_time = time.time()
        
        try:
            # 怒るべきかどうかをキーワード検索でチェック
            if self._should_get_angry(user_input):
                # シンプルひろゆき風システムを使用
                from simple_hiroyuki_chat import SimpleHiroyukiChat
                
                # 未完了タスク数を取得
                try:
                    with open("tasks.csv", 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        incomplete_count = sum(1 for row in reader if row.get('status') == 'todo')
                except:
                    incomplete_count = 0
                
                print("\n" + "="*60)
                print("🤖💢 ひろゆき風AI怒りモード発動！")
                print("="*60)
                
                # シンプルひろゆきチャットで応答生成
                hiroyuki_chat = SimpleHiroyukiChat()
                hiroyuki_input = f"ユーザーが{incomplete_count}個ものタスクを溜め込んでいます。{user_input}"
                hiroyuki_response = hiroyuki_chat.get_hiroyuki_response(hiroyuki_input)
                
                # 元の質問を処理
                print("\n" + "="*40)
                print("元の質問への回答:")
                print("="*40)
                original_response = self._process_original_query(user_input)
                
                response_time = time.time() - start_time
                
                return f"ひろゆき風指摘: {hiroyuki_response}\n\n元の質問への回答:\n{original_response}"
            
            else:
                # 🔥 STEP 2: 通常モード
                # 通常のAI処理
                return self._process_original_query(user_input, start_time)
            
        except Exception as e:
            error_response = f"エラーが発生しました: {str(e)}"
            
            # エラーも履歴に記録（怒りモードの場合は hiroyuki_system で記録済みのためスキップ）
            response_time = time.time() - start_time
            
            return error_response
    
    def _process_original_query(self, user_input: str, start_time: Optional[float] = None) -> str:
        """元の質問処理（怒りモード分離後）"""
        if start_time is None:
            start_time = time.time()
        
        # 1. 質問を分析してツールを選択
        tools_to_use = self._analyze_query(user_input)
        
        # 2. ツールを実行して結果を取得
        tool_results = self._execute_tools(tools_to_use)
        
        # 3. LLMで回答生成
        # ひろゆき風に言葉の変換も実行
        response = self._generate_response(user_input, tool_results)
        
        # 4. 対話履歴を記録
        response_time = time.time() - start_time
        if not self._should_get_angry(user_input):
            tools_used = list(tool_results.keys()) if tool_results else []
        
        return response
    
    def _analyze_query(self, query: str) -> Dict[str, bool]:
        """LLMを使ってクエリを分析し必要なツールを特定"""
        if not self.llm:
            # LLMがない場合はフォールバック（キーワードベース）
            return self._fallback_keyword_analysis(query)
        
        try:
            analysis_prompt = f"""
以下のユーザーの質問を分析し、どのツールが必要かをJSONで回答してください。

ユーザーの質問: "{query}"

判定基準:
- calendar: カレンダー情報の検索・表示が必要
- tasks: タスク一覧の表示・確認が必要  
- add_task: 新しいタスクやイベントの追加が必要
- complete_task: 既存タスクの完了マークが必要
- delete_task: タスクやイベントの削除が必要

例:
「明日までにレポートを書く」→ {{"calendar": false, "tasks": false, "add_task": true, "complete_task": false}}
「今日の予定は？」→ {{"calendar": true, "tasks": false, "add_task": false, "complete_task": false}}
「タスクの状況教えて」→ {{"calendar": false, "tasks": true, "add_task": false, "complete_task": false}}
「プレゼン準備やった」→ {{"calendar": false, "tasks": false, "add_task": false, "complete_task": true}}
「来週の火曜日3時からミーティングをカレンダーに追加」→ {{"calendar": false, "tasks": false, "add_task": true, "complete_task": false}}

JSON形式のみで回答:
"""
            
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            
            # JSONパース試行
            import json
            try:
                result = json.loads(response.content.strip())
                # 必要なキーが全て存在するかチェック
                required_keys = ['calendar', 'tasks', 'add_task', 'complete_task', 'delete_task']
                if all(key in result for key in required_keys):
                    return result
            except json.JSONDecodeError:
                pass
                
            # JSON解析失敗時はフォールバック
            return self._fallback_keyword_analysis(query)
            
        except Exception as e:
            print(f"LLM分析エラー: {e}")
            return self._fallback_keyword_analysis(query)
    
    def _fallback_keyword_analysis(self, query: str) -> Dict[str, bool]:
        """フォールバック用キーワードベース分析"""
        query_lower = query.lower()
        
        # キーワードベースで判定
        needs_calendar = any(kw in query_lower for kw in ['予定', 'スケジュール', 'カレンダー', '会議'])
        needs_tasks = any(kw in query_lower for kw in ['タスク', 'やること', 'todo', '未完了', '状況', '一覧'])
        needs_add = any(kw in query_lower for kw in ['追加', '作る', 'する', 'やる', '登録', 'までに', '入れる', '入れて', 'いれて', 'セットして', 'set'])
        needs_complete = any(kw in query_lower for kw in ['完了', '終わった', 'やった', 'できた', '済んだ'])
        needs_delete = any(kw in query_lower for kw in ['削除', '消す', '消して', 'とって', '除く', '取り消す'])
        
        # カレンダー＋追加の組み合わせは明確にタスク追加
        if needs_calendar and needs_add:
            return {
                'calendar': False,
                'tasks': False,
                'add_task': True,
                'complete_task': False,
                'delete_task': False
            }
        
        # どちらも明確でない場合は両方
        if not any([needs_calendar, needs_tasks, needs_add, needs_complete, needs_delete]):
            needs_calendar = needs_tasks = True
        
        return {
            'calendar': needs_calendar,
            'tasks': needs_tasks,
            'add_task': needs_add,
            'complete_task': needs_complete,
            'delete_task': needs_delete
        }
    
    def _execute_tools(self, tools_to_use: Dict[str, bool]) -> Dict[str, str]:
        """必要なツールを実行"""
        results = {}
        
        try:
            # カレンダー検索
            if tools_to_use['calendar']:
                results['calendar'] = search_calendar_events.func("")
            
            # タスクリスト取得
            if tools_to_use['tasks']:
                results['tasks'] = list_csv_tasks.func("todo")  # 未完了タスクのみ
            
            # 自然言語タスク操作（後で処理するためマーク）
            if tools_to_use['add_task']:
                results['add_task'] = "PENDING"
            if tools_to_use['complete_task']:
                results['complete_task'] = "PENDING"
            if tools_to_use['delete_task']:
                results['delete_task'] = "PENDING"
                
        except Exception as e:
            results['error'] = f"ツール実行エラー: {str(e)}"
        
        return results
    
    def _generate_response(self, user_input: str, tool_results: Dict[str, str]) -> str:
        """LLMで結果を統合して回答生成"""
        # 自然言語タスク操作が必要な場合は直接実行してからひろゆき風に変換
        if tool_results.get('add_task') == "PENDING":
            try:
                original_result = add_task_naturally.func(user_input)
                return self._simple_hiroyuki_convert(original_result, user_input)
            except Exception as e:
                error_msg = f"タスク追加エラー: {str(e)}"
                return self._simple_hiroyuki_convert(error_msg, user_input)
        
        if tool_results.get('complete_task') == "PENDING":
            try:
                original_result = complete_task_naturally.func(user_input)
                return self._simple_hiroyuki_convert(original_result, user_input)
            except Exception as e:
                error_msg = f"タスク完了エラー: {str(e)}"
                return self._simple_hiroyuki_convert(error_msg, user_input)
        
        if tool_results.get('delete_task') == "PENDING":
            try:
                original_result = delete_task_naturally.func(user_input)
                return self._simple_hiroyuki_convert(original_result, user_input)
            except Exception as e:
                error_msg = f"タスク削除エラー: {str(e)}"
                return self._simple_hiroyuki_convert(error_msg, user_input)
        
        # ツール結果をまとめる
        context = ""
        if 'calendar' in tool_results:
            context += f"📅 カレンダー情報:\n{tool_results['calendar']}\n\n"
        if 'tasks' in tool_results:
            context += f"📋 タスク情報:\n{tool_results['tasks']}\n\n"
        if 'error' in tool_results:
            context += f"⚠️ エラー:\n{tool_results['error']}\n\n"
        
        # LLMで回答生成
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"質問: {user_input}\n\n取得した情報:\n{context}")
        ]
        
        # LLMが利用可能な場合はHTTPリクエストを送信
        if self.llm_available:
            try:
                response = self.llm.invoke(messages)
                original_response = response.content
                
                # シンプルひろゆき風に変換
                hiroyuki_response = self._simple_hiroyuki_convert(original_response)
                
                
                return hiroyuki_response
                
            except Exception as e:
                # フォールバック
                if context:
                    fallback_response = f"以下の情報が取得できました：\n\n{context}"
                else:
                    fallback_response = "申し訳ございませんが、情報を取得できませんでした。"
                
                # フォールバックもひろゆき風に
                hiroyuki_fallback = self._simple_hiroyuki_convert(fallback_response)
                return hiroyuki_fallback
        else:
            # LLMなしの場合もひろゆき風に
            if context:
                original = f"📋 取得した情報:\n\n{context}"
            else:
                original = "LLMが利用できないため、シンプルな応答モードです。タスク操作は引き続き利用できます。"
            
            hiroyuki_response = self._simple_hiroyuki_convert(original)
            return hiroyuki_response
    
    def _simple_hiroyuki_convert(self, original_response: str, user_context: str = "") -> str:
        """シンプルひろゆき風変換（ユーザープロンプトのみ）"""
        try:
            from simple_hiroyuki_chat import SimpleHiroyukiChat
            hiroyuki_chat = SimpleHiroyukiChat()
            
            # ユーザーの指示から特定キーワードをチェック
            if user_context and any(keyword in user_context.lower() for keyword in ['オイラ', 'おいら', '論破', '敬語']):
                conversion_input = f"""ひろゆき（西村博之）として回答してください。

必須の話し方ルール:
- 一人称は必ず「オイラ」または「おいら」を使用
- 敬語で丁寧に話す（です・ます調）
- 論理的で論破するような口調
- 「〜っていうのは」「〜じゃないですか」などの語尾を使う

以下の内容を上記のルールに従ってひろゆき風に変換してください:
{original_response}"""
            else:
                conversion_input = f"以下の内容をひろゆき風に変換してください: {original_response}"
                
            return hiroyuki_chat.get_hiroyuki_response(conversion_input)
            
        except Exception as e:
            # 変換失敗時のフォールバック
            return f"おいらとしては、{original_response}って感じですよね。まあ、普通の人はそう思うんじゃないですか？"
    

    # 🤖 統合された怒りシステム
    def _should_get_angry(self, user_input: str) -> bool:
        """怒るべきかどうか判定（明確な条件のみ）"""
        # 明確な「タスク確認」を意味するキーワードのみ
        task_check_keywords = [
            "タスク確認", "タスク状況", "未完了", "残り", 
            "進捗", "タスク一覧", "やること確認"
        ]
        
        # タスク確認の意図があるかチェック
        is_task_check = any(keyword in user_input for keyword in task_check_keywords)
        
        if not is_task_check:
            return False
        
        # 未完了タスク5個以上で怒る
        incomplete_count = self._get_incomplete_task_count()
        return incomplete_count >= 5
    
    def _get_anger_message(self, user_input: str) -> Tuple[str, str]:
        """怒りメッセージを生成"""
        # どのくらい未完了のタスクがあるかを確認
        incomplete_count = self._get_incomplete_task_count()
        
        # 最適パターン選択（成功率ベース）
        # gentleかdirectの2パターンでメッセージを選択
        gentle_rate = self._get_success_rate("gentle")
        direct_rate = self._get_success_rate("direct")
        
        if self.anger_stats["gentle"]["total"] < 2 and self.anger_stats["direct"]["total"] < 2:
            import random
            pattern = random.choice(["gentle", "direct"])
        else:
            pattern = "gentle" if gentle_rate >= direct_rate else "direct"
        
        message = self.anger_patterns[pattern].format(count=incomplete_count)
        full_message = f"{message}\n\n📋 未完了タスクが{incomplete_count}個あります！\n実は終わってるタスクがあれば教えて！"
        
        return full_message, pattern
    
    def _get_incomplete_task_count(self) -> int:
        """未完了タスク数を取得"""
        try:
            with open("tasks.csv", 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                count = sum(1 for row in reader if row.get('status') == 'todo')
                return count
        except:
            return 0
    
    def _record_anger_result(self, pattern: str, was_successful: bool) -> None:
        """怒り結果記録"""
        self.anger_stats[pattern]["total"] += 1
        if was_successful:
            self.anger_stats[pattern]["success"] += 1
        self._save_anger_stats()
    
    def _get_success_rate(self, pattern: str) -> float:
        """成功率計算"""
        stats = self.anger_stats[pattern]
        if stats["total"] == 0:
            return 0.5
        return stats["success"] / stats["total"]
    
    def _load_anger_stats(self) -> None:
        """怒り統計読み込み"""
        try:
            if os.path.exists(self.anger_stats_file):
                with open(self.anger_stats_file, 'r', encoding='utf-8') as f:
                    self.anger_stats = json.load(f)
        except Exception as e:
            print(f"統計読み込みエラー: {e}")
    
    def _save_anger_stats(self) -> None:
        """怒り統計保存"""
        try:
            with open(self.anger_stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.anger_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"統計保存エラー: {e}")
    
    
    def get_simple_anger_report(self) -> str:
        """ひろゆきモード効果レポート"""
        hiroyuki_rate = self._get_success_rate("hiroyuki")
        hiroyuki_total = self.anger_stats.get("hiroyuki", {}).get("total", 0)
        
        report = "📊 ひろゆき風AI効果分析レポート\n"
        report += "="*40 + "\n"
        report += f"🤔 ひろゆきらしさ: {hiroyuki_rate:.1%} ({hiroyuki_total}回使用)\n"
        
        if hiroyuki_total > 0:
            if hiroyuki_rate >= 0.7:
                report += "\n🎆 結果: ひろゆきらしさが高度に再現されています！"
            elif hiroyuki_rate >= 0.5:
                report += "\n📈 結果: まあまあひろゆきっぽいですね"
            else:
                report += "\n🤔 結果: まだひろゆきらしさが足りないですね"
        else:
            report += "\n📈 まだデータが不十分です"
        
        return report


# GoogleColab環境専用音声機能
def setup_drive_and_find_model_dir(default_model_dir: str = "model_assets", model_name: str = "yoshino_test") -> Optional[str]:
    """Googleドライブをマウントしてモデルディレクトリを検索"""
    try:
        # より詳細なColab環境チェック
        import os
        import sys
        
        # 複数の方法でColab環境を確認
        colab_indicators = [
            'google.colab' in sys.modules,
            os.path.exists('/content'),
            os.environ.get('COLAB_GPU'),
            'COLAB_TPU_ADDR' in os.environ,
            hasattr(__builtins__, '__IPYTHON__') and os.path.exists('/content')
        ]
        
        is_colab = any(colab_indicators)
        print(f"🔍 環境チェック: Colab={is_colab}, indicators={colab_indicators}")
        
        if not is_colab:
            print("⚠️ Colab環境ではないため、ローカルパスを確認します")
            if os.path.exists(default_model_dir):
                return default_model_dir
            else:
                print(f"❌ ローカルモデルディレクトリが見つかりません: {default_model_dir}")
                return None
        
        # Googleドライブをマウント（Colab環境のみ）
        try:
            from google.colab import drive
            print("✓ google.colabモジュールのインポート成功")
            
            drive_mount_point = "/content/drive"
            
            # 既にマウントされているかチェック
            if os.path.exists(f"{drive_mount_point}/MyDrive"):
                print("✓ Googleドライブは既にマウントされています")
            else:
                print("📁 Googleドライブをマウント中...")
                
                # カーネル状態のチェックとマウント実行
                try:
                    # IPythonカーネルの状態確認
                    try:
                        from IPython import get_ipython
                        ipython = get_ipython()
                        if ipython is None:
                            print("⚠️ IPythonカーネルが見つかりません。代替方法を使用します。")
                            # 代替マウント方法を試行
                            import subprocess
                            result = subprocess.run(['ls', '/content/drive/MyDrive'], capture_output=True, text=True)
                            if result.returncode == 0:
                                print("✓ ドライブは既にアクセス可能です")
                            else:
                                print("❌ ドライブへのアクセスができません")
                                return None
                        else:
                            print("✓ IPythonカーネルが検出されました")
                            # 通常のマウント実行
                            drive.mount(drive_mount_point, force_remount=False)
                            print("✓ Googleドライブがマウントされました")
                            
                    except Exception as kernel_error:
                        print(f"⚠️ カーネルチェックエラー: {kernel_error}")
                        
                        # 最終フォールバック: 直接的なディレクトリ確認
                        print("🔄 直接ディレクトリ確認を実行中...")
                        import subprocess
                        try:
                            # Google Driveがマウントされているかチェック
                            check_cmd = ['test', '-d', '/content/drive/MyDrive']
                            result = subprocess.run(check_cmd, capture_output=True)
                            
                            if result.returncode == 0:
                                print("✓ Google Drive ディレクトリが既に存在します")
                            else:
                                print("❌ Google Driveディレクトリが見つかりません")
                                print("💡 手動でドライブをマウントしてください:")
                                print("   from google.colab import drive")
                                print("   drive.mount('/content/drive')")
                                return None
                                
                        except Exception as subprocess_error:
                            print(f"❌ ディレクトリチェックエラー: {subprocess_error}")
                            return None
                            
                except Exception as mount_error:
                    print(f"❌ ドライブマウント詳細エラー: {mount_error}")
                    print(f"エラータイプ: {type(mount_error)}")
                    
                    # エラー種別に応じた対処
                    error_str = str(mount_error)
                    if 'kernel' in error_str:
                        print("💡 カーネルエラーが検出されました。手動マウントを推奨します:")
                        print("   1. 新しいセルで以下を実行:")
                        print("   from google.colab import drive")
                        print("   drive.mount('/content/drive')")
                        print("   2. 認証を完了してから再実行してください")
                    
                    return None
            
        except ImportError as import_error:
            print(f"❌ google.colabインポートエラー: {import_error}")
            return None
        
        # 可能性のあるモデルパス候補
        possible_paths = [
            f"{drive_mount_point}/MyDrive/Style-Bert-VITS2/model_assets",  # 優先パス
            f"{drive_mount_point}/MyDrive/{default_model_dir}",
            f"{drive_mount_point}/MyDrive/model_assets",
            f"{drive_mount_point}/MyDrive/models",
            f"{drive_mount_point}/MyDrive/voice_models",
            f"{drive_mount_point}/MyDrive/AI_models/{default_model_dir}",
            f"/content/{default_model_dir}",  # ローカルアップロード
            default_model_dir  # 元のパス
        ]
        
        print("🔍 モデルディレクトリを検索中...")
        for path in possible_paths:
            print(f"  チェック中: {path}")
            if os.path.exists(path):
                # モデルファイルの存在も確認
                model_subdir = os.path.join(path, model_name)
                if os.path.exists(model_subdir):
                    print(f"✓ モデルディレクトリが見つかりました: {path}")
                    return path
                else:
                    print(f"  ⚠️ {path}は存在しますが、{model_name}フォルダが見つかりません")
        
        # 見つからない場合は手動アップロード案内
        print("❌ モデルディレクトリが見つかりませんでした")
        print("\n📋 解決方法:")
        print("1. Googleドライブのマイドライブに以下の構造でファイルを配置:")
        print("   MyDrive/Style-Bert-VITS2/model_assets/yoshino_test/")
        print("2. または、Colabの左サイドバーからファイルを直接アップロード")
        print("\n💡 推奨ドライブ構造:")
        print("   MyDrive/")
        print("   └── Style-Bert-VITS2/")
        print("       └── model_assets/")
        print("           └── yoshino_test/")
        print("               ├── config.json")
        print("               ├── model.pth")
        print("               └── style_vectors.npy")
        
        return None
        
    except Exception as e:
        print(f"❌ ドライブマウントエラー: {e}")
        return None


def is_colab_environment() -> bool:
    """GoogleColab環境かどうかを判定（強化版）"""
    try:
        import os
        import sys
        
        # 複数の指標でColab環境を判定
        indicators = {
            'google_colab_module': False,
            'content_dir': os.path.exists('/content'),
            'colab_gpu_env': bool(os.environ.get('COLAB_GPU')),
            'colab_tpu_env': bool(os.environ.get('COLAB_TPU_ADDR')),
            'ipython_and_content': hasattr(__builtins__, '__IPYTHON__') and os.path.exists('/content')
        }
        
        # google.colabモジュールの存在確認
        try:
            import google.colab
            indicators['google_colab_module'] = True
        except ImportError:
            indicators['google_colab_module'] = False
        
        # デバッグ情報出力
        print(f"🔍 Colab環境判定詳細: {indicators}")
        
        # いずれかの指標が真であればColab環境と判定
        is_colab = any(indicators.values())
        print(f"🎯 最終判定: Colab環境 = {is_colab}")
        
        return is_colab
        
    except Exception as e:
        print(f"⚠️ Colab環境判定エラー: {e}")
        return False


def initialize_tts_system(model_name: str = "yoshino_test", model_dir: str = "model_assets", device: str = "auto") -> Optional[object]:
    """音声合成システムの初期化（バックグラウンドTTSサーバー対応）"""
    # GoogleColab環境チェック
    if not is_colab_environment():
        print("⚠️ 音声機能はGoogleColab環境でのみ利用可能です")
        print("💡 GoogleColabでこのスクリプトを実行してください")
        return None
    
    try:
        # Googleドライブをマウントしてモデルパスを検索
        model_dir = setup_drive_and_find_model_dir(model_dir, model_name)
        if model_dir is None:
            return None
            
        # style_bert_vits2の存在確認
        import importlib.util
        spec = importlib.util.find_spec("style_bert_vits2")
        if spec is None:
            print("⚠️ style_bert_vits2ライブラリがインストールされていません")
            print("💡 Colabで !pip install style-bert-vits2 を実行してください")
            return None
            
        # Style-Bert-VITS2の初期化システム（app.pyと同様）
        print("🎌 pyopenjtalk_workerを初期化中...")
        from style_bert_vits2.nlp.japanese import pyopenjtalk_worker
        from style_bert_vits2.nlp.japanese.user_dict import update_dict
        
        # pyopenjtalk_workerの初期化（Style-Bert-VITS2のapp.pyと同じ）
        try:
            pyopenjtalk_worker.initialize_worker()
            print("✓ pyopenjtalk_worker初期化完了")
        except Exception as e:
            print(f"❌ pyopenjtalk_worker初期化エラー: {e}")
            print(f"❌ エラータイプ: {type(e).__name__}")
            import traceback
            print("❌ 詳細なスタックトレース:")
            traceback.print_exc()
            raise e
        
        # 辞書データの適用
        print("📚 辞書データを適用中...")
        update_dict()
        print("✓ 辞書データ適用完了")
        
        # バックグラウンドTTSサーバーを起動
        print("🚀 バックグラウンドTTSサーバーを起動中...")
        tts_server = start_background_tts_server(model_dir, model_name, device)
        
        if tts_server:
            print("✓ バックグラウンドTTSサーバー起動完了")
            return tts_server
        else:
            print("⚠️ バックグラウンドTTSサーバーの起動に失敗しました")
            return None
        
    except ImportError as e:
        print(f"⚠️ 必要なライブラリが不足しています: {e}")
        print("💡 Colabでライブラリをインストールしてください")
        return None
    except Exception as e:
        print(f"⚠️ 音声システム初期化エラー: {e}")
        return None


def start_background_tts_server(model_dir: str, model_name: str, device: str) -> Optional[object]:
    """バックグラウンドでTTSサーバーを起動"""
    try:
        import threading
        import time
        from pathlib import Path
        import torch
        from style_bert_vits2.tts_model import TTSModelHolder
        from style_bert_vits2.utils import torch_device_to_onnx_providers
        
        # デバイス設定
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                print("✓ GPU(CUDA)を使用します")
            else:
                device = "cpu" 
                print("⚠️ GPUが利用できません。CPUを使用します")
        
        print(f"📁 TTSモデルホルダーを初期化中... (パス: {model_dir})")
        
        # TTSModelHolderを作成
        try:
            model_holder = TTSModelHolder(
                Path(model_dir),
                device,
                torch_device_to_onnx_providers(device),
                ignore_onnx=True,
            )
            print("✓ TTSModelHolder作成成功")
        except Exception as e:
            print(f"❌ TTSModelHolder作成エラー: {e}")
            print(f"❌ エラータイプ: {type(e).__name__}")
            print(f"❌ モデルディレクトリ: {model_dir}")
            print(f"❌ 使用デバイス: {device}")
            import traceback
            print("❌ 詳細なスタックトレース:")
            traceback.print_exc()
            raise e
        
        print(f"📋 利用可能なモデル: {list(model_holder.model_names)}")
        
        # 指定されたモデルが存在するかチェック
        if model_name not in model_holder.model_names:
            print(f"⚠️ 指定されたモデル '{model_name}' が見つかりません")
            print(f"💡 利用可能なモデル: {list(model_holder.model_names)}")
            if model_holder.model_names:
                model_name = list(model_holder.model_names)[0]
                print(f"🔄 最初のモデルを使用します: {model_name}")
            else:
                print("❌ 利用可能なモデルがありません")
                return None
        
        # バックグラウンドTTSサーバークラス
        class BackgroundTTSServer:
            def __init__(self, model_holder, model_name):
                self.model_holder = model_holder
                self.model_name = model_name
                self.is_running = True
                
            def synthesize_speech(self, text: str, output_path: str = "output.wav", **kwargs) -> Optional[str]:
                """音声合成を実行"""
                try:
                    # デフォルトパラメータ
                    params = {
                        'model_name': self.model_name,
                        'text': text,
                        'language': kwargs.get('language', 'JP'),
                        'speaker_id': kwargs.get('speaker_id', 0),
                        'sdp_ratio': kwargs.get('sdp_ratio', 0.2),
                        'noise': kwargs.get('noise', 0.6),
                        'noise_w': kwargs.get('noise_w', 0.8),
                        'length': kwargs.get('length', 1.0),
                        'style': kwargs.get('style', 'Neutral'),
                    }
                    
                    print(f"🎵 音声合成実行中: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                    
                    # TTSModelHolderを使用して音声合成
                    result = self.model_holder.infer(**params)
                    
                    # 結果の保存
                    if hasattr(result, 'audio') and hasattr(result, 'sample_rate'):
                        from scipy.io import wavfile
                        import numpy as np
                        
                        # numpyのfloat32配列をint16に変換
                        audio_data = result.audio
                        if audio_data.dtype == np.float32:
                            audio_data = (audio_data * 32767).astype(np.int16)
                        
                        wavfile.write(output_path, result.sample_rate, audio_data)
                        print(f"✓ 音声ファイル生成完了: {output_path}")
                        return output_path
                    else:
                        print("⚠️ 音声生成結果の形式が予期されたものと異なります")
                        return None
                        
                except Exception as e:
                    print(f"⚠️ 音声合成エラー: {e}")
                    return None
                    
            def stop(self):
                """サーバー停止"""
                self.is_running = False
                print("🛑 TTSサーバーを停止しました")
        
        # サーバーインスタンス作成
        tts_server = BackgroundTTSServer(model_holder, model_name)
        
        print("✓ バックグラウンドTTSサーバーが起動しました")
        return tts_server
        
    except Exception as e:
        print(f"⚠️ バックグラウンドTTSサーバー起動エラー: {e}")
        return None


def initialize_native_tts_system(model_dir: str, model_name: str, device: str) -> Optional[object]:
    """Style-Bert-VITS2のネイティブ機能を使用したTTS初期化"""
    try:
        from pathlib import Path
        import torch
        from style_bert_vits2.tts_model import TTSModelHolder
        from style_bert_vits2.utils import torch_device_to_onnx_providers
        
        # Colab環境でのデバイス設定（GPU優先）
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                print("✓ GPU(CUDA)を使用します")
            else:
                device = "cpu"
                print("⚠️ GPUが利用できません。CPUを使用します")
        
        print(f"📁 モデルホルダーを初期化中... (パス: {model_dir})")
        
        # TTSModelHolderを作成（Style-Bert-VITS2のapp.pyと同様）
        model_holder = TTSModelHolder(
            Path(model_dir),
            device,
            torch_device_to_onnx_providers(device),
            ignore_onnx=True,  # app.pyと同じ設定
        )
        
        print(f"✓ TTSModelHolder初期化完了")
        print(f"📋 利用可能なモデル: {list(model_holder.model_names)}")
        
        # 指定されたモデルが存在するかチェック
        if model_name not in model_holder.model_names:
            print(f"⚠️ 指定されたモデル '{model_name}' が見つかりません")
            print(f"💡 利用可能なモデル: {list(model_holder.model_names)}")
            if model_holder.model_names:
                model_name = list(model_holder.model_names)[0]
                print(f"🔄 最初のモデルを使用します: {model_name}")
            else:
                print("❌ 利用可能なモデルがありません")
                return None
        
        # シンプルなラッパークラスを作成
        class NativeTTSModel:
            def __init__(self, model_holder, model_name):
                self.model_holder = model_holder
                self.model_name = model_name
            
            def inference(self, text: str, output_path: str, **kwargs) -> str:
                """音声合成を実行"""
                try:
                    # デフォルトパラメータ
                    params = {
                        'model_name': self.model_name,
                        'text': text,
                        'language': 'JP',
                        'speaker_id': 0,
                        'sdp_ratio': 0.2,
                        'noise': 0.6,
                        'noise_w': 0.8,
                        'length': 1.0,
                        **kwargs
                    }
                    
                    # TTSModelHolderを使用して音声合成
                    from pathlib import Path
                    result = self.model_holder.infer(**params)
                    
                    # 結果を指定されたパスに保存
                    if hasattr(result, 'audio') and hasattr(result, 'sample_rate'):
                        from scipy.io import wavfile
                        wavfile.write(output_path, result.sample_rate, result.audio)
                        return output_path
                    else:
                        print("⚠️ 音声生成結果の形式が予期されたものと異なります")
                        return None
                        
                except Exception as e:
                    print(f"⚠️ 音声合成エラー: {e}")
                    return None
        
        return NativeTTSModel(model_holder, model_name)
        
    except Exception as e:
        print(f"⚠️ ネイティブTTSシステム初期化エラー: {e}")
        return None


def text_to_speech_if_available(text: str, output_path: str = "output.wav") -> Optional[str]:
    """音声合成の実行（バックグラウンドTTSサーバー対応）"""
    if not is_colab_environment():
        print("⚠️ 音声合成はGoogleColab環境でのみ利用可能です")
        return None
        
    try:
        # グローバル音声サーバーの確認
        if not hasattr(text_to_speech_if_available, '_tts_server'):
            print("⚠️ TTSサーバーが初期化されていません")
            return None
            
        tts_server = getattr(text_to_speech_if_available, '_tts_server')
        if tts_server is None:
            print("⚠️ TTSサーバーが利用できません")
            return None
            
        # バックグラウンドTTSサーバーを使用して音声合成
        if hasattr(tts_server, 'synthesize_speech'):
            result_path = tts_server.synthesize_speech(text, output_path)
            return result_path
        else:
            # 従来の方式（フォールバック）
            result_path = tts_server.inference(text, output_path)
            return str(result_path)
        
    except Exception as e:
        print(f"⚠️ 音声合成エラー: {e}")
        return None


def mount_drive_safely() -> bool:
    """安全にGoogleドライブをマウントする関数"""
    try:
        import os
        from google.colab import drive
        
        drive_mount_point = "/content/drive"
        
        # 既にマウントされているかチェック
        if os.path.exists(f"{drive_mount_point}/MyDrive"):
            print("✅ Googleドライブは既にマウントされています")
            return True
        
        print("📁 Googleドライブを手動マウント中...")
        
        # 安全なマウント実行
        try:
            drive.mount(drive_mount_point)
            print("✅ Googleドライブのマウントが完了しました")
            return True
        except Exception as e:
            print(f"❌ マウントエラー: {e}")
            return False
            
    except Exception as e:
        print(f"❌ ドライブマウント関数エラー: {e}")
        return False

def integrated_langchain_mode() -> None:
    """統合LangChainモードのメイン処理（音声機能付き）"""
    print("\n=== 統合LangChain高機能自然言語モード（音声付き） ===")
    print("LangChainを使ってカレンダーとタスクの情報を検索してお答えします。")
    if is_colab_environment():
        print("🎵 AIの応答を音声でも再生します！（GoogleColab環境）")
    else:
        print("💬 音声機能はGoogleColab環境でのみ利用可能です")
    print("")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    # バックグラウンドTTSサーバーの初期化（GoogleColab環境のみ）
    tts_server = None
    if is_colab_environment():
        try:
            print("🎵 バックグラウンドTTSサーバーを初期化中...")
            tts_server = initialize_tts_system()
            if tts_server:
                # グローバル変数に保存（後で使用するため）
                text_to_speech_if_available._tts_server = tts_server
                print("✓ バックグラウンドTTSサーバー初期化完了\n")
            else:
                print("⚠️ TTSサーバーが利用できません（通常モードで続行）\n")
        except Exception as e:
            print(f"⚠️ TTSサーバー初期化エラー: {e}")
            print("💡 音声なしで続行します\n")
    else:
        print("💡 ローカル環境では音声機能は無効です\n")
    
    try:
        # エージェントの初期化
        print("🤖 統合LangChainエージェントを初期化しています...")
        agent = IntegratedLangChainAgent()
        
        if agent.llm_available:
            print("✓ LLM機能付きで初期化完了\n")
        else:
            print("⚠️ LLMなしモードで初期化完了（基本機能は利用可能）\n")
            print("💡 高度なLLM機能を使用したい場合は、OPENROUTER_API_KEYを設定してください。\n")
        
    except Exception as e:
        print(f"❌ エージェント初期化エラー: {e}")
        return
    
    
    # 対話ループ（Colab対応）
    while True:
        try:
            # Colab環境での入力対応
            if is_colab_environment():
                user_input = input("💬 質問を入力してください（'戻る'で終了）: ")
            else:
                user_input = input("💬 質問を入力してください: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 統合LangChain高機能自然言語モードを終了します。")
            break
        except Exception as e:
            print(f"⚠️ 入力エラー: {e}")
            print("💡 Colabでは直接入力ができない場合があります。")
            print("以下のようにコードセルで直接実行してください：")
            print("""
# 質問例をコードセルで直接実行
from integrated_langchain import IntegratedLangChainAgent
agent = IntegratedLangChainAgent()
response = agent.process_query("今日のタスクは？")
print(response)
""")
            break
        
        user_input = user_input.strip()
        
        # 終了条件
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit', '']:
            print("👋 統合LangChain高機能自然言語モードを終了します。")
            break
        
        if not user_input:
            print("❓ 質問を入力してください。")
            continue
        
        # 特別コマンド
        if user_input.lower() in ['怒り分析', '効果レポート', 'モチベーション分析', 'motivation report']:
            report = agent.get_simple_anger_report()
            print(f"\n{report}\n")
            print("-" * 60)
            continue
        
        print("\n🔍 統合LangChainが情報を検索・分析しています...")
        
        # agentインスタンスのprocess_queryメソッドをを呼び出している
        response = agent.process_query(user_input)
        
        print(f"\n🤖 **回答**:\n{response}\n")
        
        # バックグラウンドTTSサーバーを使用した音声生成
        if tts_server:
            try:
                # AIの出力をai_voice変数に格納
                ai_voice = response
                
                print("🎵 バックグラウンドTTSサーバーで音声を生成中...")
                # バックグラウンドTTSサーバーを使用した音声生成
                audio_file = text_to_speech_if_available(ai_voice, "out.wav")
                
                if audio_file:
                    print("🔊 音声を再生します...")
                    try:
                        from IPython.display import Audio, display
                        display(Audio(audio_file))
                        print(f"✓ 音声再生完了: {audio_file}")
                    except ImportError:
                        print("⚠️ Jupyter環境ではないため音声再生をスキップします")
                        print(f"💡 音声ファイルが生成されました: {audio_file}")
                else:
                    print("⚠️ 音声生成に失敗しました")
                    
            except Exception as e:
                print(f"⚠️ 音声生成エラー: {e}")
        
        print("-" * 60)


def colab_quick_chat(question: str = "今日のタスクは？") -> str:
    """GoogleColab用の簡単チャット関数"""
    try:
        print("🤖 AI自然言語モードを起動しています...")
        
        # エージェントの初期化
        agent = IntegratedLangChainAgent()
        
        if not agent.llm_available:
            return "❌ LLMが利用できません。APIキーを確認してください。"
        
        print(f"💬 質問: {question}")
        print("🔍 AI が回答を生成しています...")
        
        # 質問処理
        response = agent.process_query(question)
        
        print(f"\n🤖 **回答**:\n{response}\n")
        
        return response
        
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {e}"
        print(error_msg)
        return error_msg

def colab_setup_guide():
    """GoogleColab用のセットアップガイド"""
    print("""
🚀 GoogleColab用 TODO AIアプリ セットアップガイド

## 📋 必要な準備:
1. OpenRouter APIキーの設定
2. Googleドライブのマウント（音声機能用、オプション）

## 💻 使用方法:

### 方法1: 簡単チャット（推奨）
```python
# 質問をして回答を得る
colab_quick_chat("今日のタスクを確認して")
colab_quick_chat("明日までにレポートを書くタスクを追加")
colab_quick_chat("タスクの進捗はどう？")
```

### 方法2: 対話モード
```python
# 対話式モード（入力に制限あり）
integrated_langchain_mode()
```

### 方法3: 直接エージェント操作
```python
# エージェントを直接操作
from integrated_langchain import IntegratedLangChainAgent
agent = IntegratedLangChainAgent()
response = agent.process_query("カレンダーの予定を確認して")
print(response)
```

## 🎵 音声機能を使用する場合:
1. GoogleドライブをマウントしてSystem-Bert-VITS2のモデルを配置
2. パス: /content/drive/MyDrive/Style-Bert-VITS2/model_assets/yoshino_test/

## 📝 よくある質問例:
- "今日のタスクは？"
- "明日までにレポートを書くタスクを追加して"
- "完了したタスクを教えて"
- "来週の予定は？"
- "タスクの進捗状況を確認"
""")

if __name__ == "__main__":
    if is_colab_environment():
        print("🔧 GoogleColab環境が検出されました")
        colab_setup_guide()
        print("\n💡 まずは colab_quick_chat('質問内容') を試してください！")
    else:
        integrated_langchain_mode()