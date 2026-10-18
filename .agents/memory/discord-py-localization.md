---
name: discord.py command localization
description: discord.py 2.x application-command localization and permission decorators.
---

For Japanese slash-command names and option labels, use `locale_str` values and install a `Translator` on the `CommandTree` before syncing. `locale_str` extras alone do not appear in Discord's synced command payload. Keep runtime permission checks in addition to default permission hints.

Discord also validates localized option names at sync time. Avoid uppercase Latin, spaces, and punctuation such as full-width parentheses in Japanese option labels; simple Japanese text avoids HTTP 400 command-validation failures even when local payload generation succeeds.

**Why:** Local payload tests cannot catch every Discord-side constraint: sync rejected otherwise valid commands when Japanese option labels contained uppercase Latin and parentheses.

**How to apply:** When adding or changing localized slash commands, verify the translated sync payload, use simple safe option labels, confirm administrator-only commands have runtime permission checks, and check the live sync logs.
