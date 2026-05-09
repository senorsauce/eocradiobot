import os
import re
import hashlib
import asyncio
import discord
from discord import app_commands
from discord.ext import commands


token = os.getenv("DISCORD_TOKEN")
setupChannelId = int(os.getenv("SETUP_CHANNEL_ID"))
radioCategoryId = int(os.getenv("RADIO_CATEGORY_ID"))

intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


def cleanFrequency(frequency: str) -> str | None:
    frequency = frequency.strip().lower()

    if not re.fullmatch(r"[a-z0-9.-]{1,20}", frequency):
        return None

    return frequency


def getRadioChannelName(frequency: str) -> str:
    hashedFrequency = hashlib.sha256(frequency.encode()).hexdigest()

    partOne = hashedFrequency[0:4]
    partTwo = hashedFrequency[4:8]
    partThree = hashedFrequency[8:12]

    return f"cipher-{partOne}-{partTwo}-{partThree}"


async def findRadioChannel(radioCategory: discord.CategoryChannel, frequency: str):
    channelName = getRadioChannelName(frequency)

    for channel in radioCategory.voice_channels:
        if channel.name == channelName:
            return channel

    return None


def getLockedOverwrites(guild: discord.Guild, member: discord.Member):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
            connect=False
        ),
        member: discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True
        )
    }

    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            manage_channels=True,
            move_members=True
        )

    return overwrites


async def allowMemberIntoChannel(channel: discord.VoiceChannel, member: discord.Member):
    await channel.set_permissions(
        member,
        view_channel=True,
        connect=True,
        speak=True
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash command(s) to {guild.name} ({guild.id})")
    except Exception as error:
        print(f"Failed to sync slash commands: {type(error).__name__}: {error}")

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None:
        return

    channel = before.channel

    if not isinstance(channel, discord.VoiceChannel):
        return

    if channel.category_id != radioCategoryId:
        return

    if not channel.name.startswith("cipher-"):
        return

    if len(channel.members) > 0:
        return

    await asyncio.sleep(10)

    # Re-check after 10 seconds in case someone joined again.
    if len(channel.members) > 0:
        return

    try:
        await channel.delete(reason="Radio frequency empty for 10 seconds")
        print(f"Deleted empty radio channel: {channel.name}")
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print(f"Missing permissions to delete channel: {channel.name}")
    except Exception as error:
        print(f"Failed to delete channel {channel.name}: {type(error).__name__}: {error}")


bot.run(token)
