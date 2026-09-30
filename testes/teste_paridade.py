from src.paridade import criar_quadro_paridade, validar_quadro_paridade

def test_paridade_par():
    quadro = criar_quadro_paridade([1, 1, 0, 0, 0, 0, 0, 0])
    assert quadro == [1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert validar_quadro_paridade(quadro)

def test_paridade_detecta_erro():
    quadro = criar_quadro_paridade([1, 0, 0, 0, 0, 0, 0, 0])
    quadro[0] = 0
    assert not validar_quadro_paridade(quadro)