"""
Interfaz de usuario para Balatro AI.
UI moderna con estilo inspirado en el juego original.
"""

import sys
import threading
import time
from typing import Optional, List
from dataclasses import dataclass

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

from .game_state import GameState, Card, HandType, Suit, BlindInfo
from .optimizer import StrategyOptimizer
from .vision import BalatroVisionSystem


# =============================================================================
# TEMA VISUAL - Inspirado en Balatro
# =============================================================================

class Theme:
    """Paleta de colores moderna inspirada en Balatro."""
    
    # Fondos con gradiente simulado
    BG_PRIMARY = "#0d1117"      # Negro profundo
    BG_SECONDARY = "#161b22"    # Gris muy oscuro
    BG_TERTIARY = "#21262d"     # Gris oscuro
    BG_CARD = "#30363d"         # Gris para tarjetas
    BG_HOVER = "#484f58"        # Hover
    
    # Acentos vibrantes
    GOLD = "#ffd700"            # Oro brillante
    GOLD_DARK = "#b8860b"       # Oro oscuro
    RED = "#ff6b6b"             # Rojo coral
    RED_DARK = "#c0392b"        # Rojo oscuro
    GREEN = "#2ecc71"           # Verde esmeralda
    GREEN_DARK = "#27ae60"      # Verde oscuro
    BLUE = "#3498db"            # Azul claro
    BLUE_DARK = "#2980b9"       # Azul oscuro
    PURPLE = "#9b59b6"          # Púrpura
    CYAN = "#00d4aa"            # Cian/turquesa
    
    # Texto
    TEXT_WHITE = "#f0f6fc"
    TEXT_GRAY = "#8b949e"
    TEXT_MUTED = "#484f58"
    
    # Palos de cartas
    HEART = "#e74c3c"
    DIAMOND = "#e74c3c"
    CLUB = "#2c3e50"
    SPADE = "#2c3e50"
    
    # Fuentes
    FONT_MAIN = ("Segoe UI", 11)
    FONT_BOLD = ("Segoe UI", 11, "bold")
    FONT_LARGE = ("Segoe UI", 14, "bold")
    FONT_XLARGE = ("Segoe UI", 18, "bold")
    FONT_TITLE = ("Segoe UI", 24, "bold")
    FONT_CARDS = ("Consolas", 14, "bold")
    FONT_SMALL = ("Segoe UI", 9)


# =============================================================================
# COMPONENTES UI MODERNOS
# =============================================================================

class ModernCard(tk.Canvas):
    """Carta estilizada con sombra y efectos."""
    
    SUITS = {Suit.HEARTS: '♥', Suit.DIAMONDS: '♦', Suit.CLUBS: '♣', Suit.SPADES: '♠'}
    RANKS = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: '10'}
    
    def __init__(self, parent, card: Card, size: str = "normal", highlight: bool = False):
        # Tamaños
        sizes = {
            "small": (40, 56),
            "normal": (50, 70),
            "large": (60, 84)
        }
        w, h = sizes.get(size, sizes["normal"])
        
        super().__init__(parent, width=w, height=h, 
                        bg=Theme.BG_PRIMARY, highlightthickness=0)
        
        self.card = card
        is_red = card.suit in (Suit.HEARTS, Suit.DIAMONDS)
        color = Theme.HEART if is_red else Theme.SPADE
        
        # Fondo de carta con borde redondeado simulado
        border_color = Theme.GOLD if highlight else Theme.BG_HOVER
        self.create_rectangle(2, 2, w-2, h-2, fill="white", outline=border_color, width=2)
        
        # Rango
        rank_str = self.RANKS.get(card.rank, str(card.rank))
        self.create_text(w//2, h//3, text=rank_str, 
                        font=("Consolas", 12 if size == "small" else 14, "bold"),
                        fill=color)
        
        # Palo
        suit_str = self.SUITS.get(card.suit, '?')
        self.create_text(w//2, h*2//3, text=suit_str,
                        font=("Segoe UI", 14 if size == "small" else 18),
                        fill=color)


