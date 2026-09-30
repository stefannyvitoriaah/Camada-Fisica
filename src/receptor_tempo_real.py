from .metodo1_batidas import DecodificadorBatidas, DetectorBatidas
from .quadros import validar_quadros_metodo1

class ReceptorBatidas:
    def __init__(self):
        self.detector = DetectorBatidas()
        self.decodificador = DecodificadorBatidas()
        self.bits: list[int] = []
        self.batidas = 0
        self.ultimo_estado = "AGUARDANDO BATIDA"

    def processar_bloco(self, bloco):
        resultado = self.detector.processar(bloco)
        instante = self.detector.tempo_total - len(bloco) / self.detector.taxa
        bits_novos = []
        if resultado.batida:
            self.batidas += 1
            bits_novos.extend(self.decodificador.registrar_batida(instante))
            if self.decodificador.primeira_batida is not None:
                self.ultimo_estado = "BATIDA 1 — aguardando segunda..."
            elif bits_novos and bits_novos[-1] == 1:
                self.ultimo_estado = "BIT 1 — duas batidas"
        else:
            bits_novos.extend(self.decodificador.atualizar(instante))
            if bits_novos and bits_novos[-1] == 0:
                self.ultimo_estado = "BIT 0 — uma batida"

        self.bits.extend(bits_novos)
        return resultado, bits_novos

    def atualizar_tempo(self):
        instante = self.detector.tempo_total
        bits_novos = self.decodificador.atualizar(instante)
        self.bits.extend(bits_novos)
        if bits_novos and bits_novos[-1] == 0:
            self.ultimo_estado = "BIT 0 — uma batida"
        return bits_novos

    def validar_quadros_prontos(self):
        quantidade = len(self.bits) // 9
        if quantidade == 0:
            return b"", None
        quadros = [self.bits[i:i + 9] for i in range(0, quantidade * 9, 9)]
        dados, valido = validar_quadros_metodo1(quadros)
        return dados, valido

    def reiniciar(self):
        self.detector.reiniciar()
        self.decodificador.reiniciar()
        self.bits.clear()
        self.batidas = 0
        self.ultimo_estado = "AGUARDANDO BATIDA"
