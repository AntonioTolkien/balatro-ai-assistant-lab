"""
Modelo del estado del juego de Balatro.
Define todas las estructuras de datos necesarias para representar el estado actual.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from collections import Counter
import itertools


# =============================================================================
# ENUMERACIONES BÁSICAS
# =============================================================================

class Suit(Enum):
    """Palos de las cartas."""
    HEARTS = "H"
    DIAMONDS = "D"
    CLUBS = "C"
    SPADES = "S"
    
    @property
    def symbol(self) -> str:
        symbols = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
        return symbols[self.value]
    
    @property
    def color(self) -> str:
        return "red" if self in (Suit.HEARTS, Suit.DIAMONDS) else "black"


class Enhancement(Enum):
    """Mejoras de cartas en Balatro."""
    NONE = auto()
    BONUS = auto()      # +30 chips
    MULT = auto()       # +4 mult
    WILD = auto()       # Cuenta como cualquier palo
    GLASS = auto()      # x2 mult, puede romperse
    STEEL = auto()      # x1.5 mult mientras está en mano
    STONE = auto()      # +50 chips, sin rango ni palo
    GOLD = auto()       # +$3 al final de ronda
    LUCKY = auto()      # 1/5 +20 mult, 1/15 +$20


class Edition(Enum):
    """Ediciones de cartas/jokers."""
    NONE = auto()
    FOIL = auto()       # +50 chips
    HOLOGRAPHIC = auto() # +10 mult
    POLYCHROME = auto()  # x1.5 mult
    NEGATIVE = auto()    # +1 slot joker


class Seal(Enum):
    """Sellos de cartas."""
    NONE = auto()
    GOLD = auto()       # +$3 cuando se juega
    RED = auto()        # Retriggea la carta
    BLUE = auto()       # Crea un planeta al final
    PURPLE = auto()     # Crea un tarot al descartar


class HandType(Enum):
    """Tipos de manos de póker en Balatro."""
    HIGH_CARD = ("High Card", 5, 1)
    PAIR = ("Pair", 10, 2)
    TWO_PAIR = ("Two Pair", 20, 2)
    THREE_OF_A_KIND = ("Three of a Kind", 30, 3)
    STRAIGHT = ("Straight", 30, 4)
    FLUSH = ("Flush", 35, 4)
    FULL_HOUSE = ("Full House", 40, 4)
    FOUR_OF_A_KIND = ("Four of a Kind", 60, 7)
    STRAIGHT_FLUSH = ("Straight Flush", 100, 8)
    ROYAL_FLUSH = ("Royal Flush", 100, 8)
    FIVE_OF_A_KIND = ("Five of a Kind", 120, 12)
    FLUSH_HOUSE = ("Flush House", 140, 14)
    FLUSH_FIVE = ("Flush Five", 160, 16)
    
    def __init__(self, display_name: str, base_chips: int, base_mult: int):
        self.display_name = display_name
        self.base_chips = base_chips
        self.base_mult = base_mult


# =============================================================================
# MODELO DE CARTA
# =============================================================================

@dataclass
class Card:
    """Representa una carta de Balatro."""
    rank: int  # 2-14 (J=11, Q=12, K=13, A=14)
    suit: Suit
    enhancement: Enhancement = Enhancement.NONE
    edition: Edition = Edition.NONE
    seal: Seal = Seal.NONE
    
    @property
    def chip_value(self) -> int:
        """Valor en chips de la carta."""
        if self.enhancement == Enhancement.STONE:
            return 50
        if 2 <= self.rank <= 10:
            base = self.rank
        elif self.rank in (11, 12, 13):  # J, Q, K
            base = 10
        else:  # A
            base = 11
        
        # Aplicar mejoras
        if self.enhancement == Enhancement.BONUS:
            base += 30
        if self.edition == Edition.FOIL:
            base += 50
            
        return base
    
    @property
    def rank_name(self) -> str:
        names = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        return names.get(self.rank, str(self.rank))
    
    def __str__(self) -> str:
        return f"{self.rank_name}{self.suit.symbol}"
    
    def __hash__(self):
        return hash((self.rank, self.suit, self.enhancement, self.edition, self.seal))
    
    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return (self.rank == other.rank and 
                self.suit == other.suit and
                self.enhancement == other.enhancement)


# =============================================================================
# MODELO DE JOKER
# =============================================================================

@dataclass
class JokerEffect:
    """Efecto de un Joker."""
    flat_chips: int = 0
    flat_mult: int = 0
    x_mult: float = 1.0
    chip_mult: float = 1.0  # Multiplicador de chips
    conditional: Optional[str] = None  # Condición para activarse
    trigger: Optional[str] = None  # Cuándo se activa


@dataclass 
class Joker:
    """Representa un Joker de Balatro."""
    name: str
    rarity: str  # common, uncommon, rare, legendary
    edition: Edition = Edition.NONE
    effect: JokerEffect = field(default_factory=JokerEffect)
    
    def calculate_effect(self, hand: List[Card], hand_type: HandType, 
                         game_state: 'GameState') -> Tuple[int, int, float]:
        """
        Calcula el efecto del Joker.
        Retorna (chips_bonus, mult_bonus, x_mult)
        """
        return (self.effect.flat_chips, self.effect.flat_mult, self.effect.x_mult)


# =============================================================================
# BASE DE DATOS DE JOKERS COMUNES
# =============================================================================

JOKER_DATABASE: Dict[str, JokerEffect] = {
    # Jokers básicos
    "Joker": JokerEffect(flat_mult=4),
    "Greedy Joker": JokerEffect(flat_mult=3),  # +3 mult por ♦ jugado
    "Lusty Joker": JokerEffect(flat_mult=3),   # +3 mult por ♥ jugado
    "Wrathful Joker": JokerEffect(flat_mult=3), # +3 mult por ♠ jugado
    "Gluttonous Joker": JokerEffect(flat_mult=3), # +3 mult por ♣ jugado
    "Jolly Joker": JokerEffect(flat_mult=8, conditional="pair"),
    "Zany Joker": JokerEffect(flat_mult=12, conditional="three_of_a_kind"),
    "Mad Joker": JokerEffect(flat_mult=10, conditional="two_pair"),
    "Crazy Joker": JokerEffect(flat_mult=12, conditional="straight"),
    "Droll Joker": JokerEffect(flat_mult=10, conditional="flush"),
    "Sly Joker": JokerEffect(flat_chips=50, conditional="pair"),
    "Wily Joker": JokerEffect(flat_chips=100, conditional="three_of_a_kind"),
    "Clever Joker": JokerEffect(flat_chips=80, conditional="two_pair"),
    "Devious Joker": JokerEffect(flat_chips=100, conditional="straight"),
    "Crafty Joker": JokerEffect(flat_chips=80, conditional="flush"),
    "Half Joker": JokerEffect(flat_mult=20, conditional="hand_size_lte_3"),
    "Banner": JokerEffect(flat_chips=30),  # +30 chips por descarte restante
    "Mystic Summit": JokerEffect(flat_mult=15, conditional="discards_0"),
    "Fibonacci": JokerEffect(flat_mult=8),  # +8 mult por A, 2, 3, 5, 8
    "Steel Joker": JokerEffect(x_mult=1.0),  # x0.2 por cada carta Steel
    "Scary Face": JokerEffect(flat_chips=30),  # +30 chips por cara
    "Abstract Joker": JokerEffect(flat_mult=3),  # +3 mult por joker
    "Ride the Bus": JokerEffect(flat_mult=1),  # +1 mult por mano sin cara
    "Blackboard": JokerEffect(x_mult=3.0, conditional="all_spades_clubs"),
    "The Duo": JokerEffect(x_mult=2.0, conditional="pair"),
    "The Trio": JokerEffect(x_mult=3.0, conditional="three_of_a_kind"),
    "The Family": JokerEffect(x_mult=4.0, conditional="four_of_a_kind"),
    "The Order": JokerEffect(x_mult=3.0, conditional="straight"),
    "The Tribe": JokerEffect(x_mult=2.0, conditional="flush"),
}


def create_joker(name: str, edition: Edition = Edition.NONE) -> Joker:
    """Crea un Joker desde la base de datos."""
    effect = JOKER_DATABASE.get(name, JokerEffect())
    return Joker(name=name, rarity="common", edition=edition, effect=effect)


# =============================================================================
# NIVELES DE MANO
# =============================================================================

@dataclass
class HandLevel:
    """Nivel de una mano de póker (afecta chips y mult base)."""
    hand_type: HandType
    level: int = 1
    
    @property
    def chips(self) -> int:
        """Chips base según nivel."""
        base = self.hand_type.base_chips
        # Cada nivel añade chips según el tipo de mano
        level_bonus = {
            HandType.HIGH_CARD: 10,
            HandType.PAIR: 15,
            HandType.TWO_PAIR: 20,
            HandType.THREE_OF_A_KIND: 20,
            HandType.STRAIGHT: 30,
            HandType.FLUSH: 15,
            HandType.FULL_HOUSE: 25,
            HandType.FOUR_OF_A_KIND: 30,
            HandType.STRAIGHT_FLUSH: 40,
            HandType.ROYAL_FLUSH: 40,
            HandType.FIVE_OF_A_KIND: 35,
            HandType.FLUSH_HOUSE: 40,
            HandType.FLUSH_FIVE: 50,
        }
        return base + (self.level - 1) * level_bonus.get(self.hand_type, 10)
    
    @property
    def mult(self) -> int:
        """Mult base según nivel."""
        base = self.hand_type.base_mult
        # Cada nivel añade +1 mult (aproximado)
        return base + (self.level - 1)


# =============================================================================
# ESTADO COMPLETO DEL JUEGO
# =============================================================================

@dataclass
class BlindInfo:
    """Información del blind actual."""
    name: str
    target_score: int
    reward: int = 0
    is_boss: bool = False
    special_effect: Optional[str] = None  # Efecto especial del boss


@dataclass
class GameState:
    """Estado completo del juego de Balatro."""
    
    # Mano actual del jugador (cartas en mano, max 8)
    hand: List[Card] = field(default_factory=list)
    
    # Cartas restantes en el mazo
    deck: List[Card] = field(default_factory=list)
    
    # Jokers activos (max 5 normalmente)
    jokers: List[Joker] = field(default_factory=list)
    
    # Niveles de cada tipo de mano
    hand_levels: Dict[HandType, int] = field(default_factory=lambda: {ht: 1 for ht in HandType})
    
    # Recursos
    hands_remaining: int = 4
    discards_remaining: int = 3
    money: int = 0
    
    # Blind actual
    blind: BlindInfo = field(default_factory=lambda: BlindInfo("Small Blind", 300))
    
    # Puntuación actual en esta ronda
    current_score: int = 0
    
    # Información adicional
    ante: int = 1
    round_in_ante: int = 1  # 1=small, 2=big, 3=boss
    
    # Cartas jugadas esta ronda (para tracking)
    cards_played_this_round: List[Card] = field(default_factory=list)
    
    @property
    def score_needed(self) -> int:
        """Puntuación que falta para ganar el blind."""
        return max(0, self.blind.target_score - self.current_score)
    
    @property
    def can_play(self) -> bool:
        """¿Se puede jugar una mano?"""
        return self.hands_remaining > 0 and len(self.hand) > 0
    
    @property
    def can_discard(self) -> bool:
        """¿Se puede descartar?"""
        return self.discards_remaining > 0 and len(self.hand) > 0
    
    def get_hand_level(self, hand_type: HandType) -> HandLevel:
        """Obtiene el nivel de una mano."""
        level = self.hand_levels.get(hand_type, 1)
        return HandLevel(hand_type, level)
    
    def copy(self) -> 'GameState':
        """Crea una copia del estado."""
        import copy
        return copy.deepcopy(self)


# =============================================================================
# EVALUADOR DE MANOS
# =============================================================================

class HandEvaluator:
    """Evalúa manos de póker y calcula puntuaciones."""
    
    @staticmethod
    def get_hand_type(cards: List[Card]) -> Tuple[HandType, List[Card]]:
        """
        Determina el tipo de mano y las cartas que puntúan.
        
        Returns:
            Tuple de (HandType, lista de cartas que puntúan)
        """
        if len(cards) == 0:
            return HandType.HIGH_CARD, []
        
        # Obtener valores y palos (considerar wild cards)
        ranks = [c.rank for c in cards]
        suits = []
        for c in cards:
            if c.enhancement == Enhancement.WILD:
                suits.append("WILD")
            elif c.enhancement != Enhancement.STONE:
                suits.append(c.suit)
        
        rank_counts = Counter(ranks)
        suit_counts = Counter(s for s in suits if s != "WILD")
        wild_count = suits.count("WILD")
        
        sorted_counts = sorted(rank_counts.values(), reverse=True)
        
        # Verificar flush (5 del mismo palo)
        is_flush = False
        if len(cards) >= 5:
            for suit, count in suit_counts.items():
                if count + wild_count >= 5:
                    is_flush = True
                    break
            if wild_count >= 5:
                is_flush = True
        
        # Verificar straight
        is_straight = HandEvaluator._is_straight(ranks)
        
        # Determinar tipo de mano
        if len(cards) >= 5:
            # Flush Five (5 del mismo rango y palo)
            if is_flush and sorted_counts[0] >= 5:
                scoring = [c for c in cards if rank_counts[c.rank] >= 5][:5]
                return HandType.FLUSH_FIVE, scoring
            
            # Flush House (full house + flush)
            if is_flush and sorted_counts[:2] == [3, 2]:
                return HandType.FLUSH_HOUSE, cards[:5]
            
            # Five of a Kind
            if sorted_counts[0] >= 5:
                target_rank = [r for r, c in rank_counts.items() if c >= 5][0]
                scoring = [c for c in cards if c.rank == target_rank][:5]
                return HandType.FIVE_OF_A_KIND, scoring
            
            # Straight Flush / Royal Flush
            if is_flush and is_straight:
                sorted_ranks = sorted(set(ranks))
                if sorted_ranks[-5:] == [10, 11, 12, 13, 14]:
                    return HandType.ROYAL_FLUSH, cards[:5]
                return HandType.STRAIGHT_FLUSH, cards[:5]
        
        # Four of a Kind
        if sorted_counts and sorted_counts[0] >= 4:
            target_rank = [r for r, c in rank_counts.items() if c >= 4][0]
            scoring = [c for c in cards if c.rank == target_rank][:4]
            return HandType.FOUR_OF_A_KIND, scoring
        
        # Full House
        if len(sorted_counts) >= 2 and sorted_counts[0] >= 3 and sorted_counts[1] >= 2:
            three_rank = [r for r, c in rank_counts.items() if c >= 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c >= 2 and r != three_rank][0]
            scoring = [c for c in cards if c.rank == three_rank][:3]
            scoring += [c for c in cards if c.rank == pair_rank][:2]
            return HandType.FULL_HOUSE, scoring
        
        # Flush
        if is_flush:
            return HandType.FLUSH, cards[:5]
        
        # Straight
        if is_straight:
            return HandType.STRAIGHT, cards[:5]
        
        # Three of a Kind
        if sorted_counts and sorted_counts[0] >= 3:
            target_rank = [r for r, c in rank_counts.items() if c >= 3][0]
            scoring = [c for c in cards if c.rank == target_rank][:3]
            return HandType.THREE_OF_A_KIND, scoring
        
        # Two Pair
        pairs = [r for r, c in rank_counts.items() if c >= 2]
        if len(pairs) >= 2:
            scoring = []
            for r in sorted(pairs, reverse=True)[:2]:
                scoring += [c for c in cards if c.rank == r][:2]
            return HandType.TWO_PAIR, scoring
        
        # Pair
        if pairs:
            target_rank = pairs[0]
            scoring = [c for c in cards if c.rank == target_rank][:2]
            return HandType.PAIR, scoring
        
        # High Card
        scoring = [max(cards, key=lambda c: c.rank)] if cards else []
        return HandType.HIGH_CARD, scoring
    
    @staticmethod
    def _is_straight(ranks: List[int]) -> bool:
        """Verifica si los rangos forman un straight."""
        unique = sorted(set(ranks))
        if len(unique) < 5:
            return False
        
        # Verificar secuencia normal
        for i in range(len(unique) - 4):
            if unique[i+4] - unique[i] == 4:
                return True
        
        # Wheel (A-2-3-4-5)
        if set([2, 3, 4, 5, 14]).issubset(set(unique)):
            return True
        
        return False
    
    @staticmethod
    def calculate_score(cards: List[Card], game_state: GameState) -> Tuple[int, HandType, int, int]:
        """
        Calcula la puntuación de una mano.
        
        Returns:
            Tuple de (puntuación_final, tipo_mano, chips_totales, mult_total)
        """
        hand_type, scoring_cards = HandEvaluator.get_hand_type(cards)
        hand_level = game_state.get_hand_level(hand_type)
        
        # Chips base del tipo de mano
        chips = hand_level.chips
        mult = hand_level.mult
        x_mult = 1.0
        
        # Añadir chips de las cartas que puntúan
        for card in scoring_cards:
            chips += card.chip_value
            
            # Mejoras de carta
            if card.enhancement == Enhancement.MULT:
                mult += 4
            if card.edition == Edition.HOLOGRAPHIC:
                mult += 10
            if card.enhancement == Enhancement.GLASS:
                x_mult *= 2
            if card.edition == Edition.POLYCHROME:
                x_mult *= 1.5
        
        # Aplicar jokers
        for joker in game_state.jokers:
            j_chips, j_mult, j_xmult = HandEvaluator._apply_joker(
                joker, cards, hand_type, scoring_cards, game_state
            )
            chips += j_chips
            mult += j_mult
            x_mult *= j_xmult
            
            # Edición del joker
            if joker.edition == Edition.FOIL:
                chips += 50
            elif joker.edition == Edition.HOLOGRAPHIC:
                mult += 10
            elif joker.edition == Edition.POLYCHROME:
                x_mult *= 1.5
        
        # Calcular puntuación final
        final_mult = mult * x_mult
        score = int(chips * final_mult)
        
        return score, hand_type, chips, int(final_mult)
    
    @staticmethod
    def _apply_joker(joker: Joker, cards: List[Card], hand_type: HandType,
                     scoring_cards: List[Card], game_state: GameState) -> Tuple[int, int, float]:
        """Aplica el efecto de un joker."""
        effect = joker.effect
        chips = 0
        mult = 0
        x_mult = 1.0
        
        # Verificar condición
        condition_met = True
        if effect.conditional:
            condition_met = HandEvaluator._check_condition(
                effect.conditional, cards, hand_type, scoring_cards, game_state
            )
        
        if condition_met:
            chips += effect.flat_chips
            mult += effect.flat_mult
            if effect.x_mult != 1.0:
                x_mult *= effect.x_mult
        
        return chips, mult, x_mult
    
    @staticmethod
    def _check_condition(condition: str, cards: List[Card], hand_type: HandType,
                         scoring_cards: List[Card], game_state: GameState) -> bool:
        """Verifica si se cumple una condición del joker."""
        conditions = {
            "pair": hand_type == HandType.PAIR,
            "two_pair": hand_type == HandType.TWO_PAIR,
            "three_of_a_kind": hand_type == HandType.THREE_OF_A_KIND,
            "straight": hand_type in (HandType.STRAIGHT, HandType.STRAIGHT_FLUSH),
            "flush": hand_type in (HandType.FLUSH, HandType.STRAIGHT_FLUSH, 
                                   HandType.FLUSH_HOUSE, HandType.FLUSH_FIVE),
            "full_house": hand_type in (HandType.FULL_HOUSE, HandType.FLUSH_HOUSE),
            "four_of_a_kind": hand_type == HandType.FOUR_OF_A_KIND,
            "hand_size_lte_3": len(cards) <= 3,
            "discards_0": game_state.discards_remaining == 0,
            "all_spades_clubs": all(c.suit in (Suit.SPADES, Suit.CLUBS) for c in cards),
        }
        return conditions.get(condition, False)


# =============================================================================
# UTILIDADES
# =============================================================================

def create_standard_deck() -> List[Card]:
    """Crea un mazo estándar de 52 cartas."""
    deck = []
    for rank in range(2, 15):
        for suit in Suit:
            deck.append(Card(rank=rank, suit=suit))
    return deck


def parse_card(card_str: str) -> Card:
    """
    Parsea una carta desde string.
    Ejemplos: "AS", "10H", "KD", "2C"
    """
    card_str = card_str.upper().strip()
    
    suit_map = {"H": Suit.HEARTS, "D": Suit.DIAMONDS, "C": Suit.CLUBS, "S": Suit.SPADES}
    rank_map = {"A": 14, "K": 13, "Q": 12, "J": 11, "T": 10, "10": 10}
    
    suit_char = card_str[-1]
    rank_str = card_str[:-1]
    
    suit = suit_map.get(suit_char)
    if not suit:
        raise ValueError(f"Palo inválido: {suit_char}")
    
    if rank_str in rank_map:
        rank = rank_map[rank_str]
    elif rank_str.isdigit() and 2 <= int(rank_str) <= 10:
        rank = int(rank_str)
    else:
        raise ValueError(f"Rango inválido: {rank_str}")
    
    return Card(rank=rank, suit=suit)


def parse_hand(hand_str: str) -> List[Card]:
    """
    Parsea múltiples cartas separadas por espacio o coma.
    Ejemplo: "AS KH QD JC 10S"
    """
    separators = [",", " "]
    cards_str = hand_str
    for sep in separators:
        cards_str = cards_str.replace(sep, "|")
    
    card_tokens = [t.strip() for t in cards_str.split("|") if t.strip()]
    return [parse_card(t) for t in card_tokens]
