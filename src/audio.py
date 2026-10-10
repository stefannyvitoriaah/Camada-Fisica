
from pathlib import Path
from typing import Callable
from math import gcd
from queue import Queue, Empty
from threading import Event, Thread

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.signal import resample_poly

from .configuracao import (
    BLOCO_AMOSTRAS,
    CANAIS,
    TAXA_AMOSTRAGEM,
)


# ==========================================
# DISPOSITIVOS
# ==========================================

def listar_entradas() -> list[tuple[int, str]]:
    return [
        (indice, info["name"])
        for indice, info in enumerate(sd.query_devices())
        if info["max_input_channels"] > 0
    ]


def mostrar_dispositivo_entrada(
    dispositivo: int | None = None
):
    info = sd.query_devices(dispositivo, "input")

    print("[AUDIO] Dispositivo:", info["name"])
    print(
        "[AUDIO] Canais disponíveis:",
        info["max_input_channels"]
    )

    return info


def _configuracao_entrada(dispositivo):
    info = mostrar_dispositivo_entrada(dispositivo)

    # A Mixagem estéreo Realtek foi identificada
    # anteriormente como dispositivo de 48 kHz.
    eh_mixagem = "mixagem estéreo" in info["name"].lower()

    taxa = 48000 if eh_mixagem else TAXA_AMOSTRAGEM

    # Usa dois canais quando disponíveis na Mixagem estéreo.
    canais = (
        2 if eh_mixagem and info["max_input_channels"] >= 2
        else 1
    )

    sd.check_input_settings(
        device=dispositivo,
        channels=canais,
        dtype="float32",
        samplerate=taxa
    )

    return taxa, canais


# ==========================================
# REPRODUÇÃO
# ==========================================

def reproduzir_audio(audio: np.ndarray) -> None:
    sinal = np.asarray(
        audio, dtype=np.float32
    ).reshape(-1)

    print(
        "[AUDIO] Reproduzindo",
        round(len(sinal) / TAXA_AMOSTRAGEM, 2),
        "segundos"
    )

    sd.play(sinal, TAXA_AMOSTRAGEM)
    sd.wait()

    print("[AUDIO] Reprodução concluída.")


# ==========================================
# SALVAR WAV
# ==========================================

def salvar_wav(
    caminho: str | Path,
    audio: np.ndarray
) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    sinal = np.asarray(audio, dtype=np.float32)

    audio_int16 = (
        np.clip(sinal, -1.0, 1.0) * 32767
    ).astype(np.int16)

    wavfile.write(
        caminho,
        TAXA_AMOSTRAGEM,
        audio_int16
    )


# ==========================================
# ABRIR WAV
# ==========================================

def abrir_wav(caminho: str | Path) -> np.ndarray:
    taxa, sinal = wavfile.read(caminho)

    if sinal.ndim > 1:
        sinal = sinal.mean(axis=1)

    if np.issubdtype(sinal.dtype, np.integer):
        limite = max(
            abs(np.iinfo(sinal.dtype).min),
            np.iinfo(sinal.dtype).max
        )
        sinal = sinal.astype(np.float32) / limite
    else:
        sinal = sinal.astype(np.float32)

    if taxa != TAXA_AMOSTRAGEM:
        divisor = gcd(taxa, TAXA_AMOSTRAGEM)
        sinal = resample_poly(
            sinal,
            TAXA_AMOSTRAGEM // divisor,
            taxa // divisor
        ).astype(np.float32)

    return np.asarray(sinal, dtype=np.float32)


# ==========================================
# RECEPÇÃO CONTÍNUA
# ==========================================

