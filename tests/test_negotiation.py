from negotiation import AgentProfile, NegotiationOrchestrator, PriceNegotiationScenario, RuleBasedBuyer, RuleBasedSeller


def make_scenario(buyer_limit=900, seller_limit=700, max_rounds=5):
    return PriceNegotiationScenario(
        id="test", resource="resource", max_rounds=max_rounds,
        buyer=AgentProfile(id="buyer", reservation_price=buyer_limit, initial_offer=650, concession_rate=0.5),
        seller=AgentProfile(id="seller", reservation_price=seller_limit, initial_offer=1000, concession_rate=0.5),
    )


def test_rule_based_agents_reach_a_deal():
    scenario = make_scenario()
    result = NegotiationOrchestrator(scenario, RuleBasedBuyer(scenario.buyer), RuleBasedSeller(scenario.seller)).run()
    assert result.status == "deal"
    assert result.agreed_price is not None
    assert len(result.moves) >= 2


def test_incompatible_reservations_end_in_impasse():
    scenario = make_scenario(buyer_limit=600, seller_limit=1000)
    result = NegotiationOrchestrator(scenario, RuleBasedBuyer(scenario.buyer), RuleBasedSeller(scenario.seller)).run()
    assert result.status == "impasse"


def test_deadline_is_reported_when_no_agent_accepts_or_rejects():
    scenario = make_scenario(max_rounds=1)
    result = NegotiationOrchestrator(scenario, RuleBasedBuyer(scenario.buyer), RuleBasedSeller(scenario.seller)).run()
    assert result.status == "deadline"
