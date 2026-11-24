# ============================================================
# Creating heatmap out of .csv file
# Usage: python3 plot_results.py omp_scaling_test/results.csv
# ============================================================

import copy
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

if not os.environ.get("DISPLAY"):
    import matplotlib
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results.csv")
    out_img = csv_path.parent / "heatmap_mean.png"

    df = pd.read_csv(csv_path)
    df["N"] = pd.to_numeric(df["N"], errors="coerce")
    df["threads"] = pd.to_numeric(df["threads"], errors="coerce")
    df = df[df["N"].notna() & df["threads"].notna()].copy()

    if df.empty:
        raise ValueError("В results.csv нет строк с корректными N и threads.")

    df["N"] = df["N"].astype(int)
    df["threads"] = df["threads"].astype(int)

    # Хороший запуск: exit_code == 0 и конечное числовое время
    exit_num = pd.to_numeric(df["exit_code"], errors="coerce")
    time_num = pd.to_numeric(df["time_sec"], errors="coerce")
    df["is_good"] = (exit_num == 0) & np.isfinite(time_num)
    df["good_time"] = np.where(df["is_good"], time_num, np.nan)

    all_n = sorted(df["N"].unique())
    all_t = sorted(df["threads"].unique())
    grid = pd.DataFrame(np.nan, index=all_n, columns=all_t, dtype=float)

    for (n_val, t_val), grp in df.groupby(["N", "threads"]):
        good_vals = grp.loc[grp["is_good"], "good_time"]
        if len(good_vals) > 0:
            # Хотя бы одна отработала — среднее из хороших значений
            grid.loc[n_val, t_val] = good_vals.mean()
        else:
            # Все запуски для этой конфигурации с ошибкой / inf
            grid.loc[n_val, t_val] = np.inf

    raw = grid.to_numpy(dtype=float)
    inf_mask = np.isinf(raw)
    nan_mask = np.isnan(raw)

    finite_data = np.ma.masked_where(inf_mask | nan_mask, raw)
    cmap = copy.copy(plt.get_cmap("YlOrRd"))
    cmap.set_bad(color="#e0e0e0")

    fig, ax = plt.subplots(
        figsize=(max(6.5, len(all_t) * 1.25), max(4.8, len(all_n) * 0.95))
    )
    im = ax.imshow(finite_data, aspect="auto", cmap=cmap, origin="lower")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Среднее время выполнения, сек")

    ax.set_xticks(np.arange(len(all_t)))
    ax.set_xticklabels(all_t)
    ax.set_yticks(np.arange(len(all_n)))
    ax.set_yticklabels(all_n)

    ax.set_xlabel("Количество потоков (threads)")
    ax.set_ylabel("Размер задачи (N)")
    ax.set_title("Среднее время выполнения (mean, сек)")

    has_finite = finite_data.count() > 0
    mid = (finite_data.min() + finite_data.max()) / 2.0 if has_finite else 0.0

    for i in range(raw.shape[0]):
        for j in range(raw.shape[1]):
            if inf_mask[i, j]:
                ax.add_patch(
                    Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="#67000d", edgecolor="none", zorder=2)
                )
                ax.text(
                    j, i, "∞",
                    ha="center", va="center",
                    color="white", fontsize=14, fontweight="bold", zorder=3
                )
            elif nan_mask[i, j]:
                ax.text(j, i, "—", ha="center", va="center", color="#666666", fontsize=10, zorder=3)
            else:
                val = raw[i, j]
                text_color = "white" if val > mid else "black"
                label = f"{val:.4f}" if val < 1 else f"{val:.2f}"
                ax.text(
                    j, i, label,
                    ha="center", va="center",
                    color=text_color, fontsize=10, fontweight="bold", zorder=3
                )

    if inf_mask.any():
        ax.legend(
            handles=[Patch(facecolor="#67000d", label="∞ — все запуски завершились ошибкой / таймаутом")],
            loc="upper left",
            bbox_to_anchor=(0, 1.13),
            frameon=False,
        )

    plt.tight_layout()
    plt.savefig(out_img, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_img}")

    if os.environ.get("DISPLAY"):
        plt.show()


if __name__ == "__main__":
    main()