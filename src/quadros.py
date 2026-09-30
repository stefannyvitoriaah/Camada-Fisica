from .bits import bytes_para_bits, bits_para_bytes
from .crc import adicionar_crc8, validar_crc8
from .paridade import criar_quadro_paridade, validar_quadro_paridade

def criar_quadros_metodo1(dados: bytes) -> list[list[int]]:
    return [criar_quadro_paridade(bytes_para_bits(bytes([byte]))) for byte in dados]

def validar_quadros_metodo1(quadros: list[list[int]]) -> tuple[bytes, bool]:
    if not all(validar_quadro_paridade(quadro) for quadro in quadros):
        return b"", False
    bits = [bit for quadro in quadros for bit in quadro[:8]]
    return bits_para_bytes(bits), True

def criar_quadro_metodo2(dados: bytes) -> bytes:
    if len(dados) > 255:
        raise ValueError("A mensagem do Método 2 pode ter no máximo 255 bytes.")
    dados_com_tamanho = bytes([len(dados)]) + dados
    return adicionar_crc8(dados_com_tamanho)

def separar_quadro_metodo2(quadro: bytes) -> tuple[bytes, bool]:
    if not validar_crc8(quadro) or len(quadro) < 2:
        return b"", False
    dados_com_tamanho = quadro[:-1]
    tamanho = dados_com_tamanho[0]
    dados = dados_com_tamanho[1:]
    if len(dados) != tamanho:
        return b"", False
    return dados, True