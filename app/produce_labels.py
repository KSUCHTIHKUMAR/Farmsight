"""Helpers for interpreting the legacy fruit and newer produce model labels."""

import math
import re
from collections.abc import Sequence

LEGACY_LABELS = {
    "apple": ("apple", "fresh"),
    "banana": ("banana", "fresh"),
    "orange": ("orange", "fresh"),
    "rottenapples": ("apple", "rotten"),
    "rottenbanana": ("banana", "rotten"),
    "rottenoranges": ("orange", "rotten"),
}

PRODUCE_DISPLAY_NAMES = {
    "apple": "Apple",
    "banana": "Banana",
    "bellpepper": "Bell pepper",
    "carrot": "Carrot",
    "cucumber": "Cucumber",
    "grape": "Grape",
    "guava": "Guava",
    "jujube": "Jujube",
    "mango": "Mango",
    "orange": "Orange",
    "pomegranate": "Pomegranate",
    "potato": "Potato",
    "strawberry": "Strawberry",
    "tomato": "Tomato",
}


def normalize_crop_name(name: str) -> str:
    """Normalize user-facing crop names to the canonical class identifier."""
    if name is None:
        raise ValueError("Crop name cannot be None")
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def produce_parts(label: str) -> tuple[str, str]:
    """Return the produce name and normalized freshness for a model class."""
    if label in LEGACY_LABELS:
        return LEGACY_LABELS[label]

    parts = label.split("__", maxsplit=1)
    if len(parts) == 2:
        produce, condition = parts
        condition = re.sub(r"[^a-z]", "", condition.lower())
        if condition in {"healthy", "fresh", "rotten"}:
            name = normalize_crop_name(produce)
            if name not in PRODUCE_DISPLAY_NAMES:
                raise ValueError(f"Unsupported produce model class: {label}")
            return PRODUCE_DISPLAY_NAMES[name].lower(), (
                "rotten" if condition == "rotten" else "fresh"
            )

    raise ValueError(f"Unsupported produce model class: {label}")


def produce_guess(label: str) -> str:
    produce, condition = produce_parts(label)
    display_name = PRODUCE_DISPLAY_NAMES.get(normalize_crop_name(produce), produce.title())
    return f"{condition.capitalize()} {display_name}"


def summarize_produce(
    classes: Sequence[str], probabilities: Sequence[float]
) -> tuple[str, float, str, float]:
    """Return the most likely crop and its conditional Fresh/Rotten grade."""
    if len(classes) != len(probabilities) or not classes:
        raise ValueError("Produce classes and probabilities must be non-empty and aligned")

    crop_totals: dict[str, float] = {}
    crop_grades: dict[str, dict[str, float]] = {}
    for label, probability in zip(classes, probabilities):
        if probability is None or not math.isfinite(float(probability)):
            raise ValueError("Produce probabilities must be finite numbers")
        value = float(probability)
        if value < 0.0 or value > 1.0:
            raise ValueError("Produce probabilities must be between zero and one")
        crop, grade = produce_parts(label)
        crop_totals[crop] = crop_totals.get(crop, 0.0) + value
        crop_grades.setdefault(crop, {"fresh": 0.0, "rotten": 0.0})
        crop_grades[crop][grade] += value

    crop = max(crop_totals, key=crop_totals.get)
    crop_probability = crop_totals[crop]
    if crop_probability <= 0:
        raise ValueError("Selected produce class has no probability mass")

    grades = crop_grades[crop]
    fresh_probability = grades["fresh"] / crop_probability
    rotten_probability = grades["rotten"] / crop_probability
    if rotten_probability >= fresh_probability:
        return crop, crop_probability, "rotten", rotten_probability
    return crop, crop_probability, "fresh", fresh_probability
