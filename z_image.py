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


def is_in_colab():
    """Google Colab環境かどうかを判定"""
    try:
        import google.colab
        return True
    except ImportError:
        return False


def generate_celebration_image(mood: str, save_file: bool = True, return_image: bool = False):
    """気分に基づいてお祝い画像を生成してColabで表示する
    
    Args:
        mood: ユーザーの気分（例: "嬉しい", "達成感", "リラックス"など）
        save_file: ファイルとして保存するかどうか（デフォルト: True）
        return_image: PIL画像オブジェクトを返すかどうか（デフォルト: False）
    
    Returns:
        PIL.Image.Image: return_imageがTrueの場合に画像オブジェクトを返す
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
    
    # ファイル保存オプション
    if save_file:
        filename = "output.png"
        image.save(filename)
        print(f"🎉 タスク完了！画像を '{filename}' に保存しました。")
        print(f"表示するには: from PIL import Image; img = Image.open('{filename}'); img")
    
    # 表示オプション（従来機能）
    if not save_file:
        print("🎉 タスク完了おめでとうございます！")
        
        if is_in_colab():
            # Colab環境では IPython.display を最優先で使用
            try:
                from IPython.display import display
                display(image)
            except Exception as e:
                print(f"IPython.displayでの表示に失敗: {e}")
                # フォールバック: matplotlib（フォント警告無効化）
                try:
                    import matplotlib.pyplot as plt
                    import matplotlib
                    matplotlib.pyplot.rcParams['font.family'] = 'DejaVu Sans'
                    import warnings
                    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
                    
                    plt.figure(figsize=(10, 10))
                    plt.imshow(image)
                    plt.axis('off')
                    plt.title(f"Generated Image: {mood}", fontsize=16)
                    plt.tight_layout()
                    plt.show()
                except Exception as e2:
                    print(f"matplotlib表示も失敗: {e2}")
                    image.show()
        else:
            # 非Colab環境
            try:
                # matplotlibを試す
                import matplotlib.pyplot as plt
                import warnings
                warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
                
                plt.figure(figsize=(10, 10))
                plt.imshow(image)
                plt.axis('off')
                plt.title(f"Generated Image: {mood}", fontsize=16)
                plt.tight_layout()
                plt.show()
            except ImportError:
                # 通常環境での表示
                print("💡 画像生成が完了しました。")
                image.show()
    
    # 画像オブジェクトを返すオプション
    if return_image:
        return image

