from negotiation import AgentProfile, NegotiationOrchestrator, PriceNegotiationScenario, RuleBasedBuyer, RuleBasedSeller


scenario = PriceNegotiationScenario(
    id="used-laptop", resource="used laptop", max_rounds=5,
    buyer=AgentProfile(id="buyer", reservation_price=900, initial_offer=650, concession_rate=0.5),
    seller=AgentProfile(id="seller", reservation_price=700, initial_offer=1000, concession_rate=0.5),
)
result = NegotiationOrchestrator(scenario, RuleBasedBuyer(scenario.buyer), RuleBasedSeller(scenario.seller)).run()
print(result.model_dump_json(indent=2))
