from src.quadros import criar_quadros_metodo1, validar_quadros_metodo1, criar_quadro_metodo2, separar_quadro_metodo2

def test_quadro_metodo1():
    quadros = criar_quadros_metodo1(b"A")
    dados, valido = validar_quadros_metodo1(quadros)
    assert dados == b"A"
    assert valido

def test_quadro_metodo2():
    quadro = criar_quadro_metodo2(b"ABC")
    dados, valido = separar_quadro_metodo2(quadro)
    assert dados == b"ABC"
    assert valido