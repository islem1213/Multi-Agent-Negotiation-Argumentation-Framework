"""Pydantic models that define the Week 1 negotiation protocol."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


class AgentProfile(BaseModel):
    """Private strategy parameters for one price-negotiating agent."""

    id: str = Field(min_length=1)
    reservation_price: float = Field(gt=0)
    initial_offer: float = Field(gt=0)
    concession_rate: float = Field(default=0.25, ge=0, le=1)


class PriceNegotiationScenario(BaseModel):
    """A canonical bilateral buyer/seller negotiation scenario."""

    id: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    currency: str = Field(default="EUR", min_length=1)
    buyer: AgentProfile
    seller: AgentProfile
    max_rounds: int = Field(default=6, ge=1)

    @model_validator(mode="after")
    def profiles_must_be_distinct(self) -> "PriceNegotiationScenario":
        if self.buyer.id == self.seller.id:
            raise ValueError("buyer and seller must have distinct ids")
        return self


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


NegotiationMove = Annotated[
    Union[Offer, CounterOffer, Accept, Reject, Argument], Field(discriminator="type")
]


class NegotiationResult(BaseModel):
    """Replayable in-memory result of a completed protocol run."""

    scenario_id: str
    status: Literal["deal", "deadline", "impasse"]
    agreed_price: float | None = None
    moves: list[NegotiationMove]

