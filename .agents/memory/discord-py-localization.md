---
name: discord.py command localization
description: discord.py 2.x application-command localization and permission decorators.
---

For Japanese slash-command names and option labels, use `locale_str` values and install a `Translator` on the `CommandTree` before syncing. `locale_str` extras alone do not appear in Discord's synced command payload. Keep runtime permission checks in addition to default permission hints.

**Why:** During implementation, localized command payloads were missing until the translator was wired into the command tree; decorator kwargs also differed from the command decorator API.

**How to apply:** When adding or changing localized slash commands, verify the translated sync payload in a test and confirm administrator-only commands have runtime permission checks.
