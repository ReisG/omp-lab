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
from matplotlib.patches import Rectangle


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results.csv")
    out_img = csv_path.parent / "heatmap_mean.png"

    df = pd.read_csv(csv_path)
    df["N"] = pd.to_numeric(df["N"], errors="coerce")
    df["threads"] = pd.to_numeric(df["threads"], errors="coerce")
    # Строка "inf" автоматически преобразуется в float('inf')
    df["time_sec"] = pd.to_numeric(df["time_sec"], errors="coerce")

    # Берём успешные запуски (exit_code == 0) и таймауты (exit_code == TIMEOUT)
    df["exit_code_str"] = df["exit_code"].astype(str).str.strip()
    valid = df[df["exit_code_str"].isin(["0", "TIMEOUT"]) & df["time_sec"].notna()]

    if valid.empty:
        raise ValueError("Нет валидных данных для построения графика.")

    pivot = (
        valid.pivot_table(index="N", columns="threads", values="time_sec", aggfunc="mean")
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    pivot.index = pivot.index.astype(int)
    pivot.columns = pivot.columns.astype(int)

    raw = pivot.to_numpy(dtype=float)
    inf_mask = np.isinf(raw)
    nan_mask = np.isnan(raw)

    # Маскируем inf и NaN, чтобы цветовая шкала строилась только по конечным временам
    finite_data = np.ma.masked_where(inf_mask | nan_mask, raw)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="#e0e0e0")  # Серый цвет для незапущенных ячеек (NaN)

    fig, ax = plt.subplots(
        figsize=(max(6.0, len(pivot.columns) * 1.2), max(4.5, len(pivot.index) * 0.9))
    )
    im = ax.imshow(finite_data, aspect="auto", cmap=cmap, origin="lower")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Среднее время выполнения, сек")

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    ax.set_xlabel("Количество потоков (threads)")
    ax.set_ylabel("Размер задачи (N)")
    ax.set_title("Среднее время выполнения (mean, сек)")

    has_finite = finite_data.count() > 0
    mid = (finite_data.min() + finite_data.max()) / 2.0 if has_finite else 0.0

    for i in range(raw.shape[0]):
        for j in range(raw.shape[1]):
            if inf_mask[i, j]:
                # Закрашиваем ячейку с таймаутом в тёмно-бордовый и ставим знак бесконечности
                ax.add_patch(
                    Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="#67000d", edgecolor="none")
                )
                ax.text(j, i, "∞", ha="center", va="center", color="white", fontsize=14, fontweight="bold")
            elif nan_mask[i, j]:
                ax.text(j, i, "—", ha="center", va="center", color="#666666", fontsize=10)
            else:
                val = raw[i, j]
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