"""
JARVIS - Settings
=====================
Ventanita simple para activar/desactivar que Jarvis arranque
solo con Windows, y para activar/desactivar el reconocimiento de voz.
Usa el Registro de Windows (HKCU / .../ Run) y un archivo JSON local.
"""
import tkinter as tk
from tkinter import messagebox
import winreg
import os
import json

NOMBRE_ENTRADA = "Jarvis"
RUTA_EXE = r"C:\Users\PC PRIDE WHALE\AppData\Roaming\.minecraft\config\jarvis\dist\Jarvis_silencioso.exe"

CLAVE_REGISTRO = r"Software\Microsoft\Windows\CurrentVersion\Run"

CARPETA_DIST = os.path.dirname(RUTA_EXE)
RUTA_CONFIG_VOZ = os.path.join(CARPETA_DIST, "config_voz.json")


def autostart_activo():
    """Revisa si ya existe la entrada en el Registro. Devuelve True/False."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO, 0, winreg.KEY_READ) as clave:
            winreg.QueryValueEx(clave, NOMBRE_ENTRADA)
            return True
    except FileNotFoundError:
        return False


def activar_autostart():
    """Crea la entrada en el Registro para que Jarvis arranque con Windows."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO, 0, winreg.KEY_SET_VALUE) as clave:
        winreg.SetValueEx(clave, NOMBRE_ENTRADA, 0, winreg.REG_SZ, f'"{RUTA_EXE}"')


def desactivar_autostart():
    """Borra la entrada del Registro."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.DeleteValue(clave, NOMBRE_ENTRADA)
    except FileNotFoundError:
        pass  # ya estaba desactivado, no hay drama


def verificacion_voz_activa():
    """Lee si la verificación de voz está activa desde el JSON. Por defecto: activa."""
    if os.path.exists(RUTA_CONFIG_VOZ):
        try:
            with open(RUTA_CONFIG_VOZ, "r", encoding="utf-8") as f:
                return json.load(f).get("verificacion_activa", True)
        except Exception:
            return True
    return True


def guardar_estado_verificacion_voz(activa):
    """Escribe el nuevo estado en el JSON."""
    try:
        with open(RUTA_CONFIG_VOZ, "w", encoding="utf-8") as f:
            json.dump({"verificacion_activa": activa}, f)
    except Exception as e:
        messagebox.showerror("Error", f"No pude guardar la configuración de voz:\n{e}")


def on_toggle_autostart():
    if var_autostart.get():
        activar_autostart()
        label_estado_autostart.config(text="Jarvis va a arrancar con Windows", fg="green")
    else:
        desactivar_autostart()
        label_estado_autostart.config(text="Jarvis NO arranca con Windows", fg="gray")


def on_toggle_voz():
    if var_voz.get():
        guardar_estado_verificacion_voz(True)
        label_estado_voz.config(text="Jarvis solo te escucha a vos", fg="green")
    else:
        guardar_estado_verificacion_voz(False)
        label_estado_voz.config(text="Jarvis escucha a cualquiera", fg="gray")


# ------------------ INTERFAZ ------------------

ventana = tk.Tk()
ventana.title("Jarvis - Configuración")
ventana.geometry("350x230")
ventana.resizable(False, False)

if not os.path.exists(RUTA_EXE):
    messagebox.showwarning(
        "Aviso",
        f"No encontré el .exe en:\n{RUTA_EXE}\n\nRevisá la ruta antes de activar el autostart."
    )

tk.Label(ventana, text="Jarvis - Configuración", font=("Segoe UI", 12, "bold")).pack(pady=10)

# ---- Autostart ----
var_autostart = tk.BooleanVar(value=autostart_activo())

check_autostart = tk.Checkbutton(
    ventana,
    text="Iniciar Jarvis con Windows",
    variable=var_autostart,
    command=on_toggle_autostart,
    font=("Segoe UI", 10),
)
check_autostart.pack(pady=5)

texto_inicial_autostart = "Jarvis va a arrancar con Windows" if var_autostart.get() else "Jarvis NO arranca con Windows"
color_inicial_autostart = "green" if var_autostart.get() else "gray"
label_estado_autostart = tk.Label(ventana, text=texto_inicial_autostart, font=("Segoe UI", 9), fg=color_inicial_autostart)
label_estado_autostart.pack(pady=5)

# ---- Reconocimiento de voz ----
var_voz = tk.BooleanVar(value=verificacion_voz_activa())

check_voz = tk.Checkbutton(
    ventana,
    text="Reconocimiento de voz (solo vos)",
    variable=var_voz,
    command=on_toggle_voz,
    font=("Segoe UI", 10),
)
check_voz.pack(pady=5)

texto_inicial_voz = "Jarvis solo te escucha a vos" if var_voz.get() else "Jarvis escucha a cualquiera"
color_inicial_voz = "green" if var_voz.get() else "gray"
label_estado_voz = tk.Label(ventana, text=texto_inicial_voz, font=("Segoe UI", 9), fg=color_inicial_voz)
label_estado_voz.pack(pady=5)

ventana.mainloop()