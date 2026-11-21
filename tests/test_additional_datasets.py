import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.data_preparation.prepare_additional_datasets import (
    audit_class_tree,
    clean_new_records,
    split_records,
)


class AdditionalDatasetTests(unittest.TestCase):
    def test_audit_counts_classes_and_exact_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            class_root = root / "healthy"
            class_root.mkdir()
            image = Image.new("RGB", (32, 24), color=(30, 120, 60))
            image.save(class_root / "one.jpg")
            image.save(class_root / "duplicate.jpg")

            audit = audit_class_tree(root, {"healthy": "Groundnut___healthy"}, "test")

        self.assertEqual(audit["images"], 2)
        self.assertEqual(audit["classes"], 1)
        self.assertEqual(audit["class_counts"], {"Groundnut___healthy": 2})
        self.assertEqual(audit["corrupt_count"], 0)
        self.assertEqual(audit["exact_duplicate_groups"], 1)
        self.assertEqual(audit["exact_duplicate_extra_copies"], 1)

    def test_source_families_stay_in_one_stratified_split(self):
        records = [
            {
                "label": "HA",
                "family": f"pest:HA:{index}",
                "path": str(index),
            }
            for index in range(20)
        ]
        records.extend(
            [
                {"label": "HA", "family": "pest:HA:family", "path": "family-a"},
                {"label": "HA", "family": "pest:HA:family", "path": "family-b"},
            ]
        )

        assigned, small_classes = split_records(records, seed=7)
        family_splits = {
            record["split"]
            for record in assigned
            if record["family"] == "pest:HA:family"
        }

        self.assertFalse(small_classes)
        self.assertEqual(len(family_splits), 1)
        self.assertEqual(
            {record["split"] for record in assigned},
            {"train", "validation", "test"},
        )

    def test_exact_duplicates_with_conflicting_labels_are_removed(self):
        records = [
            {"digest": "same", "label": "class-a", "path": Path("a"), "relative_path": "a"},
            {"digest": "same", "label": "class-b", "path": Path("b"), "relative_path": "b"},
            {"digest": "unique", "label": "class-a", "path": Path("c"), "relative_path": "c"},
        ]

        retained, report = clean_new_records(records)

        self.assertEqual([record["relative_path"] for record in retained], ["c"])
        self.assertEqual(report["ambiguous_duplicate_groups_removed"], 1)
        self.assertEqual(report["exact_duplicates_removed"], 0)


if __name__ == "__main__":
    unittest.main()
