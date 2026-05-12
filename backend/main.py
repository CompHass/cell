from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta, date as _date
from collections import defaultdict
from backend.database import get_db
from backend.models import Group, Person, Event, Attendance

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Membership logic (frequency-based, ignores Celulain is_member field)
#
# Active member = had at least 1 presence in last 90 days
#                 AND no 5+ consecutive absences in last 90 days
# Dropout       = 5+ consecutive absences in last 90 days (within members who
#                 were ever present in last 90 days)
# Non-member    = no presence in last 90 days → excluded from all views
#
# Valid event   = at least 1 person was present (cancelled meetings excluded)
# ---------------------------------------------------------------------------

# ── Week helpers (Phase 9) ────────────────────────────────────────────
def _get_monday(d: _date) -> _date:
    """Return the Monday of the week containing d (Mon=0, Sun=6)."""
    return d - timedelta(days=d.weekday())


def _last_sunday(today: _date) -> _date:
    """Return the most recent Sunday (UTC). Returns today if today is Sunday."""
    return today - timedelta(days=(today.weekday() + 1) % 7)


def _all_weeks_since(first_event_dt: datetime, ref_sunday: _date):
    """
    Yield (monday: _date, sunday: _date) for every Mon–Sun week from
    the week containing first_event_dt through the week ending ref_sunday.
    """
    start = _get_monday(first_event_dt.date() if hasattr(first_event_dt, "date") else first_event_dt)
    end   = _get_monday(ref_sunday)
    cur   = start
    while cur <= end:
        yield cur, cur + timedelta(days=6)
        cur += timedelta(weeks=1)


def _get_valid_event_ids(db: Session, active_groups: list[str] = None) -> set[str]:
    """Return event IDs that have at least one 'present' attendance record."""
    q = db.query(Attendance.event_id).filter(Attendance.status == "present")
    if active_groups:
        q = q.filter(Attendance.group_id.in_(active_groups))
    return {r.event_id for r in q.all()}

