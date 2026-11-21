import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.data_preparation.prepare_tomato_pest_rejection import (
    REJECTION_LABEL,
    add_rejection_examples,
)


class TomatoPestRejectionTests(unittest.TestCase):
    def test_builds_balanced_non_pest_class_without_cross_split_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pest_root = root / "pest"
            leaf_root = root / "leaf"
            produce_root = root / "produce"
            for split, count in (("train", 4), ("validation", 2), ("test", 2)):
                for code in ("BA", "HA"):
                    folder = pest_root / split / code
                    folder.mkdir(parents=True, exist_ok=True)
                    for index in range(count // 2):
                        Image.new(
                            "RGB", (20, 20), (index + 1, 0, 0)
                        ).save(folder / f"{index}.jpg")
                for source_root, offset in ((leaf_root, 30), (produce_root, 60)):
                    folder = source_root / split / "sample"
                    folder.mkdir(parents=True, exist_ok=True)
                    for index in range(10):
                        Image.new(
                            "RGB", (20, 20), (offset + index, 0, 0)
                        ).save(folder / f"{index}.jpg")

            (pest_root / "class_labels.json").write_text(
                json.dumps({"classes": ["BA", "HA"], "class_to_idx": {"BA": 0, "HA": 1}}),
                encoding="utf-8",
            )
            (pest_root / "dataset_manifest.json").write_text(
                json.dumps({
                    "classes": ["BA", "HA"],
                    "class_to_idx": {"BA": 0, "HA": 1},
                    "split_counts": {
                        "train": {"BA": 2, "HA": 2},
                        "validation": {"BA": 1, "HA": 1},
                        "test": {"BA": 1, "HA": 1},
                    },
                }),
                encoding="utf-8",
            )

            manifest = add_rejection_examples(
                pest_data=pest_root,
                leaf_data=leaf_root,
                produce_data=produce_root,
                seed=3,
            )

            self.assertEqual(
                manifest["reject_split_counts"],
                {"train": 4, "validation": 2, "test": 2},
            )
            self.assertIn(REJECTION_LABEL, manifest["classes"])
            for split in ("train", "validation", "test"):
                self.assertEqual(
                    len(list((pest_root / split / REJECTION_LABEL).iterdir())),
                    manifest["reject_split_counts"][split],
                )


if __name__ == "__main__":
    unittest.main()
