"""
Balatro AI - Punto de entrada principal.
Integra todos los módulos para proporcionar asistencia en tiempo real.
"""

import sys
import time
import argparse
import threading
from typing import Optional

from .game_state import GameState, Card, parse_hand, create_joker, BlindInfo, HandType
from .optimizer import StrategyOptimizer, Recommender, Action, Strategy
from .screen_capture import ScreenCapture, BalatroRegions
from .vision import GameRecognizer, ManualInputRecognizer
from .ui import BalatroAIApp, BalatroOverlay, run_cli, TK_AVAILABLE


class BalatroAI:
    """
    Controlador principal de Balatro AI.
    Orquesta captura, reconocimiento, optimización y UI.
    """
    
    def __init__(self, mode: str = "manual"):
        """
        Inicializa Balatro AI.
        
        Args:
            mode: "manual", "auto" o "overlay"
        """
        self.mode = mode
        self.running = False
        
        # Componentes
        self.screen_capture: Optional[ScreenCapture] = None
        self.recognizer: Optional[GameRecognizer] = None
        self.manual_input = ManualInputRecognizer()
        self.recommender = Recommender()
        
        # Estado
        self.current_state: Optional[GameState] = None
        self.last_recommendation: Optional[Action] = None
        self.last_strategy: Optional[Strategy] = None
        
        # Inicializar según modo
        if mode in ("auto", "overlay"):
            self._init_auto_mode()
    
    def _init_auto_mode(self):
        """Inicializa componentes para modo automático."""
        try:
            self.screen_capture = ScreenCapture()
            self.recognizer = GameRecognizer()
            
            # Buscar ventana del juego
            window = self.screen_capture.find_game_window()
            if window:
                print(f"✓ Ventana de Balatro encontrada: {window.width}x{window.height}")
            else:
                print("⚠ Ventana de Balatro no encontrada. Usa modo manual.")
                
        except Exception as e:
            print(f"⚠ Error inicializando modo auto: {e}")
            self.mode = "manual"
    
    def update_state(self, state: GameState):
        """
        Actualiza el estado del juego y genera recomendaciones.
        """
        self.current_state = state
        self.recommender.update_state(state)
        
        # Generar recomendación
        self.last_recommendation, self.last_strategy = self.recommender.get_recommendation()
        
        return self.last_recommendation, self.last_strategy
    
    def set_hand_manual(self, cards_str: str):
        """Establece la mano manualmente."""
        self.manual_input.set_hand(cards_str)
    
    def set_blind_manual(self, name: str, target: int):
        """Establece el blind manualmente."""
        self.manual_input.set_blind(name, target)
    
    def set_resources_manual(self, hands: int, discards: int, money: int = 0):
        """Establece los recursos manualmente."""
        self.manual_input.set_resources(hands, discards, money)
    
    def set_score_manual(self, score: int):
        """Establece la puntuación actual."""
        self.manual_input.set_score(score)
    
    def add_joker_manual(self, name: str):
        """Añade un joker manualmente."""
        self.manual_input.add_joker(name)
    
    def clear_jokers(self):
        """Limpia los jokers."""
        self.manual_input.clear_jokers()
    
    def analyze(self) -> tuple[Action, Strategy]:
        """
        Analiza el estado actual y retorna recomendaciones.
        """
        state = self.manual_input.get_state()
        return self.update_state(state)
    
    def get_all_plays(self, top_n: int = 10) -> list[Action]:
        """Obtiene las mejores N jugadas."""
        if not self.current_state:
            return []
        
        optimizer = StrategyOptimizer(self.current_state)
        return optimizer.find_all_plays(top_n)
    
    def get_tips(self) -> list[str]:
        """Obtiene consejos rápidos."""
        return self.recommender.get_quick_tips()
    
    def run_auto_capture(self, callback=None, fps: int = 2):
        """
        Inicia captura automática continua.
        
        Args:
            callback: Función a llamar con cada nuevo estado
            fps: Capturas por segundo
        """
        if self.mode != "auto" or not self.screen_capture:
            print("Modo auto no disponible")
            return
        
        self.running = True
        interval = 1.0 / fps
        
        print(f"Iniciando captura automática ({fps} FPS)...")
        print("Presiona Ctrl+C para detener")
        
        try:
            while self.running:
                start = time.time()
                
                # Capturar pantalla
                image = self.screen_capture.capture_to_numpy()
                
                # Reconocer estado
                state = self.recognizer.recognize_game_state(image)
                
                # Actualizar y recomendar
                action, strategy = self.update_state(state)
                
                if callback:
                    callback(action, strategy)
                
                # Mantener FPS
                elapsed = time.time() - start
                if elapsed < interval:
                    time.sleep(interval - elapsed)
                    
        except KeyboardInterrupt:
            print("\nCaptura detenida")
        finally:
            self.running = False
    
    def stop(self):
        """Detiene la captura automática."""
        self.running = False


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def quick_analysis(hand_str: str, target: int = 800, 
                   hands: int = 4, discards: int = 3,
                   jokers: list[str] = None) -> tuple[Action, Strategy]:
    """
    Análisis rápido de una mano.
    
    Args:
        hand_str: Cartas en mano (ej: "AS KH QD JC 10S")
        target: Objetivo del blind
        hands: Manos restantes
        discards: Descartes restantes
        jokers: Lista de nombres de jokers
    
    Returns:
        Tuple de (mejor acción, estrategia completa)
    
    Ejemplo:
        >>> action, strategy = quick_analysis("AS AH KS KH QD 7C", 800, jokers=["Jolly Joker"])
        >>> print(action)
    """
    ai = BalatroAI(mode="manual")
    
    ai.set_hand_manual(hand_str)
    ai.set_blind_manual("Blind", target)
    ai.set_resources_manual(hands, discards)
    
    if jokers:
        for joker in jokers:
            ai.add_joker_manual(joker)
    
    return ai.analyze()


