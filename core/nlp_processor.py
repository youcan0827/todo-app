#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import datetime
import requests
import json
from typing import Dict, Optional, List, Tuple
from dotenv import load_dotenv
from google_calendar.calendar_client import CalendarClient
from pydantic import BaseModel, Field

load_dotenv()


# Structured Output用のPydanticモデル
class TaskInfo(BaseModel):
    """タスク情報の抽出スキーマ"""
    summary: str = Field(description="タスク名/イベント名")
    start_datetime: Optional[str] = Field(None, description="開始日時（ISO形式）")
    duration_minutes: Optional[int] = Field(None, description="所要時間（分）")
    has_datetime: bool = Field(description="日時情報が含まれているかどうか")
    confidence: float = Field(description="抽出の信頼度（0.0-1.0）")


# NLPProcessorでAPI確認と使用するモデル、プロンプト定義を行う
class NLPProcessor:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY環境変数が設定されていません")
        
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "openai/gpt-3.5-turbo"
        
        # Googleカレンダークライアントの初期化（オプション）
        try:
            self.calendar_client = CalendarClient()
            self.calendar_enabled = True
            print("✓ Googleカレンダー連携が有効になりました")
        except Exception as e:
            print(f"ℹ️  Googleカレンダー連携は無効です（{e}）")
            print("   タスク管理機能は通常通り使用できます")
            self.calendar_client = None
            self.calendar_enabled = False
        
        self.system_prompt = """あなたはタスク管理アプリの自然言語処理エンジンです。
ユーザーの入力を分析して、以下の操作のいずれかを特定してください：

1. ADD - タスクの追加
2. EDIT - タスクの編集
3. DELETE - タスクの削除
4. SHOW - タスクの表示
5. COMPLETE - タスクの完了
6. UNKNOWN - 不明な操作

また、タスク名や期限などの情報も抽出してください。

回答は以下のJSON形式で返してください：
{
    "action": "ADD|EDIT|DELETE|SHOW|COMPLETE|UNKNOWN",
    "task_name": "抽出されたタスク名",
    "due_date": "YYYY-MM-DD形式の期限（あれば）",
    "task_index": "編集・削除対象のタスク番号（あれば）",
    "confidence": 0.0-1.0の確信度
}"""

# main.pyで自然言語処理を行うときに呼び出す関数「
    def parse_natural_language(self, user_input: str) -> Dict[str, any]:
        try:
            # HTTPヘッダーを準備
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"ユーザー入力: {user_input}"}
                ],
                "temperature": 0.1
            }
            
            # APIにリクエスト送信する
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            # 結果がJSON形式で返ってくる
            response_data = response.json()
            ai_response = response_data["choices"][0]["message"]["content"]
            
            # AIの回答テキストをJSON形式のみを抽出する
            result = self._extract_json_from_response(ai_response)            
           
            if not result:
                return self._fallback_parse(user_input)
            
            return result
            
        except Exception as e:
            print(f"LLM処理エラー: {e}")
            return self._fallback_parse(user_input)
