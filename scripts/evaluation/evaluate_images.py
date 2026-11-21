"""Check model predictions against a small, explicitly labelled image manifest."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server import analyse_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "evaluation" / "web_image_manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evaluation" / "web_image_results.json",
    )
    args = parser.parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    results = []
    for group in ("web_images", "workspace_images"):
        for item in manifest.get(group, []):
            image_path = ROOT / item["path"]
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1024, 1024))
                prediction = analyse_image(item["task"], image)

            guesses = prediction["top"]
            top = guesses[0]
            record = {
                **item,
                "group": group,
                "predicted_label": top["label"],
                "predicted_name": top["name"],
                "confidence": top["prob"],
                "top_matches_expected": top["label"] == item["expected_label"],
                "expected_in_top3": any(
                    guess["label"] == item["expected_label"] for guess in guesses
                ),
                "prediction_stable": prediction.get("prediction_stable", True),
                "confident": prediction["confident"],
                "top_guesses": guesses,
            }
            results.append(record)
            print(
                f"{item['path']}: expected={item['expected_label']}; "
                f"predicted={top['label']} ({top['prob']:.1%}); "
                f"top_match={record['top_matches_expected']}; "
                f"stable={record['prediction_stable']}; "
                f"confident={record['confident']}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    evaluated = len(results)
    correct = sum(item["top_matches_expected"] for item in results)
    print(f"\nTop-1 matches: {correct}/{evaluated}")
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
