# Multi-Agent Negotiation & Argumentation Framework

[![tests](https://github.com/islem1213/Multi-Agent-Negotiation-Argumentation-Framework/actions/workflows/tests.yml/badge.svg)](https://github.com/islem1213/Multi-Agent-Negotiation-Argumentation-Framework/actions/workflows/tests.yml)

A small, typed framework in which agents negotiate through **replayable moves and structured arguments**.
Outcomes can be evaluated, and the arguments exchanged are analysed with formal argumentation semantics.

## Motivation / research question

Most multi-agent negotiation demos treat dialogue as unstructured text and
evaluate only the final agreement. This project explores whether negotiations
can instead be represented as typed, replayable moves and arguments, making it
possible to inspect how agents justify, challenge, and revise proposals—not
only whether they reach a deal. The guiding research question is: **how can
structured argument traces make LLM-agent negotiations more transparent,
auditable, and empirically evaluable?**

## Quick start

```bash
python -m pip install -e ".[dev]"
negotiate run scenarios/laptop_sale.json     # transcript + argument graph + metrics
negotiate tournament --n 300                 # compare concession tactics
python examples/argument_effect.py           # does arguing change the price?
pytest
```

Example output (abridged):

```
  R1    buyer  argue [b1] The price should be close to 750 EUR -- because three comparable listings ...
  R1    buyer  offer         650.00 EUR
  R1   seller  argue [s2] Comparable listings are not comparable -- because ... (attacks b1)
  R1   seller  counter-offer 993.25 EUR
  R2    buyer  argue [b3] The remaining warranty adds little value -- because ... (attacks s2)
  ...
  => DEAL at 740.00 EUR after 4 round(s)

Argument graph (grounded semantics):
  [   IN] b1 (buyer) <- attacked by s2
  [  OUT] s2 (seller) <- attacked by b3
  ...
```

## What is implemented

| Layer | Module | What it does |
|---|---|---|
| Protocol | `schemas.py` | Pydantic models for scenarios and moves: `Offer`, `CounterOffer`, `Accept`, `Reject` and `Argument`. Arguments carry attack relations. Scenarios are validated for consistent reservation prices and well-formed argument references. |
| Agents | `agents.py` | A `NegotiationAgent` protocol: any object with `profile` and `respond(state) -> list[move]` can play, including a future LLM agent. Rule-based buyer and seller agents are built on it. |
| Orchestration | `orchestrator.py` | Alternating offers (buyer or seller may open). Every move is validated and a broken rule raises `ProtocolViolation`. The run ends on a deal, an impasse or the deadline. |
| Argumentation | `argumentation.py` | Builds a Dung (1995) abstract argumentation framework from the trace. Computes the grounded labelling (IN / OUT / UNDEC) and the grounded extension. |
| Evaluation | `metrics.py` | Deal and missed-deal flags and ZOPA; each side's surplus share; Nash product and fairness gap; concession per agent; accepted, defeated and undecided arguments per agent. |
| Experiments | `tournament.py` | Reproducible random scenarios and a round-robin over concession tactics, with summary tables. |
| Interface | `cli.py`, `reporting.py` | `negotiate run` / `negotiate tournament`, readable transcripts, and JSON export of replayable traces. |

### Agent behaviour

The rule-based agents use four rules:

- **Time-dependent concession** (Faratin, Sierra & Jennings, 1998). At its k-th offer, an agent proposes
  `initial + (reservation − initial)·t^(1/β)` with `t = k / (max_rounds − 1)`.
  - `β < 1` is **Boulware** (holds firm, concedes late).
  - `β = 1` is linear.
  - `β > 1` is **Conceder** (concedes early).
- **AC_next acceptance.** An agent accepts an offer that is at least as good as the offer it would make next.
- **Walk-away.** An agent rejects only after it has already offered its reservation price, or on the last turn of the negotiation.
- **Arguments and persuasion.**
  - Each turn, an agent plays at most one argument, and rebuttals of opponent arguments take priority.
  - With `persuadability > 0`, every opponent argument that is *accepted under grounded semantics* advances the agent's concession clock.
  - This links the argumentation layer to the negotiated price.

## First results

`negotiate tournament --n 300` (300 random scenarios, 8 rounds, buyer opens):

| buyer \ seller | Boulware | Linear | Conceder |
|---|---|---|---|
| **Boulware** | 0.29 | 0.57 | 0.77 |
| **Linear** | 0.22 | 0.41 | 0.66 |
| **Conceder** | 0.18 | 0.26 | 0.41 |

*Cells: mean share of the surplus obtained by the buyer, over deals.*

- Every possible deal is reached: no missed deal for any pairing.
- **Boulware exploits Conceder**, and the reverse matchup is costly for the conceding side.
- In symmetric pairings, the seller gets more than half of the surplus. Responding last is an advantage, which
  `first_mover` lets you control.

## Scenario format

```json
{
  "id": "laptop-sale",
  "resource": "used laptop",
  "currency": "EUR",
  "max_rounds": 6,
  "first_mover": "buyer",
  "buyer": {
    "id": "buyer", "reservation_price": 900, "initial_offer": 650, "beta": 0.5, "persuadability": 0.15,
    "arguments": [
      {"id": "b1", "claim": "The price should be close to 750 EUR", "grounds": "comparable listings sell for 720-780 EUR"},
      {"id": "b3", "claim": "The remaining warranty adds little value", "grounds": "it expires in four months", "attacks": ["s2"]}
    ]
  },
  "seller": {"id": "seller", "reservation_price": 700, "initial_offer": 1000, "beta": 0.5, "arguments": []}
}
```

Reservation prices stay private to each agent profile; only moves are shared.
Full examples are in [`scenarios/`](scenarios).

## Roadmap

- LLM-backed agents implementing `NegotiationAgent`, whose arguments are parsed into typed `Argument` moves.
- Multi-issue negotiation (price, delivery, warranty) with additive utilities and Pareto analysis.
- Preferred and stable semantics, and value-based argumentation, for richer acceptability analysis.
- Statistical evaluation of argument-driven persuasion across many generated scenarios.

## References

- Dung, P. M. (1995). On the acceptability of arguments and its fundamental role in nonmonotonic reasoning, logic programming and n-person games. *Artificial Intelligence*, 77(2).
- Faratin, P., Sierra, C., & Jennings, N. R. (1998). Negotiation decision functions for autonomous agents. *Robotics and Autonomous Systems*, 24(3–4).
- Rahwan, I., Ramchurn, S. D., Jennings, N. R., McBurney, P., Parsons, S., & Sonenberg, L. (2003). Argumentation-based negotiation. *The Knowledge Engineering Review*, 18(4).
- Baarslag, T. et al. (2014). Effective acceptance conditions in multi-issue negotiation (AC_next). *Proc. AAMAS*.
