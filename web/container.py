import subprocess
import shlex
import os

def run_command_safely(command_string):
    """
    Executa um comando de shell a partir de uma string de forma segura,
    separando os argumentos automaticamente e sem usar shell=True.
    Retorna a saída padrão e de erro.
    """
    try:
        # Usa shlex.split() para separar a string em uma lista de argumentos
        args = shlex.split(command_string)
        
        resultado = subprocess.run(
            args, 
            check=True, 
            capture_output=True, 
            text=True
        )
        return resultado.stdout, resultado.stderr
    except subprocess.CalledProcessError as e:
        return None, e.stderr
    except FileNotFoundError:
        return None, "Comando não encontrado. Verifique o PATH."
pid = os.getpid()
commands = [
    "unshare -p -f --mount-proc /bin/bash",
    "mkdir /sys/fs/cgroup/test_group",
    "echo \"+cpu +cpuset\" > /sys/fs/cgroup/cgroup.subtree_control",
    "echo 0 > /sys/fs/cgroup/test_group/cpuset.cpus",
    "echo \"20000 100000\" > /sys/fs/cgroup/labgrp1/cpu.max",
    f"echo {pid} > /sys/fs/cgroup/test_group/cgroup.procs",
    "stress -c 1"
]

for command in commands:
    stdout, stderr = run_command_safely(command)

    if stdout:
        print("Saída do comando:")
        print(stdout)
    if stderr:
        print("Saída de erro:")
        print(stderr)
        
print("RODOU TUDO")