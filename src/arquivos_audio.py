from pathlib import Path

PASTA_AUDIO = Path("audio")

def preparar_pasta_audio() -> Path:
    PASTA_AUDIO.mkdir(parents=True, exist_ok=True)
    return PASTA_AUDIO

def listar_audios() -> list[Path]:
    preparar_pasta_audio()
    return sorted(PASTA_AUDIO.glob("*.wav"))