def print_analysis(hand_str: str, target: int = 800,
                   hands: int = 4, discards: int = 3,
                   jokers: list[str] = None):
    """
    Imprime un análisis completo de forma legible.
    """
    print("=" * 60)
    print("ANÁLISIS DE BALATRO")
    print("=" * 60)
    
    print(f"\nMano: {hand_str}")
    print(f"Objetivo: {target}")
    print(f"Manos: {hands}, Descartes: {discards}")
    if jokers:
        print(f"Jokers: {', '.join(jokers)}")
    
    action, strategy = quick_analysis(hand_str, target, hands, discards, jokers)
    
    print("\n" + "-" * 40)
    print("RECOMENDACIÓN:")
    print("-" * 40)
    
    if action.action_type.name == "PLAY":
        print(f"▶ JUGAR: {' '.join(str(c) for c in action.cards)}")
        print(f"  Tipo: {action.hand_type.display_name if action.hand_type else 'N/A'}")
        print(f"  Puntuación esperada: {action.expected_score:,}")
    else:
        print(f"🔄 DESCARTAR: {' '.join(str(c) for c in action.cards)}")
    
    print(f"  Razón: {action.reasoning}")
    
    print("\n" + "-" * 40)
    print("ESTRATEGIA:")
    print("-" * 40)
    print(strategy)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Punto de entrada principal."""
    
    parser = argparse.ArgumentParser(description="Balatro AI - Asistente de Estrategia")
    parser.add_argument("--mode", choices=["gui", "cli", "overlay", "auto"],
                       default="gui", help="Modo de ejecución")
    parser.add_argument("--hand", type=str, help="Mano para análisis rápido")
    parser.add_argument("--target", type=int, default=800, help="Objetivo del blind")
    
    args = parser.parse_args()
    
    # Análisis rápido desde línea de comandos
    if args.hand:
        print_analysis(args.hand, args.target)
        return
    
    # Modos de ejecución
    if args.mode == "cli":
        run_cli()
    
    elif args.mode == "gui":
        if TK_AVAILABLE:
            app = BalatroAIApp()
            app.run()
        else:
            print("GUI no disponible. Iniciando CLI...")
            run_cli()
    
    elif args.mode == "overlay":
        if TK_AVAILABLE:
            overlay = BalatroOverlay()
            overlay.run()
        else:
            print("Overlay no disponible")
    
    elif args.mode == "auto":
        ai = BalatroAI(mode="auto")
        
        def on_update(action, strategy):
            print(f"\r[{action.hand_type.display_name if action.hand_type else '?'}] "
                  f"{action.expected_score:,} pts", end="")
        
        ai.run_auto_capture(callback=on_update)


if __name__ == "__main__":
    main()
