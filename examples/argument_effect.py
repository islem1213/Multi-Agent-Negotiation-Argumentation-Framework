"""Does arguing change the outcome? Same scenario, persuadability 0 vs. > 0.

With persuadability = 0, arguments are recorded in the trace but have no effect
on the price. With persuadability > 0, each argument of the opponent that is
accepted under grounded semantics accelerates an agent's concession.
"""

from pathlib import Path

from negotiation import PriceNegotiationScenario, evaluate, run

base = PriceNegotiationScenario.model_validate_json(
    (Path(__file__).resolve().parents[1] / "scenarios" / "laptop_sale.json").read_text(encoding="utf-8")
)

print(f"{'persuadability':>14}  {'status':>8}  {'price':>8}  {'buyer_u':>7}  {'seller_u':>8}  {'rounds':>6}")
for p in (0.0, 0.1, 0.2, 0.3):
    sc = base.model_copy(update={
        "buyer": base.buyer.model_copy(update={"persuadability": p}),
        "seller": base.seller.model_copy(update={"persuadability": p}),
    })
    m = evaluate(run(sc), sc)
    print(f"{p:>14.1f}  {m.status:>8}  {m.agreed_price or 0:>8.2f}  {m.buyer_utility or 0:>7.3f}  "
          f"{m.seller_utility or 0:>8.3f}  {m.rounds_played:>6}")
