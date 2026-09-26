import sys
import os

if sys.stdout is None or sys.stderr is None:
    log_dir = os.path.join(os.getenv('APPDATA'), '.minecraft', 'config', 'jarvis', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'captura_preview_log.txt')
    log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file
"""
JARVIS - Previsualizador de capturas
======================================
Se lanza como proceso aparte cada vez que Jarvis saca una captura de
pantalla. Muestra la imagen en una ventanita PySide6, escalada para
que entre en la pantalla, con botón para cerrar.

USO (lo llama Jarvis.py automáticamente):
    python captura_preview.py "C:\\ruta\\a\\la\\captura.png"
"""
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


def main():
    if len(sys.argv) < 2:
        print("❌ Falta la ruta de la captura como argumento.")
        sys.exit(1)

    ruta_captura = sys.argv[1]

    app = QApplication(sys.argv)

    pixmap_original = QPixmap(ruta_captura)
    if pixmap_original.isNull():
        print(f"❌ No pude cargar la imagen: {ruta_captura}")
        sys.exit(1)

    # Escalamos para que entre cómoda en pantalla, sin pasarnos
    pantalla = app.primaryScreen().availableGeometry()
    ancho_max = int(pantalla.width() * 0.7)
    alto_max = int(pantalla.height() * 0.7)
    pixmap_escalado = pixmap_original.scaled(
        ancho_max, alto_max,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    ventana = QWidget()
    ventana.setWindowTitle("Jarvis - Previsualización de captura")
    ventana.setStyleSheet("background-color: #1e1e1e;")

    layout = QVBoxLayout(ventana)

    label_imagen = QLabel()
    label_imagen.setPixmap(pixmap_escalado)
    label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label_imagen)

    boton_cerrar = QPushButton("Cerrar")
    boton_cerrar.setStyleSheet(
        "background-color: #333; color: white; padding: 6px; border-radius: 4px;"
    )
    boton_cerrar.clicked.connect(ventana.close)
    layout.addWidget(boton_cerrar)

    ventana.setLayout(layout)
    ventana.resize(pixmap_escalado.width() + 20, pixmap_escalado.height() + 60)

    # La centramos en pantalla, como corresponde
    ventana.move(
        pantalla.center().x() - ventana.width() // 2,
        pantalla.center().y() - ventana.height() // 2,
    )

    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()