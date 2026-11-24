# ===========================================================
# Implements urgent data collection. Collection after failure
# generates experiment/results.csv that contains data for visualization
# usage: python3 collect_results.py omp_scaling_test 
# ===========================================================

import re
import sys
from collections import defaultdict
from pathlib import Path


def main():
    exp_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("omp_scaling_test")
    if not exp_dir.is_dir():
        raise FileNotFoundError(f"Папка эксперимента не найдена: {exp_dir}")

    run_dirs = []
    for d in exp_dir.iterdir():
        if d.is_dir():
            m = re.fullmatch(r"run_(\d+)", d.name)
            if m:
                run_dirs.append((int(m.group(1)), d))

    run_dirs.sort(key=lambda x: x[0])

    rows = []
    skipped = 0
    iter_counts = defaultdict(int)

    for run_id, rdir in run_dirs:
        time_file = rdir / "time.txt"
        rc_file = rdir / "exit_code.txt"
        lsf_file = rdir / "lsf.out"

        # Пропускаем задачи, которые были прерваны или не успели стартовать
        if not (time_file.exists() and rc_file.exists() and lsf_file.exists()):
            skipped += 1
            continue

        time_val = time_file.read_text().strip()
        rc_val = rc_file.read_text().strip()
        lsf_text = lsf_file.read_text(errors="replace")

        m_threads = re.search(r"OMP_NUM_THREADS=(\d+)", lsf_text)
        m_n = re.search(r"prog_N(\d+)", lsf_text)

        if not (m_threads and m_n and time_val):
            skipped += 1
            continue

        n_val = int(m_n.group(1))
        t_val = int(m_threads.group(1))
        iter_counts[(n_val, t_val)] += 1
        iter_num = iter_counts[(n_val, t_val)]

        rows.append((run_id, n_val, t_val, iter_num, time_val, rc_val))

    csv_path = exp_dir / "results.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("run_id,N,threads,iteration,time_sec,exit_code\n")
        for row in rows:
            f.write(",".join(map(str, row)) + "\n")

    print(f"Собрано завершённых запусков: {len(rows)}")
    print(f"Пропущено незавершённых/снятых: {skipped}")
    print(f"Таблица сохранена: {csv_path}")


if __name__ == "__main__":
    main()