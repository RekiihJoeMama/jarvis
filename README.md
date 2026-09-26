# Jarvis 🎙️

Asistente de voz personal para Windows, escrito en Python e inspirado en el Jarvis de Iron Man. Se activa con doble aplauso (o un atajo de teclado) y controla la PC, responde preguntas y automatiza tareas, todo por voz.

Empezó como proyecto de aprendizaje y hoy tiene uso real diario: control manos libres durante partidas, alarmas para despertarse, y un asistente conversacional de respaldo múltiple que casi nunca se queda sin poder responder.

## ✨ Funcionalidades

### Activación
- **Doble aplauso** — detección vía `sounddevice`, con filtro pasa-altos/IIR y calibración adaptativa de umbral (corrige falsos positivos).
- **Atajo de teclado** `Ctrl+Shift+J+0` — activa a Jarvis sin necesidad de aplaudir, corre en un hilo aparte para no bloquear otros atajos.
- Si está sonando una alarma, el doble aplauso la apaga en vez de activar un comando nuevo.

### 🗣️ Comandos de voz

| Categoría | Ejemplos |
|---|---|
| Saludo / control | "hola", "salí" |
| Alarmas y recordatorios | "alarma a las 6:00 am", "recordame en 2 horas que tengo que estudiar" |
| Notas | "anotá...", "qué tengo anotado", "borrá las notas" |
| Calculadora | "cuánto es 5 más 3" (+, −, x, ÷) |
| Traductor | "cómo se dice hola en inglés" (inglés/portugués/francés); "traduci la pantalla" (OCR + traducción de lo que ve) |
| Wikipedia | "qué es la fotosíntesis", "quién es Einstein" |
| Apps | Spotify, YouTube, Netflix, VS Code, Discord, Osu!, Minecraft, Claude, Steam, Geometry Dash, Garry's Mod, WhatsApp, OBS Studio, Blender, Unity |
| Música | "pausá" / "reproducí", "siguiente canción", "canción anterior" |
| Volumen | "volumen al 50", "a tope", "subí/bajá el volumen", "silenciá", "mutea el micrófono" |
| Clima | "clima", "pronóstico en x horas/días", "pronóstico mañana" |
| Noticias | "dame noticias" (general o "de [tema]") |
| Archivos | "buscá [tal cosa]" |
| Pomodoro | "pomodoro de x minutos" |
| Estado del sistema | "batería", "cpu", "estado de la pc" |
| Sistema | "bloqueá la pantalla", "captura" (con previsualización), "apagá la pc [en x minutos]", "cancelá" |
| Ventanas | "escritorio" (minimizar todo), "cerrá esta ventana", "cambiá de ventana", "cerrá todo" (respeta ventanas protegidas: consola de Jarvis, VS Code, JarvisBuddy) |
| Memoria personal | "recordá que mi cumpleaños es...", "recordá que me gusta...", "qué sabés de mí", "olvidá todo lo que sabés de mí" |
| Visión por cámara | "mirá la cámara" / "mirame" — describe lo que ve, o respondé algo puntual sobre la imagen |
| Modo no molestar | "modo no molestar" para activar por voz; `Alt+Shift+A` para desactivar (a propósito, solo por atajo) |
| Verificación de hablante | activable/desactivable por voz o desde `settings.py` |

### 🤖 IA conversacional — cascada de 3 proveedores

Cualquier consulta libre que no matchee un comando puntual sigue esta cadena:

1. **Groq** (`gpt-oss-120b`) — primera opción, rápido y gratis.
2. **OpenRouter** — si Groq falla, con 3 modelos de respaldo internos.
3. **Gemini** — red de seguridad final, y el único proveedor con capacidad de visión (usado para los comandos de cámara).

El usuario no nota la diferencia al hablar; el sistema decide solo cuál responde.

### 🎥 Otras integraciones

- **Grabación de pantalla** — OBS Studio vía `obsws-python`, atajo global `Ctrl+Shift+R` para cortar. Jarvis se silencia mientras graba. OBS debe estar abierto antes de arrancar Jarvis.
- **Vista previa de Spotify** — mini ventana con carátula, título y artista vía SMTC.
- **JarvisBuddy** — sprite pixel art que camina por el escritorio, con estados visuales (hablando, escuchando, grabando), (yo lo dibuje xd).
- **Autoarranque** — se registra en el arranque de Windows y corre en segundo plano.

