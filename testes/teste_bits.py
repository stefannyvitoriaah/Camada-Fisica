from src.bits import bits_para_bytes, bytes_para_bits, texto_para_bytes, bytes_para_texto

def test_conversao_bits():
    dados = texto_para_bytes("Oi")
    assert bytes_para_texto(bits_para_bytes(bytes_para_bits(dados))) == "Oi"