class GlowButton(tk.Canvas):
    """Botón con efecto de brillo."""
    
    def __init__(self, parent, text: str, command=None, 
                 color: str = Theme.BLUE, width: int = 120, height: int = 36):
        super().__init__(parent, width=width, height=height,
                        bg=Theme.BG_PRIMARY, highlightthickness=0)
        
        self.command = command
        self.color = color
        self.text = text
        self.width = width
        self.height = height
        
        self._draw_normal()
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def _draw_normal(self):
        self.delete("all")
        # Borde con gradiente simulado
        self.create_rectangle(0, 0, self.width, self.height,
                             fill=self.color, outline="")
        self.create_text(self.width//2, self.height//2, text=self.text,
                        font=Theme.FONT_BOLD, fill="white")
    
    def _draw_hover(self):
        self.delete("all")
        # Efecto más brillante
        self.create_rectangle(0, 0, self.width, self.height,
                             fill=self.color, outline=Theme.TEXT_WHITE, width=2)
        self.create_text(self.width//2, self.height//2, text=self.text,
                        font=Theme.FONT_BOLD, fill="white")
    
    def _on_enter(self, e):
        self._draw_hover()
    
    def _on_leave(self, e):
        self._draw_normal()
    
    def _on_click(self, e):
        if self.command:
            self.command()
    
    def set_color(self, color: str):
        self.color = color
        self._draw_normal()
    
    def set_text(self, text: str):
        self.text = text
        self._draw_normal()


class StatBox(tk.Frame):
    """Caja de estadísticas con icono y valor."""
    
    def __init__(self, parent, icon: str, label: str, value: str = "0",
                 color: str = Theme.TEXT_WHITE):
        super().__init__(parent, bg=Theme.BG_TERTIARY)
        
        self.config(padx=12, pady=8)
        
        # Icono y label
        header = tk.Frame(self, bg=Theme.BG_TERTIARY)
        header.pack(fill="x")
        
        tk.Label(header, text=icon, font=("Segoe UI", 14),
                fg=color, bg=Theme.BG_TERTIARY).pack(side="left")
        tk.Label(header, text=f" {label}", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_GRAY, bg=Theme.BG_TERTIARY).pack(side="left")
        
        # Valor
        self.value_label = tk.Label(self, text=value, font=Theme.FONT_LARGE,
                                   fg=color, bg=Theme.BG_TERTIARY)
        self.value_label.pack(anchor="w")
    
    def set_value(self, value: str, color: str = None):
        self.value_label.config(text=value)
        if color:
            self.value_label.config(fg=color)


class SectionHeader(tk.Frame):
    """Encabezado de sección con línea decorativa."""
    
    def __init__(self, parent, text: str, icon: str = ""):
        super().__init__(parent, bg=Theme.BG_PRIMARY)
        
        # Línea izquierda
        tk.Frame(self, bg=Theme.GOLD, width=3, height=20).pack(side="left", padx=(0, 8))
        
        # Texto
        full_text = f"{icon} {text}" if icon else text
        tk.Label(self, text=full_text, font=Theme.FONT_LARGE,
                fg=Theme.GOLD, bg=Theme.BG_PRIMARY).pack(side="left")


