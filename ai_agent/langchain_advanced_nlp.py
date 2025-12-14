#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Any, Dict, List, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from google_calendar.langchain_tools import get_langchain_tools
from dotenv import load_dotenv

load_dotenv()


class LangChainAdvancedNLPAgent:
    """LangChainを使用した高機能自然言語エージェント"""
    
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
        self.tools = get_langchain_tools()
        
        # ReAct形式のプロンプトテンプレート
        self.prompt = PromptTemplate.from_template("""
あなたは高機能なタスク管理アシスタントです。
ユーザーの質問や依頼に応じて、以下のツールを自律的に使用してください：

利用可能なツール:
{tools}

ツールの使用形式:
Action: [使用するツール名]
Action Input: [ツールへの入力（JSON形式）]
Observation: [ツールからの結果]

質問に答えるために、適切なツールを選択・実行し、結果を統合してわかりやすく回答してください。
回答は日本語で、親しみやすい口調で行ってください。

ユーザーの質問: {input}

{agent_scratchpad}
""")
        
        # エージェントの作成
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True,
            early_stopping_method="force"
        )
    
    def process_query(self, user_input: str) -> str:
        """
        ユーザーの質問を処理してエージェントに回答させる
        
        Args:
            user_input: ユーザーの質問や依頼
            
        Returns:
            エージェントからの回答
        """
        try:
            result = self.agent_executor.invoke({
                "input": user_input,
                "tools": "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            })
            return result.get("output", "申し訳ございませんが、回答を生成できませんでした。")
        
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"


def langchain_natural_language_mode() -> None:
    """LangChain高機能自然言語モードのメイン処理"""
    print("\n=== LangChain高機能自然言語モード ===")
    print("LangChainエージェントがカレンダーとタスクの情報を使って質問にお答えします。")
    print("例: '今週の予定と未完了タスクを教えて'、'明日は何をする予定？'")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    try:
        # エージェントの初期化
        print("🤖 LangChainエージェントを初期化しています...")
        agent = LangChainAdvancedNLPAgent()
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
        
        print("\n🔍 LangChainエージェントが情報を検索・分析しています...")
        
        # エージェントで処理
        response = agent.process_query(user_input)
        print(f"\n🤖 **回答**:\n{response}\n")
        print("-" * 60)


# テスト関数
def test_langchain_agent():
    """LangChainエージェントのテスト実行"""
    try:
        print("=== LangChainエージェントテスト ===")
        agent = LangChainAdvancedNLPAgent()
        
        test_queries = [
            "未完了のタスクはありますか？",
            "今週の予定を教えて"
        ]
        
        for query in test_queries:
            print(f"\n質問: {query}")
            response = agent.process_query(query)
            print(f"回答: {response}")
            print("-" * 30)
            
    except Exception as e:
        print(f"テストエラー: {e}")


if __name__ == "__main__":
    test_langchain_agent()