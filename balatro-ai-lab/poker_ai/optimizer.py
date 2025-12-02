"""
Motor de optimización y estrategia para Balatro AI.
Encuentra la mejor jugada dada el estado actual del juego.
"""

import itertools
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import heapq

from .game_state import (
    Card, GameState, HandType, HandEvaluator, Joker,
    BlindInfo, HandLevel, Suit
)


class ActionType(Enum):
    """Tipos de acciones posibles."""
    PLAY = auto()      # Jugar cartas
    DISCARD = auto()   # Descartar cartas


@dataclass
class PotentialHand:
    """Representa una mano potencial después de descartar."""
    hand_type: HandType
    cards_needed: int  # Cartas que faltan para completar
    cards_to_discard: List[Card]  # Cartas a descartar
    cards_to_keep: List[Card]  # Cartas a conservar
    probability: float  # Probabilidad de conseguirla (0-1)
    expected_score: int  # Puntuación esperada si se logra
    reasoning: str


@dataclass
class Action:
    """Representa una acción recomendada."""
    action_type: ActionType
    cards: List[Card]
    expected_score: int = 0
    hand_type: Optional[HandType] = None
    reasoning: str = ""
    confidence: float = 1.0  # 0-1, qué tan seguro está el sistema
    potential_hands: List[PotentialHand] = field(default_factory=list)
    
    def __str__(self):
        cards_str = " ".join(str(c) for c in self.cards)
        action = "JUGAR" if self.action_type == ActionType.PLAY else "DESCARTAR"
        return f"{action}: {cards_str} ({self.hand_type.display_name if self.hand_type else 'N/A'}) → {self.expected_score} pts"


@dataclass
class Strategy:
    """Estrategia completa para ganar el blind."""
    actions: List[Action] = field(default_factory=list)
    total_expected_score: int = 0
    hands_needed: int = 0
    discards_used: int = 0
    success_probability: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def __str__(self):
        lines = [
            f"═══ ESTRATEGIA ═══",
            f"Puntuación esperada: {self.total_expected_score}",
            f"Manos necesarias: {self.hands_needed}",
            f"Descartes usados: {self.discards_used}",
            f"Probabilidad de éxito: {self.success_probability:.1%}",
            "",
            "Acciones:"
        ]
        for i, action in enumerate(self.actions, 1):
            lines.append(f"  {i}. {action}")
        
        if self.notes:
            lines.append("\nNotas:")
            for note in self.notes:
                lines.append(f"  • {note}")
        
        return "\n".join(lines)


