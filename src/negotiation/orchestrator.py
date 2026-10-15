"""Framework-agnostic alternating-turn protocol orchestration with move validation."""

from __future__ import annotations

from .agents import NegotiationAgent, NegotiationState
from .schemas import (
    Accept,
    Argument,
    CounterOffer,
    NegotiationMove,
    NegotiationResult,
    Offer,
    PriceNegotiationScenario,
    Reject,
)


class ProtocolViolation(ValueError):
    """Raised when an agent emits a move that breaks the negotiation protocol."""


class NegotiationOrchestrator:
    """Runs an alternating-offers negotiation and enforces the protocol rules.

    Each turn an agent returns zero or more ``Argument`` moves followed by exactly
    one ``Offer``/``CounterOffer``/``Accept``/``Reject``. The run ends on a deal
    (accept), an impasse (reject) or the deadline (``max_rounds`` exhausted).
    """

    def __init__(self, scenario: PriceNegotiationScenario,
                 buyer: NegotiationAgent, seller: NegotiationAgent) -> None:
        self.scenario, self.buyer, self.seller = scenario, buyer, seller

    def run(self) -> NegotiationResult:
        moves: list[NegotiationMove] = []
        last_offer: Offer | CounterOffer | None = None
        actors = (self.buyer, self.seller) if self.scenario.first_mover == "buyer" else (self.seller, self.buyer)
        for round_number in range(1, self.scenario.max_rounds + 1):
            for position, actor in enumerate(actors):
                is_last_turn = round_number == self.scenario.max_rounds and position == len(actors) - 1
                state = NegotiationState(round_number, self.scenario.max_rounds, last_offer,
                                         tuple(moves), is_last_turn)
                turn = actor.respond(state)
                self._validate_turn(turn, actor, state, moves)
                moves.extend(turn)
                final = turn[-1]
                if isinstance(final, Accept):
                    return self._result("deal", moves, round_number, agreed_price=last_offer.price)
                if isinstance(final, Reject):
                    return self._result("impasse", moves, round_number)
                last_offer = final
        return self._result("deadline", moves, self.scenario.max_rounds)

    def _result(self, status, moves, rounds, agreed_price=None) -> NegotiationResult:
        return NegotiationResult(scenario_id=self.scenario.id, status=status,
                                 agreed_price=agreed_price, rounds_played=rounds, moves=moves)

    @staticmethod
    def _validate_turn(turn: list[NegotiationMove], actor: NegotiationAgent,
                       state: NegotiationState, history: list[NegotiationMove]) -> None:
        def fail(msg: str) -> None:
            raise ProtocolViolation(f"{actor.profile.id} (round {state.round_number}): {msg}")

        if not turn:
            fail("a turn must contain at least one move")
        *arguments, final = turn
        if any(not isinstance(m, Argument) for m in arguments):
            fail("only Argument moves may precede the final move of a turn")
        if isinstance(final, Argument):
            fail("a turn must end with an offer, counter-offer, accept or reject")

        seen_ids = {m.id for m in history}
        played_args = {m.node_id for m in history if isinstance(m, Argument)}
        for move in turn:
            if move.actor_id != actor.profile.id:
                fail(f"move {move.id!r} has actor_id {move.actor_id!r}")
            if move.round_number != state.round_number:
                fail(f"move {move.id!r} has round_number {move.round_number}")
            if move.id in seen_ids:
                fail(f"duplicate move id {move.id!r}")
            seen_ids.add(move.id)
            if isinstance(move, Argument):
                if move.node_id in played_args:
                    fail(f"argument {move.node_id!r} was already played")
                unknown = set(move.attacks) - played_args
                if unknown:
                    fail(f"argument {move.node_id!r} attacks arguments not yet played: {sorted(unknown)}")
                played_args.add(move.node_id)

        last = state.last_offer
        if isinstance(final, Offer) and last is not None:
            fail("an opening Offer is only allowed before any offer was made; use CounterOffer")
        if isinstance(final, (CounterOffer, Accept, Reject)) and last is None:
            fail(f"{final.type} requires a previous offer")
        if isinstance(final, CounterOffer) and final.in_response_to != last.id:
            fail(f"counter-offer must respond to {last.id!r}")
        if isinstance(final, Accept) and final.offer_id != last.id:
            fail(f"accept must reference the last offer {last.id!r}")
