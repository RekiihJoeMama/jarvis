"""
Graba tu voz de referencia en 3 tomas y promedia los embeddings,
para tener una referencia más robusta a la variación natural de tu voz.
Correr: python registrar_voz.py
"""
import sounddevice as sd
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

RATE = 44100
DURACION = 15
TOMAS = 3

def grabar_toma(numero):
    print(f"\n�️  Toma {numero}/{TOMAS} — vas a grabar {DURACION} segundos.")
    print("   Hablá de algo distinto cada vez (contá tu día, leé algo, lo que sea).")
    input("   Presioná ENTER cuando estés listo...")

    grabacion = sd.rec(int(DURACION * RATE), samplerate=RATE, channels=1, dtype="int16")
    sd.wait()
    print("   ✅ Toma terminada.")
    return grabacion[:, 0]

def main():
    encoder = VoiceEncoder()
    embeddings = []

    for i in range(1, TOMAS + 1):
        muestra = grabar_toma(i)
        muestra_float = muestra.astype(np.float32) / 32768.0
        wav_procesado = preprocess_wav(muestra_float, source_sr=RATE)
        embedding = encoder.embed_utterance(wav_procesado)
        embeddings.append(embedding)

    # Promediamos los 3 embeddings y normalizamos el resultado
    embedding_promedio = np.mean(embeddings, axis=0)
    embedding_promedio = embedding_promedio / np.linalg.norm(embedding_promedio)

    np.save("mi_voz.npy", embedding_promedio)
    print(f"\n✅ Guardado en mi_voz.npy, promediando {TOMAS} tomas — referencia más robusta.")

if __name__ == "__main__":
    main()