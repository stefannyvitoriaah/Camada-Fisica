from src.bits import bytes_para_bits
from src.metodo1_batidas import bits_para_audio, audio_para_bits, bits_para_texto_batidas
from src.quadros import criar_quadros_metodo1

def test_metodo1_sintetico():
    bits = [bit for quadro in criar_quadros_metodo1(b"A") for bit in quadro]
    audio = bits_para_audio(bits)
    bits_recebidos, _ = audio_para_bits(audio)
    dados, valido = bits_para_texto_batidas(bits_recebidos)
    assert valido
    assert dados == b"A"

def test_receptor_tempo_real_reconhece_batidas():
    from src.receptor_tempo_real import ReceptorBatidas
    import numpy as np

    receptor = ReceptorBatidas()
    silencio = np.zeros(2048, dtype=np.float32)
    for bit in [0, 1, 0]:
        receptor.processar_bloco(silencio)
        bloco = np.zeros(2048, dtype=np.float32)
        bloco[100:180] = 0.8
        receptor.processar_bloco(bloco)
        receptor.processar_bloco(silencio)
        if bit == 1:
            bloco2 = np.zeros(2048, dtype=np.float32)
            bloco2[100:180] = 0.8
            receptor.processar_bloco(bloco2)
            receptor.processar_bloco(silencio)
    receptor.atualizar_tempo()
    assert receptor.bits