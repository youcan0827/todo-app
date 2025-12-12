# -*- coding: utf-8 -*-
"""Z-Image画像生成モジュール

気分に基づいてお祝い画像を生成します。
"""

import datetime
import torch
import diffusers

# sdnqのインポート（オプショナル）
try:
    from sdnq import SDNQConfig  # import sdnq to register it into diffusers and transformers
    from sdnq.loader import apply_sdnq_options_to_model
    SDNQ_AVAILABLE = True
except ImportError:
    print("警告: sdnqライブラリが見つかりません。画像生成機能を使用するには以下をインストールしてください:")
    print("  !pip install git+https://github.com/Disty0/sdnq")
    SDNQ_AVAILABLE = False
    # ダミー関数を定義
    def apply_sdnq_options_to_model(model, use_quantized_matmul=True):
        return model

# モデルは初回のみ読み込む（グローバル変数として保持）
_pipe = None


def initialize_z_image_model():
    """画像生成モデルを初期化する（初回のみ実行）"""
    global _pipe
    if _pipe is None:
        # 既存のglobal pipeがあるかチェック（Colabで事前作成された場合）
        import sys
        if 'pipe' in globals() or hasattr(sys.modules.get('__main__', {}), 'pipe'):
            try:
                # グローバルスコープのpipeを使用
                import __main__
                if hasattr(__main__, 'pipe'):
                    _pipe = __main__.pipe
                    print("既存のpipeを再利用します。")
                    return _pipe
            except:
                pass
        if not SDNQ_AVAILABLE:
            error_msg = (
                "❌ sdnqライブラリがインストールされていません。\n"
                "画像生成機能を使用するには、以下のコマンドでsdnqをインストールしてください:\n"
                "  !pip install git+https://github.com/Disty0/sdnq\n\n"
                "Colabで実行する場合:\n"
                "  1. 新しいセルを作成\n"
                "  2. !pip install git+https://github.com/Disty0/sdnq を実行\n"
                "  3. ランタイムを再起動（ランタイム → ランタイムを再起動）\n"
                "  4. 再度 main.py を実行"
            )
            raise ImportError(error_msg)
        
        print("画像生成モデルを読み込んでいます...")
        try:
            _pipe = diffusers.ZImagePipeline.from_pretrained(
                "Disty0/Z-Image-Turbo-SDNQ-uint4-svd-r32",
                torch_dtype=torch.float32,
                device_map="cuda"
            )
            if SDNQ_AVAILABLE:
                _pipe.transformer = apply_sdnq_options_to_model(_pipe.transformer, use_quantized_matmul=True)
                _pipe.text_encoder = apply_sdnq_options_to_model(_pipe.text_encoder, use_quantized_matmul=True)
            print("モデルの読み込みが完了しました。")
        except Exception as e:
            print(f"モデルの読み込みエラー: {e}")
            print("CPUモードで再試行します...")
            try:
                _pipe = diffusers.ZImagePipeline.from_pretrained(
                    "Disty0/Z-Image-Turbo-SDNQ-uint4-svd-r32",
                    torch_dtype=torch.float32,
                    device_map="cpu"
                )
                if SDNQ_AVAILABLE:
                    _pipe.transformer = apply_sdnq_options_to_model(_pipe.transformer, use_quantized_matmul=True)
                    _pipe.text_encoder = apply_sdnq_options_to_model(_pipe.text_encoder, use_quantized_matmul=True)
                print("モデルの読み込みが完了しました（CPUモード）。")
            except Exception as e2:
                print(f"モデルの読み込みに失敗しました: {e2}")
                raise
    return _pipe


def generate_celebration_image(mood: str) -> None:
    """気分に基づいてお祝い画像を生成・表示する
    
    Args:
        mood: ユーザーの気分（例: "嬉しい", "達成感", "リラックス"など）
    """
    try:
        pipe = initialize_z_image_model()
        
        # 気分に基づいたプロンプトを生成
        prompt = f"{mood}な気分の画像、マスコットキャラのイラスト"
        
        print("画像を生成しています...")
        image = pipe(
            prompt=prompt,
            height=1024,
            width=1024,
            num_inference_steps=9,
            guidance_scale=0.0,
            generator=torch.manual_seed(42),
        ).images[0]
        
        # 画像を保存
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = f"celebration_{timestamp}.png"
        image.save(image_path)
        print(f"画像を保存しました: {image_path}")
        
        # 画像を表示（Colab環境と通常環境で異なる処理）
        try:
            # Colab環境かどうかをチェック
            try:
                from IPython.display import display
                import IPython
                if IPython.get_ipython() is not None:
                    # ColabまたはJupyter環境
                    display(image)
                    return
            except:
                pass
            
            # 通常のPython環境
            image.show()
        except Exception as e:
            print(f"画像を表示できませんでした: {e}")
            print("保存されたファイルを確認してください。")
            
    except Exception as e:
        print(f"画像生成エラー: {e}")
        print("画像生成をスキップします。")

