"""Simple deterministic policies used to validate the negotiation protocol."""

from __future__ import annotations

from .schemas import Accept, AgentProfile, CounterOffer, Offer, Reject


class RuleBasedBuyer:
    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile

    def respond(self, round_number: int, last_offer: Offer | CounterOffer | None):
        if last_offer is None:
            return Offer(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                         round_number=round_number, price=self.profile.initial_offer)
        if last_offer.price <= self.profile.reservation_price:
            return Accept(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                          round_number=round_number, offer_id=last_offer.id)
        price = self.profile.initial_offer + (
            self.profile.reservation_price - self.profile.initial_offer
        ) * self.profile.concession_rate * round_number
        if price >= self.profile.reservation_price:
            return Reject(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                          round_number=round_number, offer_id=last_offer.id,
                          reason="seller price exceeds buyer reservation price")
        return CounterOffer(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                            round_number=round_number, price=price, in_response_to=last_offer.id)


class RuleBasedSeller:
    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile

    def respond(self, round_number: int, last_offer: Offer | CounterOffer | None):
        if last_offer is None:
            return Offer(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                         round_number=round_number, price=self.profile.initial_offer)
        if last_offer.price >= self.profile.reservation_price:
            return Accept(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                          round_number=round_number, offer_id=last_offer.id)
        price = self.profile.initial_offer - (
            self.profile.initial_offer - self.profile.reservation_price
        ) * self.profile.concession_rate * round_number
        if price <= self.profile.reservation_price:
            return Reject(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                          round_number=round_number, offer_id=last_offer.id,
                          reason="buyer price is below seller reservation price")
        return CounterOffer(id=f"{self.profile.id}-{round_number}", actor_id=self.profile.id,
                            round_number=round_number, price=price, in_response_to=last_offer.id)
