#!/usr/bin/env python3
"""
Построить картинку "сходимость" по результатам MATSim.

Источники:
- scenarios/shamalgan/output_100it/modestats.csv  (mode shares by iteration)
- scenarios/shamalgan/output_100it/scorestats.csv (avg_executed score by iteration)

Выход:
- Visualization/docs-progress/simulation_convergence.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODESTATS = ROOT / "scenarios" / "shamalgan" / "output_100it" / "modestats.csv"
DEFAULT_SCORESTATS = ROOT / "scenarios" / "shamalgan" / "output_100it" / "scorestats.csv"
DEFAULT_OUT = ROOT / "Visualization" / "docs-progress" / "simulation_convergence.png"


def _read_modestats(path: Path) -> dict[str, list[float]]:
    # modestats.csv: iteration;car;pt;walk
    it: list[int] = []
    car: list[float] = []
    pt: list[float] = []
    walk: list[float] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            it.append(int(row["iteration"]))
            car.append(float(row.get("car", 0.0)))
            pt.append(float(row.get("pt", 0.0)))
            walk.append(float(row.get("walk", 0.0)))
    return {"iteration": [float(x) for x in it], "car": car, "pt": pt, "walk": walk}


def _read_scorestats(path: Path) -> dict[str, list[float]]:
    # scorestats.csv: iteration;avg_executed;avg_worst;avg_average;avg_best
    it: list[int] = []
    avg_executed: list[float] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            it.append(int(row["iteration"]))
            avg_executed.append(float(row.get("avg_executed", "nan")))
    return {"iteration": [float(x) for x in it], "avg_executed": avg_executed}


def main() -> None:
    ap = argparse.ArgumentParser(description="Сходимость MATSim по 0..N итерациям.")
    ap.add_argument("--modestats", type=Path, default=DEFAULT_MODESTATS)
    ap.add_argument("--scorestats", type=Path, default=DEFAULT_SCORESTATS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--title", default="Результаты симуляции — 100 итераций MATSim")
    args = ap.parse_args()

    ms = _read_modestats(args.modestats)
    ss = _read_scorestats(args.scorestats)

    # Align by iteration (take intersection, keep order).
    it_ms = list(map(int, ms["iteration"]))
    it_ss = list(map(int, ss["iteration"]))
    it_set = set(it_ms).intersection(it_ss)
    it = [i for i in it_ms if i in it_set]
    idx_ms = {i: k for k, i in enumerate(it_ms)}
    idx_ss = {i: k for k, i in enumerate(it_ss)}

    car = [ms["car"][idx_ms[i]] for i in it]
    pt = [ms["pt"][idx_ms[i]] for i in it]
    walk = [ms["walk"][idx_ms[i]] for i in it]
    avg = [ss["avg_executed"][idx_ss[i]] for i in it]

    fig = plt.figure(figsize=(12.8, 7.2), dpi=160)
    fig.suptitle(args.title, fontsize=22, y=0.98)

    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)

    # Stacked bars: mode shares.
    x = list(range(len(it)))
    ax1.bar(x, car, color="#1f77b4", label="Car")
    ax1.bar(x, pt, bottom=car, color="#2ca02c", label="PT")
    bottom2 = [car[i] + pt[i] for i in range(len(it))]
    ax1.bar(x, walk, bottom=bottom2, color="#ff7f0e", label="Walk (пешком)")

    ax1.set_title("Доли режимов по итерациям", fontsize=13)
    ax1.set_ylabel("Процент", fontsize=11)
    ax1.set_xlabel("Итерации", fontsize=11)
    ax1.set_ylim(0, 1.0)
    ax1.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax1.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])

    # Show sparse x ticks to keep readable for 0..100.
    step = 10 if len(it) > 20 else 1
    xticks = [k for k, i in enumerate(it) if i % step == 0]
    ax1.set_xticks(xticks)
    ax1.set_xticklabels([str(it[k]) for k in xticks])
    ax1.legend(loc="upper left", fontsize=10, frameon=False)

    # Score line.
    ax2.plot(it, avg, color="#1f77b4", linewidth=2.5)
    ax2.set_title("Средняя полезность агентов", fontsize=13)
    ax2.set_ylabel("Балл полезности", fontsize=11)
    ax2.set_xlabel("Итерации", fontsize=11)
    ax2.grid(True, alpha=0.35)

    # Annotate first and last (запятая как десятичный разделитель; отрицательные — с минусом).
    def _fmt_utility(v: float) -> str:
        s = f"{v:.1f}".replace(".", ",")
        return s.replace("-", "−")  # минус U+2212 для читаемости

    if it:
        ax2.annotate(_fmt_utility(avg[0]), (it[0], avg[0]), textcoords="offset points", xytext=(6, -10))
        ax2.annotate(_fmt_utility(avg[-1]), (it[-1], avg[-1]), textcoords="offset points", xytext=(6, -10))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(args.out)
    plt.close(fig)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()

