# Colabでの完全セットアップ手順（画像生成機能付き）

## 📋 前提条件

- Google Colabアカウント
- GPUランタイム（推奨）

## 🚀 完全なセットアップ手順

### ステップ1: リポジトリをクローン

```python
!git clone https://github.com/youcan0827/todo-app.git
%cd todo-app
```

### ステップ2: 依存関係のインストール（重要）

**⚠️ 画像生成機能を使用する場合、このステップは必須です**

```python
# 基本的な依存関係
!pip install -q langchain langchain-openai python-dotenv torch diffusers

# sdnqライブラリのインストール（画像生成に必須）
# このインストールには数分かかる場合があります
print("sdnqライブラリをインストール中...")
!pip install -q git+https://github.com/Disty0/sdnq

# インストール確認
import sys
try:
    import sdnq
    print("✅ sdnqのインストールに成功しました！")
except ImportError:
    print("❌ sdnqのインストールに失敗しました。")
    print("画像生成機能は使用できませんが、他の機能は動作します。")
    sys.exit(1)
```

### ステップ3: ランタイムを再起動

**重要**: インストール後、必ずランタイムを再起動してください
- メニューから: `ランタイム → ランタイムを再起動`

### ステップ4: 環境変数設定（オプション）

自然言語モードを使用する場合のみ：

```python
import os
os.environ['OPENROUTER_API_KEY'] = 'your_api_key_here'
```

### ステップ5: アプリケーション実行

```python
!python main.py
```

## 🔧 トラブルシューティング

### sdnqのインストールが失敗する場合

1. **GitHubリポジトリにアクセスできるか確認**
   ```python
   !curl -I https://github.com/Disty0/sdnq
   ```

2. **手動でインストールを試す**
   ```python
   !git clone https://github.com/Disty0/sdnq.git
   %cd sdnq
   !pip install -e .
   %cd ..
   ```

3. **diffusersを最新版に更新**
   ```python
   !pip install -U git+https://github.com/huggingface/diffusers
   ```

### sdnqがインストールできない場合の対処

画像生成機能は使用できませんが、他の機能（タスク追加、確認、完了、自然言語モード）は正常に動作します。

画像生成機能を無効化して実行する場合：

```python
# z_imageモジュールのインポートをスキップ
import sys
import main

# z_imageのインポートエラーを無視して実行
sys.modules['z_image'] = None

# main.pyを実行（画像生成部分でエラーが出ますが、他の機能は動作します）
exec(open('main.py').read())
```

## ⚠️ 重要な注意事項

1. **sdnqなしでは画像生成は不可能**: Z-Image-Turbo-SDNQモデルはsdnqに依存しています
2. **ランタイム再起動は必須**: インストール後は必ず再起動してください
3. **GPUランタイムを推奨**: 画像生成にはGPUがあると大幅に高速化されます

