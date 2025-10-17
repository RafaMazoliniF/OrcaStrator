#!/bin/bash


set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "Erro: Este script precisa ser executado como root." >&2
  exit 1
fi

if [ "$#" -lt 5 ]; then
  echo "Uso: $0 <hostname> <cgroup_name> <cpuset_cpus> '<cpu_max_quota cpu_max_period>' <comando> [args...]"
  echo "Exemplo: $0 meu-container meu-cgroup 0 '10000 100000' python3 teste.py"
  exit 1
fi

HOSTNAME=$1
CGROUP_NAME=$2
CPUSET_CPUS=$3
CPU_MAX=$4
shift 4
COMMAND=("$@")

CGROUP_PATH="/sys/fs/cgroup/${CGROUP_NAME}"

unshare --fork --pid --mount-proc --uts -- sh -c '
    hostname_ns="$1"
    cgroup_path_ns="$2"
    cpuset_cpus_ns="$3"
    cpu_max_ns="$4"
    shift 4

    hostname "$hostname_ns"
    echo "+cpu +cpuset" > /sys/fs/cgroup/cgroup.subtree_control
    rmdir "$cgroup_path_ns" 2>/dev/null || true
    mkdir "$cgroup_path_ns"
    echo "$cpuset_cpus_ns" > "${cgroup_path_ns}/cpuset.cpus"
    echo 0 > "${cgroup_path_ns}/cpuset.mems"
    echo "$cpu_max_ns" > "${cgroup_path_ns}/cpu.max"
    echo $$ > "${cgroup_path_ns}/cgroup.procs"
    exec "$@"

' sh "$HOSTNAME" "$CGROUP_PATH" "$CPUSET_CPUS" "$CPU_MAX" "${COMMAND[@]}"