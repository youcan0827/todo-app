#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from google_calendar.simple_langchain_tools import get_simple_langchain_tools
from dotenv import load_dotenv

load_dotenv()


class SimpleLangChainAgent:
    """シンプルなLangChain使用エージェント"""
    
    def __init__(self):
        # OpenRouter APIの設定
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY環境変数が設定されていません")
        
        # OpenAI互換のAPIクライアント設定
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )
        
        # 利用可能なツールを取得
        self.tools = get_simple_langchain_tools()
        
        # システムプロンプト
        self.system_prompt = """あなたは高機能なタスク管理アシスタントです。
ユーザーの質問に応じて、以下のツールを使用して情報を取得し、回答してください：

利用可能なツール:
1. search_calendar_events: Googleカレンダーから予定を検索
2. list_csv_tasks: CSVファイルからタスクリストを取得

ユーザーの質問を分析して、必要なツールを実行し、結果を統合してわかりやすく回答してください。
日本語で親しみやすい口調で回答してください。"""
    
    def process_query(self, user_input: str) -> str:
        """ユーザーの質問を処理"""
        try:
            # 1. 質問を分析してツールを選択
            tools_to_use = self._analyze_query(user_input)
            
            # 2. ツールを実行して結果を取得
            tool_results = self._execute_tools(tools_to_use)
            
            # 3. LLMで結果を統合・回答生成
            response = self._generate_response(user_input, tool_results)
            
            return response
            
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
    
    def _analyze_query(self, query: str) -> Dict[str, bool]:
        """クエリを分析して必要なツールを特定"""
        query_lower = query.lower()
        
        # キーワードベースで判定
        needs_calendar = any(kw in query_lower for kw in ['予定', 'スケジュール', 'カレンダー', '会議'])
        needs_tasks = any(kw in query_lower for kw in ['タスク', 'やること', 'todo', '未完了', '完了'])
        
        # どちらも明確でない場合は両方
        if not needs_calendar and not needs_tasks:
            needs_calendar = needs_tasks = True
        
        return {
            'calendar': needs_calendar,
            'tasks': needs_tasks
        }
    
    def _execute_tools(self, tools_to_use: Dict[str, bool]) -> Dict[str, str]:
        """必要なツールを実行"""
        results = {}
        
        try:
            # カレンダー検索
            if tools_to_use['calendar']:
                calendar_tool = self.tools[0]  # search_calendar_events
                results['calendar'] = calendar_tool.invoke({"query": ""})
            
            # タスクリスト取得
            if tools_to_use['tasks']:
                task_tool = self.tools[1]  # list_csv_tasks
                results['tasks'] = task_tool.invoke({"status_filter": "todo"})  # 未完了タスクのみ
                
        except Exception as e:
            results['error'] = f"ツール実行エラー: {str(e)}"
        
        return results
    
    def _generate_response(self, user_input: str, tool_results: Dict[str, str]) -> str:
        """LLMで結果を統合して回答生成"""
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
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            # フォールバック
            if context:
                return f"以下の情報が取得できました：\n\n{context}"
            else:
                return "申し訳ございませんが、情報を取得できませんでした。"


def simple_langchain_mode() -> None:
    """シンプルLangChainモードのメイン処理"""
    print("\n=== LangChain高機能自然言語モード ===")
    print("LangChainを使ってカレンダーとタスクの情報を検索してお答えします。")
    print("例: '今週の予定と未完了タスクを教えて'、'明日やることは？'")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    try:
        # エージェントの初期化
        print("🤖 LangChainエージェントを初期化しています...")
        agent = SimpleLangChainAgent()
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
            print("👋 LangChain高機能自然言語モードを終了します。")
            break
        
        if not user_input:
            print("❓ 質問を入力してください。")
            continue
        
        print("\n🔍 LangChainが情報を検索・分析しています...")
        
        # エージェントで処理
        response = agent.process_query(user_input)
        print(f"\n🤖 **回答**:\n{response}\n")
        print("-" * 60)


if __name__ == "__main__":
    simple_langchain_mode()