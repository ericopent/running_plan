"""Envia as próximas sessões de corrida para o Garmin como treinos estruturados
e agenda cada uma no calendário, na data do plano.

Cada passo de corrida leva o pace planejado como alvo e, se hr_cap estiver
definido em config.json, a FC máxima como alvo secundário.

    python scripts/push_garmin.py              # próximos N dias (config.json)
    python scripts/push_garmin.py --dry-run    # só mostra o JSON, sem Garmin
    python scripts/push_garmin.py --all        # todas as sessões futuras
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from garminconnect.workout import (
    CustomHeartRateTarget,
    PaceTarget,
    RunningWorkout,
    WorkoutSegment,
    create_cooldown_step,
    create_recovery_step,
    create_repeat_group,
    create_targeted_distance_interval_step,
    create_targeted_interval_step,
    create_warmup_step,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PLAN = json.loads((ROOT / "data" / "plan.json").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "data" / "pushed.json"
RUNNING = {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1}


def mps(pace: str) -> float:
    m, s = pace.split(":")
    return 1000 / (int(m) * 60 + int(s))


class Builder:
    def __init__(self, session: dict):
        self.s = session
        self.order = 0
        hr_cap = PLAN.get("hr_cap")
        pace = session["pace"]
        self.pace = PaceTarget(lower_limit=mps(pace["slow"]), upper_limit=mps(pace["fast"])) if pace else None
        self.hr = CustomHeartRateTarget(lower_limit=60, upper_limit=hr_cap) if hr_cap else None

    def next(self) -> int:
        self.order += 1
        return self.order

    def step(self, st: dict):
        t = st["type"]
        if t == "warmup":
            return create_warmup_step(st["sec"], self.next())
        if t == "cooldown":
            return create_cooldown_step(st["sec"], self.next())
        if t == "walk":
            return create_recovery_step(st["sec"], self.next())
        if t == "run":
            if "meters" in st:
                return create_targeted_distance_interval_step(
                    st["meters"], self.next(), target=self.pace, secondary_target=self.hr)
            return create_targeted_interval_step(
                st["sec"], self.next(), target=self.pace, secondary_target=self.hr)
        if t == "repeat":
            order = self.next()
            children = [self.step(c) for c in st["steps"]]
            return create_repeat_group(st["n"], children, order)
        raise ValueError(t)

    def workout(self) -> RunningWorkout:
        s = self.s
        d = date.fromisoformat(s["date"])
        name = f"{CONFIG.get('workout_prefix', 'C5K')} S{s['week']} {s['weekday']} {d:%d/%m} - {s['title']}"
        desc = f"Pace {s['pace']['fast']}-{s['pace']['slow']}/km." if s["pace"] else ""
        if PLAN.get("hr_cap"):
            desc += f" Teto de FC {PLAN['hr_cap']} bpm: passou, caminhe."
        if s["note"]:
            desc += " " + s["note"]
        return RunningWorkout(
            workoutName=name[:80],
            estimatedDurationInSecs=int(s["total_minutes"] * 60),
            description=desc.strip()[:500],
            workoutSegments=[WorkoutSegment(
                segmentOrder=1, sportType=RUNNING,
                workoutSteps=[self.step(st) for st in s["steps"]],
            )],
        )


def fingerprint(s: dict) -> str:
    key = json.dumps([s["steps"], s["pace"], PLAN.get("hr_cap"), s["note"]], sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--today")
    args = ap.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()
    horizon = date.max if args.all else today + timedelta(days=int(CONFIG.get("push_days_ahead", 7)))
    todo = [s for s in PLAN["sessions"]
            if s["kind"] == "run" and today <= date.fromisoformat(s["date"]) <= horizon]

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    client = None if args.dry_run else __import__("garmin_auth").login()

    for s in todo:
        fp = fingerprint(s)
        prev = state.get(s["id"])
        if prev and prev.get("fp") == fp:
            print(f"= {s['id']} já está no Garmin")
            continue
        payload = Builder(s).workout().to_dict()
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2) if len(todo) == 1
                  else f"~ {s['id']} {payload['workoutName']} ({len(json.dumps(payload))} bytes)")
            continue
        if prev:  # o plano mudou: atualiza o treino que já existe (mantém o agendamento)
            client.update_workout(prev["workoutId"], payload)
            wid = prev["workoutId"]
            print(f"↻ {s['id']} atualizado")
        else:
            wid = client.upload_workout(payload)["workoutId"]
            client.schedule_workout(wid, s["date"])
            print(f"+ {s['id']} enviado e agendado")
        state[s["id"]] = {"workoutId": wid, "fp": fp}

    if not args.dry_run:
        STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
