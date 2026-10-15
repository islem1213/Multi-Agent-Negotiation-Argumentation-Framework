"""Batch experiments: run every pair of concession tactics over many scenarios."""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import mean

from .agents import TACTICS, RuleBasedBuyer, RuleBasedSeller
from .metrics import evaluate
from .orchestrator import NegotiationOrchestrator
from .schemas import AgentProfile, NegotiationResult, PriceNegotiationScenario


def run(scenario: PriceNegotiationScenario) -> NegotiationResult:
    """Run a scenario with the rule-based buyer and seller."""
    return NegotiationOrchestrator(scenario, RuleBasedBuyer(scenario.buyer), RuleBasedSeller(scenario.seller)).run()


def random_scenarios(n: int, seed: int = 0, max_rounds: int = 8) -> list[PriceNegotiationScenario]:
    """Generate ``n`` reproducible scenarios; roughly 3/4 of them have a non-empty ZOPA."""
    rng = random.Random(seed)
    scenarios = []
    for i in range(n):
        seller_res = rng.uniform(400, 800)
        buyer_res = rng.uniform(450, 1000)
        scenarios.append(PriceNegotiationScenario(
            id=f"random-{seed}-{i}", resource="item", max_rounds=max_rounds,
            buyer=AgentProfile(id="buyer", reservation_price=round(buyer_res, 2),
                               initial_offer=round(buyer_res * rng.uniform(0.55, 0.85), 2)),
            seller=AgentProfile(id="seller", reservation_price=round(seller_res, 2),
                                initial_offer=round(seller_res * rng.uniform(1.15, 1.6), 2)),
        ))
    return scenarios


def run_tournament(scenarios: list[PriceNegotiationScenario],
                   tactics: dict[str, float] | None = None) -> list[dict]:
    """One row per (scenario, buyer tactic, seller tactic)."""
    tactics = tactics or TACTICS
    rows = []
    for scenario in scenarios:
        for b_name, b_beta in tactics.items():
            for s_name, s_beta in tactics.items():
                sc = scenario.model_copy(update={
                    "buyer": scenario.buyer.model_copy(update={"beta": b_beta}),
                    "seller": scenario.seller.model_copy(update={"beta": s_beta}),
                })
                m = evaluate(run(sc), sc)
                rows.append({"scenario": sc.id, "buyer_tactic": b_name, "seller_tactic": s_name,
                             **m.model_dump(include={"status", "deal", "missed_deal", "agreed_price",
                                                     "rounds_played", "buyer_utility", "seller_utility",
                                                     "nash_product"})})
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    """Aggregate tournament rows per tactic pairing (utilities over deals only)."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["buyer_tactic"], row["seller_tactic"])].append(row)

    def avg(values):
        values = [v for v in values if v is not None]
        return round(mean(values), 3) if values else None

    summary = []
    for (b, s), group in groups.items():
        deals = [r for r in group if r["deal"]]
        possible = [r for r in group if r["deal"] or r["missed_deal"]]
        summary.append({
            "buyer_tactic": b, "seller_tactic": s, "n": len(group),
            "deal_rate_when_possible": round(len(deals) / len(possible), 3) if possible else None,
            "buyer_utility": avg(r["buyer_utility"] for r in deals),
            "seller_utility": avg(r["seller_utility"] for r in deals),
            "nash_product": avg(r["nash_product"] for r in deals),
            "rounds": avg(r["rounds_played"] for r in group),
        })
    return summary
