import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class PathConfig:
    """パス設定クラス"""
    assets_root: Path
    
    def __post_init__(self):
        # assets_rootが文字列の場合はPathオブジェクトに変換
        if isinstance(self.assets_root, str):
            self.assets_root = Path(self.assets_root)

def get_path_config() -> PathConfig:
    """パス設定を取得する関数"""
    # 環境変数から取得、デフォルトは"model_assets"
    assets_root = os.getenv("MODEL_ASSETS_ROOT", "model_assets")
    
    # GoogleColab環境の場合の特別処理
    try:
        import google.colab
        # Colab環境では複数のパスを試行
        possible_paths = [
            "/content/drive/MyDrive/Style-Bert-VITS2/model_assets",
            "/content/drive/MyDrive/model_assets",
            "/content/model_assets",
            assets_root
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                assets_root = path
                print(f"✓ モデルアセットパスを設定: {assets_root}")
                break
        else:
            print(f"⚠️ モデルアセットパスが見つかりません。デフォルトを使用: {assets_root}")
            
    except ImportError:
        # Colab環境ではない場合はそのまま
        pass
    
    return PathConfig(assets_root=Path(assets_root))

@dataclass
class ServerConfig:
    """サーバー設定クラス"""
    language: str = "JP"
    model_dir: str = "model_assets"
    device: str = "auto"

@dataclass
class Config:
    """統合設定クラス"""
    assets_root: Path = Path("model_assets")
    server_config: ServerConfig = None
    
    def __post_init__(self):
        if self.server_config is None:
            self.server_config = ServerConfig()

def get_config() -> Config:
    """統合設定を取得する関数（model_load.py用）"""
    path_config = get_path_config()
    return Config(
        assets_root=path_config.assets_root,
        server_config=ServerConfig()
    )