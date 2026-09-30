from dataclasses import dataclass
import numpy as np

from .configuracao import (
    AMPLITUDE_BATIDA,
    DURACAO_BATIDA,
    FATOR_LIMIAR_RUIDO,
    INTERVALO_DUAS_BATIDAS,
    INTERVALO_SEGUNDA_BATIDA,
    INTERVALO_SIMBOLOS_TRANSMISSAO,
    LIMIAR_ENERGIA_MINIMO,
    TAXA_AMOSTRAGEM,
    TEMPO_DECISAO_BIT,
    TEMPO_MINIMO_ENTRE_BATIDAS,
    TAMANHO_JANELA_ENERGIA,
)

def _criar_batida() -> np.ndarray:
    quantidade = int(DURACAO_BATIDA * TAXA_AMOSTRAGEM)
    tempo = np.arange(quantidade, dtype=np.float32) / TAXA_AMOSTRAGEM
    envelope = np.exp(-65.0 * tempo)
    corpo = (
        np.sin(2 * np.pi * 850 * tempo)
        + 0.55 * np.sin(2 * np.pi * 1700 * tempo)
        + 0.25 * np.sin(2 * np.pi * 3200 * tempo)
    )
    return (AMPLITUDE_BATIDA * envelope * corpo).astype(np.float32)

def bits_para_audio(bits: list[int]) -> np.ndarray:
    batida = _criar_batida()
    silencio_entre_bits = max(0.0, INTERVALO_SIMBOLOS_TRANSMISSAO - INTERVALO_SEGUNDA_BATIDA)
    partes: list[np.ndarray] = []

    for indice, bit in enumerate(bits):
        if bit not in (0, 1):
            raise ValueError("A sequência deve conter apenas 0 e 1.")

        partes.append(batida)
        if bit == 1:
            intervalo = np.zeros(int(INTERVALO_SEGUNDA_BATIDA * TAXA_AMOSTRAGEM), dtype=np.float32)
            partes.extend((intervalo, batida))

        if indice != len(bits) - 1:
            partes.append(np.zeros(int(silencio_entre_bits * TAXA_AMOSTRAGEM), dtype=np.float32))

    if not partes:
        return np.zeros(0, dtype=np.float32)
    partes.append(np.zeros(int(TEMPO_DECISAO_BIT * TAXA_AMOSTRAGEM), dtype=np.float32))
    return np.concatenate(partes)

@dataclass
class ResultadoDeteccao:
    batida: bool
    energia: float
    limiar: float

class DetectorBatidas:

    def __init__(self, taxa_amostragem: int = TAXA_AMOSTRAGEM):
        self.taxa = taxa_amostragem
        self.energia_ruido = LIMIAR_ENERGIA_MINIMO / FATOR_LIMIAR_RUIDO
        self.ultimo_tempo_batida = -999.0
        self.tempo_total = 0.0
        self.energia_anterior = 0.0

    def processar(self, bloco: np.ndarray) -> ResultadoDeteccao:
        audio = np.asarray(bloco, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return ResultadoDeteccao(False, 0.0, LIMIAR_ENERGIA_MINIMO)

        janela = min(TAMANHO_JANELA_ENERGIA, audio.size)
        energias = []
        for inicio in range(0, audio.size, janela):
            parte = audio[inicio:inicio + janela]
            if parte.size:
                energias.append(float(np.sqrt(np.mean(parte * parte))))

        energia = max(energias) if energias else 0.0
        self.energia_ruido = 0.97 * self.energia_ruido + 0.03 * min(energia, self.energia_ruido * 1.5 + LIMIAR_ENERGIA_MINIMO)
        limiar = max(LIMIAR_ENERGIA_MINIMO, self.energia_ruido * FATOR_LIMIAR_RUIDO)

        agora = self.tempo_total
        subiu = energia >= limiar and self.energia_anterior < limiar
        pode_detectar = agora - self.ultimo_tempo_batida >= TEMPO_MINIMO_ENTRE_BATIDAS
        detectou = subiu and pode_detectar

        if detectou:
            self.ultimo_tempo_batida = agora

        self.energia_anterior = energia
        self.tempo_total += audio.size / self.taxa
        return ResultadoDeteccao(detectou, energia, limiar)

    def reiniciar(self) -> None:
        self.energia_ruido = LIMIAR_ENERGIA_MINIMO / FATOR_LIMIAR_RUIDO
        self.ultimo_tempo_batida = -999.0
        self.tempo_total = 0.0
        self.energia_anterior = 0.0

class DecodificadorBatidas:
    def __init__(self):
        self.primeira_batida: float | None = None
        self.ultimo_tempo = 0.0
        self.bits: list[int] = []

    def registrar_batida(self, instante: float) -> list[int]:
        produzidos: list[int] = []
        self._fechar_pendente_se_necessario(instante, produzidos)
        if self.primeira_batida is None:
            self.primeira_batida = instante
        elif instante - self.primeira_batida <= INTERVALO_DUAS_BATIDAS:
            self.bits.append(1)
            produzidos.append(1)
            self.primeira_batida = None
        else:
            self.bits.append(0)
            produzidos.append(0)
            self.primeira_batida = instante

        self.ultimo_tempo = instante
        return produzidos

    def atualizar(self, instante: float) -> list[int]:
        produzidos: list[int] = []
        self._fechar_pendente_se_necessario(instante, produzidos)
        self.ultimo_tempo = instante
        return produzidos

    def _fechar_pendente_se_necessario(self, instante: float, produzidos: list[int]) -> None:
        if self.primeira_batida is not None and instante - self.primeira_batida >= TEMPO_DECISAO_BIT:
            self.bits.append(0)
            produzidos.append(0)
            self.primeira_batida = None

    def reiniciar(self) -> None:
        self.primeira_batida = None
        self.ultimo_tempo = 0.0
        self.bits.clear()

def detectar_batidas(audio: np.ndarray, taxa_amostragem: int = TAXA_AMOSTRAGEM) -> list[float]:
    detector = DetectorBatidas(taxa_amostragem)
    instantes: list[float] = []
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    for inicio in range(0, len(audio), 2048):
        bloco = audio[inicio:inicio + 2048]
        resultado = detector.processar(bloco)
        if resultado.batida:
            instantes.append(detector.tempo_total - len(bloco) / taxa_amostragem)
    return instantes

def batidas_para_bits(instantes: list[float]) -> list[int]:
    decodificador = DecodificadorBatidas()
    bits: list[int] = []
    for instante in instantes:
        bits.extend(decodificador.atualizar(instante))
        bits.extend(decodificador.registrar_batida(instante))
    if instantes:
        bits.extend(decodificador.atualizar(instantes[-1] + TEMPO_DECISAO_BIT + 0.01))
    return bits

def audio_para_bits(audio: np.ndarray) -> tuple[list[int], list[float]]:
    instantes = detectar_batidas(audio)
    return batidas_para_bits(instantes), instantes

def bits_para_texto_batidas(bits: list[int]) -> tuple[bytes, bool]:
    from .quadros import validar_quadros_metodo1
    if len(bits) % 9 != 0:
        return b"", False
    quadros = [bits[i:i + 9] for i in range(0, len(bits), 9)]
    return validar_quadros_metodo1(quadros)
