import sys
import os

if getattr(sys, "frozen", False):
    sys.stdin = open(os.devnull, "r")
    
    
    # --- Parche anti-crash para modo silencioso (sin consola) ---
if sys.stdout is None or sys.stderr is None:
    log_dir = os.path.join(os.getenv('APPDATA'), '.minecraft', 'config', 'jarvis', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'jarvis_log.txt')
    log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file
    print(f"\n--- Nueva sesión iniciada ---")
    
def obtener_ruta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = obtener_ruta_base()
"""
JARVIS - Detector de Aplausos + Reconocimiento de Voz (sin pyaudio)
=====================================================================
Escucha el micrófono, detecta 2 aplausos seguidos para activarse
(estilo Iron Man), y una vez activado escucha tu comando de voz
y te responde hablando.

INSTALACIÓN (correr en tu PC, en una terminal):
    pip install sounddevice numpy SpeechRecognition pyttsx3 scipy

USO:
    python jarvis_clap_detector.py
"""
import sys
import obsws_python as obs
import keyboard
import sounddevice as sd
import numpy as np
import time
import speech_recognition as sr
import pyttsx3
import io
import wave
import winsound
import os
from google import genai
from scipy.signal import butter, lfilter, lfilter_zi
from datetime import datetime, timedelta
import json
ARCHIVO_ESTADO = os.path.join(BASE_DIR, "estado_jarvis.json")



def iniciar_buddy():
    """Lanza el compañero visual (buddy). Detecta si Jarvis corre empaquetado
    o desde el código fuente, y arranca el buddy de la forma correspondiente."""
    try:
        if getattr(sys, "frozen", False):
            carpeta_actual = os.path.dirname(sys.executable)
            ruta_buddy = os.path.join(carpeta_actual, "JarvisBuddy.exe")
            if os.path.exists(ruta_buddy):
                subprocess.Popen([ruta_buddy], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                print(f"⚠️ No encontré JarvisBuddy.exe en {carpeta_actual}")
        else:
            ruta_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_buddy.py")
            subprocess.Popen([sys.executable, ruta_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"❌ Error iniciando el buddy: {e}")

_ultimo_estado = "dormido"
_ultimo_texto = ""
def actualizar_estado(estado, texto=""):
    global _ultimo_estado, _ultimo_texto
    _ultimo_estado = estado
    _ultimo_texto = texto
    _escribir_estado()

def _escribir_estado():
    try:
        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            json.dump({
                "estado": _ultimo_estado,
                "texto": _ultimo_texto,
                "timestamp": time.time()   # <-- la marca de tiempo, clave para detectar si sigue vivo
            }, f)
    except Exception as e:
        print(f"❌ Error escribiendo estado: {e}")

def _latido_estado():
    """Reescribe el estado actual cada 2 segundos, aunque no haya cambiado nada.
    Así el muñeco sabe que Jarvis.py sigue vivo."""
    while True:
        time.sleep(2)
        _escribir_estado()
        # ------------------ CONFIGURACIÓN DE GEMINI ------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️  No encontré la variable de entorno GEMINI_API_KEY.")
    print("   Jarvis va a funcionar solo con los comandos fijos, sin IA de respaldo.")
    gemini_client = None
else:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ------------------ CONEXIÓN A OBS (grabación de pantalla) ------------------
try:
    cliente_obs = obs.ReqClient(host='localhost', port=4455, password='BVovPTyeHQStFEV8')
    print("✅ Conectado a OBS para grabación de pantalla")
except Exception as e:
    cliente_obs = None
    print(f"⚠️ No pude conectar con OBS (¿está abierto?): {e}")


# Instrucciones que le damos a Gemini para que actúe como Jarvis
SYSTEM_PROMPT = (
    "Sos Jarvis, un asistente de voz personal en español rioplatense/argentino. "
    "Respondé SIEMPRE en 1 o 2 oraciones cortas, nunca uses listas ni markdown "
    "porque tu respuesta se lee en voz alta con un sintetizador de voz. "
    "Sé directo y natural, como si hablaras con un amigo."
)


def preguntar_a_gemini(texto, intentos=3):
    """Le manda el texto a Gemini y devuelve la respuesta como string.
    Si el modelo está ocupado (503), reintenta un par de veces antes de rendirse."""
    if not gemini_client:
        return "No tengo conectada la inteligencia artificial todavía, revisá la variable de entorno."

    for intento in range(intentos):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-flash-latest",
                contents=texto,
                config={"system_instruction": SYSTEM_PROMPT},
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error llamando a Gemini (intento {intento + 1}/{intentos}): {e}")
            if intento < intentos - 1:
                time.sleep(1.5)  # Esperamos un cachito antes de reintentar

    return "El servidor de Gemini está saturado en este momento, probemos de nuevo en un rato."


# ------------------ CONFIGURACIÓN DE GROQ Y OPENROUTER ------------------
from openai import OpenAI

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if GROQ_API_KEY:
    cliente_groq = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        timeout=10,
    )
else:
    cliente_groq = None
    print("⚠️  No encontré GROQ_API_KEY, Groq queda fuera de la cascada de IA.")

if OPENROUTER_API_KEY:
    cliente_openrouter = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        timeout=10,
        max_retries=0,
    )
else:
    cliente_openrouter = None
    print("⚠️  No encontré OPENROUTER_API_KEY, OpenRouter queda fuera de la cascada de IA.")

MODELOS_OPENROUTER = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-27b-it:free",
    "openrouter/free",
]


def _preguntar_a_groq(texto, system_prompt=SYSTEM_PROMPT):
    if not cliente_groq:
        raise RuntimeError("Groq no está configurado")
    respuesta = cliente_groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto},
        ],
    )
    return respuesta.choices[0].message.content.strip()


def _preguntar_a_openrouter(texto, system_prompt=SYSTEM_PROMPT):
    if not cliente_openrouter:
        raise RuntimeError("OpenRouter no está configurado")
    respuesta = cliente_openrouter.chat.completions.create(
        model=MODELOS_OPENROUTER[0],
        extra_body={"models": MODELOS_OPENROUTER},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto},
        ],
    )
    return respuesta.choices[0].message.content.strip()


def preguntar_a_ia(texto):
    """Cascada de proveedores: Groq -> OpenRouter -> Gemini.
    Si uno falla (rate limit, timeout, lo que sea), pasa al siguiente sin cortar la conversación."""
    contexto_memoria = obtener_contexto_memoria()
    prompt_con_memoria = SYSTEM_PROMPT
    if contexto_memoria:
        prompt_con_memoria = SYSTEM_PROMPT + " " + contexto_memoria

    proveedores = [
        ("Groq", lambda t: _preguntar_a_groq(t, prompt_con_memoria)),
        ("OpenRouter", lambda t: _preguntar_a_openrouter(t, prompt_con_memoria)),
    ]

    for nombre, funcion in proveedores:
        try:
            respuesta = funcion(texto)
            if respuesta:
                print(f"✅ Respondió {nombre}")
                return respuesta
        except Exception as e:
            print(f"⚠️  {nombre} falló ({e}), paso al siguiente proveedor")

    print("⚠️  Groq y OpenRouter fallaron, caigo a Gemini como red de seguridad")
    return preguntar_a_gemini(texto)


# ------------------ CONFIGURACIÓN DE APLAUSOS ------------------
CHUNK = 1024
CHANNELS = 1
RATE = 44100

CLAP_THRESHOLD = 0.12
CLAP_WINDOW = 0.4
COOLDOWN = 1.5
b_filtro, a_filtro = butter(4, 1000, btype='highpass', fs=RATE)
zi_filtro = lfilter_zi(b_filtro, a_filtro) * 0.0  # estado inicial en reposo

