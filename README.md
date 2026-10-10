## 1. Fundamentação Teórica

### 1.1. Apresentação Resumida das 7 Camadas do Modelo ISO/OSI

O Modelo de Interconexão de Sistemas Abertos (ISO/OSI) é dividido em 7 camadas conceituais:

- **Camada de Aplicação (Camada 7):** Interface direta com os aplicativos e serviços finais (ex.: HTTP, FTP, SMTP).
- **Camada de Apresentação (Camada 6):** Responsável pela formatação, tradução, compressão e criptografia dos dados.
- **Camada de Sessão (Camada 5):** Gerencia, estabelece, mantém e encerra sessões de comunicação entre aplicações.
- **Camada de Transporte (Camada 4):** Garante a entrega confiável ou não de dados ponta a ponta (ex.: TCP, UDP) e realiza o controle de fluxo/erro.
- **Camada de Rede (Camada 3):** Trata do endereçamento lógico (ex.: IP) e do roteamento dos pacotes entre redes distintas.
- **Camada de Enlace de Dados (Camada 2):** Responsável pelo endereçamento físico (MAC), enquadramento (*framing*) e detecção de erros na transmissão local.
- **Camada Física (Camada 1):** Define os aspectos elétricos, mecânicos, ópticos ou acústicos para a transmissão dos bits brutos através do meio físico.

### 1.2. Detalhamento Aprofundado da Camada Física

- **Funções da Camada Física:**\
  A Camada Física é responsável por converter os bits lógicos (0s e 1s) fornecidos pelas camadas superiores em sinais físicos (sejam sinais elétricos, ondas eletromagnéticas, pulsos de luz ou ondas acústicas) capazes de propagar-se por um meio de transmissão. Além disso, define padrões de sincronização, conectores e taxas de transmissão.
- **Sinais Analógicos vs. Digitais:**
  - **Sinais Digitais:** Sinais discretos no tempo e em amplitude, representados por valores finitos e bem definidos (geralmente níveis de tensão fixos representando 0 ou 1).
  - **Sinais Analógicos:** Sinais contínuos no tempo e na amplitude, capazes de assumir infinitos valores intermediários (ex.: ondas sonoras senoidais propagadas pelo ar).
- **Largura de Banda e Taxa de Amostragem:**
  - **Largura de Banda (*Bandwidth*):** Intervalo de frequências (em Hz) suportado pelo meio de transmissão ou canal. Define a capacidade teórica de transmissão de dados.
  - **Taxa de Amostragem (*Sampling Rate*):** Frequência na qual o sinal analógico é convertido para o meio digital. Segundo o Teorema de Nyquist-Shannon, a taxa de amostragem mínima para reconstituir perfeitamente um sinal analógico deve ser de no mínimo o dobro da maior frequência presente no sinal:\
    \

  - **Condição de Nyquist:** `f_amostragem >= 2 × f_máxima`.
- **Modulação e Ruído:**
  - **Modulação:** Processo de modificar uma ou mais propriedades de uma onda portadora analógica (amplitude, frequência ou fase) de acordo com o sinal digital de dados que se deseja transmitir.
  - **Ruído:** Perturbações indesejadas introduzidas pelo meio de transmissão (como ruído térmico, interferência externa ou atenuação) que alteram a forma do sinal e podem causar erros na recepção.

### 1.3. Explicação Teórica sobre Detecção de Erros e Enquadramento

Na transmissão de dados acústicos, as perturbações físicas do meio (ruído ambiente, eco, atenuação) podem corromper os bits recebidos. Para estruturar a informação e verificar a integridade dos dados recebidos, utilizam-se técnicas de enquadramento (*framing*) e checagem de erros:

- **Paridade Par (*Even Parity*):**
  - **Conceito:** Método de detecção de erros onde um bit adicional (bit de paridade) é anexado a um bloco de dados (ex.: a cada byte / 8 bits).
  - **Funcionamento:** O valor do bit de paridade é definido de forma que a quantidade total de bits de valor 1 no quadro (incluindo o bit de paridade) seja sempre um número par.
  - **Verificação no Receptor:** Se ao receber o quadro a contagem de bits 1 for ímpar, o receptor detecta imediatamente que houve corrupção no canal físico.
