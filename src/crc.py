POLINOMIO_CRC8 = 0x07

def calcular_crc8(dados: bytes) -> int:
    crc = 0
    for byte in dados:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ POLINOMIO_CRC8) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

def adicionar_crc8(dados: bytes) -> bytes:
    return dados + bytes([calcular_crc8(dados)])

def validar_crc8(quadro: bytes) -> bool:
    if len(quadro) < 1:
        return False
    return calcular_crc8(quadro[:-1]) == quadro[-1]