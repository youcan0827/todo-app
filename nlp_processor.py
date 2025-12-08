#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import datetime
from typing import Dict, Optional, List, Tuple
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

class NLPProcessor:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY環境変数が設定されていません")
        
        self.llm = ChatOpenAI(
            model="openai/gpt-3.5-turbo",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )
        
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

    def parse_natural_language(self, user_input: str) -> Dict[str, any]:
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"ユーザー入力: {user_input}")
            ]
            
            response = self.llm.invoke(messages)
            result = self._extract_json_from_response(response.content)
            
            if not result:
                return self._fallback_parse(user_input)
            
            return result
            
        except Exception as e:
            print(f"OpenRouter API処理エラー: {e}")
            return self._fallback_parse(user_input)

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        import json
        
        json_pattern = r'\{.*?\}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None

    def _fallback_parse(self, user_input: str) -> Dict[str, any]:
        user_input = user_input.lower()
        
        add_keywords = ["追加", "作成", "新規", "登録", "add", "create", "new"]
        edit_keywords = ["編集", "修正", "変更", "更新", "edit", "modify", "update"]
        delete_keywords = ["削除", "消去", "remove", "delete"]
        show_keywords = ["表示", "確認", "一覧", "show", "list", "view"]
        complete_keywords = ["完了", "終了", "done", "complete", "finish"]
        
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

    def _extract_task_name(self, text: str) -> str:
        quote_patterns = [r'"([^"]+)"', r"'([^']+)'", r"「([^」]+)」"]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        words = text.split()
        task_words = []
        skip_words = {"を", "の", "に", "で", "は", "が", "と", "から", "まで", "する", "した", "です", "ます"}
        
        for word in words:
            if word not in skip_words and len(word) > 1:
                task_words.append(word)
        
        if task_words:
            return " ".join(task_words[:3])
        
        return ""

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