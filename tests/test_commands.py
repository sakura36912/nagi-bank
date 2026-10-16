import unittest

import discord
from discord import app_commands
from discord.ext import commands

from weapon_bot.cogs.admin import AdminCog
from weapon_bot.cogs.forge import ForgeCog
from weapon_bot.database import WeaponMirror
from weapon_bot.localization import JapaneseTranslator
from weapon_bot.nagi_api import NagiApi


class CommandRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_japanese_commands_and_admin_permissions(self) -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        mirror = WeaponMirror(":memory:")
        await bot.add_cog(ForgeCog(bot, NagiApi(), mirror))
        await bot.add_cog(AdminCog(bot, NagiApi(), mirror))
        translator = JapaneseTranslator()
        await bot.tree.set_translator(translator)

        payloads = {}
        for command in bot.tree.get_commands():
            payload = await command.get_translated_payload(bot.tree, translator)
            payloads[payload["name"]] = payload
        self.assertEqual(
            {"武器選択", "武器", "強化", "武器変更", "武器リセット", "武器データ編集"},
            {payload["name_localizations"]["ja"] for payload in payloads.values()},
        )

        admin_bit = discord.Permissions(administrator=True).value
        for name in ("weapon_admin_change", "weapon_admin_reset", "weapon_admin_edit"):
            self.assertEqual(admin_bit, payloads[name]["default_member_permissions"])

        await bot.close()


if __name__ == "__main__":
    unittest.main()