def iniciar_recepcao_continua(
    callback_bloco: Callable[[np.ndarray], None],
    dispositivo: int | None = None
):
    taxa_entrada, canais_entrada = (
        _configuracao_entrada(dispositivo)
    )

    fila_interna = Queue(maxsize=128)
    encerrar = Event()

    contador = 0
    descartados = 0

    def callback(indata, frames, tempo, status):
        nonlocal contador, descartados

        if status:
            print("[AUDIO] Aviso:", status)

        contador += 1

        if contador == 1:
            print(
                "[CAPTURA] Primeiro bloco recebido:",
                frames,
                "amostras"
            )

        try:
            # Converte estéreo para mono.
            if canais_entrada == 2:
                bloco = np.mean(
                    indata[:, :2],
                    axis=1,
                    dtype=np.float32
                )
            else:
                bloco = indata[:, 0].copy()

            # O callback só coloca o bloco na fila.
            # A reamostragem ocorre em outra thread.
            fila_interna.put_nowait(
                np.asarray(bloco, dtype=np.float32)
            )

        except Exception as erro:
            if isinstance(erro, __import__("queue").Full):
                descartados += 1
                if descartados == 1 or descartados % 100 == 0:
                    print(
                        "[AUDIO] Fila interna cheia.",
                        "Blocos descartados:",
                        descartados
                    )
            else:
                print(
                    "[AUDIO] Erro no callback:",
                    repr(erro)
                )

    def processar_audio():
        divisor = gcd(taxa_entrada, TAXA_AMOSTRAGEM)
        numerador = TAXA_AMOSTRAGEM // divisor
        denominador = taxa_entrada // divisor

        total = 0

        while not encerrar.is_set() or not fila_interna.empty():
            try:
                bloco = fila_interna.get(timeout=0.1)
            except Empty:
                continue

            try:
                if taxa_entrada != TAXA_AMOSTRAGEM:
                    bloco = resample_poly(
                        bloco,
                        numerador,
                        denominador
                    ).astype(np.float32)

                callback_bloco(bloco)

                total += 1

                if total == 1 or total % 100 == 0:
                    amplitude = (
                        float(np.max(np.abs(bloco)))
                        if bloco.size else 0.0
                    )

                    print(
                        f"[CAPTURA] {total} blocos "
                        f"| Amplitude: {amplitude:.5f}"
                    )

            except Exception as erro:
                print(
                    "[AUDIO] Erro no processamento:",
                    repr(erro)
                )

    trabalhador = Thread(
        target=processar_audio,
        daemon=True,
        name="ProcessadorAudioRX"
    )

    fluxo = sd.InputStream(
        samplerate=taxa_entrada,
        blocksize=0,
        channels=canais_entrada,
        dtype="float32",
        device=dispositivo,
        callback=callback
    )

    try:
        trabalhador.start()
        fluxo.start()
    except Exception:
        encerrar.set()
        fluxo.close()
        raise

    print(
        "[AUDIO] Captura iniciada:",
        f"{taxa_entrada} Hz,",
        f"{canais_entrada} canal(is)"
    )

    # Mantém referências necessárias ao processamento.
    fluxo._rx_encerrar = encerrar
    fluxo._rx_trabalhador = trabalhador

    return fluxo


# ==========================================
# GRAVAÇÃO POR DURAÇÃO
# ==========================================

def gravar_audio(
    duracao: float,
    dispositivo: int | None = None
) -> np.ndarray:
    taxa_entrada, canais_entrada = (
        _configuracao_entrada(dispositivo)
    )

    amostras = int(duracao * taxa_entrada)

    gravacao = sd.rec(
        amostras,
        samplerate=taxa_entrada,
        channels=canais_entrada,
        dtype="float32",
        device=dispositivo
    )

    sd.wait()

    if canais_entrada == 2:
        sinal = np.mean(
            gravacao,
            axis=1,
            dtype=np.float32
        )
    else:
        sinal = gravacao[:, 0].copy()

    if taxa_entrada != TAXA_AMOSTRAGEM:
        divisor = gcd(taxa_entrada, TAXA_AMOSTRAGEM)

        sinal = resample_poly(
            sinal,
            TAXA_AMOSTRAGEM // divisor,
            taxa_entrada // divisor
        )

    sinal = np.asarray(sinal, dtype=np.float32)

    print(
        "[AUDIO] Volume máximo capturado:",
        float(np.max(np.abs(sinal)))
        if sinal.size else 0.0
    )

    return sinal