# AIの回答テキストからJSON部分のみを抽出
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        import json
        
        # jsonパターンを定義
        json_pattern = r'\{.*?\}'
        # reのモジュールにおけるfindallメソッドを用いてjsonパターンに一致する部分を抽出
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        for match in matches:
             # json.loadsメソッドを用いてjson形式に変換する
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    # LLM処理失敗時はキーワードで出力内容を決定する
    def _fallback_parse(self, user_input: str) -> Dict[str, any]:
        user_input = user_input.lower()
        
        # それぞれの機能で想定されるキーワードを設定し、変数に格納
        add_keywords = ["追加", "作成", "新規", "登録", "add", "create", "new"]
        edit_keywords = ["編集", "修正", "変更", "更新", "edit", "modify", "update"]
        delete_keywords = ["削除", "消去", "remove", "delete"]
        show_keywords = ["表示", "確認", "一覧", "show", "list", "view"]
        complete_keywords = ["完了", "終了", "done", "complete", "finish"]
        
        # add_keywordsの要素からキーワードを見つけたらactionをADDに設定する
        action = "UNKNOWN"
        if any(keyword in user_input for keyword in add_keywords):
            action = "ADD"
        elif any(keyword in user_input for keyword in edit_keywords):
            action = "EDIT"
        elif any(keyword in user_input for keyword in delete_keywords):
            action = "DELETE"
        elif any(keyword in user_input for keyword in show_keywords):
            action = "SHOW"
        elif any(keyword in user_input for keyword in complete_keywords):
            action = "COMPLETE"
        
        # task_name,due_date,task_indexごとに適した関数を呼び出し
        task_name = self._extract_task_name(user_input)
        due_date = self._extract_due_date(user_input)
        task_index = self._extract_task_index(user_input)
        
        return {
            "action": action,
            "task_name": task_name,
            "due_date": due_date,
            "task_index": task_index,
            "confidence": 0.7
        }

# task_name = self._extract_task_name(user_input)におけるuser_inputに当たるタスク名を抽出する
    def _extract_task_name(self, text: str) -> str:
        quote_patterns = [r'"([^"]+)"', r"'([^']+)'", r"「([^」]+)」"]
        
        # 符号が含まれていたら、その部分を抽出する
        for pattern in quote_patterns:
            # reのモジュールにおけるfindballメソッドを用いて、パターンに一致する部分を抽出する
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        # スプリットメソッドを用いて、文字列を区切る
        words = text.split()
        task_words = []
        skip_words = {"を", "の", "に", "で", "は", "が", "と", "から", "まで", "する", "した", "です", "ます"}
        
        # スキップワードがないのであれば、タスク名を抽出する
        for word in words:
            if word not in skip_words and len(word) > 1:
                task_words.append(word)
        
        # 関数を呼び出している場所にタスク名を返している
        if task_words:
            return " ".join(task_words[:3])
        
        return ""

