"""
Módulo de reconocimiento visual para Balatro AI.
Detecta cartas usando template matching.
"""

import os
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    class _DummyNp:
        ndarray = object
    np = _DummyNp()

from .game_state import Card, Suit, GameState, BlindInfo


@dataclass
class DetectedCard:
    """Resultado de detección de una carta."""
    card: Card
    confidence: float
    position: Tuple[int, int, int, int]  # (x, y, width, height)


class TemplateCardDetector:
    """
    Detecta cartas usando template matching.
    """
    
    SUIT_MAP = {'H': Suit.HEARTS, 'S': Suit.SPADES, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
    RANK_MAP = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, 
                '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
    
    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
        self.templates_dir = templates_dir
        self.templates: Dict[Tuple[str, str], np.ndarray] = {}
        self.scale = 0.75  # Escala óptima para matching
        self.threshold = 0.45  # Umbral mínimo de confianza
        self.nms_distance = 70  # Distancia mínima entre detecciones
        
        self._load_templates()
    
    def _load_templates(self):
        """Carga todos los templates de cartas."""
        if not CV2_AVAILABLE or not os.path.exists(self.templates_dir):
            return
        
        for f in os.listdir(self.templates_dir):
            if f.endswith('.png') and f.startswith('template_') and f.count('_') == 2:
                parts = f.replace('template_', '').replace('.png', '').split('_')
                rank, suit = parts[0], parts[1]
                img = cv2.imread(os.path.join(self.templates_dir, f))
                if img is not None:
                    self.templates[(rank, suit)] = img
        
        print(f"Templates cargados: {len(self.templates)}")
    
    def detect_cards(self, image: np.ndarray, 
                     region: Tuple[int, int, int, int] = None) -> List[DetectedCard]:
        """
        Detecta cartas en la imagen.
        
        Args:
            image: Imagen BGR
            region: Región (x, y, w, h) donde buscar, o None para imagen completa
        
        Returns:
            Lista de cartas detectadas ordenadas por posición X
        """
        if not CV2_AVAILABLE or not self.templates:
            return []
        
        # Extraer región de interés
        if region:
            x, y, w, h = region
            roi = image[y:y+h, x:x+w]
            offset_x, offset_y = x, y
        else:
            roi = image
            offset_x, offset_y = 0, 0
        
        # Buscar todos los templates
        all_matches = []
        
        for (rank, suit), template in self.templates.items():
            # Escalar template
            scaled = cv2.resize(template, None, fx=self.scale, fy=self.scale)
            
            if scaled.shape[0] > roi.shape[0] or scaled.shape[1] > roi.shape[1]:
                continue
            
            # Template matching
            result = cv2.matchTemplate(roi, scaled, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= self.threshold)
            
            th, tw = scaled.shape[:2]
            
            for pt in zip(*locations[::-1]):
                score = result[pt[1], pt[0]]
                all_matches.append({
                    'rank': rank,
                    'suit': suit,
                    'x': pt[0],
                    'y': pt[1],
                    'w': tw,
                    'h': th,
                    'score': score
                })
        
        # Ordenar por score descendente
        all_matches.sort(key=lambda m: -m['score'])
        
        # Non-Maximum Suppression
        final_matches = []
        for match in all_matches:
            is_overlap = False
            cx1 = match['x'] + match['w'] // 2
            cy1 = match['y'] + match['h'] // 2
            
            for existing in final_matches:
                cx2 = existing['x'] + existing['w'] // 2
                cy2 = existing['y'] + existing['h'] // 2
                distance = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
                
                if distance < self.nms_distance:
                    is_overlap = True
                    break
            
            if not is_overlap:
                final_matches.append(match)
        
        # Ordenar por posición X
        final_matches.sort(key=lambda m: m['x'])
        
        # Convertir a DetectedCard
        detected = []
        for m in final_matches:
            rank_val = self.RANK_MAP.get(m['rank'], 0)
            suit_val = self.SUIT_MAP.get(m['suit'], Suit.SPADES)
            
            if rank_val > 0:
                card = Card(rank=rank_val, suit=suit_val)
                detected.append(DetectedCard(
                    card=card,
                    confidence=m['score'],
                    position=(
                        m['x'] + offset_x,
                        m['y'] + offset_y,
                        m['w'],
                        m['h']
                    )
                ))
        
        return detected


class BalatroRecognizer:
    """
    Clase auxiliar para compatibilidad con run_ai.py.
    Proporciona métodos de diagnóstico y regiones.
    """
    
    def __init__(self, hand_region: Tuple[int, int, int, int]):
        self._regions = {
            'hand': hand_region
        }
    
    def get_debug_image(self, image: np.ndarray) -> np.ndarray:
        """Devuelve imagen con las regiones marcadas."""
        debug = image.copy()
        
        for name, region in self._regions.items():
            x, y, w, h = region
            cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug, name, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return debug


class BalatroVisionSystem:
    """
    Sistema de visión para Balatro.
    """
    
    # Región de la mano (coordenadas absolutas calibradas)
    # Ampliada para capturar todas las 8 cartas incluyendo extremos
    HAND_REGION = (200, 480, 1200, 280)  # (x, y, w, h) - va de 200 a 1400, cubre más área
    EXPECTED_CARDS = 8  # Número esperado de cartas en mano
    
    def __init__(self):
        from .screen_capture import ScreenCapture
        
        self.capture = ScreenCapture()
        self.detector = TemplateCardDetector()
        self.recognizer = BalatroRecognizer(self.HAND_REGION)
        self._window_found = False
        self._last_image = None
        
        # Estado para detección estable
        self._stable_hand: Optional[List[Card]] = None
        self._stable_hand_str: str = ""
        self._detection_locked = False
        self._lock_count = 0
        self._required_confirmations = 3  # Confirmar 3 veces antes de bloquear
    
    def initialize(self) -> bool:
        """Inicializa buscando la ventana de Balatro."""
        window = self.capture.find_game_window()
        if window:
            print(f"✓ Ventana de Balatro: {window.width}x{window.height}")
            self._window_found = True
            return True
        else:
            print("✗ No se encontró la ventana de Balatro")
            return False
    
    def capture_and_analyze(self, stable_mode: bool = True) -> Tuple[Optional[GameState], Optional[np.ndarray]]:
        """
        Captura pantalla y analiza el estado.
        
        Args:
            stable_mode: Si True, usa detección estable que se bloquea al detectar 8 cartas
        
        Retorna (GameState, imagen BGR) o (None, None) si falla.
        """
        try:
            # Capturar pantalla
            img = self.capture.capture_to_numpy()
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            self._last_image = img_bgr
            
            # Detectar cartas en la mano
            detected = self.detector.detect_cards(img_bgr, self.HAND_REGION)
            current_cards = [d.card for d in detected]
            current_hand_str = ' '.join(sorted(str(c) for c in current_cards))
            
            if stable_mode:
                return self._process_stable_detection(current_cards, current_hand_str, img_bgr)
            else:
                # Modo sin estabilización
                state = GameState()
                state.hand = current_cards
                state.hands_remaining = 4
                state.discards_remaining = 3
                state.blind = BlindInfo("Blind", 300)
                return state, img_bgr
            
        except Exception as e:
            print(f"Error: {e}")
            return None, None
    
    def _process_stable_detection(self, current_cards: List[Card], 
                                   current_hand_str: str,
                                   img_bgr) -> Tuple[Optional[GameState], Optional[np.ndarray]]:
        """
        Procesa la detección con estabilización.
        Se bloquea cuando detecta 8 cartas consistentemente.
        Se desbloquea cuando cambia significativamente la mano.
        """
        num_cards = len(current_cards)
        
        # Si está bloqueado, verificar si la mano cambió significativamente
        if self._detection_locked:
            # Verificar cambio significativo (menos de 5 cartas en común = mano jugada)
            if self._stable_hand:
                stable_set = set(str(c) for c in self._stable_hand)
                current_set = set(str(c) for c in current_cards)
                common = len(stable_set & current_set)
                
                # Si hay menos de 5 cartas en común, la mano cambió
                # O si el número de cartas cambió significativamente
                if common < 5 or abs(num_cards - len(self._stable_hand)) >= 3:
                    self._unlock_detection()
                    print(f"🔓 Desbloqueado: mano cambió ({common} cartas en común)")
                else:
                    # Mantener la mano estable anterior
                    state = GameState()
                    state.hand = self._stable_hand
                    state.hands_remaining = 4
                    state.discards_remaining = 3
                    state.blind = BlindInfo("Blind", 300)
                    return state, img_bgr
        
        # Si no está bloqueado, verificar si debemos bloquear
        if not self._detection_locked:
            if num_cards == self.EXPECTED_CARDS:
                # Verificar consistencia con detección anterior
                if current_hand_str == self._stable_hand_str:
                    self._lock_count += 1
                    
                    # Bloquear después de confirmaciones suficientes
                    if self._lock_count >= self._required_confirmations:
                        self._stable_hand = current_cards.copy()
                        self._detection_locked = True
                        print(f"🔒 Bloqueado: {num_cards} cartas detectadas consistentemente")
                else:
                    # Nueva detección, reiniciar contador
                    self._stable_hand_str = current_hand_str
                    self._lock_count = 1
            else:
                # No hay 8 cartas, reiniciar
                self._lock_count = 0
                self._stable_hand_str = ""
        
        # Crear estado con la mejor detección disponible
        state = GameState()
        if self._detection_locked and self._stable_hand:
            state.hand = self._stable_hand
        else:
            state.hand = current_cards
        
        state.hands_remaining = 4
        state.discards_remaining = 3
        state.blind = BlindInfo("Blind", 300)
        
        return state, img_bgr
    
    def _unlock_detection(self):
        """Desbloquea la detección para buscar nueva mano."""
        self._detection_locked = False
        self._stable_hand = None
        self._stable_hand_str = ""
        self._lock_count = 0
    
    def force_unlock(self):
        """Fuerza el desbloqueo de la detección."""
        self._unlock_detection()
        print("🔓 Detección desbloqueada manualmente")
    
    def is_locked(self) -> bool:
        """Retorna si la detección está bloqueada."""
        return self._detection_locked
    
    def get_state(self) -> Optional[GameState]:
        """Captura y analiza el estado del juego."""
        state, _ = self.capture_and_analyze()
        return state
    
    def get_detected_cards(self) -> List[DetectedCard]:
        """Obtiene las cartas detectadas con detalles."""
        try:
            img = self.capture.capture_to_numpy()
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return self.detector.detect_cards(img_bgr, self.HAND_REGION)
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def save_debug_image(self, path: str = "deteccion_debug.png") -> bool:
        """Guarda imagen de depuración con detecciones marcadas."""
        try:
            img = self.capture.capture_to_numpy()
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Extraer región de mano
            x, y, w, h = self.HAND_REGION
            hand = img_bgr[y:y+h, x:x+w]
            
            # Detectar y dibujar
            detected = self.detector.detect_cards(img_bgr, self.HAND_REGION)
            
            suit_sym = {'H': 'h', 'D': 'd', 'S': 's', 'C': 'c'}
            rank_sym = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: '10',
                        9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}
            
            for d in detected:
                px, py, pw, ph = d.position
                # Ajustar a coordenadas de la región
                px -= x
                py -= y
                
                cv2.rectangle(hand, (px, py), (px + pw, py + ph), (0, 255, 0), 2)
                
                r = rank_sym.get(d.card.rank, str(d.card.rank))
                s = d.card.suit.name[0]
                label = f"{r}{suit_sym.get(s, s)}"
                cv2.putText(hand, label, (px, py - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imwrite(path, hand)
            print(f"✓ Imagen guardada: {path}")
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False


# Alias para compatibilidad
AutoCardDetector = TemplateCardDetector
AutoGameRecognizer = BalatroVisionSystem
CardDetector = TemplateCardDetector


if __name__ == "__main__":
    print("=== Test de Visión ===\n")
    
    vision = BalatroVisionSystem()
    
    if vision.initialize():
        print("\nDetectando cartas...")
        
        detected = vision.get_detected_cards()
        
        print(f"\n{'='*50}")
        print(f"CARTAS DETECTADAS: {len(detected)}")
        print(f"{'='*50}")
        
        suit_symbols = {Suit.HEARTS: '♥', Suit.DIAMONDS: '♦', 
                        Suit.SPADES: '♠', Suit.CLUBS: '♣'}
        rank_names = {14: 'A', 13: 'K', 12: 'Q', 11: 'J'}
        
        for i, d in enumerate(detected, 1):
            r = rank_names.get(d.card.rank, str(d.card.rank))
            s = suit_symbols.get(d.card.suit, '?')
            print(f"  {i}. {r}{s} (confianza: {d.confidence:.2f})")
        
        print(f"{'='*50}")
        
        vision.save_debug_image()