# Estado global del detector de aplausos
last_clap_time = 0
clap_count = 0
last_activation = 0
was_above_threshold = False   # Para detectar el FLANCO (transición silencio -> fuerte)
activation_pending = False    # Bandera que el callback prende y el main loop revisa
jarvis_ocupado = False        # NUEVO: True mientras Jarvis está en medio de una interacción
last_edge_time = 0            # NUEVO: para debounce de ringing del filtro
EDGE_DEBOUNCE = 0.08           # 80ms — más rápido que esto, se ignora (es ringing, no un aplauso real)
alarma_activa = None      # guarda el datetime objetivo, o None si no hay alarma puesta
alarma_sonando = False    # True mientras está sonando y esperando el aplauso para apagarse
jarvis_grabando = False       # True mientras se está grabando pantalla
modo_no_molestar = False

from resemblyzer import VoiceEncoder, preprocess_wav

RUTA_EMBEDDING_VOZ = os.path.join(BASE_DIR, "mi_voz.npy")
RUTA_CONFIG_VOZ = os.path.join(BASE_DIR, "config_voz.json")
UMBRAL_VOZ = 0.70

voice_encoder = VoiceEncoder()

if os.path.exists(RUTA_EMBEDDING_VOZ):
    embedding_referencia = np.load(RUTA_EMBEDDING_VOZ)
    print("✅ Embedding de voz cargado")
else:
    embedding_referencia = None
    print("⚠️  No encontré mi_voz.npy — corré registrar_voz.py primero. Verificación de hablante desactivada por ahora.")

def _cargar_estado_verificacion():
    """Lee si la verificación de voz está activa desde el archivo de config. Por defecto: activa."""
    if os.path.exists(RUTA_CONFIG_VOZ):
        try:
            with open(RUTA_CONFIG_VOZ, "r", encoding="utf-8") as f:
                return json.load(f).get("verificacion_activa", True)
        except Exception:
            return True
    return True

def _guardar_estado_verificacion(activa):
    try:
        with open(RUTA_CONFIG_VOZ, "w", encoding="utf-8") as f:
            json.dump({"verificacion_activa": activa}, f)
    except Exception as e:
        print(f"❌ Error guardando config de voz: {e}")

verificacion_voz_activa = _cargar_estado_verificacion()

def calibrar_umbral(duracion=2, samplerate=RATE, margen=7.0):
    print(f"🔧 Calibrando umbral de ruido... quedate en silencio {duracion} segundos.")
    grabacion = sd.rec(int(duracion * samplerate), samplerate=samplerate, channels=1, dtype="float32")
    sd.wait()
    señal_filtrada = lfilter(b_filtro, a_filtro, grabacion[:, 0])
    ruido_base = np.sqrt(np.mean(señal_filtrada**2))
    umbral = max(ruido_base * margen, 0.02)
    print(f"✅ Ruido base (filtrado): {ruido_base:.4f} | Umbral calculado: {umbral:.4f}")
    return umbral

# ------------------ CONFIGURACIÓN DE VOZ ------------------
recognizer = sr.Recognizer()

COMANDO_DURACION = 7


import asyncio
import edge_tts
import re
import threading

VOZ_JARVIS = "es-AR-TomasNeural"


import subprocess




async def _stream_voz_a_ffplay(texto, proceso_ffplay):
    """
    Genera el audio con edge-tts en modo STREAMING: en vez de esperar
    el archivo completo, va mandando cada pedacito de audio directo
    al stdin de ffplay, que lo reproduce a medida que llega.
    """
    communicate = edge_tts.Communicate(texto, VOZ_JARVIS, rate="+15%")
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            proceso_ffplay.stdin.write(chunk["data"])
            proceso_ffplay.stdin.flush()


