import unittest

from weapon_bot.config import WEAPONS, success_rate, upgrade_cost


class UpgradeRulesTests(unittest.TestCase):
    def test_six_supported_weapons(self) -> None:
        self.assertEqual(
            {"大剣", "片手剣", "槍", "弓", "双剣", "杖"},
            {weapon.name for weapon in WEAPONS.values()},
        )

    def test_configured_upgrade_cost_examples(self) -> None:
        self.assertEqual(
            [1_000, 2_500, 5_000, 8_000, 12_000, 16_000, 20_000, 24_000],
            [upgrade_cost(level) for level in range(1, 9)],
        )

    def test_success_rate_examples_and_floor(self) -> None:
        self.assertEqual(
            [100, 95, 90, 85, 80, 75, 70, 65, 60, 55],
            [success_rate(level) for level in range(1, 11)],
        )
        self.assertEqual(30, success_rate(15))
        self.assertEqual(30, success_rate(100))


if __name__ == "__main__":
    unittest.main()
