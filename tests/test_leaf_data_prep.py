import hashlib
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from pathlib import Path

from app.leaf_labels import (
    crop_has_disease_labels,
    infer_leaf_crop,
    leaf_crop_classes,
    rank_leaf_crops,
    should_use_potato_tomato_specialist,
)
from scripts.training.baseline_cnn import crop_class_names, filter_dataset_classes
from scripts.data_preparation.prepare_leaf_all_crops import (
    archive_records,
    assign_group_splits,
    deduplicate_output,
)


class LeafDataPreparationTests(unittest.TestCase):
    def test_crop_training_filter_selects_only_requested_crop_classes(self):
        classes = [
            "Apple___healthy",
            "Potato___Early_blight",
            "Potato___healthy",
            "Tomato___Late_blight",
        ]

        self.assertEqual(
            crop_class_names(classes, ["Potato", "Tomato"]),
            ["Potato___Early_blight", "Potato___healthy", "Tomato___Late_blight"],
        )
        with self.assertRaisesRegex(ValueError, "No dataset classes found"):
            crop_class_names(classes, ["Orange"])

    def test_crop_training_filter_remaps_sample_labels(self):
        dataset = SimpleNamespace(
            classes=["Apple___healthy", "Potato___healthy", "Tomato___healthy"],
            samples=[("apple.jpg", 0), ("potato.jpg", 1), ("tomato.jpg", 2)],
            imgs=[],
            targets=[],
            class_to_idx={},
        )

        filtered = filter_dataset_classes(
            dataset, ["Potato___healthy", "Tomato___healthy"]
        )

        self.assertEqual(filtered.samples, [("potato.jpg", 0), ("tomato.jpg", 1)])
        self.assertEqual(filtered.targets, [0, 1])
        self.assertEqual(filtered.class_to_idx, {"Potato___healthy": 0, "Tomato___healthy": 1})

    def test_archive_labels_are_canonical_and_fruit_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "classes.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "disease/Tomato___Tomato_mosaic_virus/mosaic.jpg", b"mosaic"
                )
                archive.writestr(
                    "disease/Pepper,_bell___healthy/pepper.jpg", b"pepper"
                )
                archive.writestr(
                    "disease/mango/Anthracnose/mango.jpg", b"mango leaf"
                )
                archive.writestr(
                    "disease/Guava _Leaf/orginal/Healthy Guava leaf/guava.jpg", b"guava"
                )
                archive.writestr(
                    "disease/Guava _Leaf/augmented/Healthy Guava leaf/augmented.jpg",
                    b"augmented",
                )
                archive.writestr(
                    "disease/pomegranate/Real Field Data Of Pomogranate crop/fruit.jpg",
                    b"fruit",
                )

            records = archive_records(archive_path, set(), set())

        self.assertEqual(
            {record["label"] for record in records},
            {
                "Tomato___Mosaic_virus",
                "Bellpepper___healthy",
                "Mango___Anthracnose",
                "Guava___healthy",
            },
        )

    def test_archive_skips_base_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "classes.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "disease/Tomato___Tomato_mosaic_virus/mosaic.jpg", b"duplicate"
                )

            records = archive_records(
                archive_path,
                set(),
                {("Tomato___Mosaic_virus", "mosaic.jpg")},
            )

        self.assertEqual(records, [])

    def test_stratified_splits_are_nonempty_and_deterministic(self):
        records = [{"key": f"image-{index}"} for index in range(100)]

        first = assign_group_splits([dict(record) for record in records], 42, "Apple___scab")
        second = assign_group_splits([dict(record) for record in records], 42, "Apple___scab")

        self.assertEqual([record["split"] for record in first], [record["split"] for record in second])
        self.assertEqual(
            {record["split"] for record in first},
            {"train", "validation", "test"},
        )

    def test_crop_selection_filters_other_species_and_flags_crop_only(self):
        classes = [
            "Apple___Apple_scab",
            "Apple___Black_rot",
            "Apple___healthy",
            "Tomato___Early_blight",
            "Tomato___healthy",
            "Carrot___leaf",
            "Orange___Huanglongbing",
        ]

        apple_indices = leaf_crop_classes(classes, "Apple")
        carrot_indices = leaf_crop_classes(classes, "Carrot")
        orange_indices = leaf_crop_classes(classes, "Orange")

        self.assertEqual(apple_indices, [0, 1, 2])
        self.assertTrue(crop_has_disease_labels(classes, apple_indices))
        self.assertFalse(crop_has_disease_labels(classes, carrot_indices))
        self.assertFalse(crop_has_disease_labels(classes, orange_indices))

    def test_leaf_crop_is_inferred_from_combined_class_probabilities(self):
        classes = [
            "Apple___Apple_scab",
            "Apple___healthy",
            "Tomato___Early_blight",
            "Tomato___healthy",
            "Carrot___leaf",
        ]
        probabilities = [0.28, 0.25, 0.18, 0.12, 0.17]

        crop, confidence, indices = infer_leaf_crop(classes, probabilities)

        self.assertEqual(crop, "Apple")
        self.assertAlmostEqual(confidence, 0.53)
        self.assertEqual(indices, [0, 1])

    def test_leaf_crop_inference_rejects_misaligned_model_output(self):
        with self.assertRaisesRegex(ValueError, "non-empty and aligned"):
            infer_leaf_crop(["Apple___healthy"], [])

    def test_crop_ranking_aggregates_disease_probabilities(self):
        ranked = rank_leaf_crops(
            [
                "Apple___scab",
                "Apple___healthy",
                "Tomato___Early_blight",
            ],
            [0.2, 0.15, 0.65],
        )

        self.assertEqual(ranked, [("Tomato", 0.65), ("Apple", 0.35)])

    def test_clear_potato_or_tomato_predictions_use_the_specialist(self):
        classes = [
            "Potato___Early_blight",
            "Potato___healthy",
            "Tomato___Early_blight",
            "Apple___healthy",
        ]
        probabilities = [0.28, 0.10, 0.36, 0.26]

        self.assertTrue(should_use_potato_tomato_specialist(classes, probabilities))

    def test_specialist_is_not_used_when_crop_evidence_is_weak_or_other_crop_wins(self):
        classes = ["Potato___Early_blight", "Tomato___Early_blight", "Apple___healthy"]

        self.assertFalse(
            should_use_potato_tomato_specialist(classes, [0.25, 0.20, 0.55])
        )
        self.assertFalse(
            should_use_potato_tomato_specialist(classes, [0.35, 0.30, 0.35])
        )

    def test_deduplication_keeps_one_split_and_drops_conflicting_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            duplicate_paths = [
                output / split / "Apple___healthy" / f"{split}.jpg"
                for split in ("train", "validation", "test")
            ]
            for path in duplicate_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"same image")

            conflicting_paths = [
                output / "train" / "Jujube___Defect" / "ambiguous.jpg",
                output / "test" / "Jujube___Insect_Feeding" / "ambiguous-copy.jpg",
            ]
            for path in conflicting_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"conflicting label")

            counts, report = deduplicate_output(output)

        self.assertEqual(report["duplicate_groups"], 2)
        self.assertEqual(report["ambiguous_groups"], 1)
        self.assertEqual(report["removed_images"], 4)
        self.assertEqual(counts, {"test/Apple___healthy": 1})
        self.assertEqual(list(output.rglob("Jujube___*")), [])

    def test_deduplication_excludes_exact_field_holdout_images(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            image = output / "train" / "Tomato___healthy" / "holdout-copy.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"field holdout")
            holdout_hash = hashlib.sha256(b"field holdout").digest()

            counts, report = deduplicate_output(output, {holdout_hash})

        self.assertEqual(counts, {})
        self.assertEqual(report["holdout_images_removed"], 1)
        self.assertFalse(image.exists())


if __name__ == "__main__":
    unittest.main()