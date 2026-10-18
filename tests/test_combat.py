import unittest

from weapon_bot.bosses.combat import calculate_boss_counter_damage, calculate_damage


class FixedRandom:
    def __init__(self, roll: float, critical_roll: float) -> None:
        self.roll = roll
        self.critical_roll = critical_roll

    def uniform(self, _minimum: float, _maximum: float) -> float:
        return self.roll

    def random(self) -> float:
        return self.critical_roll


class DamageCalculationTests(unittest.TestCase):
    def test_base_damage_uses_weapon_and_boss_defense(self) -> None:
        result = calculate_damage(
            "greatsword",
            1,
            [],
            boss_defense=2,
            rng=FixedRandom(1.0, 0.9),
        )
        self.assertEqual(8, result.damage)
        self.assertFalse(result.critical)

    def test_level_role_random_and_critical_modifiers_apply(self) -> None:
        result = calculate_damage(
            "greatsword",
            2,
            ["船長"],
            boss_defense=2,
            rng=FixedRandom(1.0, 0.0),
        )
        self.assertEqual(17, result.damage)
        self.assertTrue(result.critical)

    def test_unknown_weapon_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_damage("unknown", 1, [], boss_defense=0, rng=FixedRandom(1.0, 1.0))

    def test_boss_counterattack_uses_weapon_defense(self) -> None:
        damage = calculate_boss_counter_damage(
            boss_attack=30,
            weapon_defense=3,
            weapon_level=1,
            rng=FixedRandom(1.0, 1.0),
        )
        self.assertEqual(27, damage)


if __name__ == "__main__":
    unittest.main()
