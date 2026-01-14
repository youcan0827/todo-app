#!/usr/bin/env python3
import os
import sys

# pyopenjtalk を直接使用（ワーカーモード無効）
_style_bert_root = '/content/drive/MyDrive/todo-app/Style-Bert-VITS2'
_tts_initialized = False

os.environ["PYOPENJTALK_G2P_WORKER"] = "0"

if os.path.exists(_style_bert_root):
    sys.path.insert(0, _style_bert_root)
    _orig = os.getcwd()
    os.chdir(_style_bert_root)
    print("[TTS] 初期化開始...")
    try:
        import pyopenjtalk
        from style_bert_vits2.nlp.japanese.user_dict import update_dict
        update_dict()
        _tts_initialized = True
        print("[TTS] 初期化完了")
    except Exception as e:
        print(f"[TTS] 初期化失敗: {type(e).__name__}: {e}")
    finally:
        os.chdir(_orig)

import csv
import datetime
import json
import pickle
import traceback
from typing import Dict, List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

_tts_available = False
_tts_model = None
_audio_counter = 0

try:
    from model_load import load_model
    from IPython.display import Audio, display
    _tts_available = True
    print("[TTS] モジュールインポート成功")
except ImportError as e:
    print(f"[TTS] インポート失敗: {e}")
    pass

def _init_tts():
    global _tts_initialized
    if _tts_initialized or not _tts_available:
        return
    if not os.path.exists(_style_bert_root):
        print(f"[TTS] Style-Bert-VITS2ディレクトリが見つかりません: {_style_bert_root}")
        return
    if sys.path[0] != _style_bert_root:
        if _style_bert_root in sys.path:
            sys.path.remove(_style_bert_root)
        sys.path.insert(0, _style_bert_root)
    original_cwd = os.getcwd()
    try:
        os.chdir(_style_bert_root)
        import pyopenjtalk
        from style_bert_vits2.nlp.japanese.user_dict import update_dict
        update_dict()
        _tts_initialized = True
        print("[TTS] pyopenjtalk初期化完了")
    except Exception as e:
        print(f"[TTS] 初期化エラー: {type(e).__name__}: {e}")
    finally:
        os.chdir(original_cwd)

def _get_tts_model():
    global _tts_model
    print(f"[TTS DEBUG] _get_tts_model開始: _tts_model={_tts_model}, _tts_available={_tts_available}")
    if _tts_model is None and _tts_available:
        print("[TTS DEBUG] _init_tts呼び出し")
        _init_tts()
        print(f"[TTS DEBUG] _init_tts完了: _tts_initialized={_tts_initialized}")
        if not _tts_initialized:
            print("[TTS DEBUG] 初期化失敗のためNone返却")
            return None
        original_cwd = os.getcwd()
        try:
            os.chdir(_style_bert_root)
            print(f"[TTS DEBUG] load_model呼び出し: dir={_style_bert_root}", flush=True)
            _tts_model = load_model("yoshino_test", model_dir="/content/drive/MyDrive/Style-Bert-VITS2/model_assets", device="cuda")
            print(f"[TTS DEBUG] load_model完了: model={type(_tts_model)}", flush=True)
        except Exception as e:
            print(f"[TTS DEBUG] load_modelエラー: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            os.chdir(original_cwd)
    return _tts_model

def speak_hiroyuki(text: str) -> str:
    print(f"[TTS DEBUG] speak_hiroyuki開始: text長={len(text)}")
    if not _tts_available:
        print("[TTS] model_load未インポート")
        return ""
    try:
        global _audio_counter
        _audio_counter += 1
        out_path = f"/content/hiroyuki_{_audio_counter}.wav"
        print(f"[TTS DEBUG] 出力パス: {out_path}")
        print(f"[TTS DEBUG] モデル取得中...", flush=True)
        model = _get_tts_model()
        print(f"[TTS DEBUG] モデル取得結果: {type(model)}", flush=True)
        if model is None:
            print("[TTS DEBUG] モデルがNoneのため終了", flush=True)
            return ""
        print(f"[TTS DEBUG] inference呼び出し: text={text[:50]}...", flush=True)
        original_cwd = os.getcwd()
        os.chdir(_style_bert_root)
        try:
            model.inference(text, out_path)
        finally:
            os.chdir(original_cwd)
        print(f"[TTS DEBUG] inference完了: {out_path}", flush=True)
        display(Audio(out_path, autoplay=True))
        return out_path
    except Exception as e:
        print(f"[TTS DEBUG] エラー発生箇所のスタックトレース:")
        traceback.print_exc()
        print(f"[TTS] エラー: {type(e).__name__}: {e}")
        return ""

def _ensure_hiroyuki_csv_exists():
    conversation_log = "csv/simple_conversations.csv"
    os.makedirs("csv", exist_ok=True)
    if not os.path.exists(conversation_log):
        with open(conversation_log, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['datetime', 'user_input', 'ai_response', 'response_length'])

def _log_hiroyuki_conversation(user_input: str, ai_response: str):
    conversation_log = "csv/simple_conversations.csv"
    with open(conversation_log, 'a', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_input, ai_response, len(ai_response)])

