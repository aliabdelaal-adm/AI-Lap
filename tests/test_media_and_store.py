from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from studio_ai_lab.media import detect_media_type, user_directory
from studio_ai_lab.store import JobStore


class MediaTests(unittest.TestCase):
    def test_supported_signatures(self) -> None:
        self.assertEqual(detect_media_type(b"\xff\xd8\xffrest", "image"), "jpg")
        self.assertEqual(detect_media_type(b"\x89PNG\r\n\x1a\nrest", "image"), "png")
        self.assertEqual(
            detect_media_type(b"RIFF0000WEBP", "image"),
            "webp",
        )
        self.assertEqual(
            detect_media_type(b"RIFF0000WAVE", "audio"),
            "wav",
        )
        self.assertEqual(detect_media_type(b"ID3rest", "audio"), "mp3")

    def test_m4a_requires_expected_container_and_extension(self) -> None:
        header = b"\x00\x00\x00\x18ftypM4A "
        self.assertEqual(detect_media_type(header, "audio", "voice.m4a"), "m4a")
        self.assertIsNone(detect_media_type(header, "audio", "voice.mp4"))

    def test_unknown_signature_is_rejected(self) -> None:
        self.assertIsNone(detect_media_type(b"not media", "image"))
        self.assertIsNone(detect_media_type(b"not media", "audio"))

    def test_user_directories_do_not_use_user_input_as_a_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o777)
            directory = user_directory(root, "../../escape")
            self.assertTrue(directory.is_relative_to(root))
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)


class StoreTests(unittest.TestCase):
    def test_quota_and_owner_scoped_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = JobStore(Path(temporary) / "jobs.sqlite3")
            self.assertTrue(store.create("job-a", "alice", {}, [], 1))
            self.assertFalse(store.create("job-b", "alice", {}, [], 1))
            self.assertIsNone(store.get("job-a", "bob"))
            self.assertEqual(store.get("job-a", "alice")["status"], "waiting")
            self.assertTrue(store.cancel("job-a", "alice"))
            self.assertEqual(store.get("job-a", "alice")["status"], "cancelled")
            self.assertTrue(store.create("job-b", "alice", {}, [], 1))


if __name__ == "__main__":
    unittest.main()