- **Estrutura dos Quadros e Detecção de Erros por Método:**
  - **Enquadramento e Paridade no Método 1 (criar_quadros_metodo1 / validar_quadros_metodo1):**\
    Cada byte transmitido é convertido em um quadro de 9 bits: 8 bits de dados (*payload*) + 1 bit de Paridade Par no final. O receptor recebe a sequência total de bits, divide-a em blocos exatos de 9 bits e executa a função validar_quadros_metodo1. Se algum quadro violar a regra da paridade par ou a quantidade de bits não for múltipla de 9, a transmissão é marcada como inválida (valido = False).
  - **Enquadramento e Validação no Método 2 (criar_quadro_metodo2 / separar_quadro_metodo2):**\
    O quadro é composto pelo tamanho da mensagem nos primeiros bytes, seguido pela carga útil (*payload*) e um código de verificação de integridade (CRC) do quadro. A validação extrai a quantidade de bytes esperada (bytes_recebidos[0]) e verifica a consistência dos dados recebidos através da função separar_quadro_metodo2.

## 2. Engenharia e Arquitetura das Soluções

### 2.1. Explicação do Método 1 (Modulação por Pulsos Acústicos / Batidas)

O Método 1 implementa uma transmissão digital baseada na detecção de pulsos sonoros (batidas) no domínio do tempo.

- **Síntese do Sinal (Transmissor):**
  - **Geração da Batida (\_criar_batida):** O som da batida é gerado sinteticamente combinando três frequências fundamentais/harmônicas (850 Hz, 1700 Hz e 3200 Hz) atenuadas por um envelope exponencial decrescente ((-65.0t)).
  - **Mapeamento de Bits:**
    - O bit **0** é representado por uma **única batida**.
    - O bit **1** é representado por **duas batidas consecutivas** separadas por um intervalo curto definido por INTERVALO_SEGUNDA_BATIDA.
  - **Janelas de Tempo:** Entre a transmissão de símbolos consecutivos, aplica-se um intervalo de silêncio (silencio_entre_bits), garantindo que os ecos e reverberações do ambiente não sobreponham os símbolos seguintes.
- **Processamento e Decodificação (Receptor):**
  - **Cálculo da Energia e Limiares Adaptativos:**\
    O sinal de áudio recebido é dividido em blocos (ex.: 2048 amostras) e analisado em janelas menores para calcular a energia RMS (média(x2)).\
    O ruído de fundo é estimado dinamicamente via média móvel exponencial:\
    \

  - Exemplo de média móvel exponencial: `energia_ruido = 0,97 × energia_ruido + 0,03 × ruido_estimado`.
  - O limiar de detecção de pico é ajustado adaptativamente multiplicando a energia de ruído pelo fator FATOR_LIMIAR_RUIDO, respeitando um limite mínimo (LIMIAR_ENERGIA_MINIMO).
  - **Tratamento de Ruídos e Falsos Disparos:**\
    Uma batida só é validada no momento da borda de subida (quando a energia cruza o limiar vindo de baixo) e se tiver decorrido um tempo mínimo desde a última detecção (TEMPO_MINIMO_ENTRE_BATIDAS), evitando que uma mesma batida seja contada múltiplas vezes.
  - **Decodificação temporal (DecodificadorBatidas):**\
    Ao detectar uma primeira batida, o sistema aguarda um tempo até INTERVALO_DUAS_BATIDAS. Se uma segunda batida ocorrer dentro dessa janela, o bit 1 é decodificado. Caso o tempo ultrapasse TEMPO_DECISAO_BIT sem uma nova batida, assume-se o bit 0.

### 2.2. Explicação do Método 2 (Modulação M-FSK / 4-FSK)

O Método 2 utiliza modulação por chaveamento de frequência (*M-ary Frequency Shift Keying* — M-FSK), transmitindo 2 bits por símbolo (4 frequências distintas).

