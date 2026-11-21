import unittest

import torch
from torchvision import models

from app.leaf_labels import should_use_potato_tomato_specialist
from app.leaf_labels import crop_has_disease_labels, infer_leaf_crop
from scripts.data_preparation.prepare_leaf_extension import (
    JUTE_CLASS_LABELS,
    TOM_CLASS_LABELS,
    UNKNOWN_LABEL,
    build_class_mapping,
    split_external_records,
)
from scripts.training.train import copy_checkpoint_weights


class LeafExtensionTests(unittest.TestCase):
    def test_expanded_training_labels_keep_new_crops_crop_prefixed(self):
        labels = list(TOM_CLASS_LABELS.values()) + list(JUTE_CLASS_LABELS.values())

        self.assertTrue(all("___" in label for label in labels))
        self.assertIn("Maize___Aphids", labels)
        self.assertIn("Onion___Caterpillar", labels)
        self.assertIn("Tomato___healthy", labels)
        self.assertIn("Jute___healthy", labels)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(UNKNOWN_LABEL, "Unknown___leaf")

    def test_class_mapping_is_unique_across_splits(self):
        classes, mapping = build_class_mapping({
            "train": {"Apple___healthy": 5, "Jute___healthy": 2},
            "validation": {"Apple___healthy": 1, "Jute___healthy": 1},
            "test": {"Apple___healthy": 1},
        })

        self.assertEqual(classes, ["Apple___healthy", "Jute___healthy"])
        self.assertEqual(mapping, {"Apple___healthy": 0, "Jute___healthy": 1})

    def test_unknown_crop_class_does_not_offer_a_disease_diagnosis(self):
        classes = ["Unknown___leaf", "Tomato___healthy"]
        crop, _, indices = infer_leaf_crop(classes, [0.8, 0.2])

        self.assertEqual(crop, "Unknown")
        self.assertFalse(crop_has_disease_labels(classes, indices))

    def test_grouped_split_is_deterministic_and_keeps_families_together(self):
        records = [
            {"label": "Tomato___Alternaria", "family": f"tom:{i}", "path": str(i)}
            for i in range(100)
        ]
        first, _ = split_external_records(records, seed=42)
        second, _ = split_external_records(records, seed=42)

        self.assertEqual(
            {record["path"]: record["split"] for record in first},
            {record["path"]: record["split"] for record in second},
        )
        self.assertEqual(
            {record["split"] for record in first},
            {"train", "validation", "test"},
        )

    def test_same_family_variants_never_cross_splits(self):
        records = [
            {"label": "Jute___healthy", "family": "jute:photo-a", "path": "a1"},
            {"label": "Jute___healthy", "family": "jute:photo-a", "path": "a2"},
            *[
                {"label": "Jute___healthy", "family": f"jute:{i}", "path": str(i)}
                for i in range(2, 20)
            ],
        ]

        assigned, _ = split_external_records(records, seed=7)
        family_splits = {
            record["split"] for record in assigned
            if record["family"] == "jute:photo-a"
        }

        self.assertEqual(len(family_splits), 1)

    def test_checkpoint_head_rows_are_copied_by_label(self):
        previous = models.mobilenet_v2(weights=None)
        previous.classifier[1] = torch.nn.Linear(previous.last_channel, 2)
        with torch.no_grad():
            previous.classifier[1].weight[0].fill_(0.25)
            previous.classifier[1].weight[1].fill_(-0.5)
            previous.classifier[1].bias.copy_(torch.tensor([1.5, -2.0]))
        checkpoint = {
            "state_dict": previous.state_dict(),
            "classes": ["Apple___healthy", "Tomato___healthy"],
            "arch": "mobilenet",
        }

        expanded = models.mobilenet_v2(weights=None)
        expanded.classifier[1] = torch.nn.Linear(expanded.last_channel, 3)
        copy_checkpoint_weights(
            expanded,
            checkpoint,
            ["Jute___healthy", "Tomato___healthy", "Apple___healthy"],
            "mobilenet",
        )

        torch.testing.assert_close(
            expanded.classifier[1].weight[1],
            previous.classifier[1].weight[1],
        )
        torch.testing.assert_close(
            expanded.classifier[1].weight[2],
            previous.classifier[1].weight[0],
        )
        torch.testing.assert_close(
            expanded.features[0][0].weight,
            previous.features[0][0].weight,
        )

    def test_specialist_is_bypassed_for_new_crop_specific_classes(self):
        main_classes = [
            "Potato___Early_blight",
            "Potato___healthy",
            "Tomato___Late_blight",
            "Tomato___Helicoverpa",
        ]
        specialist_classes = main_classes[:3]

        self.assertFalse(
            should_use_potato_tomato_specialist(
                main_classes, [0.05, 0.05, 0.70, 0.20], specialist_classes
            )
        )
        self.assertTrue(
            should_use_potato_tomato_specialist(
                main_classes,
                [0.45, 0.30, 0.15, 0.10],
                specialist_classes,
            )
        )


if __name__ == "__main__":
    unittest.main()
