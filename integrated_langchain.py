#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import csv
import datetime
import json
import pickle
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
        
        # タスク名をクリーンに
        task_name = task_description
        # 時期表現を除去
        time_expressions = ["明日までに", "今日", "来週", "再来週", "2週間後", "来月"]
        for expr in time_expressions:
            task_name = task_name.replace(expr, "")
        
        # 日付表現を除去
        import re
        task_name = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日に?', '', task_name)
        task_name = re.sub(r'\d{4}-\d{2}-\d{2}に?', '', task_name) 
        task_name = re.sub(r'\d{1,2}/\d{1,2}に?', '', task_name)
        
        # 動作表現を除去
        action_expressions = ["する", "やる", "を行う", "を実行"]
        for expr in action_expressions:
            if task_name.endswith(expr):
                task_name = task_name[:-len(expr)]
        
        # カレンダー関連表現をクリーンに
        calendar_expressions = [
            "をカレンダーに追加", "をスケジュールに入れる", "を予定に入れる",
            "カレンダーに", "スケジュールに", "予定に", "を入れておいて", "と入れておいて",
            "googleカレンダーに", "Googleカレンダーに"
        ]
        for expr in calendar_expressions:
            task_name = task_name.replace(expr, "")
        
        task_name = task_name.strip()
        if not task_name:
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
        self.tools = [search_calendar_events, list_csv_tasks, add_task_naturally, complete_task_naturally]
        
        # 対話履歴記録（統合）
        self.conversations_file = "ai_conversations.csv"
        
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

ユーザーの質問を分析して、必要なツールを実行し、結果を統合してわかりやすく回答してください。
- タスクを追加したい場合：add_task_naturallyを使用
- タスクを完了したい場合：complete_task_naturallyを使用
- タスク一覧を見たい場合：list_csv_tasksを使用
- 予定を確認したい場合：search_calendar_eventsを使用