- **Estrutura dos Símbolos e Mapeamento:**\
  Cada símbolo de áudio carrega um par de bits (*dibit*):
  - (0, 0)  Símbolo 0  Frequência f0
  - (0, 1)  Símbolo 1  Frequência f1
  - (1, 0)  Símbolo 2  Frequência f2
  - (1, 1)  Símbolo 3  Frequência f3
- **Transmissor (bytes_para_audio):**
  - **Preâmbulo de Sincronização:** Toda transmissão inicia-se com uma sequência fixa de preâmbulo [0, 3, 0, 3, 0, 3, 0, 3], utilizada pelo receptor para localizar com precisão o início da mensagem.
  - **Janelamento:** Cada símbolo senoidal é multiplicado por uma Janela de Hanning (np.hanning), suavizando as bordas do sinal para reduzir o espalhamento espectral e evitar cliques/ruídos de transição no alto-falante.
- **Receptor e Detecção por Correlação de Energia (\_energia_frequencia):**
  - **Detecção de Frequência (Algoritmo do tipo Goertzel/Quadratura):**\
    Para classificar cada segmento de áudio, calcula-se a energia nas 4 frequências de interesse projetando o sinal sobre componentes ortogonais de seno e cosseno:\
    \

  - A energia é estimada pela soma dos quadrados das projeções do sinal sobre seno e cosseno na frequência analisada.
  - **Classificação:** O símbolo detectado corresponde ao índice da frequência que apresentou a maior energia (np.argmax).
  - **Sincronização e Tolerância a Erros (detectar_inicio):**\
    O receptor percorre o sinal de áudio deslizando a janela de extração para encontrar o preâmbulo. Permite-se uma tolerância de no máximo 1 erro no preâmbulo (melhor_erros <= 1), garantindo robustez contra ruídos no início da transmissão.
- **Taxa de Transmissão Teórica vs. Prática em bps:**
  - **Duração do Símbolo (Ts):** Definida em DURACAO_SIMBOLO_FSK (ex.: se Ts=0.05s, a taxa de símbolos é de 20 bauds).
  - **Taxa Teórica (Camada Física):** Como cada símbolo carrega 2 bits:\
    \

  - `Taxa bruta = 2 / Ts` bits por segundo.
  - **Taxa Prática (Efetiva/Payload):** Leva em consideração a sobrecarga (*overhead*) do preâmbulo, os bytes de controle de quadro/tamanho, a detecção de erros e os intervalos de silêncio (0.20s no início e fim):\
    \

  - `Taxa efetiva = bits úteis transmitidos / duração total do áudio (s)`.

### 2.3. Validação e Testes de Software (Módulos de Teste Sintético e Tempo Real)

O projeto descreve as seguintes rotinas de teste sintético. A presença e a execução dessas rotinas devem ser conferidas no repositório antes de declará-las como testes automatizados aprovados:

1. **Teste Sintético do Método 1 (test_metodo1_sintetico):**
   - **Objetivo:** Validar o pipeline completo de modulação e demodulação do Método 1 em ambiente isolado (sem interferência de microfone/alto-falante).
   - **Fluxo:** Converte a mensagem b"A" em quadros de 9 bits com paridade via criar_quadros_metodo1. Gera o vetor de áudio sintético correspondente via bits_para_audio. Processa o áudio através de audio_para_bits para recuperar os instantes e os bits. Valida se a mensagem recuperada é exatamente igual a b"A" e se a flag de paridade valido é verdadeira.
2. **Teste do Receptor em Tempo Real (test_receptor_tempo_real_reconhece_batidas):**
   - **Objetivo:** Garantir que o ReceptorBatidas responda adequadamente ao processamento por blocos (*streaming* em tempo real), simulando a chegada de dados por blocos de áudio.
   - **Fluxo:** Cria instâncias do receptor e alimenta a classe com blocos contendo períodos de silêncio alternados com rajadas de sinal (picos de amplitude 0.8 simulando batidas). Simula sequências representando bits 0 (uma batida) e bits 1 (duas batidas seguidas em janelas curtas). Confirma se a máquina de estados do receptor registra os bits no buffer interno (assert receptor.bits).
