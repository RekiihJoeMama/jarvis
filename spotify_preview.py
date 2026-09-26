import sys
import os

if sys.stdout is None or sys.stderr is None:
    log_dir = os.path.join(os.getenv('APPDATA'), '.minecraft', 'config', 'jarvis', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'spotify_preview_log.txt')
    log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file

def obtener_ruta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = obtener_ruta_base()
"""

JARVIS - Previsualizador de "qué está sonando" en Spotify
=============================================================
Se lanza como proceso aparte. Lee título/artista/portada vía SMTC
de Windows y los muestra en una ventanita sin borde, tipo mini-player.

USO (lo llama Jarvis.py automáticamente):
    python spotify_preview.py
"""
import sys
import asyncio
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as GestorMedios,
)
from winsdk.windows.storage.streams import DataReader


async def obtener_info_spotify():
    """Devuelve (titulo, artista, ruta_portada) o None si no hay sesión activa."""
    gestor = await GestorMedios.request_async()
    sesiones = gestor.get_sessions()
    sesion_spotify = None

    for sesion in sesiones:
        if "spotify" in sesion.source_app_user_model_id.lower():
            sesion_spotify = sesion
            break

    if not sesion_spotify:
        return None

    propiedades = await sesion_spotify.try_get_media_properties_async()
    ruta_portada = None

    if propiedades.thumbnail:
        stream = await propiedades.thumbnail.open_read_async()
        lector = DataReader(stream)
        await lector.load_async(stream.size)
        buffer = bytearray(stream.size)
        lector.read_bytes(buffer)

        ruta_portada = os.path.join(BASE_DIR, "portada_actual.jpg")
        with open(ruta_portada, "wb") as f:
            f.write(buffer)

    return (propiedades.title, propiedades.artist, ruta_portada)


def main():
    # Primero resolvemos la parte async (leer los datos de Windows),
    # y recién con los datos ya listos arrancamos la ventana normal de PySide6.
    datos = asyncio.run(obtener_info_spotify())

    app = QApplication(sys.argv)

    ventana = QWidget()
    ventana.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    ventana.setFixedSize(280, 340)
    ventana.setStyleSheet("background-color: #121212; border-radius: 12px;")

    layout = QVBoxLayout(ventana)
    layout.setContentsMargins(16, 16, 16, 16)

    if not datos:
        label_vacio = QLabel("No hay nada sonando\nen Spotify ahora mismo")
        label_vacio.setStyleSheet("color: #b3b3b3; font-size: 14px;")
        label_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_vacio)
    else:
        titulo, artista, ruta_portada = datos

        if ruta_portada:
            label_portada = QLabel()
            pixmap = QPixmap(ruta_portada).scaled(
                248, 248,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label_portada.setPixmap(pixmap)
            label_portada.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label_portada)

        label_titulo = QLabel(titulo)
        label_titulo.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        label_titulo.setWordWrap(True)
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_titulo)

        label_artista = QLabel(artista)
        label_artista.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        label_artista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_artista)

    # Centrado en pantalla, esquina inferior derecha tipo notificación
    pantalla = app.primaryScreen().availableGeometry()
    ventana.move(pantalla.width() - ventana.width() - 20, pantalla.height() - ventana.height() - 20)

    ventana.show()

    # Se cierra sola a los 6 segundos, como una notificación
    from PySide6.QtCore import QTimer
    QTimer.singleShot(6000, app.quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()