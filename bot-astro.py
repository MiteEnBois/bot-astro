import os
import gspread
import sqlite3
import re
import yaml
from datetime import date
import time
from oauth2client.service_account import ServiceAccountCredentials
import discord
import io
from discord.ext import commands
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
from verbecc import Conjugator
from verbecc.exceptions import ConjugatorError
from random import shuffle, randint, seed
import numpy as np

# python -m pip -r install requirements.txt


# ----------------------------- SETUP VARIABLES GLOBALES ET BOT
print("start loading")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='##')

# code pour acceder à l'api
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

# load la base de donnée
conn = sqlite3.connect('astro.db')
c = conn.cursor()


# ----------------------------- FONCTIONS UTILITAIRES


@bot.command(name='ping', help='Pong!')
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command(name='pong', help='Ping!')
async def ping(ctx):
    await ctx.send("Ping!")

# ----------------------------- COMMANDES


def select(query):
    taille = []
    for row in c.execute(query):
        if taille == []:
            for x in range(len(row)):
                taille.append(0)
        i = 0
        for col in row:
            if len(str(col)) > taille[i]:
                taille[i] = len(str(col))
            i += 1
    txt = ""
    for row in c.execute(query):
        i = 0
        for col in row:
            txt += f"{col} "+" "*(taille[i]-len(str(col)))
            i += 1
        txt += "\n"
    return txt


def update_db():
    anime = []
    i = 0
    try:
        for row in c.execute('SELECT distinct origine FROM personnages'):
            anime.append(row[0])
        for x in c.execute('SELECT max(id) FROM personnages'):
            i = x[0]
    except sqlite3.OperationalError:
        c.execute('''CREATE TABLE personnages
                    (id, nom text, origine text,jour integer, mois integer, annee integer, signe text)''')

    sheets = client.open("Tableau Date de Naissance").worksheets()
    db = []
    nb_anime = 0
    nb_perso = 0
    for sh in sheets:
        delta = time.time()
        title = sh.title
        if title not in anime and title not in ["Front", "Template"]:
            nb_anime += 1
            for x in sh.get_all_values():
                if x[0] == "Personnage" or x[0] == "" or x[1] == "" or x[1] == "???":
                    continue
                date = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", x[1])
                if date is None:
                    continue
                jour = date.group(1)
                mois = date.group(2)
                annee = date.group(4)
                if annee is None:
                    annee = 2019
                row = (i, x[0], title, jour, mois, annee, x[2])
                db.append(row)
                i += 1
                nb_perso += 1
            print(f"{title} : {time.time()-delta}")
            while time.time()-delta <= 1.05:
                time.sleep(.01)

    c.executemany('INSERT INTO personnages VALUES (?,?,?,?,?,?,?)', db)

    conn.commit()
    return [nb_anime, nb_perso]


update_db()

signetab = {"belier": [80, 110], "taureau": [111, 140], "gémeaux": [141, 172], "cancer": [173, 203], "lion": [204, 234], "vierge": [235, 265], "balance": [266, 295], "scorpion": [296, 326], "sagittaire": [327, 355], "capricorne": [0, 0], "verseau": [21, 50], "poissons": [51, 79]}
signecolor = {"belier": "lightcoral", "taureau": "greenyellow", "gémeaux": "palegoldenrod", "cancer": "lightblue", "lion": "indianred", "vierge": "lightgreen", "balance": "khaki", "scorpion": "cyan", "sagittaire": "red", "capricorne": "forestgreen", "verseau": "goldenrod", "poissons": "royalblue"}


def trouve_signe(jour):
    if jour >= 356 or jour <= 20:
        return "capricorne"
    for s in signetab:
        if s == "capricorne":
            if jour <= signetab[s][0] or jour >= signetab[s][1]:
                return s
        else:
            if jour >= signetab[s][0] and jour <= signetab[s][1]:
                return s
    return ""


def str_to_day(signe):
    search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", signe)
    if search is None:
        return -1
    day = int(search.group(1))
    month = int(search.group(2))
    if day == 29 and month == 2:
        day = 28
    return int(date(2019, month, day).timetuple().tm_yday)


