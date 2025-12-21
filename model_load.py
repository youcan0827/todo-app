# model_load.py
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import torch
from scipy.io import wavfile

from config import get_config
from style_bert_vits2.constants import (
    DEFAULT_ASSIST_TEXT_WEIGHT,
    DEFAULT_LENGTH,
    DEFAULT_LINE_SPLIT,
    DEFAULT_NOISE,
    DEFAULT_NOISEW,
    DEFAULT_SDP_RATIO,
    DEFAULT_SPLIT_INTERVAL,
    DEFAULT_STYLE,
    DEFAULT_STYLE_WEIGHT,
    Languages,
)
from style_bert_vits2.logging import logger
from style_bert_vits2.nlp import bert_models, onnx_bert_models
from style_bert_vits2.nlp.japanese import pyopenjtalk_worker as pyopenjtalk
from style_bert_vits2.nlp.japanese.user_dict import update_dict
from style_bert_vits2.tts_model import TTSModel, TTSModelHolder
from style_bert_vits2.utils import torch_device_to_onnx_providers


# ----------------------------
# プロセス内キャッシュ/初期化フラグ
# ----------------------------
_init_lock = threading.Lock()
_pyopenjtalk_ready = False

# BERTは「デバイスごと」にロード済み判定しておく(同一プロセスでcpu→cudaを切り替えるケースに備える)
_bert_ready: Dict[Tuple[str, bool], bool] = {}  # (device, onnx) -> loaded?

# model_dir+deviceのTTSModelHolderキャッシュ
_holder_cache: Dict[Tuple[str, str], TTSModelHolder] = {}

# (model_dir, device, model_name) -> LoadedModelキャッシュ
_model_cache: Dict[Tuple[str, str, str], "LoadedModel"] = {}

# ロード競合防止(多スレッド環境向けに最低限)
_model_cache_lock = threading.Lock()


def _resolve_device(device: Optional[str] = None, cpu: bool = False) -> str:
    if device is not None:
        return device
    if cpu:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def _init_pyopenjtalk_once() -> None:
    global _pyopenjtalk_ready
    if _pyopenjtalk_ready:
        return
    # pyopenjtalk_workerはTCPソケットサーバーなのでプロセス内で一度だけ起動
    pyopenjtalk.initialize_worker()
    update_dict()
    _pyopenjtalk_ready = True


def _init_bert_once(device: str, preload_onnx_bert: bool) -> None:
    """
    server_fastapi.pyと同じ思想:
    - 既定は日本語BERTのみ事前ロード
    - ONNX版は必要ならロード
    """
    key_pt = (device, False)
    if not _bert_ready.get(key_pt, False):
        bert_models.load_model(Languages.JP, device_map=device)
        bert_models.load_tokenizer(Languages.JP)
        _bert_ready[key_pt] = True

    if preload_onnx_bert:
        key_onnx = (device, True)
        if not _bert_ready.get(key_onnx, False):
            onnx_bert_models.load_model(
                Languages.JP,
                onnx_providers=torch_device_to_onnx_providers(device),
            )
            onnx_bert_models.load_tokenizer(Languages.JP)
            _bert_ready[key_onnx] = True


def _get_holder(model_dir: Union[str, Path], device: str) -> TTSModelHolder:
    md = str(Path(model_dir))
    k = (md, device)
    holder = _holder_cache.get(k)
    if holder is not None:
        return holder

    holder = TTSModelHolder(
        Path(model_dir),
        device,
        torch_device_to_onnx_providers(device),
    )
    if len(holder.model_names) == 0:
        raise RuntimeError(f"Models not found in {model_dir}")
    _holder_cache[k] = holder
    return holder


def list_models(model_dir: Union[str, Path], device: Optional[str] = None, cpu: bool = False) -> list[str]:
    device = _resolve_device(device, cpu=cpu)
    holder = _get_holder(model_dir, device)
    return list(holder.model_names)


@dataclass(frozen=True)
class ModelInfo:
    model_name: str
    model_id: int
    model_path: Path
    config_path: Path
    style_vec_path: Path


