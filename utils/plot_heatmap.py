# ============================================================
# Creating heatmap out of .csv file
# Usage: python3 plot_results.py omp_scaling_test/results.csv
# ============================================================

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

if not os.environ.get("DISPLAY"):
    import matplotlib
    matplotlib.use("Agg")

import matplotlib.pyplot as plt


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results.csv")
    out_img = csv_path.parent / "heatmap_mean.png"

    df = pd.read_csv(csv_path)
    for col in ("N", "threads", "time_sec", "exit_code"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid = df[(df["exit_code"] == 0) & df["time_sec"].notna()]
    if valid.empty:
        raise ValueError("No valid runs found (exit_code == 0).")

    # Строки — N, столбцы — threads, значения — среднее время по запускам
    pivot = (
        valid.pivot_table(index="N", columns="threads", values="time_sec", aggfunc="mean")
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    pivot.index = pivot.index.astype(int)
    pivot.columns = pivot.columns.astype(int)

    data = np.ma.masked_invalid(pivot.to_numpy(dtype=float))
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="#e0e0e0")

    fig, ax = plt.subplots(
        figsize=(max(6.0, len(pivot.columns) * 1.2), max(4.5, len(pivot.index) * 0.9))
    )
    im = ax.imshow(data, aspect="auto", cmap=cmap, origin="lower")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Среднее время выполнения, сек")

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    ax.set_xlabel("Количество потоков (threads)")
    ax.set_ylabel("Размер задачи (N)")
    ax.set_title("Среднее время выполнения (mean, сек)")

    mid = (data.min() + data.max()) / 2.0
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if np.ma.is_masked(data[i, j]):
                ax.text(j, i, "—", ha="center", va="center", color="#666666", fontsize=10)
            else:
                val = data[i, j]
                text_color = "white" if val > mid else "black"
                label = f"{val:.4f}" if val < 1 else f"{val:.2f}"
                ax.text(
                    j, i, label,
                    ha="center", va="center",
                    color=text_color, fontsize=10, fontweight="bold"
                )

    plt.tight_layout()
    plt.savefig(out_img, dpi=150)
    print(f"Saved: {out_img}")

    if os.environ.get("DISPLAY"):
        plt.show()


if __name__ == "__main__":
    main()