class HandDisplay(tk.Frame):
    """Display de mano con cartas estilizadas."""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG_PRIMARY)
        
        self.header = SectionHeader(self, "MANO DETECTADA", "🃏")
        self.header.pack(fill="x", pady=(0, 10))
        
        self.cards_frame = tk.Frame(self, bg=Theme.BG_PRIMARY)
        self.cards_frame.pack()
        
        self.info_label = tk.Label(self, text="Esperando detección...",
                                  font=Theme.FONT_SMALL, fg=Theme.TEXT_GRAY,
                                  bg=Theme.BG_PRIMARY)
        self.info_label.pack(pady=(8, 0))
    
    def update(self, cards: List[Card], locked: bool = False):
        # Limpiar
        for w in self.cards_frame.winfo_children():
            w.destroy()
        
        if not cards:
            self.info_label.config(text="No se detectaron cartas", fg=Theme.TEXT_MUTED)
            return
        
        # Mostrar cartas
        for card in cards:
            c = ModernCard(self.cards_frame, card, size="normal")
            c.pack(side="left", padx=2)
        
        # Info
        lock_icon = "🔒" if locked else "🔍"
        self.info_label.config(
            text=f"{lock_icon} {len(cards)} cartas en mano",
            fg=Theme.GREEN if locked else Theme.TEXT_GRAY
        )


class RecommendationBox(tk.Frame):
    """Caja de recomendación principal con estilo destacado."""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG_SECONDARY)
        self.config(padx=16, pady=12)
        
        # Header
        self.header_label = tk.Label(self, text="RECOMENDACIÓN",
                                    font=Theme.FONT_BOLD, fg=Theme.GOLD,
                                    bg=Theme.BG_SECONDARY)
        self.header_label.pack(anchor="w")
        
        # Acción principal
        self.action_frame = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.action_frame.pack(fill="x", pady=(8, 0))
        
        self.action_icon = tk.Label(self.action_frame, text="▶",
                                   font=("Segoe UI", 20), fg=Theme.BLUE,
                                   bg=Theme.BG_SECONDARY)
        self.action_icon.pack(side="left")
        
        self.action_text = tk.Label(self.action_frame, text="Analizando...",
                                   font=Theme.FONT_XLARGE, fg=Theme.TEXT_WHITE,
                                   bg=Theme.BG_SECONDARY)
        self.action_text.pack(side="left", padx=(8, 0))
        
        # Cartas a jugar
        self.cards_frame = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.cards_frame.pack(fill="x", pady=(12, 0))
        
        # Score esperado
        self.score_frame = tk.Frame(self, bg=Theme.BG_TERTIARY)
        self.score_frame.pack(fill="x", pady=(12, 0))
        
        tk.Label(self.score_frame, text="Puntuación esperada:",
                font=Theme.FONT_SMALL, fg=Theme.TEXT_GRAY,
                bg=Theme.BG_TERTIARY).pack(side="left", padx=8, pady=6)
        
        self.score_label = tk.Label(self.score_frame, text="0 pts",
                                   font=Theme.FONT_LARGE, fg=Theme.GREEN,
                                   bg=Theme.BG_TERTIARY)
        self.score_label.pack(side="right", padx=8, pady=6)
        
        # Razón
        self.reason_label = tk.Label(self, text="",
                                    font=Theme.FONT_SMALL, fg=Theme.TEXT_GRAY,
                                    bg=Theme.BG_SECONDARY, wraplength=350)
        self.reason_label.pack(anchor="w", pady=(8, 0))
    
    def update_play(self, cards: List[Card], hand_name: str, score: int, 
                   is_winner: bool, reason: str = ""):
        # Limpiar cartas anteriores
        for w in self.cards_frame.winfo_children():
            w.destroy()
        
        if is_winner:
            self.action_icon.config(text="🎉", fg=Theme.GREEN)
            self.action_text.config(text=f"¡GANADORA! {hand_name}", fg=Theme.GREEN)
            self.header_label.config(fg=Theme.GREEN)
        else:
            self.action_icon.config(text="▶", fg=Theme.BLUE)
            self.action_text.config(text=f"JUGAR: {hand_name}", fg=Theme.TEXT_WHITE)
            self.header_label.config(fg=Theme.GOLD)
        
        # Mostrar cartas
        for card in cards:
            c = ModernCard(self.cards_frame, card, size="normal", highlight=True)
            c.pack(side="left", padx=2)
        
        self.score_label.config(text=f"{score:,} pts")
        self.reason_label.config(text=reason)
    
    def update_discard(self, cards: List[Card], reason: str):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        
        self.action_icon.config(text="🔄", fg=Theme.RED)
        self.action_text.config(text="DESCARTAR", fg=Theme.RED)
        self.header_label.config(fg=Theme.GOLD)
        
        for card in cards:
            c = ModernCard(self.cards_frame, card, size="normal")
            c.pack(side="left", padx=2)
        
        self.score_label.config(text="—")
        self.reason_label.config(text=reason)
    
    def set_waiting(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        
        self.action_icon.config(text="👀", fg=Theme.TEXT_GRAY)
        self.action_text.config(text="Buscando cartas...", fg=Theme.TEXT_GRAY)
        self.score_label.config(text="—")
        self.reason_label.config(text="")


class PlaysListBox(tk.Frame):
    """Lista de jugadas posibles con scroll."""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG_PRIMARY)
        
        header = SectionHeader(self, "MEJORES JUGADAS", "📊")
        header.pack(fill="x", pady=(0, 8))
        
        # Lista con estilo
        list_frame = tk.Frame(self, bg=Theme.BG_TERTIARY)
        list_frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            bg=Theme.BG_TERTIARY,
            fg=Theme.TEXT_WHITE,
            selectbackground=Theme.BLUE,
            selectforeground="white",
            highlightthickness=0,
            borderwidth=0,
            height=6,
            activestyle="none"
        )
        self.listbox.pack(fill="both", expand=True, padx=4, pady=4)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", 
                                command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
    
    def update(self, optimizer: StrategyOptimizer):
        self.listbox.delete(0, "end")
        
        try:
            plays = optimizer.find_all_plays(top_n=8)
            for i, play in enumerate(plays, 1):
                cards_str = " ".join(str(c) for c in play.cards)
                hand_name = play.hand_type.display_name if play.hand_type else "?"
                # Formato: ranking | puntos | tipo | cartas
                line = f" {i}. {play.expected_score:>5} pts │ {hand_name:<13} │ {cards_str}"
                self.listbox.insert("end", line)
                
                # Color alternado
                if i % 2 == 0:
                    self.listbox.itemconfig(i-1, bg=Theme.BG_CARD)
        except Exception as e:
            self.listbox.insert("end", f" Error: {e}")


