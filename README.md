# OrcaStrator

## Banco de Dados
- id : int autoincrement
- name : string
- cpu_pins : array(int)
- cpu-max : int
- mem : int
- io : int
- status: int (0, 1 ou 2)
- timestamp : datetime (last action)
- output_path: string
- referencia para a tabela de programas (uma tabela para cada env)

## Rotas
- /home
- /new-env -> abre popup com formulario
- /save-env -> fecha popup executando todas as ações de registro no banco e criação do env e cgroup
- /start-env/{id}
- /stop-env/{id}
- /delete-env/{id}
- /outputfile/{id} -> pagina com o texto de output

## Cgroups
```bash
echo "+cpu +cpuset" > /sys/fs/cgroup/cgroup.subtree_control
mkdir /sys/fs/cgroup/<name>
echo <ID> > /sys/fs/cgroup/<name>/cpuset.cpus
echo "<relation>" > /sys/fs/cgroup/<name>/cpu.max
```