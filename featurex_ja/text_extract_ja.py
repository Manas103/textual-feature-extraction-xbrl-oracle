"""The Japanese text-rule reading: matches a filing's own
`label_text[field]` (one of `config.TEXT_LABELS_JA[field]`'s real
vocabulary choices) back to a field by exact membership, the Japanese
analogue of `featurex/text_extract.py`'s English keyword matching.

Because this reading always recovers the field whose own real label it
was handed, it is correct by construction here; its role is to be the
independent second reading the LLM extraction in `llm_extract.py` is
checked against (`measurements.py::measure_raw_agreement`), exactly the
role `featurex/text_extract.py` plays opposite `featurex/oracle.py`.
"""

from __future__ import annotations

from featurex_ja import config


def match_label(label_text: str) -> str | None:
    for field, labels in config.TEXT_LABELS_JA.items():
        if label_text in labels:
            return field
    return None


def true_value_for_label(filing, label_text: str) -> float | None:
    field = match_label(label_text)
    if field is None:
        return None
    return filing.true_values.get(field)
