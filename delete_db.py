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


def remove_user(utilisateur, server):
    c.execute(f"DELETE FROM appartenances_serveurs where id_util = {utilisateur} and id_serveur = {server}")
    found = None
    for row in c.execute(f'SELECT count(id_serveur) FROM appartenances_serveurs where id_util = {utilisateur}'):
        found = row[0]
    if found is None or found == 0:
        c.execute(f"DELETE FROM utilisateurs where id = {utilisateur}")
    conn.commit()



if len(sys.argv) == 1:
    print(select('SELECT s.id from serveurs s'))
elif len(sys.argv) == 2:
    
    print(select(f'SELECT u.id, jour || "/" || mois from serveurs s, utilisateurs u, appartenances_serveurs a where u.id = a.id_util and a.id_serveur = s.id and s.id = {sys.argv[1]} order by mois, jour'))
else 
    remove_user(sys.argv[1],sys.argv[2])