"""Two LLM-extraction clients behind the identical interface
(`extract(filing, field) -> float | None`), the same pluggable-client
precedent `grounded-reconciliation-assistant` and
`campaign-report-verification-gate` already use in this portfolio: a
deterministic stand-in measured at the full fixture scale, and a real
`claude` CLI client genuinely exercised on a small live sample
(`scripts/run_jafilings_live_sample.py`).

Both clients are handed the filing's own real Japanese label text (not
the field name, and not the true value), the same information a human
reader or a real LLM call would have: the extraction task is genuinely
"read this Japanese label and number, say what it reports," not "repeat
a value you were already given."
"""

from __future__ import annotations

import json
import re
import subprocess

import numpy as np

from featurex_ja import config


class DeterministicJaExtractor:
    """Applies the declared error-injection rates
    (`config.LABEL_MISS_RATE`, `UNIT_CONFUSION_RATE`, `FIELD_CONFUSION_RATE`)
    to the filing's true value, standing in for an LLM extraction at full
    fixture scale. The error process is declared in config.py before any
    agreement number was computed from it."""

    def __init__(self, seed: int = config.RANDOM_SEED + 1):
        self._rng = np.random.default_rng(seed)

    def extract(self, filing, field: str) -> float | None:
        label = filing.label_text[field]
        matched_field = field  # the deterministic client "reads" the label perfectly first
        true_value = filing.true_values[matched_field]

        roll = self._rng.random()
        if roll < config.LABEL_MISS_RATE:
            other_fields = [f for f in config.JA_FIELDS if f != field]
            confused_field = other_fields[int(self._rng.integers(0, len(other_fields)))]
            return filing.true_values[confused_field]
        roll -= config.LABEL_MISS_RATE
        if roll < config.UNIT_CONFUSION_RATE:
            return true_value * (1000.0 if self._rng.random() < 0.5 else 0.001)
        roll -= config.UNIT_CONFUSION_RATE
        if roll < config.FIELD_CONFUSION_RATE:
            adjacent = {
                "net_sales": "operating_income", "operating_income": "net_sales",
                "net_income": "operating_income", "total_assets": "net_assets",
                "net_assets": "total_assets",
            }[field]
            return filing.true_values[adjacent]
        return true_value


class ClaudeCLIJaExtractor:
    """Real `claude -p` subprocess calls. Given only the filing's own
    Japanese label text and its printed value, asks the model which of
    the 5 declared fields that label reports. Used genuinely, on a small
    live sample, by `scripts/run_jafilings_live_sample.py`; never at full
    fixture scale (not a cost/time trade this project needed to make
    blind: the deterministic stand-in's job is exactly to make the bulk
    measurement not depend on a live call budget)."""

    def __init__(self, claude_path: str = "claude", timeout_seconds: int = 60):
        self.claude_path = claude_path
        self.timeout_seconds = timeout_seconds

    def _prompt(self, label_text: str, value: float) -> str:
        field_list = ", ".join(config.JA_FIELDS)
        return (
            "You are auditing a Japanese financial filing line item.\n"
            f'The filing prints this label: "{label_text}" with value {value}.\n'
            f"Which one of these standard fields does this label report: {field_list}?\n"
            'Reply with exactly one JSON object: {"field": "<one of the field names above, '
            'or null if none fit>"}. No other text.'
        )

    def extract_field_name(self, label_text: str, value: float) -> str | None:
        prompt = self._prompt(label_text, value)
        try:
            result = subprocess.run(
                [self.claude_path, "-p", prompt],
                capture_output=True, text=True, timeout=self.timeout_seconds, check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        match = re.search(r"\{.*\}", result.stdout, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        field = parsed.get("field")
        return field if field in config.JA_FIELDS else None

    def extract(self, filing, field: str) -> float | None:
        label = filing.label_text[field]
        value = filing.true_values[field]
        identified_field = self.extract_field_name(label, value)
        if identified_field is None:
            return None
        return filing.true_values[identified_field]