def get_hiroyuki_response(user_input: str) -> str:
    _ensure_hiroyuki_csv_exists()
    llm = ChatOpenAI(temperature=0.7, model="openai/gpt-3.5-turbo", openai_api_base="https://openrouter.ai/api/v1", openai_api_key=os.getenv("OPENROUTER_API_KEY"))
    system_prompt = """あなたはひろゆき（西村博之）として回答してください。
以下のルールを厳守してください：
1. 主語は「おいら」を使用
2. 敬語を使いながら論破口調で話す
3. 「〜って〜なんですよね、はい。」のような口調を使う
4. 科学的根拠や論理的な説明を含める
5. 辻褄が合う、説得力のある回答をする
6. 最後に「まぁ、頑張ってください。」や類似の締めの言葉を使う

例：「タスクを確認してきました。〜タスク〜やるべきことは多いですが、一つ一つ集中的に行うことが生産性を上げるって科学的に証明されてるんですよね、はい。まぁ、頑張ってください。」"""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
    response = llm.invoke(messages)
    ai_response = response.content
    _log_hiroyuki_conversation(user_input, ai_response)
    return ai_response

SCOPES = ['https://www.googleapis.com/auth/calendar']

@tool("search_calendar_events")
def search_calendar_events(query: str = "") -> str:
    """
    Googleカレンダーから今日から7日間の予定を検索する

    Args:
        query: 検索クエリ（省略可）。特定のキーワードでフィルタリングする場合に使用

    Returns:
        予定のリスト（最大10件）。日時とタイトルを含む文字列を返す
    """
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
                return "認証ファイルなし"
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.now()
    time_min = now.isoformat() + '+09:00'
    week_later = now + datetime.timedelta(days=7)
    time_max = week_later.isoformat() + '+09:00'
    events_result = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max, maxResults=10, singleEvents=True, orderBy='startTime', q=query).execute()
    events = events_result.get('items', [])
    if not events:
        return "予定なし"
    result = f"予定({len(events)}件):\n"
    for i, event in enumerate(events, 1):
        start_time = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start_time:
            dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            start_time = dt.strftime('%m/%d %H:%M')
        result += f"{i}. {event.get('summary', 'タイトルなし')} ({start_time})\n"
    return result

@tool("list_csv_tasks")
def list_csv_tasks(status_filter: str = None) -> str:
    """
    CSVファイルからタスク一覧を取得する

    Args:
        status_filter: ステータスフィルタ（省略可）。'todo'または'done'を指定可能

    Returns:
        タスク一覧。タスク名、期日、完了状態を含む文字列を返す
    """
    csv_file = "csv/tasks.csv"
    os.makedirs("csv", exist_ok=True)
    if not os.path.exists(csv_file):
        return "タスクファイルなし"
    tasks = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if status_filter and row.get('status', '') != status_filter:
                continue
            tasks.append(row)
    if not tasks:
        return "タスクなし"
    result = f"タスク({len(tasks)}件):\n"
    for i, task in enumerate(tasks, 1):
        task_name = task.get('task_name', 'なし')
        due_date = task.get('due_date', '')
        status = task.get('status', 'unknown')
        due_info = f" ({due_date})" if due_date else ""
        status_jp = "完了" if status == "done" else "未完了"
        result += f"{i}. {task_name}{due_info} - {status_jp}\n"
    return result

