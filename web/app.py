from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime

import sqlite3, os, uuid

from manip_db import *
# containers.py não precisa ser importado aqui

app = Flask(__name__)
app.secret_key = "orcastrator"

@app.route("/")
def direct():
    return redirect(url_for("home"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db') 

# Define o caminho raiz dos logs (consistente com containers.py)
LOGS_DIR_ROOT = os.path.join(BASE_DIR, '..', 'logs')

#/home -> visualização geral
@app.route("/home")
def home():
    envs = get_envs()
    error_delete = request.args.get('error_delete')
    
    return render_template('home.html', envs=envs, error_delete=error_delete)

#/new-env -> abre popup com formulario
@app.route("/new_env")
def new_env():
    return render_template('new_env.html')

@app.route("/save_env", methods=['POST'])
def save_env():
    #pega os dados do form e cria no database e cria o namespace
    name = request.form["name"].capitalize()

    cpu_pins = ",".join(map(str, sorted(int(n.strip()) for n in request.form.get("cpu_pins", "").split(",") if n.strip().isdigit())))

    data = {
        "name": name,
        "cpu_pins": cpu_pins,  
        "cpu_max": int(request.form.get("cpu_max", 0)),
        "mem": int(request.form.get("mem", 0)),
        "io": int(request.form.get("io", 0)),
        "command": request.form.get("command", ""), # Campo de comando
        "status": 1,
    }
    
    env_id = add_env(data)
    if env_id is None:
        envs = get_envs()
        return render_template("home.html", envs=envs, error_name=f"Já existe um ambiente com o nome '{name}'!")
    
    return redirect('/home')

#/start-env/{id}
@app.route("/start_env/<int:env_id>")
def start_env_route(env_id):
    start_env(env_id)
    
    return redirect(url_for("home"))

#/stop-env/{id}
@app.route("/stop_env/<int:env_id>")
def stop_env_route(env_id):
    stop_env(env_id)
    
    return redirect(url_for("home"))

#/delete-env/{id}
@app.route("/delete_env/<int:env_id>")
def delete_env_route(env_id):
    error_delete = delete_env(env_id)

    if error_delete:
        return redirect(url_for("home", error_delete=error_delete))
    
    return redirect(url_for("home"))

# ROTA MODIFICADA para ler os logs de stdout e stderr
@app.route("/program_content/<int:env_id>")
def program_content(env_id):
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    c.execute("SELECT name FROM envs WHERE id=?", (env_id,))
    row = c.fetchone()
    con.close()

    if not row:
        return jsonify({"error": "Ambiente não encontrado."}), 404

    env_name = row[0]
    
    # Constrói os caminhos para os arquivos de log que containers.py cria

    log_dir = os.path.join(LOGS_DIR_ROOT, env_name)
    stdout_path = os.path.join(log_dir, f"{env_name}_stdout.log")
    stderr_path = os.path.join(log_dir, f"{env_name}_stderr.log")

    content = ""
    
    if os.path.exists(stdout_path):
        try:
            with open(stdout_path, "r", encoding="utf-8") as f:
                content += "--- STDOUT ---\n"
                content += f.read()
        except Exception as e:
            content += f"\nErro ao ler stdout: {e}\n"
    
    if os.path.exists(stderr_path):
        try:
            with open(stderr_path, "r", encoding="utf-8") as f:
                content += "\n\n--- STDERR ---\n"
                content += f.read()
        except Exception as e:
            content += f"\nErro ao ler stderr: {e}\n"

    if not content:
        # Adicionado verificação se o diretório existe para dar uma msg melhor
        if not os.path.exists(log_dir):
             return jsonify({"content": f"(Diretório de log não encontrado em: {log_dir})"})
        return jsonify({"content": "(Nenhum output registrado para este ambiente)"})

    return jsonify({"content": content})


if __name__ == "__main__":
    init_db() 
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)