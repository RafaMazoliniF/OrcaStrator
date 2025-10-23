import sqlite3, json, os, shutil
from datetime import datetime
from functions import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db') 

def init_db():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    c.execute("CREATE TABLE IF NOT EXISTS envs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, cpu_pins TEXT, cpu_max INTEGER, mem INTEGER, io INTEGER, status INTEGER CHECK(status IN (0,1,2)), timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, id_program TEXT)")

    c.execute("CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY AUTOINCREMENT, env_id INTEGER NOT NULL, path TEXT NOT NULL, FOREIGN KEY(env_id) REFERENCES envs(id) ON DELETE CASCADE)")

    c.execute("CREATE TRIGGER IF NOT EXISTS prevent_delete_active_env BEFORE DELETE ON envs FOR EACH ROW WHEN OLD.status = 0 BEGIN SELECT RAISE(ABORT, 'Não é permitido deletar um ambiente ativo. Pare-o primeiro'); END;")
    
    con.commit()
    con.close()

def add_env(data):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    try:
        c.execute("INSERT INTO envs (name, cpu_pins, cpu_max, mem, io, status) " \
        "VALUES (?, ?, ?, ?, ?, ?)", (data["name"], str(data.get("cpu_pins")), data.get("cpu_max"), 
                                        data.get("mem"), data.get("io"), data.get("status")))
        
        con.commit()
        env_id = c.lastrowid

        return env_id
    except sqlite3.IntegrityError:
        return None

    finally:
        con.close()

def add_programs(env_id, name, files):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    folder = f"./programs/{name}"
    os.makedirs(folder, exist_ok=True)

    program_ids = []
    for file in files:
        file_path = os.path.join(folder, file.filename.lower().replace(" ", "_"))
        file.save(file_path)

        c.execute("INSERT INTO programs (env_id, path) VALUES (?, ?)", (env_id, file_path))
        program_ids.append(c.lastrowid)

    c.execute("UPDATE envs SET id_program=? WHERE id=?", (json.dumps(program_ids), env_id))

    con.commit()
    con.close()

def start_env(env_id):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("UPDATE envs SET status=0 WHERE id=?", (env_id,))
    
    #start_env_cgroups()

    con.commit()
    con.close()

def stop_env(env_id):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("UPDATE envs SET status=1 WHERE id=?", (env_id,))

    #stop_env_cgroups()

    con.commit()
    con.close()

import shutil

def delete_env(env_id):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    c.execute("SELECT name FROM envs WHERE id=?", (env_id,))
    row = c.fetchone()
    if not row:
        con.close()
        return "Ambiente não encontrado"

    env_name = row[0]

    try:
        c.execute("DELETE FROM envs WHERE id = ?", (env_id,))
        con.commit()
        con.close()

        folder_path = os.path.join(BASE_DIR, "programs", env_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

        return None 
    except sqlite3.IntegrityError as e:
        con.close()
        return str(e)
    except Exception as e:
        return str(e)

def get_envs():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("SELECT * FROM envs")
    response = c.fetchall()

    con.close()

    return response

def get_files(env_id):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    c.execute("SELECT path FROM programs WHERE env_id=?", (env_id,))
    result = c.fetchall()

    con.close()

    if result:
        paths = [row[0] for row in result]
        
        return paths
    else:
        return None
    
def get_available_mem():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("SELECT SUM(mem) FROM envs")
    usage_mem = c.fetchone()[0] or 0

    available_mem = 4096 - usage_mem

    return available_mem