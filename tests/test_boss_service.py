import tempfile
import time
import unittest
from pathlib import Path

from weapon_bot.bosses.service import BossService
from weapon_bot.bosses.store import BossStore
from weapon_bot.database import WeaponMirror
from weapon_bot.nagi_api import NagiApiError


class FakeApi:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.calls: list[dict] = []

    async def wallet_transaction(self, user_id: str, **kwargs) -> dict:
        self.calls.append({"user_id": user_id, **kwargs})
        if self.fail_first:
            self.fail_first = False
            raise NagiApiError(503, "nagi_unavailable", "unavailable")
        return {"money": 9_000, "transactionId": "tx-1"}


class BossServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = str(Path(self.temp_dir.name) / "pirate.db")
        self.mirror = WeaponMirror(path)
        self.mirror.initialize()
        self.store = BossStore(path)
        self.store.initialize()
        now = time.time()
        boss = {
            "boss_id": "kraken",
            "name": "クラーケン",
            "difficulty": "通常",
            "attack": 30,
            "defense": 2,
            "reward": 600,
            "icon": "🐙",
            "description": "海魔。",
            "skills": [],
            "phases": [],
        }
        self.store.create_event(
            guild_id="guild",
            channel_id="channel",
            boss=boss,
            solo_hp=100,
            party_hp=400,
            duration_seconds=3600,
            party_window_seconds=60,
            special_event=None,
            now=now,
        )
        self.store.create_solo_run("guild", "user", "Pirate", now + 1)
        self.api = FakeApi(fail_first=True)
        self.service = BossService(self.api, self.mirror, self.store)

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_pending_charge_retries_with_same_idempotency_key(self) -> None:
        with self.assertRaises(NagiApiError):
            await self.service.perform_action(
                interaction_id="first-interaction",
                user_id="user",
                action_type="attack",
                cost=100,
                damage=12,
                counter_damage=5,
            )

        result = await self.service.perform_action(
            interaction_id="new-interaction",
            user_id="user",
            action_type="attack",
            cost=100,
            damage=20,
            counter_damage=5,
        )
        self.assertTrue(result["recovered_previous_action"])
        self.assertEqual(12, result["damage"])
        self.assertEqual(
            "boss-action:first-interaction",
            self.api.calls[0]["idempotency_key"],
        )
        self.assertEqual(
            self.api.calls[0]["idempotency_key"],
            self.api.calls[1]["idempotency_key"],
        )

    async def test_same_interaction_is_applied_only_once(self) -> None:
        self.api.fail_first = False
        first = await self.service.perform_action(
            interaction_id="same-interaction",
            user_id="user",
            action_type="attack",
            cost=100,
            damage=12,
            counter_damage=5,
        )
        repeated = await self.service.perform_action(
            interaction_id="same-interaction",
            user_id="user",
            action_type="attack",
            cost=100,
            damage=12,
            counter_damage=5,
        )
        self.assertTrue(first["newly_applied"])
        self.assertFalse(repeated["newly_applied"])
        self.assertEqual(1, len(self.api.calls))


if __name__ == "__main__":
    unittest.main()