日本語で親しみやすい口調で回答してください。"""
    
    def process_query(self, user_input: str) -> str:
        """ユーザーの質問を処理"""
        start_time = time.time()
        
        try:
            # 怒るべきかどうかをキーワード検索でチェック
            if self._should_get_angry(user_input):
                # 怒りモードを発動
                # ユーザーインプットに対してメッセージとパターンをリターンで取得
                anger_message, anger_pattern = self._get_anger_message(user_input)
                
                print("\n" + "="*60)
                print("🤖💢 AI怒りモード発動！")
                print("="*60)
                #　実際にリターンで返されたメッセージをprint
                print(anger_message)
                print("="*60)
                
                # モチベーション効果のアンケート
                print("\n📊 怒りモード効果アンケート")
                print("今の怒り方はモチベーションアップにつながりましたか？")
                
                try:
                    while True:
                        motivation_feedback = input("a（良い） / b（悪い）: ").strip().lower()
                        if motivation_feedback in ['a', 'b']:
                            break
                        print("aかbで答えてください。")
                except EOFError:
                    # 入力が終了した場合はデフォルトで'a'とする
                    motivation_feedback = 'a'
                    print("\n入力が終了したため、デフォルトで「a（良い）」として記録します。")
                
                # アンケート結果を記録
                is_effective = (motivation_feedback == 'a')
                self._record_anger_result(anger_pattern, is_effective)
                
                if is_effective:
                    final_response = "ありがとうございます！この怒り方が効果的だったようですね。😊\n次回もこの調子で応援します！\n\n元の質問にお答えします：\n\n"
                else:
                    final_response = "そうでしたか...今度はもう少し優しく（または厳しく）アプローチしてみますね。😅\n\n元の質問にお答えします：\n\n"
                
                # 元の質問を処理
                original_response = self._process_original_query(user_input)
                final_response += original_response
                
                # 怒り込みでの対話記録
                response_time = time.time() - start_time
                self._log_conversation(
                    user_input=user_input,
                    ai_response=f"[怒りモード:{anger_pattern}] {anger_message} | [アンケート] {motivation_feedback} | [結果] {final_response}",
                    tools_used=["anger_with_survey"],
                    response_time=response_time
                )
                
                return final_response
            
            else:
                # 🔥 STEP 2: 通常モード
                # 通常のAI処理
                return self._process_original_query(user_input, start_time)
            
        except Exception as e:
            error_response = f"エラーが発生しました: {str(e)}"
            
            # エラーも履歴に記録
            response_time = time.time() - start_time
            self._log_conversation(
                user_input=user_input,
                ai_response=error_response,
                tools_used=[],
                response_time=response_time
            )
            
            return error_response
    
    def _process_original_query(self, user_input: str, start_time: Optional[float] = None) -> str:
        """元の質問処理（怒りモード分離後）"""
        if start_time is None:
            start_time = time.time()
        
        # 1. 質問を分析してツールを選択
        tools_to_use = self._analyze_query(user_input)
        
        # 2. ツールを実行して結果を取得
        tool_results = self._execute_tools(tools_to_use)
        
        # 3. LLMで結果を統合・回答生成
        response = self._generate_response(user_input, tool_results)
        
        # 4. 対話履歴を記録
        response_time = time.time() - start_time
        tools_used = list(tool_results.keys()) if tool_results else []
        self._log_conversation(
            user_input=user_input,
            ai_response=response,
            tools_used=tools_used,
            response_time=response_time
        )
        
        return response
    
    def _analyze_query(self, query: str) -> Dict[str, bool]:
        """クエリを分析して必要なツールを特定"""
        query_lower = query.lower()
        
        # キーワードベースで判定
        needs_calendar = any(kw in query_lower for kw in ['予定', 'スケジュール', 'カレンダー', '会議'])
        needs_tasks = any(kw in query_lower for kw in ['タスク', 'やること', 'todo', '未完了', '状況', '一覧'])
        needs_add = any(kw in query_lower for kw in ['追加', '作る', 'する', 'やる', '登録', 'までに', '入れる', '入れて', 'いれて', 'セットして', 'set'])
        needs_complete = any(kw in query_lower for kw in ['完了', '終わった', 'やった', 'できた', '済んだ'])
        
        # カレンダー＋追加の組み合わせは明確にタスク追加
        if needs_calendar and needs_add:
            return {
                'calendar': False,
                'tasks': False,
                'add_task': True,
                'complete_task': False
            }
        
        # どちらも明確でない場合は両方
        if not any([needs_calendar, needs_tasks, needs_add, needs_complete]):
            needs_calendar = needs_tasks = True
        
        return {
            'calendar': needs_calendar,
            'tasks': needs_tasks,
            'add_task': needs_add,
            'complete_task': needs_complete
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
                
        except Exception as e:
            results['error'] = f"ツール実行エラー: {str(e)}"
        
        return results
    
    def _generate_response(self, user_input: str, tool_results: Dict[str, str]) -> str:
        """LLMで結果を統合して回答生成"""
        # 自然言語タスク操作が必要な場合は直接実行
        if tool_results.get('add_task') == "PENDING":
            try:
                return add_task_naturally.func(user_input)
            except Exception as e:
                return f"タスク追加エラー: {str(e)}"
        
        if tool_results.get('complete_task') == "PENDING":
            try:
                return complete_task_naturally.func(user_input)
            except Exception as e:
                return f"タスク完了エラー: {str(e)}"
        
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
                return response.content
            except Exception as e:
                # フォールバック
                if context:
                    return f"以下の情報が取得できました：\n\n{context}"
                else:
                    return "申し訳ございませんが、情報を取得できませんでした。"
        else:
            # LLMなしの場合はシンプルに情報を返す
            if context:
                return f"📋 取得した情報:\n\n{context}"
            else:
                return "LLMが利用できないため、シンプルな応答モードです。タスク操作は引き続き利用できます。"
    
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
    
    def _log_conversation(self, user_input: str, ai_response: str, tools_used: List[str], response_time: float) -> None:
        """対話履歴記録"""
        try:
            session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # CSVヘッダーチェック・作成
            file_exists = os.path.exists(self.conversations_file)
            
            with open(self.conversations_file, 'a', newline='', encoding='utf-8') as file:
                fieldnames = ['session_id', 'timestamp', 'user_input', 'ai_response', 'conversation_type', 'tools_used', 'response_time']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'session_id': session_id,
                    'timestamp': timestamp,
                    'user_input': user_input,
                    'ai_response': ai_response,
                    'conversation_type': 'general_query',
                    'tools_used': ','.join(tools_used) if tools_used else '',
                    'response_time': f'{response_time:.2f}s'
                })
        except Exception as e:
            print(f"対話履歴記録エラー: {e}")
    
    def get_simple_anger_report(self) -> str:
        """AIモチベーション効果レポート"""
        gentle_rate = self._get_success_rate("gentle")
        direct_rate = self._get_success_rate("direct")
        
        gentle_total = self.anger_stats["gentle"]["total"]
        direct_total = self.anger_stats["direct"]["total"]
        
        report = "📊 AIモチベーション効果分析レポート\n"
        report += "="*40 + "\n"
        report += f"😊 優しい怒り: モチベーション効果{gentle_rate:.1%} ({gentle_total}回実施)\n"
        report += f"😤 直接的怒り: モチベーション効果{direct_rate:.1%} ({direct_total}回実施)\n"
        
        if gentle_total > 0 and direct_total > 0:
            if gentle_rate > direct_rate:
                report += "\n💡 優しい怒り方の方がモチベーションアップ効果が高いです！"
                report += "\n🎯 次回は優しいアプローチを採用します。"
            elif direct_rate > gentle_rate:
                report += "\n💡 直接的な怒り方の方がモチベーションアップ効果が高いです！"
                report += "\n🎯 次回は直接的アプローチを採用します。"
            else:
                report += "\n💡 どちらも同程度のモチベーション効果です。"
                report += "\n🎯 引き続きバランス良く使い分けます。"
        else:
            report += "\n💡 データ蓄積中... より多くのフィードバックをお待ちしています！"
        
        return report


def integrated_langchain_mode() -> None:
    """統合LangChainモードのメイン処理"""
    print("\n=== 統合LangChain高機能自然言語モード ===")
    print("LangChainを使ってカレンダーとタスクの情報を検索してお答えします。")
    print("📋 未完了タスクが5個以上だとAIが怒ることがあります...")
    print("")
    print("💡 新機能:")
    print("  • 「明日までにレポート書く」→ タスク追加")
    print("  • 「サッカーやった」→ タスク完了")
    print("  • 「タスク状況教えて」→ 一覧表示")
    print("")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
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
    
    # 対話ループ
    # 何がTrueの間？
    while True:
        user_input = input("💬 質問を入力してください: ").strip()
        
        # 終了条件
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit']:
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
        print("-" * 60)


if __name__ == "__main__":
    integrated_langchain_mode()