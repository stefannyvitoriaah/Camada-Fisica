def texto_para_bytes(texto: str) -> bytes:
    return texto.encode("utf-8")

def bytes_para_texto(dados: bytes) -> str:
    return dados.decode("utf-8")

def byte_para_bits(valor: int) -> list[int]:
    if not 0 <= valor <= 255:
        raise ValueError("Um byte deve estar entre 0 e 255.")
    return [(valor >> deslocamento) & 1 for deslocamento in range(7, -1, -1)]

def bits_para_byte(bits: list[int]) -> int:
    if len(bits) != 8 or any(bit not in (0, 1) for bit in bits):
        raise ValueError("São necessários exatamente 8 bits válidos.")
    valor = 0
    for bit in bits:
        valor = (valor << 1) | bit
    return valor

def bytes_para_bits(dados: bytes) -> list[int]:
    resultado = []
    for byte in dados:
        resultado.extend(byte_para_bits(byte))
    return resultado

def bits_para_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("A quantidade de bits deve ser múltipla de 8.")
    return bytes(bits_para_byte(bits[i:i + 8]) for i in range(0, len(bits), 8))