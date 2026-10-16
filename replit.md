# Discord鍛冶屋Bot

Python版Discord BOTが「本船員」ロールのメンバーに武器選択・確認・強化機能を提供します。既存のTypeScript版は比較・切り戻し用に残し、同じDiscord application tokenで同時起動しません。

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm --filter @workspace/scripts run discord-bot` — run the Python discord.py bot
- `pnpm --filter @workspace/scripts run discord-bot-node` — run the retained TypeScript version (do not run alongside Python)
- `python -m unittest discover -s tests` — run Python unit tests
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secret: `DISCORD_BOT_TOKEN`
- Required env: `NAGI_API_BASE_URL` — Nagi Bot HTTPS API base URL
- Required secret: `NAGI_API_TOKEN` — service-to-service bearer token for Nagi API
- Optional env: `CREW_ROLE_NAME` — role name allowed to select a weapon (defaults to `本船員`)
- Optional env: `WEAPON_DB_PATH` — local SQLite mirror path (defaults to `data/pirate.db`)

## Stack

- Python 3.13, discord.py 2.x
- Local SQLite mirror plus authenticated HTTPS calls to the separate Nagi Bot
- Existing TypeScript / PostgreSQL implementation remains available as an alternate version

## Where things live

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

- Nagi Bot runs in another Replit; local SQLite files are not shared. Nagi's authenticated HTTPS API is authoritative for both wallet and weapon changes.
- The Python BOT keeps a durable SQLite mirror at `data/pirate.db`, but never uses that mirror to authorize a charge or overwrite newer API state.
- Nagi must deduct currency and update weapon level/stats in the same transaction. The BOT mirrors only successful API responses.
- The account key is Discord user ID, so one user owns one weapon globally, not one per guild.

## Product

- `/武器選択` — choose one of six weapons, only once and only with the required role.
- `/武器` — view public weapon info, skill, next upgrade price, and success rate; internal stats are hidden.
- `/強化` — attempt an upgrade; the Nagi API charges on both success and failure and rolls back no stats on failure.
- Administrator commands: `/武器変更`, `/武器リセット`, `/武器データ編集`.
- Nagi Bot API contract: `docs/nagi-wallet-api.md`.
- The Discord application must be invited with the `bot` and `applications.commands` scopes. Global slash commands can take time to appear after first registration.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
