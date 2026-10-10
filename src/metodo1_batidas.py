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


# ==========================================
# GERAÇÃO DAS BATIDAS
# ==========================================

def _criar_batida() -> np.ndarray:

    quantidade = int(
        DURACAO_BATIDA * TAXA_AMOSTRAGEM
    )

    tempo = (
        np.arange(
            quantidade,
            dtype=np.float32
        ) / TAXA_AMOSTRAGEM
    )

    envelope = np.exp(-65.0 * tempo)

    corpo = (
        np.sin(2 * np.pi * 850 * tempo)
        + 0.55 * np.sin(2 * np.pi * 1700 * tempo)
        + 0.25 * np.sin(2 * np.pi * 3200 * tempo)
    )

    sinal = AMPLITUDE_BATIDA * envelope * corpo

    pico = np.max(np.abs(sinal))

    if pico > 0:
        sinal = (
            sinal / pico * AMPLITUDE_BATIDA
        )

    return sinal.astype(np.float32)


# ==========================================
# CONVERSÃO DE BITS EM ÁUDIO
# ==========================================

def bits_para_audio(
    bits: list[int]
) -> np.ndarray:

    if not bits:
        return np.zeros(
            0,
            dtype=np.float32
        )

    batida = _criar_batida()

    duracao_total = (
        (len(bits) - 1)
        * INTERVALO_SIMBOLOS_TRANSMISSAO
        + INTERVALO_SEGUNDA_BATIDA
        + 2 * DURACAO_BATIDA
        + TEMPO_DECISAO_BIT
    )

    audio = np.zeros(
        int(
            np.ceil(
                duracao_total
                * TAXA_AMOSTRAGEM
            )
        ),
        dtype=np.float32
    )

    def inserir_batida(instante):

        inicio = int(
            round(
                instante * TAXA_AMOSTRAGEM
            )
        )

        fim = inicio + len(batida)

        audio[inicio:fim] += batida

    for indice, bit in enumerate(bits):

        if bit not in (0, 1):
            raise ValueError(
                "A sequência deve conter apenas 0 e 1."
            )

        inicio_simbolo = (
            indice
            * INTERVALO_SIMBOLOS_TRANSMISSAO
        )

        inserir_batida(
            inicio_simbolo
        )

        if bit == 1:

            inicio_segunda = (
                inicio_simbolo
                + DURACAO_BATIDA
                + INTERVALO_SEGUNDA_BATIDA
            )

            inserir_batida(
                inicio_segunda
            )

    return np.clip(
        audio,
        -1,
        1
    ).astype(np.float32)


# ==========================================
# RESULTADO DA DETECÇÃO
# ==========================================

@dataclass
class ResultadoDeteccao:

    batida: bool
    energia: float
    limiar: float


# ==========================================
# DETECTOR DE BATIDAS
# ==========================================

class DetectorBatidas:

    def __init__(
        self,
        taxa_amostragem: int = TAXA_AMOSTRAGEM
    ):

        self.taxa = taxa_amostragem

        self.reiniciar()

    def reiniciar(self):

        self.energia_ruido = (
            LIMIAR_ENERGIA_MINIMO
            / FATOR_LIMIAR_RUIDO
        )

        self.ultimo_tempo_batida = -999.0

        self.tempo_total = 0.0

        self.energia_anterior = 0.0

        self.ativo = False

        self.instantes_bloco = []

    def processar(
        self,
        bloco: np.ndarray
    ) -> ResultadoDeteccao:

        audio = np.asarray(
            bloco,
            dtype=np.float32
        ).reshape(-1)

        self.instantes_bloco = []

        if audio.size == 0:

            return ResultadoDeteccao(
                False,
                0.0,
                LIMIAR_ENERGIA_MINIMO
            )

        maior_energia = 0.0

        ultimo_limiar = (
            LIMIAR_ENERGIA_MINIMO
        )

        tamanho = max(
            32,
            TAMANHO_JANELA_ENERGIA
        )

        for inicio in range(
            0,
            len(audio),
            tamanho
        ):

            parte = audio[
                inicio:inicio + tamanho
            ]

            if not parte.size:
                continue

            energia = float(
                np.sqrt(
                    np.mean(
                        parte.astype(
                            np.float64
                        ) ** 2
                    )
                )
            )

            maior_energia = max(
                maior_energia,
                energia
            )

            limiar = max(
                LIMIAR_ENERGIA_MINIMO,
                self.energia_ruido
                * FATOR_LIMIAR_RUIDO
            )

            ultimo_limiar = limiar

            instante = (
                self.tempo_total
                + inicio / self.taxa
            )

            acima = (
                energia >= limiar
            )

            pode_detectar = (
                instante
                - self.ultimo_tempo_batida
                >= TEMPO_MINIMO_ENTRE_BATIDAS
            )

            # Identifica o início de um impacto
            if (
                acima
                and not self.ativo
                and pode_detectar
            ):

                self.instantes_bloco.append(
                    instante
                )

                self.ultimo_tempo_batida = (
                    instante
                )

            # Controle de estado do sinal
            if acima:

                self.ativo = True

            elif energia < limiar * 0.65:

                self.ativo = False

            # ==================================
            # FILTRO DE RUÍDO ATUALIZADO
            # ==================================
            # Adaptação mais lenta para não
            # elevar o limiar rapidamente.

            if not acima:

                self.energia_ruido = (
                    0.995
                    * self.energia_ruido
                    + 0.005
                    * energia
                )

        self.tempo_total += (
            len(audio) / self.taxa
        )

        return ResultadoDeteccao(
            bool(self.instantes_bloco),
            maior_energia,
            ultimo_limiar
        )