# 期限を抽出する
    def _extract_due_date(self, text: str) -> Optional[str]:
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})月(\d{1,2})日'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    if pattern == r'(\d{1,2})月(\d{1,2})日':
                        month, day = matches[0]
                        year = datetime.datetime.now().year
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif pattern == r'(\d{1,2})/(\d{1,2})/(\d{4})':
                        month, day, year = matches[0]
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    else:
                        year, month, day = matches[0]
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                except:
                    continue
        
        relative_patterns = {
            "今日": 0,
            "明日": 1,
            "明後日": 2,
            "来週": 7
        }
        
        for keyword, days in relative_patterns.items():
            if keyword in text:
                target_date = datetime.datetime.now() + datetime.timedelta(days=days)
                return target_date.strftime("%Y-%m-%d")
        
        return None

    def _extract_task_index(self, text: str) -> Optional[int]:
        number_patterns = [
            r'(\d+)番目',
            r'(\d+)番',
            r'No\.(\d+)',
            r'(\d+)つ目'
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    return int(matches[0])
                except:
                    continue
        
        return None

    def generate_confirmation_message(self, parsed_data: Dict) -> str:
        # parsed_dataからgetメソッドを用いて抽出する
        action = parsed_data.get("action", "UNKNOWN")
        task_name = parsed_data.get("task_name", "")
        due_date = parsed_data.get("due_date", "")
        task_index = parsed_data.get("task_index")
        
        if action == "ADD":
            msg = f"タスク「{task_name}」を追加します"
            if due_date:
                msg += f"（期限: {due_date}）"
        elif action == "EDIT":
            if task_index:
                msg = f"タスク{task_index}番を編集します"
            else:
                msg = f"タスク「{task_name}」を編集します"
        elif action == "DELETE":
            if task_index:
                msg = f"タスク{task_index}番を削除します"
            else:
                msg = f"タスク「{task_name}」を削除します"
        elif action == "COMPLETE":
            if task_index:
                msg = f"タスク{task_index}番を完了にします"
            else:
                msg = f"タスク「{task_name}」を完了にします"
        elif action == "SHOW":
            msg = "タスク一覧を表示します"
        else:
            msg = "操作を理解できませんでした。もう一度お試しください。"
        
        return msg

    def extract_task_info(self, text: str) -> TaskInfo:
        """
        自然言語入力からタスク情報を抽出（Structured Output）
        
        Args:
            text: ユーザーの自然言語入力
            
        Returns:
            TaskInfo: 抽出されたタスク情報
        """
        try:
            system_prompt = """あなたはタスク管理アプリの情報抽出エンジンです。
ユーザーの入力から以下の情報を抽出してください：

1. summary: タスク名/イベント名
2. start_datetime: 開始日時（ISO 8601形式、例: 2025-12-20T15:00:00）
3. duration_minutes: 所要時間（分）、明記されていない場合は60分
4. has_datetime: 日時情報が含まれているかどうか
5. confidence: 抽出の信頼度（0.0-1.0）

相対的な日時表現（今日、明日、金曜日など）は具体的な日時に変換してください。
時刻が指定されていない場合は、適切なデフォルト時刻を設定してください。

回答は必ずJSON形式で返してください：
{
    "summary": "抽出されたタスク名",
    "start_datetime": "2025-12-20T15:00:00",
    "duration_minutes": 60,
    "has_datetime": true,
    "confidence": 0.9
}"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"ユーザー入力: {text}"}
                ],
                "temperature": 0.1
            }
            
            # APIにリクエストを送る
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            ai_response = response_data["choices"][0]["message"]["content"]
            
            # JSON形式の回答を抽出
            result = self._extract_json_from_response(ai_response)
            
            if result:
                return TaskInfo(**result)
            else:
                # フォールバック: 既存の抽出ロジックを使用
                return self._fallback_extract_task_info(text)
                
        except Exception as e:
            print(f"タスク情報抽出エラー: {e}")
            return self._fallback_extract_task_info(text)

    def _fallback_extract_task_info(self, text: str) -> TaskInfo:
        """
        LLM処理失敗時のフォールバック抽出
        
        Args:
            text: ユーザー入力
            
        Returns:
            TaskInfo: 抽出されたタスク情報
        """
        # 既存のロジックを使用
        task_name = self._extract_task_name(text)
        due_date = self._extract_due_date(text)
        
        # 日時情報の変換
        start_datetime = None
        has_datetime = False
        
        if due_date:
            try:
                # 日付のみの場合は適切な時刻を設定
                if len(due_date) == 10:  # YYYY-MM-DD形式
                    start_datetime = f"{due_date}T10:00:00"  # デフォルト10:00
                else:
                    start_datetime = due_date
                has_datetime = True
            except:
                pass
        
        return TaskInfo(
            summary=task_name if task_name else "新しいタスク",
            start_datetime=start_datetime,
            duration_minutes=60 if has_datetime else None,
            has_datetime=has_datetime,
            confidence=0.7
        )

    def add_calendar_event(self, task_info: TaskInfo) -> Optional[str]:
        """
        Googleカレンダーにイベントを作成
        
        Args:
            task_info: タスク情報
            
        Returns:
            イベントID（失敗時はNone）
        """
        if not self.calendar_enabled or not task_info.has_datetime:
            return None
            
        try:
            # 終了時刻を計算
            start_dt = datetime.datetime.fromisoformat(task_info.start_datetime)
            duration = datetime.timedelta(minutes=task_info.duration_minutes or 60)
            end_dt = start_dt + duration
            
            event_id = self.calendar_client.create_event(
                summary=task_info.summary,
                start_datetime=start_dt.isoformat(),
                end_datetime=end_dt.isoformat(),
                description=f"タスク管理アプリから作成されたイベント"
            )
            
            return event_id
            
        except Exception as e:
            print(f"カレンダーイベント作成エラー: {e}")
            return None