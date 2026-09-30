from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np

from .. import audio
from ..arquivos_audio import preparar_pasta_audio
from ..bits import bytes_para_bits, texto_para_bytes
from ..metodo1_batidas import bits_para_audio
from ..metodo2_fsk import bytes_para_audio, audio_para_bytes
from ..quadros import criar_quadros_metodo1
from ..receptor_tempo_real import ReceptorBatidas
from ..configuracao import QUANTIDADE_PONTOS_GRAFICO, TAXA_AMOSTRAGEM

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

        self.metodo = tk.StringVar(value="Método 1 — Batidas")
        self.mensagem = tk.StringVar()
        self.status = tk.StringVar(value="AGUARDANDO")
        self.bits_var = tk.StringVar(value="")
        self.batidas_var = tk.StringVar(value="0")
        self.resultado_var = tk.StringVar(value="")

        self.fila_audio: queue.Queue[np.ndarray] = queue.Queue()
        self.receptor = ReceptorBatidas()
        self.fluxo = None
        self.capturando = False
        self.audio_recebido: list[np.ndarray] = []
        self.audio_atual = None
        self.caminho_audio = None
        self.pontos = np.zeros(QUANTIDADE_PONTOS_GRAFICO, dtype=np.float32)

        self._montar_interface()
        self._atualizar_tela()

    def _montar_interface(self):
        tk.Label(self.raiz, text="AULA DE REDES DE COMPUTADORES", bg=FUNDO, fg=TEXTO,
                 font=("Consolas", 16, "bold")).pack(pady=(12, 2))
        tk.Label(self.raiz, text="CAMADA FÍSICA — COMUNICAÇÃO POR SOM", bg=FUNDO, fg=VERDE,
                 font=("Consolas", 11, "bold")).pack()

        topo = tk.Frame(self.raiz, bg=FUNDO)
        topo.pack(fill="x", padx=20, pady=10)
        tk.Label(topo, text="Método:", bg=FUNDO, fg=TEXTO, font=("Consolas", 10)).pack(side="left")
        menu = tk.OptionMenu(topo, self.metodo, "Método 1 — Batidas", "Método 2 — 4-FSK")
        menu.config(bg=PAINEL, fg=TEXTO, activebackground="#222222", activeforeground=TEXTO,
                    highlightthickness=0, font=("Consolas", 10))
        menu["menu"].config(bg=PAINEL, fg=TEXTO, font=("Consolas", 10))
        menu.pack(side="left", padx=(8, 18))

        tk.Label(topo, text="Mensagem:", bg=FUNDO, fg=TEXTO, font=("Consolas", 10)).pack(side="left")
        entrada = tk.Entry(topo, textvariable=self.mensagem, bg=PAINEL, fg=TEXTO,
                           insertbackground=TEXTO, relief="flat", font=("Consolas", 10))
        entrada.pack(side="left", fill="x", expand=True, padx=8)

        botoes = tk.Frame(self.raiz, bg=FUNDO)
        botoes.pack(fill="x", padx=20, pady=(0, 8))
        self.botao_transmitir = self._botao(botoes, "[t] TRANSMITIR", self.transmitir)
        self.botao_receber = self._botao(botoes, "[r] RECEBER", self.receber)
        self.botao_parar = self._botao(botoes, "[s] PARAR", self.parar_recepcao)
        self._botao(botoes, "[a] ABRIR WAV", self.abrir_wav)
        self._botao(botoes, "[p] REPRODUZIR", self.reproduzir)
        self._botao(botoes, "[q] SAIR", self.raiz.destroy)

        principal = tk.Frame(self.raiz, bg=PAINEL, highlightbackground="#303030", highlightthickness=1)
        principal.pack(fill="both", expand=True, padx=20)

        self.canvas = tk.Canvas(principal, bg=PAINEL, highlightthickness=0, height=300)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda _: self._desenhar_grafico())

        info = tk.Frame(principal, bg=PAINEL)
        info.pack(fill="x", padx=12, pady=(0, 12))
        self._linha_info(info, "Estado:", self.status)
        self._linha_info(info, "Batidas no símbolo atual:", self.batidas_var)
        self._linha_info(info, "Bits recebidos:", self.bits_var)
        self._linha_info(info, "Resultado:", self.resultado_var)

        tk.Label(self.raiz, text="CODIFICAÇÃO", bg=FUNDO, fg=VERDE,
                 font=("Consolas", 10, "bold")).pack(anchor="w", padx=20, pady=(8, 0))
        tk.Label(self.raiz, text="1 batida = 0       2 batidas consecutivas = 1       quadro = 8 bits + paridade",
                 bg=FUNDO, fg=CINZA, font=("Consolas", 9)).pack(anchor="w", padx=20)

        self.log = tk.Label(self.raiz, text="Sistema pronto.", bg=FUNDO, fg=CINZA,
                            font=("Consolas", 8), anchor="w")
        self.log.pack(fill="x", padx=20, pady=(6, 10))

        self.raiz.bind("<KeyPress-t>", lambda _: self.transmitir())
        self.raiz.bind("<KeyPress-r>", lambda _: self.receber())
        self.raiz.bind("<KeyPress-s>", lambda _: self.parar_recepcao())
        self.raiz.bind("<KeyPress-q>", lambda _: self.raiz.destroy())

    def _botao(self, pai, texto, comando):
        botao = tk.Button(pai, text=texto, command=comando, bg=PAINEL, fg=TEXTO,
                          activebackground="#202020", activeforeground=VERDE,
                          relief="flat", font=("Consolas", 9), padx=8, pady=4)
        botao.pack(side="left", padx=(0, 5))
        return botao

    @staticmethod
    def _linha_info(pai, titulo, variavel):
        linha = tk.Frame(pai, bg=PAINEL)
        linha.pack(fill="x")
        tk.Label(linha, text=titulo, bg=PAINEL, fg=CINZA,
                 font=("Consolas", 9), width=27, anchor="w").pack(side="left")
        tk.Label(linha, textvariable=variavel, bg=PAINEL, fg=TEXTO,
                 font=("Consolas", 9), anchor="w").pack(side="left", fill="x")

    def _registrar(self, texto):
        self.log.config(text=f"[{datetime.now():%H:%M:%S}] {texto}")

    def _atualizar_tela(self):
        self._processar_fila()
        if self.capturando and self.metodo.get().startswith("Método 1"):
            novos = self.receptor.atualizar_tempo()
            if novos:
                self._atualizar_resultado()
        self._desenhar_grafico()
        self.raiz.after(50, self._atualizar_tela)

    def _processar_fila(self):
        processados = 0
        while processados < 4:
            try:
                bloco = self.fila_audio.get_nowait()
            except queue.Empty:
                break
            self.audio_recebido.append(bloco)
            if self.metodo.get().startswith("Método 1"):
                resultado, novos = self.receptor.processar_bloco(bloco)
                self.status.set(self.receptor.ultimo_estado)
                self.batidas_var.set(str(self.receptor.batidas))
                if novos:
                    self.bits_var.set("".join(map(str, self.receptor.bits)))
                    self._atualizar_resultado()
            self.pontos = np.concatenate((self.pontos, bloco))[-QUANTIDADE_PONTOS_GRAFICO:]
            processados += 1

    def _desenhar_grafico(self):
        largura = max(100, self.canvas.winfo_width())
        altura = max(100, self.canvas.winfo_height())
        self.canvas.delete("grafico")
        self.canvas.create_line(0, altura / 2, largura, altura / 2, fill="#333333", tags="grafico")
        if len(self.pontos) < 2:
            return
        escala = max(0.05, float(np.max(np.abs(self.pontos))))
        valores = np.clip(self.pontos / escala, -1, 1)
        pontos = []
        for i, valor in enumerate(valores):
            x = i * (largura - 1) / (len(valores) - 1)
            y = altura / 2 - valor * (altura * 0.42)
            pontos.extend((x, y))
        self.canvas.create_line(*pontos, fill=VERDE, width=1, tags="grafico")

    def transmitir(self):
        texto = self.mensagem.get()
        if not texto:
            messagebox.showwarning("Mensagem", "Digite uma mensagem.")
            return
        try:
            dados = texto_para_bytes(texto)
            if self.metodo.get().startswith("Método 1"):
                quadros = criar_quadros_metodo1(dados)
                bits = [bit for quadro in quadros for bit in quadro]
                audio_transmitido = bits_para_audio(bits)
            else:
                audio_transmitido, _ = bytes_para_audio(dados)

            self.audio_atual = audio_transmitido
            caminho = preparar_pasta_audio() / f"transmissao_{datetime.now():%Y%m%d_%H%M%S}.wav"
            audio.salvar_wav(caminho, audio_transmitido)
            self.caminho_audio = caminho
            self._registrar(f"Transmitindo {len(dados)} byte(s) pelo alto-falante.")
            threading.Thread(target=audio.reproduzir_audio, args=(audio_transmitido,), daemon=True).start()
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))

    def receber(self):
        if self.capturando:
            return
        self._limpar_recepcao()
        self.capturando = True
        self.status.set("OUVINDO MICROFONE")
        self._registrar("Recepção ativa. Agora transmita pelo outro computador.")
        try:
            self.fluxo = audio.iniciar_recepcao_continua(self.fila_audio.put)
            self.botao_receber.config(state="disabled")
        except Exception as erro:
            self.capturando = False
            messagebox.showerror("Microfone", str(erro))

    def parar_recepcao(self):
        if not self.capturando:
            return
        self.capturando = False
        if self.fluxo is not None:
            self.fluxo.stop()
            self.fluxo.close()
            self.fluxo = None

        self.receptor.atualizar_tempo()
        self.bits_var.set("".join(map(str, self.receptor.bits)))
        self._atualizar_resultado()

        if self.audio_recebido:
            self.audio_atual = np.concatenate(self.audio_recebido)
            caminho = preparar_pasta_audio() / f"recepcao_{datetime.now():%Y%m%d_%H%M%S}.wav"
            audio.salvar_wav(caminho, self.audio_atual)
            self.caminho_audio = caminho
            self._registrar(f"Recepção encerrada. WAV salvo em {caminho}.")
        self.botao_receber.config(state="normal")

    def _limpar_recepcao(self):
        self.receptor.reiniciar()
        self.audio_recebido.clear()
        self.pontos.fill(0)
        self.status.set("OUVINDO MICROFONE")
        self.batidas_var.set("0")
        self.bits_var.set("")
        self.resultado_var.set("")
        while not self.fila_audio.empty():
            try:
                self.fila_audio.get_nowait()
            except queue.Empty:
                break

    def _atualizar_resultado(self):
        dados, valido = self.receptor.validar_quadros_prontos()
        if valido is None:
            self.resultado_var.set("")
        elif valido:
            try:
                texto = dados.decode("utf-8")
            except UnicodeDecodeError:
                texto = "<dados não formam UTF-8 válido>"
            self.resultado_var.set(f"SUCESSO — {texto}")
        else:
            self.resultado_var.set("FALHA DE TRANSMISSÃO — paridade inválida")

    def abrir_wav(self):
        caminho = filedialog.askopenfilename(filetypes=[("Áudio WAV", "*.wav")])
        if not caminho:
            return
        try:
            audio_aberto = audio.abrir_wav(caminho)
            self.audio_atual = audio_aberto
            self.pontos = audio_aberto[-QUANTIDADE_PONTOS_GRAFICO:]
            if self.metodo.get().startswith("Método 1"):
                from ..metodo1_batidas import audio_para_bits
                bits, _ = audio_para_bits(audio_aberto)
                self.bits_var.set("".join(map(str, bits)))
            else:
                dados, valido, _ = audio_para_bytes(audio_aberto)
                self.resultado_var.set("SUCESSO" if valido else "FALHA DE TRANSMISSÃO")
                if valido:
                    self.resultado_var.set(f"SUCESSO — {dados.decode('utf-8', errors='replace')}")
            self._registrar(f"WAV aberto: {Path(caminho).name}")
        except Exception as erro:
            messagebox.showerror("Erro ao abrir WAV", str(erro))

    def reproduzir(self):
        if self.audio_atual is None:
            messagebox.showinfo("Áudio", "Nenhum áudio carregado.")
            return
        threading.Thread(target=audio.reproduzir_audio, args=(self.audio_atual,), daemon=True).start()
        self._registrar("Reproduzindo áudio.")

def iniciar_interface():
    raiz = tk.Tk()
    JanelaPrincipal(raiz)
    raiz.mainloop()