@tool("add_task_naturally")
def add_task_naturally(task_description: str) -> str:
    """
    自然言語でタスクを追加する

    Args:
        task_description: タスクの説明。「明日」「今日」などの日付表現を自動認識

    Returns:
        タスク追加の確認メッセージ
    """
    due_date = ""
    if "明日" in task_description:
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        due_date = tomorrow.strftime("%Y-%m-%d")
    elif "今日" in task_description:
        due_date = datetime.datetime.now().strftime("%Y-%m-%d")
    csv_file = "csv/tasks.csv"
    os.makedirs("csv", exist_ok=True)
    csv_headers = ["task_name", "due_date", "status", "created_at", "calendar_event_id"]
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(csv_headers)
    tasks = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        tasks = list(reader)
    new_task = {"task_name": task_description, "due_date": due_date, "status": "todo", "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "calendar_event_id": ""}
    tasks.append(new_task)
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(tasks)
    return f"タスク「{task_description}」を追加"

@tool("complete_task_naturally")
def complete_task_naturally(task_hint: str) -> str:
    """
    自然言語でタスクを完了状態にする

    Args:
        task_hint: 完了させたいタスクのヒント（部分一致で検索）

    Returns:
        タスク完了の確認メッセージ、または該当タスクが見つからない場合のエラーメッセージ
    """
    csv_file = "csv/tasks.csv"
    os.makedirs("csv", exist_ok=True)
    if not os.path.exists(csv_file):
        return "タスクファイルなし"
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        tasks = list(reader)
    incomplete_tasks = [(i, task) for i, task in enumerate(tasks) if task["status"] == "todo"]
    if not incomplete_tasks:
        return "完了可能なタスクなし"
    task_hint_clean = task_hint.lower().replace("完了", "").replace("やった", "").replace("できた", "").strip()
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
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["task_name", "due_date", "status", "created_at", "calendar_event_id"])
            writer.writeheader()
            writer.writerows(tasks)
        return f"タスク「{completed_task_name}」を完了"
    else:
        return "完了するタスクが特定できませんでした"

