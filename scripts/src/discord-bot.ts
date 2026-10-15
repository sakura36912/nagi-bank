import {
  APIInteractionGuildMember,
  ChatInputCommandInteraction,
  Client,
  Events,
  GatewayIntentBits,
  GuildMember,
  MessageFlags,
  SlashCommandBuilder,
} from "discord.js";
import { Pool } from "pg";
import pino from "pino";
import { findWeapon, WEAPONS } from "./discord-weapons.js";

const logger = pino({ level: process.env.LOG_LEVEL ?? "info" });
const token = process.env.DISCORD_BOT_TOKEN;
const databaseUrl = process.env.DATABASE_URL;
const requiredRoleName = process.env.CREW_ROLE_NAME?.trim() || "本船員";

if (!token) {
  throw new Error("DISCORD_BOT_TOKEN が設定されていません。");
}
if (!databaseUrl) {
  throw new Error("DATABASE_URL が設定されていません。");
}

const pool = new Pool({ connectionString: databaseUrl });
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

const commands = [
  new SlashCommandBuilder()
    .setName("weapon")
    .setNameLocalizations({ ja: "武器選択" })
    .setDescription("鍛冶屋で武器を選択します")
    .addStringOption((option) =>
      option
        .setName("type")
        .setNameLocalizations({ ja: "種類" })
        .setDescription("選ぶ武器")
        .setRequired(true)
        .addChoices(...WEAPONS.map(({ id, name }) => ({ name, value: id }))),
    ),
  new SlashCommandBuilder()
    .setName("weapon-status")
    .setNameLocalizations({ ja: "武器確認" })
    .setDescription("所持している武器とレベルを確認します"),
].map((command) => command.toJSON());

async function initializeDatabase(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS discord_weapon_ownership (
      guild_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      weapon_id TEXT NOT NULL,
      level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
      acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (guild_id, user_id)
    )
  `);
}

function memberRoleIds(
  member: GuildMember | APIInteractionGuildMember | null,
): string[] {
  if (!member) return [];
  if (Array.isArray(member.roles)) return member.roles;
  return member.roles.cache.map((role) => role.id);
}

async function reply(
  interaction: ChatInputCommandInteraction,
  content: string,
): Promise<void> {
  await interaction.editReply({ content });
}

client.on(Events.InteractionCreate, async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (!interaction.guild) {
    await interaction.reply({
      content: "❌ このコマンドはサーバー内で使用してください。",
      flags: MessageFlags.Ephemeral,
    });
    return;
  }
  if (interaction.commandName !== "weapon" && interaction.commandName !== "weapon-status") {
    return;
  }

  try {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    if (interaction.commandName === "weapon-status") {
      const result = await pool.query<{ weapon_id: string; level: number }>(
        `SELECT weapon_id, level
         FROM discord_weapon_ownership
         WHERE guild_id = $1 AND user_id = $2`,
        [interaction.guild.id, interaction.user.id],
      );
      const owned = result.rows[0];
      if (!owned) {
        await reply(interaction, "まだ武器を所持していません。鍛冶屋で武器を選択してください。");
        return;
      }

      const weapon = findWeapon(owned.weapon_id);
      if (!weapon) {
        logger.error({ weaponId: owned.weapon_id }, "登録されていない武器データです");
        await reply(interaction, "武器データを読み込めませんでした。管理者にお問い合わせください。");
        return;
      }
      await reply(
        interaction,
        `⚔️ 所持武器\n武器：${weapon.name}\nLv：${owned.level}\n固有スキル：${weapon.skill} — ${weapon.skillDescription}`,
      );
      return;
    }

    const roleIds = memberRoleIds(interaction.member);
    const roles = await interaction.guild.roles.fetch();
    const crewRole = roles.find((role) => role.name === requiredRoleName);
    if (!crewRole || !roleIds.includes(crewRole.id)) {
      await reply(
        interaction,
        "❌ あなたはまだ鍛冶屋を利用できません。\n「本船員」ロールを取得すると武器を選択できます。",
      );
      return;
    }

    const weaponId = interaction.options.getString("type", true);
    const weapon = findWeapon(weaponId);
    if (!weapon) {
      await reply(interaction, "❌ 武器の選択内容を確認できませんでした。もう一度お試しください。");
      return;
    }

    const result = await pool.query<{ weapon_id: string }>(
      `INSERT INTO discord_weapon_ownership (guild_id, user_id, weapon_id, level)
       VALUES ($1, $2, $3, 1)
       ON CONFLICT (guild_id, user_id) DO NOTHING
       RETURNING weapon_id`,
      [interaction.guild.id, interaction.user.id, weapon.id],
    );
    if (result.rowCount === 0) {
      await reply(interaction, "❌ あなたは既に武器を所持しています。\n武器は1人につき1つまでです。");
      return;
    }

    await reply(
      interaction,
      `⚔️ 武器を選択しました！\n武器：${weapon.name}\nLv：1\nボス戦・PvPで使用できるようになりました。`,
    );
  } catch (error) {
    logger.error({ error, commandName: interaction.commandName }, "Discordコマンド処理に失敗しました");
    const message = "処理中にエラーが発生しました。時間をおいて再度お試しください。";
    if (interaction.deferred) {
      await interaction.editReply({ content: message }).catch(() => {});
    } else {
      await interaction
        .reply({ content: message, flags: MessageFlags.Ephemeral })
        .catch(() => {});
    }
  }
});

client.once(Events.ClientReady, async (readyClient) => {
  try {
    await readyClient.application.commands.set(commands);
    logger.info(
      { bot: readyClient.user.tag, commandCount: commands.length, requiredRoleName },
      "Discord武器Botが起動しました",
    );
  } catch (error) {
    logger.error({ error }, "スラッシュコマンドの登録に失敗しました");
    process.exitCode = 1;
    readyClient.destroy();
    await pool.end();
  }
});

async function shutdown(signal: string): Promise<void> {
  logger.info({ signal }, "Discord武器Botを終了します");
  client.destroy();
  await pool.end();
}

process.once("SIGINT", () => void shutdown("SIGINT"));
process.once("SIGTERM", () => void shutdown("SIGTERM"));

try {
  await initializeDatabase();
  await client.login(token);
} catch (error) {
  logger.fatal({ error }, "Discord武器Botの起動に失敗しました");
  await pool.end();
  process.exitCode = 1;
}
