#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import datetime
from typing import List, Dict, Optional
from nlp_processor import NLPProcessor


# CSVファイルのパス定義
CSV_FILE = "tasks.csv"
# CSVヘッダー定義
CSV_HEADERS = ["task_name", "due_date", "status", "created_at"]

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
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

def add_task_from_nlp(parsed_data: Dict) -> None:
    task_name = parsed_data.get("task_name", "").strip()
    due_date = parsed_data.get("due_date", "").strip()
    
    if not task_name:
        print("エラー: タスク名が特定できませんでした。")
        return
    
    if due_date:
        try:
            datetime.datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            print(f"警告: 期限の形式が不正です（{due_date}）。期限なしで登録します。")
            due_date = ""
    
    new_task = {
        "task_name": task_name,
        "due_date": due_date,
        "status": "todo",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    tasks = read_tasks()
    tasks.append(new_task)
    write_tasks(tasks)
    
    due_info = f" (期限: {due_date})" if due_date else ""
    print(f"タスク「{task_name}」を追加しました{due_info}")

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
            tasks[actual_index]["status"] = "done"
            write_tasks(tasks)
            print(f"タスク「{tasks[actual_index]['task_name']}」を完了しました。")
        else:
            print("エラー: 無効な番号です。")
    except ValueError:
        print("エラー: 数値を入力してください。")

def natural_language_mode() -> None:
    # 4が選択されたらこのテキストが出力される
    print("\n=== 自然言語モード ===")
    print("自然な日本語でタスクの操作を指示してください。")
    print("例: '明日までに買い物を追加して'、'1番目のタスクを削除'、'タスク一覧を見せて'")
    print("'戻る'と入力すると通常モードに戻ります。\n")
    
    # NLPProcessorクラス（APIに関する処理）を呼び出して、それが無理ならエラーを出力
    try:
        #これがAPIの確認と呼び出し
        nlp = NLPProcessor()
    except ValueError as e:
        print(f"エラー: {e}")
        print("環境変数OPENROUTER_API_KEYを設定してください。")
        return
    
    # while True（APIが稼働できている状態の時？）
    while True:
        user_input = input("自然言語で操作を指示してください: ").strip()
        
        # この四つが入力されないと戻れない（元のインターフェースに戻る時のみ）
        if user_input.lower() in ['戻る', 'back', 'exit', 'quit']:
            break
        
        # 入力がない場合は何もしない
        if not user_input:
            continue
        
        # actionの変数に対するparsed_data.getはnlp_processor.pyから関数の中身を呼び出している
        # これがキーワードではなく、自然言語処理を行うコード部分
        try:
            # ユーザーインプットを引数に入れてparse_natural_language関数を呼び出す
            # parsed_natural_language関数のリターン値（json）をparsed_dataとして格納できる
            # これって元々の自然言語である引数のuser_inputがリターン値に成長して返ってきているということ？←その通り
            parsed_data = nlp.parse_natural_language(user_input)
            action = parsed_data.get("action", "UNKNOWN")
            
            #　confirmationにJSON形式のメッセージを引数に入れてgenerate_confirmation_message関数を呼び出す
            # リターンで〜という{task_name}を〜〜しますとリターンが返ってくる
            confirmation = nlp.generate_confirmation_message(parsed_data)
            # 〜〜という{task_name}を〜〜しますと出力
            print(f"解釈: {confirmation}")
            
            if action == "UNKNOWN":
                print("操作を理解できませんでした。もう一度お試しください。")
                continue
            
            confirm = input("この操作を実行しますか？ (y/n): ").strip().lower()
            if confirm not in ['y', 'yes', 'はい']:
                print("操作をキャンセルしました。")
                continue
            
            # それぞれのアクションに対する変数を呼び出す。ADDだったらadd_keywords = ["追加", "作成", "新規", "登録", "add", "create", "new"]
            if action == "ADD":
                # add_keywordsの中のどれかが入力されたらadd_task_from_nlpを呼び出す？でもnlp_processor.pyになかった
                add_task_from_nlp(parsed_data)
            elif action == "SHOW":
                show_tasks()
            elif action == "EDIT":
                edit_task_from_nlp(parsed_data)
            elif action == "DELETE":
                delete_task_from_nlp(parsed_data)
            elif action == "COMPLETE":
                complete_task_from_nlp(parsed_data)
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")

# タスク編集について
def edit_task_from_nlp(parsed_data: Dict) -> None:
    tasks = read_tasks()
    if not tasks:
        print("タスクがありません。")
        return
    
    task_index = parsed_data.get("task_index")
    task_name = parsed_data.get("task_name", "")
    
    target_index = None
    
    if task_index and 1 <= task_index <= len(tasks):
        target_index = task_index - 1
    elif task_name:
        for i, task in enumerate(tasks):
            if task_name.lower() in task["task_name"].lower():
                target_index = i
                break
    
    if target_index is None:
        print("対象のタスクが見つかりませんでした。")
        return
    
    old_task = tasks[target_index]
    print(f"編集対象: {old_task['task_name']}")
    
    new_name = input(f"新しいタスク名 (現在: {old_task['task_name']}): ").strip()
    if new_name:
        tasks[target_index]["task_name"] = new_name
    
    new_due = input(f"新しい期限 (現在: {old_task['due_date']}): ").strip()
    if new_due:
        try:
            datetime.datetime.strptime(new_due, "%Y-%m-%d")
            tasks[target_index]["due_date"] = new_due
        except ValueError:
            print("期限の形式が不正です。変更しませんでした。")
    
    write_tasks(tasks)
    print("タスクを編集しました。")

def delete_task_from_nlp(parsed_data: Dict) -> None:
    tasks = read_tasks()
    if not tasks:
        print("タスクがありません。")
        return
    
    task_index = parsed_data.get("task_index")
    task_name = parsed_data.get("task_name", "")
    
    target_index = None
    
    if task_index and 1 <= task_index <= len(tasks):
        target_index = task_index - 1
    elif task_name:
        for i, task in enumerate(tasks):
            if task_name.lower() in task["task_name"].lower():
                target_index = i
                break
    
    if target_index is None:
        print("対象のタスクが見つかりませんでした。")
        return
    
    deleted_task = tasks.pop(target_index)
    write_tasks(tasks)
    print(f"タスク「{deleted_task['task_name']}」を削除しました。")

def complete_task_from_nlp(parsed_data: Dict) -> None:
    tasks = read_tasks()
    if not tasks:
        print("タスクがありません。")
        return
    
    task_index = parsed_data.get("task_index")
    task_name = parsed_data.get("task_name", "")
    
    target_index = None
    
    if task_index and 1 <= task_index <= len(tasks):
        target_index = task_index - 1
    elif task_name:
        for i, task in enumerate(tasks):
            if task_name.lower() in task["task_name"].lower() and task["status"] == "todo":
                target_index = i
                break
    
    if target_index is None:
        print("対象の未完了タスクが見つかりませんでした。")
        return
    
    tasks[target_index]["status"] = "done"
    write_tasks(tasks)
    print(f"タスク「{tasks[target_index]['task_name']}」を完了しました。")

# メニュー画面
def show_menu() -> None:
    print("\n" + "="*40)
    print("         CLI TODO管理アプリ")
    print("="*40)
    print("1. タスク追加")
    print("2. タスク確認")
    print("3. タスク完了")
    print("4. 自然言語モード")
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