# ==========================================
# DECODIFICADOR DE BATIDAS
# ==========================================

class DecodificadorBatidas:

    def __init__(self):

        self.reiniciar()

    def reiniciar(self):

        self.primeira_batida = None

        self.ultimo_tempo = 0.0

        self.bits = []

    def registrar_batida(
        self,
        instante: float
    ) -> list[int]:

        produzidos = []

        if self.primeira_batida is not None:

            diferenca = (
                instante
                - self.primeira_batida
            )

            if (
                0 <= diferenca
                <= INTERVALO_DUAS_BATIDAS
            ):

                self.bits.append(1)

                produzidos.append(1)

                self.primeira_batida = None

            else:

                self.bits.append(0)

                produzidos.append(0)

                self.primeira_batida = instante

        else:

            self.primeira_batida = instante

        self.ultimo_tempo = instante

        return produzidos

    def atualizar(
        self,
        instante: float
    ) -> list[int]:

        produzidos = []

        if self.primeira_batida is not None:

            diferenca = (
                instante
                - self.primeira_batida
            )

            if diferenca >= TEMPO_DECISAO_BIT:

                self.bits.append(0)

                produzidos.append(0)

                self.primeira_batida = None

        self.ultimo_tempo = instante

        return produzidos


# ==========================================
# DETECTAR BATIDAS NO ÁUDIO
# ==========================================

def detectar_batidas(
    audio: np.ndarray,
    taxa_amostragem: int = TAXA_AMOSTRAGEM
) -> list[float]:

    detector = DetectorBatidas(
        taxa_amostragem
    )

    instantes = []

    audio = np.asarray(
        audio,
        dtype=np.float32
    ).reshape(-1)

    for inicio in range(
        0,
        len(audio),
        2048
    ):

        bloco = audio[
            inicio:inicio + 2048
        ]

        detector.processar(bloco)

        instantes.extend(
            detector.instantes_bloco
        )

    return instantes


# ==========================================
# CONVERTER BATIDAS EM BITS
# ==========================================

def batidas_para_bits(
    instantes: list[float]
) -> list[int]:

    decodificador = (
        DecodificadorBatidas()
    )

    bits = []

    for instante in instantes:

        bits.extend(
            decodificador.registrar_batida(
                instante
            )
        )

    if instantes:

        bits.extend(
            decodificador.atualizar(
                instantes[-1]
                + TEMPO_DECISAO_BIT
                + 0.01
            )
        )

    return bits


# ==========================================
# CONVERTER ÁUDIO EM BITS
# ==========================================

def audio_para_bits(
    audio: np.ndarray
) -> tuple[list[int], list[float]]:

    instantes = detectar_batidas(
        audio
    )

    bits = batidas_para_bits(
        instantes
    )

    return bits, instantes


# ==========================================
# VALIDAR QUADROS DO MÉTODO 1
# ==========================================

def bits_para_texto_batidas(
    bits: list[int]
) -> tuple[bytes, bool]:

    from .quadros import (
        validar_quadros_metodo1
    )

    if len(bits) % 9 != 0:

        return b"", False

    quadros = [
        bits[i:i + 9]
        for i in range(
            0,
            len(bits),
            9
        )
    ]

    return validar_quadros_metodo1(
        quadros
    )