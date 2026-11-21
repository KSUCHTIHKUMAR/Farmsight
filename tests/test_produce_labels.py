import unittest

from app.produce_labels import (
    PRODUCE_DISPLAY_NAMES,
    produce_guess,
    produce_parts,
    summarize_produce,
)


class ProduceLabelTests(unittest.TestCase):
    def test_all_supported_crops_have_fresh_and_rotten_classes(self):
        classes = [
            f"{crop.replace(' ', '')}__{grade}"
            for crop in PRODUCE_DISPLAY_NAMES.values()
            for grade in ("Healthy", "Rotten")
        ]

        self.assertEqual(len(classes), 28)
        self.assertEqual(
            {produce_parts(label)[0] for label in classes},
            {name.lower() for name in PRODUCE_DISPLAY_NAMES.values()},
        )
        self.assertTrue(
            all(
                {produce_parts(label)[1] for label in classes if produce_parts(label)[0] == crop}
                == {"fresh", "rotten"}
                for crop in (name.lower() for name in PRODUCE_DISPLAY_NAMES.values())
            )
        )

    def test_grade_is_conditional_on_selected_crop(self):
        summary = summarize_produce(
            [
                "Apple__Healthy",
                "Apple__Rotten",
                "Banana__Healthy",
                "Banana__Rotten",
            ],
            [0.30, 0.21, 0.0, 0.49],
        )

        self.assertEqual(summary, ("apple", 0.51, "fresh", 0.30 / 0.51))

    def test_bell_pepper_has_consistent_display_name(self):
        self.assertEqual(produce_parts("Bellpepper__Healthy"), ("bell pepper", "fresh"))
        self.assertEqual(produce_parts("Bell Pepper__Healthy"), ("bell pepper", "fresh"))
        self.assertEqual(produce_guess("Bellpepper__Rotten"), "Rotten Bell pepper")
        self.assertEqual(produce_guess("Bell Pepper__Rotten"), "Rotten Bell pepper")

    def test_rejects_misaligned_or_empty_inputs(self):
        for classes, probabilities in (([], []), (["Apple__Healthy"], [])):
            with self.subTest(classes=classes, probabilities=probabilities):
                with self.assertRaises(ValueError):
                    summarize_produce(classes, probabilities)

    def test_rejects_unknown_model_crop(self):
        with self.assertRaises(ValueError):
            produce_parts("UnknownCrop__Healthy")


if __name__ == "__main__":
    unittest.main()
