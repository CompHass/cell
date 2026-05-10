import json
import os
import sys
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert

# Add parent dir to path so we can import backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.database import init_db, SessionLocal
from backend.models import Group, Person, Event, Attendance

def migrate():
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    try:
        events_path = os.path.join("artifacts", "extract", "event_summary.json")
        attendance_path = os.path.join("artifacts", "extract", "attendance_rows.ndjson")
        
        events_data = []
        if os.path.exists(events_path):
            with open(events_path, "r", encoding="utf-8") as f:
                try:
                    events_data = json.load(f)
                except json.JSONDecodeError:
                    print("Failed to decode events JSON.")
                    
        attendance_data = []
        if os.path.exists(attendance_path):
            with open(attendance_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        attendance_data.append(json.loads(line))
        
        if not events_data and not attendance_data:
            print("No data found to migrate. Migration completed.")
            return

        # Simple grouping structure if needed
        # We need group_id. We'll extract group_id from attendance records if it exists, or provide a default "default_group".
        
        # Load group names from per-group JSON artifacts (group_<id>.json) or fallback to group.json
        group_names = {}
        extract_dir = os.path.join("artifacts", "extract")

        def _load_group_entry(gj):
            """Extract {id: name} from a single group JSON object."""
            data = gj.get("data") if isinstance(gj, dict) else None
            if not data:
                return
            # Handle array (multi-group group.json)
            if isinstance(data, list):
                for item in data:
                    gid = item.get("id")
                    attrs = item.get("attributes") or {}
                    gname = attrs.get("name") or attrs.get("nickname")
                    if gid and gname:
                        group_names[gid] = gname
            else:
                gid = data.get("id")
                attrs = (data.get("attributes") or {})
                gname = attrs.get("name") or attrs.get("nickname")
                if gid and gname:
                    group_names[gid] = gname

        # Prefer per-group files written by extract.py
        import glob as _glob
        per_group_files = _glob.glob(os.path.join(extract_dir, "group_*.json"))
        if per_group_files:
            for path in per_group_files:
                with open(path, "r", encoding="utf-8") as f:
                    _load_group_entry(json.load(f))
        else:
            # Fallback: legacy single group.json
            group_json_path = os.path.join(extract_dir, "group.json")
            if os.path.exists(group_json_path):
                with open(group_json_path, "r", encoding="utf-8") as f:
                    _load_group_entry(json.load(f))

        print("Upserting groups...")
        unique_groups = set(row.get("group_id", "default_group") for row in attendance_data)
        for g_id in unique_groups:
            g_name = group_names.get(g_id, g_id)
            stmt = insert(Group).values(id=g_id, name=g_name)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(name=stmt.excluded.name)
            )
            db.execute(stmt)
            
        print("Upserting persons...")
        # Load is_member from persons.ndjson if available
        persons_path = os.path.join("artifacts", "extract", "persons.ndjson")
        person_membership: dict[str, bool] = {}
        if os.path.exists(persons_path):
            with open(persons_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        p = json.loads(line)
                        person_membership[p["id"]] = bool(p.get("is_member", True))

        for row in attendance_data:
            p_id = str(row.get("person_id", ""))
            if not p_id: continue
            name = row.get("person_name", "Unknown")
            g_id = row.get("group_id", "default_group")
            is_mem = person_membership.get(p_id, True)  # default True if not in persons.ndjson

            stmt = insert(Person).values(id=p_id, name=name, group_id=g_id, is_member=is_mem)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(name=stmt.excluded.name, group_id=stmt.excluded.group_id,
                          is_member=stmt.excluded.is_member)
            )
            db.execute(stmt)
            
        print("Upserting events...")
        # Get group_id per event from attendance if possible
        event_to_group = {}
        for row in attendance_data:
            e_id = str(row.get("event_id", ""))
            g_id = row.get("group_id", "default_group")
            if e_id and e_id not in event_to_group:
                event_to_group[e_id] = g_id
                
        for ev in events_data:
            e_id = str(ev.get("event_id", ""))
            if not e_id: continue
            date_str = ev.get("event_date", ev.get("date", ""))
            dt = datetime.now()
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    pass
                    
            name = ev.get("name", "Unknown Event")
            g_id = event_to_group.get(e_id, "default_group")
            
            stmt = insert(Event).values(id=e_id, date=dt, name=name, group_id=g_id)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(date=stmt.excluded.date, name=stmt.excluded.name, group_id=stmt.excluded.group_id)
            )
            db.execute(stmt)
            
        print("Upserting attendance...")
        for row in attendance_data:
            e_id = str(row.get("event_id", ""))
            p_id = str(row.get("person_id", ""))
            if not e_id or not p_id: continue
            status = row.get("status", "unknown")
            g_id = row.get("group_id", "default_group")
            
            stmt = insert(Attendance).values(event_id=e_id, person_id=p_id, status=status, group_id=g_id)
            stmt = stmt.on_conflict_do_update(
                index_elements=['event_id', 'person_id'],
                set_=dict(status=stmt.excluded.status, group_id=stmt.excluded.group_id)
            )
            db.execute(stmt)
            
        db.commit()
        print("Migration completed.")
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
