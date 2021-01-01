import os
import gspread
import sqlite3
import re
import yaml
from datetime import date
import time
from oauth2client.service_account import ServiceAccountCredentials
from discord.ext import commands
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
from verbecc import Conjugator
from verbecc.exceptions import ConjugatorError
from random import shuffle, randint, seed

# python -m pip -r install requirements.txt


# ----------------------------- SETUP VARIABLES GLOBALES ET BOT
print("start loading")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='##')

insultes = []
with open("insultes.yml", mode="r", encoding='utf-8') as f:
    insultes = yaml.load(f, Loader=yaml.FullLoader)
    f.close()

cg = Conjugator(lang='fr')

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

    for sh in sheets:
        delta = time.time()
        title = sh.title
        if title not in anime and title not in ["Front", "Template"]:
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
            print(f"{title} : {time.time()-delta}")
            while time.time()-delta <= 1.05:
                time.sleep(.01)

    c.executemany('INSERT INTO personnages VALUES (?,?,?,?,?,?,?)', db)

    conn.commit()


update_db()

signetab = {"belier": [80, 110], "taureau": [111, 140], "gémeaux": [141, 172], "cancer": [173, 203], "lion": [204, 234], "vierge": [235, 265], "balance": [266, 295], "scorpion": [296, 326], "sagittaire": [327, 355], "verseau": [21, 50], "poissons": [51, 79]}


def trouve_signe(jour):
    for s in signetab:
        if s == "capricorne":
            if jour <= signetab[s][0] or jour >= signetab[s][1]:
                return s
        else:
            if jour >= signetab[s][0] and jour <= signetab[s][1]:
                return s
    if jour >= 356 or jour <= 20:
        return "capricorne"


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


@bot.command(name='conjugue', help='Conjuge un verbe')
async def conjugue(ctx,
                   verbe,
                   mode="indicatif",
                   temps="présent",
                   pronom=""):
    try:
        conjugaison = cg.conjugate(verbe)
    except ConjugatorError:
        await ctx.send(f"Nique ta mere c'est pas un verbe")
        return
    if pronom == "":
        pronom = -1
    if mode not in conjugaison["moods"]:
        txt = ""
        for x in conjugaison['moods']:
            txt += x+", "
        await ctx.send(f"Temps utilisable : {txt[:-2]}")
        return
    if temps not in conjugaison["moods"][mode]:
        txt = ""
        for x in conjugaison['moods'][mode]:
            txt += x+", "
        await ctx.send(f"Temps utilisable avec {mode} : {txt[:-2]}")
        return
    try:
        pronom = int(pronom)
    except ValueError:
        i = 0
        for x in conjugaison["moods"][mode][temps]:
            if pronom in x:
                pronom = i
                break
            i += 1
        if pronom != i:
            await ctx.send(f"{pronom} n'a pas été trouvé pour {mode} et {temps}")
    txt = ""
    if pronom == -1:
        for x in conjugaison["moods"][mode][temps]:
            txt += x + ", "
        txt = txt[:-2]
    else:
        txt = conjugaison["moods"][mode][temps][pronom]
    await ctx.send(txt)


def insulte_gen():
    starter = ["espèce de ", "sale ", "fils de ", "connard de ", "gros "]
    start = starter[randint(0, len(starter) - 1)]
    insulte = insultes[randint(0, len(insultes) - 1)]
    voy = ["a", "e", "i", "o", "u", "y", "é", "è"]
    if (start[-4:] == " de "
            and insulte[0].lower() in voy) or (insulte[0].lower() == "h"
                                               and insulte[1].lower() in voy):
        start = start[:-4] + " d'"
    link = "https://fr.wiktionary.org/wiki/" + insulte.replace(" ", "_")
    return f"{start}**{insulte}**\n||{link}||"


@bot.command(name='insulte', help='')
async def insulte(ctx, *arr):
    l = " ".join(arr)
    if "@everyone" in str(ctx.message.content):
        await ctx.send(f"{ctx.author.mention}, parce que tu a tenté, {insulte_gen()}")
        return
    if l != "":
        l += ', '
    await ctx.send(f"{l}{insulte_gen()}")


# ----------------------------- FIN SETUP

# S'execute quand le bot est prêt; Affiche la liste des serveurs sur lesquelles le bot est actuellement


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        vrai_insulte = ["Nique tes morts en fait", "C'est pas ta mère qui est une célèbre pute ?", "Va te faire enculer pour voir ?", "you can't tell me what to do!", "T'aimes ça quand je te ping fils de pute ?"]
        await message.channel.send(f"{message.author.mention}, {vrai_insulte[randint(0,len(vrai_insulte)-1)]}")
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