class StrategyOptimizer:
    """
    Motor de optimización que encuentra la mejor estrategia.
    
    Objetivo: Alcanzar el puntaje del blind usando el mínimo de manos.
    """
    
    def __init__(self, game_state: GameState):
        self.state = game_state
        self.evaluator = HandEvaluator
    
    def find_best_play(self) -> Action:
        """
        Encuentra la mejor mano para jugar ahora mismo.
        
        Returns:
            Action con la mejor jugada
        """
        hand = self.state.hand
        
        if len(hand) == 0:
            return Action(
                action_type=ActionType.PLAY,
                cards=[],
                expected_score=0,
                reasoning="No hay cartas en mano"
            )
        
        best_action = None
        best_score = -1
        
        # Evaluar todas las combinaciones de 1-5 cartas
        for num_cards in range(1, min(6, len(hand) + 1)):
            for combo in itertools.combinations(hand, num_cards):
                cards = list(combo)
                score, hand_type, chips, mult = self.evaluator.calculate_score(
                    cards, self.state
                )
                
                if score > best_score:
                    best_score = score
                    best_action = Action(
                        action_type=ActionType.PLAY,
                        cards=cards,
                        expected_score=score,
                        hand_type=hand_type,
                        reasoning=f"{chips} chips × {mult} mult"
                    )
        
        return best_action
    
    def find_all_plays(self, top_n: int = 10) -> List[Action]:
        """
        Encuentra las mejores N jugadas posibles.
        
        Args:
            top_n: Número de jugadas a retornar
        
        Returns:
            Lista de las mejores acciones ordenadas por puntuación
        """
        hand = self.state.hand
        plays = []
        
        for num_cards in range(1, min(6, len(hand) + 1)):
            for combo in itertools.combinations(hand, num_cards):
                cards = list(combo)
                score, hand_type, chips, mult = self.evaluator.calculate_score(
                    cards, self.state
                )
                
                action = Action(
                    action_type=ActionType.PLAY,
                    cards=cards,
                    expected_score=score,
                    hand_type=hand_type,
                    reasoning=f"{chips} chips × {mult} mult"
                )
                plays.append(action)
        
        # Ordenar por puntuación descendente
        plays.sort(key=lambda a: a.expected_score, reverse=True)
        return plays[:top_n]
    
    def find_best_discard(self) -> Action:
        """
        Encuentra el mejor descarte para mejorar la mano.
        
        Analiza qué cartas descartar para maximizar el valor esperado
        de la siguiente mano.
        """
        if not self.state.can_discard:
            return Action(
                action_type=ActionType.DISCARD,
                cards=[],
                reasoning="No quedan descartes"
            )
        
        hand = self.state.hand
        
        # Encontrar la mejor jugada actual
        current_best = self.find_best_play()
        scoring_cards = set(id(c) for c in current_best.cards)
        
        # Candidatas a descartar: cartas que no están en la mejor jugada
        discard_candidates = [c for c in hand if id(c) not in scoring_cards]
        
        if not discard_candidates:
            # Todas las cartas son útiles
            return Action(
                action_type=ActionType.DISCARD,
                cards=[],
                reasoning="Todas las cartas son útiles, no descartar"
            )
        
        # Analizar qué descartes mejorarían más la mano
        best_discard = self._analyze_discards(hand, discard_candidates)
        
        return best_discard
    
    def analyze_potential_hands(self) -> List[PotentialHand]:
        """
        Analiza las manos potenciales que se podrían conseguir descartando.
        
        Busca:
        - Flush (5 del mismo palo)
        - Straight (5 consecutivas)
        - Full House (trio + par)
        - Four of a Kind
        - Mejoras a manos actuales
        
        Returns:
            Lista de PotentialHand ordenadas por valor esperado
        """
        hand = self.state.hand
        potentials = []
        
        # Analizar distribución de la mano
        rank_counts = {}
        suit_counts = {}
        cards_by_suit = {Suit.HEARTS: [], Suit.DIAMONDS: [], Suit.CLUBS: [], Suit.SPADES: []}
        cards_by_rank = {}
        
        for card in hand:
            rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
            suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
            cards_by_suit[card.suit].append(card)
            if card.rank not in cards_by_rank:
                cards_by_rank[card.rank] = []
            cards_by_rank[card.rank].append(card)
        
        # 1. Potencial de FLUSH
        for suit, count in suit_counts.items():
            if count >= 4:
                cards_needed = 5 - count
                cards_to_keep = cards_by_suit[suit]
                cards_to_discard = [c for c in hand if c.suit != suit][:5]  # Max 5
                
                # Probabilidad aproximada de conseguir flush
                # Quedan ~9 cartas del palo en el mazo de 52
                remaining_in_suit = 13 - count
                prob = self._calculate_draw_probability(cards_needed, remaining_in_suit, 52 - 8)
                
                if cards_needed <= 2:  # Solo si falta 1 o 2 cartas
                    potentials.append(PotentialHand(
                        hand_type=HandType.FLUSH,
                        cards_needed=cards_needed,
                        cards_to_discard=cards_to_discard[:cards_needed + 2],
                        cards_to_keep=cards_to_keep,
                        probability=prob,
                        expected_score=self._estimate_hand_score(HandType.FLUSH, cards_to_keep),
                        reasoning=f"Tienes {count} {self._suit_name(suit)}, falta{'n' if cards_needed > 1 else ''} {cards_needed}"
                    ))
        
        # 2. Potencial de STRAIGHT
        sorted_ranks = sorted(set(rank_counts.keys()))
        straight_potential = self._find_straight_potential(hand, sorted_ranks, cards_by_rank)
        if straight_potential:
            potentials.append(straight_potential)
        
        # 3. Potencial de FOUR OF A KIND
        for rank, count in rank_counts.items():
            if count == 3:
                cards_needed = 1
                cards_to_keep = cards_by_rank[rank]
                cards_to_discard = [c for c in hand if c.rank != rank]
                
                prob = self._calculate_draw_probability(1, 1, 52 - 8)  # 1 carta del mismo rank
                
                potentials.append(PotentialHand(
                    hand_type=HandType.FOUR_OF_A_KIND,
                    cards_needed=1,
                    cards_to_discard=cards_to_discard[:3],
                    cards_to_keep=cards_to_keep,
                    probability=prob,
                    expected_score=self._estimate_hand_score(HandType.FOUR_OF_A_KIND, cards_to_keep),
                    reasoning=f"Tienes trío de {self._rank_name(rank)}, falta 1 para poker"
                ))
        
        # 4. Potencial de FULL HOUSE
        pairs = [(rank, count) for rank, count in rank_counts.items() if count >= 2]
        if len(pairs) >= 2:
            # Ya tenemos potencial de full house
            trips = [p for p in pairs if p[1] >= 3]
            twos = [p for p in pairs if p[1] == 2]
            
            if trips and twos:
                potentials.append(PotentialHand(
                    hand_type=HandType.FULL_HOUSE,
                    cards_needed=0,
                    cards_to_discard=[],
                    cards_to_keep=hand,
                    probability=1.0,
                    expected_score=self._estimate_hand_score(HandType.FULL_HOUSE, hand[:5]),
                    reasoning="¡Ya tienes Full House!"
                ))
            elif len(twos) >= 2:
                # Dos pares, podría mejorar a full
                best_pair_rank = max(twos, key=lambda x: x[0])[0]
                other_pair_rank = min(twos, key=lambda x: x[0])[0]
                
                cards_to_keep = cards_by_rank[best_pair_rank] + cards_by_rank[other_pair_rank]
                cards_to_discard = [c for c in hand if c not in cards_to_keep]
                
                prob = self._calculate_draw_probability(1, 4, 52 - 8)  # Necesita 1 de cualquiera de los 2 ranks
                
                potentials.append(PotentialHand(
                    hand_type=HandType.FULL_HOUSE,
                    cards_needed=1,
                    cards_to_discard=cards_to_discard[:len(cards_to_discard)],
                    cards_to_keep=cards_to_keep,
                    probability=prob,
                    expected_score=self._estimate_hand_score(HandType.FULL_HOUSE, cards_to_keep),
                    reasoning=f"Dos pares ({self._rank_name(best_pair_rank)}, {self._rank_name(other_pair_rank)}), busca Full House"
                ))
        
        # 5. Potencial de THREE OF A KIND (si tiene par)
        for rank, count in rank_counts.items():
            if count == 2:
                cards_to_keep = cards_by_rank[rank]
                cards_to_discard = [c for c in hand if c.rank != rank]
                
                prob = self._calculate_draw_probability(1, 2, 52 - 8)
                
                potentials.append(PotentialHand(
                    hand_type=HandType.THREE_OF_A_KIND,
                    cards_needed=1,
                    cards_to_discard=cards_to_discard[:3],
                    cards_to_keep=cards_to_keep,
                    probability=prob,
                    expected_score=self._estimate_hand_score(HandType.THREE_OF_A_KIND, cards_to_keep),
                    reasoning=f"Par de {self._rank_name(rank)}, busca trío"
                ))
        
        # Ordenar por valor esperado (score * probabilidad)
        potentials.sort(key=lambda p: p.expected_score * p.probability, reverse=True)
        
        return potentials
    
    def _find_straight_potential(self, hand: List[Card], sorted_ranks: List[int], 
                                  cards_by_rank: Dict) -> Optional[PotentialHand]:
        """Busca potencial de escalera."""
        
        # Buscar secuencias de 4 cartas
        for i in range(len(sorted_ranks) - 3):
            window = sorted_ranks[i:i+4]
            if window[-1] - window[0] == 3:  # 4 consecutivas
                # Encontrar qué falta
                needed_rank = None
                if i > 0 and sorted_ranks[i-1] == window[0] - 1:
                    needed_rank = window[0] - 1
                elif i + 4 < len(sorted_ranks) and sorted_ranks[i+4] == window[-1] + 1:
                    needed_rank = window[-1] + 1
                else:
                    # Falta arriba o abajo
                    if window[0] > 2:
                        needed_rank = window[0] - 1
                    elif window[-1] < 14:
                        needed_rank = window[-1] + 1
                
                if needed_rank:
                    cards_to_keep = []
                    for rank in window:
                        cards_to_keep.extend(cards_by_rank[rank][:1])
                    
                    cards_to_discard = [c for c in hand if c not in cards_to_keep]
                    
                    prob = self._calculate_draw_probability(1, 4, 52 - 8)
                    
                    return PotentialHand(
                        hand_type=HandType.STRAIGHT,
                        cards_needed=1,
                        cards_to_discard=cards_to_discard[:4],
                        cards_to_keep=cards_to_keep,
                        probability=prob,
                        expected_score=self._estimate_hand_score(HandType.STRAIGHT, cards_to_keep),
                        reasoning=f"4 consecutivas ({window[0]}-{window[-1]}), falta {self._rank_name(needed_rank)}"
                    )
        
        # Buscar 3 consecutivas
        for i in range(len(sorted_ranks) - 2):
            window = sorted_ranks[i:i+3]
            if window[-1] - window[0] == 2:  # 3 consecutivas
                cards_to_keep = []
                for rank in window:
                    cards_to_keep.extend(cards_by_rank[rank][:1])
                
                cards_to_discard = [c for c in hand if c not in cards_to_keep]
                
                prob = self._calculate_draw_probability(2, 8, 52 - 8)  # Necesita 2 cartas específicas
                
                if prob > 0.05:  # Solo si hay probabilidad razonable
                    return PotentialHand(
                        hand_type=HandType.STRAIGHT,
                        cards_needed=2,
                        cards_to_discard=cards_to_discard[:5],
                        cards_to_keep=cards_to_keep,
                        probability=prob,
                        expected_score=self._estimate_hand_score(HandType.STRAIGHT, cards_to_keep),
                        reasoning=f"3 consecutivas ({window[0]}-{window[-1]}), faltan 2 para escalera"
                    )
        
        return None
    
    def _calculate_draw_probability(self, cards_needed: int, 
                                     favorable_cards: int, 
                                     deck_size: int) -> float:
        """Calcula probabilidad aproximada de sacar las cartas necesarias."""
        if cards_needed == 0:
            return 1.0
        if cards_needed == 1:
            return favorable_cards / deck_size
        if cards_needed == 2:
            # Probabilidad de sacar al menos 1 de favorable en 2 intentos
            p_miss = ((deck_size - favorable_cards) / deck_size) * \
                     ((deck_size - favorable_cards - 1) / (deck_size - 1))
            return 1 - p_miss
        # Para más cartas, aproximación conservadora
        return max(0.01, (favorable_cards / deck_size) ** cards_needed * 10)
    
    def _estimate_hand_score(self, hand_type: HandType, scoring_cards: List[Card] = None) -> int:
        """
        Estima el puntaje de un tipo de mano basándose en las cartas reales.
        
        Args:
            hand_type: Tipo de mano
            scoring_cards: Cartas que puntuarían (opcional, para cálculo más preciso)
        
        Returns:
            Puntuación estimada
        """
        # Chips base por tipo de mano (valores de Balatro)
        base_chips = {
            HandType.HIGH_CARD: 5,
            HandType.PAIR: 10,
            HandType.TWO_PAIR: 20,
            HandType.THREE_OF_A_KIND: 30,
            HandType.STRAIGHT: 30,
            HandType.FLUSH: 35,
            HandType.FULL_HOUSE: 40,
            HandType.FOUR_OF_A_KIND: 60,
            HandType.STRAIGHT_FLUSH: 100,
            HandType.ROYAL_FLUSH: 100,
        }
        
        # Multiplicador base por tipo de mano
        base_mult = {
            HandType.HIGH_CARD: 1,
            HandType.PAIR: 2,
            HandType.TWO_PAIR: 2,
            HandType.THREE_OF_A_KIND: 3,
            HandType.STRAIGHT: 4,
            HandType.FLUSH: 4,
            HandType.FULL_HOUSE: 4,
            HandType.FOUR_OF_A_KIND: 7,
            HandType.STRAIGHT_FLUSH: 8,
            HandType.ROYAL_FLUSH: 8,
        }
        
        chips = base_chips.get(hand_type, 5)
        mult = base_mult.get(hand_type, 1)
        
        # Añadir chips de las cartas si se proporcionan
        if scoring_cards:
            for card in scoring_cards:
                # Valor de chips por carta
                card_chips = card.rank if card.rank <= 10 else 10
                if card.rank == 14:  # As
                    card_chips = 11
                chips += card_chips
        else:
            # Estimación promedio si no hay cartas específicas
            avg_card_chips = 7  # Promedio aproximado
            num_cards = 5 if hand_type in [HandType.STRAIGHT, HandType.FLUSH, 
                                            HandType.FULL_HOUSE, HandType.STRAIGHT_FLUSH,
                                            HandType.ROYAL_FLUSH] else 2
            chips += avg_card_chips * num_cards
        
        # Aplicar nivel de mano
        level = self.state.hand_levels.get(hand_type, 1)
        # Cada nivel añade chips y mult base
        level_bonus_chips = (level - 1) * 10
        level_bonus_mult = (level - 1) * 1
        
        chips += level_bonus_chips
        mult += level_bonus_mult
        
        # Aplicar jokers (estimación simple)
        for joker in self.state.jokers:
            if joker.trigger_type == joker.trigger_type:  # Simplificado
                mult += 2  # Estimación conservadora
        
        return chips * mult
    
    def _suit_name(self, suit: Suit) -> str:
        """Nombre del palo en español."""
        names = {
            Suit.HEARTS: "♥ corazones",
            Suit.DIAMONDS: "♦ diamantes", 
            Suit.CLUBS: "♣ tréboles",
            Suit.SPADES: "♠ picas"
        }
        return names.get(suit, str(suit))
    
    def _rank_name(self, rank: int) -> str:
        """Nombre del rango."""
        names = {14: 'A', 13: 'K', 12: 'Q', 11: 'J'}
        return names.get(rank, str(rank))
    
    def _analyze_discards(self, hand: List[Card], 
                          candidates: List[Card]) -> Action:
        """Analiza opciones de descarte basándose en potencial de mejora."""
        
        # Usar el nuevo análisis de potencial
        potential_hands = self.analyze_potential_hands()
        
        if potential_hands:
            best_potential = potential_hands[0]
            
            # Si hay buena probabilidad de mejorar
            if best_potential.probability >= 0.1 and best_potential.cards_needed > 0:
                return Action(
                    action_type=ActionType.DISCARD,
                    cards=best_potential.cards_to_discard[:5],  # Max 5
                    expected_score=int(best_potential.expected_score * best_potential.probability),
                    hand_type=best_potential.hand_type,
                    reasoning=best_potential.reasoning,
                    potential_hands=potential_hands[:3]  # Top 3 potenciales
                )
        
        # Fallback: descartar cartas de menor valor
        rank_counts = {}
        suit_counts = {}
        
        for card in hand:
            rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
            suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
        
        # Puntuación de cada carta (menor = mejor para descartar)
        card_values = []
        
        for card in candidates:
            value = 0
            value += rank_counts[card.rank] * 20
            value += suit_counts[card.suit] * 5
            if card.rank >= 10:
                value += 10
            if card.rank == 14:
                value += 15
            if card.enhancement != card.enhancement.NONE:
                value += 30
            if card.edition != card.edition.NONE:
                value += 40
            
            card_values.append((value, card))
        
        card_values.sort(key=lambda x: x[0])
        to_discard = [card for _, card in card_values[:min(5, len(card_values))]]
        
        reasoning = self._generate_discard_reasoning(to_discard, rank_counts, suit_counts)
        
        return Action(
            action_type=ActionType.DISCARD,
            cards=to_discard,
            reasoning=reasoning,
            potential_hands=potential_hands[:3] if potential_hands else []
        )
    
    def _generate_discard_reasoning(self, discards: List[Card],
                                    rank_counts: Dict, suit_counts: Dict) -> str:
        """Genera explicación del descarte."""
        reasons = []
        
        for card in discards:
            if rank_counts[card.rank] == 1:
                reasons.append(f"{card}: no forma par")
            if suit_counts[card.suit] < 3:
                reasons.append(f"{card}: palo minoritario")
        
        if not reasons:
            return "Cartas de menor valor esperado"
        
        return "; ".join(reasons[:3])
    
    def calculate_strategy(self) -> Strategy:
        """
        Calcula la estrategia óptima completa para ganar el blind.
        
        Considera:
        - Puntuación objetivo del blind
        - Manos y descartes restantes
        - Estado actual de la mano
        - Jokers activos
        
        Returns:
            Strategy con el plan completo
        """
        target = self.state.blind.target_score
        current = self.state.current_score
        needed = target - current
        
        strategy = Strategy()
        
        if needed <= 0:
            strategy.success_probability = 1.0
            strategy.notes.append("¡Ya ganaste el blind!")
            return strategy
        
        # Simular estado
        sim_state = self.state.copy()
        total_score = current
        
        while total_score < target and sim_state.hands_remaining > 0:
            optimizer = StrategyOptimizer(sim_state)
            
            # Decidir: ¿jugar o descartar?
            best_play = optimizer.find_best_play()
            
            # ¿Vale la pena descartar para mejorar?
            should_discard = False
            if sim_state.discards_remaining > 0:
                potential_improvement = self._estimate_discard_value(sim_state)
                
                # Descartar si:
                # 1. Tenemos descartes disponibles
                # 2. La mejora potencial justifica usar un descarte
                # 3. No estamos en la última mano
                if (potential_improvement > best_play.expected_score * 0.3 and
                    sim_state.hands_remaining > 1):
                    should_discard = True
            
            if should_discard:
                discard_action = optimizer.find_best_discard()
                if discard_action.cards:
                    strategy.actions.append(discard_action)
                    strategy.discards_used += 1
                    
                    # Simular descarte (en realidad robaríamos nuevas cartas)
                    sim_state.discards_remaining -= 1
                    for card in discard_action.cards:
                        if card in sim_state.hand:
                            sim_state.hand.remove(card)
                    
                    # Nota: En la simulación real, robaríamos nuevas cartas
                    strategy.notes.append(
                        f"Descarte para mejorar hacia mejor mano"
                    )
                    continue
            
            # Jugar la mejor mano
            strategy.actions.append(best_play)
            strategy.hands_needed += 1
            total_score += best_play.expected_score
            
            # Actualizar simulación
            sim_state.hands_remaining -= 1
            for card in best_play.cards:
                if card in sim_state.hand:
                    sim_state.hand.remove(card)
        
        # Calcular probabilidad de éxito
        strategy.total_expected_score = total_score
        
        if total_score >= target:
            strategy.success_probability = 0.95  # Alta confianza
            if strategy.hands_needed <= self.state.hands_remaining:
                strategy.notes.append("✓ Suficientes manos para ganar")
            else:
                strategy.success_probability = 0.0
                strategy.notes.append("✗ No hay suficientes manos")
        else:
            # Calcular probabilidad basada en cercanía
            strategy.success_probability = min(0.8, total_score / target)
            strategy.notes.append(
                f"⚠ Puntuación esperada ({total_score}) < objetivo ({target})"
            )
        
        return strategy
    
    def _estimate_discard_value(self, state: GameState) -> int:
        """
        Estima el valor de descartar vs jugar inmediatamente.
        
        Considera qué tan lejos está la mano de formar algo mejor.
        """
        hand = state.hand
        
        # Analizar potencial de la mano
        rank_counts = {}
        suit_counts = {}
        
        for card in hand:
            rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
            suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
        
        potential_value = 0
        
        # Cerca de flush (4 del mismo palo)
        max_suit = max(suit_counts.values()) if suit_counts else 0
        if max_suit == 4:
            potential_value += 200  # Alto valor, 1 carta para flush
        elif max_suit == 3:
            potential_value += 50   # Medio, 2 cartas para flush
        
        # Cerca de straight
        sorted_ranks = sorted(set(rank_counts.keys()))
        consecutive = self._count_consecutive(sorted_ranks)
        if consecutive == 4:
            potential_value += 150  # 1 carta para straight
        elif consecutive == 3:
            potential_value += 30   # 2 cartas para straight
        
        # Cerca de trips/quads
        max_rank = max(rank_counts.values()) if rank_counts else 0
        if max_rank == 3:
            potential_value += 100  # Ya tiene trips, podría mejorar
        elif max_rank == 2:
            # ¿Dos pares? Potencial full house
            pairs = sum(1 for c in rank_counts.values() if c >= 2)
            if pairs >= 2:
                potential_value += 80
        
        return potential_value
    
    def _count_consecutive(self, sorted_ranks: List[int]) -> int:
        """Cuenta el número máximo de cartas consecutivas."""
        if len(sorted_ranks) < 2:
            return len(sorted_ranks)
        
        max_consecutive = 1
        current = 1
        
        for i in range(1, len(sorted_ranks)):
            if sorted_ranks[i] == sorted_ranks[i-1] + 1:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 1
        
        # Considerar A-2-3-4-5
        if 14 in sorted_ranks and 2 in sorted_ranks:
            wheel_ranks = [2, 3, 4, 5]
            wheel_count = 1 + sum(1 for r in wheel_ranks if r in sorted_ranks)
            max_consecutive = max(max_consecutive, wheel_count)
        
        return max_consecutive


