from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from .. import audio
from ..arquivos_audio import preparar_pasta_audio
from ..bits import texto_para_bytes
from ..metodo1_batidas import (
    bits_para_audio,
    audio_para_bits,
    bits_para_texto_batidas,
)
from ..metodo2_fsk import (
    bytes_para_audio,
    audio_para_bytes,
)
from ..quadros import criar_quadros_metodo1
from ..receptor_tempo_real import ReceptorBatidas
from ..configuracao import QUANTIDADE_PONTOS_GRAFICO
FUNDO = "#090909"
PAINEL = "#101010"
TEXTO = "#dddddd"
VERDE = "#00e5a0"
CINZA = "#777777"
class JanelaPrincipal:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.raiz.title("Camada Física usando Som")
        self.raiz.geometry("900x650")
        self.raiz.minsize(760, 560)
        self.raiz.configure(bg=FUNDO)
        self.metodo = tk.StringVar(
            value="Método 1 — Batidas"
        )
        self.mensagem = tk.StringVar()
        self.status = tk.StringVar(value="AGUARDANDO")
        self.bits_var = tk.StringVar(value="")
        self.batidas_var = tk.StringVar(value="0")
        self.resultado_var = tk.StringVar(value="")
        self.fila_audio = queue.Queue()
        self.receptor = ReceptorBatidas()
        self.fluxo = None
        self.capturando = False
        self.audio_recebido = []
        self.metodo_recepcao = None
        self._fsk_ultima_tentativa = 0
        self._fsk_concluido = False
        self.audio_atual = None
        self.caminho_audio = None
        self.pontos = np.zeros(
            QUANTIDADE_PONTOS_GRAFICO,
            dtype=np.float32
        )
        self.ultimo_resultado_log = None
        self._montar_interface()
        self._atualizar_tela()
        self.raiz.protocol(
            "WM_DELETE_WINDOW",
            self.fechar
        )
    def _montar_interface(self):
        tk.Label(
            self.raiz,
            text="AULA DE REDES DE COMPUTADORES",
            bg=FUNDO,
            fg=TEXTO,
            font=("Consolas", 16, "bold")
        ).pack(pady=(12, 2))
        tk.Label(
            self.raiz,
            text="CAMADA FÍSICA — COMUNICAÇÃO POR SOM",
            bg=FUNDO,
            fg=VERDE,
            font=("Consolas", 11, "bold")
        ).pack()
        topo = tk.Frame(self.raiz, bg=FUNDO)
        topo.pack(fill="x", padx=20, pady=10)
        tk.Label(
            topo,
            text="Método:",
            bg=FUNDO,
            fg=TEXTO
        ).pack(side="left")
        menu = tk.OptionMenu(
            topo,
            self.metodo,
            "Método 1 — Batidas",
            "Método 2 — 4-FSK"
        )
        menu.config(
            bg=PAINEL,
            fg=TEXTO,
            highlightthickness=0
        )
        menu.pack(side="left", padx=(8, 18))
        tk.Label(
            topo,
            text="Mensagem:",
            bg=FUNDO,
            fg=TEXTO
        ).pack(side="left")
        entrada = tk.Entry(
            topo,
            textvariable=self.mensagem,
            bg=PAINEL,
            fg=TEXTO,
            insertbackground=TEXTO,
            relief="flat"
        )
        entrada.pack(
            side="left",
            fill="x",
            expand=True,
            padx=8
        )
        botoes = tk.Frame(self.raiz, bg=FUNDO)
        botoes.pack(
            fill="x",
            padx=20,
            pady=(0, 8)
        )
        self.botao_transmitir = self._botao(
            botoes, "TRANSMITIR", self.transmitir
        )
        self.botao_receber = self._botao(
            botoes, "RECEBER", self.receber
        )
        self.botao_parar = self._botao(
            botoes, "PARAR", self.parar_recepcao
        )
        self._botao(
            botoes, "ABRIR WAV", self.abrir_wav
        )
        self._botao(
            botoes, "REPRODUZIR", self.reproduzir
        )
        self._botao(
            botoes, "SAIR", self.fechar
        )
        principal = tk.Frame(
            self.raiz,
            bg=PAINEL,
            highlightbackground="#303030",
            highlightthickness=1
        )
        principal.pack(
            fill="both",
            expand=True,
            padx=20
        )
        self.canvas = tk.Canvas(
            principal,
            bg=PAINEL,
            highlightthickness=0,
            height=300
        )
        self.canvas.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )
        self.canvas.bind(
            "<Configure>",
            lambda _: self._desenhar_grafico()
        )
        info = tk.Frame(principal, bg=PAINEL)
        info.pack(
            fill="x",
            padx=12,
            pady=(0, 12)
        )
        self._linha_info(
            info, "Estado:", self.status
        )
        self._linha_info(
            info,
            "Batidas no símbolo atual:",
            self.batidas_var
        )
        self._linha_info(
            info,
            "Bits recebidos:",
            self.bits_var
        )
        self._linha_info(
            info,
            "Resultado:",
            self.resultado_var
        )
        tk.Label(
            self.raiz,
            text="CODIFICAÇÃO",
            bg=FUNDO,
            fg=VERDE,
            font=("Consolas", 10, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(8, 0)
        )
        tk.Label(
            self.raiz,
            text=(
                "1 batida = 0       "
                "2 batidas consecutivas = 1       "
                "quadro = 8 bits + paridade"
            ),
            bg=FUNDO,
            fg=CINZA,
            font=("Consolas", 9)
        ).pack(anchor="w", padx=20)
        self.log = tk.Label(
            self.raiz,
            text="Sistema pronto.",
            bg=FUNDO,
            fg=CINZA,
            font=("Consolas", 8),
            anchor="w"
        )
        self.log.pack(
            fill="x",
            padx=20,
            pady=(6, 10)
        )
    def _botao(self, pai, texto, comando):
        botao = tk.Button(
            pai,
            text=texto,
            command=comando,
            bg=PAINEL,
            fg=TEXTO,
            activebackground="#202020",
            activeforeground=VERDE,
            relief="flat",
            font=("Consolas", 9),
            padx=8,
            pady=4
        )
        botao.pack(side="left", padx=(0, 5))
        return botao
    @staticmethod
    def _linha_info(pai, titulo, variavel):
        linha = tk.Frame(pai, bg=PAINEL)
        linha.pack(fill="x")
        tk.Label(
            linha,
            text=titulo,
            bg=PAINEL,
            fg=CINZA,
            font=("Consolas", 9),
            width=27,
            anchor="w"
        ).pack(side="left")
        tk.Label(
            linha,
            textvariable=variavel,
            bg=PAINEL,
            fg=TEXTO,
            font=("Consolas", 9),
            anchor="w"
        ).pack(
            side="left",
            fill="x"
        )
    def _registrar(self, texto):
        horario = datetime.now().strftime("%H:%M:%S")
        self.log.config(text=f"[{horario}] {texto}")
    def _atualizar_tela(self):
        if not self.raiz.winfo_exists():
            return
        self._processar_fila()
        if self.capturando and self.metodo_recepcao == "FSK":
            self._tentar_decodificar_fsk()
        if (
            self.capturando
            and self.metodo.get().startswith("Método 1")
        ):
            novos = self.receptor.atualizar_tempo()
            if novos:
                self._mostrar_bits_recebidos()
                self._atualizar_resultado()
        self._desenhar_grafico()
        self.raiz.after(
            50,
            self._atualizar_tela
        )
    def _processar_fila(self):
        processados = 0
        while processados < 4:
            try:
                bloco = self.fila_audio.get_nowait()
                print(
                     "[FILA] Bloco recebido:",
                      len(bloco),
                      "amostras" )
            except queue.Empty:
                 break
            bloco = np.asarray(
                bloco,
                dtype=np.float32
            ).reshape(-1)
            self.audio_recebido.append(bloco)
            # Verifica se existe áudio chegando
            amplitude = float(np.max(np.abs(bloco))) if bloco.size else 0.0
            if amplitude > 0.01:
                print(
                    f"[DEBUG] Áudio recebido | "
                    f"Amplitude: {amplitude:.4f}"
                )
            if self.metodo_recepcao != "FSK":
                resultado, novos = (
                    self.receptor.processar_bloco(bloco)
                )
                # Verifica se o detector identificou batidas
                if resultado.batida or novos:
                    print(
                        f"[DEBUG] Batida: {resultado.batida} | "
                        f"Novos bits: {novos} | "
                        f"Energia: {resultado.energia:.5f} | "
                        f"Limiar: {resultado.limiar:.5f}"
                    )
                self.status.set(
                    self.receptor.ultimo_estado
                )
                self.batidas_var.set(
                    str(self.receptor.batidas)
                )
                if novos:
                    self._mostrar_bits_recebidos()
                    self._atualizar_resultado()
            self.pontos = np.concatenate(
                (self.pontos, bloco)
            )[-QUANTIDADE_PONTOS_GRAFICO:]
            processados += 1
    def _tentar_decodificar_fsk(self, forcar=False):
        if self._fsk_concluido or not self.audio_recebido:
            return
        total = sum(len(bloco) for bloco in self.audio_recebido)
        from ..configuracao import TAXA_AMOSTRAGEM
        if total < int(0.7 * TAXA_AMOSTRAGEM):
            return
        if not forcar and total - self._fsk_ultima_tentativa < int(0.5 * TAXA_AMOSTRAGEM):
            return
        self._fsk_ultima_tentativa = total
        sinal = np.concatenate(self.audio_recebido)
        # O limite impede que uma gravação longa congele a interface.
        if len(sinal) > 20 * TAXA_AMOSTRAGEM:
            self.status.set("FSK: gravação longa; pressione PARAR para analisar")
            return
        try:
            dados, valido, simbolos = audio_para_bytes(sinal)
            if valido:
                texto = dados.decode("utf-8", errors="replace")
                self._fsk_concluido = True
                self.resultado_var.set(f"SUCESSO — {texto}")
                self.status.set("FSK RECEBIDO — CRC VÁLIDO")
                self.bits_var.set("".join(f"{byte:08b}" for byte in dados))
                self._registrar(f"FSK recebido: {texto}")
                print("[FSK RX] CRC válido | Mensagem:", texto)
        except Exception as erro:
            print("[FSK RX] Erro na decodificação:", repr(erro))

    def _mostrar_bits_recebidos(self):
        bits = "".join(
            map(str, self.receptor.bits)
        )
        self.bits_var.set(bits)
        print(
            f"[RX] Bits recebidos: {bits}",
            flush=True
        )
    def _desenhar_grafico(self):
        largura = max(
            100,
            self.canvas.winfo_width()
        )
        altura = max(
            100,
            self.canvas.winfo_height()
        )
        self.canvas.delete("grafico")
        self.canvas.create_line(
            0,
            altura / 2,
            largura,
            altura / 2,
            fill="#333333",
            tags="grafico"
        )
        if len(self.pontos) < 2:
            return
        escala = max(
            0.05,
            float(np.max(np.abs(self.pontos)))
        )
        valores = np.clip(
            self.pontos / escala,
            -1,
            1
        )
        pontos = []
        for i, valor in enumerate(valores):
            x = (
                i * (largura - 1)
                / (len(valores) - 1)
            )
            y = (
                altura / 2
                - valor * (altura * 0.42)
            )
            pontos.extend((x, y))
        self.canvas.create_line(
            *pontos,
            fill=VERDE,
            width=1,
            tags="grafico"
        )
    def transmitir(self):
        texto = self.mensagem.get()
        if not texto:
            messagebox.showwarning(
                "Mensagem",
                "Digite uma mensagem."
            )
            return
        try:
            dados = texto_para_bytes(texto)
            print("\n========== TRANSMISSÃO ==========")
            print(f"[TX] Mensagem: {texto}")
            print(f"[TX] Bytes: {len(dados)}")
            print(
                "[TX] Binário:",
                " ".join(f"{b:08b}" for b in dados)
            )
            if self.metodo.get().startswith("Método 1"):
                quadros = criar_quadros_metodo1(dados)
                bits = [
                    bit
                    for quadro in quadros
                    for bit in quadro
                ]
                print("[TX] Método 1 — Batidas")
                for indice, quadro in enumerate(
                    quadros, start=1
                ):
                    print(
                        f"[TX] Quadro {indice}: "
                        f"{''.join(map(str, quadro))}"
                    )
                audio_transmitido = bits_para_audio(
                    bits
                )
            else:
                print("[TX] Método 2 — 4-FSK")
                audio_transmitido, _ = (
                    bytes_para_audio(dados)
                )
            self.audio_atual = audio_transmitido
            caminho = preparar_pasta_audio() / (
                f"transmissao_"
                f"{datetime.now():%Y%m%d_%H%M%S}.wav"
            )
            audio.salvar_wav(
                caminho,
                audio_transmitido
            )
            self.caminho_audio = caminho
            self._registrar(
                f"Transmitindo {len(dados)} byte(s)."
            )
            threading.Thread(
                target=audio.reproduzir_audio,
                args=(audio_transmitido,),
                daemon=True
            ).start()
        except Exception as erro:
            messagebox.showerror(
                "Erro na transmissão",
                str(erro)
            )
    def receber(self):
        if self.capturando:
            return
        self._limpar_recepcao()
        self.metodo_recepcao = (
            "FSK" if self.metodo.get().startswith("Método 2") else "BATIDAS"
        )
        try:
            self.fluxo = audio.iniciar_recepcao_continua(
                self.fila_audio.put,
                dispositivo=15
            )
            self.capturando = True
            self.status.set("OUVINDO FSK" if self.metodo_recepcao == "FSK"
                            else "OUVINDO MIXAGEM ESTÉREO")
            self.botao_receber.config(state="disabled")
            self._registrar("Recepção ativa.")
            print("\n========== RECEPÇÃO ==========")
            print("[RX] Mixagem estéreo ativada.")
            print("[TESTE] Fluxo ativo:", self.fluxo.active)
            print("[TESTE] Fluxo parado:", self.fluxo.stopped)
            print("[TESTE] Taxa:", self.fluxo.samplerate)
            self.raiz.after(
                3000,
                lambda: print(
                    "[TESTE 3s] Fluxo ativo:",
                    (self.fluxo.active if self.fluxo is not None else False),
                    "| Blocos na fila:",
                    self.fila_audio.qsize()
                )
            )
        except Exception as erro:
            self.capturando = False
            messagebox.showerror(
                "Erro na recepção",
                str(erro)
            )
    def parar_recepcao(self):
        if not self.capturando:
            return
        self.capturando = False
        if self.fluxo is not None:
            self.fluxo.stop()
            self.fluxo.close()
            if hasattr(self.fluxo, "_rx_encerrar"):
                self.fluxo._rx_encerrar.set()
            if hasattr(self.fluxo, "_rx_trabalhador"):
                self.fluxo._rx_trabalhador.join(timeout=2)
            self.fluxo = None
        # Processa os blocos que ainda estavam na fila.
        while not self.fila_audio.empty():
            self._processar_fila()
        if self.metodo_recepcao == "FSK":
            self._tentar_decodificar_fsk(forcar=True)
            if not self._fsk_concluido:
                self.resultado_var.set("FSK: quadro não encontrado ou CRC inválido")
        else:
            self.receptor.atualizar_tempo()
            self._mostrar_bits_recebidos()
            self._atualizar_resultado()
        if self.audio_recebido:
            self.audio_atual = np.concatenate(
                self.audio_recebido
            )
            caminho = preparar_pasta_audio() / (
                f"recepcao_"
                f"{datetime.now():%Y%m%d_%H%M%S}.wav"
            )
            audio.salvar_wav(
                caminho,
                self.audio_atual
            )
            self.caminho_audio = caminho
            self._registrar(
                f"Recepção encerrada. WAV: {caminho}"
            )
        self.botao_receber.config(
            state="normal"
        )
        print("[RX] Recepção encerrada.")
    def _limpar_recepcao(self):
        self.receptor.reiniciar()
        self._fsk_ultima_tentativa = 0
        self._fsk_concluido = False
        self.audio_recebido.clear()
        self.pontos.fill(0)
        self.status.set("OUVINDO MICROFONE")
        self.batidas_var.set("0")
        self.bits_var.set("")
        self.resultado_var.set("")
        self.ultimo_resultado_log = None
        while True:
            try:
                self.fila_audio.get_nowait()
            except queue.Empty:
                break
    def _atualizar_resultado(self):
        dados, valido = (
            self.receptor.validar_quadros_prontos()
        )
        if valido is None:
            self.resultado_var.set("")
            return
        if valido:
            texto = dados.decode(
                "utf-8",
                errors="replace"
            )
            self.resultado_var.set(
                f"SUCESSO — {texto}"
            )
            resultado_log = (
                len(dados),
                True,
                texto
            )
        else:
            self.resultado_var.set(
                "FALHA DE TRANSMISSÃO — "
                "paridade inválida"
            )
            resultado_log = (
                len(self.receptor.bits),
                False,
                ""
            )
        if resultado_log != self.ultimo_resultado_log:
            print(
                "[RX] Paridade:",
                "VÁLIDA" if valido else "INVÁLIDA"
            )
            if valido:
                print(
                    "[RX] Bytes:",
                    " ".join(
                        f"{b:08b}" for b in dados
                    )
                )
                print(
                    f"[RX] Mensagem: {texto}"
                )
            self.ultimo_resultado_log = resultado_log
    def abrir_wav(self):
        caminho = filedialog.askopenfilename(
            filetypes=[
                ("Áudio WAV", "*.wav")
            ]
        )
        if not caminho:
            return
        try:
            audio_aberto = audio.abrir_wav(
                caminho
            )
            self.audio_atual = audio_aberto
            self.pontos = np.asarray(
                audio_aberto[-QUANTIDADE_PONTOS_GRAFICO:],
                dtype=np.float32
            )
            if self.metodo.get().startswith("Método 1"):
                bits, instantes = audio_para_bits(
                    audio_aberto
                )
                self.bits_var.set(
                    "".join(map(str, bits))
                )
                print(
                    "[WAV] Batidas detectadas:",
                    len(instantes)
                )
                print(
                    "[WAV] Bits:",
                    "".join(map(str, bits))
                )
                dados, valido = (
                    bits_para_texto_batidas(bits)
                )
                if valido:
                    texto = dados.decode(
                        "utf-8",
                        errors="replace"
                    )
                    self.resultado_var.set(
                        f"SUCESSO — {texto}"
                    )
                else:
                    self.resultado_var.set(
                        "FALHA OU QUADRO INCOMPLETO"
                    )
            else:
                dados, valido, _ = (
                    audio_para_bytes(audio_aberto)
                )
                if valido:
                    texto = dados.decode(
                        "utf-8",
                        errors="replace"
                    )
                    self.resultado_var.set(
                        f"SUCESSO — {texto}"
                    )
                else:
                    self.resultado_var.set(
                        "FALHA DE TRANSMISSÃO"
                    )
            self._registrar(
                f"WAV aberto: {Path(caminho).name}"
            )
        except Exception as erro:
            messagebox.showerror(
                "Erro ao abrir WAV",
                str(erro)
            )
    def reproduzir(self):
        if self.audio_atual is None:
            messagebox.showinfo(
                "Áudio",
                "Nenhum áudio carregado."
            )
            return
        threading.Thread(
            target=audio.reproduzir_audio,
            args=(self.audio_atual,),
            daemon=True
        ).start()
        self._registrar(
            "Reproduzindo áudio."
        )
    def fechar(self):
        if self.capturando:
            self.parar_recepcao()
        self.raiz.destroy()
def iniciar_interface():
    raiz = tk.Tk()
    JanelaPrincipal(raiz)
    raiz.mainloop()
