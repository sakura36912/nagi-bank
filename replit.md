# Discord武器選択Bot

「本船員」ロールのメンバーが鍛冶屋で武器を1つだけ選び、武器とレベルをサーバーごとに保存するDiscord Botです。

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm --filter @workspace/scripts run discord-bot` — run the Discord bot
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- Required secret: `DISCORD_BOT_TOKEN`
- Optional env: `CREW_ROLE_NAME` — role name allowed to select a weapon (defaults to `本船員`)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

_Populate as you build — non-obvious choices a reader couldn't infer from the code (3-5 bullets)._

## Product

- `/weapon` (`/武器選択`) — choose one of six weapons, only once and only with the required role.
- `/weapon-status` (`/武器確認`) — view the owned weapon, level, and its unique skill.
- Weapon ownership is stored in PostgreSQL with a per-server, per-member uniqueness constraint.
- Nagi Bot wallet/API proposal: `docs/nagi-wallet-api.md`. Nagi runs in a separate Replit, so its SQLite file is not directly shared; currency debits and weapon levels must be updated by Nagi's own authenticated API in one SQLite transaction.
- The Discord application must be invited with the `bot` and `applications.commands` scopes. Global slash commands can take time to appear after first registration.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
