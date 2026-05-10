"""
extract.py — Python port of scripts/extract-attendance.mjs

Authenticates against celula.in via Bearer token and writes all output
artefacts to artifacts/extract/ in the same schema as the Node scripts.
"""

import asyncio
import csv
import io
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Load .env from the repository root (if present)."""
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def extract_token(payload: dict) -> str:
    """Extract Bearer token from an /authenticate response with multiple fallbacks."""
    if not isinstance(payload, dict):
        return ""
    return (
        payload.get("access_token")
        or payload.get("token")
        or (payload.get("data") or {}).get("attributes", {}).get("token")
        or (payload.get("data") or {}).get("token")
        or ""
    )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _json_headers(app_url: str) -> dict:
    return {
        "accept": "application/vnd.api+json",
        "content-type": "application/vnd.api+json",
        "origin": app_url,
        "referer": f"{app_url}/",
    }


def _authed_headers(app_url: str, token: str) -> dict:
    headers = _json_headers(app_url)
    headers["authorization"] = f"Bearer {token}"
    return headers


async def _parse_json_response(response: httpx.Response, context: str) -> dict:
    status = response.status_code
    body = response.text
    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"{context} returned non-JSON body (HTTP {status})."
        )
    if status >= 400:
        raise RuntimeError(
            f"{context} failed (HTTP {status}): {json.dumps(data)[:500]}"
        )
    return data


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

async def authenticate(
    *,
    api_base: str,
    app_url: str,
    email: str,
    password: str,
    account: str,
) -> str:
    """POST /authenticate and return the Bearer token."""
    async with httpx.AsyncClient(headers=_json_headers(app_url), timeout=30) as client:
        response = await client.post(
            f"{api_base}/authenticate",
            json={"username": email, "password": password, "account": account},
        )
    payload = await _parse_json_response(response, "/authenticate")
    token = extract_token(payload)
    if not token:
        raise ValueError(
            "Token not found in /authenticate response. "
            f"Keys present: {list(payload.keys())}"
        )
    return token


# ---------------------------------------------------------------------------
# API fetches
# ---------------------------------------------------------------------------

async def fetch_group_events(
    client: httpx.AsyncClient, api_base: str, group_id: str
) -> dict:
    """GET /v1/groups/{groupId}?include=events"""
    response = await client.get(f"{api_base}/v1/groups/{group_id}?include=events")
    return await _parse_json_response(response, f"/v1/groups/{group_id}")


async def fetch_event_detail(
    client: httpx.AsyncClient, api_base: str, event_id: str
) -> tuple[dict | None, dict | None]:
    """
    GET /v1/group-events/{eventId}?include=attendees,guests,group.
    Returns (event_json, error_summary) — one of the two is None.
    """
    url = f"{api_base}/v1/group-events/{event_id}?include=attendees,guests,group"
    response = await client.get(url)
    status = response.status_code
    if status >= 400:
        err_text = response.text
        return None, {
            "event_id": event_id,
            "status": status,
            "error": err_text[:200],
        }
    data = await _parse_json_response(response, f"/v1/group-events/{event_id}")
    return data, None


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def map_included_people(included: list) -> dict:
    """Return {person_id: full_name} from a JSON:API included array."""
    result: dict[str, str] = {}
    for item in included or []:
        if not isinstance(item, dict) or item.get("type") != "people":
            continue
        attrs = item.get("attributes") or {}
        name = (
            attrs.get("full-name")
            or attrs.get("name")
            or attrs.get("nickname")
            or ""
        )
        result[item["id"]] = name
    return result


def extract_persons_from_group_json(group_json: dict, group_id: str) -> list[dict]:
    """Return list of {id, name, is_member, group_id} from group JSON:API included."""
    result = []
    for item in group_json.get("included") or []:
        if not isinstance(item, dict) or item.get("type") != "people":
            continue
        attrs = item.get("attributes") or {}
        name = (
            attrs.get("full-name")
            or attrs.get("name")
            or attrs.get("nickname")
            or ""
        )
        is_member = bool(attrs.get("is-member", True))
        result.append({
            "id": item["id"],
            "name": name,
            "is_member": is_member,
            "group_id": group_id,
        })
    return result


def to_csv(rows: list[dict], headers: list[str]) -> str:
    """Convert a list of dicts to a CSV string with the given column order."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(h, "") for h in headers])
    # Ensure trailing newline
    value = buf.getvalue()
    if rows and not value.endswith("\n"):
        value += "\n"
    return value


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def extract_group(
    client: httpx.AsyncClient,
    api_base: str,
    group_id: str,
    max_events: int,
    out_dir: Path,
    raw_path: Path,
    row_records: list,
    event_summaries: list,
    group_jsons: list,
    person_records: list,
) -> None:
    """Extract events and attendance for a single group_id, appending into shared lists."""
    group_json = await fetch_group_events(client, api_base, group_id)
    group_jsons.append(group_json)

    # Extract person membership info from group JSON included
    persons = extract_persons_from_group_json(group_json, group_id)
    person_records.extend(persons)
    print(f"   grupo {group_id}: {len(persons)} pessoas extraídas (is_member)")

    event_ids: list[str] = [
        e["id"]
        for e in (
            (group_json.get("data") or {})
            .get("relationships", {})
            .get("events", {})
            .get("data") or []
        )
    ]
    selected_ids = event_ids[-max_events:] if max_events > 0 else event_ids

    print(f"   grupo {group_id}: {len(selected_ids)} eventos")

    for event_id in selected_ids:
        event_json, err = await fetch_event_detail(client, api_base, event_id)
        if err is not None:
            event_summaries.append(err)
            continue

        with raw_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_json, ensure_ascii=False) + "\n")

        event_data = event_json.get("data") or {}
        attrs = event_data.get("attributes") or {}
        rel = event_data.get("relationships") or {}

        attendees: set[str] = {
            p["id"] for p in (rel.get("attendees") or {}).get("data") or []
        }
        guests: set[str] = {
            p["id"] for p in (rel.get("guests") or {}).get("data") or []
        }
        all_people: set[str] = guests | attendees
        people_by_id = map_included_people(event_json.get("included") or [])

        present = 0
        absent = 0
        for person_id in all_people:
            is_present = person_id in attendees
            if is_present:
                present += 1
            else:
                absent += 1
            row_records.append(
                {
                    "event_id": event_id,
                    "event_date": attrs.get("date", ""),
                    "event_name": attrs.get("name", ""),
                    "person_id": person_id,
                    "person_name": people_by_id.get(person_id, ""),
                    "status": "present" if is_present else "absent",
                    "group_id": (rel.get("group") or {}).get("data", {}).get("id")
                    or group_id,
                }
            )

        event_summaries.append(
            {
                "event_id": event_id,
                "event_date": attrs.get("date", ""),
                "event_name": attrs.get("name", ""),
                "attendees_count": present,
                "absentees_inferred_count": absent,
                "people_total": len(all_people),
                "status": 200,
                "group_id": group_id,
            }
        )


