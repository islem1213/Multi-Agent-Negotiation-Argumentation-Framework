"""Human-readable rendering of traces, argument graphs and tables."""

from __future__ import annotations

from .argumentation import ArgumentationFramework
from .metrics import NegotiationMetrics
from .schemas import Accept, Argument, CounterOffer, NegotiationResult, Offer, PriceNegotiationScenario, Reject


def format_transcript(result: NegotiationResult, scenario: PriceNegotiationScenario) -> str:
    cur = scenario.currency
    lines = [f"Negotiation '{scenario.id}' over {scenario.resource} ({scenario.max_rounds} rounds max)"]
    for m in result.moves:
        head = f"  R{m.round_number} {m.actor_id:>8}"
        if isinstance(m, (Offer, CounterOffer)):
            lines.append(f"{head}  {m.type.replace('_', '-'):<13} {m.price:,.2f} {cur}")
        elif isinstance(m, Accept):
            lines.append(f"{head}  accept        {m.offer_id}")
        elif isinstance(m, Reject):
            lines.append(f"{head}  reject        {m.reason}")
        elif isinstance(m, Argument):
            target = f" (attacks {', '.join(m.attacks)})" if m.attacks else ""
            lines.append(f"{head}  argue [{m.node_id}] {m.claim} -- because {m.grounds}{target}")
    outcome = f"{result.status.upper()}"
    if result.agreed_price is not None:
        outcome += f" at {result.agreed_price:,.2f} {cur}"
    lines.append(f"  => {outcome} after {result.rounds_played} round(s)")
    return "\n".join(lines)


def format_argument_graph(result: NegotiationResult) -> str:
    framework = ArgumentationFramework.from_moves(result.moves)
    if not framework.arguments:
        return "No arguments were exchanged."
    labels = framework.grounded_labelling()
    lines = ["Argument graph (grounded semantics):"]
    for arg in sorted(framework.arguments):
        attackers = sorted(framework.attackers(arg))
        by = f" <- attacked by {', '.join(attackers)}" if attackers else ""
        lines.append(f"  [{labels[arg]:>5}] {arg} ({framework.owner[arg]}){by}")
    return "\n".join(lines)


def format_metrics(m: NegotiationMetrics) -> str:
    def f(x):
        return "-" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))

    zopa = "empty" if m.zopa is None else f"[{m.zopa[0]:g}, {m.zopa[1]:g}]"
    return "\n".join([
        "Metrics:",
        f"  status={m.status}  ZOPA={zopa}  missed_deal={m.missed_deal}",
        f"  buyer_utility={f(m.buyer_utility)}  seller_utility={f(m.seller_utility)}  "
        f"nash={f(m.nash_product)}  fairness_gap={f(m.fairness_gap)}",
        f"  concession: buyer={m.buyer_concession:.2f} seller={m.seller_concession:.2f}  "
        f"moves={m.n_moves} offers={m.n_offers} arguments={m.n_arguments}",
        f"  arguments accepted={m.accepted_arguments} defeated={m.defeated_arguments} "
        f"undecided={m.undecided_arguments}",
    ])


def format_table(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"
    cols = list(rows[0])
    cells = [[("-" if r[c] is None else str(r[c])) for c in cols] for r in rows]
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(cols)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    return "\n".join([fmt.format(*cols), fmt.format(*("-" * w for w in widths)),
                      *(fmt.format(*row) for row in cells)])
