from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from .configuracao import BLOCO_AMOSTRAS, CANAIS, TAXA_AMOSTRAGEM

def listar_entradas() -> list[tuple[int, str]]:
    resultado = []
    for indice, dispositivo in enumerate(sd.query_devices()):
        if dispositivo["max_input_channels"] > 0:
            resultado.append((indice, dispositivo["name"]))
    return resultado

def reproduzir_audio(audio: np.ndarray) -> None:
    sd.play(np.asarray(audio, dtype=np.float32), TAXA_AMOSTRAGEM)
    sd.wait()

def salvar_wav(caminho: str | Path, audio: np.ndarray) -> None:
    caminho = Path(caminho)
    audio_int16 = np.clip(np.asarray(audio) * 32767, -32768, 32767).astype(np.int16)
    wavfile.write(caminho, TAXA_AMOSTRAGEM, audio_int16)

def abrir_wav(caminho: str | Path) -> np.ndarray:
    taxa, audio = wavfile.read(caminho)
    if taxa != TAXA_AMOSTRAGEM:
        raise ValueError(f"Taxa de amostragem incompatível: {taxa} Hz. Esperado: {TAXA_AMOSTRAGEM} Hz.")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if np.issubdtype(audio.dtype, np.integer):
        audio = audio.astype(np.float32) / np.iinfo(audio.dtype).max
    return np.asarray(audio, dtype=np.float32)

def iniciar_recepcao_continua(callback_bloco: Callable[[np.ndarray], None], dispositivo: int | None = None):
    def callback(indata, frames, tempo, status):
        if status:
            pass
        callback_bloco(indata[:, 0].copy())

    fluxo = sd.InputStream(
        samplerate=TAXA_AMOSTRAGEM,
        blocksize=BLOCO_AMOSTRAS,
        channels=CANAIS,
        dtype="float32",
        device=dispositivo,
        callback=callback,
    )
    fluxo.start()
    return fluxo

def gravar_audio(duracao: float, dispositivo: int | None = None) -> np.ndarray:
    amostras = int(duracao * TAXA_AMOSTRAGEM)
    audio = sd.rec(amostras, samplerate=TAXA_AMOSTRAGEM, channels=CANAIS, dtype="float32", device=dispositivo)
    sd.wait()
    return np.asarray(audio).reshape(-1)
