# ==========================================
# CONFIGURAÇÕES GERAIS DE ÁUDIO
# ==========================================

TAXA_AMOSTRAGEM = 44100
CANAIS = 1
BLOCO_AMOSTRAS = 2048
QUANTIDADE_PONTOS_GRAFICO = 1000

# ==========================================
# MÉTODO 1 - BATIDAS ACÚSTICAS
# ==========================================

AMPLITUDE_BATIDA = 0.8
DURACAO_BATIDA = 0.05

INTERVALO_SEGUNDA_BATIDA = 0.08
INTERVALO_DUAS_BATIDAS = 0.
INTERVALO_SIMBOLOS_TRANSMISSAO = 8.25

TEMPO_DECISAO_BIT = 0.15
TEMPO_MINIMO_ENTRE_BATIDAS = 0.03

TAMANHO_JANELA_ENERGIA = 2048

FATOR_LIMIAR_RUIDO = 3.0
LIMIAR_ENERGIA_MINIMO = 0.001


# ==========================================
# MÉTODO 2 - 4-FSK
# ==========================================

AMPLITUDE_FSK = 0.8
DURACAO_SIMBOLO_FSK = 0.05

FREQUENCIAS_FSK = (
    1000,
    1500,
    2000,
    2500,
)