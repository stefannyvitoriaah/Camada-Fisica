import numpy as np

from .configuracao import AMPLITUDE_FSK, DURACAO_SIMBOLO_FSK, FREQUENCIAS_FSK, TAXA_AMOSTRAGEM
from .quadros import criar_quadro_metodo2, separar_quadro_metodo2

PREAMBULO = [0, 3, 0, 3, 0, 3, 0, 3]
MAPA_SIMBOLO = {(0, 0): 0, (0, 1): 1, (1, 0): 2, (1, 1): 3}

def _bits_para_simbolos(bits: list[int]) -> list[int]:
    if len(bits) % 2:
        bits = bits + [0]
    return [MAPA_SIMBOLO[(bits[i], bits[i + 1])] for i in range(0, len(bits), 2)]

def _simbolos_para_bits(simbolos: list[int]) -> list[int]:
    resultado = []
    for simbolo in simbolos:
        resultado.extend([(simbolo >> 1) & 1, simbolo & 1])
    return resultado

def bytes_para_audio(dados: bytes) -> tuple[np.ndarray, list[int]]:
    quadro = criar_quadro_metodo2(dados)
    bits = []
    for byte in quadro:
        bits.extend((byte >> deslocamento) & 1 for deslocamento in range(7, -1, -1))

    simbolos = PREAMBULO + _bits_para_simbolos(bits)
    quantidade = int(DURACAO_SIMBOLO_FSK * TAXA_AMOSTRAGEM)
    tempo = np.arange(quantidade, dtype=np.float32) / TAXA_AMOSTRAGEM
    janela = np.hanning(quantidade)
    partes = [np.zeros(int(0.20 * TAXA_AMOSTRAGEM), dtype=np.float32)]

    for simbolo in simbolos:
        frequencia = FREQUENCIAS_FSK[simbolo]
        partes.append((AMPLITUDE_FSK * np.sin(2 * np.pi * frequencia * tempo) * janela).astype(np.float32))

    partes.append(np.zeros(int(0.20 * TAXA_AMOSTRAGEM), dtype=np.float32))
    return np.concatenate(partes), simbolos

def _energia_frequencia(segmento: np.ndarray, frequencia: float) -> float:
    n = len(segmento)
    tempo = np.arange(n, dtype=np.float32) / TAXA_AMOSTRAGEM
    seno = np.sin(2 * np.pi * frequencia * tempo)
    cosseno = np.cos(2 * np.pi * frequencia * tempo)
    return float(np.mean(segmento * seno) ** 2 + np.mean(segmento * cosseno) ** 2)

def _classificar_segmento(segmento: np.ndarray) -> int:
    energias = [_energia_frequencia(segmento, frequencia) for frequencia in FREQUENCIAS_FSK]
    return int(np.argmax(energias))

def _extrair_simbolos(audio: np.ndarray, inicio: int) -> list[int]:
    tamanho = int(DURACAO_SIMBOLO_FSK * TAXA_AMOSTRAGEM)
    return [
        _classificar_segmento(audio[posicao:posicao + tamanho])
        for posicao in range(inicio, len(audio) - tamanho + 1, tamanho)
    ]

def detectar_inicio(audio: np.ndarray) -> int | None:
    tamanho = int(DURACAO_SIMBOLO_FSK * TAXA_AMOSTRAGEM)
    limite = min(len(audio) - tamanho * len(PREAMBULO), int(TAXA_AMOSTRAGEM * 1.5))
    passo = max(1, int(TAXA_AMOSTRAGEM * 0.01))
    melhor_inicio = None
    melhor_erros = len(PREAMBULO) + 1

    for inicio in range(0, max(0, limite), passo):
        simbolos = _extrair_simbolos(audio, inicio)[:len(PREAMBULO)]
        if len(simbolos) < len(PREAMBULO):
            continue
        erros = sum(a != b for a, b in zip(simbolos, PREAMBULO))
        if erros < melhor_erros:
            melhor_erros = erros
            melhor_inicio = inicio
    return melhor_inicio if melhor_inicio is not None and melhor_erros <= 1 else None

def audio_para_bytes(audio: np.ndarray) -> tuple[bytes, bool, list[int]]:
    inicio = detectar_inicio(audio)
    if inicio is None:
        return b"", False, []

    simbolos = _extrair_simbolos(audio, inicio)
    bits = _simbolos_para_bits(simbolos[len(PREAMBULO):])
    bytes_recebidos = []
    for i in range(0, len(bits) - 7, 8):
        bytes_recebidos.append(int("".join(map(str, bits[i:i + 8])), 2))
        if len(bytes_recebidos) >= 2 and len(bytes_recebidos) == bytes_recebidos[0] + 2:
            break
    dados, valido = separar_quadro_metodo2(bytes(bytes_recebidos))
    return dados, valido, simbolos