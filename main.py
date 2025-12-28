#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Style-Bert-VITS2パス優先順位修正
# システムインストール済みライブラリを最優先で読み込む
import sys
import os

# カレントディレクトリを sys.path から除去（古いローカルファイルを避ける）
if '.' in sys.path:
    sys.path.remove('.')
if '' in sys.path:
    sys.path.remove('')

# システムライブラリパスを最優先に設定
system_lib_path = '/usr/local/lib/python3.12/dist-packages'
if system_lib_path not in sys.path:
    sys.path.insert(0, system_lib_path)

# 標準ライブラリのインポート
import csv
import datetime
from typing import List, Dict, Optional

# Style-Bert-VITS2インポートテスト
try:
    from style_bert_vits2.utils import torch_device_to_onnx_providers
    print("✅ style_bert_vits2.utils.torch_device_to_onnx_providers のインポートに成功しました")
except ImportError as e:
    print(f"❌ style_bert_vits2.utils.torch_device_to_onnx_providers のインポートに失敗: {e}")
    print("💡 Google Colabで 'pip install style_bert_vits2' を実行してください")
# 履歴確認機能（統合版に移行済み）
# 画像生成機能（オプション）
try:
    from image.z_image import generate_celebration_image
    IMAGE_GENERATION_AVAILABLE = True
except ImportError:
    IMAGE_GENERATION_AVAILABLE = False
    def generate_celebration_image(mood):
        print("画像生成機能は利用できません（依存関係が不足しています）")
# 統合LangChain自然言語モード
try:
    from integrated_langchain import integrated_langchain_mode as natural_language_mode_langchain
    LANGCHAIN_NLP_AVAILABLE = True
    print("✅ 統合LangChain自然言語モード（拡張機能付き）が利用可能です")
except ImportError:
    LANGCHAIN_NLP_AVAILABLE = False
    def natural_language_mode_langchain():
        print("統合LangChain自然言語モードは利用できません（LangChain依存関係が不足しています）")
        print("requirements.txtから必要な依存関係をインストールしてください。")


# CSVファイルのパス定義
CSV_FILE = "tasks.csv"
# CSVヘッダー定義
CSV_HEADERS = ["task_name", "due_date", "status", "created_at", "calendar_event_id"]

# csvファイルがない場合作る
def initialize_csv() -> None:
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

# csvファイルを読み込む時によく使う関数
def read_tasks() -> List[Dict[str, str]]:
    tasks = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            # csvを辞書形式で読み込んで、tasksに格納する
            reader = csv.DictReader(file)
            for row in reader:
                tasks.append(row)
    except FileNotFoundError:
        # ファイルが存在しない場合は空リストを返す
        pass
    return tasks

# csvファイルに書き込む時によく使う関数
def write_tasks(tasks: List[Dict[str, str]]) -> None:
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        # csvモジュールにおけるDictWriterメソッドをを呼び出す
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        # ヘッダーを書き込む
        writer.writeheader()
        # tasksを書き込む
        writer.writerows(tasks)

# 「タスク追加」の時に呼び出す
def add_task() -> None:
    print("\n=== タスク追加 ===")
    
    # タスク名入力
    task_name = input("タスク名を入力してください: ").strip()
    if not task_name:
        print("エラー: タスク名は必須です。")
        return
    
    # 期限入力
    due_date = input("期限を入力してください (YYYY-MM-DD形式): ").strip()
    
    # 期限の形式バリデーション（簡易）
    if due_date:
        try:
            # 多分既存のdatetimeモジュールのstriptimeを呼び出して%Y-%m-%dの形にしているのかな
            datetime.datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            print("エラー: 期限は YYYY-MM-DD 形式で入力してください。")
            return
    
    # 新規タスクデータ作成
    new_task = {
        "task_name": task_name,
        "due_date": due_date,
        "status": "todo",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "calendar_event_id": ""
    }
    
    # 既存タスクを読み込み、新規タスクを追加 
    # read_task関数呼び出して、csv読み込んで、そこにnew_taskを追加して保存する
    # new_tasks（詳細の情報）はtasksに追加されて、tasksはread_tasks()である。じゃあread_tasks()は、、
    tasks = read_tasks()
    # tasksにnew_taskを追加
    tasks.append(new_task)
    # write_tasks関数を呼び出して、tasksをcsvファイルに書き込む
    write_tasks(tasks)
    
    print(f"タスク「{task_name}」が追加されました。")



