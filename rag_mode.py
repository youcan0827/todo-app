#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import datetime

try:
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, PromptTemplate
    from llama_index.core.node_parser import SentenceSplitter
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

QA_TEMPLATE = None
if RAG_AVAILABLE:
    QA_TEMPLATE = PromptTemplate(
        "以下のコンテキスト情報を参照してください。\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "上記の情報に基づき、以下の質問に日本語で回答してください。\n"
        "質問: {query_str}\n"
        "回答:"
    )

def rag_mode() -> None:
    if not RAG_AVAILABLE:
        print("\n❌ RAGモードは利用できません")
        print("pip install llama-index llama-index-readers-file")
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
    
    print("📄 PDFを読み込んでいます...")
    documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()

    if not documents:
        print("❌ PDFからテキストを抽出できませんでした")
        return

    print("🧠 インデックスを作成しています...")
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine(text_qa_template=QA_TEMPLATE)

    print("✅ インデックス作成完了！")
    print("PDFについて質問してください（'exit'で終了）")

    pdf_filename = os.path.basename(pdf_path)

    while True:
        question = input("\n質問: ").strip()
        if question.lower() == 'exit':
            break
        if not question:
            continue

        print("🤖 回答を生成中...")
        response = query_engine.query(question)
        answer = str(response)
        print(f"\n回答: {answer}")
        save_rag_conversation(pdf_filename, question, answer)
        print("✅ 会話を記録しました")

    print("\nRAGモードを終了します")