class IntegratedLangChainAgent:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, openai_api_base="https://openrouter.ai/api/v1", temperature=0.1)
            self.llm_available = True
        else:
            self.llm = None
            self.llm_available = False
        self.tools = [search_calendar_events, list_csv_tasks, add_task_naturally, complete_task_naturally]
        self.anger_stats_file = "csv/anger_stats.json"
        os.makedirs("csv", exist_ok=True)
        self.anger_patterns = {"gentle": "{count}個のタスクが残ってるね", "direct": "{count}個もタスク残ってる！"}
        self.anger_stats = {"gentle": {"success": 0, "total": 0}, "direct": {"success": 0, "total": 0}}
        self._load_anger_stats()
    
    def process_query(self, user_input: str) -> str:
        if self._should_get_angry(user_input):
            incomplete_count = self._get_incomplete_task_count()
            hiroyuki_input = f"ユーザーが{incomplete_count}個ものタスクを溜め込んでいます。{user_input}"
            hiroyuki_response = get_hiroyuki_response(hiroyuki_input)
            original_response = self._process_original_query(user_input)
            speak_hiroyuki(hiroyuki_response)
            return f"ひろゆき風: {hiroyuki_response}\n\n元の回答:\n{original_response}"
        else:
            response = self._process_original_query(user_input)
            speak_hiroyuki(response)
            return response
    
    def _process_original_query(self, user_input: str) -> str:
        tools_to_use = self._analyze_query(user_input)
        tool_results = self._execute_tools(tools_to_use)
        return self._generate_response(user_input, tool_results)
    
    def _analyze_query(self, query: str) -> Dict[str, bool]:
        query_lower = query.lower()
        needs_calendar = any(kw in query_lower for kw in ['予定', 'スケジュール', 'カレンダー'])
        needs_tasks = any(kw in query_lower for kw in ['タスク', 'やること', 'todo'])
        needs_add = any(kw in query_lower for kw in ['追加', '作る', 'する', 'やる'])
        needs_complete = any(kw in query_lower for kw in ['完了', '終わった', 'やった', 'できた'])
        return {'calendar': needs_calendar, 'tasks': needs_tasks, 'add_task': needs_add, 'complete_task': needs_complete}
    
    def _execute_tools(self, tools_to_use: Dict[str, bool]) -> Dict[str, str]:
        results = {}
        if tools_to_use['calendar']:
            results['calendar'] = search_calendar_events.func("")
        if tools_to_use['tasks']:
            results['tasks'] = list_csv_tasks.func("todo")
        if tools_to_use['add_task']:
            results['add_task'] = "PENDING"
        if tools_to_use['complete_task']:
            results['complete_task'] = "PENDING"
        return results
    
    def _generate_response(self, user_input: str, tool_results: Dict[str, str]) -> str:
        if tool_results.get('add_task') == "PENDING":
            return self._simple_hiroyuki_convert(add_task_naturally.func(user_input))
        if tool_results.get('complete_task') == "PENDING":
            return self._simple_hiroyuki_convert(complete_task_naturally.func(user_input))
        context = ""
        if 'calendar' in tool_results:
            context += f"📅 {tool_results['calendar']}\n\n"
        if 'tasks' in tool_results:
            context += f"📋 {tool_results['tasks']}\n\n"
        if self.llm_available:
            messages = [SystemMessage(content="タスク管理アシスタント"), HumanMessage(content=f"質問: {user_input}\n情報:\n{context}")]
            response = self.llm.invoke(messages)
            return self._simple_hiroyuki_convert(response.content)
        else:
            return self._simple_hiroyuki_convert(context if context else "情報取得できませんでした")
    
    def _simple_hiroyuki_convert(self, original_response: str) -> str:
        llm = ChatOpenAI(temperature=0.7, model="openai/gpt-3.5-turbo", openai_api_base="https://openrouter.ai/api/v1", openai_api_key=os.getenv("OPENROUTER_API_KEY"))
        system_prompt = """あなたはひろゆき（西村博之）として、与えられた情報を元に回答してください。
以下のルールを厳守してください：
1. 主語は「おいら」を使用
2. 敬語を使いながら論破口調で話す
3. 「〜って〜なんですよね。」のような口調を使う
4. 科学的根拠や論理的な説明を含める
5. 辻褄が合う、説得力のある回答をする
6. 最後に「まぁ、頑張ってください。」や類似の締めの言葉を使う"""
        conversion_input = f"以下の情報をひろゆき風に変換して回答してください：\n{original_response}"
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=conversion_input)]
        response = llm.invoke(messages)
        return response.content
    
    def _should_get_angry(self, user_input: str) -> bool:
        task_check_keywords = ["タスク確認", "タスク状況", "未完了", "残り", "進捗", "タスク一覧", "やること確認"]
        is_task_check = any(keyword in user_input for keyword in task_check_keywords)
        if not is_task_check:
            return False
        incomplete_count = self._get_incomplete_task_count()
        return incomplete_count >= 5
    
    def _get_incomplete_task_count(self) -> int:
        csv_file = "csv/tasks.csv"
        if not os.path.exists(csv_file):
            return 0
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = sum(1 for row in reader if row.get('status') == 'todo')
            return count
    
    def _load_anger_stats(self) -> None:
        if os.path.exists(self.anger_stats_file):
            with open(self.anger_stats_file, 'r', encoding='utf-8') as f:
                self.anger_stats = json.load(f)
    
    def get_simple_anger_report(self) -> str:
        return "効果レポート"

def integrated_langchain_mode() -> None:
    agent = IntegratedLangChainAgent()
    while True:
        user_input = input("質問: ").strip()
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit']:
            break
        if not user_input:
            continue
        if user_input.lower() in ['怒り分析', '効果レポート']:
            print(f"\n{agent.get_simple_anger_report()}\n")
            continue
        response = agent.process_query(user_input)
        print(f"\n{response}\n")