import json
import sys
from pathlib import Path

def verify_attendance_rows(file_path):
    required_keys = {'event_id', 'event_date', 'event_name', 'person_id', 'person_name', 'status', 'group_id'}
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return False
        
    with open(path, 'r') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                missing = required_keys - set(row.keys())
                if missing:
                    print(f"Row {i+1} missing keys: {missing}")
                    return False
            except json.JSONDecodeError:
                print(f"Invalid JSON at line {i+1}")
                return False
    print(f"Verified {file_path} successfully.")
    return True

def verify_event_summary(file_path):
    required_keys = {'event_id', 'attendees_count'}
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return False
        
    with open(path, 'r') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                summaries = data
            else:
                summaries = [data]
                
            for i, summary in enumerate(summaries):
                missing = required_keys - set(summary.keys())
                if missing:
                    print(f"Summary {i+1} missing keys: {missing}")
                    return False
            print(f"Verified {file_path} successfully.")
            return True
        except json.JSONDecodeError:
            print(f"Invalid JSON in {file_path}")
            return False

def main():
    artifacts_dir = Path('artifacts/extract')
    attendance_file = artifacts_dir / 'attendance_rows.ndjson'
    summary_file = artifacts_dir / 'event_summary.json'
    
    success = True
    if not verify_attendance_rows(attendance_file):
        success = False
    
    if not verify_event_summary(summary_file):
        success = False
        
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
