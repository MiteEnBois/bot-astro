import os
import gspread
import sqlite3
import re
from datetime import date
import time
from oauth2client.service_account import ServiceAccountCredentials
import discord
import io
import asyncio
from discord.ext import commands
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

bot = commands.Bot(command_prefix='!', intents=intents)

# code pour acceder à l'api
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

# load la base de donnée
conn = sqlite3.connect('astro.db')
c = conn.cursor()

signetab = {"belier": [80, 110], "taureau": [111, 140], "gémeaux": [141, 172], "cancer": [173, 203], "lion": [204, 234], "vierge": [235, 265], "balance": [266, 295], "scorpion": [296, 326], "sagittaire": [327, 355], "capricorne": [-1, -1], "verseau": [21, 50], "poissons": [51, 79]}
signecolor = {"belier": "lightcoral", "taureau": "greenyellow", "gémeaux": "palegoldenrod", "cancer": "lightblue", "lion": "indianred", "vierge": "lightgreen", "balance": "khaki", "scorpion": "cyan", "sagittaire": "red", "capricorne": "forestgreen", "verseau": "goldenrod", "poissons": "royalblue"}


# personnages(
#     id integer PRIMARY KEY,
#     nom text,
#     origine text,
#     jour integer,
#     mois integer,
#     annee integer,
#     signe text)

# serveurs(
#     id integer PRIMARY KEY,
#     canal integer)

# utilisateurs(
#     id integer PRIMARY KEY,
#     jour integer,
#     mois integer)

# appartenances_serveurs(
#     id_serveur integer,
#     id_util,
#     PRIMARY KEY(id_serveur,id_util))

# ----------------------------- FONCTIONS UTILITAIRES


async def confirmation(ctx, message, confirmation):
    conf = await ctx.send(
        f"{message}\nEnvoyez {confirmation} pour confirmer, sinon ne répondez pas"
    )

    def check(m):
        return m.content == confirmation and m.channel == ctx.channel and m.author == ctx.author

    try:
        resp = await bot.wait_for("message", check=check, timeout=30)
        await conf.delete()
        await resp.delete()
        return True

    except asyncio.TimeoutError:
        await conf.edit(content="Timeout")
        await asyncio.sleep(10)
        await conf.delete()
        return False


def remove_user(utilisateur):
    c.execute(f"DELETE FROM appartenances_serveurs where id_util = {utilisateur.id} and id_serveur = {utilisateur.guild.id}")
    found = None
    for row in c.execute(f'SELECT count(id_serveur) FROM appartenances_serveurs where id_util = {utilisateur.id}'):
        found = row[0]
    if found is None or found == 0:
        c.execute(f"DELETE FROM utilisateurs where id = {utilisateur.id}")
    conn.commit()


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


def next_bday(server_id):
    today = date.today()
    # today = date(2021, 1, 2)
    nexts = []
    for row in c.execute(f"SELECT u.id, u.jour, u.mois from appartenances_serveurs a, serveurs s, utilisateurs u where u.id = a.id_util and a.id_serveur = {server_id} and a.id_serveur = s.id and u.mois >= {today.month} order by u.mois, u.jour"):
        try:
            bd = date(today.year, row[2], row[1])
        except ValueError:
            continue
        if len(nexts) > 0 and nexts[len(nexts)-1][1] != (bd-today).days:
            break
        if bd >= today:
            nexts.append([bd, (bd-today).days, row[0]])
    if len(nexts) == 0:
        for row in c.execute(f"SELECT u.id, u.jour, u.mois from appartenances_serveurs a, serveurs s, utilisateurs u where u.id = a.id_util and a.id_serveur = {server_id} and a.id_serveur = s.id order by u.mois, u.jour"):
            try:
                bd = date(today.year+1, row[2], row[1])
            except ValueError:
                continue
            if bd >= today:
                nexts.append([bd, (bd-today).days, row[0]])
    if len(nexts) == 0:
        return None
    else:
        return nexts


