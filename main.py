#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI TODO管理アプリケーション
ターミナル上で動作するシンプルなタスク管理システム
"""

import csv
import os
import datetime
from typing import List, Dict, Optional


# CSVファイルのパス定義
CSV_FILE = "tasks.csv"
# CSVヘッダー定義
CSV_HEADERS = ["task_name", "due_date", "status", "created_at"]


def initialize_csv() -> None:
    """
    CSVファイルが存在しない場合、ヘッダー付きで新規作成する
    この関数はアプリ起動時に自動実行される
    """
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)


def read_tasks() -> List[Dict[str, str]]:
    """
    CSVファイルからタスクデータを読み込み、辞書形式のリストで返す
    ファイルが存在しない場合は空のリストを返す
    
    Returns:
        List[Dict]: タスク情報の辞書リスト
    """
    tasks = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tasks.append(row)
    except FileNotFoundError:
        # ファイルが存在しない場合は空リストを返す
        pass
    return tasks


def write_tasks(tasks: List[Dict[str, str]]) -> None:
    """
    タスクリストをCSVファイルに保存する
    既存のファイルは上書きされる
    
    Args:
        tasks: 保存するタスク情報の辞書リスト
    """
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(tasks)


def add_task() -> None:
    """
    新しいタスクを追加する機能
    ユーザーからタスク名と期限を入力受付し、CSVに保存する
    """
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
    tasks = read_tasks()
    tasks.append(new_task)
    write_tasks(tasks)
    
    print(f"タスク「{task_name}」が追加されました。")


def show_tasks() -> None:
    """
    すべてのタスクを一覧表示する機能
    タスクが存在しない場合は適切なメッセージを表示する
    """
    print("\n=== タスク一覧 ===")
    tasks = read_tasks()
    
    if not tasks:
        print("データがありません。")
        return
    
    # タスクを番号付きで表示
    for i, task in enumerate(tasks, 1):
        due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
        status_jp = "完了" if task["status"] == "done" else "未完了"
        print(f"[No.{i}] {task['task_name']}{due_info} - Status: {status_jp}")


def complete_task() -> None:
    """
    指定したタスクを完了状態にする機能
    タスク一覧を表示後、ユーザーに完了するタスク番号を選択させる
    """
    print("\n=== タスク完了 ===")
    tasks = read_tasks()
    
    if not tasks:
        print("データがありません。")
        return
    
    # 未完了タスクのみ表示
    incomplete_tasks = [task for task in tasks if task["status"] == "todo"]
    
    if not incomplete_tasks:
        print("完了可能なタスクがありません。")
        return
    
    print("未完了のタスク:")
    task_indices = []
    display_count = 1
    
    for i, task in enumerate(tasks):
        if task["status"] == "todo":
            due_info = f" (期限: {task['due_date']})" if task['due_date'] else ""
            print(f"[No.{display_count}] {task['task_name']}{due_info}")
            task_indices.append(i)
            display_count += 1
    
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


def show_menu() -> None:
    """
    メインメニューを表示する
    """
    print("\n" + "="*40)
    print("         CLI TODO管理アプリ")
    print("="*40)
    print("1. タスク追加")
    print("2. タスク確認")
    print("3. タスク完了")
    print("4. 終了")
    print("="*40)


def main() -> None:
    """
    アプリケーションのメイン処理
    ユーザーの選択に応じて各機能を呼び出すループ処理
    """
    # CSVファイル初期化
    initialize_csv()
    
    print("CLI TODO管理アプリへようこそ！")
    
    while True:
        show_menu()
        choice = input("選択してください (1-4): ").strip()
        
        if choice == "1":
            add_task()
        elif choice == "2":
            show_tasks()
        elif choice == "3":
            complete_task()
        elif choice == "4":
            print("アプリケーションを終了します。")
            break
        else:
            print("エラー: 1-4の数字を入力してください。")


if __name__ == "__main__":
    main()