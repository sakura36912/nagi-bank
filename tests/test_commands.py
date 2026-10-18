import unittest

import discord
from discord import app_commands
from discord.ext import commands

from weapon_bot.cogs.admin import AdminCog
from weapon_bot.cogs.boss import BossCog
from weapon_bot.cogs.forge import ForgeCog
from weapon_bot.bosses.store import BossStore
from weapon_bot.database import WeaponMirror
from weapon_bot.localization import JapaneseTranslator
from weapon_bot.nagi_api import NagiApi


class CommandRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_japanese_commands_and_admin_permissions(self) -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        mirror = WeaponMirror(":memory:")
        api = NagiApi()
        await bot.add_cog(ForgeCog(bot, api, mirror))
        await bot.add_cog(AdminCog(bot, api, mirror))
        await bot.add_cog(BossCog(bot, api, mirror, BossStore(":memory:")))
        translator = JapaneseTranslator()
        await bot.tree.set_translator(translator)

        payloads = {}
        for command in bot.tree.get_commands():
            payload = await command.get_translated_payload(bot.tree, translator)
            payloads[payload["name"]] = payload
        self.assertEqual(
            {
                "武器選択", "武器", "強化", "武器変更", "武器リセット", "武器データ編集",
                "ボス開催", "ボス終了", "ボス情報", "参加", "攻撃", "回復",
            },
            {payload["name_localizations"]["ja"] for payload in payloads.values()},
        )
        boss_start_options = {
            option["name"]: option["name_localizations"]["ja"]
            for option in payloads["boss_start"]["options"]
        }
        self.assertEqual(
            {
                "boss": "ボス",
                "solo_hp": "ソロ体力",
                "party_hp": "パーティ体力",
                "duration_minutes": "制限時間分",
                "party_window_minutes": "受付時間分",
                "special_event": "特殊イベント",
            },
            boss_start_options,
        )
        self.assertTrue(
            all(not any(character in name for character in "()（） ") for name in boss_start_options.values())
        )

        admin_bit = discord.Permissions(administrator=True).value
        for name in (
            "weapon_admin_change",
            "weapon_admin_reset",
            "weapon_admin_edit",
            "boss_start",
            "boss_end",
        ):
            self.assertEqual(admin_bit, payloads[name]["default_member_permissions"])

        await bot.close()


if __name__ == "__main__":
    unittest.main()