def update_db():
    # c.execute('DROP TABLE personnages')
    # c.execute('DROP TABLE serveurs')
    # c.execute('DROP TABLE utilisateurs')
    # c.execute('DROP TABLE appartenances_serveurs')
    i = 0
    anime = []
    try:
        for row in c.execute('SELECT distinct origine FROM personnages'):
            anime.append(row[0])
        for x in c.execute('SELECT max(id) FROM personnages'):
            i = x[0]+1
    except sqlite3.OperationalError:
        print("create personnages")
        c.execute('''CREATE TABLE personnages(id integer PRIMARY KEY, nom text, origine text,jour integer, mois integer, annee integer, signe text)''')

    serveurs = []
    try:
        for row in c.execute('SELECT count(id) FROM serveurs'):
            print(f"Serveurs : {row[0]}")
    except sqlite3.OperationalError:
        print("create serveurs")
        c.execute('''CREATE TABLE serveurs(id integer PRIMARY KEY, canal integer)''')

    for row in c.execute('SELECT id FROM serveurs'):
        serveurs.append(row[0])
    for guild in bot.guilds:
        if guild.id not in serveurs:
            c.execute(f'INSERT INTO serveurs VALUES ({guild.id},{guild.channels[0].id})')

    try:
        for row in c.execute('SELECT count(id) FROM utilisateurs'):
            print(f"Utilisateurs : {row[0]}")
    except sqlite3.OperationalError:
        print("create utilisateurs")
        c.execute('''CREATE TABLE utilisateurs(id integer PRIMARY KEY, jour integer, mois integer)''')

    try:
        for row in c.execute('SELECT count(id_util) FROM appartenances_serveurs'):
            print(f"Liens : {row[0]}")
    except sqlite3.OperationalError:
        print("create appartenance_serveur")
        c.execute('''CREATE TABLE appartenances_serveurs(id_serveur integer, id_util, PRIMARY KEY(id_serveur,id_util))''')

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
    print("fini")
    return [nb_anime, nb_perso]


def day_to_sign(day):
    if day >= 356 or day <= 20:
        return "capricorne"
    for s in signetab:
        if day >= signetab[s][0] and day <= signetab[s][1]:
            return s
    return -3


def str_to_day(string):
    search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", string)
    if search is None:
        return -1
    day = int(search.group(1))
    month = int(search.group(2))
    if day == 29 and month == 2:
        day = 28
    try:
        dd = int(date(2019, month, day).timetuple().tm_yday)
    except ValueError:
        return -2
    return dd


def find_sign(str):
    if str in signetab:
        return str
    day = str_to_day(str)
    if day < 0:
        return day
    return day_to_sign(day)


async def checkBD():
    for guild in bot.guilds:
        txt = "On souhaite un joyeux anniversaire à "
        nexts = next_bday(guild.id)
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
            await guild.get_channel(channel).send(txt[:-2]+"!!")


async def timer():
    await asyncio.sleep(60)

    now = datetime.now()

    current_time = now.strftime("%H:%M")
    # print("Current Time =", current_time)

    if(current_time == '07:00'):  # check if matches with the desired time
        await checkBD()
    await timer()

# ----------------------------- COMMANDES

help = """Met à jour la base de donnée avec de potentielles nouvelle donnée
        Ne rajoute que les anime pas encore présent"""


@bot.command(name='maj', help=help)
async def maj(ctx):
    await ctx.send("Update lancée")
    tab = update_db()
    await ctx.send(f"Update terminée:\nAnimes rajoutés : {tab[0]}\nPersos rajoutés : {tab[1]}")


help = """Recréé la base de donnée des personnages d'anime. A n'utiliser qu'en cas de modification dans les tableurs. 
    Précisez un anime si vous voulez juste supprimer celui ci"""


@bot.command(name='grossemaj', help=help)
async def grossemaj(ctx, *arr):
    origine = ' '.join(arr)
    if origine == "":
        if not await confirmation(ctx, f"Vous vous appretez à refaire toute la base de donnée des anime. Cela va prendre ~1min, souhaitez-vous continuer?", "Oui"):
            return
        c.execute('DROP TABLE personnages')
    else:
        found = None
        for row in c.execute(f'SELECT count(id) FROM personnages where lower(origine)="{origine.lower()}"'):
            found = row[0]
        if found is None or found == 0:
            await ctx.send("Pas trouvé l'anime")
            return
        if not await confirmation(ctx, f"Vous vous appretez à refaire l'anime {origine}, souhaitez-vous continuer?", "Oui"):
            return
        c.execute(f'DELETE FROM personnages where lower(origine)="{origine.lower()}"')
    await ctx.send("Update lancée")
    tab = update_db()
    await ctx.send(f"Update terminée:\nAnimes rajoutés : {tab[0]}\nPersos rajoutés : {tab[1]}")

