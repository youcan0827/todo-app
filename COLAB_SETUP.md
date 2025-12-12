# Google Colabでの実行方法

このプロジェクトをGoogle Colabで実行する手順です。

## 🚀 シンプルな実行手順（3ステップ）

### ステップ1: リポジトリをクローン

```python
!git clone https://github.com/youcan0827/todo-app.git
%cd todo-app
```

### ステップ2: 依存関係のインストール

```python
# 基本的な依存関係
!pip install -q langchain langchain-openai python-dotenv torch

# diffusersとsdnqを最新版でインストール（画像生成に必須）
!pip install -U git+https://github.com/huggingface/diffusers git+https://github.com/Disty0/sdnq
```

**注意**: 
- 複数のgitリポジトリを一度にインストールする場合は、スペースで区切ることができます
- このインストールには数分かかる場合があります

### ステップ3: アプリケーション実行

```python
!python main.py
```

**完了！** これでアプリが起動します。

---

## 📋 詳細なセットアップ手順

### 1. リポジトリをクローン

Colabの新しいノートブックで以下のセルを実行：

```python
!git clone https://github.com/youcan0827/todo-app.git
%cd todo-app
```

### 2. 依存関係のインストール

```python
# 基本的な依存関係
!pip install -q langchain langchain-openai python-dotenv torch

# diffusersとsdnqを最新版でインストール（画像生成に必須）
# ⚠️ 重要: このインストールには数分かかる場合があります
!pip install -U git+https://github.com/huggingface/diffusers git+https://github.com/Disty0/sdnq

# インストール確認（オプション）
try:
    import sdnq
    print("✅ sdnqのインストールに成功しました")
except ImportError:
    print("❌ sdnqのインストールに失敗しました。画像生成機能は使用できません。")
```

### 3. 環境変数の設定（オプション）

自然言語モード（機能4）を使用する場合は、OpenRouter APIキーが必要です：

```python
import os
os.environ['OPENROUTER_API_KEY'] = 'your_api_key_here'
```

### 4. アプリケーションの実行

```python
!python main.py
```

---

## ⚠️ 重要な注意事項

1. **GPUランタイムの使用推奨**: 画像生成機能（z-image）はGPUがあると高速に動作します。
   - ランタイム → ランタイムのタイプを変更 → GPU を選択

2. **初回実行時のモデルダウンロード**: z-imageのモデルは初回実行時に自動的にダウンロードされます（数GB）。時間がかかります。

3. **インタラクティブな入力**: Colabでは`input()`関数が正常に動作しますが、セルごとに実行されます。

4. **生成された画像**: 生成された画像は`celebration_*.png`として保存され、Colabのファイルパネルから確認・ダウンロードできます。

---

## 🔧 トラブルシューティング

### モデルのダウンロードが失敗する場合

```python
!pip install -U huggingface_hub
```

### GPUメモリ不足の場合

`z_image.py`の`device_map="cuda"`を`device_map="cpu"`に変更（処理が遅くなります）

### sdnqモジュールが見つからない場合

画像生成機能を使用する場合、`sdnq`ライブラリのインストールが必要です：

```python
# 再度インストールを試す
!pip install -U git+https://github.com/Disty0/sdnq

# 確認
import sdnq
print("✅ インストール成功")
```

もし`sdnq`のインストールに失敗する場合：
- 画像生成機能（タスク完了時の画像表示）は使用できません
- その他の機能（タスク追加、確認、完了、自然言語モード）は正常に動作します
- エラーが発生しても、アプリケーションは継続して動作します
