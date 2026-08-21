"""Framework-agnostic alternating-turn protocol orchestration."""

from __future__ import annotations

from .agents import RuleBasedBuyer, RuleBasedSeller
from .schemas import Accept, CounterOffer, NegotiationResult, Offer, PriceNegotiationScenario, Reject


class NegotiationOrchestrator:
    def __init__(self, scenario: PriceNegotiationScenario, buyer: RuleBasedBuyer, seller: RuleBasedSeller) -> None:
        self.scenario, self.buyer, self.seller = scenario, buyer, seller

    def run(self) -> NegotiationResult:
        moves = []
        last_offer: Offer | CounterOffer | None = None
        actors = (self.buyer, self.seller)
        for round_number in range(1, self.scenario.max_rounds + 1):
            for actor in actors:
                move = actor.respond(round_number, last_offer)
                moves.append(move)
                if isinstance(move, Accept):
                    return NegotiationResult(scenario_id=self.scenario.id, status="deal",
                                             agreed_price=last_offer.price if last_offer else None, moves=moves)
                if isinstance(move, Reject):
                    return NegotiationResult(scenario_id=self.scenario.id, status="impasse", moves=moves)
                last_offer = move
        return NegotiationResult(scenario_id=self.scenario.id, status="deadline", moves=moves)
