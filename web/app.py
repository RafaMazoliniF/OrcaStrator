from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime

import sqlite3, os, uuid

from functions import *
from manip_db import *

app = Flask(__name__)
app.secret_key = "orcastrator"

@app.route("/")
def direct():
    return redirect(url_for("home"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db') 

#/outputfile/{id} -> pagina com o texto de output

#/home -> visualização geral
@app.route("/home")
def home():
    envs = get_envs()
    return render_template('home.html', envs=envs)

#/new-env -> abre popup com formulario
@app.route("/new_env")
def new_env():
    return render_template('new_env.html')

@app.route("/save_env", methods=['POST'])
def save_env():
    #pega os dados do form e cria no database e cria o namespace
    name = request.form["name"]

    data = {
        "name": name,
        "cpu_pins": request.form.get("cpu_pins").split(","),  
        "cpu_max": int(request.form.get("cpu_max", 0)),
        "mem": int(request.form.get("mem", 0)),
        "io": int(request.form.get("io", 0)),
        "status": 1,
    }
    #timestamp atualizado direto no banco

    #adiciona no db
    env_id = add_env(data)
    #cria o namespace
    create_env(env_id, data)
    
    files = request.files.getlist("program_file")
    files = [f for f in files if f.filename]
    if files:   
        add_programs(env_id, name, files)

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
    delete_env(env_id)
    
    return redirect(url_for("home"))


if __name__ == "__main__":        
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
