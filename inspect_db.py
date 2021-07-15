import sqlite3
import sys
# load la base de donnée
conn = sqlite3.connect('astro.db')
c = conn.cursor()


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
            txt += f"{col} " + " " * (taille[i] - len(str(col)))
            i += 1
        txt += "\n"
    return txt


if len(sys.argv) == 1:
    print(select('SELECT s.id from serveurs s'))
else:
    print(select(f'SELECT u.id, jour || "/" || mois from serveurs s, utilisateurs u, appartenances_serveurs a where u.id = a.id_util and a.id_serveur = s.id and s.id = {sys.argv[1]} order by mois, jour'))
