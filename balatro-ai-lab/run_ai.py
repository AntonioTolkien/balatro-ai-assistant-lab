#!/usr/bin/env python3
"""
Balatro AI - Script de ejecución principal
Sistema AUTOMÁTICO de análisis y recomendaciones para Balatro.
"""

import sys
import os
import time

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_ai.game_state import GameState, BlindInfo, parse_hand, create_joker
from poker_ai.optimizer import StrategyOptimizer


def clear_screen():
    """Limpia la pantalla."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              🃏  BALATRO AI  🃏                             ║")
    print("║           Sistema de Análisis AUTOMÁTICO                   ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def check_dependencies():
    """Verifica dependencias."""
    missing = []
    
    try:
        import mss
    except ImportError:
        missing.append("mss")
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")
    
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    except ImportError:
        missing.append("pytesseract")
    
    if missing:
        print("❌ Faltan dependencias:")
        for dep in missing:
            print(f"   - {dep}")
        print(f"\nInstala con: pip install {' '.join(missing)}")
        return False
    
    print("✓ Dependencias OK")
    return True


def print_state(state: GameState):
    """Muestra el estado detectado."""
    print("\n" + "─" * 55)
    print("📊 ESTADO DETECTADO")
    print("─" * 55)
    
    if state.hand:
        cards_str = ' '.join(str(c) for c in state.hand)
        print(f"\n🃏 Mano ({len(state.hand)} cartas): {cards_str}")
    else:
        print("\n🃏 Mano: [No detectada]")
    
    if state.blind:
        print(f"🎯 Objetivo: {state.blind.target_score:,}")
    
    print(f"📊 Puntuación actual: {state.current_score:,}")
    print(f"✋ Manos restantes: {state.hands_remaining}")
    print(f"🗑️ Descartes restantes: {state.discards_remaining}")
    
    if state.jokers:
        joker_names = ', '.join(j.name for j in state.jokers)
        print(f"🎪 Jokers: {joker_names}")


def print_recommendation(state: GameState, optimizer):
    """Muestra la recomendación de jugada de forma clara."""
    print("\n" + "═" * 60)
    print("💡 ANÁLISIS Y RECOMENDACIÓN")
    print("═" * 60)
    
    if not state.hand or len(state.hand) == 0:
        print("\n⚠ No hay cartas en mano")
        return
    
    target = state.blind.target_score if state.blind else 300
    current = state.current_score
    needed = target - current
    
    print(f"\n🎯 Necesitas: {needed:,} puntos para ganar")
    
    # Encontrar la mejor jugada posible
    best_play = optimizer.find_best_play()
    
    if best_play and best_play.cards:
        cards_str = ' '.join(str(c) for c in best_play.cards)
        hand_name = best_play.hand_type.display_name if best_play.hand_type else "Carta alta"
        expected = best_play.expected_score
        
        print(f"\n📊 Mejor mano disponible:")
        print(f"   {hand_name}: {cards_str}")
        print(f"   Puntaje esperado: {expected:,}")
        
        # ¿Es suficiente para ganar?
        if expected >= needed:
            print("\n" + "🎉" * 20)
            print("   ¡¡¡TIENES MANO GANADORA!!!")
            print("🎉" * 20)
            print(f"\n   ✅ JUEGA ESTAS CARTAS: {cards_str}")
            print(f"   → {hand_name} = {expected:,} puntos")
            print(f"   → Necesitas {needed:,}, ¡sobra!")
        else:
            # No es suficiente, ¿vale la pena descartar?
            gap = needed - expected
            print(f"\n   ⚠ Faltarían {gap:,} puntos")
            
            if state.discards_remaining > 0:
                # Buscar qué descartar
                discard = optimizer.find_best_discard()
                
                if discard and discard.cards:
                    discard_str = ' '.join(str(c) for c in discard.cards)
                    keep_cards = [c for c in state.hand if c not in discard.cards]
                    keep_str = ' '.join(str(c) for c in keep_cards)
                    
                    print(f"\n   🔄 RECOMENDACIÓN: DESCARTAR")
                    print(f"   ❌ Descarta: {discard_str}")
                    print(f"   ✓ Conserva: {keep_str}")
                    if discard.reasoning:
                        print(f"   📝 Razón: {discard.reasoning}")
                else:
                    print(f"\n   ✅ JUEGA LA MEJOR MANO:")
                    print(f"   → {cards_str}")
                    print(f"   (No hay mejor descarte disponible)")
            else:
                print(f"\n   ✅ JUEGA LA MEJOR MANO (no quedan descartes):")
                print(f"   → {cards_str}")
            
            # Mostrar cuántas manos quedan
            if state.hands_remaining > 1:
                remaining_needed = needed - expected
                print(f"\n   📊 Con {state.hands_remaining} manos restantes,")
                print(f"      necesitarás ~{remaining_needed // (state.hands_remaining-1):,} pts/mano")
    else:
        print("\n⚠ No se pudo calcular una jugada")
    
    print("\n" + "─" * 60)


def print_potential(state: GameState, optimizer):
    """Muestra las manos potenciales que se podrían conseguir descartando."""
    print("\n" + "═" * 60)
    print("🔮 POTENCIAL DE DESCARTE")
    print("═" * 60)
    
    try:
        potentials = optimizer.analyze_potential_hands()
        
        if not potentials:
            print("\n   No hay mejoras claras descartando.")
            return
        
        has_discards = state.discards_remaining > 0
        shown = 0
        
        for pot in potentials:
            if pot.cards_needed == 0:
                continue  # Ya tiene la mano
            
            if shown >= 3:
                break
            
            shown += 1
            prob_pct = pot.probability * 100
            
            print(f"\n   {shown}. {pot.hand_type.display_name} ({prob_pct:.0f}% prob.) → ~{pot.expected_score} pts")
            print(f"      {pot.reasoning}")
            
            if pot.cards_to_discard:
                action = "Descarta" if has_discards else "Juega (para robar)"
                discard_str = ' '.join(str(c) for c in pot.cards_to_discard[:5])
                print(f"      → {action}: {discard_str}")
        
        if not has_discards and shown > 0:
            print("\n   ⚠️ Sin descartes disponibles.")
            print("   Puedes jugar cartas débiles para robar nuevas")
            print("   y potencialmente conseguir una mejor mano.")
            
    except Exception as e:
        print(f"\n   Error analizando potencial: {e}")


def modo_automatico_continuo():
    """
    Modo automático con captura CONTINUA de pantalla.
    Analiza el juego en tiempo real sin intervención del usuario.
    """
    try:
        from poker_ai.vision import BalatroVisionSystem
        import cv2
    except ImportError as e:
        print(f"\n❌ Error importando módulo de visión: {e}")
        return
    
    clear_screen()
    print("\n" + "═" * 60)
    print("🤖 BALATRO AI - MODO AUTOMÁTICO CONTINUO")
    print("═" * 60)
    
    print("\n📌 IMPORTANTE:")
    print("   1. Balatro debe estar mostrando TUS CARTAS (en una ronda)")
    print("   2. Las cartas deben ser visibles en la parte inferior")
    print("   3. Presiona Ctrl+C para detener")
    print()
    
    # Inicializar
    print("🔍 Buscando ventana de Balatro...")
    vision = BalatroVisionSystem()
    
    if not vision.initialize():
        print("\n❌ No se encontró la ventana de Balatro")
        print("   → Abre el juego y vuelve a intentar")
        return False
    
    # Captura inicial para diagnóstico
    print("\n📸 Capturando pantalla para diagnóstico...")
    state, img = vision.capture_and_analyze()
    
    if img is not None:
        # Calcular brillo promedio
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        avg_brightness = gray.mean()
        bright_pixels = (gray > 80).sum()
        total_pixels = gray.size
        bright_ratio = bright_pixels / total_pixels * 100
        
        print(f"\n📊 Diagnóstico de imagen:")
        print(f"   Resolución: {img.shape[1]}x{img.shape[0]}")
        print(f"   Brillo promedio: {avg_brightness:.1f}/255")
        print(f"   Píxeles brillantes: {bright_ratio:.1f}%")
        
        if avg_brightness < 50:
            print("\n⚠️  La pantalla parece muy OSCURA.")
            print("   ¿Estás en una ronda con cartas visibles?")
            print("   ¿O en un menú/pantalla de transición?")
        
        if state and state.hand:
            print(f"\n✅ ¡Cartas detectadas!: {len(state.hand)}")
        else:
            print("\n⚠️  No se detectaron cartas en la captura actual.")
            print("   Asegúrate de estar en una ronda jugable.")
        
        # Guardar imagen de diagnóstico
        cv2.imwrite("balatro_diagnostico.png", img)
        debug = vision.recognizer.get_debug_image(img)
        cv2.imwrite("balatro_regiones.png", debug)
        print("\n📷 Imágenes guardadas:")
        print("   - balatro_diagnostico.png (captura original)")
        print("   - balatro_regiones.png (regiones marcadas)")
    
    print("\n" + "─" * 60)
    input("Presiona Enter para iniciar el análisis continuo...")
    
    print("\n✅ Iniciando análisis continuo...")
    print("   (La pantalla se actualizará cuando detecte cambios)")
    print("   Detección estable: se bloquea al detectar 8 cartas")
    print("   Presiona Ctrl+C para detener\n")
    
    last_hand_str = ""
    analysis_count = 0
    no_cards_count = 0
    
    try:
        while True:
            # Capturar y analizar con modo estable
            state, img = vision.capture_and_analyze(stable_mode=True)
            
            if state and state.hand and len(state.hand) >= 1:
                # Crear string único de la mano para detectar cambios
                current_hand_str = ' '.join(sorted(str(c) for c in state.hand))
                
                if current_hand_str != last_hand_str:
                    last_hand_str = current_hand_str
                    analysis_count += 1
                    no_cards_count = 0
                    
                    # Nueva mano detectada - mostrar análisis
                    clear_screen()
                    print("═" * 60)
                    lock_icon = "🔒" if vision.is_locked() else "🔍"
                    print(f"🤖 BALATRO AI - Análisis #{analysis_count} {lock_icon}")
                    print("═" * 60)
                    
                    # Mostrar estado detectado
                    print_state(state)
                    
                    # Calcular recomendación
                    optimizer = StrategyOptimizer(state)
                    
                    print_recommendation(state, optimizer)
                    
                    # Mostrar potencial de descarte
                    print_potential(state, optimizer)
                    
                    print("\n" + "─" * 60)
                    if vision.is_locked():
                        print("🔒 Detección bloqueada - esperando que juegues una mano...")
                    else:
                        print("⏳ Esperando detectar 8 cartas estables...")
                    print("   (Presiona Ctrl+C para detener)")
            else:
                no_cards_count += 1
                if no_cards_count == 1:
                    print("👀 Buscando cartas...", end="", flush=True)
                elif no_cards_count % 10 == 0:
                    print(".", end="", flush=True)
                    
                    # Cada 50 intentos sin cartas, guardar imagen de diagnóstico
                    if no_cards_count % 50 == 0 and img is not None:
                        cv2.imwrite("balatro_ultimo.png", img)
            
            # Esperar antes del siguiente análisis
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n⏹ Detenido por el usuario")
    
    print(f"\n📊 Total de análisis: {analysis_count}")
    return True


def modo_captura_unica():
    """
    Captura una sola vez y muestra el análisis.
    """
    try:
        from poker_ai.vision import BalatroVisionSystem
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        return
    
    print("\n🔍 Buscando ventana de Balatro...")
    
    vision = BalatroVisionSystem()
    
    if not vision.initialize():
        print("❌ No se encontró la ventana de Balatro")
        return
    
    print("📸 Capturando pantalla...")
    state, img = vision.capture_and_analyze()
    
    if state:
        print_state(state)
        
        if state.hand and len(state.hand) >= 1:
            optimizer = StrategyOptimizer(state)
            print_recommendation(state, optimizer)
        
        # Guardar imagen de depuración
        vision.save_debug_image("balatro_debug.png")
        print("\n📷 Imagen de depuración: balatro_debug.png")
    else:
        print("❌ No se pudo analizar el estado del juego")


def modo_debug():
    """
    Modo de depuración para ver qué está detectando el sistema.
    """
    try:
        from poker_ai.vision import BalatroVisionSystem
        import cv2
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        return
    
    print("\n🔧 MODO DEPURACIÓN")
    print("═" * 40)
    
    vision = BalatroVisionSystem()
    
    if not vision.initialize():
        print("❌ No se encontró Balatro")
        return
    
    print("\nCapturando...")
    state, img = vision.capture_and_analyze()
    
    if img is not None:
        # Guardar imágenes
        cv2.imwrite("debug_original.png", img)
        print("✓ Captura original: debug_original.png")
        
        debug_img = vision.recognizer.get_debug_image(img)
        cv2.imwrite("debug_regions.png", debug_img)
        print("✓ Regiones marcadas: debug_regions.png")
        
        # Info
        print(f"\n📐 Resolución: {img.shape[1]}x{img.shape[0]}")
        print(f"\n📦 Regiones de detección:")
        for name, region in vision.recognizer._regions.items():
            x, y, w, h = region
            print(f"   {name}: pos=({x}, {y}) size={w}x{h}")
        
        if state:
            print(f"\n🃏 Cartas detectadas: {len(state.hand)}")
            for i, c in enumerate(state.hand, 1):
                print(f"   {i}. {c}")
            
            print(f"\n📊 Puntuación detectada: {state.current_score}")
            if state.blind:
                print(f"🎯 Objetivo detectado: {state.blind.target_score}")
            print(f"✋ Manos: {state.hands_remaining}")
            print(f"🗑️ Descartes: {state.discards_remaining}")
    else:
        print("❌ Error al capturar")


def main():
    """Punto de entrada principal."""
    while True:
        clear_screen()
        print_banner()
        
        if not check_dependencies():
            input("\nPresiona Enter para salir...")
            break
        
        print("\n  Selecciona un modo:\n")
        print("    1. 🔄 Análisis CONTINUO (recomendado)")
        print("       Captura automáticamente mientras juegas")
        print()
        print("    2. 📸 Captura ÚNICA")
        print("       Analiza una sola captura de pantalla")
        print()
        print("    3. 🔧 Modo DEBUG")
        print("       Ver qué está detectando el sistema")
        print()
        print("    4. 🚪 Salir")
        print()
        
        opcion = input("  Opción (1-4): ").strip()
        
        if opcion == "1":
            modo_automatico_continuo()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "2":
            modo_captura_unica()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "3":
            modo_debug()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == "4":
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("\n⚠ Opción no válida")
            time.sleep(1)


if __name__ == "__main__":
    main()
