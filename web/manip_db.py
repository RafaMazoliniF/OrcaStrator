import sqlite3, json, os, shutil
from datetime import datetime
import containers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db') 
# Caminho para logs (Aponta para o diretório PAI (..))
LOGS_DIR = os.path.join(BASE_DIR, '..', 'logs')

def init_db():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    # MODIFICADO: Adicionado 'ns_pid INTEGER'
    c.execute("""CREATE TABLE IF NOT EXISTS envs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT NOT NULL UNIQUE, 
        cpu_pins TEXT, 
        cpu_max INTEGER, 
        mem INTEGER, 
        io INTEGER, 
        status INTEGER CHECK(status IN (0,1,2)), 
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
        command TEXT NOT NULL,
        ns_pid INTEGER 
    )""")

    c.execute("""CREATE TRIGGER IF NOT EXISTS prevent_delete_active_env 
        BEFORE DELETE ON envs 
        FOR EACH ROW 
        WHEN OLD.status = 0 
        BEGIN 
            SELECT RAISE(ABORT, 'Não é permitido deletar um ambiente ativo. Pare-o primeiro'); 
        END;
    """)
    
    con.commit()
    con.close()


def add_env(data):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    try:
        env_name = data["name"]
        pins = data.get("cpu_pins")
        cpu_max = data.get("cpu_max")
        mem = data.get("mem")
        io = data.get("io")
        status = data.get("status")
        command = data.get("command", "") 

        # MODIFICADO: Captura o ns_pid retornado por containers.create()
        ns_pid = containers.create(env_name, pins, cpu_max * 1000, 100000, f"M{mem}", "max")

        # MODIFICADO: Adicionado 'ns_pid' ao INSERT
        c.execute("""INSERT INTO envs (name, cpu_pins, cpu_max, mem, io, status, command, ns_pid) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                    (env_name, pins, cpu_max, mem, io, status, command, ns_pid))
        
        con.commit()
        env_id = c.lastrowid
        return env_id
        
    except sqlite3.IntegrityError:
        return None
    except Exception:
        # Se containers.create() falhar, não insere no DB
        return None
    finally:
        con.close()


def start_env(env_id):
    """MODIFICADO: Retoma um ambiente pausado e inicia o processo se for a primeira vez."""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    c.execute("SELECT name, command, status FROM envs WHERE id=?", (env_id,))
    row = c.fetchone()
    
    if not row:
        con.close()
        return

    env_name, command, status = row

    try:
        # Retoma o cgroup (caso esteja pausado)
        containers.resume(env_name)
        
        # Verifica se o processo precisa ser iniciado
        # (Se só houver 1 processo, é o 'sleep infinity')
        if containers.get_proc_count(env_name) <= 1:
            if command:
                containers.run_program(env_name, command)
        
        # Atualiza o status para 0 (Em execução)
        c.execute("UPDATE envs SET status=0 WHERE id=?", (env_id,))
        con.commit()
        
    except Exception as e:
        print(f"Erro ao iniciar/retomar {env_name}: {e}")
    finally:
        con.close()


def stop_env(env_id):
    """MODIFICADO: Pausa (congela) o ambiente e atualiza o status para 1 (parado)"""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("SELECT name FROM envs WHERE id=?", (env_id,))
    row = c.fetchone()
    if not row:
        con.close()
        return "Ambiente não encontrado"
    
    env_name = row[0]

    try:
        # Pausa o cgroup
        containers.pause(env_name)
        # Atualiza o status para 1 (Parado/Pausado)
        c.execute("UPDATE envs SET status=1 WHERE id=?", (env_id,))
        con.commit()
    except Exception as e:
        print(f"Erro ao pausar {env_name}: {e}")
    finally:
        con.close()


def delete_env(env_id):
    """Deleta um ambiente e seus arquivos associados"""

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
        # Tenta descongelar antes de destruir (caso esteja pausado)
        containers.resume(env_name)
    except Exception:
        pass # Ignora erro se o cgroup já foi removido

    containers.destroy(env_name)

    try:
        c.execute("DELETE FROM envs WHERE id = ?", (env_id,))
        con.commit()
        con.close()
        
        # Remove logs se existirem (usa LOGS_DIR corrigido)
        logs_path = os.path.join(LOGS_DIR, env_name)
        if os.path.exists(logs_path):
            shutil.rmtree(logs_path)

        return None 
        
    except sqlite3.IntegrityError as e:
        con.close()
        return str(e)
    except Exception as e:
        con.close()
        return str(e)


def get_envs():
    """Retorna todos os ambientes"""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    # MODIFICADO: Seleciona 'ns_pid' (agora é a 10ª coluna, índice 9)
    c.execute("SELECT id, name, cpu_pins, cpu_max, mem, io, status, timestamp, command, ns_pid FROM envs")
    response = c.fetchall()

    con.close()
    return response


def get_env_by_id(env_id):
    """Retorna um ambiente específico"""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    # MODIFICADO: Seleciona todas as colunas (incluindo ns_pid)
    c.execute("SELECT * FROM envs WHERE id=?", (env_id,))
    response = c.fetchone()

    con.close()
    return response


def get_available_mem():
    """Calcula memória disponível (assumindo 4GB total)"""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    c.execute("SELECT SUM(mem) FROM envs WHERE status=0")
    usage_mem = c.fetchone()[0] or 0

    con.close()

    # Assume 4GB de memória total
    available_mem = 4096 - usage_mem
    return available_mem


def get_active_envs():
    """Retorna apenas ambientes ativos (status=0)"""
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()

    # MODIFICADO: Seleciona todas as colunas (incluindo ns_pid)
    c.execute("SELECT * FROM envs WHERE status=0")
    response = c.fetchall()

    con.close()
    return response