3. **Teste Sintético do Método 2 (test_metodo2_sintetico):**
   - **Objetivo:** Testar a modulação 4-FSK, o enquadramento com preâmbulo e o algoritmo de correlação de energia em frequências.
   - **Fluxo:** Modula o texto b"ABC" em sinal de áudio analógico com a função bytes_para_audio. Submete o vetor gerado ao processo de sincronização por preâmbulo e demodulação via audio_para_bytes. Verifica se a mensagem b"ABC" foi decodificada com sucesso e se o quadro é válido.




### 2.4. Resultados observados nos testes com Mixagem estéreo

Nos testes realizados no computador, a saída de áudio foi capturada pelo dispositivo **Mixagem estéreo (Realtek HD Audio Stereo input)**. O dispositivo trabalhava com dois canais a **48.000 Hz**, enquanto o processamento do projeto utilizava **44.100 Hz**, exigindo conversão de taxa de amostragem.

- **Método 1:** a transmissão do caractere `$` produziu o byte `00100100` e o quadro `001001000` (o último bit corresponde à paridade). A recepção recuperou os nove bits, validou a paridade e apresentou a mensagem `$`.
- **Método 2:** a transmissão do mesmo caractere foi decodificada com os bits úteis `00100100`; a interface apresentou **“FSK RECEBIDO — CRC VÁLIDO”** e **“SUCESSO — $”**. O áudio transmitido teve duração aproximada de **1,4 s**.

Esses resultados comprovam o funcionamento **nas condições testadas com captura interna de áudio**. Não equivalem a uma validação de transmissão pelo ar entre dois equipamentos, nem comprovam desempenho sob diferentes níveis de ruído ou para mensagens extensas.

## 3. Divisão de Tarefas da Equipe

**Integrantes:** Leilla Mendes da Silva, Stefanny Vitoria da Costa Rosa, Icaro de Souza Feitosa.


- **Stefanny:** Responsável pela elaboração da estrutura inicial de todos os códigos do projeto.
- **Leila:** Responsável pela revisão, correção e aprimoramento dos códigos, elaboração e execução dos casos de teste, desenvolvimento do relatório e produção do vídeo de apresentação.
- **Ícaro:** Responsável pela revisão dos códigos, contribuindo para a verificação da implementação.

## 4. Desafios, Problemas e Soluções

### 4.1. Preparação do ambiente Python

Durante a configuração do projeto no Windows, surgiram dificuldades com a ativação do ambiente virtual pelo PowerShell, instalação de dependências e importações entre módulos. Entre os erros registrados esteve `ModuleNotFoundError: No module named 'src.configuracao'`. Foram revisados a estrutura de pastas, os imports relativos e a execução do programa a partir da raiz do repositório com `python main.py`.

### 4.2. Fluxo de captura iniciado, mas sem receber amostras

O transmissor gerava e reproduzia os sinais, e a decodificação de arquivos WAV do Método 1 já funcionava. Porém, na recepção contínua, o fluxo de entrada chegava a iniciar e posteriormente ficava inativo, sem executar o primeiro callback ou entregar blocos à fila da interface. Isso impedia a identificação dos bits em tempo real.

Para isolar a falha, foram testados os dispositivos de entrada com a biblioteca `sounddevice`. A **Mixagem estéreo Realtek** conseguiu registrar áudio reproduzido por outros aplicativos quando configurada com **dois canais e 48.000 Hz**. O módulo de captura foi então ajustado para usar essas configurações, em vez de depender da configuração mono utilizada anteriormente.

### 4.3. Diferença entre taxas de amostragem

A taxa de captura de **48.000 Hz** era diferente da taxa de processamento de **44.100 Hz**. Para compatibilizar as amostras com os decodificadores, o sistema passou a converter o sinal usando `scipy.signal.resample_poly`. Os canais estéreo também foram combinados em um sinal mono para análise.

### 4.4. Processamento em tempo real e integração com Tkinter

