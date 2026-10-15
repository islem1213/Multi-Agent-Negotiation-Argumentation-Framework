# Changelog

## 0.2.0

### Fixed
- **The seller's opening price was never offered.** The seller conceded on its very first move, using
  `round_number=1` in the concession formula. Agents now open with their initial offer.
- **Agents walked away while a deal was still possible.** The buyer rejected as soon as its *next* concession
  would reach its limit, even when a zone of agreement existed. Agents now reject only after they have offered
  their reservation price, or on the last turn.
- **Agents accepted deals worse than their own next offer.** Acceptance now follows the AC_next rule.

### Added
- Time-dependent concession tactics (Boulware, linear, Conceder) through `AgentProfile.beta`.
- Argument moves with attack relations, and argument scripts declared in each scenario.
- Dung abstract argumentation with grounded semantics (`ArgumentationFramework`).
- A persuasion mechanism (`persuadability`): accepted opponent arguments speed up concession.
- `NegotiationAgent` protocol for pluggable agents (e.g. LLM-backed).
- Move validation in the orchestrator, raising `ProtocolViolation`.
- `first_mover` option on scenarios.
- Scenario consistency checks.
- Evaluation metrics: ZOPA, surplus shares, Nash product, fairness gap, concession and argument statistics.
- Reproducible tactic tournaments.
- `negotiate` command-line tool with `run` and `tournament`.
- Example scenarios, GitHub Actions CI and an expanded test suite (3 → 23 tests).

### Changed (breaking)
- `AgentProfile.concession_rate` is replaced by `beta`.
- `respond(round_number, last_offer)` is now `respond(state) -> list[move]`.
