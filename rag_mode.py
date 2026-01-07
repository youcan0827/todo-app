#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import datetime
from typing import Optional

try:
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
    from llama_index.core.node_parser import SentenceSplitter
    import pdfplumber
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

def extract_pdf_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def rag_mode() -> None:
    if not RAG_AVAILABLE:
        print("\n❌ RAGモードは利用できません")
        print("必要な依存関係をインストールしてください：")
        print("pip install llama-index pdfplumber")
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
        pdf_text = extract_pdf_text(pdf_path)
        
        if not pdf_text.strip():
            print("❌ PDFからテキストを抽出できませんでした")
            return
        
        print("🧠 インデックスを作成しています...")
        
        with open("temp_text.txt", "w", encoding="utf-8") as temp_file:
            temp_file.write(pdf_text)
        
        documents = SimpleDirectoryReader(input_files=["temp_text.txt"]).load_data()
        
        Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        index = VectorStoreIndex.from_documents(documents)
        query_engine = index.as_query_engine()
        
        os.remove("temp_text.txt")
        
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
        if os.path.exists("temp_text.txt"):
            os.remove("temp_text.txt")