async def main() -> None:
    load_env()

    app_url = os.environ.get("CELULA_APP_URL", "https://app.celula.in")
    api_base = os.environ.get("CELULA_API_BASE", "https://api.celula.in").rstrip("/")
    # Support comma-separated list of group IDs
    group_ids_raw = _required("CELULA_GROUP_ID")
    group_ids = [g.strip() for g in group_ids_raw.split(",") if g.strip()]
    max_events = int(os.environ.get("CELULA_MAX_EVENTS", "0") or "0")

    email = os.environ.get("CELULA_EMAIL", "")
    password = os.environ.get("CELULA_PASSWORD", "")
    account = os.environ.get("CELULA_ACCOUNT", "")
    token = os.environ.get("CELULA_TOKEN", "").strip()

    # --- Phase 1/5: authentication ---
    if not token:
        if not (email and password and account):
            raise ValueError(
                "Set CELULA_TOKEN or CELULA_EMAIL/CELULA_PASSWORD/CELULA_ACCOUNT."
            )
        print("1/5 autenticando via /authenticate...")
        token = await authenticate(
            api_base=api_base,
            app_url=app_url,
            email=email,
            password=password,
            account=account,
        )
    else:
        print("1/5 usando token fornecido em CELULA_TOKEN...")

    async with httpx.AsyncClient(
        headers=_authed_headers(app_url, token), timeout=30
    ) as client:

        out_dir = Path("artifacts") / "extract"
        out_dir.mkdir(parents=True, exist_ok=True)

        # --- Phase 2/5: load groups + event IDs ---
        print(f"2/5 carregando {len(group_ids)} grupo(s) e ids de eventos...")

        raw_path = out_dir / "group_events_raw.ndjson"
        raw_path.write_text("", encoding="utf-8")  # truncate / create

        row_records: list[dict] = []
        event_summaries: list[dict] = []
        group_jsons: list[dict] = []
        person_records: list[dict] = []

        # --- Phase 3/5: collect event details for all groups ---
        print("3/5 coletando eventos...")
        for gid in group_ids:
            await extract_group(
                client, api_base, gid, max_events,
                out_dir, raw_path, row_records, event_summaries, group_jsons,
                person_records,
            )

        # Write merged group.json (first group as primary, all appended)
        (out_dir / "group.json").write_text(
            json.dumps(group_jsons[0] if len(group_jsons) == 1 else group_jsons,
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Write per-group files for migrate_history.py compat
        for gid, gj in zip(group_ids, group_jsons):
            (out_dir / f"group_{gid}.json").write_text(
                json.dumps(gj, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    # --- Phase 4/5: write normalised artefacts ---
    print("4/5 gerando artefatos normalizados...")

    (out_dir / "attendance_rows.ndjson").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in row_records)
        + ("\n" if row_records else ""),
        encoding="utf-8",
    )

    # Deduplicate persons: prefer is_member=True if same person appears in multiple groups
    seen_persons: dict[str, dict] = {}
    for p in person_records:
        pid = p["id"]
        if pid not in seen_persons or p["is_member"]:
            seen_persons[pid] = p
    (out_dir / "persons.ndjson").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in seen_persons.values())
        + ("\n" if seen_persons else ""),
        encoding="utf-8",
    )
    print(f"   {len(seen_persons)} pessoas únicas salvas em persons.ndjson")

    (out_dir / "event_summary.json").write_text(
        json.dumps(event_summaries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    (out_dir / "attendance.csv").write_text(
        to_csv(
            row_records,
            ["event_id", "event_date", "event_name", "person_id", "person_name", "status", "group_id"],
        ),
        encoding="utf-8",
    )

    # Person-level summary
    person_map: dict[str, dict] = {}
    for row in row_records:
        pid = row["person_id"]
        entry = person_map.setdefault(
            pid,
            {
                "person_id": pid,
                "person_name": row["person_name"],
                "present_count": 0,
                "absent_count": 0,
                "total_events": 0,
                "attendance_rate": 0.0,
            },
        )
        if row["status"] == "present":
            entry["present_count"] += 1
        else:
            entry["absent_count"] += 1
        entry["total_events"] += 1

    person_summary = sorted(
        [
            {
                **p,
                "attendance_rate": round(p["present_count"] / p["total_events"], 4)
                if p["total_events"] > 0
                else 0.0,
            }
            for p in person_map.values()
        ],
        key=lambda p: p["attendance_rate"],
        reverse=True,
    )

    (out_dir / "attendance_summary_by_person.csv").write_text(
        to_csv(
            person_summary,
            ["person_id", "person_name", "present_count", "absent_count", "total_events", "attendance_rate"],
        ),
        encoding="utf-8",
    )

    # --- Phase 5/5: done ---
    print("5/5 concluido.")
    print(f"Arquivos: {out_dir.resolve()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
