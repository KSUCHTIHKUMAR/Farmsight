import asyncio
import io
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from PIL import Image

import server


def _post_analysis(task: str, filename: str, content: bytes) -> dict:
    upload = UploadFile(filename=filename, file=io.BytesIO(content))
    return asyncio.run(server.analyse(task, upload, crop=None))


class FarmSightApiTests(unittest.TestCase):
    def test_health_reports_original_model_paths(self):
        response = server.health()

        self.assertTrue(response["ok"])
        self.assertEqual(set(response["models"]), set(server.MODEL_FILES))
        self.assertTrue(response["models"]["leaf"])
        self.assertTrue(response["models"]["produce"])
        self.assertTrue(response["models"]["tomato_pest"])

    def test_rejects_unknown_task_without_running_inference(self):
        with self.assertRaises(HTTPException) as raised:
            _post_analysis("unknown", "sample.jpg", b"not an image")
        self.assertEqual(raised.exception.status_code, 400)

    def test_rejects_oversized_image_before_decode(self):
        payload = b"x" * (server.MAX_UPLOAD_BYTES + 1)

        with self.assertRaises(HTTPException) as raised:
            _post_analysis("leaf", "large.jpg", payload)
        self.assertEqual(raised.exception.status_code, 413)

    def test_maps_original_result_to_frontend_contract(self):
        photo = Image.new("RGB", (16, 16), "green")
        original_result = {
            "classes": ["Apple__Healthy", "Apple__Rotten", "Banana__Healthy"],
            "probs": [0.8, 0.1, 0.1],
            "order": [0, 1, 2],
            "view": photo,
            "overlay": photo,
            "produce": "Apple",
            "produce_probability": 0.9,
            "grade": "fresh",
            "grade_probability": 0.8,
        }

        with patch.object(server.original_app, "analyse", return_value=original_result):
            result = server.analyse_image("produce", photo)

        self.assertEqual(result["task"], "produce")
        self.assertTrue(result["confident"])
        self.assertEqual(result["top"][0]["label"], "Apple__Healthy")
        self.assertEqual(result["fruit"], {"name": "Apple", "prob": 0.9})
        self.assertEqual(result["state"], {"name": "fresh", "prob": 0.8})
        self.assertTrue(result["images"]["heatmap"].startswith("data:image/jpeg;base64,"))

    def test_rejects_non_image_payload(self):
        with self.assertRaises(HTTPException) as raised:
            _post_analysis("leaf", "broken.jpg", b"not an image")
        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
