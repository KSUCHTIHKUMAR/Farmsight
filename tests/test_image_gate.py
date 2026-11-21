import unittest

from app.image_gate import task_image_confidence


class ImageGateTests(unittest.TestCase):
    def test_confidence_is_zero_when_another_gate_class_wins(self):
        self.assertEqual(
            task_image_confidence("produce", ["leaf", "produce", "other"], [0.8, 0.1, 0.1]),
            0.0,
        )

    def test_confidence_is_returned_for_the_requested_task(self):
        self.assertAlmostEqual(
            task_image_confidence("leaf", ["leaf", "produce", "other"], [0.72, 0.2, 0.08]),
            0.72,
        )

    def test_invalid_task_and_misaligned_outputs_are_reported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported image task"):
            task_image_confidence("fruit", ["leaf"], [1.0])
        with self.assertRaisesRegex(ValueError, "non-empty and aligned"):
            task_image_confidence("leaf", ["leaf", "other"], [1.0])


if __name__ == "__main__":
    unittest.main()
