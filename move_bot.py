import discord
from discord.ext import commands
from discord import app_commands

import os
bot.run(os.environ.get("DISCORD_TOKEN"))

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─────────────────────────────────────────────
# KONFIGURATION – hier anpassen
# ─────────────────────────────────────────────

# User-IDs der 20 zu verschiebenden User
USER_GROUPS = {
    "A": [
        176775112635318273, 212985137602887680, 1402209257461514273, 315200821983707136, 1079095662223818792,
        270171716507009025, 338716386241150977, 156458632240693250, 148813554240323584, 1101526494259445902,
    ],
    "B": [
        282943498746069003, 149606674590597120, 305164060843048960, 240590339063152651, 401911283768885248,
        378667374854799361, 186303461384650765, 244855999431835648, 171704840773304320, 330347281024811009,
    ],
}

CHANNELS = {
    "A": 1458531173046292571,  # Channel-ID für Team A
    "B": 1475976949678477424,  # Channel-ID für Team B
}

# Channel-ID, in den ALLE User verschoben werden (Sammel-Button)
MAIN_CHANNEL_ID = 1457420470868774937

# Rolle, die den Button verwenden darf (Name der Admin-Rolle)
ADMIN_ROLE_NAME = "Offizier"

# ─────────────────────────────────────────────

# Hilfsfunktion: Admin-Check
def is_admin(member: discord.Member) -> bool:
    return any(r.name == ADMIN_ROLE_NAME for r in member.roles)

# Hilfsfunktion: User verschieben und Ergebnis sammeln
async def move_users(guild, user_ids, target_channel):
    results, errors = [], []
    for user_id in user_ids:
        member = guild.get_member(user_id)
        if not member:
            errors.append(f"User {user_id} nicht gefunden.")
            continue
        if not member.voice or not member.voice.channel:
            errors.append(f"{member.display_name} ist in keinem Voice-Channel.")
            continue
        try:
            await member.move_to(target_channel)
            results.append(f"✅ {member.display_name} → {target_channel.name}")
        except discord.Forbidden:
            errors.append(f"❌ Kein Zugriff auf {member.display_name}.")
    return results, errors

# ─────────────────────────────────────────────

@bot.event
async def on_ready():
    # Persistent View beim Start registrieren, damit Buttons nach Neustart funktionieren
    bot.add_view(AdminMoveView())
    print(f"✅ Bot online als {bot.user}")
    await bot.tree.sync()

@bot.tree.command(name="move-panel", description="Erstellt das Admin-Move-Panel")
async def move_panel(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return

    view = AdminMoveView()
    await interaction.response.send_message(
        "🚀 **Teams verteilen** – verteilt Raider in 2 Channels"
        "🔁 **Alle zusammen** – Alle in den Raid-Channel",
        view=view
    )

# ─────────────────────────────────────────────

class AdminMoveView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Kein Timeout → Button bleibt dauerhaft aktiv

    # Button 1: Teams auf A/B/C/D verteilen
    @discord.ui.button(
        label="🚀 Teams verteilen",
        style=discord.ButtonStyle.danger,
        custom_id="btn_distribute"  # Feste ID → überlebt Bot-Neustart
    )
    async def distribute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        all_results, all_errors = [], []

        for group, user_ids in USER_GROUPS.items():
            target_channel = guild.get_channel(CHANNELS[group])
            if not target_channel:
                all_errors.append(f"Channel {group} nicht gefunden!")
                continue
            results, errors = await move_users(guild, user_ids, target_channel)
            all_results.extend(results)
            all_errors.extend(errors)

        summary = "**Ergebnis:**\n" + "\n".join(all_results)
        if all_errors:
            summary += "\n\n**Fehler:**\n" + "\n".join(all_errors)

        await interaction.followup.send(summary, ephemeral=True)

    # Button 2: Alle User in einen Channel sammeln
    @discord.ui.button(
        label="🔁 Alle zusammen",
        style=discord.ButtonStyle.primary,
        custom_id="btn_collect"  # Feste ID → überlebt Bot-Neustart
    )
    async def collect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = guild.get_channel(MAIN_CHANNEL_ID)

        if not target_channel:
            await interaction.followup.send("❌ Haupt-Channel nicht gefunden!", ephemeral=True)
            return

        # Alle User aus allen Gruppen zusammenführen
        all_user_ids = [uid for ids in USER_GROUPS.values() for uid in ids]
        results, errors = await move_users(guild, all_user_ids, target_channel)

        summary = f"**Alle in {target_channel.name}:**\n" + "\n".join(results)
        if errors:
            summary += "\n\n**Fehler:**\n" + "\n".join(errors)

        await interaction.followup.send(summary, ephemeral=True)
