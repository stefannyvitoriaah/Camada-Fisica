import numpy as np
from scipy.signal import fftconvolve

from .configuracao import (
    AMPLITUDE_FSK, DURACAO_SIMBOLO_FSK,
    FREQUENCIAS_FSK, TAXA_AMOSTRAGEM,
)
from .quadros import criar_quadro_metodo2, separar_quadro_metodo2

PREAMBULO = [0, 3, 0, 3, 0, 3, 0, 3]
MAPA_SIMBOLO = {(0, 0): 0, (0, 1): 1, (1, 0): 2, (1, 1): 3}


def _bits_para_simbolos(bits):
    if len(bits) % 2:
        bits = bits + [0]
    return [MAPA_SIMBOLO[(bits[i], bits[i + 1])] for i in range(0, len(bits), 2)]


def _simbolos_para_bits(simbolos):
    resultado = []
    for simbolo in simbolos:
        resultado.extend([(simbolo >> 1) & 1, simbolo & 1])
    return resultado


def _tamanho_simbolo():
    return int(DURACAO_SIMBOLO_FSK * TAXA_AMOSTRAGEM)


def _onda_simbolo(simbolo):
    n = _tamanho_simbolo()
    t = np.arange(n, dtype=np.float64) / TAXA_AMOSTRAGEM
    return (AMPLITUDE_FSK * np.sin(2 * np.pi * FREQUENCIAS_FSK[simbolo] * t)
            * np.hanning(n)).astype(np.float32)


def bytes_para_audio(dados: bytes) -> tuple[np.ndarray, list[int]]:
    quadro = criar_quadro_metodo2(dados)
    bits = [((byte >> deslocamento) & 1)
            for byte in quadro for deslocamento in range(7, -1, -1)]
    simbolos = PREAMBULO + _bits_para_simbolos(bits)
    silencio = np.zeros(int(0.20 * TAXA_AMOSTRAGEM), dtype=np.float32)
    partes = [silencio] + [_onda_simbolo(s) for s in simbolos] + [silencio]
    return np.concatenate(partes), simbolos


def _classificar_segmento(segmento):
    n = len(segmento)
    if n != _tamanho_simbolo():
        raise ValueError('Segmento FSK incompleto')
    t = np.arange(n, dtype=np.float64) / TAXA_AMOSTRAGEM
    janela = np.hanning(n)
    ponderado = segmento * janela
    energias = [abs(np.dot(ponderado, np.exp(-2j * np.pi * f * t))) ** 2
                for f in FREQUENCIAS_FSK]
    return int(np.argmax(energias))


def _extrair_simbolos(audio, inicio):
    tamanho = _tamanho_simbolo()
    return [_classificar_segmento(audio[p:p + tamanho])
            for p in range(inicio, len(audio) - tamanho + 1, tamanho)]


def _candidatos_inicio(audio):
    """Busca o preâmbulo por correlação, com alinhamento em amostras."""
    referencia = np.concatenate([_onda_simbolo(s) for s in PREAMBULO])
    if len(audio) < len(referencia):
        return []
    correlacao = fftconvolve(audio, referencia[::-1], mode='valid')
    # Normalização para evitar falsos positivos em silêncio/ruído baixo.
    energia = fftconvolve(audio.astype(np.float64) ** 2,
                         np.ones(len(referencia), dtype=np.float64), mode='valid')
    energia_ref = float(np.dot(referencia, referencia))
    qualidade = np.abs(correlacao) / np.sqrt(np.maximum(energia * energia_ref, 1e-15))
    qualidade[energia < 0.001] = 0.0
    candidatos = []
    separacao = max(1, _tamanho_simbolo() // 2)
    for _ in range(12):
        indice = int(np.argmax(qualidade))
        if qualidade[indice] < 0.55:
            break
        candidatos.append(indice)
        qualidade[max(0, indice - separacao):indice + separacao + 1] = 0
    return sorted(candidatos)


def detectar_inicio(audio: np.ndarray) -> int | None:
    sinal = np.asarray(audio, dtype=np.float32).reshape(-1)
    for inicio in _candidatos_inicio(sinal):
        simbolos = _extrair_simbolos(sinal, inicio)[:len(PREAMBULO)]
        if simbolos == PREAMBULO:
            return inicio
    return None


def audio_para_bytes(audio: np.ndarray) -> tuple[bytes, bool, list[int]]:
    sinal = np.asarray(audio, dtype=np.float32).reshape(-1)
    inicio = detectar_inicio(sinal)
    if inicio is None:
        return b'', False, []
    simbolos = _extrair_simbolos(sinal, inicio)
    if simbolos[:len(PREAMBULO)] != PREAMBULO:
        return b'', False, simbolos
    bits = _simbolos_para_bits(simbolos[len(PREAMBULO):])
    if len(bits) < 8:
        return b'', False, simbolos
    tamanho_dados = int(''.join(map(str, bits[:8])), 2)
    total_bytes = tamanho_dados + 2
    if len(bits) < total_bytes * 8:
        return b'', False, simbolos
    quadro = bytes(int(''.join(map(str, bits[i:i + 8])), 2)
                   for i in range(0, total_bytes * 8, 8))
    dados, valido = separar_quadro_metodo2(quadro)
    return dados, bool(valido), simbolos
