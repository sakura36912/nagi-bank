import tempfile
import unittest
from pathlib import Path

from weapon_bot.database import WeaponMirror


class WeaponMirrorTests(unittest.TestCase):
    def test_mirror_persists_and_updates_remote_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = str(Path(temp_dir) / "pirate.db")
            mirror = WeaponMirror(database_path)
            mirror.initialize()

            mirror.save_forge(
                "123",
                {
                    "weaponId": "greatsword",
                    "weapon": "大剣",
                    "level": 1,
                    "attack": 10,
                    "defense": 3,
                    "accuracy": 75,
                    "money": 35_000,
                    "createdAt": "2026-10-16T00:00:00Z",
                    "updatedAt": "2026-10-16T00:00:00Z",
                },
            )
            mirror.save_forge(
                "123",
                {
                    "weaponId": "greatsword",
                    "weapon": "大剣",
                    "level": 1,
                    "attack": 10,
                    "defense": 3,
                    "accuracy": 75,
                    "money": 34_000,
                    "createdAt": "2026-10-16T00:00:00Z",
                    "updatedAt": "2026-10-16T00:01:00Z",
                },
            )

            restored = WeaponMirror(database_path).get_user("123")
            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual("大剣", restored["weapon"])
            self.assertEqual(1, restored["weapon_level"])
            self.assertEqual(34_000, restored["money"])
            self.assertEqual(10, restored["attack"])


if __name__ == "__main__":
    unittest.main()
