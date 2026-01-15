#!/usr/bin/env python3
import sys
import os
import csv
import datetime
from typing import List, Dict

if '.' in sys.path:
    sys.path.remove('.')
if '' in sys.path:
    sys.path.remove('')
system_lib_path = '/usr/local/lib/python3.12/dist-packages'
if system_lib_path not in sys.path:
    sys.path.insert(0, system_lib_path)
try:
    from integrated_langchain import integrated_langchain_mode as natural_language_mode_langchain
    LANGCHAIN_NLP_AVAILABLE = True
except ImportError:
    LANGCHAIN_NLP_AVAILABLE = False
    def natural_language_mode_langchain():
        print("LangChain依存関係が不足しています")

try:
    from rag_mode import rag_mode
except ImportError:
    def rag_mode():
        print("依存関係が不足しています")

CSV_FILE = "csv/tasks.csv"
CSV_HEADERS = ["task_name", "due_date", "status", "created_at", "calendar_event_id"]

def initialize_csv() -> None:
    os.makedirs("csv", exist_ok=True)
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

def read_tasks() -> List[Dict[str, str]]:
    tasks = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tasks.append(row)
    except FileNotFoundError:
        pass
    return tasks

def write_tasks(tasks: List[Dict[str, str]]) -> None:
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(tasks)

def add_task() -> None:
    print("\n=== タスク追加 ===")
    task_name = input("タスク名: ").strip()
    if not task_name:
        return
    due_date = input("期限 (YYYY-MM-DD): ").strip()
    if due_date:
        try:
            datetime.datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return
    new_task = {
        "task_name": task_name,
        "due_date": due_date,
        "status": "todo",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "calendar_event_id": ""
    }
    tasks = read_tasks()
    tasks.append(new_task)
    write_tasks(tasks)

def show_tasks() -> None:
    tasks = read_tasks()
    if not tasks:
        return
    for i, task in enumerate(tasks, 1):
        due_info = f" ({task['due_date']})" if task['due_date'] else ""
        status_jp = "完了" if task["status"] == "done" else "未完了"
        print(f"[{i}] {task['task_name']}{due_info} - {status_jp}")

def complete_task() -> None:
    tasks = read_tasks()
    if not tasks:
        return
    incomplete_tasks = [task for task in tasks if task["status"] == "todo"]
    if not incomplete_tasks:
        return
    task_indices = []
    display_count = 1
    for i, task in enumerate(tasks):
        if task["status"] == "todo":
            due_info = f" ({task['due_date']})" if task['due_date'] else ""
            print(f"[{display_count}] {task['task_name']}{due_info}")
            task_indices.append(i)
            display_count += 1
    try:
        choice = int(input("番号: "))
        if 1 <= choice <= len(task_indices):
            actual_index = task_indices[choice - 1]
            tasks[actual_index]["status"] = "done"
            write_tasks(tasks)
    except ValueError:
        pass

def natural_language_mode() -> None:
    if LANGCHAIN_NLP_AVAILABLE:
        natural_language_mode_langchain()
    else:
        print("LangChain利用不可")

# メニュー画面
def show_menu() -> None:
    print("\n1. タスク追加")
    print("2. タスク確認")
    print("3. タスク完了")
    print("4. AI自然言語")
    print("5. RAGモード")
    print("6. 終了")

# メニュー画面の選択に応じた挙動
def main() -> None:
    initialize_csv()
    while True:
        show_menu()
        choice = input("> ").strip()
        if choice == "1":
            add_task()
        elif choice == "2":
            show_tasks()
        elif choice == "3":
            complete_task()
        elif choice == "4":
            natural_language_mode()
        elif choice == "5":
            rag_mode()
        elif choice == "6":
            break

if __name__ == "__main__":
    main()