class PotentialBox(tk.Frame):
    """Caja de potencial de descarte mejorada."""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG_PRIMARY)
        
        header = SectionHeader(self, "POTENCIAL DE MEJORA", "🔮")
        header.pack(fill="x", pady=(0, 8))
        
        self.content = tk.Frame(self, bg=Theme.BG_PRIMARY)
        self.content.pack(fill="both", expand=True)
        
        self.empty_label = tk.Label(self.content, text="Analizando opciones...",
                                   font=Theme.FONT_SMALL, fg=Theme.TEXT_MUTED,
                                   bg=Theme.BG_PRIMARY)
        self.empty_label.pack(pady=20)
    
    def update(self, optimizer: StrategyOptimizer, has_discards: bool = True):
        # Limpiar
        for w in self.content.winfo_children():
            w.destroy()
        
        try:
            potentials = optimizer.analyze_potential_hands()
            
            if not potentials:
                tk.Label(self.content, text="No hay mejoras claras",
                        font=Theme.FONT_SMALL, fg=Theme.TEXT_MUTED,
                        bg=Theme.BG_PRIMARY).pack(pady=20)
                return
            
            shown = 0
            for pot in potentials:
                if pot.cards_needed == 0:
                    continue
                if shown >= 3:
                    break
                shown += 1
                
                # Frame para cada opción
                opt_frame = tk.Frame(self.content, bg=Theme.BG_TERTIARY)
                opt_frame.pack(fill="x", pady=3, padx=2)
                
                # Header: Tipo + Probabilidad + Puntos
                hdr = tk.Frame(opt_frame, bg=Theme.BG_TERTIARY)
                hdr.pack(fill="x", padx=8, pady=(6, 2))
                
                prob = pot.probability * 100
                prob_color = Theme.GREEN if prob >= 20 else Theme.GOLD if prob >= 10 else Theme.TEXT_GRAY
                
                tk.Label(hdr, text=f"→ {pot.hand_type.display_name}",
                        font=Theme.FONT_BOLD, fg=Theme.CYAN,
                        bg=Theme.BG_TERTIARY).pack(side="left")
                
                tk.Label(hdr, text=f"({prob:.0f}%)",
                        font=Theme.FONT_SMALL, fg=prob_color,
                        bg=Theme.BG_TERTIARY).pack(side="left", padx=6)
                
                tk.Label(hdr, text=f"~{pot.expected_score} pts",
                        font=Theme.FONT_BOLD, fg=Theme.GREEN,
                        bg=Theme.BG_TERTIARY).pack(side="right")
                
                # Descripción
                tk.Label(opt_frame, text=pot.reasoning,
                        font=Theme.FONT_SMALL, fg=Theme.TEXT_GRAY,
                        bg=Theme.BG_TERTIARY, wraplength=280,
                        justify="left").pack(anchor="w", padx=8)
                
                # Cartas a descartar
                if pot.cards_to_discard:
                    cards_str = " ".join(str(c) for c in pot.cards_to_discard[:5])
                    action = "Descarta:" if has_discards else "Juega:"
                    color = Theme.RED if has_discards else Theme.GOLD
                    
                    tk.Label(opt_frame, text=f"{action} {cards_str}",
                            font=("Consolas", 9), fg=color,
                            bg=Theme.BG_TERTIARY).pack(anchor="w", padx=8, pady=(2, 6))
            
            if not has_discards and shown > 0:
                tk.Label(self.content, text="⚠️ Sin descartes disponibles",
                        font=Theme.FONT_SMALL, fg=Theme.GOLD,
                        bg=Theme.BG_PRIMARY).pack(pady=4)
                        
        except Exception as e:
            tk.Label(self.content, text=f"Error: {e}",
                    font=Theme.FONT_SMALL, fg=Theme.RED,
                    bg=Theme.BG_PRIMARY).pack(pady=10)


