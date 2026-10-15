"""Run the laptop scenario and print the transcript, argument graph and metrics."""

from pathlib import Path

from negotiation import PriceNegotiationScenario, evaluate, run
from negotiation.reporting import format_argument_graph, format_metrics, format_transcript

scenario = PriceNegotiationScenario.model_validate_json(
    (Path(__file__).resolve().parents[1] / "scenarios" / "laptop_sale.json").read_text(encoding="utf-8")
)
result = run(scenario)
print(format_transcript(result, scenario), format_argument_graph(result),
      format_metrics(evaluate(result, scenario)), sep="\n\n")
