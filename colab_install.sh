#!/bin/bash
# Colab用のセットアップスクリプト
# このスクリプトはColabのセルで実行できます: !bash colab_install.sh

echo "📦 依存関係をインストール中..."

# 基本的な依存関係
pip install -q langchain langchain-openai python-dotenv torch diffusers

# sdnqライブラリのインストール（画像生成に必須）
echo "📦 sdnqライブラリをインストール中（時間がかかる場合があります）..."
pip install -q git+https://github.com/Disty0/sdnq

# インストール確認
echo "🔍 インストール確認中..."
python -c "
try:
    import sdnq
    print('✅ sdnqのインストールに成功しました')
except ImportError:
    print('❌ sdnqのインストールに失敗しました')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ すべての依存関係のインストールが完了しました"
    echo "⚠️  ランタイムを再起動してください（ランタイム → ランタイムを再起動）"
else
    echo "❌ インストールにエラーが発生しました"
fi

