#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Any, Dict, List, Optional
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from google_calendar.langchain_tools import get_langchain_tools
from dotenv import load_dotenv

load_dotenv()


class AdvancedNLPAgent:
    """高機能自然言語モード用のLangChainエージェント"""
    
    def __init__(self):
        # OpenRouter APIの設定
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY環境変数が設定されていません")
        
        # OpenAI互換のAPIクライアント設定
        self.llm = ChatOpenAI(
            model="openai/gpt-3.5-turbo",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )
        
        # 利用可能なツールを取得
        self.tools = get_langchain_tools()
        
        # エージェント用のプロンプトテンプレート
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # エージェントの作成
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
    
    def _get_system_prompt(self) -> str:
        """エージェント用のシステムプロンプト"""
        return """あなたは高機能なタスク管理アシスタントです。
ユーザーの質問や依頼に応じて、以下のツールを自律的に使用してください：

1. search_calendar_events: Googleカレンダーから予定を検索する
2. list_csv_tasks: CSVファイルからタスクの一覧を取得する

ユーザーが予定やタスクについて質問した場合は、適切なツールを選択・実行し、
結果を統合してわかりやすく回答してください。

例：
- 「今週の予定は？」→ search_calendar_eventsで今週の予定を検索
- 「未完了のタスクは？」→ list_csv_tasksで未完了タスクをフィルタ
- 「今日の予定と未完了タスクを教えて」→ 両方のツールを実行して統合

回答は日本語で、親しみやすい口調で行ってください。
エラーが発生した場合は、その旨をユーザーに分かりやすく伝えてください。"""
    
    def process_query(self, user_input: str) -> str:
        """
        ユーザーの質問を処理してエージェントに回答させる
        
        Args:
            user_input: ユーザーの質問や依頼
            
        Returns:
            エージェントからの回答
        """
        try:
            result = self.agent_executor.invoke({"input": user_input})
            return result.get("output", "申し訳ございませんが、回答を生成できませんでした。")
        
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"


def advanced_natural_language_mode() -> None:
    """高機能自然言語モード（エージェント化）のメイン処理"""
    print("\n=== 高機能自然言語モード ===")
    print("AIエージェントがカレンダーとタスクの情報を使って質問にお答えします。")
    print("例: '今週の予定と未完了タスクを教えて'、'明日は何をする予定？'")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    try:
        # エージェントの初期化
        print("AIエージェントを初期化しています...")
        agent = AdvancedNLPAgent()
        print("✓ 初期化完了\n")
        
    except ValueError as e:
        print(f"エラー: {e}")
        print("環境変数OPENROUTER_API_KEYを設定してください。")
        return
    except Exception as e:
        print(f"エージェント初期化エラー: {e}")
        return
    
    # 対話ループ
    while True:
        user_input = input("質問を入力してください: ").strip()
        
        # 終了条件
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit']:
            break
        
        if not user_input:
            continue
        
        print("\n🤖 AIエージェントが回答を生成しています...\n")
        
        # エージェントで処理
        response = agent.process_query(user_input)
        print(f"📋 回答: {response}\n")
        print("-" * 50)


# テスト関数
def test_agent():
    """エージェントのテスト実行"""
    try:
        print("=== エージェントテスト ===")
        agent = AdvancedNLPAgent()
        
        test_queries = [
            "未完了のタスクはありますか？",
            "今週の予定を教えて",
            "今日やるべきことは何ですか？"
        ]
        
        for query in test_queries:
            print(f"\n質問: {query}")
            response = agent.process_query(query)
            print(f"回答: {response}")
            print("-" * 30)
            
    except Exception as e:
        print(f"テストエラー: {e}")


if __name__ == "__main__":
    test_agent()