# =============================================================================
# APLICACIÓN PRINCIPAL
# =============================================================================

class BalatroAIApp:
    """Aplicación principal con diseño moderno."""
    
    def __init__(self):
        if not TK_AVAILABLE:
            raise RuntimeError("Tkinter no disponible")
        
        self.root = tk.Tk()
        self.root.title("Balatro AI")
        self.root.geometry("950x700")
        self.root.configure(bg=Theme.BG_PRIMARY)
        self.root.minsize(800, 600)
        
        # Estado
        self.vision: Optional[BalatroVisionSystem] = None
        self.current_state: Optional[GameState] = None
        self.running = False
        self.last_hand_str = ""
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz."""
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=Theme.BG_SECONDARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Logo y título
        title_frame = tk.Frame(header, bg=Theme.BG_SECONDARY)
        title_frame.pack(side="left", padx=20, pady=15)
        
        tk.Label(title_frame, text="🃏", font=("Segoe UI", 28),
                fg=Theme.GOLD, bg=Theme.BG_SECONDARY).pack(side="left")
        
        title_text = tk.Frame(title_frame, bg=Theme.BG_SECONDARY)
        title_text.pack(side="left", padx=(10, 0))
        
        tk.Label(title_text, text="BALATRO AI", font=Theme.FONT_TITLE,
                fg=Theme.TEXT_WHITE, bg=Theme.BG_SECONDARY).pack(anchor="w")
        tk.Label(title_text, text="Asistente Inteligente", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_GRAY, bg=Theme.BG_SECONDARY).pack(anchor="w")
        
        # Botones de control
        ctrl_frame = tk.Frame(header, bg=Theme.BG_SECONDARY)
        ctrl_frame.pack(side="right", padx=20)
        
        self.start_btn = GlowButton(ctrl_frame, "▶ INICIAR", 
                                    command=self._toggle, color=Theme.GREEN)
        self.start_btn.pack(side="left", padx=5)
        
        self.unlock_btn = GlowButton(ctrl_frame, "🔓 UNLOCK",
                                    command=self._force_unlock, color=Theme.BLUE)
        self.unlock_btn.pack(side="left", padx=5)
        
        # ===== STATS BAR =====
        stats_bar = tk.Frame(self.root, bg=Theme.BG_TERTIARY)
        stats_bar.pack(fill="x", padx=15, pady=(15, 0))
        
        self.stat_target = StatBox(stats_bar, "🎯", "Objetivo", "—", Theme.GOLD)
        self.stat_target.pack(side="left", padx=(0, 10))
        
        self.stat_needed = StatBox(stats_bar, "📊", "Necesitas", "—", Theme.RED)
        self.stat_needed.pack(side="left", padx=10)
        
        self.stat_hands = StatBox(stats_bar, "✋", "Manos", "—", Theme.BLUE)
        self.stat_hands.pack(side="left", padx=10)
        
        self.stat_discards = StatBox(stats_bar, "🔄", "Descartes", "—", Theme.PURPLE)
        self.stat_discards.pack(side="left", padx=10)
        
        # Status
        self.status_label = tk.Label(stats_bar, text="⏸ Detenido",
                                    font=Theme.FONT_BOLD, fg=Theme.TEXT_GRAY,
                                    bg=Theme.BG_TERTIARY)
        self.status_label.pack(side="right", padx=15, pady=8)
        
        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=Theme.BG_PRIMARY)
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Layout: Izquierda (listas) | Centro (mano + recomendación) | Derecha (potencial)
        
        # Columna izquierda
        left = tk.Frame(main, bg=Theme.BG_PRIMARY, width=300)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        
        self.plays_list = PlaysListBox(left)
        self.plays_list.pack(fill="both", expand=True)
        
        # Columna central
        center = tk.Frame(main, bg=Theme.BG_PRIMARY)
        center.pack(side="left", fill="both", expand=True, padx=10)
        
        self.hand_display = HandDisplay(center)
        self.hand_display.pack(fill="x", pady=(0, 15))
        
        self.recommendation = RecommendationBox(center)
        self.recommendation.pack(fill="x")
        
        # Columna derecha
        right = tk.Frame(main, bg=Theme.BG_PRIMARY, width=320)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)
        
        self.potential_box = PotentialBox(right)
        self.potential_box.pack(fill="both", expand=True)
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg=Theme.BG_SECONDARY, height=30)
        footer.pack(fill="x", side="bottom")
        
        tk.Label(footer, text="Presiona INICIAR para comenzar el análisis automático",
                font=Theme.FONT_SMALL, fg=Theme.TEXT_MUTED,
                bg=Theme.BG_SECONDARY).pack(pady=6)
    
    def _toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()
    
    def _start(self):
        self.status_label.config(text="🔍 Buscando Balatro...", fg=Theme.BLUE)
        self.root.update()
        
        try:
            self.vision = BalatroVisionSystem()
            if not self.vision.initialize():
                self.status_label.config(text="❌ No se encontró Balatro", fg=Theme.RED)
                messagebox.showerror("Error", 
                    "No se encontró la ventana de Balatro.\nAbre el juego y vuelve a intentar.")
                return
            
            self.running = True
            self.start_btn.set_text("⏹ DETENER")
            self.start_btn.set_color(Theme.RED)
            self.status_label.config(text="✅ Analizando...", fg=Theme.GREEN)
            
            # Thread de captura
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
        except Exception as e:
            self.status_label.config(text=f"❌ Error: {e}", fg=Theme.RED)
    
    def _stop(self):
        self.running = False
        self.start_btn.set_text("▶ INICIAR")
        self.start_btn.set_color(Theme.GREEN)
        self.status_label.config(text="⏸ Detenido", fg=Theme.TEXT_GRAY)
    
    def _force_unlock(self):
        if self.vision:
            self.vision.force_unlock()
            self.last_hand_str = ""
            self.status_label.config(text="🔓 Desbloqueado", fg=Theme.CYAN)
    
    def _capture_loop(self):
        while self.running:
            try:
                state, img = self.vision.capture_and_analyze(stable_mode=True)
                
                if state and state.hand:
                    current = ' '.join(sorted(str(c) for c in state.hand))
                    
                    if current != self.last_hand_str:
                        self.last_hand_str = current
                        self.current_state = state
                        self.root.after(0, self._update_ui, state)
                    
                    self.root.after(0, self._update_status)
                    
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(0.5)
    
    def _update_status(self):
        if self.vision:
            locked = self.vision.is_locked()
            icon = "🔒" if locked else "🔍"
            text = "Bloqueado" if locked else "Buscando"
            color = Theme.GREEN if locked else Theme.BLUE
            
            n_cards = len(self.current_state.hand) if self.current_state else 0
            self.status_label.config(text=f"{icon} {text} ({n_cards} cartas)", fg=color)
    
    def _update_ui(self, state: GameState):
        try:
            # Stats
            target = state.blind.target_score if state.blind else 300
            needed = max(0, target - state.current_score)
            
            self.stat_target.set_value(f"{target:,}")
            self.stat_needed.set_value(f"{needed:,}", 
                                       Theme.GREEN if needed == 0 else Theme.RED)
            self.stat_hands.set_value(str(state.hands_remaining))
            self.stat_discards.set_value(str(state.discards_remaining))
            
            # Mano
            locked = self.vision.is_locked() if self.vision else False
            self.hand_display.update(state.hand, locked)
            
            # Optimizador
            optimizer = StrategyOptimizer(state)
            
            # Lista de jugadas
            self.plays_list.update(optimizer)
            
            # Potencial
            self.potential_box.update(optimizer, state.discards_remaining > 0)
            
            # Recomendación
            best = optimizer.find_best_play()
            if best and best.cards:
                is_winner = best.expected_score >= needed
                hand_name = best.hand_type.display_name if best.hand_type else "Carta Alta"
                self.recommendation.update_play(
                    best.cards, hand_name, best.expected_score,
                    is_winner, best.reasoning
                )
            else:
                self.recommendation.set_waiting()
                
        except Exception as e:
            print(f"Error UI: {e}")
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        self.running = False
        self.root.destroy()


# =============================================================================
# OVERLAY COMPACTO
# =============================================================================

class BalatroOverlay:
    """Overlay flotante compacto y moderno."""
    
    def __init__(self):
        if not TK_AVAILABLE:
            raise RuntimeError("Tkinter no disponible")
        
        self.root = tk.Tk()
        self.root.title("Balatro AI")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        self.root.overrideredirect(True)
        self.root.geometry("380x180+50+50")
        self.root.configure(bg=Theme.BG_SECONDARY)
        
        self.vision = None
        self.running = False
        self.last_hand = ""
        
        self._build()
        self._make_draggable()
    
    def _build(self):
        # Borde decorativo
        border = tk.Frame(self.root, bg=Theme.GOLD)
        border.pack(fill="both", expand=True, padx=2, pady=2)
        
        main = tk.Frame(border, bg=Theme.BG_SECONDARY)
        main.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(main, bg=Theme.BG_TERTIARY)
        header.pack(fill="x")
        
        tk.Label(header, text="🃏 Balatro AI", font=Theme.FONT_BOLD,
                fg=Theme.GOLD, bg=Theme.BG_TERTIARY).pack(side="left", padx=8, pady=4)
        
        tk.Button(header, text="✕", font=("Segoe UI", 9), 
                 bg=Theme.RED, fg="white", bd=0,
                 command=self._close).pack(side="right", padx=4, pady=2)
        
        self.toggle_btn = tk.Button(header, text="▶", font=("Segoe UI", 9),
                                   bg=Theme.GREEN, fg="white", bd=0,
                                   command=self._toggle)
        self.toggle_btn.pack(side="right", padx=2, pady=2)
        
        # Contenido
        content = tk.Frame(main, bg=Theme.BG_SECONDARY)
        content.pack(fill="both", expand=True, padx=10, pady=8)
        
        self.status = tk.Label(content, text="Presiona ▶",
                              font=Theme.FONT_SMALL, fg=Theme.TEXT_GRAY,
                              bg=Theme.BG_SECONDARY)
        self.status.pack()
        
        self.action = tk.Label(content, text="",
                              font=Theme.FONT_LARGE, fg=Theme.TEXT_WHITE,
                              bg=Theme.BG_SECONDARY)
        self.action.pack(pady=4)
        
        self.cards = tk.Label(content, text="",
                             font=("Consolas", 16, "bold"), fg=Theme.CYAN,
                             bg=Theme.BG_SECONDARY)
        self.cards.pack(pady=2)
        
        self.score = tk.Label(content, text="",
                             font=Theme.FONT_BOLD, fg=Theme.GREEN,
                             bg=Theme.BG_SECONDARY)
        self.score.pack()
    
    def _make_draggable(self):
        self.root.bind('<Button-1>', lambda e: setattr(self, '_drag', (e.x, e.y)))
        self.root.bind('<B1-Motion>', lambda e: self.root.geometry(
            f"+{self.root.winfo_x() + e.x - self._drag[0]}+{self.root.winfo_y() + e.y - self._drag[1]}"))
    
    def _toggle(self):
        if self.running:
            self.running = False
            self.toggle_btn.config(text="▶", bg=Theme.GREEN)
            self.status.config(text="⏸ Detenido", fg=Theme.TEXT_GRAY)
        else:
            self._start()
    
    def _start(self):
        self.status.config(text="🔍 Buscando...", fg=Theme.BLUE)
        self.root.update()
        
        try:
            self.vision = BalatroVisionSystem()
            if not self.vision.initialize():
                self.status.config(text="❌ No encontrado", fg=Theme.RED)
                return
            
            self.running = True
            self.toggle_btn.config(text="⏹", bg=Theme.RED)
            self._loop()
        except Exception as e:
            self.status.config(text=f"❌ {e}", fg=Theme.RED)
    
    def _loop(self):
        if not self.running:
            return
        
        try:
            state, _ = self.vision.capture_and_analyze()
            if state and state.hand:
                current = ' '.join(sorted(str(c) for c in state.hand))
                if current != self.last_hand:
                    self.last_hand = current
                    self._update(state)
        except Exception as e:
            print(f"Error: {e}")
        
        self.root.after(500, self._loop)
    
    def _update(self, state: GameState):
        optimizer = StrategyOptimizer(state)
        best = optimizer.find_best_play()
        
        target = state.blind.target_score if state.blind else 300
        needed = target - state.current_score
        
        self.status.config(text=f"✅ {len(state.hand)} cartas | 🎯 {target:,}", fg=Theme.GREEN)
        
        if best and best.cards:
            is_winner = best.expected_score >= needed
            name = best.hand_type.display_name if best.hand_type else "?"
            
            if is_winner:
                self.action.config(text=f"🎉 ¡GANADORA! {name}", fg=Theme.GREEN)
            else:
                self.action.config(text=f"▶ {name}", fg=Theme.BLUE)
            
            self.cards.config(text=" ".join(str(c) for c in best.cards))
            self.score.config(text=f"→ {best.expected_score:,} pts")
    
    def _close(self):
        self.running = False
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("Iniciando Balatro AI...")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--overlay":
        BalatroOverlay().run()
    else:
        BalatroAIApp().run()


if __name__ == "__main__":
    main()
