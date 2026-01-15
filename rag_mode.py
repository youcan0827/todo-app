#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import datetime
from typing import Optional

try:
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.prompts import PromptTemplate
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

RAG_CSV_FILE = "rag_conversations.csv"
RAG_CSV_HEADERS = ["timestamp", "pdf_file", "question", "answer"]

def initialize_rag_csv() -> None:
    if not os.path.exists(RAG_CSV_FILE):
        with open(RAG_CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(RAG_CSV_HEADERS)

def save_rag_conversation(pdf_file: str, question: str, answer: str) -> None:
    with open(RAG_CSV_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, pdf_file, question, answer])


def rag_mode() -> None:
    if not RAG_AVAILABLE:
        print("\n❌ RAGモードは利用できません")
        print("必要な依存関係をインストールしてください：")
        print("pip install llama-index")
        return
    
    initialize_rag_csv()
    
    print("\n=== RAGモード ===")
    print("PDFファイルをアップロードして質問してください")
    
    pdf_path = input("PDFファイルのパスを入力してください: ").strip()
    
    if not os.path.exists(pdf_path):
        print("❌ ファイルが見つかりません")
        return
    
    if not pdf_path.lower().endswith('.pdf'):
        print("❌ PDFファイルを指定してください")
        return
    
    try:
        print("📄 PDFを読み込んでいます...")
        documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()

        if not documents:
            print("❌ PDFからテキストを抽出できませんでした")
            return

        print("🧠 インデックスを作成しています...")
        Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        index = VectorStoreIndex.from_documents(documents)

        qa_prompt_tmpl = PromptTemplate(
            "あなたは日本語で回答するアシスタントです。"
            "以下の情報を参考にして、質問に日本語で正確に答えてください。\n\n"
            "情報:\n{context_str}\n\n"
            "質問: {query_str}\n"
            "回答:"
        )
        query_engine = index.as_query_engine(text_qa_template=qa_prompt_tmpl)
        
        print("✅ インデックス作成完了！")
        print("\nPDFについて質問してください（'exit'で終了）")
        
        pdf_filename = os.path.basename(pdf_path)
        
        while True:
            question = input("\n質問: ").strip()
            
            if question.lower() == 'exit':
                break
            
            if not question:
                print("質問を入力してください")
                continue
            
            print("🤖 回答を生成中...")
            response = query_engine.query(question)
            answer = str(response)
            
            print(f"\n回答: {answer}")
            
            save_rag_conversation(pdf_filename, question, answer)
            print("✅ 会話を記録しました")
        
        print("\nRAGモードを終了します")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")