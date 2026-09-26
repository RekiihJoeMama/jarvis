import sys
import glob
import random
import json
import os
import time
import keyboard
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPixmap, QTransform

if sys.stdout is None or sys.stderr is None:
    log_dir = os.path.join(os.getenv('APPDATA'), '.minecraft', 'config', 'jarvis', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'buddy_log.txt')
    log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file
    print("--- Buddy iniciado ---")
    
def obtener_ruta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = obtener_ruta_base()

CARPETA_IDLE = os.path.join(BASE_DIR, "sprites", "idle")
CARPETA_CAMINA = os.path.join(BASE_DIR, "sprites", "camina")
FRAMES_CAMINA_DESDE = 4
ESCALA = 4
ARCHIVO_ESTADO = os.path.join(BASE_DIR, "estado_jarvis.json")

VELOCIDAD_ANIM_IDLE_MS = 100
VELOCIDAD_ANIM_CAMINA_MS = 90
VELOCIDAD_MOVIMIENTO_PX = 3
INTERVALO_MOVIMIENTO_MS = 30
TIEMPO_MIN_QUIETO = 2000
TIEMPO_MAX_QUIETO = 6000
TIEMPO_MIN_CAMINANDO = 1500
TIEMPO_MAX_CAMINANDO = 4000

salir_solicitado = False
mostrar_ocultar_solicitado = False

def _on_f4():
    global salir_solicitado
    salir_solicitado = True

def _on_f5():
    global mostrar_ocultar_solicitado
    mostrar_ocultar_solicitado = True

keyboard.add_hotkey('f4', _on_f4)
keyboard.add_hotkey('f5', _on_f5)


def cargar_frames(carpeta, escala, desde=0):
    rutas = sorted(glob.glob(f"{carpeta}/*.png"))[desde:]
    frames = []
    for ruta in rutas:
        pixmap = QPixmap(ruta)
        tamaño = pixmap.width() * escala
        frames.append(pixmap.scaled(tamaño, tamaño, Qt.KeepAspectRatio, Qt.FastTransformation))
    return frames


from PySide6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtGui import QColor, QFont


from PySide6.QtGui import QPainter, QPen, QPolygon


class ColaGlobo(QWidget):
    """El triangulito que sobresale del globo y apunta hacia el muñeco."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("JarvisUI - Cola")   # <-- NUEVA LÍNEA
        self.setFixedSize(20, 12)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 30, 35, 235))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        triangulo = QPolygon([QPoint(0, 0), QPoint(20, 0), QPoint(10, 12)])
        painter.drawPolygon(triangulo)


class Burbuja(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("JarvisUI - Burbuja")   # <-- NUEVA LÍNEA

        self.tarjeta = QLabel(self)
        self.tarjeta.setWordWrap(True)
        self.tarjeta.setStyleSheet("""
            background-color: rgba(30, 30, 35, 235);
            color: #f0f0f0;
            border: 1px solid rgba(255, 255, 255, 40);
            border-radius: 14px;
            padding: 12px 14px;
        """)
        self.tarjeta.setFont(QFont("Segoe UI", 10))
        self.tarjeta.setFixedWidth(230)

        self.etiqueta = QLabel("● JARVIS", self)
        self.etiqueta.setStyleSheet("""
            color: #6fb3ff;
            font-weight: bold;
            font-size: 10px;
            letter-spacing: 1px;
            background: transparent;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.tarjeta)

        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(25)
        sombra.setOffset(0, 4)
        sombra.setColor(QColor(0, 0, 0, 160))
        self.tarjeta.setGraphicsEffect(sombra)

        # NUEVO: la colita, como ventana propia (para que quede prolija sobre el fondo)
        self.cola = ColaGlobo()

        self.hide()

    def mostrar_texto(self, texto, buddy_x, buddy_y, buddy_ancho, buddy_alto):
        self.tarjeta.setText(texto)
        self.adjustSize()

        pantalla = QApplication.primaryScreen().geometry()
        centro_buddy_x = buddy_x + buddy_ancho // 2

        # Centramos el globo horizontalmente sobre el muñeco, sin salirnos de la pantalla
        bubble_x = centro_buddy_x - self.width() // 2
        bubble_x = max(10, min(bubble_x, pantalla.width() - self.width() - 10))
        bubble_y = buddy_y - self.height() - 15

        self.move(bubble_x, bubble_y)
        self.show()

        # La colita va justo debajo del globo, apuntando hacia el centro real del muñeco
        cola_x = centro_buddy_x - self.cola.width() // 2
        cola_x = max(bubble_x + 15, min(cola_x, bubble_x + self.width() - 35))
        self.cola.move(cola_x, bubble_y + self.height() - 1)
        self.cola.show()

    def hide(self):
        super().hide()
        if hasattr(self, "cola"):
            self.cola.hide()

    