class LoadedModel:
    """
    sample_modelとして保持して、sample_model.inference(...)で使う想定の薄いラッパー。
    """

    def __init__(self, *, tts_model: TTSModel, info: ModelInfo):
        self._model = tts_model
        self.info = info

        # 推論中の競合を避けたい場合に使う(アプリ側が単一スレッドなら不要)
        self._infer_lock = threading.Lock()

        # 明示ロード(モデルによってはinfer内でlazy loadすることもあるが、ここで統一して先にロード)
        if hasattr(self._model, "load") and callable(getattr(self._model, "load")):
            logger.info(f"Loading weights:{info.model_name}")
            self._model.load()

    @property
    def spk2id(self):
        return self._model.spk2id

    @property
    def id2spk(self):
        return self._model.id2spk

    @property
    def style2id(self):
        return self._model.style2id

    def inference(
        self,
        text: str,
        output_path: Union[str, Path],
        *,
        speaker_name: Optional[str] = None,
        speaker_id: Optional[int] = None,
        language: Union[Languages, str, None] = None,
        sdp_ratio: float = DEFAULT_SDP_RATIO,
        noise: float = DEFAULT_NOISE,
        noise_w: float = DEFAULT_NOISEW,
        length: float = DEFAULT_LENGTH,
        line_split: bool = DEFAULT_LINE_SPLIT,
        split_interval: float = DEFAULT_SPLIT_INTERVAL,
        assist_text: Optional[str] = None,
        assist_text_weight: float = DEFAULT_ASSIST_TEXT_WEIGHT,
        style: Optional[str] = DEFAULT_STYLE,
        style_weight: float = DEFAULT_STYLE_WEIGHT,
        reference_audio_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        推論してoutput_pathにwav保存。保存先Pathを返す。
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            raise ValueError("text is empty")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() != ".wav":
            # 事故りやすいので強制はしないが警告
            logger.warning(f"output_path is not .wav:{out}")

        if language is None:
            config = get_config()
            language = config.server_config.language
        if isinstance(language, str):
            s = language.strip()
            if s.startswith("Languages."):
                s = s.split(".", 1)[1]
            language = Languages[s.upper()]

        # 話者解決(server_fastapi.pyの挙動に合わせる)
        if speaker_name is not None:
            if speaker_name not in self._model.spk2id:
                raise ValueError(f"speaker_name={speaker_name} not found")
            sid = self._model.spk2id[speaker_name]
        else:
            if speaker_id is None:
                sid = 0 if 0 in self._model.id2spk else next(iter(self._model.id2spk.keys()))
            else:
                if speaker_id not in self._model.id2spk:
                    raise ValueError(f"speaker_id={speaker_id} not found")
                sid = speaker_id

        # スタイル解決(server_fastapi.pyは存在しない場合エラーなので踏襲)
        if style is None:
            style = DEFAULT_STYLE
        if style not in self._model.style2id:
            raise ValueError(f"style={style} not found. available={list(self._model.style2id.keys())}")

        ref = str(reference_audio_path) if reference_audio_path is not None else None

        # 多スレッドで呼ばれる可能性があるならロック(必要なければ外してOK)
        with self._infer_lock:
            sr, audio = self._model.infer(
                text=text,
                language=language,
                speaker_id=sid,
                reference_audio_path=ref,
                sdp_ratio=sdp_ratio,
                noise=noise,
                noise_w=noise_w,
                length=length,
                line_split=line_split,
                split_interval=split_interval,
                assist_text=assist_text,
                assist_text_weight=assist_text_weight,
                use_assist_text=bool(assist_text),
                style=style,
                style_weight=style_weight,
            )

        wavfile.write(str(out), sr, audio)
        return out


def load_model(
    model_name: str,
    *,
    model_dir: Union[str, Path, None] = None,
    device: Optional[str] = None,
    cpu: bool = False,
    preload_onnx_bert: bool = False,
    force_reload: bool = False,
) -> LoadedModel:
    """
    モデル名を指定してロード済みモデル(LoadedModel)を返す。
    同一プロセス内ではキャッシュされ、同じ(model_dir,device,model_name)なら同一インスタンスを返す。

    例:
      sample_model=load_model("my_model",model_dir="/content/model_assets")
      sample_model.inference("aaa","/content/out.wav")
    """
    config = get_config()
    if model_dir is None:
        model_dir = config.assets_root

    device = _resolve_device(device, cpu=cpu)
    md = str(Path(model_dir))
    cache_key = (md, device, model_name)

    with _model_cache_lock:
        if (not force_reload) and cache_key in _model_cache:
            return _model_cache[cache_key]

        # 初期化は最初の1回だけ
        with _init_lock:
            _init_pyopenjtalk_once()
            _init_bert_once(device, preload_onnx_bert)

        holder = _get_holder(model_dir, device)

        # holder.models_info.nameがディレクトリ名(=server_fastapi.pyのmodel_name)想定
        model_ids = [i for i, x in enumerate(holder.models_info) if x.name == model_name]
        if not model_ids:
            raise ValueError(f"model_name={model_name} not found. available={list(holder.model_names)}")
        if len(model_ids) > 1:
            raise ValueError(f"model_name={model_name} is ambiguous")

        model_id = model_ids[0]
        # model_files_dictのkey順とmodels_infoの順が一致する保証が薄いので、models_infoから逆引きせず
        # server_fastapi.pyと同じ流れで「model_name→パス」を取る
        if model_name not in holder.model_files_dict:
            # 念のためフォールバック(ただし通常はここに来ない想定)
            raise RuntimeError(f"Internal mismatch:model_name={model_name} not in model_files_dict")

        model_paths = holder.model_files_dict[model_name]
        model_path = model_paths[0]
        config_path = holder.root_dir / model_name / "config.json"
        style_vec_path = holder.root_dir / model_name / "style_vectors.npy"

        tts_model = TTSModel(
            model_path=model_path,
            config_path=config_path,
            style_vec_path=style_vec_path,
            device=holder.device,
        )

        loaded = LoadedModel(
            tts_model=tts_model,
            info=ModelInfo(
                model_name=model_name,
                model_id=model_id,
                model_path=Path(model_path),
                config_path=Path(config_path),
                style_vec_path=Path(style_vec_path),
            ),
        )

        _model_cache[cache_key] = loaded
        return loaded