# [タスク確認]の際に呼び出す
def show_tasks() -> None:
    print("\n=== タスク一覧 ===")
    tasks = read_tasks()
    
    if not tasks:
        print("データがありません。")
        return
    
    # タスクを番号付きで表示
    # 通常インデックス番号は0からだが、enumerateを使用することで1から表示できる
    # iが数字で、taskは辞書内容？
    for i, task in enumerate(tasks, 1):
        due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
        status_jp = "完了" if task["status"] == "done" else "未完了"
        print(f"[No.{i}] {task['task_name']}{due_info} - Status: {status_jp}")

# 「タスク完了」の際に呼び出す
def complete_task() -> None:
    print("\n=== タスク完了 ===")
    # read_tasks関数を呼び出して、csvファイルを読み込み、tasksという変数に格納する
    tasks = read_tasks()
    
    if not tasks:
        print("データがありません。")
        return
    
    # 未完了タスクのみ表示
    # statusがtodoのものはincomplate_tasksだと定義
    incomplete_tasks = [task for task in tasks if task["status"] == "todo"]
    
    # もしincomplateなタスクがなければ完了可能にできるタスクはないと返す
    if not incomplete_tasks:
        print("完了可能なタスクがありません。")
        return
    
    # 未完了のタスクを表示
    print("未完了のタスク:")
    task_indices = []
    display_count = 1
    
    # enumerateで1からカウントして表示
    # タスクのstatusがtodoなら具体的に情報を表示する
    # tasksは本来read_tasksであり、new_tasksでもある
    for i, task in enumerate(tasks):
        if task["status"] == "todo":
            due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
            print(f"[No.{display_count}] {task['task_name']}{due_info}")
            task_indices.append(i)
            display_count += 1
    
    # 未完了のタスクを見つけた時の上書きアプローチをtryで実行
    try:
        choice = int(input("\n完了するタスクの番号を入力してください: "))
        if 1 <= choice <= len(task_indices):
            actual_index = task_indices[choice - 1]
            completed_task_name = tasks[actual_index]['task_name']
            tasks[actual_index]["status"] = "done"
            write_tasks(tasks)
            print(f"タスク「{completed_task_name}」を完了しました。")
            
            
            # 画像生成を追加（利用可能な場合のみ）
            if IMAGE_GENERATION_AVAILABLE:
                print("\nおめでとうございます！タスクを完了しました。")
                mood = input("今の気分を教えてください（例: 嬉しい、達成感、リラックスなど）: ").strip()
                
                if mood:
                    try:
                        generate_celebration_image(mood)
                    except Exception as e:
                        print(f"画像生成中にエラーが発生しました: {e}")
                        print("タスクは正常に完了しましたが、画像生成をスキップします。")
                else:
                    print("気分の入力がなかったため、画像生成をスキップします。")
            else:
                print("\nおめでとうございます！タスクを完了しました。")
        else:
            print("エラー: 無効な番号です。")
    except ValueError:
        print("エラー: 数値を入力してください。")

def natural_language_mode() -> None:
    """統合された自然言語モード（LangChain使用）"""
    if LANGCHAIN_NLP_AVAILABLE:
        natural_language_mode_langchain()
    else:
        print("\n❌ LangChain自然言語モードは利用できません")
        print("必要な依存関係をインストールしてください：")
        print("pip install langchain langchain-openai python-dotenv")




# メニュー画面
def show_menu() -> None:
    print("\n" + "="*40)
    print("         CLI TODO管理アプリ")
    print("="*40)
    print("1. タスク追加")
    print("2. タスク確認")
    print("3. タスク完了")
    print("4. 🤖 AI自然言語モード（LangChain統合）")
    print("5. 終了")
    print("="*40)

# メニュー画面の選択に応じた挙動
def main() -> None:
    # CSVファイル初期化
    initialize_csv()
    
    print("CLI TODO管理アプリへようこそ！")
    
    while True:
        show_menu()
        choice = input("選択してください (1-5): ").strip()
        
        if choice == "1":
            add_task()
        elif choice == "2":
            show_tasks()
        elif choice == "3":
            complete_task()
        elif choice == "4":
            natural_language_mode()
        elif choice == "5":
            print("アプリケーションを終了します。")
            break
        else:
            print("エラー: 1-5の数字を入力してください。")


if __name__ == "__main__":
    main()