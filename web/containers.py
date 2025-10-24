import os
import subprocess
import time
import sys
import shutil
from pathlib import Path

# Definido globalmente para consistência
LOGS_DIR_PATH = "../logs"

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

            # MODIFICADO: Adicionado '+freezer'
            echo "+cpu +cpuset +memory +io +freezer" > /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || true

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
        print(f"O cgroup \"{env_name}\" não existe. Continuando para limpar logs...")
        # Não levanta erro, permite limpar logs órfãos
    else:
        # Mata todos os processos do cgroup
        path_to_exclude = Path(f"{cgroup_path}/cgroup.kill")
        try:
            if path_to_exclude.write_text("1") == 0:
                print(f"Aviso: Escrita de remoção falhou para cgroup {env_name}")
        except IOError as e:
            print(f"Aviso: Não foi possível matar processos do cgroup {env_name}: {e}")
        
        time.sleep(0.1)
        
        # Apaga o cgroup
        try:
            cgroup_path.rmdir()
        except OSError as e:
            print(f"Aviso: Não foi possível remover o diretório cgroup {env_name}: {e}")
    
    # Usa a variável global LOGS_DIR_PATH
    logs_dir_path = Path(LOGS_DIR_PATH) / env_name
    if logs_dir_path.exists():
        try:
            shutil.rmtree(logs_dir_path)
        except OSError as e:
            print(f"Aviso: Não foi possível remover diretório de log {logs_dir_path}: {e}")
            

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
        raise ValueError(f"O ambiente não existe ou não tem processos")
    # -----------------------------------------------
    
    ns_pid = min(procs)
    
    # Usa a variável global LOGS_DIR_PATH
    log_path = Path(f"{LOGS_DIR_PATH}/{env_name}")
    log_path.mkdir(parents=True, exist_ok=True)
    
    with open(f"{log_path}/{env_name}_stdout.log", "w") as stdout_f, open(f"{log_path}/{env_name}_stderr.log", "w") as stderr_f:
        full_command = [
            "nsenter", "--all", "--cgroup", "--target", str(ns_pid), 
            "--", 
            "stdbuf", "-oL", "-eL", "sh", "-c", command
        ]
        
        proc = subprocess.Popen(
            full_command,
            stdout=stdout_f,
            stderr=stderr_f
        )
        
    with open(f"{cgroup_path}/cgroup.procs", "a") as f:
        print(f"{proc.pid}", file=f)

        
    return proc.pid

# --- ADICIONADO: Funções do Freezer ---

def pause(env_name: str):
    """Pausa (congela) todos os processos no cgroup"""
    if os.geteuid() != 0:
        raise PermissionError("Este comando precisa de privilégios root")
    cgroup_path = Path(f"/sys/fs/cgroup/{env_name}")
    if not cgroup_path.is_dir(): 
        raise ValueError(f"O cgroup \"{env_name}\" não existe")
    
    freeze_path = cgroup_path / "cgroup.freeze"
    try:
        freeze_path.write_text("1")
    except IOError as e:
        raise IOError(f"Falha ao pausar cgroup {env_name}: {e}")

def resume(env_name: str):
    """Retoma (descongela) todos os processos no cgroup"""
    if os.geteuid() != 0:
        raise PermissionError("Este comando precisa de privilégios root")
    cgroup_path = Path(f"/sys/fs/cgroup/{env_name}")
    if not cgroup_path.is_dir(): 
        raise ValueError(f"O cgroup \"{env_name}\" não existe")
    
    freeze_path = cgroup_path / "cgroup.freeze"
    try:
        freeze_path.write_text("0")
    except IOError as e:
        raise IOError(f"Falha ao retomar cgroup {env_name}: {e}")

def get_proc_count(env_name: str) -> int:
    """Retorna o número de processos no cgroup"""
    if os.geteuid() != 0:
        raise PermissionError("Este comando precisa de privilégios root")
        
    cgroup_path = Path(f"/sys/fs/cgroup/{env_name}")
    if not cgroup_path.is_dir(): 
        raise ValueError(f"O cgroup \"{env_name}\" não existe")
    
    cgroup_procs = Path(f"{cgroup_path}/cgroup.procs")
    procs_raw = cgroup_procs.read_text()
    
    if not procs_raw:
        return 0
    
    return len(procs_raw.splitlines())