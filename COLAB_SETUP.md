# Google Colabでの実行方法

このプロジェクトをGoogle Colabで実行する手順です。

## セットアップ手順

### 1. リポジトリをクローン

Colabの新しいノートブックで以下のセルを実行：

```python
!git clone <your-repository-url>
%cd todo_app
```

### 2. 依存関係のインストール

```python
# 基本的な依存関係
!pip install -q langchain langchain-openai python-dotenv torch diffusers

# z-image用の依存関係（GitHubから直接インストール）
!pip install -q git+https://github.com/huggingface/diffusers git+https://github.com/Disty0/sdnq
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

または、Pythonから直接実行：

```python
import sys
sys.path.append('/content/todo_app')

exec(open('main.py').read())
```

## 注意事項

1. **GPUランタイムの使用推奨**: 画像生成機能（z-image）はGPUがあると高速に動作します。
   - ランタイム → ランタイムのタイプを変更 → GPU を選択

2. **初回実行時のモデルダウンロード**: z-imageのモデルは初回実行時に自動的にダウンロードされます（数GB）。時間がかかります。

3. **インタラクティブな入力**: Colabでは`input()`関数が正常に動作しますが、セルごとに実行されます。

4. **生成された画像**: 生成された画像は`celebration_*.png`として保存され、Colabのファイルパネルから確認・ダウンロードできます。

## トラブルシューティング

### モデルのダウンロードが失敗する場合

```python
!pip install -U huggingface_hub
```

### GPUメモリ不足の場合

`z-image.py`の`device_map="cuda"`を`device_map="cpu"`に変更（処理が遅くなります）

### モジュールが見つからないエラー

```python
import sys
sys.path.append('/content/todo_app')
```

を実行してから、再度`main.py`を実行してください。

