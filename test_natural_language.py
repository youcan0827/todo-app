#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from dotenv import load_dotenv
from nlp_processor import NLPProcessor

load_dotenv()

def main():
    print("=== 自然言語処理テスト ===")
    
    # テスト前の確認
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("エラー: OPENROUTER_API_KEYが設定されていません。")
        print(".envファイルを確認してください。")
        return
    
    try:
        nlp = NLPProcessor()
        print("NLPプロセッサーの初期化成功")
        
        # テストケース
        test_cases = [
            "明日までに買い物を追加して",
            "タスク一覧を見せて",
            "1番目のタスクを削除",
            "宿題というタスクを完了して",
            "来週までに報告書を作成する",
            "不明な操作"
        ]
        
        for test_case in test_cases:
            print(f"\n入力: '{test_case}'")
            try:
                result = nlp.parse_natural_language(test_case)
                print(f"解析結果: {result}")
                
                confirmation = nlp.generate_confirmation_message(result)
                print(f"確認メッセージ: {confirmation}")
            except Exception as e:
                print(f"エラー: {e}")
            
            print("-" * 50)
        
    except Exception as e:
        print(f"初期化エラー: {e}")

if __name__ == "__main__":
    main()