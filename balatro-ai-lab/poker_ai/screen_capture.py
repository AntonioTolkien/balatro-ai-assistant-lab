"""
Módulo de captura de pantalla para Balatro AI.
Captura la ventana del juego para análisis.
"""

import time
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from PIL import Image
import numpy as np

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import win32gui
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class CaptureRegion:
    """Define una región de captura."""
    left: int
    top: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.left + self.width
    
    @property
    def bottom(self) -> int:
        return self.top + self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)
    
    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.left, self.top, self.width, self.height)
    
    def as_bbox(self) -> Tuple[int, int, int, int]:
        """Retorna como (left, top, right, bottom)."""
        return (self.left, self.top, self.right, self.bottom)


class ScreenCapture:
    """
    Clase para capturar la pantalla del juego Balatro.
    Soporta múltiples backends: mss (rápido), pyautogui, win32.
    """
    
    # Títulos EXACTOS de la ventana del juego (no parciales)
    WINDOW_TITLES_EXACT = ["Balatro"]
    
    def __init__(self, backend: str = "auto"):
        """
        Inicializa el capturador.
        
        Args:
            backend: "mss", "pyautogui", "win32" o "auto"
        """
        self.backend = self._select_backend(backend)
        self.game_window: Optional[CaptureRegion] = None
        self._mss_instance = None
        self._window_hwnd = None  # Handle de la ventana del juego
        
        if self.backend == "mss" and MSS_AVAILABLE:
            self._mss_instance = mss.mss()
    
    def _select_backend(self, preferred: str) -> str:
        """Selecciona el backend disponible."""
        if preferred != "auto":
            return preferred
        
        # Prioridad: mss > win32 > pyautogui
        if MSS_AVAILABLE:
            return "mss"
        if WIN32_AVAILABLE:
            return "win32"
        if PYAUTOGUI_AVAILABLE:
            return "pyautogui"
        
        raise RuntimeError("No hay ningún backend de captura disponible. "
                          "Instala: pip install mss pillow")
    
    def find_game_window(self) -> Optional[CaptureRegion]:
        """
        Encuentra la ventana del juego Balatro.
        Busca específicamente ventanas con título EXACTO "Balatro".
        
        Returns:
            CaptureRegion con la posición de la ventana, o None si no se encuentra.
        """
        if not WIN32_AVAILABLE:
            return None
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # Buscar coincidencia EXACTA del título
                if title in self.WINDOW_TITLES_EXACT:
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    # Verificar que sea una ventana real (no muy pequeña)
                    if width > 200 and height > 200:
                        windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'rect': rect,
                            'width': width,
                            'height': height
                        })
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        if windows:
            # Tomar la ventana de Balatro (debería haber solo una)
            window = windows[0]
            rect = window['rect']
            self._window_hwnd = window['hwnd']
            
            self.game_window = CaptureRegion(
                left=rect[0],
                top=rect[1],
                width=window['width'],
                height=window['height']
            )
            return self.game_window
        
        return None
    
    def capture_screen(self, region: Optional[CaptureRegion] = None) -> Image.Image:
        """
        Captura la pantalla o una región específica.
        Usa captura directa de ventana si hay un hwnd válido.
        
        Args:
            region: Región a capturar (None = pantalla completa o ventana del juego)
        
        Returns:
            Imagen PIL de la captura.
        """
        # Si tenemos el handle de la ventana, capturar directamente la ventana
        # Esto funciona aunque la ventana esté detrás de otras
        if self._window_hwnd and WIN32_AVAILABLE:
            return self._capture_window_direct(self._window_hwnd)
        
        if region is None:
            region = self.game_window
        
        if self.backend == "mss":
            return self._capture_mss(region)
        elif self.backend == "pyautogui":
            return self._capture_pyautogui(region)
        elif self.backend == "win32":
            return self._capture_win32(region)
        else:
            raise ValueError(f"Backend desconocido: {self.backend}")
    
    def _capture_mss(self, region: Optional[CaptureRegion]) -> Image.Image:
        """Captura usando mss (más rápido)."""
        if region:
            monitor = {
                "left": region.left,
                "top": region.top,
                "width": region.width,
                "height": region.height
            }
        else:
            monitor = self._mss_instance.monitors[0]  # Pantalla principal
        
        screenshot = self._mss_instance.grab(monitor)
        return Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
    
    def _capture_pyautogui(self, region: Optional[CaptureRegion]) -> Image.Image:
        """Captura usando pyautogui."""
        if region:
            screenshot = pyautogui.screenshot(region=region.as_tuple())
        else:
            screenshot = pyautogui.screenshot()
        return screenshot
    
    def _capture_win32(self, region: Optional[CaptureRegion]) -> Image.Image:
        """Captura usando win32 API."""
        if region:
            left, top, width, height = region.as_tuple()
        else:
            left, top = 0, 0
            width = win32gui.GetSystemMetrics(win32con.SM_CXSCREEN)
            height = win32gui.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        hwnd = win32gui.GetDesktopWindow()
        
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (left, top), win32con.SRCCOPY)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        
        img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                               bmpstr, 'raw', 'BGRX', 0, 1)
        
        # Limpiar
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return img
    
    def _capture_window_direct(self, hwnd: int) -> Image.Image:
        """
        Captura directamente el contenido de una ventana específica.
        Funciona aunque la ventana esté detrás de otras o parcialmente oculta.
        """
        import ctypes
        
        # Obtener el tamaño de la ventana
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        
        # Usar PrintWindow para capturar la ventana aunque esté oculta
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # PrintWindow captura el contenido real de la ventana
        # Flag 2 = PW_RENDERFULLCONTENT (captura incluso contenido DirectX/OpenGL)
        ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        
        img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                               bmpstr, 'raw', 'BGRX', 0, 1)
        
        # Limpiar
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return img
    
    def capture_to_numpy(self, region: Optional[CaptureRegion] = None) -> np.ndarray:
        """
        Captura y convierte a numpy array (RGB).
        
        Returns:
            Array numpy de forma (height, width, 3)
        """
        img = self.capture_screen(region)
        return np.array(img)
    
    def start_continuous_capture(self, callback: Callable[[Image.Image], None],
                                  fps: int = 10, duration: Optional[float] = None):
        """
        Inicia captura continua con callback.
        
        Args:
            callback: Función que recibe cada captura
            fps: Capturas por segundo
            duration: Duración en segundos (None = infinito)
        """
        interval = 1.0 / fps
        start_time = time.time()
        
        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    break
                
                frame_start = time.time()
                
                img = self.capture_screen()
                callback(img)
                
                # Mantener FPS
                elapsed = time.time() - frame_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            pass