def hablar(texto):
    print(f"🗣️  Jarvis: {texto}")
    actualizar_estado("hablando", texto)
    try:
        proceso = subprocess.Popen(
    ["ffplay", "-autoexit", "-nodisp", "-loglevel", "quiet",
     "-af", "aformat=channel_layouts=stereo", "-i", "pipe:0"],
    stdin=subprocess.PIPE,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
        asyncio.run(_stream_voz_a_ffplay(texto, proceso))
        proceso.stdin.close()
        proceso.wait()
    except Exception as e:
        print(f"❌ Error con la voz neuronal: {e}")
        hablar("Tuve un problema con la voz neuronal.")
        
def grabar_audio(duracion=COMANDO_DURACION, samplerate=RATE):
    """Graba con sounddevice y arma un AudioData para SpeechRecognition."""
    grabacion = sd.rec(
        int(duracion * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(grabacion.tobytes())
    buffer.seek(0)

    with sr.AudioFile(buffer) as source:
        audio_data = recognizer.record(source)

    return audio_data, grabacion[:, 0]   # <-- devolvemos también las muestras crudas


def verificar_hablante(muestra_int16, samplerate=RATE):
    """Compara la muestra de audio contra tu embedding de referencia.
    Devuelve True si es tu voz, si la verificación está apagada, o si no hay referencia cargada."""
    if not verificacion_voz_activa or embedding_referencia is None:
        return True

    try:
        muestra_float = muestra_int16.astype(np.float32) / 32768.0
        wav_procesado = preprocess_wav(muestra_float, source_sr=samplerate)
        embedding_actual = voice_encoder.embed_utterance(wav_procesado)

        similitud = np.dot(embedding_referencia, embedding_actual) / (
            np.linalg.norm(embedding_referencia) * np.linalg.norm(embedding_actual)
        )
        print(f"� Similitud de voz: {similitud:.3f} (umbral: {UMBRAL_VOZ})")
        return similitud >= UMBRAL_VOZ
    except Exception as e:
        print(f"❌ Error verificando hablante: {e}")
        return True

def escuchar_comando():
    actualizar_estado("escuchando")
    print(f"�️ Escuchando tu comando ({COMANDO_DURACION} segundos)...")
    winsound.Beep(1000, 150)
    try:
        audio, muestra_cruda = grabar_audio()
    except Exception as e:
        print(f"❌ Error al grabar: {e}")
        hablar("Tuve un problema grabando, probemos de nuevo.")
        return None

    if not verificar_hablante(muestra_cruda):
        print("� Voz no reconocida, ignorando comando.")
        hablar("No te reconozco la voz, no puedo hacer eso.")
        return None

    try:
        texto = recognizer.recognize_google(audio, language="es-AR")
        print(f"�️ Vos dijiste: {texto}")
        return texto
    except sr.UnknownValueError:
        hablar("No te entendí bien, repetime.")
        return None
    except sr.RequestError as e:
        print(f"❌ Error de conexión con Google: {e}")
        hablar("Me quedé sin internet para procesar la voz.")
        return None
    
def controlar_volumen(accion, nivel=None):
    """accion: 'subir', 'bajar', 'silenciar' o 'nivel'. Si accion es 'nivel', usa el parámetro nivel (0-100)."""
    try:
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume

        if accion == "silenciar":
            nuevo_mute = not volume.GetMute()
            volume.SetMute(nuevo_mute, None)
            return "Silenciado" if nuevo_mute else "Reactivé el sonido"

        if accion == "nivel" and nivel is not None:
            nivel = max(0, min(100, nivel))
            volume.SetMasterVolumeLevelScalar(nivel / 100, None)
            return f"Volumen al {nivel} por ciento"

        actual = volume.GetMasterVolumeLevelScalar()  # 0.0 a 1.0
        paso = 0.1
        nuevo = actual + paso if accion == "subir" else actual - paso
        nuevo = max(0.0, min(1.0, nuevo))
        volume.SetMasterVolumeLevelScalar(nuevo, None)
        return f"Volumen en {int(nuevo * 100)} por ciento"

    except Exception as e:
        print(f"❌ Error controlando volumen: {e}")
        return "No pude controlar el volumen."
    
def mutear_microfono():
    """Mutea o desmutea el micrófono de entrada (no el volumen de salida)."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        mic_device = AudioUtilities.GetMicrophone()
        interface = mic_device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        nuevo_mute = not volume.GetMute()
        volume.SetMute(nuevo_mute, None)
        return "Micrófono silenciado" if nuevo_mute else "Micrófono reactivado"
    except Exception as e:
        print(f"❌ Error muteando micrófono: {e}")
        return "No pude controlar el micrófono."

def _descripcion_clima(codigo):
    """Traduce el weather_code de Open-Meteo (estándar WMO) a texto en español."""
    codigos = {
        0: "cielo despejado",
        1: "mayormente despejado",
        2: "parcialmente nublado",
        3: "nublado",
        45: "con niebla",
        48: "con niebla escarchada",
        51: "con llovizna leve",
        53: "con llovizna moderada",
        55: "con llovizna intensa",
        61: "con lluvia leve",
        63: "con lluvia moderada",
        65: "con lluvia intensa",
        71: "con nevada leve",
        73: "con nevada moderada",
        75: "con nevada intensa",
        80: "con chubascos leves",
        81: "con chubascos moderados",
        82: "con chubascos fuertes",
        95: "con tormenta",
        96: "con tormenta y granizo",
        99: "con tormenta y granizo fuerte",
    }
    return codigos.get(codigo, "con condiciones variables")

def _normalizar_numeros_texto(texto):
    """Convierte números escritos en palabras (uno, dos, tres...) a dígitos,
    porque el reconocimiento de voz a veces transcribe así en vez de '2'."""
    numeros_palabra = {
        "un": "1", "uno": "1", "una": "1",
        "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5",
        "seis": "6", "siete": "7", "ocho": "8", "nueve": "9",
        "diez": "10", "once": "11", "doce": "12", "trece": "13",
        "catorce": "14", "quince": "15", "dieciséis": "16", "dieciseis": "16",
        "diecisiete": "17", "dieciocho": "18", "diecinueve": "19",
        "veinte": "20", "veinticuatro": "24", "treinta": "30",
        "cuarenta": "40", "cuarenta y ocho": "48",
    }
    for palabra, digito in numeros_palabra.items():
        texto = re.sub(rf"\b{palabra}\b", digito, texto)
    return texto

EXCLUSIONES_CERRAR_TODO = [
    "jarvis",
    "visual studio code",
    "program manager",
    "windows powershell",
]

def cerrar_todo():
    """Cierra todas las ventanas visibles, excepto las protegidas en EXCLUSIONES_CERRAR_TODO."""
    import pygetwindow as gw

    ventanas = gw.getAllWindows()
    cerradas = []

    for v in ventanas:
        titulo = v.title.strip()
        if not titulo:
            continue
        if any(exclusion in titulo.lower() for exclusion in EXCLUSIONES_CERRAR_TODO):
            continue
        try:
            v.close()
            cerradas.append(titulo)
        except Exception as e:
            print(f"⚠️  No pude cerrar '{titulo}': {e}")

    if not cerradas:
        return "No había ventanas para cerrar."
    return f"Listo, cerré {len(cerradas)} ventanas."

def obtener_pronostico(texto_original):
    """Parsea 'pronóstico en N horas/días' o 'pronóstico mañana' y consulta Open-Meteo."""
    import requests
    texto = texto_original.lower()
    texto = _normalizar_numeros_texto(texto)   # <-- NUEVA LÍNEA: "dos días" -> "2 días"
    match_horas = re.search(r"(\d+)\s*horas?", texto)
    match_dias = re.search(r"(\d+)\s*d[ií]as?", texto)
    es_manana = "mañana" in texto or "manana" in texto

    try:
        # ---- Pedido en HORAS ----
        if match_horas:
            n = int(match_horas.group(1))
            if n > 48:
                return "El pronóstico por hora solo llega hasta 48 horas, pedime algo dentro de ese rango."

            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=32.6245&longitude=-115.4523"
                "&hourly=temperature_2m,weather_code"
                "&timezone=America%2FTijuana"
                "&forecast_days=3"
            )
            resp = requests.get(url, timeout=5)
            data = resp.json()
            horas = data["hourly"]["time"]
            temps = data["hourly"]["temperature_2m"]
            codigos = data["hourly"]["weather_code"]

            objetivo = datetime.now() + timedelta(hours=n)
            objetivo_str = objetivo.strftime("%Y-%m-%dT%H:00")

            if objetivo_str not in horas:
                return "No pude encontrar el pronóstico para ese horario."

            idx = horas.index(objetivo_str)
            temp = temps[idx]
            desc = _descripcion_clima(codigos[idx])
            return f"En {n} horas, a las {objetivo.strftime('%H:%M')}, va a haber {temp} grados, {desc}"

        # ---- Pedido en DÍAS (o "mañana") ----
        elif match_dias or es_manana:
            n = int(match_dias.group(1)) if match_dias else 1
            if n > 7:
                return "El pronóstico por día solo llega hasta 7 días, pedime algo dentro de ese rango."

            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=32.6245&longitude=-115.4523"
                "&daily=temperature_2m_max,temperature_2m_min,weather_code"
                "&timezone=America%2FTijuana"
                "&forecast_days=8"
            )
            resp = requests.get(url, timeout=5)
            data = resp.json()
            max_t = data["daily"]["temperature_2m_max"]
            min_t = data["daily"]["temperature_2m_min"]
            codigos = data["daily"]["weather_code"]

            if n >= len(max_t):
                return "No tengo pronóstico para tantos días."

            desc = _descripcion_clima(codigos[n])
            etiqueta = "mañana" if n == 1 else f"en {n} días"
            return f"Para {etiqueta} va a estar entre {int(min_t[n])} y {int(max_t[n])} grados, {desc}"

        # ---- Sin especificar: pronóstico genérico de un par de horas ----
        else:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=32.6245&longitude=-115.4523"
                "&hourly=temperature_2m,weather_code"
                "&timezone=America%2FTijuana"
                "&forecast_days=1"
            )
            resp = requests.get(url, timeout=5)
            data = resp.json()
            idx = min(datetime.now().hour + 3, 23)
            temp = data["hourly"]["temperature_2m"][idx]
            desc = _descripcion_clima(data["hourly"]["weather_code"][idx])
            return (
                f"En un par de horas va a haber {temp} grados, {desc}. "
                "Si querés algo más puntual, decime 'pronóstico en 5 horas' o 'pronóstico mañana'."
            )

    except Exception as e:
        print(f"❌ Error consultando pronóstico: {e}")
        return "No pude consultar el pronóstico, revisemos la conexión."

def obtener_clima():
    """Consulta el clima actual en Mexicali usando Open-Meteo (API gratis, sin key)."""
    import requests
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=32.6245&longitude=-115.4523"
            "&current=temperature_2m,weather_code"
            "&timezone=America%2FTijuana"
        )
        resp = requests.get(url, timeout=5)
        data = resp.json()
        temp = data["current"]["temperature_2m"]
        return f"En Mexicali hay {temp} grados ahora mismo"
    except Exception as e:
        print(f"❌ Error consultando clima: {e}")
        return "No pude consultar el clima, revisemos la conexión a internet."


def obtener_estado_pc():
    """Usa psutil para leer batería, CPU y RAM de la PC."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        bateria = psutil.sensors_battery()

        partes = [f"CPU al {cpu} por ciento", f"RAM al {ram} por ciento"]
        if bateria:
            partes.append(f"batería al {int(bateria.percent)} por ciento")

        return ", ".join(partes)
    except Exception as e:
        print(f"❌ Error leyendo estado de la PC: {e}")
        return "No pude leer el estado de la PC."
    
  
def abrir_discord():
    """
    Discord en Windows no se abre con un .exe fijo - se lanza a través
    de Update.exe con un parámetro especial. Buscamos esa ruta típica.
    """
    ruta_update = os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
    if os.path.exists(ruta_update):
        subprocess.Popen([ruta_update, "--processStart", "Discord.exe"],
                  creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    return False

def controlar_musica(accion):
    """accion: 'pausar', 'siguiente' o 'anterior'. Manda teclas de medios, funciona con cualquier reproductor activo."""
    import keyboard
    try:
        if accion == "pausar":
            keyboard.send("play/pause media")
            return "Listo"
        elif accion == "siguiente":
            keyboard.send("next track")
            return "Siguiente canción"
        elif accion == "anterior":
            import time as t
            keyboard.send("previous track")
            t.sleep(0.3)
            keyboard.send("previous track")
            return "Canción anterior"
    except Exception as e:
        print(f"❌ Error controlando música: {e}")
        return "No pude controlar la música."
    
    
# ------------------ VISIÓN POR CÁMARA ------------------

def sacar_foto_camara():
    import cv2
    camara = cv2.VideoCapture(0)
    if not camara.isOpened():
        print("❌ No pude abrir la cámara.")
        return None

    ret, frame = camara.read()
    camara.release()

    if not ret:
        print("❌ No pude capturar el frame.")
        return None

    ruta = os.path.abspath("foto_camara_jarvis.jpg")
    cv2.imwrite(ruta, frame)
    return ruta


def preguntar_con_imagen(ruta_imagen, pregunta="Describí brevemente y en 1 o 2 oraciones qué ves en esta imagen, en tono natural como si le hablaras a un amigo.", intentos=3):
    if not gemini_client:
        return "No tengo conectada la inteligencia artificial para ver imágenes, revisá la variable de entorno."

    try:
        with open(ruta_imagen, "rb") as f:
            bytes_imagen = f.read()
    except Exception as e:
        print(f"❌ Error leyendo la imagen: {e}")
        return "No pude leer la foto que saqué, probemos de nuevo."

    for intento in range(intentos):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-flash-latest",
                contents=[
                    {"inline_data": {"mime_type": "image/jpeg", "data": bytes_imagen}},
                    pregunta,
                ],
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error consultando Gemini con imagen (intento {intento + 1}/{intentos}): {e}")
            if intento < intentos - 1:
                time.sleep(1.5)

    return "El servidor de Gemini está saturado en este momento, probemos de nuevo en un rato."


def mirar_camara(texto_original):
    ruta = sacar_foto_camara()
    if not ruta:
        return "No pude acceder a la cámara, revisá que esté conectada y no la esté usando otra app."

    match = re.search(r"mir[áa] la c[áa]mara y (?:dec[íi]me|dime) (.+)", texto_original.lower())
    if match:
        pregunta = match.group(1).strip()
        return preguntar_con_imagen(ruta, pregunta)

    return preguntar_con_imagen(ruta)

    # ------------------ CONTROL DEL SISTEMA ------------------

def bloquear_pantalla():
    import ctypes
    ctypes.windll.user32.LockWorkStation()


def sacar_captura():
    from PIL import ImageGrab
    carpeta_descargas = os.path.expanduser("~/Downloads")
    nombre_archivo = f"captura_jarvis_{int(time.time())}.png"
    ruta = os.path.join(carpeta_descargas, nombre_archivo)
    captura = ImageGrab.grab()
    captura.save(ruta)

        # Lanzamos la previsualización como proceso aparte (mismo patrón que el buddy)
    try:
        if getattr(sys, "frozen", False):
            ruta_exe = os.path.join(BASE_DIR, "CapturaPreview.exe")
            subprocess.Popen([ruta_exe, ruta], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            ruta_script_preview = os.path.join(BASE_DIR, "captura_preview.py")
            subprocess.Popen([sys.executable, ruta_script_preview, ruta], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"❌ No pude abrir la previsualización: {e}")

    return nombre_archivo

def iniciar_grabacion_pantalla():
    global jarvis_grabando

    if cliente_obs is None:
        return "No tengo conexión con OBS, fijate que esté abierto."

    try:
        cliente_obs.start_record()
        jarvis_grabando = True
        print("🔴 Grabación iniciada (OBS)")
        return "Dale, arranco a grabar. Quedo en modo silencio hasta que cortes con control shift R"
    except Exception as e:
        print(f"❌ Error iniciando grabación: {e}")
        return "No pude iniciar la grabación en OBS."


def detener_grabacion_pantalla():
    global jarvis_grabando

    if cliente_obs is None:
        print("⚠️ No hay conexión con OBS.")
        return

    try:
        cliente_obs.stop_record()
        jarvis_grabando = False
        print("⏹️ Grabación detenida (OBS), Jarvis despierto de nuevo.")
    except Exception as e:
        print(f"❌ Error deteniendo grabación: {e}")

def apagar_pc(minutos):
    segundos = minutos * 60
    subprocess.run(["shutdown", "/s", "/t", str(segundos)], creationflags=subprocess.CREATE_NO_WINDOW)


def cancelar_apagado():
    subprocess.run(["shutdown", "/a"], creationflags=subprocess.CREATE_NO_WINDOW)


# ------------------ NOTAS ------------------

ARCHIVO_NOTAS = os.path.join(BASE_DIR, "jarvis_notas.txt")


def agregar_nota(texto_nota):
    with open(ARCHIVO_NOTAS, "a", encoding="utf-8") as f:
        f.write(texto_nota.strip() + "\n")


def leer_notas():
    if not os.path.exists(ARCHIVO_NOTAS):
        return "No tenés ninguna nota anotada todavía."
    with open(ARCHIVO_NOTAS, "r", encoding="utf-8") as f:
        lineas = [l.strip() for l in f.readlines() if l.strip()]
    if not lineas:
        return "No tenés ninguna nota anotada todavía."
    return "Tenés anotado: " + ", ".join(lineas)


def borrar_notas():
    if os.path.exists(ARCHIVO_NOTAS):
        os.remove(ARCHIVO_NOTAS)

# ------------------ MEMORIA PERSONAL ------------------

ARCHIVO_MEMORIA = os.path.join(BASE_DIR, "memoria.json")


def cargar_memoria():
    if not os.path.exists(ARCHIVO_MEMORIA):
        return {"cumpleaños": None, "gustos": []}
    try:
        with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"cumpleaños": None, "gustos": []}


def guardar_memoria(memoria):
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def guardar_cumpleaños(texto_original):
    match = re.search(r"cumplea[ñn]os es (.+)", texto_original.lower())
    if not match:
        return "Decime algo como 'recordá que mi cumpleaños es el 15 de marzo'."
    fecha = match.group(1).strip()
    memoria = cargar_memoria()
    memoria["cumpleaños"] = fecha
    guardar_memoria(memoria)
    return f"Listo, guardé que tu cumpleaños es {fecha}"


def guardar_gusto(texto_original):
    texto_normalizado = texto_original.lower()
    match = re.search(r"me (?:gusta|gustan|encanta|encantan|fascina|fascinan) (.+)", texto_normalizado)
    if not match:
        return "Decime algo como 'recordá que me gusta el rock'."

    # Separamos por " y " para permitir decir varios gustos en una sola frase
    gustos_nuevos = [g.strip() for g in re.split(r"\s+y\s+", match.group(1)) if g.strip()]

    memoria = cargar_memoria()
    agregados = []
    for gusto in gustos_nuevos:
        if gusto not in memoria["gustos"]:
            memoria["gustos"].append(gusto)
            agregados.append(gusto)
    guardar_memoria(memoria)

    if not agregados:
        return "Ya tenía anotado eso."
    return "Anotado: " + ", ".join(agregados)


def leer_memoria_hablada():
    memoria = cargar_memoria()
    partes = []
    if memoria.get("cumpleaños"):
        partes.append(f"tu cumpleaños es {memoria['cumpleaños']}")
    if memoria.get("gustos"):
        partes.append("te gusta " + ", ".join(memoria["gustos"]))
    if not partes:
        return "Todavía no tengo nada guardado sobre vos."
    return "Sé que " + ", y ".join(partes) + "."


def borrar_memoria():
    if os.path.exists(ARCHIVO_MEMORIA):
        os.remove(ARCHIVO_MEMORIA)


def obtener_contexto_memoria():
    """Arma un texto corto con lo guardado, para inyectarlo en el prompt de la IA."""
    memoria = cargar_memoria()
    partes = []
    if memoria.get("cumpleaños"):
        partes.append(f"El cumpleaños del usuario es {memoria['cumpleaños']}")
    if memoria.get("gustos"):
        partes.append("Le gusta: " + ", ".join(memoria["gustos"]))
    if not partes:
        return ""
    return "Datos que sabés del usuario: " + ". ".join(partes) + "."


# ------------------ INFO RÁPIDA ------------------

def calcular(texto_original):
    """Busca un patrón tipo 'N operador N' (+, -, x/por, /) y lo resuelve."""
    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(mas|más|\+|menos|-|por|x|\*|dividido|/)\s*(-?\d+(?:\.\d+)?)",
        texto_original.lower(),
    )
    if not match:
        return "Decime algo como 'cuánto es 5 más 3'."

    n1, operador, n2 = match.groups()
    n1, n2 = float(n1), float(n2)

    if operador in ("mas", "más", "+"):
        resultado = n1 + n2
    elif operador in ("menos", "-"):
        resultado = n1 - n2
    elif operador in ("por", "x", "*"):
        resultado = n1 * n2
    elif operador in ("dividido", "/"):
        if n2 == 0:
            return "No se puede dividir por cero, che."
        resultado = n1 / n2

    if resultado == int(resultado):
        resultado = int(resultado)
    return f"El resultado es {resultado}"


def traducir(texto_original):
    from deep_translator import GoogleTranslator
    match = re.search(r"dice (.+?) en (inglés|ingles|portugués|portugues|francés|frances)", texto_original.lower())
    if not match:
        return "Decime algo como 'cómo se dice hola en inglés'."

    frase, idioma = match.groups()
    idiomas = {"inglés": "en", "ingles": "en", "portugués": "pt", "portugues": "pt", "francés": "fr", "frances": "fr"}
    try:
        traduccion = GoogleTranslator(source="es", target=idiomas[idioma]).translate(frase.strip())
        return f"Se dice: {traduccion}"
    except Exception as e:
        print(f"❌ Error traduciendo: {e}")
        return "No pude traducir eso, revisemos la conexión."


def buscar_wikipedia(texto_original):
    """Consulta directo la API REST de Wikipedia en español, sin depender de la librería 'wikipedia' (abandonada)."""
    import requests

    match = re.search(r"qué es (.+)|que es (.+)|quién es (.+)|quien es (.+)", texto_original.lower())
    if not match:
        return "Preguntame algo como 'qué es la fotosíntesis'."

    termino = next(g for g in match.groups() if g).strip()

    try:
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{termino.replace(' ', '_')}"
        resp = requests.get(url, timeout=5, headers={"User-Agent": "JarvisAsistente/1.0"})

        if resp.status_code != 200:
            return f"No encontré info clara sobre {termino}."

        data = resp.json()
        extracto = data.get("extract", "")
        if not extracto:
            return f"No encontré info clara sobre {termino}."

        # Cortamos a las primeras 2 oraciones para que no sea eterno al hablarlo
        oraciones = extracto.split(". ")
        resumen = ". ".join(oraciones[:2])
        if not resumen.endswith("."):
            resumen += "."
        return resumen

    except Exception as e:
        print(f"❌ Error en Wikipedia: {e}")
        return f"No encontré info clara sobre {termino}."


# ------------------ CONTROL DE VENTANAS ------------------

def minimizar_todo():
    keyboard.send("windows+d")


def cerrar_ventana_activa():
    keyboard.send("alt+f4")


def cambiar_ventana():
    keyboard.send("alt+tab")

# ------------------ ALARMA ------------------

def parsear_hora_alarma(texto_original):
    """Busca 'alarma a las H:MM am/pm' y devuelve un datetime futuro, o None si no matchea."""
    texto = texto_original.lower()
    match = re.search(
        r"alarma a las (\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?|de la mañana|de la tarde|de la noche)?",
        texto
    )
    if not match:
        return None

    hora = int(match.group(1))
    minuto = int(match.group(2)) if match.group(2) else 0
    marca = match.group(3)

    marca_normalizada = marca.replace(".", "") if marca else ""
    es_pm = marca_normalizada in ("pm", "de la tarde", "de la noche")
    es_am = marca_normalizada in ("am", "de la mañana")

    if hora == 12 and es_am:
        hora = 0
    elif hora != 12 and es_pm:
        hora += 12

    ahora = datetime.now()
    objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    if objetivo <= ahora:
        objetivo += timedelta(days=1)

    return objetivo

def programar_alarma(objetivo):
    global alarma_activa
    alarma_activa = objetivo
    hilo = threading.Thread(target=_esperar_alarma, args=(objetivo,), daemon=True)
    hilo.start()


def _esperar_alarma(objetivo):
    global alarma_activa, alarma_sonando

    while datetime.now() < objetivo:
        if alarma_activa != objetivo:
            return  # se canceló o se reemplazó por otra alarma
        time.sleep(1)

    if alarma_activa != objetivo:
        return

    alarma_sonando = True
    hablar(f"¡Son las {objetivo.strftime('%H:%M')}! Dale, arriba, aplaudí dos veces para apagarme.")

    while alarma_sonando:
        winsound.Beep(1000, 400)
        time.sleep(0.3)

    alarma_activa = None
    
def abrir_steam():
    try:
        os.startfile("steam://open/main")
        return "Abriendo Steam"
    except Exception as e:
        print(f"❌ Error abriendo Steam: {e}")
        return "No pude abrir Steam."
    
def buscar_archivo(nombre_busqueda):
    """Busca un archivo/carpeta usando el índice de búsqueda de Windows (rápido).
    Devuelve hasta 3 resultados con su ruta completa."""
    import subprocess

    comando_powershell = (
        f'Get-ChildItem -Path "$env:USERPROFILE" -Recurse -Filter "*{nombre_busqueda}*" '
        f'-ErrorAction SilentlyContinue | Select-Object -First 3 -ExpandProperty FullName'
    )

    try:
        resultado = subprocess.run(
            ["powershell", "-Command", comando_powershell],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        rutas = [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]

        if not rutas:
            return f"No encontré nada con el nombre {nombre_busqueda}."

        if len(rutas) == 1:
            nombre_archivo = os.path.basename(rutas[0])
            return f"Encontré {nombre_archivo} en {os.path.dirname(rutas[0])}"

        nombres = [os.path.basename(r) for r in rutas]
        return f"Encontré {len(rutas)} resultados, el primero es {nombres[0]}"

    except subprocess.TimeoutExpired:
        return "La búsqueda tardó demasiado, probá con un nombre más específico."
    except Exception as e:
        print(f"❌ Error buscando archivo: {e}")
        return "No pude hacer la búsqueda."
    
pomodoro_activo = False   # para poder cancelarlo si hace falta

def traducir_pantalla():
    from PIL import ImageGrab
    import pytesseract
    from deep_translator import GoogleTranslator

    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    try:
        captura = ImageGrab.grab()
        texto_detectado = pytesseract.image_to_string(captura, lang="eng").strip()
    except Exception as e:
        print(f"❌ Error en captura/OCR: {e}")
        return "No pude leer la pantalla."

    if not texto_detectado:
        return "No detecté texto en la pantalla ahora mismo."

    # Filtro de calidad: si el texto es puro ruido (símbolos, muy poca letra real),
    # ni intentamos traducir
    letras = sum(c.isalpha() for c in texto_detectado)
    if letras < len(texto_detectado) * 0.4 or letras < 5:
        return "Lo que veo en pantalla es demasiado ruido para traducir, probá con texto más claro."

    texto_detectado = texto_detectado[:500]

    try:
        traduccion = GoogleTranslator(source="en", target="es").translate(texto_detectado)
        return f"Esto dice en la pantalla: {traduccion}"
    except Exception as e:
        print(f"❌ Error traduciendo (servicio): {e}")
        return "El traductor no pudo procesar ese texto, probá con algo más claro en pantalla."
    
def iniciar_pomodoro(texto_original, duracion_default=25):
    global pomodoro_activo

    texto_normalizado = _normalizar_numeros_texto(texto_original.lower())
    match_horas = re.search(r"pomodoro de (\d+)\s*horas?", texto_normalizado)
    match_minutos = re.search(r"pomodoro de (\d+)(?:\s*minutos?)?", texto_normalizado)

    if match_horas:
        minutos = int(match_horas.group(1)) * 60
    elif match_minutos:
        minutos = int(match_minutos.group(1))
    else:
        minutos = duracion_default

    if minutos <= 0 or minutos > 180:
        return "Decime un número de minutos que tenga sentido, entre 1 y 180."

    pomodoro_activo = True
    hilo = threading.Thread(target=_correr_pomodoro, args=(minutos,), daemon=True)
    hilo.start()

    return f"Pomodoro de {minutos} minutos arrancado, dale para adelante"

def programar_recordatorio(texto_original):
    """Parsea 'recordame/recuérdame/recordarme en N minutos/horas (que) <mensaje>' y agenda el aviso."""
    texto_normalizado = _normalizar_numeros_texto(texto_original.lower())
    texto_normalizado = (
        texto_normalizado
        .replace("recuérdame", "recordame")
        .replace("recuerdame", "recordame")
        .replace("recordarme", "recordame")
    )

    match = re.search(
        r"recordame en (\d+)\s*(minutos?|horas?)\s*(?:que\s*)?(.+)",
        texto_normalizado
    )

    if not match:
        return "Decime algo como 'recordame en 30 minutos que tengo que estudiar'."

    cantidad, unidad, mensaje = match.groups()
    cantidad = int(cantidad)
    segundos = cantidad * 60 if "minuto" in unidad else cantidad * 3600

    if segundos <= 0 or segundos > 24 * 3600:
        return "Decime un tiempo que tenga sentido, hasta 24 horas."

    hilo = threading.Thread(target=_avisar_recordatorio, args=(segundos, mensaje.strip()), daemon=True)
    hilo.start()

    if "minuto" in unidad:
        unidad_legible = "minuto" if cantidad == 1 else "minutos"
    else:
        unidad_legible = "hora" if cantidad == 1 else "horas"
    return f"Listo, en {cantidad} {unidad_legible} te recuerdo: {mensaje.strip()}"

def _avisar_recordatorio(segundos, mensaje):
    time.sleep(segundos)
    winsound.Beep(1000, 250)
    time.sleep(0.15)
    winsound.Beep(1000, 250)
    hablar(f"Recordatorio: {mensaje}")

def _correr_pomodoro(minutos):
    global pomodoro_activo
    time.sleep(minutos * 60)

    if not pomodoro_activo:
        return  # se canceló antes de terminar

    pomodoro_activo = False
    winsound.Beep(1200, 300)
    time.sleep(0.2)
    winsound.Beep(1200, 300)
    hablar(f"Se cumplieron los {minutos} minutos del pomodoro, tomate un descanso")


def cancelar_pomodoro():
    global pomodoro_activo
    if pomodoro_activo:
        pomodoro_activo = False
        return "Pomodoro cancelado"
    return "No tenés ningún pomodoro corriendo"    

def mostrar_spotify_actual():
    try:
        if getattr(sys, "frozen", False):
            ruta_exe = os.path.join(BASE_DIR, "SpotifyPreview.exe")
            subprocess.Popen([ruta_exe], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            ruta_script = os.path.join(BASE_DIR, "spotify_preview.py")
            subprocess.Popen([sys.executable, ruta_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"❌ No pude abrir la previsualización de Spotify: {e}")

def procesar_comando(texto):
    global verificacion_voz_activa
    texto_original = texto
    texto = texto.lower()
    texto_sin_tildes = texto.translate(str.maketrans("áéíóú", "aeiou"))

    # ---- Comandos exactos / muy específicos primero ----
    if texto.strip() in ["hola", "hola jarvis", "buenas", "qué onda", "que onda"]:
        hablar("Hola, ¿en qué te ayudo?")
        
    elif "alarma" in texto:
        objetivo = parsear_hora_alarma(texto_original)
        if objetivo:
            programar_alarma(objetivo)
            hablar(f"Listo, alarma puesta para las {objetivo.strftime('%H:%M')}")
        else:
            hablar("Decime algo como 'alarma a las 6:00 am'.")
            
    elif "pomodoro" in texto and ("cancelá" in texto or "cancela" in texto):
        hablar(cancelar_pomodoro())

    elif "pomodoro" in texto:
        hablar(iniciar_pomodoro(texto_original))    
        
    elif "recordame" in texto or "recuérdame" in texto or "recuerdame" in texto or "recordarme" in texto:
        hablar(programar_recordatorio(texto_original))  
        
    elif "modo no molestar" in texto and not any(palabra in texto for palabra in ["desactivá", "desactiva", "apagá", "apaga", "quitá", "quita"]):
        activar_no_molestar()
        hablar("Listo, activo el modo no molestar. Para desactivarlo apretá Alt Shift A.")
                
    elif "activá el reconocimiento de voz" in texto or "activa el reconocimiento de voz" in texto or "activá la verificación de voz" in texto or "activa la verificacion de voz" in texto:
        verificacion_voz_activa = True
        _guardar_estado_verificacion(True)
        hablar("Listo, reconocimiento de voz activado. Ahora solo te voy a escuchar a vos.")

    elif "desactivá el reconocimiento de voz" in texto or "desactiva el reconocimiento de voz" in texto or "desactivá la verificación de voz" in texto or "desactiva la verificacion de voz" in texto:
        verificacion_voz_activa = False
        _guardar_estado_verificacion(False)
        hablar("Listo, reconocimiento de voz desactivado. Ahora cualquiera puede darme comandos.")
        
    elif "que suena" in texto_sin_tildes or "que esta sonando" in texto_sin_tildes:
        mostrar_spotify_actual()

    elif re.search(r"\bhora\b", texto):
        hora_actual = time.strftime("%H:%M")
        hablar(f"Son las {hora_actual}")
        
    elif "apágate" in texto or "apagate" in texto or "salí" in texto or "sali" in texto or "salir" in texto:
        hablar("Listo, nos vemos.")
        return False

    elif "cumpleaños" in texto and ("recordá" in texto or "recorda" in texto):
        hablar(guardar_cumpleaños(texto_original))

    elif ("me gusta" in texto or "me gustan" in texto or "me encanta" in texto or "me encantan" in texto or "me fascina" in texto or "me fascinan" in texto) and ("recordá" in texto or "recorda" in texto or "recuerda" in texto):
        hablar(guardar_gusto(texto_original))

    elif "qué sabés de mí" in texto or "que sabes de mi" in texto or "qué sabes de mí" in texto:
        hablar(leer_memoria_hablada())

    elif "olvidá todo lo que sabés de mí" in texto or "olvida todo lo que sabes de mi" in texto:
        borrar_memoria()
        hablar("Listo, borré todo lo que sabía de vos.")

    # ---- Notas (estructurados, van antes que "anota" suelto) ----
    elif "qué tengo anotado" in texto or "que tengo anotado" in texto:
        hablar(leer_notas())

    elif "borrá las notas" in texto or "borra las notas" in texto:
        borrar_notas()
        hablar("Listo, borré todas las notas")

    elif re.search(r"\banotá\b|\banota\b", texto):
        nota = texto_original.lower()
        nota = re.sub(r"\banotá\b|\banota\b", "", nota).strip()
        if nota:
            agregar_nota(nota)
            hablar("Anotado")
        else:
            hablar("¿Qué querés que anote?")

    # ---- Calculadora, traductor, wikipedia (estructurados) ----
    elif re.search(r"\d+\s*(mas|más|\+|menos|por|x|dividido)\s*\d+", texto):
        hablar(calcular(texto_original))

    elif "traducí la pantalla" in texto or "traduci la pantalla" in texto or "traducí pantalla" in texto or "traduci pantalla" in texto or "traduce la pantalla" in texto or "traduce pantalla" in texto or "traducir la pantalla" in texto or "traducir pantalla" in texto:
        hablar(traducir_pantalla())
        
    elif re.search(r"se dice|dice.+en (inglés|ingles|portugués|portugues|francés|frances)", texto):
        hablar(traducir(texto_original))

    elif "qué es" in texto or "que es" in texto or "quién es" in texto or "quien es" in texto:
        hablar(buscar_wikipedia(texto_original))

    elif "mirá la cámara" in texto or "mira la cámara" in texto or "voltéate a ver" in texto or "voltéame a ver" in texto or "volteate a ver" in texto or "volteame a ver" in texto or "mirame" in texto or "mírame" in texto:
        hablar(mirar_camara(texto_original))
        
    # ---- Apps (una sola palabra, van después de todo lo específico) ----
    elif "spotify" in texto:
        hablar("Abriendo Spotify")
        try:
            subprocess.Popen(["spotify"], creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError:
            hablar("No encontré Spotify en el PATH.")

    elif "youtube" in texto or "you tube" in texto or "yutub" in texto:
        hablar("Abriendo YouTube")
        import webbrowser
        webbrowser.open("https://youtube.com")

    elif "netflix" in texto:
        hablar("Abriendo Netflix")
        import webbrowser
        webbrowser.open("https://netflix.com")

    elif "vs code" in texto or "visual studio" in texto:
        hablar("Abriendo VS Code")
        try:
            subprocess.Popen(["code"], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError:
            hablar("No encontré VS Code en el PATH.")

    elif "discord" in texto:
        hablar("Abriendo Discord")
        if not abrir_discord():
            hablar("No encontré Discord instalado en la ruta esperada.")

    elif "whatsapp" in texto or "whats app" in texto:
        hablar(abrir_whatsapp())

    elif "osu" in texto or "osu!" in texto or "oso" in texto or "osú" in texto or "osú!" in texto or "osu!mania" in texto:
        hablar(abrir_osu())

    elif "geometry dash" in texto or "geometry" in texto:
        hablar(abrir_geometry_dash())

    elif "minecraft" in texto:
        hablar(abrir_minecraft())

    elif "garry's mod" in texto or "garrys mod" in texto or "gmod" in texto:
        hablar(abrir_gmod())
    
    elif "steam" in texto:
        hablar(abrir_steam())    

    elif "claude" in texto:
        hablar(abrir_claude_app())

    elif re.search(r"\bobs\b", texto):
        hablar(abrir_obs())

    elif "blender" in texto:
        hablar(abrir_blender())

    elif "unity" in texto:
        hablar(abrir_unity())

    # ---- Música ----
    elif "pausá" in texto or "pausa" in texto or "reproducí" in texto or "reproduci" in texto or "reproduce" in texto or "play" in texto:
        hablar(controlar_musica("pausar"))

    elif "siguiente canción" in texto or "siguiente cancion" in texto or "próxima canción" in texto or "proxima cancion" in texto:
        hablar(controlar_musica("siguiente"))

    elif "canción anterior" in texto or "cancion anterior" in texto:
        hablar(controlar_musica("anterior"))

    # ---- Volumen ----
    # ---- Volumen a nivel específico (va ANTES de las reglas genéricas de subir/bajar) ----
    elif re.search(r"volumen al (\d+)|volumen a (\d+)|(\d+)\s*(por ciento|%)\s*(el volumen|de volumen)?", texto):
        match_vol = re.search(r"(\d+)", texto)
        if match_vol:
            nivel = int(match_vol.group(1))
            hablar(controlar_volumen("nivel", nivel))
        else:
            hablar("No te entendí el número.")

    elif "volumen al máximo" in texto or "volumen al maximo" in texto or "volumen a tope" in texto:
        hablar(controlar_volumen("nivel", 100))

    elif "subí el volumen" in texto or "sube el volumen" in texto or "más volumen" in texto:
        hablar(controlar_volumen("subir"))
        
    elif "subí el volumen" in texto or "sube el volumen" in texto or "más volumen" in texto:
        hablar(controlar_volumen("subir"))
    
    elif "bajá el volumen" in texto or "baja el volumen" in texto or "menos volumen" in texto:
        hablar(controlar_volumen("bajar"))
        
    elif "mutea el micrófono" in texto or "mutea el microfono" in texto or "silenciá el micrófono" in texto or "silencia el microfono" in texto:
                hablar(mutear_microfono())    
                
    elif "silenciá" in texto or "silencia" in texto or "mute" in texto:
        hablar(controlar_volumen("silenciar"))
            
    # ---- Clima y estado PC ----
    elif "pronóstico" in texto or "pronostico" in texto:
        hablar(obtener_pronostico(texto_original))
        
    elif "clima" in texto:
        hablar(obtener_clima())

    elif "batería" in texto or "bateria" in texto or "estado de la pc" in texto or "cpu" in texto:
        hablar(obtener_estado_pc())
        
    elif "noticias" in texto:
        hablar(obtener_noticias(texto_original))    

    # ---- Sistema ----
    elif "bloqueá la pantalla" in texto or "bloquea la pantalla" in texto:
        hablar("Bloqueando pantalla")
        bloquear_pantalla()

    elif "captura" in texto:
        nombre = sacar_captura()
        hablar("Guardé la captura en descargas")
        
    elif "grabá pantalla" in texto or "graba pantalla" in texto or "grabá la pantalla" in texto or "graba la pantalla" in texto:
        respuesta = iniciar_grabacion_pantalla()
        hablar(respuesta)

    elif "apagá la pc" in texto or "apaga la pc" in texto:
        match_min = re.search(r"(\d+) minuto", texto)
        minutos = int(match_min.group(1)) if match_min else 1
        hablar(f"Apagando la PC en {minutos} minutos. Decime cancelá si te arrepentís.")
        apagar_pc(minutos)

    elif "cancelá" in texto or "cancela" in texto:
        cancelar_apagado()
        hablar("Cancelado")

    elif "cerrá todo" in texto or "cerra todo" in texto or "cierra todo" in texto:
        hablar(cerrar_todo())
        
    # ---- Ventanas ----
    elif "escritorio" in texto:
        hablar("Listo")
        minimizar_todo()

    elif "cerrá esta ventana" in texto or "cerra esta ventana" in texto:
        hablar("Cerrando")
        cerrar_ventana_activa()

    elif "cambiá de ventana" in texto or "cambia de ventana" in texto:
        cambiar_ventana()
        
    elif re.search(r"busc[áa] (el archivo|la carpeta|el|la) (.+)", texto):
        match_busqueda = re.search(r"busc[áa] (?:el archivo|la carpeta|el|la) (.+)", texto)
        termino = match_busqueda.group(1).strip()
        hablar(buscar_archivo(termino))
    else:
        respuesta = preguntar_a_ia(texto_original)
        hablar(respuesta)
    return True

def obtener_noticias(texto_original):
    """Lee titulares desde el RSS de Google Noticias. Si detecta un tema
    después de 'de', busca sobre ese tema; si no, trae lo general del día."""
    import requests
    import xml.etree.ElementTree as ET

    match_tema = re.search(r"noticias de (.+)", texto_original.lower())

    try:
        if match_tema:
            tema = match_tema.group(1).strip()
            url = f"https://news.google.com/rss/search?q={tema}&hl=es-419&gl=MX&ceid=MX:es-419"
        else:
            url = "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419"

        resp = requests.get(url, timeout=6)
        raiz = ET.fromstring(resp.content)
        items = raiz.findall(".//item")[:3]

        if not items:
            return "No encontré noticias sobre eso."

        titulares = []
        for item in items:
            titulo = item.find("title").text
            # Google News agrega " - Fuente" al final del título, se lo sacamos para que suene más natural hablado
            titulo_limpio = titulo.rsplit(" - ", 1)[0]
            titulares.append(titulo_limpio)

        intro = f"Esto encontré sobre {tema}: " if match_tema else "Estas son las noticias más importantes: "
        return intro + ". ".join(titulares)

    except Exception as e:
        print(f"❌ Error consultando noticias: {e}")
        return "No pude consultar las noticias, revisemos la conexión."

def abrir_whatsapp():
    try:
        os.startfile("whatsapp:")
        return "Abriendo WhatsApp"
    except Exception as e:
        print(f"❌ Error abriendo WhatsApp: {e}")
        return "No pude abrir WhatsApp."


def abrir_osu():
    rutas = [
        r"C:\Users\PC PRIDE WHALE\AppData\Local\osulazer\current\osu!.exe",
    ]
    return abrir_programa(rutas, "Osu")


def abrir_geometry_dash():
    try:
        os.startfile("steam://rungameid/322170")
        return "Abriendo Geometry Dash"
    except Exception as e:
        print(f"❌ Error abriendo Geometry Dash: {e}")
        return "No pude abrir Geometry Dash."


def abrir_minecraft():
    ruta = r"C:\Users\PC PRIDE WHALE\OneDrive\Desktop\SKlauncher-3.2.18.jar"
    if os.path.exists(ruta):
        subprocess.Popen(["javaw", "-jar", ruta], creationflags=subprocess.CREATE_NO_WINDOW)
        return "Abriendo Minecraft"
    return "No encontré el SKlauncher, revisá la ruta en el código."


def abrir_gmod():
    try:
        os.startfile("steam://rungameid/4000")
        return "Abriendo Garry's Mod"
    except Exception as e:
        print(f"❌ Error abriendo Garry's Mod: {e}")
        return "No pude abrir Garry's Mod."


def abrir_claude_app():
    ruta = r"C:\Users\PC PRIDE WHALE\OneDrive\Desktop\Claude.lnk"
    if os.path.exists(ruta):
        try:
            os.startfile(ruta)
            return "Abriendo Claude"
        except Exception as e:
            print(f"❌ Error abriendo Claude: {e}")
            return "No pude abrir Claude."
    return "No encontré Claude instalado en las rutas que tengo, revisá la ruta en el código."



def abrir_obs():
    ruta_exe = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
    carpeta_obs = os.path.dirname(ruta_exe)
    if os.path.exists(ruta_exe):
        subprocess.Popen(
            [ruta_exe],
            cwd=carpeta_obs,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "Abriendo OBS Studio"
    return "No encontré OBS Studio instalado en las rutas que tengo, revisá la ruta en el código."

def abrir_blender():
    rutas = [r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"]  # AJUSTAR si el nombre de carpeta difiere
    return abrir_programa(rutas, "Blender")


def abrir_unity():
    rutas = [
        r"C:\Program Files\Unity Hub\Unity Hub.exe",
        r"C:\Program Files\Unity\Hub\Editor\Unity Hub.exe",
    ]
    return abrir_programa(rutas, "Unity Hub")

def abrir_programa(rutas_posibles, nombre_amigable):
    """Prueba una lista de rutas candidatas y abre la primera que exista.
    Si ninguna existe, avisa para que ajustes la ruta real."""
    for ruta in rutas_posibles:
        ruta_expandida = os.path.expandvars(ruta)
        if os.path.exists(ruta_expandida):
            subprocess.Popen([ruta_expandida], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Abriendo {nombre_amigable}"
    return f"No encontré {nombre_amigable} instalado en las rutas que tengo, revisá la ruta en el código."

def activar_por_teclado():
    """Callback del atajo de teclado. Corre en un hilo aparte para no
    bloquear el hilo interno de la librería 'keyboard'."""
    if jarvis_ocupado or jarvis_grabando or alarma_sonando:
        print("⌨️  Atajo presionado, pero Jarvis ya está ocupado. Ignorado.")
        return
    threading.Thread(target=on_jarvis_activated, daemon=True).start()

def on_jarvis_activated():
    global jarvis_ocupado, last_activation
    jarvis_ocupado = True
    try:
        print("\n🔵 ¡JARVIS ACTIVADO!\n")
        texto = escuchar_comando()
        if texto:
            seguir = procesar_comando(texto)
            if not seguir:
                raise KeyboardInterrupt
    finally:
        jarvis_ocupado = False
        last_activation = time.time()
        actualizar_estado("grabando" if jarvis_grabando else "dormido")

def activar_no_molestar():
    global modo_no_molestar
    modo_no_molestar = True
    print("🔕 Modo no molestar activado.")
    actualizar_estado("dormido")

def desactivar_no_molestar():
    global modo_no_molestar
    modo_no_molestar = False
    print("🔔 Modo no molestar desactivado.")
    actualizar_estado("idle")

def audio_callback(indata, frames, time_info, status):
    global last_clap_time, clap_count, last_activation
    global was_above_threshold, activation_pending, zi_filtro, jarvis_ocupado
    global last_edge_time, alarma_sonando, jarvis_grabando, modo_no_molestar

    if status:
        print(status)

    señal_filtrada, zi_filtro = lfilter(b_filtro, a_filtro, indata[:, 0], zi=zi_filtro)
    volume = np.sqrt(np.mean(señal_filtrada**2))

    now = time.time()

    if modo_no_molestar:
        was_above_threshold = False
        return

    if (jarvis_ocupado or jarvis_grabando) and not alarma_sonando:
        was_above_threshold = False
        return

    is_above = volume > CLAP_THRESHOLD

    if now - last_activation < COOLDOWN:
        was_above_threshold = is_above
        return

    if is_above and not was_above_threshold:
        print(f"🔍 FLANCO detectado | t={now:.3f} | volume={volume:.4f} | clap_count antes={clap_count}")

        if now - last_edge_time < EDGE_DEBOUNCE:
            print(f"   ⛔ Descartado por debounce (gap={now - last_edge_time:.3f}s)")
            was_above_threshold = is_above
            return
        last_edge_time = now

        if clap_count == 0:
            clap_count = 1
            last_clap_time = now
        elif now - last_clap_time <= CLAP_WINDOW:
            clap_count = 0
            last_activation = now
            if alarma_sonando:
                alarma_sonando = False
            else:
                activation_pending = True
        else:
            clap_count = 1
            last_clap_time = now

    if clap_count == 1 and (now - last_clap_time) > CLAP_WINDOW:
        clap_count = 0

    was_above_threshold = is_above


def main():
    global activation_pending, CLAP_THRESHOLD

    CLAP_THRESHOLD = calibrar_umbral()

    print("🎤 Jarvis está escuchando... aplaudí 2 veces para activarlo (Ctrl+C para salir)")
    print(f"   Umbral de detección: {CLAP_THRESHOLD}\n")
    
    keyboard.add_hotkey('ctrl+shift+r', detener_grabacion_pantalla)
    keyboard.add_hotkey('ctrl+shift+j+0', activar_por_teclado)   # <-- NUEVA LÍNEA
    keyboard.add_hotkey('alt+shift+a', desactivar_no_molestar)   # <-- NUEVA LÍNEA
    threading.Thread(target=_latido_estado, daemon=True).start()   # <-- NUEVA LÍNEA
    actualizar_estado("dormido")   # <-- NUEVA LÍNEA
    iniciar_buddy()
    try:
        with sd.InputStream(
            channels=CHANNELS,
            samplerate=RATE,
            blocksize=CHUNK,
            callback=audio_callback,
        ):
            while True:
                if activation_pending:
                    activation_pending = False
                    on_jarvis_activated()
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n👋 Jarvis apagado. ¡Nos vemos!")


if __name__ == "__main__":
    main()