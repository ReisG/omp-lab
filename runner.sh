#!/bin/bash
# Usage: ./runner.sh experiment_name
# runs provided parallel omp program with
# different parameters (N, THREADS)
# and generates expreriment_name/results.csv afterwards
# required for visualization

set -euo pipefail

# ================= НАСТРОЙКИ ЭКСПЕРИМЕНТА =================
EXP_NAME="${1:-exp_$(date +%Y%m%d_%H%M%S)}"
SRC_FILE="main.c"
CC="gcc"
CFLAGS="-O3 -fopenmp -lm"

# Перебираемые параметры
# 30 50 100 500 1000 1500 5000 10000 15000 50000 100000
N_LIST=(30 50 70 90 100 500 1000)
# 1 2 3 4 5 6 7 8 9 10 20 40 60 80 100 120 140 160
THREADS_LIST=(10 20 40 60 80 100 120 140 160) # one thread program. No need for multiple threads

REPEATS=5

# Настройки LSF (Polus)
WTIME="00:15"       # Лимит времени на 1 запуск (ЧЧ:ММ)
MAX_ACTIVE_JOBS=4   # Лимит Polus: не более 4 задач одновременно
POLL_INTERVAL=1     # Пауза (сек) между проверками очереди
# ==========================================================

EXP_DIR="$PWD/$EXP_NAME"
BIN_DIR="$EXP_DIR/bins"
CSV_FILE="$EXP_DIR/results.csv"

mkdir -p "$EXP_DIR" "$BIN_DIR"

# Ждём, пока число наших задач в LSF станет меньше MAX_ACTIVE_JOBS
wait_for_slot() {
    while true; do
        local active
        active=$(bjobs -noheader 2>/dev/null | wc -l)
        if (( active < MAX_ACTIVE_JOBS )); then
            break
        fi
        sleep "$POLL_INTERVAL"
    done
}

# Ждём завершения вообще всех наших задач перед сбором CSV
wait_all_jobs() {
    echo "Ожидание завершения всех задач в очереди..."
    while true; do
        local active
        active=$(bjobs -noheader 2>/dev/null | wc -l)
        if (( active == 0 )); then
            break
        fi
        sleep "$POLL_INTERVAL"
    done
}

# 1. Компиляция бинарников под каждое N (на логин-узле)
echo "=== Компиляция ==="
for N in "${N_LIST[@]}"; do
    BIN="$BIN_DIR/prog_N${N}"
    echo "Компилирую N=$N -> $BIN"
    "$CC" $CFLAGS -DN="$N" "$SRC_FILE" -o "$BIN"
done

# 2. Постановка задач в очередь
echo "=== Запуск эксперимента: $EXP_NAME ==="
RUN_ID=0
declare -a RUN_META=()

for N in "${N_LIST[@]}"; do
    BIN="$BIN_DIR/prog_N${N}"
    for T in "${THREADS_LIST[@]}"; do
        # Выделяем по 1 физическому ядру на поток (на узле Polus их 20, дальше SMT)
        CORES=$T
        if (( CORES > 20 )); then
            CORES=20
        fi

        for (( iter=1; iter<=REPEATS; iter++ )); do
            RUN_ID=$((RUN_ID + 1))
            RUN_DIR="$EXP_DIR/run_${RUN_ID}"
            mkdir -p "$RUN_DIR"

            wait_for_slot

            echo "[Run #$RUN_ID] N=$N, threads=$T, iter=$iter/$REPEATS (cores=$CORES)"

            # Отправляем задачу в LSF напрямую.
            # Вывод программы отделён от вывода LSF через > prog.out 2> prog.err
            bsub -n "$CORES" \
                 -R "span[hosts=1]" \
                 -W "$WTIME" \
                 -o "$RUN_DIR/lsf.out" \
                 -e "$RUN_DIR/lsf.err" \
                 "export OMP_NUM_THREADS=$T; \
                  t_start=\$(date +%s.%N); \
                  \"$BIN\" > \"$RUN_DIR/prog.out\" 2> \"$RUN_DIR/prog.err\"; \
                  rc=\$?; \
                  t_end=\$(date +%s.%N); \
                  awk -v s=\"\$t_start\" -v e=\"\$t_end\" 'BEGIN { printf \"%.6f\n\", e - s }' > \"$RUN_DIR/time.txt\"; \
                  echo \"\$rc\" > \"$RUN_DIR/exit_code.txt\"" \
                 > "$RUN_DIR/submit.log" 2>&1

            RUN_META+=("${RUN_ID},${N},${T},${iter}")
        done
    done
done

# 3. Ожидание завершения и сбор результатов в CSV
wait_all_jobs

echo "=== Сбор результатов в $CSV_FILE ==="
echo "run_id,N,threads,iteration,time_sec,exit_code" > "$CSV_FILE"

for meta in "${RUN_META[@]}"; do
    IFS=',' read -r rid n t iter <<< "$meta"
    RUN_DIR="$EXP_DIR/run_${rid}"

    if [[ -f "$RUN_DIR/time.txt" && -f "$RUN_DIR/exit_code.txt" ]]; then
        time_val=$(cat "$RUN_DIR/time.txt")
        rc_val=$(cat "$RUN_DIR/exit_code.txt")
    elif grep -q "TERM_RUNLIMIT" "$RUN_DIR/lsf.out" 2>/dev/null; then
        time_val="inf"
        rc_val="TIMEOUT"
    else
        time_val="NA"
        rc_val="ERR"
    fi

    echo "${rid},${n},${t},${iter},${time_val},${rc_val}" >> "$CSV_FILE"
done