"""Pydantic models that define the negotiation protocol, scenarios and results."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


class ArgumentSpec(BaseModel):
    """An argument an agent may put forward during the negotiation.

    ``attacks`` lists the ids of *opponent* arguments this argument rebuts. An
    argument with no attacks supports the agent's own position; an argument with
    attacks is only played once one of its targets has been played.
    """

    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    grounds: str = Field(min_length=1)
    attacks: list[str] = Field(default_factory=list)


class AgentProfile(BaseModel):
    """Private strategy parameters for one price-negotiating agent.

    ``beta`` shapes the time-dependent concession curve (Faratin et al., 1998):
    ``beta < 1`` is Boulware (concede late), ``beta == 1`` is linear and
    ``beta > 1`` is Conceder (concede early). ``persuadability`` in [0, 1] is how
    much each accepted opponent argument accelerates this agent's concession.
    """

    id: str = Field(min_length=1)
    reservation_price: float = Field(gt=0)
    initial_offer: float = Field(gt=0)
    beta: float = Field(default=1.0, gt=0)
    persuadability: float = Field(default=0.0, ge=0, le=1)
    arguments: list[ArgumentSpec] = Field(default_factory=list)


class PriceNegotiationScenario(BaseModel):
    """A canonical bilateral buyer/seller negotiation scenario."""

    id: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    currency: str = Field(default="EUR", min_length=1)
    buyer: AgentProfile
    seller: AgentProfile
    max_rounds: int = Field(default=6, ge=1)
    first_mover: Literal["buyer", "seller"] = "buyer"

    @model_validator(mode="after")
    def check_consistency(self) -> "PriceNegotiationScenario":
        if self.buyer.id == self.seller.id:
            raise ValueError("buyer and seller must have distinct ids")
        if self.buyer.initial_offer > self.buyer.reservation_price:
            raise ValueError("buyer initial_offer must not exceed the buyer reservation_price")
        if self.seller.initial_offer < self.seller.reservation_price:
            raise ValueError("seller initial_offer must not be below the seller reservation_price")
        buyer_ids = [a.id for a in self.buyer.arguments]
        seller_ids = [a.id for a in self.seller.arguments]
        all_ids = buyer_ids + seller_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("argument ids must be unique across both agents")
        for own, opponent in ((self.buyer, set(seller_ids)), (self.seller, set(buyer_ids))):
            for arg in own.arguments:
                unknown = set(arg.attacks) - opponent
                if unknown:
                    raise ValueError(
                        f"argument {arg.id!r} attacks unknown opponent argument(s): {sorted(unknown)}"
                    )
        return self

    @property
    def zopa(self) -> tuple[float, float] | None:
        """Zone of possible agreement (seller floor, buyer ceiling), or None if empty."""
        low, high = self.seller.reservation_price, self.buyer.reservation_price
        return (low, high) if low <= high else None


class Move(BaseModel):
    """Base fields shared by every protocol move."""

    id: str
    actor_id: str
    round_number: int = Field(ge=1)


class Offer(Move):
    type: Literal["offer"] = "offer"
    price: float = Field(gt=0)


class CounterOffer(Move):
    type: Literal["counter_offer"] = "counter_offer"
    price: float = Field(gt=0)
    in_response_to: str


class Accept(Move):
    type: Literal["accept"] = "accept"
    offer_id: str


class Reject(Move):
    type: Literal["reject"] = "reject"
    offer_id: str | None = None
    reason: str = Field(min_length=1)


class Argument(Move):
    type: Literal["argument"] = "argument"
    claim: str = Field(min_length=1)
    grounds: str = Field(min_length=1)
    target_move_id: str | None = None
    argument_id: str | None = None
    attacks: list[str] = Field(default_factory=list)

    @property
    def node_id(self) -> str:
        """Identifier of this argument in the argumentation graph."""
        return self.argument_id or self.id


NegotiationMove = Annotated[
    Union[Offer, CounterOffer, Accept, Reject, Argument], Field(discriminator="type")
]


class NegotiationResult(BaseModel):
    """Replayable result of a completed protocol run."""

    scenario_id: str
    status: Literal["deal", "deadline", "impasse"]
    agreed_price: float | None = None
    rounds_played: int = 0
    moves: list[NegotiationMove]
