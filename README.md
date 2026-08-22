# Multi-Agent Negotiation & Argumentation Framework

It contains typed scenario and move schemas, deterministic buyer/seller agents,
and a small turn-based orchestrator. No LLM, argument graph, UI, metrics, or
benchmarking layer is included yet.

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
python examples/run_price_negotiation.py
pytest
```

## What is implemented

- JSON/YAML-ready Pydantic schemas for a buyer/seller price scenario.
- Typed `Offer`, `CounterOffer`, `Accept`, `Reject`, and `Argument` moves.
- Configurable rule-based strategies (reservation price and concession rate).
- A framework-agnostic alternating-turn orchestrator that ends on a deal,
  deadline, or impasse.

## Scenario format

```json
{
  "id": "laptop-sale",
  "resource": "used laptop",
  "currency": "EUR",
  "buyer": {"id": "buyer", "reservation_price": 900, "initial_offer": 650, "concession_rate": 0.5},
  "seller": {"id": "seller", "reservation_price": 700, "initial_offer": 1000, "concession_rate": 0.5},
  "max_rounds": 6
}
```

Private reservation prices are held in each agent profile. A scenario can be
loaded with `PriceNegotiationScenario.model_validate_json(...)`.
