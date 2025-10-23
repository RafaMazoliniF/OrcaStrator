import os
import subprocess
import time
import sys
import shutil
from pathlib import Path

def create(name: str, cpuset: str, cpu_quota: int, cpu_period: int = 100000,
               memory_max: str = "max", io_max: str = "max") -> int:
        """
        Cria um novo container
        
        Args:
            name: Nome do container
            cpuset: CPUs para pinning (ex: "0", "0-1", "0,2")
            cpu_quota: Quota de CPU em microsegundos
            cpu_period: Período de CPU em microsegundos (padrão: 100000)
            memory_max: Limite de memória (ex: "512M", "1G", "max")
            io_max: Limite de I/O (ex: "rbps=10485760 wbps=10485760", "max")
        """
        if os.geteuid() != 0:
            raise PermissionError("Este comando precisa de privilégios root")
        
        cgroup_path = f"/sys/fs/cgroup/{name}"
        
        # Script que roda dentro do namespace
        script = f"""
            hostname "{name}"
            mount -t proc proc /proc

            echo "+cpu +cpuset +memory +io" > /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || true

            # Cria e configura o cgroup
            mkdir -p "{cgroup_path}"
            echo "{cpuset}" > "{cgroup_path}/cpuset.cpus"
            echo 0 > "{cgroup_path}/cpuset.mems"
            echo "{cpu_quota} {cpu_period}" > "{cgroup_path}/cpu.max"
            echo "{memory_max}" > "{cgroup_path}/memory.max"

            # Configura I/O se não for "max"
            if [ "{io_max}" != "max" ]; then
                echo "{io_max}" > "{cgroup_path}/io.max" 2>/dev/null || true
            fi

            # Adiciona este processo ao cgroup
            echo $$ > "{cgroup_path}/cgroup.procs"

            # Mantém o namespace vivo
            exec sleep infinity
        """
        
        # Inicia o namespace
        proc = subprocess.Popen(
            ["unshare", "--fork", "--pid", "--mount-proc", "--uts", "--",
             "sh", "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        unshare_pid = proc.pid
        
        time.sleep(0.05) 

        try:
            children_path = f"/proc/{unshare_pid}/task/{unshare_pid}/children"
            with open(children_path, 'r') as f:
                sleep_infinity_pid = int(f.read().split()[0])
            
            time.sleep(0.05)
            return sleep_infinity_pid

        except Exception as e:
            proc.kill()
            proc.communicate() # Limpa os pipes
            raise IOError(f"Falha ao encontrar PID filho para o unshare (PID {unshare_pid}): {e}")
    

def destroy(env_name: str):
    if os.geteuid() != 0:
        raise PermissionError("Este comando precisa de privilégios root")
        
    # ----- Verificação de validade do ambiente ------
    cgroup_path = Path(f"/sys/fs/cgroup/{env_name}")
    if not cgroup_path.is_dir(): 
        raise ValueError(f"O cgroup \"{env_name}\" não existe")
    #-------------------------------------------------
    
    # Mata todos os processos do cgroup
    path_to_exclude = Path(f"{cgroup_path}/cgroup.kill")
    if path_to_exclude.write_text("1") == 0:
        raise RuntimeError("Escrita de remoção falhou")
    
    time.sleep(0.1)
    
    # Apaga o cgroup
    cgroup_path.rmdir()
    
    logs_dir_path = Path(f"/home/vagrant/logs/{env_name}")
    shutil.rmtree(logs_dir_path)    
        
LOGS_DIR_PATH = "../logs"
def run_program(env_name: str, command: str) -> int:
    if os.geteuid() != 0:
        raise PermissionError("Este comando precisa de privilégios root")
        
    # ----- Verificação de validade do ambiente ------
    cgroup_path = Path(f"/sys/fs/cgroup/{env_name}")
    if not cgroup_path.is_dir(): 
        raise ValueError(f"O cgroup \"{env_name}\" não existe")
    
    cgroup_procs = Path(f"{cgroup_path}/cgroup.procs")
    procs_raw = cgroup_procs.read_text()
    procs = []
    if procs_raw:
        procs = [int(pid_str) for pid_str in procs_raw.splitlines()]
    else:
        raise ValueError(f"O ambiente não existe")
    # -----------------------------------------------
    
    ns_pid = min(procs)
    
    log_path = Path(f"{LOGS_DIR_PATH}/{env_name}")
    log_path.mkdir(parents=True, exist_ok=True)
    
    with open(f"{log_path}/{env_name}_stdout.log", "w") as stdout_f, open(f"{log_path}/{env_name}_stderr.log", "w") as stderr_f:
        proc = subprocess.Popen(
            ["nsenter", "--all", "--cgroup", "--target", str(ns_pid), "--"] + command,
            stdout=stdout_f,
            stderr=stderr_f
        )
        
    with open(f"{cgroup_path}/cgroup.procs", "a") as f:
        print(f"{proc.pid}", file=f)

        
    return proc.pid

print(create("teste1", "0", 10000, 100000, "512M", "max"))
try: 
    print(run_program("teste1", ["python3", "/home/vagrant/web/stress.py"]))
except Exception as e:
    print(f"Erro ao executar programa: {e}")
    destroy("teste1")
    sys.exit()
    
print("FOI")
time.sleep(30)
destroy("teste1")