A recepção exigia conciliar três atividades: coletar áudio continuamente, interpretar os blocos e atualizar a interface gráfica. Para reduzir o trabalho dentro do callback de áudio, foi adotado o encaminhamento dos blocos a uma fila interna, com processamento em uma thread auxiliar. A interface passou a consumir os blocos recebidos e a apresentar informações de depuração, como amplitude, energia, limiar e bits identificados.

Durante a integração também ocorreu o erro de indentação `IndentationError: expected an indented block after 'if' statement`, na rotina de encerramento da recepção. A função foi reorganizada, preservando o fechamento do fluxo e o processamento dos dados pendentes.

### 4.5. Detecção das batidas no Método 1

A dificuldade principal consistiu em reconhecer as batidas e decidir quando um símbolo representava `0` ou `1`. A análise considerava limiares de energia e intervalos temporais para evitar contagens duplicadas e distinguir uma batida de duas batidas consecutivas.

Depois de estabilizar a captura, os registros passaram a mostrar os eventos detectados e a reconstrução progressiva dos bits. No teste com `$`, a sequência recebida foi `001001000`, idêntica à transmitida, e a paridade foi considerada válida.

### 4.6. Sincronização e validação do Método 2 — 4-FSK

Na implementação inicial do Método 2, a interface chegou a apresentar **“FSK: quadro não encontrado ou CRC inválido”**. Esse resultado, isoladamente, não permitia concluir se a falha estava no reconhecimento do preâmbulo, no alinhamento dos símbolos, na classificação das frequências ou na validação do quadro.

Foram feitos ajustes na detecção do preâmbulo, na decodificação dos símbolos e na integração do processamento FSK com a interface. No teste posterior com `$`, o programa recuperou `00100100` e indicou **CRC válido**, demonstrando o funcionamento do método nesse cenário.

### 4.7. Papel e limites da detecção de erros

No Método 1, a **paridade par** permite identificar determinadas alterações na sequência de bits, mas pode deixar passar erros que modifiquem um número par de bits. No Método 2, o **CRC** verifica a integridade do quadro e identifica muitas classes de erro, mas não é uma garantia absoluta contra corrupção. Nenhum desses mecanismos, por si só, corrige automaticamente os dados recebidos.

### 4.8. Limitações ainda existentes

A validação apresentada ocorreu com **Mixagem estéreo**, capturando o som internamente no mesmo computador. Permanecem como possibilidades de avaliação futura: transmissão pelo ar entre alto-falante e microfone, mensagens maiores, diferentes níveis de ruído, distância entre dispositivos e medições repetidas de taxa de erro. Esses testes não devem ser descritos como concluídos sem evidências adicionais.

## 5. Declaração do Uso de Inteligência Artificial

Durante o desenvolvimento, foi utilizada **IA generativa (ChatGPT)** como ferramenta de apoio à identificação e interpretação de erros, sugestão de alterações em funções Python, revisão de indentação, organização do processamento de áudio e elaboração/revisão de trechos da documentação técnica.

As sugestões foram avaliadas por meio de testes executados no ambiente do projeto. Os resultados observados e os limites desses testes são apresentados neste README. A utilização de IA não substituiu a necessidade de configurar os dispositivos, executar o software e verificar as saídas obtidas.

## 6. Conclusão

O projeto permitiu aplicar conceitos da Camada Física por meio de duas estratégias de representação de dados em sinais sonoros: pulsos acústicos no Método 1 e modulação 4-FSK no Método 2. A experiência evidenciou que a comunicação depende tanto dos algoritmos de codificação e detecção quanto da configuração de dispositivos, da amostragem e da sincronização.

Os testes com o caractere `$` demonstraram a recuperação correta da mensagem nos dois métodos, com paridade válida no primeiro e CRC válido no segundo. A principal limitação dos resultados é o uso da Mixagem estéreo, que não reproduz integralmente as interferências de um canal acústico pelo ar. Ainda assim, a atividade proporcionou aprendizado prático sobre geração, captura, processamento e verificação de sinais na transmissão digital.

