from .metodo1_batidas import (
    DecodificadorBatidas,
    DetectorBatidas,
)
from .quadros import validar_quadros_metodo1


class ReceptorBatidas:

    def __init__(self):
        self.detector = DetectorBatidas()
        self.decodificador = DecodificadorBatidas()

        self.bits: list[int] = []
        self.batidas = 0
        self.ultimo_estado = "AGUARDANDO BATIDA"

    def _registrar_bits(self, novos):
        if not novos:
            return

        self.bits.extend(novos)
        self.batidas = 0

        if novos[-1] == 1:
            self.ultimo_estado = "BIT 1 — duas batidas"
        else:
            self.ultimo_estado = "BIT 0 — uma batida"

    def processar_bloco(self, bloco):
        resultado = self.detector.processar(bloco)
        novos = []

        for instante in self.detector.instantes_bloco:
            produzidos = self.decodificador.registrar_batida(
                instante
            )

            novos.extend(produzidos)
            self._registrar_bits(produzidos)

            if self.decodificador.primeira_batida is not None:
                self.batidas = 1
                self.ultimo_estado = (
                    "BATIDA 1 — aguardando segunda..."
                )

        produzidos = self.decodificador.atualizar(
            self.detector.tempo_total
        )

        novos.extend(produzidos)
        self._registrar_bits(produzidos)

        return resultado, novos

    def atualizar_tempo(self):
        novos = self.decodificador.atualizar(
            self.detector.tempo_total
        )

        self._registrar_bits(novos)

        return novos

    def validar_quadros_prontos(self):
        quantidade = len(self.bits) // 9

        if quantidade == 0:
            return b"", None

        quadros = [
            self.bits[i:i + 9]
            for i in range(0, quantidade * 9, 9)
        ]

        return validar_quadros_metodo1(quadros)

    def reiniciar(self):
        self.detector.reiniciar()
        self.decodificador.reiniciar()

        self.bits.clear()
        self.batidas = 0
        self.ultimo_estado = "AGUARDANDO BATIDA"