help = """##liste (anime). Liste les animes cherchables.\nSi un anime est fourni, affiche si il est cherchable"""


@bot.command(name='liste', help=help)
async def liste(ctx, *arr):
    origine = ' '.join(arr)
    if origine != "":
        tab = []
        reussite = []
        for row in c.execute(f'SELECT distinct origine FROM personnages order by origine'):
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
        for row in c.execute('SELECT distinct origine FROM personnages order by origine'):
            txt += row[0]+", "
        await ctx.send(f"{txt[:-2]}")

help = """##astro signe anime. Affiche les perso du meme signe dans un anime.
        Le signe peut etre le signe directement ou une date de naissance"""


@bot.command(name='astro', help=help)
async def astro(ctx, signe="", *arr):
    origine = ' '.join(arr)
    if origine == "":
        await ctx.send(f"Pas d'anime marqué")
        return
    signe = find_sign(signe)
    if signe == -1:
        await ctx.send(f"Date pas reconnue")
        return
    if signe == -2:
        await ctx.send(f"Date incorrect")
        return
    if signe == -3:
        await ctx.send(f"Signe pas trouvé")
        return
    found = None
    for row in c.execute(f'SELECT distinct origine from personnages where lower(origine) = "{origine.lower()}"'):
        found = row[0]
    if found is None:
        await ctx.send(f"Anime '{origine}' pas trouvé")
        return
    origine = found
    description = ""
    for row in c.execute(f'SELECT nom, jour || "/" || mois FROM personnages where lower(signe)="{signe.lower()}" and lower(origine)="{origine.lower()}" order by mois, jour'):
        description += f"**{row[0]}** {row[1]}\n"
    embed = discord.Embed(title=f"Perso de {origine} étant {signe}", url="https://docs.google.com/spreadsheets/d/12rZUluWhjaikfK38hXo1xrNtDYyJF98OTFtdQ1kcFHI/edit?usp=sharing", description=description, color=0xbb1b1b)
    embed.set_author(name="AstroBot", url="https://github.com/MiteEnBois/bot-astro", icon_url="https://i2.wp.com/multiversitystatic.s3.amazonaws.com/uploads/2018/12/Shonen-Jump-logo.jpg")
    await ctx.send(embed=embed)

help = """##graph (anime). Affiche le graphique de la distribution des signes dans la base de donnée
        Un anime peut etre donné pour voir la distribution dans cet anime uniquement"""


@bot.command(name='graph', help=help)
async def graph(ctx, *arr):
    origine = ' '.join(arr)
    data = []
    labels = []
    colors = []
    title = "Total"
    query = "SELECT signe, count(nom), origine FROM personnages GROUP BY signe"
    if origine != "":
        query = query.replace("personnages", f'personnages WHERE lower(origine) = "{origine.lower()}"')
    temp_dict = {}
    for row in c.execute(query):
        if title == "Total" and origine != "":
            title = row[2]
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

help = """Permet d'enregistrer sa date d'anniversaire"""