# =============================================================================
# REGIONES PREDEFINIDAS DE LA UI DE BALATRO
# =============================================================================

class BalatroRegions:
    """
    Define las regiones de la UI de Balatro para diferentes resoluciones.
    Estas son posiciones aproximadas - se ajustarán según la resolución detectada.
    """
    
    def __init__(self, game_region: CaptureRegion):
        """
        Inicializa las regiones basándose en la ventana del juego.
        
        Args:
            game_region: Región de la ventana del juego
        """
        self.game = game_region
        w = game_region.width
        h = game_region.height
        
        # Calcular regiones relativas (basado en 1920x1080)
        self._calculate_regions(w, h)
    
    def _calculate_regions(self, w: int, h: int):
        """Calcula todas las regiones basándose en el tamaño de ventana."""
        
        # Factores de escala respecto a 1920x1080
        sx = w / 1920
        sy = h / 1080
        
        # Mano del jugador (cartas en la parte inferior)
        self.hand = CaptureRegion(
            left=self.game.left + int(300 * sx),
            top=self.game.top + int(750 * sy),
            width=int(1320 * sx),
            height=int(200 * sy)
        )
        
        # Jokers (parte superior izquierda)
        self.jokers = CaptureRegion(
            left=self.game.left + int(50 * sx),
            top=self.game.top + int(50 * sy),
            width=int(600 * sx),
            height=int(150 * sy)
        )
        
        # Blind info (centro-derecha)
        self.blind_info = CaptureRegion(
            left=self.game.left + int(1400 * sx),
            top=self.game.top + int(100 * sy),
            width=int(450 * sx),
            height=int(200 * sy)
        )
        
        # Puntuación actual
        self.score = CaptureRegion(
            left=self.game.left + int(1400 * sx),
            top=self.game.top + int(300 * sy),
            width=int(400 * sx),
            height=int(100 * sy)
        )
        
        # Manos y descartes restantes
        self.hands_discards = CaptureRegion(
            left=self.game.left + int(50 * sx),
            top=self.game.top + int(600 * sy),
            width=int(200 * sx),
            height=int(150 * sy)
        )
        
        # Dinero
        self.money = CaptureRegion(
            left=self.game.left + int(50 * sx),
            top=self.game.top + int(250 * sy),
            width=int(150 * sx),
            height=int(50 * sy)
        )
        
        # Área de juego central (donde se muestran las cartas jugadas)
        self.play_area = CaptureRegion(
            left=self.game.left + int(400 * sx),
            top=self.game.top + int(350 * sy),
            width=int(1000 * sx),
            height=int(300 * sy)
        )
    
    def get_card_positions(self, num_cards: int = 8) -> list[CaptureRegion]:
        """
        Calcula las posiciones individuales de cada carta en la mano.
        
        Args:
            num_cards: Número de cartas en mano (default 8)
        
        Returns:
            Lista de CaptureRegion para cada carta
        """
        card_width = self.hand.width // num_cards
        positions = []
        
        for i in range(num_cards):
            pos = CaptureRegion(
                left=self.hand.left + (i * card_width),
                top=self.hand.top,
                width=card_width,
                height=self.hand.height
            )
            positions.append(pos)
        
        return positions
    
    def get_joker_positions(self, num_jokers: int = 5) -> list[CaptureRegion]:
        """Calcula las posiciones de los jokers."""
        joker_width = self.jokers.width // num_jokers
        positions = []
        
        for i in range(num_jokers):
            pos = CaptureRegion(
                left=self.jokers.left + (i * joker_width),
                top=self.jokers.top,
                width=joker_width,
                height=self.jokers.height
            )
            positions.append(pos)
        
        return positions


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("=== Test de Captura de Pantalla ===\n")
    
    # Verificar backends disponibles
    print("Backends disponibles:")
    print(f"  - mss: {'✓' if MSS_AVAILABLE else '✗'}")
    print(f"  - pyautogui: {'✓' if PYAUTOGUI_AVAILABLE else '✗'}")
    print(f"  - win32: {'✓' if WIN32_AVAILABLE else '✗'}")
    print()
    
    try:
        capture = ScreenCapture()
        print(f"Backend seleccionado: {capture.backend}")
        
        # Buscar ventana de Balatro
        window = capture.find_game_window()
        if window:
            print(f"\n✓ Ventana de Balatro encontrada:")
            print(f"  Posición: ({window.left}, {window.top})")
            print(f"  Tamaño: {window.width}x{window.height}")
            
            # Capturar
            img = capture.capture_screen()
            print(f"\n✓ Captura realizada: {img.size}")
            
            # Guardar para verificación
            img.save("balatro_capture_test.png")
            print("  Guardada en: balatro_capture_test.png")
        else:
            print("\n⚠ Ventana de Balatro no encontrada.")
            print("  Ejecuta Balatro y vuelve a intentar.")
            
            # Captura de pantalla completa de prueba
            print("\n  Realizando captura de pantalla completa...")
            img = capture.capture_screen()
            print(f"  Captura: {img.size}")
            img.save("screen_capture_test.png")
            print("  Guardada en: screen_capture_test.png")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nInstala las dependencias:")
        print("  pip install mss pillow pywin32")
