"""Gera data/plan.json a partir da tabela do plano.

Edite SESSIONS (ou config.json) e rode:  python scripts/build_plan.py
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

WARMUP_SEC = 5 * 60
COOLDOWN_SEC = 5 * 60

# (semana, data ISO, especificação, pace "m:ss-m:ss" ou None, nota)
# Especificação:
#   "8x(1/2)"     -> 8 repetições de 1 min correndo + 2 min caminhando
#   "run:20"      -> 20 min contínuos
#   "run:5km"     -> 5 km contínuos
#   "walk:20"     -> caminhada de 20 min (não vai para o Garmin)
SESSIONS = [
    (0, "2026-11-05", "walk:20", None, "Depois da musculação. Esteira com 3 a 5% de inclinação ou rua."),
    (0, "2026-11-07", "6x(1/2)", "8:00-8:45", "Primeira corrida. Anote o pace com a FC no teto para calibrar o plano."),
    (1, "2026-11-09", "8x(1/2)", "8:00-8:45", ""),
    (1, "2026-11-12", "walk:20", None, "Caminhada inclinada depois da musculação."),
    (1, "2026-11-14", "8x(1.5/2)", "8:00-8:45", ""),
    (2, "2026-11-16", "7x(1.5/2)", "8:00-8:45", ""),
    (2, "2026-11-19", "walk:25", None, "Caminhada inclinada depois da musculação."),
    (2, "2026-11-21", "6x(2/2)", "8:00-8:45", ""),
    (3, "2026-11-23", "6x(2/2)", "8:00-8:45", ""),
    (3, "2026-11-26", "walk:25", None, "Caminhada inclinada depois da musculação."),
    (3, "2026-11-28", "5x(3/2)", "8:00-8:45", ""),
    (4, "2026-11-30", "5x(3/2)", "7:45-8:30", ""),
    (4, "2026-12-03", "4x(1/1.5)", "8:15-9:00", "Primeira corrida de quinta, depois da musculação."),
    (4, "2026-12-05", "4x(4/2)", "7:45-8:30", ""),
    (5, "2026-12-07", "4x(3/2)", "8:00-8:45", "Semana de recuperação."),
    (5, "2026-12-10", "walk:20", None, "Semana de recuperação."),
    (5, "2026-12-12", "4x(4/2)", "8:00-8:45", "Semana de recuperação."),
    (6, "2026-12-14", "4x(4.5/2)", "7:45-8:30", ""),
    (6, "2026-12-17", "4x(2/1.5)", "8:15-9:00", ""),
    (6, "2026-12-19", "3x(6/2)", "7:45-8:30", ""),
    (7, "2026-12-21", "3x(6/2)", "7:45-8:30", ""),
    (7, "2026-12-24", "walk:20", None, "Opcional (véspera de Natal)."),
    (7, "2026-12-26", "3x(7/2)", "7:45-8:30", ""),
    (8, "2026-12-28", "2x(10/2)", "7:45-8:30", ""),
    (8, "2026-12-31", "3x(3/1)", "8:15-9:00", "Pode pular (réveillon)."),
    (8, "2027-01-02", "2x(12/2)", "7:45-8:30", ""),
    (9, "2027-01-04", "2x(12/2)", "7:45-8:30", ""),
    (9, "2027-01-07", "3x(4/1)", "8:15-9:00", ""),
    (9, "2027-01-09", "run:20", "8:00-8:45", "Primeiro bloco contínuo. Se a FC passar do teto, caminhe 1 min e siga."),
    (10, "2027-01-11", "run:22", "8:00-8:45", ""),
    (10, "2027-01-14", "3x(5/1)", "8:15-9:00", ""),
    (10, "2027-01-16", "run:30", "8:00-8:45", "Marco: 30 minutos contínuos."),
    (11, "2027-01-18", "run:25", "7:45-8:30", ""),
    (11, "2027-01-21", "run:15", "8:15-9:00", ""),
    (11, "2027-01-23", "run:33", "8:00-8:45", ""),
    (12, "2027-01-25", "run:25", "7:45-8:30", ""),
    (12, "2027-01-28", "run:15", "8:15-9:00", "Bem leve, véspera do teste."),
    (12, "2027-01-30", "run:5km", "7:30-8:00", "Meta: 5 km contínuos, no ritmo que for."),
]

WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def pace_to_sec(p: str) -> int:
    m, s = p.split(":")
    return int(m) * 60 + int(s)


def sec_to_pace(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def fmt_min(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x).replace(".", ",")


def parse(spec: str, pace: dict | None) -> tuple[list[dict], float, str, str]:
    """Devolve (passos, minutos correndo, título, tipo)."""
    if spec.startswith("walk:"):
        mins = int(spec.split(":")[1])
        steps = [{"type": "walk", "sec": mins * 60, "label": "Caminhada rápida"}]
        return steps, 0.0, f"Caminhada {mins} min", "walk"

    warm = {"type": "warmup", "sec": WARMUP_SEC, "label": "Aquecimento caminhando"}
    cool = {"type": "cooldown", "sec": COOLDOWN_SEC, "label": "Desaquecimento caminhando"}

    if spec.startswith("run:"):
        val = spec.split(":")[1]
        if val.endswith("km"):
            km = float(val[:-2])
            mid = (pace_to_sec(pace["fast"]) + pace_to_sec(pace["slow"])) / 2
            est_min = round(km * mid / 60)
            main = {"type": "run", "meters": int(km * 1000), "sec": est_min * 60,
                    "label": f"Corrida contínua {fmt_min(km)} km"}
            return [warm, main, cool], float(est_min), f"{fmt_min(km)} km contínuos", "run"
        mins = int(val)
        main = {"type": "run", "sec": mins * 60, "label": f"Corrida contínua {mins} min"}
        return [warm, main, cool], float(mins), f"{mins} min contínuos", "run"

    m = re.fullmatch(r"(\d+)x\(([\d.]+)/([\d.]+)\)", spec)
    if not m:
        raise ValueError(f"especificação inválida: {spec}")
    n, run_m, walk_m = int(m[1]), float(m[2]), float(m[3])
    rep = {
        "type": "repeat",
        "n": n,
        "steps": [
            {"type": "run", "sec": int(run_m * 60), "label": f"Corre {fmt_min(run_m)} min"},
            {"type": "walk", "sec": int(walk_m * 60), "label": f"Caminha {fmt_min(walk_m)} min"},
        ],
    }
    title = f"{n}x ({fmt_min(run_m)} corre / {fmt_min(walk_m)} caminha)"
    return [warm, rep, cool], n * run_m, title, "run"


def total_sec(steps: list[dict]) -> int:
    t = 0
    for s in steps:
        t += s["n"] * total_sec(s["steps"]) if s["type"] == "repeat" else s["sec"]
    return t


def main() -> None:
    offset = int(CONFIG.get("pace_offset_sec", 0))
    out = []
    for week, iso, spec, pace_str, note in SESSIONS:
        d = date.fromisoformat(iso)
        pace = None
        if pace_str:
            fast, slow = pace_str.split("-")
            pace = {
                "fast": sec_to_pace(pace_to_sec(fast) + offset),
                "slow": sec_to_pace(pace_to_sec(slow) + offset),
            }
        steps, run_min, title, kind = parse(spec, pace)
        out.append({
            "id": iso,
            "date": iso,
            "weekday": WEEKDAYS[d.weekday()],
            "week": week,
            "kind": kind,
            "title": title,
            "spec": spec,
            "run_minutes": run_min,
            "total_minutes": round(total_sec(steps) / 60, 1),
            "pace": pace,
            "steps": steps,
            "note": note,
        })

    plan = {
        "name": CONFIG.get("plan_name", "Do zero aos 5 km"),
        "hr_cap": CONFIG.get("hr_cap"),
        "pace_offset_sec": offset,
        "weekly": CONFIG.get("weekly", {}),
        "sessions": out,
    }
    dest = ROOT / "data" / "plan.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(out)} sessões gravadas em {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
