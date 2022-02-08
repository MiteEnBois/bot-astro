import os
import gspread
import sqlite3
import re
import time
from oauth2client.service_account import ServiceAccountCredentials
import discord
import io
import asyncio
from discord.ext import commands, tasks
from discord import Intents
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date


# pip freeze > requirements.txt
# virtualenv venv
# source venv/bin/activate
# pip install -r requirements.txt


# ----------------------------- SETUP VARIABLES GLOBALES ET BOT
print("start loading")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='##', intents=intents)


# load la base de donnée
conn = sqlite3.connect(os.getcwd() + '\\astro.db')
c = conn.cursor()


def next_bday(server_id):
    today = date.today()
    # today = date(2021, 1, 2)
    nexts = []
    for row in c.execute(f"SELECT u.id, u.jour, u.mois from appartenances_serveurs a, serveurs s, utilisateurs u where u.id = a.id_util and a.id_serveur = {server_id} and a.id_serveur = s.id and u.mois >= {today.month} order by u.mois, u.jour"):
        try:
            bd = date(today.year, row[2], row[1])
        except ValueError:
            continue
        if len(nexts) > 0 and nexts[len(nexts) - 1][1] != (bd - today).days:
            break
        if bd >= today:
            nexts.append([bd, (bd - today).days, row[0]])
    if len(nexts) == 0:
        for row in c.execute(f"SELECT u.id, u.jour, u.mois from appartenances_serveurs a, serveurs s, utilisateurs u where u.id = a.id_util and a.id_serveur = {server_id} and a.id_serveur = s.id order by u.mois, u.jour"):
            try:
                bd = date(today.year + 1, row[2], row[1])
            except ValueError:
                continue
            if bd >= today:
                nexts.append([bd, (bd - today).days, row[0]])
    if len(nexts) == 0:
        return None
    else:
        return nexts


async def checkBD():
    for guild in bot.guilds:
        txt = "On souhaite un joyeux anniversaire à "
        nexts = next_bday(guild.id)
        if nexts is None:
            continue
        channel = None
        for canal in c.execute(f'SELECT canal FROM serveurs where id = {guild.id}'):
            channel = canal[0]
            break
        if channel is None:
            print("Pas de canal trouvé")
            break
        for row in nexts:
            if row is not None and row[1] == 0:
                id = row[2]
                member = guild.get_member(id)
                if member is None:
                    memberMention = id
                else:
                    memberMention = member.mention
                txt += f"{memberMention}, "
            print(row)
        if txt != "On souhaite un joyeux anniversaire à ":
            await guild.get_channel(channel).send(txt[:-2] + "!!")


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(f"{bot.command_prefix}help"))
    print(f'{bot.user} is connected to the following guild:')
    for guild in bot.guilds:
        print(f'-{guild.name}')
    print(f'{bot.user} has started')
    await checkBD()
    await bot.logout()
    # exit()


# lance le bot
bot.run(TOKEN)
