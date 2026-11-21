"""Input-type checks shared by leaf and produce image flows."""

import math
from collections.abc import Sequence


def task_image_confidence(
    task: str, classes: Sequence[str], probabilities: Sequence[float]
) -> float:
    """Return the gate probability for a task, or zero when another class wins."""
    if task not in {"leaf", "produce"}:
        raise ValueError(f"Unsupported image task: {task}")
    if len(classes) != len(probabilities) or not classes:
        raise ValueError("Image-gate classes and probabilities must be non-empty and aligned")

    for probability in probabilities:
        if probability is None or not math.isfinite(float(probability)):
            raise ValueError("Image-gate probabilities must be finite numbers")
        if float(probability) < 0.0 or float(probability) > 1.0:
            raise ValueError("Image-gate probabilities must be between zero and one")

    top_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    if classes[top_index] != task:
        return 0.0
    return float(probabilities[top_index])
