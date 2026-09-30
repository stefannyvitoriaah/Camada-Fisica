def calcular_paridade_par(bits_dados: list[int]) -> int:
    if len(bits_dados) != 8 or any(bit not in (0, 1) for bit in bits_dados):
        raise ValueError("A paridade do Método 1 usa exatamente 8 bits de dados.")
    return sum(bits_dados) % 2

def criar_quadro_paridade(bits_dados: list[int]) -> list[int]:
    return bits_dados + [calcular_paridade_par(bits_dados)]

def validar_quadro_paridade(quadro: list[int]) -> bool:
    if len(quadro) != 9 or any(bit not in (0, 1) for bit in quadro):
        return False
    return calcular_paridade_par(quadro[:8]) == quadro[8]