# =============================================================================
# RECOMENDADOR INTERACTIVO
# =============================================================================

class Recommender:
    """
    Sistema de recomendación interactivo.
    Proporciona consejos en tiempo real al jugador.
    """
    
    def __init__(self):
        self.history: List[Action] = []
        self.current_state: Optional[GameState] = None
    
    def update_state(self, state: GameState):
        """Actualiza el estado del juego."""
        self.current_state = state
    
    def get_recommendation(self) -> Tuple[Action, Strategy]:
        """
        Obtiene la recomendación actual.
        
        Returns:
            Tuple de (acción inmediata, estrategia completa)
        """
        if not self.current_state:
            raise ValueError("No hay estado de juego")
        
        optimizer = StrategyOptimizer(self.current_state)
        
        # Obtener estrategia completa
        strategy = optimizer.calculate_strategy()
        
        # La primera acción es la recomendación inmediata
        if strategy.actions:
            immediate_action = strategy.actions[0]
        else:
            immediate_action = optimizer.find_best_play()
        
        return immediate_action, strategy
    
    def explain_recommendation(self, action: Action) -> str:
        """Genera una explicación detallada de la recomendación."""
        
        if action.action_type == ActionType.PLAY:
            lines = [
                f"🎴 RECOMENDACIÓN: JUGAR",
                f"",
                f"Cartas: {' '.join(str(c) for c in action.cards)}",
                f"Tipo: {action.hand_type.display_name if action.hand_type else 'N/A'}",
                f"Puntuación: {action.expected_score}",
                f"",
                f"Razón: {action.reasoning}"
            ]
        else:
            lines = [
                f"🔄 RECOMENDACIÓN: DESCARTAR",
                f"",
                f"Cartas: {' '.join(str(c) for c in action.cards)}",
                f"",
                f"Razón: {action.reasoning}",
                f"",
                f"Objetivo: Mejorar la mano para la siguiente jugada"
            ]
        
        return "\n".join(lines)
    
    def get_quick_tips(self) -> List[str]:
        """Obtiene consejos rápidos basados en el estado actual."""
        tips = []
        
        if not self.current_state:
            return tips
        
        state = self.current_state
        
        # Consejos sobre recursos
        if state.hands_remaining == 1:
            tips.append("⚠️ ¡Última mano! Juega tu mejor combinación.")
        
        if state.discards_remaining == 0:
            tips.append("Sin descartes. Optimiza con las cartas actuales.")
        
        # Consejos sobre el objetivo
        score_needed = state.score_needed
        optimizer = StrategyOptimizer(state)
        best_play = optimizer.find_best_play()
        
        if best_play.expected_score >= score_needed:
            tips.append(f"✓ ¡Puedes ganar con una mano! Juega: {best_play.hand_type.display_name}")
        elif best_play.expected_score * state.hands_remaining >= score_needed:
            tips.append(f"Necesitas ~{score_needed // state.hands_remaining} pts/mano")
        else:
            tips.append("⚠️ Difícil alcanzar el objetivo. Busca combos fuertes.")
        
        # Consejos sobre jokers
        if state.jokers:
            joker_names = [j.name for j in state.jokers[:3]]
            tips.append(f"Jokers activos: {', '.join(joker_names)}")
        
        return tips


