"""Label and abstention helpers for the separate tomato-pest classifier."""

import math
from collections.abc import Sequence


TOMATO_PEST_CLASSES = ("BA", "HA", "MP", "SE", "SL", "TP", "TU", "ZC")
NOT_TOMATO_PEST = "Not_Tomato_Pest"


def select_tomato_pest(
    classes: Sequence[str],
    probabilities: Sequence[float],
    prediction_stable: bool,
    minimum_confidence: float = 0.60,
) -> tuple[str | None, float, bool]:
    """Return (pest code, confidence, is_non_target) or abstain on uncertainty."""
    if len(classes) != len(probabilities) or not classes:
        raise ValueError("Pest classes and probabilities must be non-empty and aligned")
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("Minimum confidence must be between zero and one")

    for probability in probabilities:
        if probability is None or not math.isfinite(float(probability)):
            raise ValueError("Pest probabilities must be finite numbers")
        if float(probability) < 0.0 or float(probability) > 1.0:
            raise ValueError("Pest probabilities must be between zero and one")

    top_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    label = classes[top_index]
    confidence = float(probabilities[top_index])
    if not prediction_stable or confidence < minimum_confidence:
        return None, confidence, False
    if label == NOT_TOMATO_PEST:
        return None, confidence, True
    if label not in TOMATO_PEST_CLASSES:
        raise ValueError(f"Unknown tomato pest label: {label}")
    return label, confidence, False
