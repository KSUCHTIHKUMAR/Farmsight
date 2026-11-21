import unittest

from app.tomato_pest_labels import select_tomato_pest


class TomatoPestLabelTests(unittest.TestCase):
    def test_selects_stable_supported_pest_category(self):
        prediction = select_tomato_pest(
            ["BA", "Not_Tomato_Pest"], [0.82, 0.18], True
        )

        self.assertEqual(prediction, ("BA", 0.82, False))

    def test_reject_class_never_becomes_a_pest_prediction(self):
        prediction = select_tomato_pest(
            ["BA", "Not_Tomato_Pest"], [0.10, 0.90], True
        )

        self.assertEqual(prediction, (None, 0.90, True))

    def test_uncertain_or_unstable_pest_predictions_abstain(self):
        low_confidence = select_tomato_pest(
            ["BA", "Not_Tomato_Pest"], [0.55, 0.45], True
        )
        unstable = select_tomato_pest(
            ["BA", "Not_Tomato_Pest"], [0.80, 0.20], False
        )

        self.assertEqual(low_confidence, (None, 0.55, False))
        self.assertEqual(unstable, (None, 0.80, False))

    def test_invalid_label_mappings_are_rejected(self):
        with self.assertRaises(ValueError):
            select_tomato_pest(["other"], [1.0], True)
        with self.assertRaises(ValueError):
            select_tomato_pest(["BA"], [], True)


if __name__ == "__main__":
    unittest.main()
