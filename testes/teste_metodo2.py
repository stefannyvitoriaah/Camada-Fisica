from src.metodo2_fsk import bytes_para_audio, audio_para_bytes

def test_metodo2_sintetico():
    audio, _ = bytes_para_audio(b"ABC")
    dados, valido, _ = audio_para_bytes(audio)
    assert valido
    assert dados == b"ABC"
