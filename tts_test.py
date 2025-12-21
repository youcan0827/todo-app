#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音声合成機能のテスト用スクリプト
"""

def test_tts_system():
    """音声合成システムのテスト"""
    try:
        from integrated_langchain import initialize_tts_system, text_to_speech_if_available
        
        print("🧪 音声合成システムのテスト開始")
        print("=" * 50)
        
        # Step 1: TTS初期化
        print("Step 1: TTS初期化")
        tts = initialize_tts_system(
            model_name="yoshino_test",
            model_dir="model_assets", 
            device="cuda"
        )
        
        # Step 2: テスト音声合成
        print("\nStep 2: テスト音声合成")
        test_text = "こんにちは。これはひろゆき風音声合成のテストです。"
        audio_file = text_to_speech_if_available(test_text, "test_output.wav")
        
        if audio_file:
            print(f"✅ 音声ファイル生成成功: {audio_file}")
        else:
            print("❌ 音声合成に失敗しました")
        
        # Step 3: 統合システムテスト
        print("\nStep 3: 統合システムテスト")
        from integrated_langchain import IntegratedLangChainAgent
        
        agent = IntegratedLangChainAgent()
        response = agent.process_query("オイラで敬語で答えて。今日の天気はどう？")
        
        print(f"応答: {response[:100]}...")
        
        # 音声合成
        audio_file2 = text_to_speech_if_available(response, "integrated_test.wav")
        if audio_file2:
            print(f"✅ 統合音声ファイル: {audio_file2}")
        
        print("\n" + "=" * 50)
        print("🎉 テスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

def test_without_model():
    """model_loadなしでのテスト"""
    print("🧪 model_loadなしでのテスト")
    print("=" * 30)
    
    try:
        from integrated_langchain import initialize_tts_system, text_to_speech_if_available
        
        tts = initialize_tts_system()
        result = text_to_speech_if_available("テストです")
        
        if result is None:
            print("✅ model_loadなし環境での適切なハンドリング確認")
        else:
            print("⚠️ 予期しない動作")
            
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    print("🎵 音声合成システム テストスイート")
    print("=" * 60)
    
    # テスト選択
    print("テスト選択:")
    print("1. フル機能テスト（model_load必要）")
    print("2. model_loadなしテスト")
    
    try:
        choice = input("選択 (1/2): ").strip()
        
        if choice == "1":
            test_tts_system()
        elif choice == "2":
            test_without_model()
        else:
            print("❌ 無効な選択")
            
    except KeyboardInterrupt:
        print("\n👋 テスト終了")