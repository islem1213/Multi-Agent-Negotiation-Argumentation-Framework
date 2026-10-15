"""Abstract argumentation (Dung, 1995) over the arguments exchanged in a negotiation.

The negotiation trace is turned into an argumentation framework ``(A, R)`` where
``A`` is the set of arguments actually played and ``R`` the attacks between them.
The grounded labelling then says which justifications survive the dialogue:

* ``IN``: accepted (every attacker is OUT),
* ``OUT``: defeated (at least one attacker is IN),
* ``UNDEC``: undecided (e.g. two arguments attacking each other).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from .schemas import Argument

Label = Literal["IN", "OUT", "UNDEC"]


class ArgumentationFramework:
    def __init__(self, arguments: Iterable[str], attacks: Iterable[tuple[str, str]] = ()) -> None:
        self.arguments: set[str] = set(arguments)
        self.attacks: set[tuple[str, str]] = set()
        for attacker, target in attacks:
            if attacker not in self.arguments or target not in self.arguments:
                raise ValueError(f"attack {attacker!r} -> {target!r} refers to an unknown argument")
            self.attacks.add((attacker, target))
        self.owner: dict[str, str] = {}

    @classmethod
    def from_moves(cls, moves: Iterable[object]) -> "ArgumentationFramework":
        """Build the framework from the ``Argument`` moves of a negotiation trace."""
        args = [m for m in moves if isinstance(m, Argument)]
        nodes = {a.node_id for a in args}
        edges = [(a.node_id, t) for a in args for t in a.attacks if t in nodes]
        framework = cls(nodes, edges)
        framework.owner = {a.node_id: a.actor_id for a in args}
        return framework

    def attackers(self, argument: str) -> set[str]:
        return {a for a, t in self.attacks if t == argument}

    def is_conflict_free(self, subset: set[str]) -> bool:
        return not any(a in subset and t in subset for a, t in self.attacks)

    def defends(self, subset: set[str], argument: str) -> bool:
        """True if every attacker of ``argument`` is attacked by some member of ``subset``."""
        return all(self.attackers(b) & subset for b in self.attackers(argument))

    def grounded_labelling(self) -> dict[str, Label]:
        """Grounded labelling, computed as the least fixed point of label propagation."""
        labels: dict[str, Label] = {}
        changed = True
        while changed:
            changed = False
            for arg in sorted(self.arguments - labels.keys()):
                attackers = self.attackers(arg)
                if all(labels.get(b) == "OUT" for b in attackers):
                    labels[arg] = "IN"
                    changed = True
                elif any(labels.get(b) == "IN" for b in attackers):
                    labels[arg] = "OUT"
                    changed = True
        return {arg: labels.get(arg, "UNDEC") for arg in self.arguments}

    def grounded_extension(self) -> set[str]:
        return {a for a, label in self.grounded_labelling().items() if label == "IN"}
