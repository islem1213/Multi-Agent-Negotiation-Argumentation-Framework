"""Outcome, process and argumentation metrics for a completed negotiation."""

from __future__ import annotations

from pydantic import BaseModel

from .argumentation import ArgumentationFramework
from .schemas import Argument, CounterOffer, NegotiationResult, Offer, PriceNegotiationScenario


class NegotiationMetrics(BaseModel):
    scenario_id: str
    status: str
    deal: bool
    agreed_price: float | None
    zopa: tuple[float, float] | None
    missed_deal: bool
    """A zone of agreement existed but the agents did not reach a deal."""
    rounds_played: int
    n_moves: int
    n_offers: int
    n_arguments: int
    buyer_utility: float | None
    """Buyer's share of the available surplus, in [0, 1]."""
    seller_utility: float | None
    nash_product: float | None
    fairness_gap: float | None
    """|buyer_utility - seller_utility|: 0 is an even split, 1 is all surplus to one side."""
    buyer_concession: float
    """Fraction of the buyer's initial-to-reservation range conceded in its offers."""
    seller_concession: float
    accepted_arguments: dict[str, int]
    defeated_arguments: dict[str, int]
    undecided_arguments: dict[str, int]


def _concession(result: NegotiationResult, actor_id: str, initial: float, reservation: float) -> float:
    prices = [m.price for m in result.moves if isinstance(m, (Offer, CounterOffer)) and m.actor_id == actor_id]
    if not prices or reservation == initial:
        return 0.0
    return (prices[-1] - initial) / (reservation - initial)


def evaluate(result: NegotiationResult, scenario: PriceNegotiationScenario) -> NegotiationMetrics:
    buyer, seller = scenario.buyer, scenario.seller
    zopa = scenario.zopa
    deal = result.status == "deal"
    buyer_u = seller_u = nash = gap = None
    if deal and zopa is not None:
        width = zopa[1] - zopa[0]
        if width > 0:
            buyer_u = (buyer.reservation_price - result.agreed_price) / width
            seller_u = (result.agreed_price - seller.reservation_price) / width
        else:
            buyer_u = seller_u = 0.5
        nash = buyer_u * seller_u
        gap = abs(buyer_u - seller_u)

    framework = ArgumentationFramework.from_moves(result.moves)
    labels = framework.grounded_labelling()
    counts = {label: {buyer.id: 0, seller.id: 0} for label in ("IN", "OUT", "UNDEC")}
    for arg, label in labels.items():
        counts[label][framework.owner[arg]] += 1

    return NegotiationMetrics(
        scenario_id=result.scenario_id,
        status=result.status,
        deal=deal,
        agreed_price=result.agreed_price,
        zopa=zopa,
        missed_deal=zopa is not None and not deal,
        rounds_played=result.rounds_played,
        n_moves=len(result.moves),
        n_offers=sum(isinstance(m, (Offer, CounterOffer)) for m in result.moves),
        n_arguments=sum(isinstance(m, Argument) for m in result.moves),
        buyer_utility=buyer_u,
        seller_utility=seller_u,
        nash_product=nash,
        fairness_gap=gap,
        buyer_concession=_concession(result, buyer.id, buyer.initial_offer, buyer.reservation_price),
        seller_concession=_concession(result, seller.id, seller.initial_offer, seller.reservation_price),
        accepted_arguments=counts["IN"],
        defeated_arguments=counts["OUT"],
        undecided_arguments=counts["UNDEC"],
    )