@bot.command(name='annif', help=help)
async def annif(ctx, date=""):

    found = None
    for row in c.execute(f'SELECT jour || "/" || mois FROM utilisateurs where id = {ctx.author.id}'):
        found = row[0]
    if found is None:
        if date == "":
            await ctx.send("Vous n'êtes pas enregistré. Enregistrez votre date de naissance")
            return
        else:
            search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", date)
            if search is None:
                await ctx.send("Date incorrect. Format : 01/12")
            day = int(search.group(1))
            month = int(search.group(2))
            c.execute(f'INSERT INTO utilisateurs VALUES ({ctx.author.id},{day},{month})')
            c.execute(f'INSERT INTO appartenances_serveurs VALUES ({ctx.guild.id} ,{ctx.author.id})')
            await ctx.send(f"Anniversaire enregistré au {day}/{month}!")
            conn.commit()
            return
    else:
        if date == "":
            await ctx.send(f"Date de naissance enregistrée : {found}")
        else:
            search = re.search("([0-9]{1,2})/([0-9]{1,2})(/([0-9]{4}))?", date)
            if search is None:
                await ctx.send("Date incorrect. Format : 01/12")
            day = int(search.group(1))
            month = int(search.group(2))
            c.execute(f'UPDATE utilisateurs SET jour = {day}, mois={month} where id = {ctx.author.id}')
            await ctx.send(f"Anniversaire modifié au {day}/{month}!")
        s = None
        for row in c.execute(f'SELECT id_serveur, id_util FROM appartenances_serveurs where id_serveur = {ctx.guild.id} and id_util = {ctx.author.id}'):
            s = row[0]
        if s is None:
            c.execute(f'INSERT INTO appartenances_serveurs VALUES ({ctx.guild.id} ,{ctx.author.id})')
            await ctx.send(f"Rajouté au serveur")
            conn.commit()


help = """Affiche le prochain anniversaire"""


@bot.command(name='annifpro', help=help)
async def annifpro(ctx):
    nexts = next_bday(ctx.guild.id)
    if nexts is None:
        await ctx.send(f"Pas d'anniversaire trouvé :(")
        return
    for row in nexts:
        jours = row[1]
        id = row[2]

        member = ctx.guild.get_member(id)
        if member is None:
            memberName = id
            memberMention = id
        else:
            memberName = member.display_name
            memberMention = member.mention
        txt = ""
        if jours != 0:
            if jours > 1:
                txt += f"Le prochain anniversaire sera celui de **{memberName}**, dans {jours} jours! (le {row[0].day:02}/{row[0].month:02}/{row[0].year})\n"
            else:
                txt += f"Le prochain anniversaire sera celui de **{memberName}**, demain! (le {row[0].day:02}/{row[0].month:02}/{row[0].year})\n"
        else:
            txt += f"Le prochain anniversaire sera celui de **{memberName}**, ...aujourd'hui! Bon anniversaire {memberMention}!!\n"

        await ctx.send(txt)


help = """Change le canal d'annonce du serveur"""


@bot.command(name='canal', help=help)
async def canal(ctx, id: int):
    ch = ctx.guild.get_channel(id)
    if ch is None:
        await ctx.send("ID incorrect")
        return

    c.execute(f'UPDATE serveurs SET canal = {id} where id = {ctx.guild.id}')
    conn.commit()
    await ctx.send(f"La canal d'annonce du serveur est à présent le canal {ch.mention}")

help = """Permet de se retirer de la base de donnée de ce serveur"""


@bot.command(name='enleve', help=help)
async def enleve(ctx):
    remove_user(ctx.author)
    await ctx.send(f"Vous êtes retiré de ce serveur")

help = """Pong!"""


@bot.command(name='ping', help=help)
async def ping(ctx):
    await ctx.send("Pong!")

help = """Ping!"""


@bot.command(name='pong', help=help)
async def ping(ctx):
    await ctx.send("Ping!")


# ----------------------------- FIN SETUP

# c.execute(f'INSERT INTO utilisateurs VALUES ({4646},{18},{2})')
# c.execute(f'INSERT INTO appartenances_serveurs VALUES ({370295251983663114} ,{4646})')

# print(next_bday(370295251983663114))


@bot.event
async def on_member_remove(member):
    remove_user(member)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


@bot.event
async def on_guild_join(guild):
    c.execute(f'INSERT INTO serveurs VALUES ({guild.id},{0})')
    print(f"added {guild}")


# S'execute quand le bot est prêt; Affiche la liste des serveurs sur lesquelles le bot est actuellement

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(f"{bot.command_prefix}help"))
    print(f'{bot.user} is connected to the following guild:')
    for guild in bot.guilds:
        print(f'-{guild.name}')
    print(f'{bot.user} has started')
    update_db()
    await timer()

# lance le bot
bot.run(TOKEN)
