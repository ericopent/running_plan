"""Baixa as atividades do Garmin e cruza com o plano.

Grava data/activities.json, sem trajeto GPS (o repositório é público).
Teste sem Garmin:  python scripts/fetch_garmin.py --from-file exemplo.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / "data" / "plan.json").read_text(encoding="utf-8"))

RUN_TYPES = {"running", "treadmill_running", "trail_running", "track_running", "indoor_running"}
WALK_TYPES = {"walking", "casual_walking", "speed_walking", "hiking"}
KEEP = ["activityId", "activityName", "startTimeLocal", "duration", "movingDuration",
        "distance", "averageHR", "maxHR", "averageSpeed", "calories", "elevationGain"]


def slim(a: dict) -> dict:
    out = {k: a.get(k) for k in KEEP}
    out["type"] = (a.get("activityType") or {}).get("typeKey", "other")
    return out


def pace_str(speed_ms: float | None) -> str | None:
    if not speed_ms:
        return None
    sec = round(1000 / speed_ms)
    return f"{sec // 60}:{sec % 60:02d}"


def match(acts: list[dict], today: date) -> dict:
    by_day: dict[str, list[dict]] = {}
    for a in acts:
        by_day.setdefault(a["startTimeLocal"][:10], []).append(a)

    results = {}
    for s in PLAN["sessions"]:
        d = date.fromisoformat(s["date"])
        wanted = RUN_TYPES | WALK_TYPES if s["kind"] == "run" else WALK_TYPES | RUN_TYPES
        cands = [a for a in by_day.get(s["date"], []) if a["type"] in wanted]
        if not cands:
            status = "pendente" if d >= today else "pulado"
            results[s["id"]] = {"status": status}
            continue
        a = max(cands, key=lambda x: x.get("duration") or 0)
        planned = s["total_minutes"] * 60
        dur = a.get("movingDuration") or a.get("duration") or 0
        ratio = dur / planned if planned else 1
        if s["kind"] == "run" and a["type"] not in RUN_TYPES:
            status = "adaptado"
        else:
            status = "feito" if ratio >= 0.8 else "adaptado"
        results[s["id"]] = {
            "status": status,
            "activityId": a["activityId"],
            "name": a.get("activityName"),
            "type": a["type"],
            "minutes": round(dur / 60, 1),
            "km": round((a.get("distance") or 0) / 1000, 2),
            "pace": pace_str(a.get("averageSpeed")),
            "avgHR": a.get("averageHR"),
            "maxHR": a.get("maxHR"),
            "pct_planned": round(ratio * 100),
        }
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="JSON com atividades no formato do Garmin (teste)")
    ap.add_argument("--today", help="data de referência AAAA-MM-DD (teste)")
    args = ap.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()
    start = (date.fromisoformat(PLAN["sessions"][0]["date"]) - timedelta(days=30)).isoformat()

    if args.from_file:
        raw = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    else:
        from garmin_auth import login
        raw = login().get_activities_by_date(start, today.isoformat())

    acts = [slim(a) for a in raw]
    acts.sort(key=lambda a: a["startTimeLocal"], reverse=True)
    out = {
        "updated": datetime.now().isoformat(timespec="minutes"),
        "sessions": match(acts, today),
        "recent": acts[:30],
    }
    dest = ROOT / "data" / "activities.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    done = sum(1 for r in out["sessions"].values() if r["status"] in ("feito", "adaptado"))
    print(f"{len(acts)} atividades; {done} sessões do plano com treino registrado.")


if __name__ == "__main__":
    main()