def _compute_active_members(db: Session, active_groups: list[str]) -> set[str]:
    """
    Return set of person_ids considered active members based on attendance
    in the last 90 days:
      - had >= 1 presence in last 90 days
      - did NOT have 5+ consecutive absences at the END of their last-90-days history
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=90)
    valid_ids = _get_valid_event_ids(db, active_groups)

    eq = db.query(Event).filter(Event.date >= cutoff).order_by(Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    recent_events = [e for e in eq.all() if e.id in valid_ids]
    if not recent_events:
        return set()

    recent_ids = {e.id for e in recent_events}
    event_order = {e.id: i for i, e in enumerate(recent_events)}

    aq = db.query(Attendance).filter(Attendance.event_id.in_(recent_ids))
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    person_evs: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for r in rows:
        idx = event_order.get(r.event_id)
        if idx is None:
            continue
        person_evs[r.person_id].append((idx, r.status))

    active = set()
    for pid, evs in person_evs.items():
        evs_sorted = sorted(evs, key=lambda x: x[0])
        # Must have at least 1 presence
        if not any(s == "present" for _, s in evs_sorted):
            continue
        # Consecutive absent streak from end
        streak = 0
        for _, s in reversed(evs_sorted):
            if s == "absent":
                streak += 1
            else:
                break
        if streak >= 5:
            continue  # dropout — excluded from active members
        active.add(pid)

    return active


def _compute_dropouts(db: Session, active_groups: list[str]) -> list[dict]:
    """
    Members who had >= 1 presence in last 90 days but have 5+ consecutive
    absences at the end of their last-90-days history.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=90)
    valid_ids = _get_valid_event_ids(db, active_groups)

    eq = db.query(Event).filter(Event.date >= cutoff).order_by(Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    recent_events = [e for e in eq.all() if e.id in valid_ids]
    if not recent_events:
        return []

    recent_ids = {e.id for e in recent_events}
    event_order = {e.id: i for i, e in enumerate(recent_events)}
    event_dates = {e.id: e.date for e in recent_events}

    # All-time events for last_seen
    eq_all = db.query(Event).order_by(Event.date)
    if active_groups:
        eq_all = eq_all.filter(Event.group_id.in_(active_groups))
    all_events = [e for e in eq_all.all() if e.id in valid_ids]
    all_event_dates = {e.id: e.date for e in all_events}

    aq = db.query(Attendance).filter(Attendance.event_id.in_(recent_ids))
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    # All attendance for last_seen calculation
    aq_all = db.query(Attendance)
    if active_groups:
        aq_all = aq_all.filter(Attendance.group_id.in_(active_groups))
    all_rows = aq_all.all()

    person_evs: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for r in rows:
        idx = event_order.get(r.event_id)
        if idx is None:
            continue
        person_evs[r.person_id].append((idx, r.status))

    person_all_present: dict[str, list] = defaultdict(list)
    for r in all_rows:
        if r.status == "present" and r.event_id in all_event_dates:
            person_all_present[r.person_id].append(all_event_dates[r.event_id])

    # Load person names
    pq = db.query(Person)
    if active_groups:
        pq = pq.join(Attendance, Attendance.person_id == Person.id).filter(
            Attendance.group_id.in_(active_groups)
        ).distinct()
    person_names = {p.id: p.name for p in pq.all()}

    result = []
    for pid, evs in person_evs.items():
        evs_sorted = sorted(evs, key=lambda x: x[0])
        # Must have at least 1 presence in last 90 days
        if not any(s == "present" for _, s in evs_sorted):
            continue
        # Consecutive absent streak from end
        streak = 0
        for _, s in reversed(evs_sorted):
            if s == "absent":
                streak += 1
            else:
                break
        if streak < 5:
            continue

        present_dates = person_all_present.get(pid, [])
        last_seen = max(present_dates).date().isoformat() if present_dates else None
        result.append({
            "id":             pid,
            "name":           person_names.get(pid, pid),
            "dropout_streak": streak,
            "total_present":  len(present_dates),
            "last_seen":      last_seen,
        })

    result.sort(key=lambda x: -x["dropout_streak"])
    return result


@app.get("/health")
def healthcheck():
    return {"status": "healthy"}

@app.get("/api/groups")
def list_groups(db: Session = Depends(get_db)):
    groups = db.query(Group).all()
    return [{"id": g.id, "name": g.name} for g in groups]

@app.get("/api/members")
def list_members(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    """Active members only (frequency-based), optionally filtered by group."""
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    if not member_ids:
        return []
    persons = db.query(Person).filter(Person.id.in_(member_ids)).order_by(Person.name).all()
    return [{"id": p.id, "name": p.name} for p in persons]


def _apply_common_filters(q, group_id, person_id, date_from, date_to, person_name):
    active_groups = [g for g in group_id if g and g != "all"]
    if active_groups:
        q = q.filter(Attendance.group_id.in_(active_groups))
    if person_id:
        q = q.filter(Person.id.in_(person_id))
    if date_from:
        q = q.filter(Event.date >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(Event.date <= datetime.fromisoformat(date_to))
    if person_name:
        q = q.filter(Person.name.ilike(f"%{person_name}%"))
    return q


@app.get("/api/top-absent")
def top_absent(
    group_id: list[str] = Query(default=[]),
    person_id: list[str] = Query(default=[]),
    date_from: str = Query(None),
    date_to: str = Query(None),
    person_name: str = Query(None),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    if not member_ids:
        return {"items": []}

    valid_ids = _get_valid_event_ids(db, active_groups)
    q = (
        db.query(Person.name, func.count(Attendance.event_id).label("absences"))
        .join(Attendance, Attendance.person_id == Person.id)
        .join(Event, Event.id == Attendance.event_id)
        .filter(Attendance.status == "absent")
        .filter(Attendance.event_id.in_(valid_ids))
        .filter(Person.id.in_(member_ids))
    )
    q = _apply_common_filters(q, group_id, person_id, date_from, date_to, person_name)
    results = q.group_by(Person.name).order_by(func.count(Attendance.event_id).desc()).limit(10).all()
    return {"items": [{"name": r.name, "count": r.absences} for r in results]}


@app.get("/api/attendance-trend")
def attendance_trend(
    group_id: list[str] = Query(default=[]),
    date_from: str = Query(None),
    date_to: str = Query(None),
    person_name: str = Query(None),
    db: Session = Depends(get_db),
):
    """Presença % média por semana do mês — apenas membros ativos."""
    import math

    active_groups = [g for g in group_id if g and g != "all"]
    valid_ids = _get_valid_event_ids(db, active_groups)
    member_ids = _compute_active_members(db, active_groups)

    q = (
        db.query(
            Event.date,
            func.sum(case((Attendance.status == "present", 1), else_=0)).label("present"),
            func.sum(case((Attendance.status == "absent",  1), else_=0)).label("absent"),
        )
        .join(Attendance, Attendance.event_id == Event.id)
        .join(Person, Person.id == Attendance.person_id)
        .filter(Attendance.event_id.in_(valid_ids))
    )
    if member_ids:
        q = q.filter(Person.id.in_(member_ids))
    if active_groups:
        q = q.filter(Attendance.group_id.in_(active_groups))
    if date_from:
        q = q.filter(Event.date >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(Event.date <= datetime.fromisoformat(date_to))
    if person_name:
        q = q.filter(Person.name.ilike(f"%{person_name}%"))

    results = q.group_by(Event.date).order_by(Event.date).all()

    buckets: dict[int, list[float]] = defaultdict(list)
    for row in results:
        d = row.date if hasattr(row.date, 'day') else row.date.date()
        week_of_month = min(math.ceil(d.day / 7), 4)
        total = (row.present or 0) + (row.absent or 0)
        if total > 0:
            buckets[week_of_month].append(round((row.present / total) * 100, 1))

    labels = ["1ª semana", "2ª semana", "3ª semana", "4ª semana"]
    rates  = [round(sum(buckets[i]) / len(buckets[i]), 1) if buckets[i] else 0 for i in range(1, 5)]
    counts = [len(buckets[i]) for i in range(1, 5)]
    return {"labels": labels, "rates": rates, "counts": counts}


@app.get("/api/attendance-by-week")
def attendance_by_week(
    group_id: list[str] = Query(default=[]),
    person_id: list[str] = Query(default=[]),
    date_from: str = Query(None),
    date_to: str = Query(None),
    person_name: str = Query(None),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    valid_ids = _get_valid_event_ids(db, active_groups)

    q = (
        db.query(
            func.extract("week", Event.date).label("week"),
            func.sum(case((Attendance.status == "present", 1), else_=0)).label("present"),
            func.sum(case((Attendance.status == "absent", 1), else_=0)).label("absent"),
        )
        .join(Attendance, Attendance.event_id == Event.id)
        .join(Person, Person.id == Attendance.person_id)
        .filter(Attendance.event_id.in_(valid_ids))
    )
    if member_ids:
        q = q.filter(Person.id.in_(member_ids))
    q = _apply_common_filters(q, group_id, person_id, date_from, date_to, person_name)
    results = q.group_by(func.extract("week", Event.date)).order_by("week").all()
    weeks   = [f"Sem {int(r.week)}" for r in results]
    present = [int(r.present) for r in results]
    absent  = [int(r.absent)  for r in results]
    return {"weeks": weeks, "present": present, "absent": absent}


@app.get("/api/top-present")
def top_present(
    group_id: list[str] = Query(default=[]),
    person_id: list[str] = Query(default=[]),
    date_from: str = Query(None),
    date_to: str = Query(None),
    person_name: str = Query(None),
    db: Session = Depends(get_db),
):
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    if not member_ids:
        return {"items": []}

    valid_ids = _get_valid_event_ids(db, active_groups)
    q = (
        db.query(Person.name, func.count(Attendance.event_id).label("presences"))
        .join(Attendance, Attendance.person_id == Person.id)
        .join(Event, Event.id == Attendance.event_id)
        .filter(Attendance.status == "present")
        .filter(Attendance.event_id.in_(valid_ids))
        .filter(Person.id.in_(member_ids))
    )
    q = _apply_common_filters(q, group_id, person_id, date_from, date_to, person_name)
    results = q.group_by(Person.name).order_by(func.count(Attendance.event_id).desc()).limit(10).all()
    return {"items": [{"name": r.name, "count": r.presences} for r in results]}


@app.get("/api/member-status")
def member_status(
    group_id: list[str] = Query(default=[]),
    inactive_threshold: int = Query(5),
    db: Session = Depends(get_db),
):
    """
    Per-member status — apenas membros ativos (freq-based).
    Dropout = 5+ faltas consecutivas nos últimos 90 dias.
    """
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    valid_ids = _get_valid_event_ids(db, active_groups)

    eq = db.query(Event).order_by(Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    all_events = [e for e in eq.all() if e.id in valid_ids]
    event_order = {e.id: i for i, e in enumerate(all_events)}
    event_dates = {e.id: e.date for e in all_events}

    now = datetime.utcnow()
    cutoff_2m = now - timedelta(days=60)
    cutoff_3m = now - timedelta(days=90)

    recent_2m_ids = {e.id for e in all_events if e.date >= cutoff_2m}
    recent_3m_ids = {e.id for e in all_events if e.date >= cutoff_3m}

    aq = db.query(Attendance)
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    pq = db.query(Person)
    if active_groups:
        pq = pq.join(Attendance, Attendance.person_id == Person.id).filter(
            Attendance.group_id.in_(active_groups)
        ).distinct()
    # Only active members
    persons = {p.id: p.name for p in pq.all() if p.id in member_ids}

    person_events: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for row in rows:
        if row.person_id not in persons:
            continue
        idx = event_order.get(row.event_id)
        if idx is None:
            continue
        person_events[row.person_id].append((idx, row.event_id, row.status))

    result = []
    last4_events = [e.id for e in all_events[-4:]] if all_events else []

    for pid, name in persons.items():
        evs = sorted(person_events.get(pid, []), key=lambda x: x[0])
        if not evs:
            continue

        present_count = sum(1 for _, _, s in evs if s == "present")
        absent_count  = sum(1 for _, _, s in evs if s == "absent")
        total         = len(evs)
        rate          = round(present_count / total, 3) if total else 0.0

        # Streak: last-2-months events
        evs_2m = [(idx, eid, s) for idx, eid, s in evs if eid in recent_2m_ids]
        streak = 0
        for _, eid, s in reversed(evs_2m if evs_2m else evs):
            if streak == 0:
                streak = 1 if s == "present" else -1
            elif s == "present" and streak > 0:
                streak += 1
            elif s == "absent" and streak < 0:
                streak -= 1
            else:
                break

        # Best consecutive present streak (all time)
        best = cur = 0
        for _, _, s in evs:
            if s == "present":
                cur += 1
                best = max(best, cur)
            else:
                cur = 0

        ev_status_map = {eid: s for _, eid, s in evs}
        dots = [ev_status_map.get(eid, "none") for eid in last4_events]

        first_seen = event_dates.get(evs[0][1])
        last_seen  = event_dates.get(evs[-1][1])

        absent_streak_2m = abs(streak) if streak < 0 else 0
        inactive = absent_streak_2m >= inactive_threshold

        # Risk
        if inactive:
            risk = "inactive"
        elif streak <= -3:
            risk = "critical"
        elif rate < 0.5 and total >= 4:
            risk = "warning"
        elif total < 4:
            risk = "new"
        else:
            risk = "ok"

        result.append({
            "id":              pid,
            "name":            name,
            "present":         present_count,
            "absent":          absent_count,
            "total":           total,
            "rate":            rate,
            "streak":          streak,
            "best_streak":     best,
            "qualified":       best >= 3,
            "consecutive_now": streak if streak > 0 else 0,
            "dots":            dots,
            "risk":            risk,
            "inactive":        inactive,
            "first_seen":      first_seen.date().isoformat() if first_seen else None,
            "last_seen":       last_seen.date().isoformat()  if last_seen  else None,
        })

    risk_order = {"critical": 0, "warning": 1, "new": 2, "ok": 3, "inactive": 9}
    result.sort(key=lambda x: (risk_order.get(x["risk"], 9), x["name"]))
    return result


@app.get("/api/dropouts")
def dropouts(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    """
    Pessoas com >= 1 presença nos últimos 90 dias MAS com 3+ faltas consecutivas
    ao final desse período — estão deixando de participar.
    """
    active_groups = [g for g in group_id if g and g != "all"]
    return _compute_dropouts(db, active_groups)


@app.get("/api/at-risk")
def at_risk(
    group_id: list[str] = Query(default=[]),
    alert_threshold: int = Query(3),
    inactive_threshold: int = Query(5),
    db: Session = Depends(get_db),
):
    """Membros ativos com absent streak >= alert_threshold mas < inactive_threshold."""
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    valid_ids = _get_valid_event_ids(db, active_groups)

    eq = db.query(Event).order_by(Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    all_events = [e for e in eq.all() if e.id in valid_ids]
    event_order = {e.id: i for i, e in enumerate(all_events)}
    event_dates = {e.id: e.date for e in all_events}

    aq = db.query(Attendance)
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    pq = db.query(Person)
    if active_groups:
        pq = pq.join(Attendance, Attendance.person_id == Person.id).filter(
            Attendance.group_id.in_(active_groups)
        ).distinct()
    persons = {p.id: p.name for p in pq.all() if p.id in member_ids}

    person_events: dict[str, list] = defaultdict(list)
    for row in rows:
        if row.person_id not in persons:
            continue
        idx = event_order.get(row.event_id)
        if idx is None:
            continue
        person_events[row.person_id].append((idx, row.event_id, row.status))

    result = []
    for pid, name in persons.items():
        evs = sorted(person_events.get(pid, []), key=lambda x: x[0])
        if not evs:
            continue

        streak = 0
        for _, eid, s in reversed(evs):
            if s == "absent":
                streak += 1
            else:
                break

        if alert_threshold <= streak < inactive_threshold:
            present_count = sum(1 for _, _, s in evs if s == "present")
            present_dates = [event_dates[eid] for _, eid, s in evs if s == "present" and eid in event_dates]
            last_seen = max(present_dates).date().isoformat() if present_dates else None
            result.append({
                "id":            pid,
                "name":          name,
                "absent_streak": streak,
                "total_present": present_count,
                "last_seen":     last_seen,
            })

    result.sort(key=lambda x: -x["absent_streak"])
    return result


@app.get("/api/pending-meetings")
def pending_meetings(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    """
    Return groups that are missing a weekly meeting registration for one or
    more Mon–Sun weeks from their first event through last Sunday (UTC).

    A week is considered 'registered' when ANY event row exists for the group
    within that Monday–Sunday range (D-03). Full history per group (D-04/D-05).

    Response: { count: int, groups: [ { id, name, missing_weeks: ["YYYY-Www", ...] } ] }
    """
    active_groups = [g for g in group_id if g and g != "all"]

    # 1. Groups in scope
    gq = db.query(Group)
    if active_groups:
        gq = gq.filter(Group.id.in_(active_groups))
    groups = gq.all()
    if not groups:
        return {"count": 0, "groups": []}

    # 2. First event date per group (one aggregation query)
    feq = (
        db.query(Event.group_id, func.min(Event.date).label("first_date"))
        .group_by(Event.group_id)
    )
    if active_groups:
        feq = feq.filter(Event.group_id.in_(active_groups))
    first_dates: dict[str, datetime] = {r.group_id: r.first_date for r in feq.all()}

    # 3. Reference Sunday (UTC, consistent with rest of codebase)
    today = datetime.utcnow().date()
    ref_sunday = _last_sunday(today)

    # 4. Build covered set: (group_id, monday_of_week) for all event rows
    eq = db.query(Event.group_id, Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    covered: set[tuple[str, _date]] = set()
    for row in eq.all():
        d: _date = row.date.date() if hasattr(row.date, "date") else row.date
        covered.add((row.group_id, _get_monday(d)))

    # 5. Find missing weeks per group
    result = []
    for g in groups:
        first_dt = first_dates.get(g.id)
        if not first_dt:
            continue  # group has no events at all — skip (A2 assumption)

        missing: list[str] = []
        for monday, _ in _all_weeks_since(first_dt, ref_sunday):
            if (g.id, monday) not in covered:
                # Format as ISO week label: YYYY-Www
                iso_year, iso_week, _ = monday.isocalendar()
                missing.append(f"{iso_year}-W{iso_week:02d}")

        if missing:
            result.append({"id": g.id, "name": g.name, "missing_weeks": missing})

    return {"count": len(result), "groups": result}


@app.get("/api/person-week-heatmap")
def person_week_heatmap(
    group_id: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    """
    Taxa de presença por pessoa × semana do mês (1ª–4ª).
    Apenas membros ativos. Retorna lista ordenada por nome.
    """
    import math

    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    if not member_ids:
        return {"persons": [], "labels": ["1ª", "2ª", "3ª", "4ª"]}

    valid_ids = _get_valid_event_ids(db, active_groups)
    eq = db.query(Event)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    events = [e for e in eq.all() if e.id in valid_ids]
    event_dates = {e.id: e.date for e in events}

    aq = db.query(Attendance).filter(Attendance.person_id.in_(member_ids))
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    # Load names
    persons = db.query(Person).filter(Person.id.in_(member_ids)).all()
    names = {p.id: p.name for p in persons}

    # Aggregate: person_id -> week -> (present, total)
    from collections import defaultdict
    data: dict[str, dict[int, tuple[int, int]]] = defaultdict(lambda: defaultdict(lambda: (0, 0)))
    for r in rows:
        d = event_dates.get(r.event_id)
        if d is None:
            continue
        week = min(math.ceil(d.day / 7), 4)
        pr, tot = data[r.person_id][week]
        tot += 1
        if r.status == "present":
            pr += 1
        data[r.person_id][week] = (pr, tot)

    result = []
    for pid in member_ids:
        name = names.get(pid, pid)
        weeks = []
        for w in range(1, 5):
            pr, tot = data[pid].get(w, (0, 0))
            rate = round((pr / tot) * 100, 1) if tot > 0 else None
            weeks.append(rate)
        result.append({"name": name, "weeks": weeks})
    result.sort(key=lambda x: x["name"].lower())
    return {"persons": result, "labels": ["1ª", "2ª", "3ª", "4ª"]}


@app.get("/api/gone-silent")
def gone_silent(
    group_id: list[str] = Query(default=[]),
    weeks: int = Query(3),
    db: Session = Depends(get_db),
):
    """Membros ativos que não apareceram nos últimos N eventos."""
    active_groups = [g for g in group_id if g and g != "all"]
    member_ids = _compute_active_members(db, active_groups)
    valid_ids = _get_valid_event_ids(db, active_groups)

    eq = db.query(Event).order_by(Event.date)
    if active_groups:
        eq = eq.filter(Event.group_id.in_(active_groups))
    all_events = [e for e in eq.all() if e.id in valid_ids]
    if not all_events:
        return []

    cutoff_events = {e.id for e in all_events[-weeks:]}
    all_event_ids = {e.id for e in all_events}
    event_dates   = {e.id: e.date for e in all_events}

    aq = db.query(Attendance)
    if active_groups:
        aq = aq.filter(Attendance.group_id.in_(active_groups))
    rows = aq.all()

    person_rows: dict[str, list] = defaultdict(list)
    for row in rows:
        person_rows[row.person_id].append(row)

    pq = db.query(Person)
    if active_groups:
        pq = pq.join(Attendance, Attendance.person_id == Person.id).filter(
            Attendance.group_id.in_(active_groups)
        ).distinct()

    result = []
    for p in pq.all():
        if p.id not in member_ids:
            continue
        evs = person_rows.get(p.id, [])
        if not evs:
            continue

        present_total = sum(1 for r in evs if r.status == "present")
        if present_total == 0:
            continue

        in_recent = any(r.event_id in cutoff_events and r.status == "present" for r in evs)
        if in_recent:
            continue

        present_dates = [event_dates[r.event_id] for r in evs
                         if r.status == "present" and r.event_id in event_dates]
        if not present_dates:
            continue
        last_seen = max(present_dates)

        all_sorted = sorted(
            [r for r in evs if r.event_id in all_event_ids],
            key=lambda r: event_dates.get(r.event_id, datetime.min)
        )
        streak = 0
        for r in reversed(all_sorted):
            if r.status == "absent":
                streak += 1
            else:
                break

        result.append({
            "id":            p.id,
            "name":          p.name,
            "last_seen":     last_seen.date().isoformat(),
            "absent_streak": streak,
            "total_present": present_total,
        })

    result.sort(key=lambda x: x["last_seen"])
    return result


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