class JarvisBuddy(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("JarvisUI - Buddy")   # <-- NUEVA LÍNEA

        self.frames_idle_derecha = cargar_frames(CARPETA_IDLE, ESCALA)
        self.frames_camina_derecha = cargar_frames(CARPETA_CAMINA, ESCALA, desde=FRAMES_CAMINA_DESDE)
        self.frames_idle_izquierda = [self._espejar(p) for p in self.frames_idle_derecha]
        self.frames_camina_izquierda = [self._espejar(p) for p in self.frames_camina_derecha]

        self.frame_actual = 0
        self.mirando_derecha = True
        self.dx = 0   # NUEVO: velocidad horizontal actual
        self.dy = 0   # NUEVO: velocidad vertical actual
        self.estado = "idle"
        self.congelado_hablando = False   # NUEVO: True mientras Jarvis habla o graba

        self.setPixmap(self.frames_idle_derecha[0])
        self.resize(self.frames_idle_derecha[0].size())
        self.move(600, 400)

        self.burbuja = Burbuja()

        self.timer_animacion = QTimer()
        self.timer_animacion.timeout.connect(self._siguiente_frame)
        self.timer_animacion.start(VELOCIDAD_ANIM_IDLE_MS)

        self.timer_movimiento = QTimer()
        self.timer_movimiento.timeout.connect(self._mover)
        self.timer_movimiento.start(INTERVALO_MOVIMIENTO_MS)

        self.timer_decision = QTimer()
        self.timer_decision.setSingleShot(True)
        self.timer_decision.timeout.connect(self._cambiar_estado)
        self.timer_decision.start(random.randint(TIEMPO_MIN_QUIETO, TIEMPO_MAX_QUIETO))

        self.timer_hotkeys = QTimer()
        self.timer_hotkeys.timeout.connect(self._chequear_hotkeys)
        self.timer_hotkeys.start(100)

        # NUEVO: Timer que lee el estado real de Jarvis
        self.timer_estado_jarvis = QTimer()
        self.timer_estado_jarvis.timeout.connect(self._leer_estado_jarvis)
        self.timer_estado_jarvis.start(150)

        self._arrastrando = False
        self._offset = QPoint()

    def _espejar(self, pixmap):
        return pixmap.transformed(QTransform().scale(-1, 1))

    def _frames_actuales(self):
        if self.estado == "camina":
            return self.frames_camina_derecha if self.mirando_derecha else self.frames_camina_izquierda
        return self.frames_idle_derecha if self.mirando_derecha else self.frames_idle_izquierda

    def _siguiente_frame(self):
        frames = self._frames_actuales()
        self.frame_actual = (self.frame_actual + 1) % len(frames)
        self.setPixmap(frames[self.frame_actual])

    def _cambiar_estado(self):
        if self._arrastrando or self.congelado_hablando:
            self.timer_decision.start(500)
            return
        if self.estado == "idle":
            self.estado = "camina"
            self._elegir_nueva_direccion()
            self.timer_animacion.setInterval(VELOCIDAD_ANIM_CAMINA_MS)
            self.timer_decision.start(random.randint(TIEMPO_MIN_CAMINANDO, TIEMPO_MAX_CAMINANDO))
        else:
            self.estado = "idle"
            self.timer_animacion.setInterval(VELOCIDAD_ANIM_IDLE_MS)
            self.timer_decision.start(random.randint(TIEMPO_MIN_QUIETO, TIEMPO_MAX_QUIETO))
        self.frame_actual = 0

    def _mover(self):
        if self._arrastrando or self.congelado_hablando or self.estado != "camina":
            return

        pantalla = QApplication.primaryScreen().geometry()
        pos = self.pos()
        ancho = self.width()
        alto = self.height()

        nueva_x = pos.x() + self.dx
        nueva_y = pos.y() + self.dy

        rebotó = False

        if nueva_x <= 0:
            nueva_x = 0
            self.dx = abs(self.dx)
            rebotó = True
        elif nueva_x + ancho >= pantalla.width():
            nueva_x = pantalla.width() - ancho
            self.dx = -abs(self.dx)
            rebotó = True

        if nueva_y <= 0:
            nueva_y = 0
            self.dy = abs(self.dy)
            rebotó = True
        elif nueva_y + alto >= pantalla.height():
            nueva_y = pantalla.height() - alto
            self.dy = -abs(self.dy)
            rebotó = True

        if rebotó:
            self.mirando_derecha = self.dx >= 0

        self.move(int(nueva_x), int(nueva_y))
    
    def _elegir_nueva_direccion(self):
        import math
        angulo = random.uniform(0, 2 * math.pi)
        self.dx = math.cos(angulo) * VELOCIDAD_MOVIMIENTO_PX
        self.dy = math.sin(angulo) * VELOCIDAD_MOVIMIENTO_PX
        self.mirando_derecha = self.dx >= 0

    def _leer_estado_jarvis(self):
        if not os.path.exists(ARCHIVO_ESTADO):
            return
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        # NUEVO: si el archivo es muy viejo, Jarvis.py ya no está corriendo
        timestamp = data.get("timestamp", 0)
        if time.time() - timestamp > 5:
            self.congelado_hablando = False
            self.burbuja.hide()
            return

        estado_jarvis = data.get("estado", "dormido")
        texto = data.get("texto", "")

        if estado_jarvis == "hablando":
            self.congelado_hablando = True
            pos = self.pos()
            self.burbuja.mostrar_texto(texto, pos.x(), pos.y(), self.width(), self.height())
        elif estado_jarvis == "grabando":
            self.congelado_hablando = True
            self.burbuja.hide()
        else:
            self.congelado_hablando = False
            self.burbuja.hide()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._arrastrando = True
            self._offset = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._arrastrando:
            nueva_pos = self.mapToGlobal(event.position().toPoint() - self._offset)
            self.move(nueva_pos)

    def mouseReleaseEvent(self, event):
        self._arrastrando = False

    def _chequear_hotkeys(self):
        global salir_solicitado, mostrar_ocultar_solicitado
        if salir_solicitado:
            QApplication.instance().quit()
            return
        if mostrar_ocultar_solicitado:
            mostrar_ocultar_solicitado = False
            if self.isVisible():
                self.hide()
                self.burbuja.hide()
            else:
                self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    buddy = JarvisBuddy()
    buddy.show()
    sys.exit(app.exec())