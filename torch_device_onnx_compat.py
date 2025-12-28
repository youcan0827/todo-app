# torch_device_onnx_compat.py
# torch_device_to_onnx_providers関数の互換性ライブラリ

def torch_device_to_onnx_providers(device):
    """
    PyTorchデバイスをONNX Runtime実行プロバイダーに変換する互換実装
    
    Args:
        device: PyTorchデバイス (torch.device, str)
        
    Returns:
        list: ONNX Runtime実行プロバイダーのリスト
    """
    try:
        import torch
    except ImportError:
        # torchが利用できない場合はCPUプロバイダーのみ
        return ["CPUExecutionProvider"]
    
    # デバイスの正規化
    if isinstance(device, str):
        device = torch.device(device)
    elif isinstance(device, torch.device):
        pass
    else:
        device = torch.device('cpu')
    
    # デバイスタイプに基づいてプロバイダーを選択
    if device.type == "cuda":
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif device.type == "mps":  # Apple Silicon
        return ["CPUExecutionProvider"]  # MPS未対応の場合
    else:
        return ["CPUExecutionProvider"]

# 互換性チェック関数
def check_torch_device_to_onnx_providers_availability():
    """torch_device_to_onnx_providers関数の利用可能性をチェック"""
    try:
        from style_bert_vits2.utils import torch_device_to_onnx_providers
        return True, torch_device_to_onnx_providers
    except ImportError:
        return False, torch_device_to_onnx_providers