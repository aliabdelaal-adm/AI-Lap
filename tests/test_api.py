from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from studio_ai_lab.app import create_app
from studio_ai_lab.config import Settings


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
MP3 = b"ID3" + b"\x00" * 24
TOKEN_A = "user-a-token-" + "a" * 32
TOKEN_B = "user-b-token-" + "b" * 32


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        settings = Settings(
            data_dir=Path(self.temp_dir.name),
            api_tokens={"user-a": TOKEN_A, "user-b": TOKEN_B},
        )
        self.client = TestClient(create_app(settings))

    def create_job(self, token: str = TOKEN_A):
        return self.client.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer " + token},
            data={"scene": "إعلان قصير", "seed": "15"},
            files={
                "image": ("portrait.png", PNG, "image/png"),
                "audio": ("speech.mp3", MP3, "audio/mpeg"),
            },
        )

    def test_unauthenticated_jobs_are_rejected(self) -> None:
        response = self.client.get("/v1/jobs")
        self.assertEqual(response.status_code, 401)

    def test_upload_is_recorded_then_fails_without_fabricating_video(self) -> None:
        response = self.create_job()
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["id"]
        job = self.client.get(
            f"/v1/jobs/{job_id}",
            headers={"Authorization": "Bearer " + TOKEN_A},
        ).json()
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["output_url"])
        self.assertIn("inference was not run", job["error"])
        output = self.client.get(
            f"/v1/jobs/{job_id}/output",
            headers={"Authorization": "Bearer " + TOKEN_A},
        )
        self.assertEqual(output.status_code, 409)

    def test_jobs_are_scoped_to_the_authenticated_user(self) -> None:
        response = self.create_job()
        self.assertEqual(response.status_code, 202)
        job_id = response.json()["id"]
        other_user = self.client.get(
            f"/v1/jobs/{job_id}",
            headers={"Authorization": "Bearer " + TOKEN_B},
        )
        self.assertEqual(other_user.status_code, 404)
        listing = self.client.get(
            "/v1/jobs",
            headers={"Authorization": "Bearer " + TOKEN_B},
        )
        self.assertEqual(listing.json(), [])

    def test_invalid_media_is_rejected_and_partial_upload_is_removed(self) -> None:
        response = self.client.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer " + TOKEN_A},
            data={"scene": "test"},
            files={
                "image": ("portrait.png", b"not an image", "image/png"),
                "audio": ("speech.mp3", MP3, "audio/mpeg"),
            },
        )
        self.assertEqual(response.status_code, 415)
        user_dir = next((Path(self.temp_dir.name) / "users").iterdir())
        upload_dir = user_dir / "uploads"
        self.assertFalse(upload_dir.exists() and any(upload_dir.iterdir()))

    def test_file_limit_is_enforced(self) -> None:
        self.client.close()
        settings = Settings(
            data_dir=Path(self.temp_dir.name) / "small",
            api_tokens={"user-a": TOKEN_A},
            max_image_bytes=16,
        )
        self.client = TestClient(create_app(settings))
        response = self.client.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer " + TOKEN_A},
            data={"scene": "test"},
            files={
                "image": ("portrait.png", PNG, "image/png"),
                "audio": ("speech.mp3", MP3, "audio/mpeg"),
            },
        )
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
