"""Crop inference helpers for the all-crop leaf disease classifier."""

import math
from collections.abc import Sequence

try:
    from .produce_labels import normalize_crop_name
except ImportError:
    from produce_labels import normalize_crop_name


def leaf_crop_classes(classes: Sequence[str], crop: str) -> list[int]:
    crop_key = normalize_crop_name(crop)
    return [
        index for index, label in enumerate(classes)
        if "___" in label
        and normalize_crop_name(label.split("___", maxsplit=1)[0]) == crop_key
    ]


def rank_leaf_crops(
    classes: Sequence[str], probabilities: Sequence[float]
) -> list[tuple[str, float]]:
    """Aggregate disease-class probabilities into ranked crop probabilities."""
    if len(classes) != len(probabilities) or not classes:
        raise ValueError("Leaf classes and probabilities must be non-empty and aligned")

    crop_scores: dict[str, float] = {}
    crop_names: dict[str, str] = {}
    for label, probability in zip(classes, probabilities):
        if not math.isfinite(float(probability)):
            raise ValueError("Leaf probabilities must be finite numbers")
        if "___" not in label:
            continue
        raw_crop = label.split("___", maxsplit=1)[0]
        crop_key = normalize_crop_name(raw_crop)
        crop_names.setdefault(crop_key, raw_crop)
        crop_scores[crop_key] = crop_scores.get(crop_key, 0.0) + float(probability)
    if not crop_scores:
        raise ValueError("The leaf model has no crop-prefixed classes")
    ordered = sorted(crop_scores.items(), key=lambda item: item[1], reverse=True)
    return [(crop_names[key], value) for key, value in ordered]


def infer_leaf_crop(
    classes: Sequence[str], probabilities: Sequence[float]
) -> tuple[str, float, list[int]]:
    """Select the crop with the greatest combined probability mass."""
    crop, confidence = rank_leaf_crops(classes, probabilities)[0]
    return crop, confidence, leaf_crop_classes(classes, crop)


def should_use_potato_tomato_specialist(
    classes: Sequence[str],
    probabilities: Sequence[float],
    specialist_classes: Sequence[str] | None = None,
) -> bool:
    """Route clear potato/tomato candidates to the proven two-crop model."""
    if len(classes) != len(probabilities) or not classes:
        raise ValueError("Leaf classes and probabilities must be non-empty and aligned")

    top_label = classes[max(range(len(probabilities)), key=probabilities.__getitem__)]
    top_crop = normalize_crop_name(top_label.split("___", maxsplit=1)[0])
    if top_crop not in {"potato", "tomato"}:
        return False
    if specialist_classes is not None:
        candidate_labels = [
            label for label in classes
            if "___" in label and normalize_crop_name(label.split("___", maxsplit=1)[0]) == top_crop
        ]
        specialist_labels = set(specialist_classes)
        if not candidate_labels or not set(candidate_labels).issubset(specialist_labels):
            return False

    supported_probability = sum(
        float(probability)
        for label, probability in zip(classes, probabilities)
        if "___" in label and normalize_crop_name(label.split("___", maxsplit=1)[0]) in {"potato", "tomato"}
    )
    return supported_probability >= 0.70


def crop_has_disease_labels(classes: Sequence[str], indices: Sequence[int]) -> bool:
    conditions = set()
    for index in indices:
        if index < 0 or index >= len(classes):
            continue
        label = classes[index]
        if "___" not in label:
            continue
        conditions.add(label.split("___", maxsplit=1)[1].lower())
    return "healthy" in conditions and any(condition != "healthy" for condition in conditions)