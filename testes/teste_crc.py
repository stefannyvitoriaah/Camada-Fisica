from src.crc import adicionar_crc8, validar_crc8

def test_crc():
    quadro = adicionar_crc8(b"teste")
    assert validar_crc8(quadro)
    corrompido = bytearray(quadro)
    corrompido[0] ^= 1
    assert not validar_crc8(bytes(corrompido))