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
        
        # ひろゆき風応答システムの初期化
        self.hiroyuki_system = HiroyukiResponseSystem()
        
        # 音声合成システムの初期化
        self.tts_model = None
        self.tts_available = False
        self._initialize_tts_system()
        
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
    
    def _install_required_packages(self):
        """必要なパッケージを自動インストール"""
        import subprocess
        import sys
        
        packages = {
            'gtts': 'gTTS',
            'pygame': 'pygame', 
            'transformers': 'transformers',
            'torch': 'torch',
            'style-bert-vits2': 'style-bert-vits2'
        }
        
        installed = []
        for package_name, import_name in packages.items():
            try:
                __import__(import_name.lower().replace('-', '_'))
                print(f"✅ {package_name} 既にインストール済み")
            except ImportError:
                try:
                    print(f"📥 {package_name} インストール中...")
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install', package_name, '--quiet'
                    ])
                    installed.append(package_name)
                    print(f"✅ {package_name} インストール完了")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ {package_name} インストール失敗: {e}")
        
        if installed:
            print(f"🎉 新規インストール完了: {', '.join(installed)}")
        return len(installed) > 0

    def _is_colab_environment(self) -> bool:
        """Google Colab環境かどうかを判定"""
        try:
            import google.colab
            return True
        except ImportError:
            return False

    def _initialize_simple_tts(self):
        """Google Colab専用：シンプルな音声合成システム初期化"""
        print("🔊 【シンプルモード】音声合成システム初期化中...")
        
        try:
            # Google Colab環境確認
            import google.colab
            print("✅ Google Colab環境を確認")
        except ImportError:
            print("❌ Google Colab環境ではありません。通常モードにフォールバック")
            return self._initialize_tts_system_fallback()
        
        # test_yoshino_model_simple と完全に同じ処理を実行
        return self._execute_simple_model_load()

    def _execute_simple_model_load(self):
        """test_yoshino_model_simple と同じロジック"""
        try:
            print("📦 最小実行パターンでmodel_load.pyインポート...")
            
            # test_yoshino_model_simpleと全く同じ手順
            import os
            import tempfile
            
            # model_load.py を直接使用（最小実行と同じ）
            from model_load import load_model
            print("✅ model_load.py インポート成功")
            
            # シンプルなパス設定（test_yoshino_model_simpleと同じ）
            model_dir = "/content/drive/MyDrive/Style-Bert-VITS2/model_assets"
            model_name = "yoshino_test"
            
            if not os.path.exists(model_dir):
                print(f"❌ モデルディレクトリが存在しません: {model_dir}")
                print("💡 Google Driveがマウントされ、モデルが配置されているか確認してください")
                return self._initialize_gtts_fallback()
            
            print(f"🎯 モデル: {model_name}")
            print(f"📁 パス: {model_dir}")
            
            # ユーザー指定パターンでモデル読み込み（test_yoshino_model_simpleと同じ）
            print(f"sample_model = load_model('{model_name}', model_dir='{model_dir}', device='cuda')")
            sample_model = load_model(model_name, model_dir=model_dir, device="cuda")
            
            print("✅ sample_model 読み込み成功")
            
            # テスト実行して動作確認
            out_path = "/content/todoapp_simple_test.wav"
            test_text = "TODOアプリのシンプルモード初期化完了"
            
            print(f"🧪 初期化テスト実行: sample_model.inference('{test_text}', '{out_path}')")
            result = sample_model.inference(test_text, out_path)
            
            print(f"✅ 初期化テスト完了: {result}")
            if os.path.exists(out_path):
                size = os.path.getsize(out_path)
                print(f"📁 ファイルサイズ: {size} bytes")
            
            # 成功した場合、sample_modelを設定
            self.tts_model = sample_model
            self.tts_available = True
            print("✅ 【シンプルモード】TODOアプリ音声合成初期化成功")
            return
            
        except Exception as e:
            print(f"❌ シンプルモード失敗: {e}")
            print("⚠️ gTTSにフォールバックします")
            import traceback
            traceback.print_exc()
            return self._initialize_gtts_fallback()

    def _initialize_tts_system_fallback(self):
        """従来の複雑な初期化（フォールバック用）"""
        print("🔊 【従来モード】音声合成システム初期化中...")
        
        # 0. 必要なライブラリを自動インストール
        packages_installed = self._install_required_packages()
        if packages_installed:
            print("⚡ ライブラリインストール後、Pythonモジュールを再ロード中...")
            import importlib
            import sys
            # 新しくインストールされたモジュールを利用可能にする
            importlib.invalidate_caches()
        
        # 方法1: Style-Bert-VITS2を試行（model_load.py必須使用）

    def _initialize_gtts_fallback(self):
        """gTTSへの緊急フォールバック"""
        print("🔊 gTTS緊急フォールバック初期化中...")
        try:
            # 基本的なgTTS設定
            if self._is_colab_environment():
                self.tts_model = "gtts_file_only"
            else:
                self.tts_model = "gtts_with_audio"
            self.tts_available = True
            print("✅ gTTSフォールバック初期化成功")
        except Exception as e:
            print(f"❌ gTTSフォールバック失敗: {e}")
            self.tts_available = False

    def _initialize_tts_system(self):
        """音声合成システムを初期化（複数のフォールバック方式）"""
        
        # Google Colab環境では自動的にシンプルモードを使用
        if self._is_colab_environment():
            print("🎯 Google Colab環境検出：シンプルモードを使用します")
            return self._initialize_simple_tts()
        
        print("🔊 音声合成システム初期化中...")
        
        # 0. 必要なライブラリを自動インストール
        packages_installed = self._install_required_packages()
        if packages_installed:
            print("⚡ ライブラリインストール後、Pythonモジュールを再ロード中...")
            import importlib
            import sys
            # 新しくインストールされたモジュールを利用可能にする
            importlib.invalidate_caches()
        
        # 方法1: Style-Bert-VITS2を試行（model_load.py必須使用）
        try:
            print("🔧 model_load.py を使用してカスタムモデルをロード中...")
            
            # まず必要なモジュールが利用可能か確認
            self._ensure_model_load_dependencies()
            
            # model_load.py を使用してモデルロード
            loaded_model = self._load_style_bert_with_model_load()
            
            if loaded_model:
                self.tts_model = loaded_model
                self.tts_available = True
                print("✅ model_load.py によるカスタムモデル初期化成功")
                return
            else:
                print("⚠️ model_load.py によるカスタムモデル読み込みに失敗、フォールバックします")
                
        except Exception as style_bert_error:
            print(f"⚠️ model_load.py による Style-Bert-VITS2初期化失敗: {style_bert_error}")
            import traceback
            traceback.print_exc()
        
        # 方法2: gTTSを試行（軽量代替案）
        try:
            from gtts import gTTS
            
            # テスト音声生成（ファイル保存のみ）
            test_text = "テストです"
            tts = gTTS(text=test_text, lang='ja')
            test_file = "/tmp/test_tts.mp3"
            tts.save(test_file)
            
            # Google Colabの場合はpygame音声再生をスキップ
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(test_file)
                self.tts_model = "gtts_with_audio"
                print("✅ gTTS + pygame 音声合成システム利用可能")
            except (pygame.error, OSError) as audio_error:
                # 音声デバイスがない環境（Colab等）では音声ファイル生成のみ
                print(f"⚠️ 音声再生デバイスなし（{audio_error}）、ファイル生成のみ利用可能")
                self.tts_model = "gtts_file_only"
                print("✅ gTTS ファイル生成システム利用可能")
            
            self.tts_available = True
            return
            
        except Exception as gtts_error:
            print(f"⚠️ gTTS初期化失敗: {gtts_error}")
        
        # 方法3: システム音声（最後の手段）
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Darwin":  # macOS
                # macOS sayコマンドのテスト
                try:
                    result = subprocess.run(["say", "--version"], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        self.tts_model = "macos_say"
                        self.tts_available = True
                        print("✅ macOS say コマンド利用可能")
                        return
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    print("⚠️ macOS sayコマンドが見つかりません")
                    
            elif system == "Linux":
                # Linux espeak/festival/speakコマンドのテスト
                tts_commands = ["espeak", "festival", "spd-say"]
                for cmd in tts_commands:
                    try:
                        result = subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            self.tts_model = f"linux_{cmd}"
                            self.tts_available = True
                            print(f"✅ Linux {cmd} システム音声利用可能")
                            return
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                        
            elif system == "Windows":
                # Windows SAPI (PowerShell)のテスト
                try:
                    result = subprocess.run([
                        "powershell", "-Command", 
                        "Add-Type -AssemblyName System.Speech; exit 0"
                    ], capture_output=True, timeout=10)
                    if result.returncode == 0:
                        self.tts_model = "windows_sapi"
                        self.tts_available = True
                        print("✅ Windows SAPI 音声合成利用可能")
                        return
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    print("⚠️ Windows SAPI が利用できません")
                    
        except Exception as system_tts_error:
            print(f"⚠️ システム音声初期化失敗: {system_tts_error}")
        
        print("❌ 全ての音声合成方法が失敗。音声機能は無効化されます。")
        print("💡 アプリは音声なしで正常に動作します。")
    
    def test_tts_system(self):
        """音声合成システムのテスト実行"""
        print("\n🧪 音声合成システムテスト開始")
        print("="*50)
        
        if not self.tts_available:
            print("❌ 音声機能が利用できないため、テストをスキップします")
            return False
        
        test_text = "こんにちは、音声合成テストです"
        
        try:
            print(f"🔊 使用中の音声モデル: {self.tts_model}")
            print(f"📝 テスト文章: {test_text}")
            
            # 音声合成テスト
            self.speak_response(test_text)
            
            print("✅ 音声合成テスト完了")
            return True
            
        except Exception as test_error:
            print(f"❌ 音声合成テスト失敗: {test_error}")
            return False
    
    def get_system_info(self):
        """システム情報を取得"""
        import platform
        import sys
        
        info = {
            "platform": platform.system(),
            "python_version": sys.version,
            "tts_available": self.tts_available,
            "tts_model": self.tts_model if self.tts_available else "なし",
            "llm_available": self.llm_available
        }
        
        print("\n💻 システム情報")
        print("="*30)
        for key, value in info.items():
            print(f"{key}: {value}")
        
        return info
    
    def _ensure_model_load_dependencies(self):
        """model_load.py の依存関係が利用可能か確認・修正"""
        try:
            print("🔍 model_load.py 依存関係チェック中...")
            
            # 1. config.py 確認
            try:
                from config import get_config
                config = get_config()
                print("✅ config.py インポート成功")
            except ImportError as e:
                print(f"❌ config.py インポートエラー: {e}")
                raise
            
            # 2. scipy.io.wavfile 確認
            try:
                from scipy.io import wavfile
                print("✅ scipy.io.wavfile インポート成功")
            except ImportError:
                print("📥 scipy インストール中...")
                import subprocess
                import sys
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scipy'])
                from scipy.io import wavfile
                print("✅ scipy インストール完了")
            
            # 3. torch_device_onnx_compat 確認
            try:
                from torch_device_onnx_compat import torch_device_to_onnx_providers
                print("✅ torch_device_onnx_compat インポート成功")
            except ImportError as e:
                print(f"❌ torch_device_onnx_compat インポートエラー: {e}")
                # このファイルは既に存在するはずなので、パスの問題かもしれない
                import os
                current_dir = os.path.dirname(__file__)
                compat_file = os.path.join(current_dir, 'torch_device_onnx_compat.py')
                if os.path.exists(compat_file):
                    print(f"✅ {compat_file} は存在します")
                else:
                    print(f"❌ {compat_file} が見つかりません")
                raise
            
            # 4. style_bert_vits2 関連モジュール確認
            try:
                from style_bert_vits2.constants import Languages
                from style_bert_vits2.tts_model import TTSModel
                print("✅ style_bert_vits2 モジュール インポート成功")
            except ImportError as e:
                print(f"❌ style_bert_vits2 インポートエラー: {e}")
                # macOS環境での特別なエラーメッセージ
                if "pyopenjtalk" in str(e).lower() or "cmake" in str(e).lower():
                    print("🔧 macOS環境でのStyle-Bert-VITS2ビルドエラーが検出されました")
                    print("💡 Google Colab環境での使用を推奨します")
                    raise Exception("Style-Bert-VITS2はmacOS環境でのビルドに制限があります。Google Colabでの実行を推奨します。")
                else:
                    raise Exception(f"Style-Bert-VITS2のインポートに失敗: {e}")
            
            print("✅ model_load.py 依存関係チェック完了")
            
        except Exception as e:
            print(f"❌ model_load.py 依存関係エラー: {e}")
            raise

    def _load_style_bert_with_model_load(self):
        """model_load.py を使用してStyle-Bert-VITS2モデルをロード"""
        try:
            print("🔧 model_load.py によるモデルロード開始...")
            
            # model_load.py をインポート
            from model_load import load_model, list_models
            
            # Google Driveのカスタムモデルパスを確認
            model_configs = [
                {
                    "model_dir": "/content/drive/MyDrive/Style-Bert-VITS2/model_assets",
                    "model_names": ["yoshino_test", "hiroyuki"]
                },
                {
                    "model_dir": "/content",
                    "model_names": ["hiroyuki_model", "yoshino_model"]
                }
            ]
            
            for config in model_configs:
                model_dir = config["model_dir"]
                
                if not os.path.exists(model_dir):
                    print(f"❌ ディレクトリが存在しません: {model_dir}")
                    continue
                
                print(f"🔍 モデル検索中: {model_dir}")
                
                try:
                    # list_models でモデル一覧を取得
                    available_models = list_models(model_dir)
                    print(f"📂 利用可能なモデル: {available_models}")
                    
                    # 優先順位でモデルを試行
                    for model_name in config["model_names"]:
                        if model_name in available_models:
                            print(f"🎯 モデル '{model_name}' を model_load.py でロード中...")
                            
                            import torch
                            device = "cuda" if torch.cuda.is_available() else "cpu"
                            
                            # model_load.py の load_model 関数を使用（ユーザー指定パターン）
                            print(f"📋 使用例パターン:")
                            print(f"   from model_load import load_model")
                            print(f"   sample_model = load_model('{model_name}', model_dir='{model_dir}', device='{device}')")
                            print(f"   sample_model.inference('テスト文章', '/content/out.wav')")
                            print(f"")
                            
                            loaded_model = load_model(
                                model_name,  # モデル名を第一引数として指定
                                model_dir=model_dir,  # model_dirをキーワード引数として明示
                                device=device,  # deviceをキーワード引数として明示
                                preload_onnx_bert=False,  # ONNX BERTは無効化
                                force_reload=False
                            )
                            
                            print(f"✅ model_load.py によるモデルロード成功:")
                            print(f"  - モデル名: {loaded_model.info.model_name}")
                            print(f"  - モデルパス: {loaded_model.info.model_path}")
                            try:
                                print(f"  - 話者: {list(loaded_model.spk2id.keys())}")
                                print(f"  - スタイル: {list(loaded_model.style2id.keys())}")
                            except:
                                print("  - 話者・スタイル情報の取得に失敗")
                            
                            # サンプル推論テスト（ユーザー指定パターンのテスト）
                            print(f"🧪 sample_model.inference() テスト実行...")
                            try:
                                import tempfile
                                temp_dir = tempfile.gettempdir()
                                test_output = os.path.join(temp_dir, "style_bert_test.wav")
                                
                                # ユーザー指定パターンと同じ形式でテスト
                                loaded_model.inference("テスト音声合成", test_output)
                                print(f"✅ sample_model.inference() テスト成功: {test_output}")
                                
                                if os.path.exists(test_output):
                                    print(f"📁 生成ファイルサイズ: {os.path.getsize(test_output)} bytes")
                                
                            except Exception as test_error:
                                print(f"⚠️ sample_model.inference() テスト失敗: {test_error}")
                            
                            return loaded_model
                            
                except Exception as model_error:
                    print(f"⚠️ モデル '{model_dir}' 処理エラー: {model_error}")
                    continue
            
            print("❌ model_load.py で利用可能なカスタムモデルが見つかりませんでした")
            return None
            
        except ImportError as import_error:
            print(f"❌ model_load.py インポートエラー: {import_error}")
            import traceback
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"❌ model_load.py によるモデルロードエラー: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _load_style_bert_model_direct(self):
        """Style-Bert-VITS2モデルを直接ロード（model_load.py依存なし）"""
        try:
            print("🔧 Style-Bert-VITS2カスタムモデル直接ロード開始...")
            
            # Google Driveのカスタムモデルパスを確認
            model_configs = [
                {
                    "model_dir": "/content/drive/MyDrive/Style-Bert-VITS2/model_assets",
                    "model_names": ["yoshino_test", "hiroyuki"]
                },
                {
                    "model_dir": "/content",
                    "model_names": ["hiroyuki_model", "yoshino_model"]
                }
            ]
            
            for config in model_configs:
                model_dir = config["model_dir"]
                
                if not os.path.exists(model_dir):
                    print(f"❌ ディレクトリが存在しません: {model_dir}")
                    continue
                
                print(f"🔍 モデル検索中: {model_dir}")
                
                for model_name in config["model_names"]:
                    model_path = os.path.join(model_dir, model_name)
                    
                    if not os.path.exists(model_path):
                        print(f"❌ モデルパス存在しません: {model_path}")
                        continue
                    
                    print(f"📁 モデルディレクトリ発見: {model_path}")
                    
                    # 必須ファイル確認
                    config_file = os.path.join(model_path, "config.json")
                    style_file = os.path.join(model_path, "style_vectors.npy")
                    
                    # モデルファイル検索
                    model_file = None
                    for ext in [".safetensors", ".pth", ".pt"]:
                        candidate = os.path.join(model_path, f"model{ext}")
                        if os.path.exists(candidate):
                            model_file = candidate
                            break
                    
                    if not os.path.exists(config_file):
                        print(f"❌ config.json が見つかりません: {config_file}")
                        continue
                    
                    if not model_file:
                        print(f"❌ モデルファイルが見つかりません: {model_path}")
                        continue
                    
                    print(f"✅ 必要ファイル確認完了:")
                    print(f"  - config: {config_file}")
                    print(f"  - model: {model_file}")
                    print(f"  - style: {style_file}")
                    
                    try:
                        # Style-Bert-VITS2の初期化
                        self._initialize_style_bert_dependencies()
                        
                        # TTSModelを直接作成
                        from style_bert_vits2.tts_model import TTSModel
                        import torch
                        
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                        print(f"🔧 使用デバイス: {device}")
                        
                        # カスタムロードモデルクラス
                        class CustomLoadedModel:
                            def __init__(self, model_path, config_path, style_path, device):
                                self.tts_model = TTSModel(
                                    model_path=model_path,
                                    config_path=config_path,
                                    style_vec_path=style_path if os.path.exists(style_path) else None,
                                    device=device
                                )
                                self.model_name = model_name
                                
                            def inference(self, text, output_path=None, **kwargs):
                                """音声生成（LoadedModelインターフェース互換）"""
                                if output_path:
                                    import tempfile
                                    from scipy.io import wavfile
                                    
                                    # Style-Bert-VITS2で音声生成
                                    sr, audio = self.tts_model.infer(text=text)
                                    
                                    # WAVファイルとして保存
                                    wavfile.write(output_path, sr, audio)
                                    return output_path
                                else:
                                    # 音声データのみ返す
                                    return self.tts_model.infer(text=text)
                            
                            def infer(self, text, **kwargs):
                                """従来のinferインターフェース"""
                                return self.tts_model.infer(text=text, **kwargs)
                        
                        # カスタムモデルインスタンス作成
                        custom_model = CustomLoadedModel(
                            model_path=model_file,
                            config_path=config_file,
                            style_path=style_file,
                            device=device
                        )
                        
                        print(f"✅ カスタムモデル '{model_name}' 読み込み完了")
                        return custom_model
                        
                    except Exception as load_error:
                        print(f"❌ モデル '{model_name}' 読み込みエラー: {load_error}")
                        continue
            
            print("❌ 利用可能なカスタムモデルが見つかりませんでした")
            return None
            
        except Exception as e:
            print(f"❌ 直接モデルロードエラー: {e}")
            return None
    
    def _initialize_style_bert_dependencies(self):
        """Style-Bert-VITS2の依存関係を初期化"""
        try:
            print("🔧 Style-Bert-VITS2依存関係初期化中...")
            
            # pyopenjtalk初期化
            try:
                from style_bert_vits2.nlp.japanese import pyopenjtalk_worker
                from style_bert_vits2.nlp.japanese.user_dict import update_dict
                
                pyopenjtalk_worker.initialize_worker()
                update_dict()
                print("✅ pyopenjtalk初期化完了")
            except Exception as pyopenjtalk_error:
                print(f"⚠️ pyopenjtalk初期化エラー: {pyopenjtalk_error}")
            
            # BERT初期化
            try:
                from style_bert_vits2.nlp import bert_models
                from style_bert_vits2.constants import Languages
                import torch
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # 日本語BERTモデルロード
                bert_models.load_model(Languages.JP, device_map=device)
                bert_models.load_tokenizer(Languages.JP)
                print("✅ BERT初期化完了")
                
            except Exception as bert_error:
                print(f"⚠️ BERT初期化エラー: {bert_error}")
                # BERTエラーでも続行
                pass
                
        except Exception as e:
            print(f"⚠️ 依存関係初期化エラー: {e}")
    
    def diagnose_tts_system(self):
        """TTS システムの詳細診断"""
        print("\n🔍 TTS システム診断開始")
        print("="*60)
        
        # 1. 基本情報
        print("📊 基本情報:")
        print(f"  - TTS利用可能: {self.tts_available}")
        print(f"  - TTSモデル: {self.tts_model}")
        print(f"  - LLM利用可能: {self.llm_available}")
        
        # 2. ファイルシステム確認
        print("\n📁 ファイルシステム確認:")
        model_paths = [
            "/content/drive/MyDrive/Style-Bert-VITS2/model_assets/yoshino_test",
            "/content/drive/MyDrive/Style-Bert-VITS2/model_assets/hiroyuki",
            "/content/hiroyuki_model",
            "/content/yoshino_model"
        ]
        
        for path in model_paths:
            exists = os.path.exists(path)
            status = "✅" if exists else "❌"
            print(f"  {status} {path}")
            
            if exists:
                try:
                    files = os.listdir(path)
                    config_exists = 'config.json' in files
                    model_files = [f for f in files if f.endswith(('.safetensors', '.pth', '.pt'))]
                    style_exists = 'style_vectors.npy' in files
                    
                    print(f"    📄 config.json: {'✅' if config_exists else '❌'}")
                    print(f"    🤖 モデルファイル: {len(model_files)} 個 {model_files[:3]}...")
                    print(f"    🎨 style_vectors.npy: {'✅' if style_exists else '❌'}")
                except Exception as e:
                    print(f"    ❌ ディレクトリ読み取りエラー: {e}")
        
        # 3. Style-Bert-VITS2モジュール確認
        print("\n🔧 Style-Bert-VITS2モジュール確認:")
        try:
            import style_bert_vits2
            print("  ✅ style_bert_vits2モジュール利用可能")
            
            try:
                from style_bert_vits2.tts_model import TTSModel
                print("  ✅ TTSModel インポート可能")
            except Exception as e:
                print(f"  ❌ TTSModel インポートエラー: {e}")
                
            try:
                from style_bert_vits2.nlp import bert_models
                print("  ✅ bert_models インポート可能")
                
                if hasattr(bert_models, 'DEFAULT_BERT_TOKENIZER_PATHS'):
                    paths = getattr(bert_models, 'DEFAULT_BERT_TOKENIZER_PATHS', {})
                    print(f"  📝 BERT設定: {paths}")
                else:
                    print("  ⚠️ DEFAULT_BERT_TOKENIZER_PATHSが見つかりません")
                    
            except Exception as e:
                print(f"  ❌ bert_models インポートエラー: {e}")
                
        except ImportError as e:
            print(f"  ❌ style_bert_vits2インポートエラー: {e}")
        
        # 4. 環境変数確認
        print("\n🌐 環境変数確認:")
        env_vars = [
            'STYLE_BERT_VITS2_BERT_JP',
            'BERT_MODELS_JP',
            'BERT_BASE_DIR',
            'JP_BERT_PATH'
        ]
        
        for var in env_vars:
            value = os.environ.get(var, "未設定")
            print(f"  {var}: {value}")
        
        print("\n" + "="*60)
        print("🔍 TTS システム診断完了")
    
    def download_voice_file(self, text: str, filename: str = None):
        """Google Colab環境で音声ファイルを生成してダウンロード可能にする"""
        try:
            from gtts import gTTS
            from google.colab import files
            import time
            
            if not filename:
                filename = f"hiroyuki_voice_{int(time.time())}.mp3"
            
            # 音声ファイル生成
            tts = gTTS(text=text, lang='ja')
            filepath = f"/content/{filename}"
            tts.save(filepath)
            
            print(f"📁 音声ファイル生成完了: {filepath}")
            print("🎧 ファイルをダウンロードしています...")
            
            # ダウンロード実行
            files.download(filepath)
            print("✅ ダウンロード完了！")
            
        except ImportError:
            print("⚠️ Google Colab環境でのみ利用可能です")
        except Exception as e:
            print(f"❌ 音声ファイルダウンロードエラー: {e}")
    
    def speak_response(self, text: str):
        """応答を音声で読み上げる"""
        if not self.tts_available:
            print("🔇 音声機能が利用できません")
            return
        
        try:
            # 長いテキストを適切に処理
            if len(text) > 200:
                text = text[:200] + "..."
                print("📝 長い文章のため200文字で切り詰めました")
            
            if self.tts_model in ["gtts_with_audio", "gtts_file_only"]:
                from gtts import gTTS
                import tempfile
                
                tts = gTTS(text=text, lang='ja')
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    tts.save(temp_file.name)
                    
                    if self.tts_model == "gtts_with_audio":
                        # 音声再生可能な環境
                        try:
                            import pygame
                            pygame.mixer.init()
                            pygame.mixer.music.load(temp_file.name)
                            pygame.mixer.music.play()
                            
                            # 再生完了まで待機（タイムアウト付き）
                            timeout = 30  # 30秒でタイムアウト
                            elapsed = 0
                            while pygame.mixer.music.get_busy() and elapsed < timeout:
                                time.sleep(0.1)
                                elapsed += 0.1
                                
                            if elapsed >= timeout:
                                pygame.mixer.music.stop()
                                print("⚠️ 音声再生タイムアウト")
                            else:
                                print("🎵 gTTS音声再生完了")
                        except (pygame.error, OSError):
                            # 音声再生失敗時はファイル生成のみ
                            print(f"🎵 gTTS音声ファイル生成完了: {temp_file.name}")
                            print("💡 Google Colabの場合、ファイルをダウンロードして再生できます")
                    else:
                        # ファイル生成のみ（Colab環境）
                        print(f"🎵 gTTS音声ファイル生成完了: {temp_file.name}")
                        print("💡 Google Colabでファイルをダウンロード可能です")
                        
                        # Colab環境の場合、ファイルをダウンロード可能にする
                        try:
                            from google.colab import files
                            import shutil
                            import time
                            
                            # 保存ファイル名を作成
                            save_filename = f"hiroyuki_voice_{int(time.time())}.mp3"
                            shutil.copy(temp_file.name, f"/content/{save_filename}")
                            print(f"📁 音声ファイルを保存しました: /content/{save_filename}")
                            
                            # ダウンロード提案（ユーザーが選択）
                            print("🎧 音声ファイルをダウンロードしますか？")
                            # files.download(f"/content/{save_filename}")  # 自動実行はしない
                        except ImportError:
                            # Colab環境でない場合
                            pass
                
                # 一時ファイル削除（必要に応じて）
                if self.tts_model == "gtts_with_audio":
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                
            elif self.tts_model == "macos_say":
                import subprocess
                subprocess.run(["say", text], check=True, timeout=30)
                print("🎵 macOS音声再生完了")
                
            elif self.tts_model.startswith("linux_"):
                import subprocess
                cmd = self.tts_model.split("_")[1]
                if cmd == "espeak":
                    subprocess.run(["espeak", text], check=True, timeout=30)
                elif cmd == "festival":
                    subprocess.run(["festival", "--tts"], input=text, text=True, check=True, timeout=30)
                elif cmd == "spd-say":
                    subprocess.run(["spd-say", text], check=True, timeout=30)
                print(f"🎵 {cmd}音声再生完了")
                
            elif self.tts_model == "windows_sapi":
                import subprocess
                ps_command = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{text.replace('"', "'")}")'
                subprocess.run(["powershell", "-Command", ps_command], check=True, timeout=30)
                print("🎵 Windows SAPI音声再生完了")
                
            elif hasattr(self.tts_model, 'inference'):  # model_load.py LoadedModel
                # 【シンプルモード】LoadedModelのinference関数を使用
                print(f"🎵 【シンプルモード】Style-Bert-VITS2音声生成中...")
                
                try:
                    import tempfile
                    import time
                    
                    # シンプルなファイル名で生成
                    output_path = f"/content/yoshino_voice_{int(time.time())}.wav"
                    
                    # ユーザー指定パターンと同じ呼び出し方
                    result_path = self.tts_model.inference(text, output_path)
                    
                    print(f"✅ yoshino音声生成完了: {result_path}")
                    
                    # ファイル存在確認
                    if os.path.exists(result_path):
                        size = os.path.getsize(result_path)
                        print(f"📁 ファイルサイズ: {size} bytes")
                    
                    # Google Colab環境での保存は既にresult_pathに完了
                    print(f"🎧 Google Colabで再生可能: {result_path}")
                    
                except Exception as inference_error:
                    print(f"❌ inference実行エラー: {inference_error}")
                    # 詳細なエラー情報を表示
                    import traceback
                    traceback.print_exc()
                    print("⚠️ gTTSにフォールバックします")
                    # gTTSでのフォールバック実行
                    self._speak_with_gtts(text)
                        
            elif hasattr(self.tts_model, 'infer'):  # 従来のTTSModel（フォールバック）
                audio = self.tts_model.infer(text=text)
                print("🎵 Style-Bert-VITS2音声生成完了")
                
            else:
                print(f"⚠️ 不明な音声モデル: {self.tts_model}")
                
        except subprocess.TimeoutExpired:
            print("⚠️ 音声再生がタイムアウトしました")
        except Exception as speak_error:
            print(f"⚠️ 音声再生エラー: {speak_error}")
            # 音声エラー時は音声機能を無効化
            self.tts_available = False
            print("🔇 音声機能を無効化しました")

    def _speak_with_gtts(self, text: str):
        """gTTSでのフォールバック音声生成"""
        try:
            print("🔊 gTTSフォールバック実行中...")
            from gtts import gTTS
            import tempfile
            import time
            
            tts = gTTS(text=text, lang='ja')
            output_path = f"/content/gtts_fallback_{int(time.time())}.mp3"
            tts.save(output_path)
            print(f"✅ gTTS音声生成完了: {output_path}")
            
        except Exception as gtts_error:
            print(f"❌ gTTSフォールバックも失敗: {gtts_error}")

    def test_voice_synthesis(self, text: str = "こんにちは、TODOアプリの音声合成テストです"):
        """音声合成のテスト"""
        print("🧪 TODOアプリ音声合成テスト開始...")
        print(f"📝 テスト文章: {text}")
        print(f"🎯 使用モデル: {self.tts_model}")
        print(f"🌐 Colab環境: {self._is_colab_environment()}")
        
        if self.tts_available:
            self.speak_response(text)
        else:
            print("❌ 音声機能が利用できません")
    
    def process_query(self, user_input: str) -> str:
        """ユーザーの質問を処理"""
        start_time = time.time()
        
        try:
            # 怒るべきかどうかをキーワード検索でチェック
            if self._should_get_angry(user_input):
                # シンプルひろゆき風システムを使用（インポートエラー対応）
                try:
                    from simple_hiroyuki_chat import SimpleHiroyukiChat
                except ImportError:
                    print("⚠️ simple_hiroyuki_chat モジュールが見つかりません。内蔵のひろゆき風応答を使用します。")
                    # 代替処理：内蔵のHiroyukiResponseSystemを使用
                    SimpleHiroyukiChat = None
                
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
                if SimpleHiroyukiChat:
                    hiroyuki_chat = SimpleHiroyukiChat()
                    hiroyuki_input = f"ユーザーが{incomplete_count}個ものタスクを溜め込んでいます。{user_input}"
                    hiroyuki_response = hiroyuki_chat.get_hiroyuki_response(hiroyuki_input)
                else:
                    # 内蔵システムを使用
                    hiroyuki_response = self.hiroyuki_system.get_hiroyuki_response(
                        f"ユーザーが{incomplete_count}個ものタスクを溜め込んでいます。{user_input}", 
                        incomplete_count
                    )
                
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
        
        # 5. 音声で応答（バックグラウンド実行）
        if self.tts_available and response:
            try:
                # 音声合成を別スレッドで実行（メイン処理をブロックしない）
                import threading
                speech_thread = threading.Thread(target=self.speak_response, args=(response,))
                speech_thread.daemon = True
                speech_thread.start()
            except Exception as speech_error:
                print(f"⚠️ 音声合成スレッドエラー: {speech_error}")
        
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
            try:
                from simple_hiroyuki_chat import SimpleHiroyukiChat
            except ImportError:
                # simple_hiroyuki_chatが見つからない場合は内蔵システムを使用
                return self.hiroyuki_system.get_hiroyuki_response(
                    original_response, 
                    self._count_incomplete_tasks()
                )
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
    
    def _count_incomplete_tasks(self) -> int:
        """未完了タスク数をカウント"""
        return self._get_incomplete_task_count()
    

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
            
        # style_bert_vits2の存在確認と詳細チェック
        import importlib.util
        spec = importlib.util.find_spec("style_bert_vits2")
        if spec is None:
            print("⚠️ style_bert_vits2ライブラリがインストールされていません")
            print("💡 Colabで !pip install style-bert-vits2 を実行してください")
            return None
        
        # TTSModelクラスの存在確認
        try:
            from style_bert_vits2.tts_model import TTSModel
            print("✓ TTSModelクラスのインポートに成功しました")
        except ImportError as e:
            print(f"⚠️ TTSModelクラスのインポートに失敗: {e}")
            print("💡 style_bert_vits2が古いバージョンの可能性があります")
            return None
        
        # 日本語BERTモデルの初期化
        try:
            print("🔄 Style-Bert-VITS2の日本語BERTモデルを初期化中...")
            from style_bert_vits2 import bert_models
            from style_bert_vits2.constants import Languages
            
            # 日本語BERTモデルとトークナイザーをロード
            bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            print("✓ 日本語BERTモデルの初期化に成功しました")
        except Exception as bert_error:
            print(f"⚠️ BERTモデル初期化エラー: {bert_error}")
            print("💡 フォールバック用BERTモデルを試行します...")
            try:
                bert_models.load_model(Languages.JP, "cl-tohoku/bert-base-japanese-v3")
                bert_models.load_tokenizer(Languages.JP, "cl-tohoku/bert-base-japanese-v3")
                print("✓ フォールバックBERTモデルの初期化に成功しました")
            except Exception as fallback_error:
                print(f"⚠️ フォールバックBERTモデル初期化も失敗: {fallback_error}")
                print("💡 音声合成でBERTエラーが発生する可能性があります")
            
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


def initialize_bert_for_japanese() -> bool:
    """Style-Bert-VITS2用の日本語BERTモデル初期化"""
    try:
        print("🔄 Style-Bert-VITS2の日本語BERTモデルを初期化中...")
        from style_bert_vits2 import bert_models
        from style_bert_vits2.constants import Languages
        
        # メインのBERTモデル（推奨）
        try:
            bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
            print("✓ 日本語BERTモデル（deberta-v2-large）の初期化に成功")
            return True
        except Exception as main_error:
            print(f"⚠️ メインBERTモデルエラー: {main_error}")
            
            # フォールバックモデル
            try:
                bert_models.load_model(Languages.JP, "cl-tohoku/bert-base-japanese-v3")
                bert_models.load_tokenizer(Languages.JP, "cl-tohoku/bert-base-japanese-v3")
                print("✓ フォールバックBERTモデル（bert-base-japanese）の初期化に成功")
                return True
            except Exception as fallback_error:
                print(f"❌ フォールバックBERTモデルも失敗: {fallback_error}")
                return False
                
    except ImportError as e:
        print(f"❌ BERTモデル機能のインポートに失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ BERT初期化で予期しないエラー: {e}")
        return False

def start_background_tts_server(model_dir: str, model_name: str, device: str) -> Optional[object]:
    """バックグラウンドでTTSサーバーを起動（model_load.py方式、レガシー関数）"""
    print("⚠️ この関数は廃止予定です。model_load.pyを直接使用してください。")
    try:
        import threading
        import time
        from pathlib import Path
        import torch
        import os
        import sys
        
        # BERT問題を事前に解決
        print("🔧 BERT設定の問題を解決中...")
        try:
            # 1. transformersライブラリの動的インストール（必要に応じて）
            try:
                from transformers import AutoTokenizer, AutoModel
                print("✅ transformers利用可能")
            except ImportError:
                print("📥 transformersライブラリをインストール中...")
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'transformers', 'torch'])
                from transformers import AutoTokenizer, AutoModel
                print("✅ transformersインストール完了")
            
            # 2. BERTモデルのGoogle Colab対応準備
            # カスタムモデル用BERTディレクトリを設定
            if "/content/drive/" in model_dir:
                # Google Driveの場合はそのモデル用のBERTディレクトリを使用
                bert_dir = Path(model_dir).parent / 'bert_models'
            else:
                # ローカルの場合は従来通り
                bert_dir = Path(model_dir).parent / 'bert_models' / 'japanese'
            
            bert_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 BERTモデルディレクトリ: {bert_dir}")
            
            # 複数のBERTモデル候補を試行
            bert_model_candidates = [
                'ku-nlp/deberta-v2-large-japanese-char-wwm',
                'cl-tohoku/bert-large-japanese-char-v2', 
                'cl-tohoku/bert-base-japanese-v3'
            ]
            
            bert_success = False
            for bert_model in bert_model_candidates:
                if (bert_dir / 'config.json').exists():
                    bert_success = True
                    print(f"✅ 既存BERTモデル発見: {bert_dir}")
                    break
                    
                print(f"📥 {bert_model} BERTモデル準備中...")
                try:
                    tokenizer = AutoTokenizer.from_pretrained(
                        bert_model,
                        cache_dir=str(bert_dir)
                    )
                    model = AutoModel.from_pretrained(
                        bert_model,
                        cache_dir=str(bert_dir)
                    )
                    bert_success = True
                    print(f"✅ {bert_model} BERTモデル準備完了")
                    break
                except Exception as download_error:
                    print(f"⚠️ {bert_model} ダウンロードエラー: {download_error}")
                    continue
            
            if not bert_success:
                print("⚠️ 全てのBERTモデル準備に失敗、音声合成でエラーが発生する可能性があります")
            
            # 3. Style-Bert-VITS2のBERT設定を完全パッチ
            try:
                from style_bert_vits2.nlp import bert_models
                
                # DEFAULT_BERT_TOKENIZER_PATHSを強制設定
                if not hasattr(bert_models, 'DEFAULT_BERT_TOKENIZER_PATHS'):
                    bert_models.DEFAULT_BERT_TOKENIZER_PATHS = {}
                
                bert_models.DEFAULT_BERT_TOKENIZER_PATHS['JP'] = str(bert_dir)
                
                # Languagesクラスの完全パッチ
                if not hasattr(bert_models, 'Languages'):
                    # Languagesクラス自体を作成
                    class Languages:
                        pass
                    bert_models.Languages = Languages()
                
                # JP言語の動的設定（複数の方法で確実に設定）
                class JP:
                    bert_tokenizer_path = str(bert_dir)
                    code = 'JP'
                    
                    @classmethod
                    def get_path(cls):
                        return str(bert_dir)
                    
                    def __str__(self):
                        return 'JP'
                
                # JP設定の複数方法での追加
                bert_models.Languages.JP = JP()
                setattr(bert_models.Languages, 'JP', JP())
                
                # モジュール内のグローバル変数としても設定
                setattr(bert_models, 'JP_BERT_PATH', str(bert_dir))
                
                # 環境変数も設定（最強の保険）
                os.environ['STYLE_BERT_VITS2_BERT_JP'] = str(bert_dir)
                os.environ['BERT_MODELS_JP'] = str(bert_dir)
                
                print(f"✅ 完全BERT設定パッチ完了: {bert_dir}")
                print(f"✅ DEFAULT_BERT_TOKENIZER_PATHS: {getattr(bert_models, 'DEFAULT_BERT_TOKENIZER_PATHS', {})}")
                print(f"✅ Languages.JP: {getattr(bert_models.Languages, 'JP', None)}")
                
            except Exception as patch_error:
                print(f"⚠️ BERTパッチエラー、モンキーパッチを試行: {patch_error}")
                
                # モンキーパッチによる強制設定
                try:
                    import sys
                    import types
                    
                    # bert_modelsモジュールを取得または作成
                    if 'style_bert_vits2.nlp.bert_models' in sys.modules:
                        bert_mod = sys.modules['style_bert_vits2.nlp.bert_models']
                    else:
                        bert_mod = types.ModuleType('bert_models')
                        sys.modules['style_bert_vits2.nlp.bert_models'] = bert_mod
                    
                    # 強制的に設定
                    bert_mod.DEFAULT_BERT_TOKENIZER_PATHS = {'JP': str(bert_dir)}
                    
                    # Languagesオブジェクト作成
                    languages_obj = types.SimpleNamespace()
                    jp_obj = types.SimpleNamespace()
                    jp_obj.bert_tokenizer_path = str(bert_dir)
                    jp_obj.code = 'JP'
                    languages_obj.JP = jp_obj
                    bert_mod.Languages = languages_obj
                    
                    print(f"✅ モンキーパッチによるBERT設定完了: {bert_dir}")
                    
                except Exception as monkey_error:
                    print(f"⚠️ モンキーパッチも失敗: {monkey_error}")
                    # 環境変数のみで頑張る
                    os.environ['BERT_BASE_DIR'] = str(bert_dir.parent)
                    os.environ['JP_BERT_PATH'] = str(bert_dir)
                    print(f"✅ 環境変数によるBERT設定: {bert_dir}")
        
        except Exception as bert_setup_error:
            print(f"⚠️ BERT設定エラー、TTS初期化を続行: {bert_setup_error}")
        
        # 新しいAPI: TTSModelを直接使用
        from style_bert_vits2.tts_model import TTSModel
        
        # モデルファイル構造の確認と自動検索（パス処理修正）
        model_dir_path = Path(model_dir)
        if model_name:
            model_path = model_dir_path / model_name
        else:
            model_path = model_dir_path
        
        # パスの正規化と存在確認
        if not model_path.exists():
            print(f"⚠️ モデルディレクトリが存在しません: {model_path}")
            print(f"📁 検索対象ディレクトリ: {model_dir_path}")
            if model_dir_path.exists():
                print(f"📂 利用可能なファイル: {list(model_dir_path.iterdir())}")
            return None
        
        # 基本的な必須ファイル（Pathオブジェクトとして安全に処理）
        required_files = {}
        config_file = model_path / 'config.json'
        style_vectors_file = model_path / 'style_vectors.npy'
        
        if config_file.exists():
            required_files['config.json'] = config_file
        if style_vectors_file.exists():
            required_files['style_vectors.npy'] = style_vectors_file
        
        # モデルファイルの候補を安全に検索
        model_file_candidates = []
        try:
            # 明示的なファイル名での検索
            for ext in ['.safetensors', '.pth', '.pt', '.ckpt']:
                explicit_file = model_path / f'model{ext}'
                if explicit_file.exists():
                    model_file_candidates.append(explicit_file)
            
            # glob検索（例外処理付き）
            for pattern in ['*.safetensors', '*.pth', '*.pt', '*.ckpt']:
                try:
                    model_file_candidates.extend(list(model_path.glob(pattern)))
                except OSError as glob_error:
                    print(f"⚠️ Globパターン {pattern} 検索エラー: {glob_error}")
        except Exception as search_error:
            print(f"⚠️ モデルファイル検索エラー: {search_error}")
        
        # 重複除去
        model_file_candidates = list(set(model_file_candidates))
        
        model_file = None
        for candidate in model_file_candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    model_file = candidate
                    print(f"✓ モデルファイル発見: {candidate}")
                    break
            except Exception as candidate_error:
                print(f"⚠️ ファイル確認エラー {candidate}: {candidate_error}")
        
        if model_file is None:
            print(f"❌ モデルファイルが見つかりません:")
            print(f"   検索対象: {[str(c) for c in model_file_candidates[:6]]}")  # 最初の6個を表示
            print(f"   ディレクトリの内容: {list(model_path.glob('*')) if model_path.exists() else 'ディレクトリが存在しません'}")
            return None
        
        # モデルファイルを確定
        required_files['model'] = model_file
        
        # その他のファイル存在確認
        missing_files = []
        for file_type, file_path in required_files.items():
            if file_type == 'model':
                continue  # 既にチェック済み
            if not file_path.exists():
                missing_files.append(f"{file_type}: {file_path}")
        
        if missing_files:
            print(f"⚠️ 一部のファイルが見つかりません:")
            for missing in missing_files:
                print(f"   - {missing}")
            
            # style_vectors.npyが見つからない場合は作成を試行
            if 'style_vectors.npy' in [m.split(':')[0] for m in missing_files]:
                print(f"💡 style_vectors.npyが見つからないため、デフォルトを使用します")
                # 簡易的な空のstyle vectorsファイルを作成
                import numpy as np
                try:
                    np.save(model_path / 'style_vectors.npy', np.array([]))
                    required_files['style_vectors.npy'] = model_path / 'style_vectors.npy'
                    print(f"✓ デフォルトのstyle_vectors.npyを作成しました")
                except Exception as e:
                    print(f"⚠️ style_vectors.npy作成に失敗: {e}")
                    return None
        
        print(f"✅ モデルファイル構造確認完了: {model_name}")
        
        # デバイス設定
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                print("✓ GPU(CUDA)を使用します")
            else:
                device = "cpu" 
                print("⚠️ GPUが利用できません。CPUを使用します")
        
        print(f"📁 TTSModelを直接初期化中... (パス: {model_path})")
        
        # BERTモデルの事前初期化
        if not initialize_bert_for_japanese():
            print("⚠️ BERTモデルの初期化に失敗しましたが、TTSModel作成を続行します")
        
        # TTSModelを直接作成（新しいAPI）
        try:
            print(f"🔄 TTSModel初期化中...")
            print(f"   - モデルファイル: {required_files['model']}")
            print(f"   - 設定ファイル: {required_files['config.json']}")
            print(f"   - スタイルベクトル: {required_files['style_vectors.npy']}")
            print(f"   - デバイス: {device}")
            
            # Pathオブジェクトを文字列に変換（Style-Bert-VITS2は文字列パスを要求）
            tts_model = TTSModel(
                model_path=str(required_files['model']),
                config_path=str(required_files['config.json']),
                style_vec_path=str(required_files['style_vectors.npy']),
                device=device
            )
            print("✅ TTSModel作成成功")
        except ImportError as e:
            print(f"❌ インポートエラー: {e}")
            print("💡 style_bert_vits2ライブラリが正しくインストールされているか確認してください")
            return None
        except FileNotFoundError as e:
            print(f"❌ ファイルが見つかりません: {e}")
            print("💡 モデルファイルのパスを確認してください")
            return None
        except RuntimeError as e:
            if "CUDA" in str(e):
                print(f"❌ CUDA関連エラー: {e}")
                print("💡 CPUデバイスで再試行します")
                try:
                    tts_model = TTSModel(
                        model_path=required_files['model'],
                        config_path=required_files['config.json'],
                        style_vec_path=required_files['style_vectors.npy'],
                        device="cpu"
                    )
                    print("✅ CPUでのTTSModel作成に成功")
                except Exception as cpu_error:
                    print(f"❌ CPU再試行も失敗: {cpu_error}")
                    return None
            else:
                print(f"❌ ランタイムエラー: {e}")
                return None
        except Exception as e:
            print(f"❌ TTSModel作成エラー: {e}")
            print(f"❌ エラータイプ: {type(e).__name__}")
            print(f"❌ モデルディレクトリ: {model_dir}")
            print(f"❌ 使用デバイス: {device}")
            import traceback
            print("❌ 詳細なスタックトレース:")
            traceback.print_exc()
            print("\n💡 トラブルシューティング:")
            print("   1. style_bert_vits2が最新版かチェック: pip install --upgrade style-bert-vits2")
            print("   2. モデルファイルが破損していないかチェック")
            print("   3. 十分なメモリがあるかチェック")
            print("   4. Pythonバージョンの互換性をチェック")
            return None
        
        # バックグラウンドTTSサーバークラス（TTSModel直接使用）
        class BackgroundTTSServer:
            def __init__(self, tts_model, model_name):
                self.tts_model = tts_model
                self.model_name = model_name
                self.is_running = True
                
            def synthesize_speech(self, text: str, output_path: str = "output.wav", **kwargs) -> Optional[str]:
                """音声合成を実行（TTSModel直接使用）"""
                try:
                    print(f"🎵 音声合成実行中: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                    
                    # TTSModelのinferメソッドを直接呼び出し（新しいAPI）
                    try:
                        # Style-Bert-VITS2の標準パラメータでinfer実行
                        sr, audio = self.tts_model.infer(
                            text=text,
                            language="JP",  # 日本語
                            speaker_id=kwargs.get('speaker_id', 0),
                            reference_audio_path=kwargs.get('reference_audio_path', None),
                            sdp_ratio=kwargs.get('sdp_ratio', 0.2),
                            noise=kwargs.get('noise', 0.6), 
                            noise_w=kwargs.get('noise_w', 0.8),
                            length=kwargs.get('length', 1.0)
                        )
                        
                        print(f"✅ 音声合成成功 - サンプリングレート: {sr}")
                        
                    except Exception as infer_error:
                        print(f"⚠️ inferメソッドでエラー: {infer_error}")
                        # フォールバック: 他のメソッドを試行
                        available_methods = [method for method in dir(self.tts_model) 
                                           if not method.startswith('_') and callable(getattr(self.tts_model, method))]
                        print(f"🔍 利用可能なメソッド: {available_methods}")
                        raise infer_error
                    
                    # 音声データの保存
                    if audio is not None:
                        from scipy.io import wavfile
                        import numpy as np
                        
                        # numpyの型変換（必要に応じて）
                        if isinstance(audio, np.ndarray):
                            if audio.dtype == np.float32 or audio.dtype == np.float64:
                                # float -> int16 変換
                                audio_int16 = (audio * 32767).astype(np.int16)
                            else:
                                audio_int16 = audio
                        else:
                            audio_int16 = np.array(audio, dtype=np.int16)
                        
                        # WAVファイルとして保存
                        wavfile.write(output_path, sr, audio_int16)
                        print(f"✓ 音声ファイル生成完了: {output_path}")
                        return output_path
                    else:
                        print("⚠️ 音声データがNoneです")
                        return None
                        
                except Exception as e:
                    print(f"⚠️ 音声合成エラー: {e}")
                    print(f"⚠️ エラータイプ: {type(e).__name__}")
                    print(f"⚠️ 入力テキスト: {text}")
                    import traceback
                    print("⚠️ 詳細なエラー情報:")
                    traceback.print_exc()
                    return None
                    
            def stop(self):
                """サーバー停止"""
                self.is_running = False
                print("🛑 TTSサーバーを停止しました")
        
        # サーバーインスタンス作成
        tts_server = BackgroundTTSServer(tts_model, model_name)
        
        print("✓ バックグラウンドTTSサーバーが起動しました")
        return tts_server
        
    except Exception as e:
        print(f"⚠️ バックグラウンドTTSサーバー起動エラー: {e}")
        return None


def initialize_native_tts_system(model_dir: str, model_name: str, device: str) -> Optional[object]:
    """Style-Bert-VITS2のネイティブ機能を使用したTTS初期化（TTSModel直接使用）"""
    try:
        from pathlib import Path
        import torch
        from style_bert_vits2.tts_model import TTSModel
        
        # Colab環境でのデバイス設定（GPU優先）
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                print("✓ GPU(CUDA)を使用します")
            else:
                device = "cpu"
                print("⚠️ GPUが利用できません。CPUを使用します")
        
        print(f"📁 TTSModelを直接初期化中... (パス: {model_dir}/{model_name})")
        
        # BERTモデルの事前初期化
        if not initialize_bert_for_japanese():
            print("⚠️ BERTモデルの初期化に失敗しましたが、TTSModel作成を続行します")
        
        # モデルファイル構造の確認と自動検索
        model_path = Path(model_dir) / model_name
        
        # 基本的な必須ファイル
        required_files = {
            'config.json': model_path / 'config.json',
            'style_vectors.npy': model_path / 'style_vectors.npy'
        }
        
        # モデルファイルの候補を検索（複数形式対応）
        model_file_candidates = [
            model_path / 'model.safetensors',
            model_path / 'model.pth', 
            model_path / 'model.pt',
            model_path / 'model.ckpt',
            *model_path.glob('*.safetensors'),
            *model_path.glob('*.pth'),
            *model_path.glob('*.pt')
        ]
        
        model_file = None
        for candidate in model_file_candidates:
            if candidate.exists() and candidate.is_file():
                model_file = candidate
                print(f"✓ モデルファイル発見: {candidate}")
                break
        
        if model_file is None:
            print(f"❌ モデルファイルが見つかりません:")
            print(f"   検索対象: {[str(c) for c in model_file_candidates[:6]]}")
            print(f"   ディレクトリの内容: {list(model_path.glob('*')) if model_path.exists() else 'ディレクトリが存在しません'}")
            return None
        
        # モデルファイルを確定
        required_files['model'] = model_file
        
        # その他のファイル存在確認
        missing_files = []
        for file_type, file_path in required_files.items():
            if file_type == 'model':
                continue  # 既にチェック済み
            if not file_path.exists():
                missing_files.append(f"{file_type}: {file_path}")
        
        if missing_files:
            print(f"⚠️ 一部のファイルが見つかりません:")
            for missing in missing_files:
                print(f"   - {missing}")
            
            # style_vectors.npyが見つからない場合は作成を試行
            if 'style_vectors.npy' in [m.split(':')[0] for m in missing_files]:
                print(f"💡 style_vectors.npyが見つからないため、デフォルトを使用します")
                # 簡易的な空のstyle vectorsファイルを作成
                import numpy as np
                try:
                    np.save(model_path / 'style_vectors.npy', np.array([]))
                    required_files['style_vectors.npy'] = model_path / 'style_vectors.npy'
                    print(f"✓ デフォルトのstyle_vectors.npyを作成しました")
                except Exception as e:
                    print(f"⚠️ style_vectors.npy作成に失敗: {e}")
                    return None
        
        # TTSModelを直接作成
        try:
            print(f"🔄 TTSModel初期化中...")
            print(f"   - モデルファイル: {required_files['model']}")
            print(f"   - 設定ファイル: {required_files['config.json']}")
            print(f"   - スタイルベクトル: {required_files['style_vectors.npy']}")
            print(f"   - デバイス: {device}")
            
            tts_model = TTSModel(
                model_path=required_files['model'],
                config_path=required_files['config.json'],
                style_vec_path=required_files['style_vectors.npy'],
                device=device
            )
            print(f"✓ TTSModel初期化完了")
        except Exception as e:
            print(f"❌ TTSModel初期化エラー: {e}")
            print(f"❌ エラータイプ: {type(e).__name__}")
            import traceback
            print("❌ 詳細なスタックトレース:")
            traceback.print_exc()
            return None
        
        # シンプルなラッパークラスを作成（TTSModel直接使用）
        class NativeTTSModel:
            def __init__(self, tts_model, model_name):
                self.tts_model = tts_model
                self.model_name = model_name
            
            def inference(self, text: str, output_path: str, **kwargs) -> str:
                """音声合成を実行（TTSModel直接使用）"""
                try:
                    print(f"🎵 音声合成実行中: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                    
                    # TTSModelのinferメソッドを直接呼び出し
                    sr, audio = self.tts_model.infer(
                        text=text,
                        language="JP",
                        speaker_id=kwargs.get('speaker_id', 0),
                        reference_audio_path=kwargs.get('reference_audio_path', None),
                        sdp_ratio=kwargs.get('sdp_ratio', 0.2),
                        noise=kwargs.get('noise', 0.6),
                        noise_w=kwargs.get('noise_w', 0.8),
                        length=kwargs.get('length', 1.0)
                    )
                    
                    print(f"✅ 音声合成成功 - サンプリングレート: {sr}")
                    
                    # 音声データの保存
                    if audio is not None:
                        from scipy.io import wavfile
                        import numpy as np
                        
                        # numpyの型変換
                        if isinstance(audio, np.ndarray):
                            if audio.dtype == np.float32 or audio.dtype == np.float64:
                                audio_int16 = (audio * 32767).astype(np.int16)
                            else:
                                audio_int16 = audio
                        else:
                            audio_int16 = np.array(audio, dtype=np.int16)
                        
                        wavfile.write(output_path, sr, audio_int16)
                        print(f"✓ 音声ファイル生成完了: {output_path}")
                        return output_path
                    else:
                        print("⚠️ 音声データがNoneです")
                        return None
                        
                except Exception as e:
                    print(f"⚠️ 音声合成エラー: {e}")
                    print(f"⚠️ エラータイプ: {type(e).__name__}")
                    print(f"⚠️ 入力テキスト: {text}")
                    import traceback
                    print("⚠️ 詳細なエラー情報:")
                    traceback.print_exc()
                    return None
        
        return NativeTTSModel(tts_model, model_name)
        
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
    """GoogleColab用の簡単チャット関数（音声ファイル生成付き）"""
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
        
        # 音声ファイル生成とダウンロードの提案
        if agent.tts_available:
            print("🎵 この回答の音声ファイルを生成しますか？ (y/n)")
            print("💡 'y' を入力すると音声ファイルがダウンロードされます")
            
            # Google Colab環境での音声ファイル保存
            try:
                import time
                save_filename = f"todo_response_{int(time.time())}.mp3"
                agent.download_voice_file(response, save_filename)
            except Exception as audio_error:
                print(f"⚠️ 音声ファイル生成エラー: {audio_error}")
        
        return response
        
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {e}"
        print(error_msg)
        return error_msg

def colab_setup_style_bert():
    """Google Colab用 Style-Bert-VITS2セットアップ"""
    try:
        print("🔧 Style-Bert-VITS2セットアップを開始します...")
        
        # Google Driveマウント確認
        drive_path = "/content/drive/MyDrive"
        if not os.path.exists(drive_path):
            print("📁 Google Driveをマウントしています...")
            try:
                from google.colab import drive
                drive.mount('/content/drive')
                print("✅ Google Driveマウント完了")
            except ImportError:
                print("❌ Google Colab環境でない、またはマウントに失敗しました")
                return False
        else:
            print("✅ Google Drive既にマウント済み")
        
        # カスタムモデルパス確認
        model_paths = [
            "/content/drive/MyDrive/Style-Bert-VITS2/model_assets/yoshino_test",
            "/content/drive/MyDrive/Style-Bert-VITS2/model_assets/hiroyuki"
        ]
        
        found_models = []
        for path in model_paths:
            if os.path.exists(path):
                files = os.listdir(path)
                has_config = 'config.json' in files
                has_model = any(f.endswith('.safetensors') or f.endswith('.pth') for f in files)
                if has_config and has_model:
                    found_models.append(path)
                    print(f"✅ 有効なモデル発見: {path}")
                else:
                    print(f"⚠️ 不完全なモデル: {path} (config:{has_config}, model:{has_model})")
            else:
                print(f"❌ モデルパス存在しません: {path}")
        
        if found_models:
            print(f"🎉 {len(found_models)} 個のカスタムモデルが利用可能です")
            return True
        else:
            print("❌ 利用可能なカスタムモデルが見つかりません")
            print("💡 Google DriveのStyle-Bert-VITS2フォルダにモデルを配置してください")
            return False
            
    except Exception as e:
        print(f"❌ セットアップエラー: {e}")
        return False

def test_yoshino_model_simple(text: str = "こんにちは、テストです"):
    """Google Colab環境専用：シンプルなyoshino_testテスト"""
    try:
        print("🧪 【Google Colab専用】シンプルなyoshino_testテスト開始...")
        
        # 必要最小限のインポート
        import os
        import tempfile
        
        # Google Colab環境確認
        try:
            import google.colab
            print("✅ Google Colab環境を確認")
        except ImportError:
            print("❌ Google Colab環境ではありません。この関数はGoogle Colab専用です。")
            return False
        
        # model_load.py を直接使用
        print("📦 model_load.py インポート中...")
        from model_load import load_model
        
        # シンプルなパス設定
        model_dir = "/content/drive/MyDrive/Style-Bert-VITS2/model_assets"
        model_name = "yoshino_test"
        
        if not os.path.exists(model_dir):
            print(f"❌ モデルディレクトリが存在しません: {model_dir}")
            print("💡 Google Driveがマウントされ、モデルが配置されているか確認してください")
            return False
        
        print(f"🎯 モデル: {model_name}")
        print(f"📁 パス: {model_dir}")
        print(f"📝 テスト文章: {text}")
        
        # ユーザー指定パターンでモデル読み込み
        print("\n📋 実行コード:")
        print(f"sample_model = load_model('{model_name}', model_dir='{model_dir}', device='cuda')")
        
        sample_model = load_model(model_name, model_dir=model_dir, device="cuda")
        
        print("✅ sample_model 読み込み成功")
        
        # 一回だけテスト実行
        out_path = "/content/yoshino_simple_test.wav"
        print(f"\n🎵 音声生成テスト:")
        print(f"sample_model.inference('{text}', '{out_path}')")
        
        result = sample_model.inference(text, out_path)
        
        print(f"✅ 音声生成完了: {result}")
        if os.path.exists(out_path):
            size = os.path.getsize(out_path)
            print(f"📁 ファイルサイズ: {size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ シンプルテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yoshino_model(text: str = "こんにちは、テストです"):
    """yoshino_testモデルの動作テスト（model_load.py必須使用版）"""
    try:
        print("🧪 yoshino_testモデルのテスト（model_load.py使用）を開始...")
        
        # 依存関係の確認
        print("🔍 model_load.py依存関係チェック...")
        agent = IntegratedLangChainAgent()
        agent._ensure_model_load_dependencies()
        
        # ユーザー指定パターンの実装例表示
        print("\n" + "="*60)
        print("🎯 ユーザー指定パターンの実装例:")
        print("="*60)
        print("from model_load import load_model")
        print("")
        print("# 第1引数にモデル名、model_dirとdeviceはキーワード引数")
        print("sample_model = load_model(\"モデル名\", model_dir=\"/content/model_assets\", device=\"cuda\")")
        print("")
        print("# sample_modelを使い回してinference実行")
        print("sample_model.inference(\"aaa\", \"/content/out.wav\")")
        print("sample_model.inference(\"次の発話\", \"/content/out2.wav\")")
        print("="*60)
        print("")
        
        # model_load.pyを使用してテスト
        from model_load import load_model
        import torch
        import tempfile
        
        model_dir = "/content/drive/MyDrive/Style-Bert-VITS2/model_assets"
        model_name = "yoshino_test"
        
        if not os.path.exists(model_dir):
            print(f"❌ モデルディレクトリが存在しません: {model_dir}")
            return False
        
        print(f"🎯 テスト対象: {model_dir}/{model_name}")
        print(f"📝 テスト文章: {text}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 使用デバイス: {device}")
        
        # ユーザー指定パターンと同じ形式でモデル読み込み
        print("🔧 ユーザー指定パターンでモデル読み込み中...")
        print(f"   実行: sample_model = load_model('{model_name}', model_dir='{model_dir}', device='{device}')")
        
        # ユーザー指定パターンと完全に同じ呼び出し方法
        sample_model = load_model(
            model_name,  # 第1引数として位置引数で指定（ユーザーパターン準拠）
            model_dir=model_dir,  # キーワード引数（ユーザーパターン準拠）
            device=device,  # キーワード引数（ユーザーパターン準拠）
            preload_onnx_bert=False
        )
        
        print("✅ sample_model 初期化成功（ユーザー指定パターン）")
        print(f"  - モデル名: {sample_model.info.model_name}")
        try:
            print(f"  - 話者: {list(sample_model.spk2id.keys())}")
            print(f"  - スタイル: {list(sample_model.style2id.keys())}")
        except:
            print("  - 話者・スタイル情報取得失敗")
        
        # ユーザー指定パターンでの音声生成テスト
        print("\n🎵 ユーザーパターンでの連続音声生成テスト:")
        print("   sample_model.inference(\"aaa\", \"/content/out.wav\")")
        print("   sample_model.inference(\"次の発話\", \"/content/out2.wav\")")
        print("")
        
        # テスト1: "aaa"
        temp_dir = tempfile.gettempdir()
        out1_path = os.path.join(temp_dir, "out.wav")
        print(f"🧪 テスト1実行: sample_model.inference(\"aaa\", \"{out1_path}\")")
        result1 = sample_model.inference("aaa", out1_path)
        print(f"   ✅ 完了: {result1}")
        
        # テスト2: "次の発話"  
        out2_path = os.path.join(temp_dir, "out2.wav")
        print(f"🧪 テスト2実行: sample_model.inference(\"次の発話\", \"{out2_path}\")")
        result2 = sample_model.inference("次の発話", out2_path)
        print(f"   ✅ 完了: {result2}")
        
        # テスト3: ユーザー指定テキスト
        out3_path = os.path.join(temp_dir, "user_test.wav")
        print(f"🧪 テスト3実行: sample_model.inference(\"{text}\", \"{out3_path}\")")
        result3 = sample_model.inference(text, out3_path)
        print(f"   ✅ 完了: {result3}")
        
        # 生成結果サマリー
        print("\n" + "="*60)
        print("📊 sample_model 使い回しテスト結果:")
        print("="*60)
        print(f"✅ テスト1: aaa -> {out1_path}")
        print(f"✅ テスト2: 次の発話 -> {out2_path}")
        print(f"✅ テスト3: {text} -> {out3_path}")
        
        # ファイルサイズ確認
        for i, (path, description) in enumerate([(out1_path, "aaa"), (out2_path, "次の発話"), (out3_path, text)], 1):
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"📁 ファイル{i}: {size} bytes ({description})")
        
        # Google Colab環境の場合、ファイルをダウンロード可能にする
        try:
            from google.colab import files
            import shutil
            import time
            
            print(f"\n🎧 Google Colab環境: 音声ファイルのダウンロード準備中...")
            for i, (src_path, filename) in enumerate([(out1_path, "out.wav"), (out2_path, "out2.wav"), (out3_path, "user_test.wav")], 1):
                if os.path.exists(src_path):
                    colab_path = f"/content/{filename}"
                    shutil.copy(src_path, colab_path)
                    print(f"📁 ファイル{i}保存: {colab_path}")
                    
        except ImportError:
            print(f"📁 ローカル環境: 音声ファイル生成完了")
        
        print("\n✅ ユーザー指定パターン sample_model 使い回しテスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ yoshino_testモデルテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yoshino_model_legacy(text: str = "こんにちは、テストです"):
    """yoshino_testモデルの動作テスト（model_load.py使用版）"""
    try:
        print("🧪 yoshino_testモデルのテスト（model_load.py版）を開始...")
        
        # model_load.pyを使用してテスト
        from model_load import load_model
        import torch
        import tempfile
        
        model_dir = "/content/drive/MyDrive/Style-Bert-VITS2/model_assets"
        model_name = "yoshino_test"
        
        if not os.path.exists(model_dir):
            print(f"❌ モデルディレクトリが存在しません: {model_dir}")
            return False
        
        print(f"🎯 テスト対象: {model_dir}/{model_name}")
        print(f"📝 テスト文章: {text}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 使用デバイス: {device}")
        
        # model_load.pyを使用してモデル読み込み
        loaded_model = load_model(
            model_name=model_name,
            model_dir=model_dir,
            device=device,
            preload_onnx_bert=False
        )
        
        print("✅ yoshino_testモデル初期化成功")
        print(f"  - 話者: {list(loaded_model.spk2id.keys())}")
        print(f"  - スタイル: {list(loaded_model.style2id.keys())}")
        
        # 音声生成テスト
        print("🎵 音声生成テスト中...")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = loaded_model.inference(
                text=text,
                output_path=temp_file.name,
                speaker_id=0,
                language="JP"
            )
            
            print(f"✅ yoshino_test音声生成成功: {output_path}")
            
            # Google Colab環境の場合、ファイルをダウンロード可能にする
            try:
                from google.colab import files
                import shutil
                import time
                
                save_filename = f"yoshino_test_legacy_{int(time.time())}.wav"
                shutil.copy(str(output_path), f"/content/{save_filename}")
                print(f"📁 音声ファイル保存: /content/{save_filename}")
                
                print("🎧 音声ファイルをダウンロードしますか？")
                files.download(f"/content/{save_filename}")
                
            except ImportError:
                print(f"📁 音声ファイル生成: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ yoshino_testモデルテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def force_style_bert_mode():
    """Style-Bert-VITS2のみを使用（gTTSを無効化）"""
    try:
        print("🎯 Style-Bert-VITS2専用モードで初期化...")
        
        # gTTSを無効化したエージェント作成
        agent = IntegratedLangChainAgent()
        
        # gTTSが設定されていたら強制的にStyle-Bert-VITS2に切り替え
        if hasattr(agent, 'tts_model') and isinstance(agent.tts_model, str):
            print("⚠️ gTTSが検出されました。Style-Bert-VITS2に強制切り替えします...")
            agent.tts_available = False
            agent._initialize_style_bert_only()
        
        # sample_model パターンの説明を追加
        if hasattr(agent, 'tts_model') and agent.tts_model is not None:
            print("\n" + "="*60)
            print("🎯 ユーザー指定パターン（sample_model）の使用方法:")
            print("="*60)
            print("from model_load import load_model")
            print("")
            print("# sample_modelとして初期化")
            print("sample_model = load_model(\"yoshino_test\", model_dir=\"/content/model_assets\", device=\"cuda\")")
            print("")
            print("# sample_modelを使い回して音声生成")
            print("sample_model.inference(\"テスト音声\", \"/content/out.wav\")")
            print("sample_model.inference(\"次の音声\", \"/content/out2.wav\")")
            print("="*60)
            print("")
        
        return agent
        
    except Exception as e:
        print(f"❌ Style-Bert-VITS2専用モード失敗: {e}")
        return None

def colab_voice_chat(question: str = "今日のタスクは？") -> str:
    """Google Colab専用：音声ファイル自動生成チャット"""
    try:
        print("🎵 音声付きチャット開始...")
        
        # エージェント初期化
        agent = IntegratedLangChainAgent()
        
        if not agent.llm_available:
            return "❌ LLMが利用できません。APIキーを確認してください。"
        
        print(f"💬 質問: {question}")
        response = agent.process_query(question)
        print(f"\n🤖 **回答**:\n{response}\n")
        
        # 自動音声ファイル生成
        if agent.tts_available:
            print("🎵 音声ファイルを自動生成中...")
            try:
                import time
                filename = f"hiroyuki_voice_auto_{int(time.time())}.mp3"
                agent.download_voice_file(response, filename)
            except Exception as e:
                print(f"⚠️ 音声生成エラー: {e}")
        
        return response
        
    except Exception as e:
        error_msg = f"❌ エラー: {e}"
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
# 通常チャット（音声オプション）
colab_quick_chat("今日のタスクを確認して")
colab_quick_chat("明日までにレポートを書くタスクを追加") 

# 音声自動生成チャット（Google Colab専用）
colab_voice_chat("ひろゆき風でタスク状況を教えて")
colab_voice_chat("タスク管理についてアドバイスして")

# カスタムモデルセットアップ（初回実行推奨）
colab_setup_style_bert()  # Google Driveマウント & モデル確認

# 🎯 1. シンプルテスト（推奨 - エラーが少ない）
test_yoshino_model_simple("こんにちは、テストです")

# 🎯 2. TODOアプリでの統合テスト（修正版）
agent = IntegratedLangChainAgent()
agent.test_voice_synthesis("こんにちは、TODOアプリの音声合成です")

# 🎯 3. 詳細テスト（詳しい情報が必要な場合）
test_yoshino_model("こんにちは、yoshino音声テストです")

# 診断機能（トラブルシューティング）
agent = IntegratedLangChainAgent()
agent.diagnose_tts_system()  # 詳細診断

# 🎯 ユーザー指定パターン（sample_model）
from model_load import load_model

# sample_modelとして初期化（ユーザー指定形式）
sample_model = load_model("モデル名", model_dir="/content/model_assets", device="cuda")

# sample_modelを使い回して複数音声生成
sample_model.inference("aaa", "/content/out.wav")
sample_model.inference("次の発話", "/content/out2.wav")

# 実際の例（yoshino_testモデル）
sample_model = load_model("yoshino_test", model_dir="/content/drive/MyDrive/Style-Bert-VITS2/model_assets", device="cuda")
sample_model.inference("こんにちは、テストです", "/content/yoshino_test1.wav")
sample_model.inference("さらに次のテスト", "/content/yoshino_test2.wav")

# 🎯 4. アプリ統合使用（model_load.py + yoshino_testモデル自動使用）
agent = IntegratedLangChainAgent()  # Google Colab環境では自動的にシンプルモード
response = agent.process_query("今日のタスクを教えて")  # yoshino_testモデルで音声生成

# 🎯 5. 実際のTODOアプリ機能テスト
agent = IntegratedLangChainAgent()
agent.process_query("明日までにレポートを書くタスクを追加")  # タスク追加 + 音声応答
agent.process_query("今日のタスクを確認")  # タスク確認 + 音声応答
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
        print("🚀 統合TODOアプリを起動中...")
        
        # アプリケーション初期化
        agent = IntegratedLangChainAgent()
        
        # システム情報とテスト実行
        agent.get_system_info()
        
        # 音声テスト（利用可能な場合）
        if agent.tts_available:
            print("\n🎵 音声合成テストを実行しますか？ (y/n):")
            if input().lower().startswith('y'):
                agent.test_tts_system()
        
        print("\n✅ 初期化完了！通常モードで起動します。")
        integrated_langchain_mode()