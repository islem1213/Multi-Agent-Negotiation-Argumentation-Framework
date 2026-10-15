"""Negotiation agents: a pluggable agent protocol and time-dependent rule-based tactics.

Any object with a ``profile`` and a ``respond(state)`` method returning a list of
moves can take part in a negotiation (for example a future LLM-backed agent).
The rule-based agents are deterministic and stateless: everything they need is
derived from the shared :class:`NegotiationState`, so a trace can be replayed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .argumentation import ArgumentationFramework
from .schemas import (
    Accept,
    AgentProfile,
    Argument,
    ArgumentSpec,
    CounterOffer,
    NegotiationMove,
    Offer,
    Reject,
)

#: Classic time-dependent tactics (Faratin, Sierra & Jennings, 1998).
TACTICS: dict[str, float] = {"boulware": 0.2, "linear": 1.0, "conceder": 5.0}


@dataclass(frozen=True)
class NegotiationState:
    """Everything an agent can observe when it is asked to move."""

    round_number: int
    max_rounds: int
    last_offer: Offer | CounterOffer | None
    history: tuple[NegotiationMove, ...] = ()
    is_last_turn: bool = False
    """True for the very last turn of the negotiation (nobody can answer afterwards)."""

    def played_argument_ids(self) -> set[str]:
        return {m.node_id for m in self.history if isinstance(m, Argument)}


@runtime_checkable
class NegotiationAgent(Protocol):
    profile: AgentProfile

    def respond(self, state: NegotiationState) -> list[NegotiationMove]:
        """Return zero or more ``Argument`` moves followed by exactly one
        ``Offer``/``CounterOffer``/``Accept``/``Reject``."""
        ...


class TimeDependentAgent:
    """Rule-based agent with a time-dependent concession curve and AC_next acceptance.

    * Concession: at its k-th offer (k = 0 is the opening) the agent proposes
      ``initial + (reservation - initial) * t ** (1 / beta)`` with
      ``t = k / (max_rounds - 1)``, so it opens at its initial offer and reaches
      its reservation price on its last possible turn.
    * Acceptance (AC_next): accept the opponent's offer if it is at least as good
      as the offer this agent would make next.
    * Walk-away: reject an offer outside its reservation price only after having
      already offered its reservation price, or on the last turn of the negotiation.
      On the last turn it accepts any offer within its reservation price.
    * Arguments: play at most one argument per turn, rebuttals first.
    * Persuasion: each opponent argument that is accepted (grounded semantics)
      advances the agent's concession clock by ``persuadability``.
    """

    role: Literal["buyer", "seller"]

    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile

    # ---- concession -------------------------------------------------------
    def offers_made(self, state: NegotiationState) -> int:
        return sum(
            1 for m in state.history
            if m.actor_id == self.profile.id and isinstance(m, (Offer, CounterOffer))
        )

    def persuasion_shift(self, state: NegotiationState) -> float:
        if self.profile.persuadability == 0:
            return 0.0
        framework = ArgumentationFramework.from_moves(state.history)
        accepted = framework.grounded_extension()
        n_opponent = sum(1 for a in accepted if framework.owner.get(a) != self.profile.id)
        return self.profile.persuadability * n_opponent

    def concession_time(self, k: int, state: NegotiationState) -> float:
        horizon = state.max_rounds - 1
        t = k / horizon if horizon > 0 else 0.0
        return min(1.0, t + self.persuasion_shift(state))

    def target_price(self, k: int, state: NegotiationState) -> float:
        p = self.profile
        t = self.concession_time(k, state)
        return p.initial_offer + (p.reservation_price - p.initial_offer) * t ** (1 / p.beta)

    # ---- role-specific comparisons -----------------------------------------
    def at_least_as_good(self, price: float, reference: float) -> bool:
        return price <= reference if self.role == "buyer" else price >= reference

    def within_reservation(self, price: float) -> bool:
        return self.at_least_as_good(price, self.profile.reservation_price)

    # ---- arguments -------------------------------------------------------------
    def select_arguments(self, state: NegotiationState, target_move_id: str | None) -> list[Argument]:
        played = state.played_argument_ids()
        own_ids = {a.id for a in self.profile.arguments}
        opponent_played = played - own_ids
        unplayed = [a for a in self.profile.arguments if a.id not in played]
        rebuttal = next((a for a in unplayed if set(a.attacks) & opponent_played), None)
        support = next((a for a in unplayed if not a.attacks), None)
        chosen: ArgumentSpec | None = rebuttal or support
        if chosen is None:
            return []
        return [Argument(
            id=f"{self.profile.id}-{state.round_number}-arg",
            actor_id=self.profile.id,
            round_number=state.round_number,
            claim=chosen.claim,
            grounds=chosen.grounds,
            target_move_id=target_move_id,
            argument_id=chosen.id,
            attacks=[t for t in chosen.attacks if t in opponent_played],
        )]

    # ---- policy -------------------------------------------------------------------
    def respond(self, state: NegotiationState) -> list[NegotiationMove]:
        pid, rnd, last = self.profile.id, state.round_number, state.last_offer
        k = self.offers_made(state)
        next_price = round(self.target_price(k, state), 2)
        move_id = f"{pid}-{rnd}"

        if last is None:
            return [*self.select_arguments(state, None),
                    Offer(id=move_id, actor_id=pid, round_number=rnd, price=next_price)]

        if state.is_last_turn:
            if self.within_reservation(last.price):
                return [Accept(id=move_id, actor_id=pid, round_number=rnd, offer_id=last.id)]
            return [Reject(id=move_id, actor_id=pid, round_number=rnd, offer_id=last.id,
                           reason=f"{last.price:g} is outside {pid}'s reservation price on the last turn")]

        if self.at_least_as_good(last.price, next_price):
            return [Accept(id=move_id, actor_id=pid, round_number=rnd, offer_id=last.id)]

        own_prices = [m.price for m in state.history
                      if m.actor_id == pid and isinstance(m, (Offer, CounterOffer))]
        made_final_offer = bool(own_prices) and math.isclose(
            own_prices[-1], self.profile.reservation_price, abs_tol=0.01)
        if made_final_offer and not self.within_reservation(last.price):
            return [Reject(id=move_id, actor_id=pid, round_number=rnd, offer_id=last.id,
                           reason=f"{last.price:g} is outside {pid}'s reservation price after its final offer")]

        return [*self.select_arguments(state, last.id),
                CounterOffer(id=move_id, actor_id=pid, round_number=rnd,
                             price=next_price, in_response_to=last.id)]


class RuleBasedBuyer(TimeDependentAgent):
    role = "buyer"


class RuleBasedSeller(TimeDependentAgent):
    role = "seller"
