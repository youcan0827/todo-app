# Googleカレンダー連携セットアップガイド

## 概要

このガイドではタスク管理CLIアプリにGoogleカレンダー連携機能を追加するための設定手順を説明します。

## 新機能

### 1. インテリジェント・タスク追加
- 自然言語入力から日時情報を自動抽出
- 日時情報がある場合は自動でGoogleカレンダーにイベントを作成
- 例: 「金曜日の15時から会議」→ 自動的にカレンダーイベントを作成

### 2. 高機能自然言語モード（AIエージェント）
- LangChainエージェントが質問に応じてカレンダー検索やタスク参照を自律実行
- 例: 「今週の予定と未完了タスクを教えて」→ 複数のツールを組み合わせて回答

## 必要な準備

### 1. Google Cloud Projectの設定

#### ステップ1: Google Cloud Consoleでプロジェクトを作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成または既存プロジェクトを選択
3. プロジェクトIDをメモしておく

#### ステップ2: Google Calendar APIの有効化
1. 左側メニューから「APIとサービス」→「ライブラリ」を選択
2. 「Google Calendar API」を検索
3. 「有効にする」をクリック

#### ステップ3: 認証情報の作成
1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth 2.0 クライアントID」を選択
3. 初回の場合は「OAuth同意画面を設定」が必要
   - ユーザータイプ: 外部
   - アプリ名: 任意（例: タスク管理CLI）
   - ユーザーサポートメール: あなたのGmailアドレス
   - 開発者の連絡先情報: あなたのGmailアドレス
4. 「OAuth 2.0 クライアントID」作成画面で：
   - アプリケーションの種類: デスクトップアプリケーション
   - 名前: 任意（例: タスク管理CLIクライアント）
5. 作成後、JSONファイルをダウンロード

### 2. 認証情報ファイルの設置

#### ダウンロードしたJSONファイルを設置
```bash
# ダウンロードしたファイル名を変更してプロジェクトディレクトリに配置
cp ~/Downloads/client_secret_xxxxx.json /Users/yoshinomukanou/todo_app/credentials.json
```

### 3. 環境変数の設定

#### .envファイルの作成
```bash
cd /Users/yoshinomukanou/todo_app
touch .env
```

#### 環境変数の設定（.envファイルに追記）
```env
# OpenRouter API（既存）
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Google Calendar API設定（オプション）
GOOGLE_CALENDAR_ID=primary
```

### 4. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 初回認証

### 1. アプリケーションの実行
```bash
python main.py
```

### 2. Googleカレンダー認証
- インテリジェント・タスク追加（メニュー5）または高機能自然言語モード（メニュー6）を初回実行時
- Webブラウザが自動で開きます
- Googleアカウントでログイン
- アプリケーションのカレンダーアクセスを許可
- 認証完了後、`token.pickle`ファイルが自動作成されます

## 使用方法

### インテリジェント・タスク追加
```
メニューで「5」を選択
例: 「明日の14時から企画会議」
→ 自動的にタスク追加 + Googleカレンダーイベント作成
```

### 高機能自然言語モード
```
メニューで「6」を選択
例: 「今週の予定と未完了のタスクを教えて」
→ AIエージェントが自律的に情報を収集・統合して回答
```

## データ構造の変更点

### CSVファイル構造
```csv
task_name,due_date,status,created_at,calendar_event_id
田中さんと打ち合わせ,2025-12-20,todo,2025-12-14 10:30:15,abc123xyz
```

- `calendar_event_id`: GoogleカレンダーのイベントIDが格納されます

## トラブルシューティング

### 認証エラー
```
エラー: credentials.jsonが見つかりません
```
**解決策**: `credentials.json`ファイルがプロジェクトディレクトリに正しく配置されているか確認

### API制限エラー
```
HttpError 403: Rate Limit Exceeded
```
**解決策**: API使用量が上限に達しています。しばらく待ってから再試行

### 依存関係エラー
```
ModuleNotFoundError: No module named 'google'
```
**解決策**: 
```bash
pip install -r requirements.txt
```

### LangChainエラー
```
エラー: OPENROUTER_API_KEY環境変数が設定されていません
```
**解決策**: `.env`ファイルにOpenRouter APIキーが正しく設定されているか確認

## ファイル構成

```
todo_app/
├── main.py                    # メインアプリケーション（更新）
├── nlp_processor.py          # NLP処理（更新）
├── calendar_client.py        # Google Calendar APIクライアント（新規）
├── langchain_tools.py        # LangChainツール（新規）
├── advanced_nlp.py           # 高機能NLPエージェント（新規）
├── tasks.csv                 # タスクデータ（構造更新）
├── requirements.txt          # 依存関係（更新）
├── credentials.json          # Google認証情報（手動配置）
├── token.pickle              # 認証トークン（自動生成）
├── .env                      # 環境変数
└── SETUP_GUIDE.md           # このファイル
```

## セキュリティ注意事項

- `credentials.json`と`token.pickle`は機密情報です
- これらのファイルをGitリポジトリにコミットしないよう注意
- `.gitignore`に以下を追加することを推奨:
  ```
  credentials.json
  token.pickle
  .env
  ```

## サポート

問題が発生した場合は、エラーメッセージとともにアプリケーション開発者に連絡してください。