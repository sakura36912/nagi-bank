import tempfile
import time
import unittest
from pathlib import Path

from weapon_bot.bosses.store import (
    AlreadyHunting,
    BossStore,
    EventAlreadyActive,
    PlayerDown,
)
from weapon_bot.database import WeaponMirror


TEST_BOSS = {
    "boss_id": "kraken",
    "name": "クラーケン",
    "difficulty": "通常",
    "attack": 30,
    "defense": 2,
    "reward": 600,
    "icon": "🐙",
    "description": "深海から現れた海魔。",
    "skills": ["触手攻撃"],
    "phases": [],
}


class BossStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp_dir.name) / "pirate.db")
        WeaponMirror(self.path).initialize()
        self.store = BossStore(self.path)
        self.store.initialize()
        self.now = time.time()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_event(self, guild_id: str = "guild-1", party_window: int = 300) -> dict:
        return self.store.create_event(
            guild_id=guild_id,
            channel_id="channel-1",
            boss=TEST_BOSS,
            solo_hp=100,
            party_hp=400,
            duration_seconds=3600,
            party_window_seconds=party_window,
            special_event=None,
            now=self.now,
        )

    def test_only_one_active_event_per_guild(self) -> None:
        self.create_event()
        with self.assertRaises(EventAlreadyActive):
            self.create_event()
        self.create_event(guild_id="guild-2")

    def test_event_and_participation_survive_store_restart(self) -> None:
        self.create_event()
        run = self.store.create_solo_run("guild-1", "user-1", "Pirate", self.now + 1)
        restarted = BossStore(self.path)
        self.assertEqual(run["id"], restarted.get_user_run("user-1")["id"])

    def test_solo_run_is_private_and_user_cannot_join_twice(self) -> None:
        self.create_event()
        run = self.store.create_solo_run("guild-1", "user-1", "Pirate", self.now + 1)
        self.assertEqual("solo", run["mode"])
        self.assertEqual(100, run["current_hp"])
        with self.assertRaises(AlreadyHunting):
            self.store.join_party("guild-1", "user-1", "Pirate", self.now + 2)

    def test_party_starts_at_four_and_shares_one_hp_pool(self) -> None:
        self.create_event()
        for index in range(3):
            run, started = self.store.join_party(
                "guild-1", f"user-{index}", f"pirate-{index}", self.now + index + 1
            )
            self.assertFalse(started)
        run, started = self.store.join_party(
            "guild-1", "user-3", "pirate-3", self.now + 4
        )
        self.assertTrue(started)
        self.assertEqual(400, run["current_hp"])
        self.assertEqual(4, len(run["members"]))

    def test_attacks_are_applied_once_and_create_reward_outbox(self) -> None:
        event = self.create_event()
        run = self.store.create_solo_run("guild-1", "user-1", "Pirate", self.now + 1)
        self.assertEqual("user-1", self.store.get_user_run("user-1")["user_id"])
        self.store.create_action(
            interaction_id="interaction-1",
            user_id="user-1",
            action_type="attack",
            cost=100,
            damage=100,
            counter_damage=25,
            now=self.now + 2,
        )
        self.store.mark_action_charged("interaction-1", 900)
        result = self.store.apply_action("interaction-1")
        self.assertTrue(result["killed"])
        self.assertEqual(100, result["damage"])
        self.assertEqual(100, result["player_hp"])
        self.assertEqual(event["id"], result["event_id"])
        self.assertFalse(self.store.apply_action("interaction-1")["newly_applied"])
        reward = self.store.get_pending_rewards()[0]
        self.assertEqual(600, reward["amount"])
        self.assertEqual(run["id"], reward["run_id"])

        summary = self.store.get_run_result(run["id"])
        self.assertEqual(100, summary["total_damage"])
        self.assertEqual("user-1", summary["mvp"]["user_id"])

    def test_party_recruitment_cancels_a_single_player_after_window(self) -> None:
        self.create_event(party_window=30)
        self.store.join_party("guild-1", "user-1", "Pirate", self.now + 1)
        result = self.store.resolve_party_recruitment(self.now + 32)
        self.assertEqual("cancelled", result[0]["status"])
        self.assertIsNone(self.store.get_user_run("user-1"))

    def test_late_join_opens_a_new_party_after_recruitment_deadline(self) -> None:
        self.create_event(party_window=30)
        old_run, _ = self.store.join_party("guild-1", "user-1", "Pirate", self.now + 1)
        new_run, started = self.store.join_party(
            "guild-1", "user-2", "Pirate", self.now + 32
        )
        self.assertFalse(started)
        self.assertNotEqual(old_run["id"], new_run["id"])
        resolved = self.store.resolve_party_recruitment(self.now + 33)
        self.assertEqual("cancelled", resolved[0]["status"])

    def test_party_reward_is_split_across_all_members(self) -> None:
        self.create_event(party_window=30)
        first, _ = self.store.join_party("guild-1", "user-1", "One", self.now + 1)
        run, _ = self.store.join_party("guild-1", "user-2", "Two", self.now + 2)
        started = self.store.resolve_party_recruitment(self.now + 32)
        self.assertEqual("started", started[0]["status"])
        self.store.create_action(
            interaction_id="party-kill",
            user_id="user-1",
            action_type="attack",
            cost=100,
            damage=400,
            now=self.now + 33,
        )
        self.store.mark_action_charged("party-kill", 900)
        self.store.apply_action("party-kill")
        rewards = self.store.get_pending_rewards()
        self.assertEqual(2, len(rewards))
        self.assertEqual({300}, {reward["amount"] for reward in rewards})
        self.assertEqual(first["id"], run["id"])

    def test_defeated_player_must_heal_before_attacking_again(self) -> None:
        self.create_event()
        self.store.create_solo_run("guild-1", "user-1", "Pirate", self.now + 1)
        self.store.create_action(
            interaction_id="knockout",
            user_id="user-1",
            action_type="attack",
            cost=100,
            damage=1,
            counter_damage=100,
            now=self.now + 2,
        )
        self.store.mark_action_charged("knockout", 900)
        self.store.apply_action("knockout")
        with self.assertRaises(PlayerDown):
            self.store.create_action(
                interaction_id="blocked",
                user_id="user-1",
                action_type="attack",
                cost=100,
                damage=1,
                now=self.now + 3,
            )
        self.store.create_action(
            interaction_id="heal",
            user_id="user-1",
            action_type="heal",
            cost=250,
            heal_amount=30,
            now=self.now + 4,
        )
        self.store.mark_action_charged("heal", 650)
        result = self.store.apply_action("heal")
        self.assertEqual(30, result["player_hp"])


if __name__ == "__main__":
    unittest.main()
