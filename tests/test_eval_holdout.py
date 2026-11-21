import unittest

import torch

from scripts.evaluation.eval_holdout import crop_aware_predictions


class CropAwareHoldoutTests(unittest.TestCase):
    def test_predictions_are_restricted_to_the_expected_crop(self):
        classes = [
            "Apple___healthy",
            "Apple___Apple_scab",
            "Tomato___healthy",
            "Tomato___Early_blight",
        ]
        logits = torch.tensor([
            [0.2, 0.3, 0.9, 0.8],
            [0.1, 0.9, 0.2, 0.8],
        ])

        predictions = crop_aware_predictions(logits, [0, 3], classes)

        self.assertEqual(predictions, [1, 3])

    def test_crop_aware_predictions_reject_non_crop_labels(self):
        with self.assertRaisesRegex(ValueError, "Crop___Condition"):
            crop_aware_predictions(torch.tensor([[1.0]]), [0], ["healthy"])


if __name__ == "__main__":
    unittest.main()
