"""Typed, replayable multi-agent negotiation with structured argumentation."""

from .agents import TACTICS, NegotiationAgent, NegotiationState, RuleBasedBuyer, RuleBasedSeller, TimeDependentAgent
from .argumentation import ArgumentationFramework
from .metrics import NegotiationMetrics, evaluate
from .orchestrator import NegotiationOrchestrator, ProtocolViolation
from .schemas import (
    Accept,
    AgentProfile,
    Argument,
    ArgumentSpec,
    CounterOffer,
    NegotiationResult,
    Offer,
    PriceNegotiationScenario,
    Reject,
)
from .tournament import random_scenarios, run, run_tournament, summarize

__all__ = [
    "TACTICS", "Accept", "AgentProfile", "Argument", "ArgumentSpec", "ArgumentationFramework",
    "CounterOffer", "NegotiationAgent", "NegotiationMetrics", "NegotiationOrchestrator",
    "NegotiationResult", "NegotiationState", "Offer", "PriceNegotiationScenario", "ProtocolViolation",
    "Reject", "RuleBasedBuyer", "RuleBasedSeller", "TimeDependentAgent", "evaluate",
    "random_scenarios", "run", "run_tournament", "summarize",
]
