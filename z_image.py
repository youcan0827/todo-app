# -*- coding: utf-8 -*-
"""Z-Image画像生成モジュール

気分に基づいてお祝い画像を生成してColabで表示します。
"""

import torch
import diffusers
from sdnq import SDNQConfig  # import sdnq to register it into diffusers and transformers
from sdnq.loader import apply_sdnq_options_to_model

# モデルは初回のみ読み込む（グローバル変数として保持）
_pipe = None


def initialize_z_image_model():
    """画像生成モデルを初期化する（初回のみ実行）"""
    global _pipe
    if _pipe is None:
        # 既存のglobal pipeがあるかチェック（Colabで事前作成された場合）
        import __main__
        if hasattr(__main__, 'pipe'):
            _pipe = __main__.pipe
            print("既存のpipeを再利用します。")
            return _pipe
        
        print("画像生成モデルを読み込んでいます...")
        _pipe = diffusers.ZImagePipeline.from_pretrained(
            "Disty0/Z-Image-Turbo-SDNQ-uint4-svd-r32",
            torch_dtype=torch.float32,
            device_map="cuda"
        )
        _pipe.transformer = apply_sdnq_options_to_model(_pipe.transformer, use_quantized_matmul=True)
        _pipe.text_encoder = apply_sdnq_options_to_model(_pipe.text_encoder, use_quantized_matmul=True)
        print("モデルの読み込みが完了しました。")
    return _pipe


def generate_celebration_image(mood: str) -> None:
    """気分に基づいてお祝い画像を生成してColabで表示する
    
    Args:
        mood: ユーザーの気分（例: "嬉しい", "達成感", "リラックス"など）
    """
    pipe = initialize_z_image_model()
    
    # 気分に基づいたプロンプトを生成
    prompt = f"{mood}な気分の画像、マスコットキャラのイラスト"
    
    print("🎨 画像を生成しています...")
    image = pipe(
        prompt=prompt,
        height=1024,
        width=1024,
        num_inference_steps=9,
        guidance_scale=0.0,
        generator=torch.manual_seed(42),
    ).images[0]
    
    # Colabで画像を直接表示
    try:
        from IPython.display import display
        print("🎉 タスク完了おめでとうございます！")
        display(image)
    except ImportError:
        # IPythonが利用できない場合（通常のPython環境）
        print("🎉 タスク完了おめでとうございます！")
        print("💡 画像生成が完了しましたが、表示機能はColab専用です。")
        image.show()  # 通常環境での表示を試行