@bot.command(name='update', help='Ping!')
async def update(ctx):
    await ctx.send("Update lancée")
    tab = update_db()
    await ctx.send(f"Update terminée:\nAnimes rajoutés : {tab[0]}\nPersos rajoutés : {tab[1]}")


@bot.command(name='list', help='##liste (anime). Liste les animes cherchables.\nSi un anime est fourni, affiche si il est cherchable')
async def list(ctx, *arr):
    origine = ' '.join(arr)
    if origine != "":
        tab = []
        reussite = []
        for row in c.execute(f'SELECT distinct origine FROM personnages'):
            if origine.lower() in row[0].lower():
                reussite.append(row[0])
        if reussite != []:
            txt = "Anime trouvé : "
            for x in reussite:
                txt += x+", "
            await ctx.send(f"{txt[:-2]}")
        else:

            await ctx.send(f"Pas trouvé {origine} :/\nAnime qu'on a cherché mais où yavais pas de date : Berserk, Btooom, Darwin's Game, Dr Stone, Erased, FMA, Gurenn Lagan, Magi, SNK, DBZ")
    else:
        txt = "Anime cherchable: "
        for row in c.execute('SELECT distinct origine FROM personnages'):
            txt += row[0]+", "
        await ctx.send(f"{txt[:-2]}")


@bot.command(name='astro', help='##astro signe anime. Affiche les perso du meme signe dans un anime.\nLe signe peut etre le signe directement ou une date de naissance')
async def astro(ctx, signe, *arr,):
    origine = ' '.join(arr)
    if origine == "" and signe not in signetab:
        search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", signe)
        if search is None:
            await ctx.send(f"Date pas reconnue")
            return
        day = int(search.group(1))
        month = int(search.group(2))
        txt = select(f'SELECT origine, nom, jour || "/" || mois, signe FROM personnages where jour = {day} and mois = {month} order by origine')
        if txt != "":
            await ctx.send(f"```{txt}```")

    elif signe not in signetab:
        search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", signe)
        if search is None:
            await ctx.send(f"Date pas reconnue")
            return
        day = int(search.group(1))
        month = int(search.group(2))
        if day == 29 and month == 2:
            day = 28

        dd = int(date(2019, month, day).timetuple().tm_yday)
        print(f"dd {dd}; day {day}; month {month}")
        signe = trouve_signe(dd)

    txt = select(f'SELECT origine, nom, jour || "/" || mois, signe FROM personnages where lower(signe)="{signe.lower()}" and lower(origine)="{origine.lower()}" order by mois, jour')
    if txt != "":
        await ctx.send(f"```{txt}```")


@bot.command(name='graph', help='Ping!')
async def graph(ctx, *arr):
    origine = ' '.join(arr)
    data = []
    labels = []
    colors = []
    title = "Total"
    query = "SELECT signe, count(nom) FROM personnages GROUP BY signe"
    if origine != "":
        query = query.replace("personnages", f'personnages WHERE lower(origine) = "{origine.lower()}"')
        title = origine
    temp_dict = {}
    for row in c.execute(query):
        temp_dict[row[0].lower()] = row[1]
    if temp_dict == {}:
        await ctx.send(f"Anime pas reconnu, vérifiez l'ortographe avec ##list")
        return
    for x in signetab:
        if x not in temp_dict:
            continue
        labels.append(f"{x} : {temp_dict[x]}")
        data.append(temp_dict[x])
        colors.append(signecolor[x])

    fig, ax1 = plt.subplots()
    ax1.pie(data, labels=labels, autopct='%1.1f%%', counterclock=False, startangle=90, colors=colors)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title(title)
    # plt.show()
    fig = io.BytesIO()

    plt.savefig(fig, bbox_inches='tight', format="png")
    fig.seek(0)
    await ctx.send(file=discord.File(fig, title+'.png'))

# ----------------------------- FIN SETUP

# S'execute quand le bot est prêt; Affiche la liste des serveurs sur lesquelles le bot est actuellement


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f'{bot.user} is connected to the following guild:')
    for guild in bot.guilds:
        print(f'-{guild.name}')
    print(f'{bot.user} has started')


# lance le bot
bot.run(TOKEN)
