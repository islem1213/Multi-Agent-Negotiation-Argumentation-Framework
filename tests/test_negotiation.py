import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from negotiation import (
    TACTICS,
    Accept,
    AgentProfile,
    ArgumentationFramework,
    ArgumentSpec,
    CounterOffer,
    NegotiationOrchestrator,
    NegotiationResult,
    NegotiationState,
    Offer,
    PriceNegotiationScenario,
    ProtocolViolation,
    Reject,
    RuleBasedBuyer,
    RuleBasedSeller,
    evaluate,
    random_scenarios,
    run,
    run_tournament,
    summarize,
)
from negotiation.cli import main

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


def make_scenario(buyer_limit=900, seller_limit=700, max_rounds=5, buyer_beta=1.0, seller_beta=1.0, **kw):
    return PriceNegotiationScenario(
        id="test", resource="resource", max_rounds=max_rounds,
        buyer=AgentProfile(id="buyer", reservation_price=buyer_limit, initial_offer=min(650, buyer_limit),
                           beta=buyer_beta, **kw.get("buyer", {})),
        seller=AgentProfile(id="seller", reservation_price=seller_limit, initial_offer=max(1000, seller_limit),
                            beta=seller_beta, **kw.get("seller", {})),
    )


def load(name):
    return PriceNegotiationScenario.model_validate_json((SCENARIOS / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- outcomes
def test_rule_based_agents_reach_a_deal_inside_the_zopa():
    result = run(make_scenario())
    assert result.status == "deal"
    assert 700 <= result.agreed_price <= 900


def test_incompatible_reservations_end_in_impasse():
    result = run(make_scenario(buyer_limit=600, seller_limit=1000))
    assert result.status == "impasse"
    assert isinstance(result.moves[-1], Reject)


def test_deadline_is_reported_when_no_agent_accepts_or_rejects():
    class Stubborn:
        """Repeats its opening price forever: never accepts, never walks away."""

        def __init__(self, profile):
            self.profile = profile

        def respond(self, state):
            pid, rnd, last = self.profile.id, state.round_number, state.last_offer
            if last is None:
                return [Offer(id=f"{pid}-{rnd}", actor_id=pid, round_number=rnd, price=self.profile.initial_offer)]
            return [CounterOffer(id=f"{pid}-{rnd}", actor_id=pid, round_number=rnd,
                                 price=self.profile.initial_offer, in_response_to=last.id)]

    sc = make_scenario(max_rounds=3)
    result = NegotiationOrchestrator(sc, Stubborn(sc.buyer), Stubborn(sc.seller)).run()
    assert result.status == "deadline"
    assert result.rounds_played == 3
    assert len(result.moves) == 6


# ---------------------------------------------------------------- regressions
def test_seller_opening_counter_is_its_initial_offer():
    # Before v0.2 the seller conceded on its very first move and never stated 1000.
    result = run(make_scenario())
    first_seller = next(m for m in result.moves if m.actor_id == "seller")
    assert isinstance(first_seller, CounterOffer) and first_seller.price == 1000


def test_no_premature_walk_away_when_a_deal_is_possible():
    # Before v0.2 the buyer rejected in round 2 although the ZOPA [780, 800] was non-empty.
    sc = make_scenario(buyer_limit=800, seller_limit=780, max_rounds=6, buyer_beta=5.0, seller_beta=0.2)
    assert run(sc).status == "deal"


def test_every_possible_deal_is_reached_by_all_tactic_pairs():
    rows = run_tournament(random_scenarios(60, seed=1))
    assert not any(r["missed_deal"] for r in rows)


def test_first_mover_can_be_the_seller():
    sc = make_scenario().model_copy(update={"first_mover": "seller"})
    result = run(sc)
    assert result.moves[0].actor_id == "seller" and result.moves[0].price == 1000
    assert result.status == "deal"


# ---------------------------------------------------------------- concession and acceptance
def _state(k_offers, max_rounds=5, actor="buyer"):
    history = tuple(Offer(id=f"{actor}-{i}", actor_id=actor, round_number=i + 1, price=700)
                    for i in range(k_offers))
    return NegotiationState(round_number=k_offers + 1, max_rounds=max_rounds, last_offer=None, history=history)


def test_concession_curve_endpoints_and_shapes():
    prices = {}
    for name, beta in TACTICS.items():
        agent = RuleBasedBuyer(AgentProfile(id="buyer", reservation_price=900, initial_offer=600, beta=beta))
        assert agent.target_price(0, _state(0)) == 600
        assert agent.target_price(4, _state(4)) == pytest.approx(900)
        prices[name] = agent.target_price(2, _state(2))
    assert prices["boulware"] < prices["linear"] < prices["conceder"]


def test_ac_next_accepts_only_offers_at_least_as_good_as_own_next_offer():
    seller = RuleBasedSeller(AgentProfile(id="seller", reservation_price=700, initial_offer=1000))
    buyer_offer = Offer(id="b-1", actor_id="buyer", round_number=1, price=750)
    move = seller.respond(NegotiationState(1, 5, buyer_offer, (buyer_offer,)))[-1]
    assert isinstance(move, CounterOffer)  # 750 is above reservation but worse than seller's next offer
    good_offer = Offer(id="b-1", actor_id="buyer", round_number=1, price=1000)
    assert isinstance(seller.respond(NegotiationState(1, 5, good_offer, (good_offer,)))[-1], Accept)


# ---------------------------------------------------------------- validation
def test_scenario_rejects_inconsistent_profiles():
    with pytest.raises(ValidationError):
        PriceNegotiationScenario(
            id="x", resource="r",
            buyer=AgentProfile(id="b", reservation_price=500, initial_offer=600),
            seller=AgentProfile(id="s", reservation_price=700, initial_offer=1000))


def test_scenario_rejects_unknown_or_duplicate_argument_ids():
    with pytest.raises(ValidationError, match="unknown opponent argument"):
        make_scenario(buyer={"arguments": [ArgumentSpec(id="b1", claim="c", grounds="g", attacks=["zz"])]})
    with pytest.raises(ValidationError, match="unique"):
        make_scenario(buyer={"arguments": [ArgumentSpec(id="a", claim="c", grounds="g")]},
                      seller={"arguments": [ArgumentSpec(id="a", claim="c", grounds="g")]})


def test_orchestrator_rejects_protocol_violations():
    class Cheater(RuleBasedSeller):
        def respond(self, state):
            return [Accept(id="s-x", actor_id="seller", round_number=state.round_number, offer_id="not-the-last")]

    sc = make_scenario()
    with pytest.raises(ProtocolViolation, match="last offer"):
        NegotiationOrchestrator(sc, RuleBasedBuyer(sc.buyer), Cheater(sc.seller)).run()


# ---------------------------------------------------------------- argumentation
def test_grounded_semantics_on_a_chain():
    af = ArgumentationFramework({"a", "b", "c"}, {("b", "a"), ("c", "b")})
    assert af.grounded_extension() == {"a", "c"}
    assert af.grounded_labelling()["b"] == "OUT"


def test_grounded_semantics_on_mutual_attack_is_undecided():
    af = ArgumentationFramework({"a", "b", "c"}, {("a", "b"), ("b", "a")})
    labels = af.grounded_labelling()
    assert labels == {"a": "UNDEC", "b": "UNDEC", "c": "IN"}
    assert af.is_conflict_free(af.grounded_extension())


def test_unknown_attack_is_rejected():
    with pytest.raises(ValueError):
        ArgumentationFramework({"a"}, {("a", "zz")})


def test_laptop_scenario_arguments_rebuttals_and_labels():
    sc = load("laptop_sale.json")
    result = run(sc)
    args = [m for m in result.moves if m.type == "argument"]
    assert [a.node_id for a in args][:2] == ["b1", "s2"]  # the seller rebuts the buyer's comparables
    assert args[1].attacks == ["b1"]
    labels = ArgumentationFramework.from_moves(result.moves).grounded_labelling()
    assert labels["b1"] == "IN" and labels["s2"] == "OUT"  # b3 reinstates b1 by defeating s2


def test_persuasion_changes_the_outcome():
    base = load("laptop_sale.json")
    neutral = base.model_copy(update={
        "buyer": base.buyer.model_copy(update={"persuadability": 0.0}),
        "seller": base.seller.model_copy(update={"persuadability": 0.0})})
    persuaded = base.model_copy(update={
        "buyer": base.buyer.model_copy(update={"persuadability": 0.0}),
        "seller": base.seller.model_copy(update={"persuadability": 0.2})})
    # The buyer wins the argument, so a persuadable seller concedes more.
    assert run(persuaded).agreed_price < run(neutral).agreed_price


# ---------------------------------------------------------------- metrics, tournament, replay, CLI
def test_metrics_split_the_surplus():
    sc = make_scenario()
    m = evaluate(run(sc), sc)
    assert m.buyer_utility + m.seller_utility == pytest.approx(1.0)
    assert m.nash_product == pytest.approx(m.buyer_utility * m.seller_utility)
    assert not m.missed_deal and m.zopa == (700, 900)


def test_metrics_without_zopa():
    sc = load("no_zopa.json")
    m = evaluate(run(sc), sc)
    assert m.zopa is None and m.buyer_utility is None and not m.missed_deal


def test_boulware_beats_conceder():
    summary = {(r["buyer_tactic"], r["seller_tactic"]): r for r in summarize(run_tournament(random_scenarios(50)))}
    assert summary[("boulware", "conceder")]["buyer_utility"] > summary[("conceder", "boulware")]["buyer_utility"]


def test_tournament_is_reproducible():
    assert run_tournament(random_scenarios(10, seed=3)) == run_tournament(random_scenarios(10, seed=3))


def test_trace_round_trips_through_json():
    result = run(load("laptop_sale.json"))
    assert NegotiationResult.model_validate_json(result.model_dump_json()) == result


def test_cli_run_and_tournament(capsys, tmp_path):
    out = tmp_path / "trace.json"
    assert main(["run", str(SCENARIOS / "laptop_sale.json"), "--out", str(out)]) == 0
    assert "Argument graph" in capsys.readouterr().out
    assert json.loads(out.read_text())["status"] == "deal"
    assert main(["tournament", "--n", "5"]) == 0
    assert "boulware" in capsys.readouterr().out