## 🛠️ Tecnologías

- **Runtime:** Python 3.14
- **Audio y voz:** `sounddevice`, `scipy` (filtro Butterworth), `edge-tts`, `ffplay`, `resemblyzer`
- **Automatización:** `keyboard`, `pycaw`, `psutil`, `winreg`, `winsound`
- **Integraciones:** `obsws-python` (OBS Studio), `pytesseract` + `deep_translator` (OCR/traducción)
- **UI:** `tkinter` (panel de configuración)
- **APIs:** Groq, OpenRouter, Google Gemini (capa gratuita), Google Speech Recognition, Open-Meteo
- **Empaquetado:** PyInstaller

## 📦 Instalación

```bash
git clone https://github.com/RekiihJoeMama/jarvis.git
cd jarvis
pip install -r requirements.txt
```

### Requisitos externos

- **FFmpeg** — necesario para la reproducción de voz con `ffplay`.
- **OBS Studio** (opcional) — solo si vas a usar la grabación de pantalla. Tiene que estar abierto y con el WebSocket habilitado *antes* de arrancar Jarvis.
- **Tesseract OCR** (opcional) — solo si vas a usar el traductor de pantalla.

### Variables de entorno

Creá un archivo `.env` (nunca lo subas, ya está en `.gitignore`) con:

```
GEMINI_API_KEY=tu_api_key_de_gemini
GROQ_API_KEY=tu_api_key_de_groq
OPENROUTER_API_KEY=tu_api_key_de_openrouter
OBS_WEBSOCKET_PASSWORD=tu_password_de_obs
```

## ▶️ Uso

```bash
python Jarvis.py
```

Aplaudí dos veces (o usá `Ctrl+Shift+J+0`) para activarlo y decile un comando — la lista completa está en la sección de Funcionalidades. Mientras está procesando o respondiendo, el ícono de estado (`jarvis_ocupado`) evita que un aplauso de fondo lo reactive por error.

Desde `settings.py` podés activar/desactivar el autoarranque, la verificación de hablante, y ver el estado en vivo del asistente.

## 📜 Historial de versiones

- **v2.2** (11/9/26) — Cascada de 3 IAs, atajo de teclado, comando "cerrá todo", memoria personal, visión por webcam.
- **v2.1.1** (9/9/26) — Noticias, búsqueda de archivos por voz, pomodoro, recordatorios con fecha, Spotify más prolijo, traductor de pantalla, toggle de reconocimiento de voz.
- **v2.1** (8/9/26) — Previsualización de capturas, 10 apps nuevas, pronóstico del clima.
- **v1.x** — Núcleo funcional: activación por aplauso, comandos básicos, alarmas, TTS, verificación de hablante, grabación con OBS, JarvisBuddy, empaquetado con PyInstaller.

## 🗺️ Roadmap

- [ ] Fuzzy matching para tolerar más variantes de transcripción de voz
- [ ] Recarga en caliente de `settings.py` sin reiniciar
- [ ] Memoria de contexto entre comandos dentro de una misma conversación
- [ ] Revisar proveedores gratuitos alternativos con visión, si la cuota de Gemini algún día queda corta

## 🚫 Descartado / Pausado (con motivo)

- **Wake-word (Picovoice Porcupine)** — descartado: implicaría un modelo corriendo todo el tiempo en paralelo, más carga de CPU y riesgo de falsos positivos. El combo aplauso + atajo ya cubre bien los casos de uso.
- **Persistencia de alarma en disco** — descartado: no se usan auriculares al dormir, así que la alarma no cumpliría su función igual.
- **Autocargar el último save de un juego** — pausado: no hay forma universal de decirle a un juego "cargá tal save" desde afuera.

## ⚠️ Limitaciones conocidas

- La transcripción por voz a veces falla con comandos poco comunes (fuzzy matching pendiente).
- OBS debe estar abierto antes de iniciar Jarvis; la conexión WebSocket se intenta una sola vez al arrancar.

## 📄 Licencia

Proyecto personal de aprendizaje. Podés usarlo y modificarlo libremente citando la fuente.