# =============================================================================
# TESTS Y DEMO
# =============================================================================

def demo():
    """Demo del optimizador."""
    from .game_state import parse_hand, create_joker
    
    print("═" * 60)
    print("DEMO: Motor de Optimización de Balatro")
    print("═" * 60)
    
    # Crear estado de ejemplo
    hand = parse_hand("AS AH KS KH QD 7C 3S 2H")
    
    state = GameState(
        hand=hand,
        hands_remaining=4,
        discards_remaining=3,
        blind=BlindInfo("Big Blind", 800),
        current_score=0,
        jokers=[
            create_joker("Jolly Joker"),  # +8 mult en pair
            create_joker("Joker"),        # +4 mult siempre
        ]
    )
    
    # Subir nivel de algunas manos
    state.hand_levels[HandType.TWO_PAIR] = 3
    state.hand_levels[HandType.PAIR] = 2
    
    print(f"\nMano: {' '.join(str(c) for c in hand)}")
    print(f"Objetivo: {state.blind.target_score}")
    print(f"Manos: {state.hands_remaining}, Descartes: {state.discards_remaining}")
    print(f"Jokers: {', '.join(j.name for j in state.jokers)}")
    
    # Optimizar
    optimizer = StrategyOptimizer(state)
    
    print("\n" + "─" * 40)
    print("TOP 5 JUGADAS:")
    print("─" * 40)
    
    best_plays = optimizer.find_all_plays(top_n=5)
    for i, play in enumerate(best_plays, 1):
        print(f"{i}. {play}")
    
    print("\n" + "─" * 40)
    print("ESTRATEGIA COMPLETA:")
    print("─" * 40)
    
    strategy = optimizer.calculate_strategy()
    print(strategy)
    
    # Recomendador
    print("\n" + "─" * 40)
    print("RECOMENDACIÓN:")
    print("─" * 40)
    
    recommender = Recommender()
    recommender.update_state(state)
    action, _ = recommender.get_recommendation()
    print(recommender.explain_recommendation(action))
    
    print("\nConsejos rápidos:")
    for tip in recommender.get_quick_tips():
        print(f"  {tip}")


if __name__ == "__main__":
    demo()
