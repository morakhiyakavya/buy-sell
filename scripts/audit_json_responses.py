import os
import json
from collections import Counter

JSON_DIR = r"c:\Users\Admin\Documents\programming\buy-sell\json"

def audit_json_files():
    if not os.path.exists(JSON_DIR):
        print(f"Directory {JSON_DIR} does not exist.")
        return

    files = [f for f in os.listdir(JSON_DIR) if f.endswith('.json')]
    print(f"Found {len(files)} JSON files in {JSON_DIR}:\n")

    overall_stats = {
        'total_files': len(files),
        'total_records': 0,
        'error_records': 0,
        'success_records': 0,
        'error_types': Counter(),
        'all_keys': Counter(),
        'categories': Counter(),
        'bank_codes': Counter(),
        'alloted_counts': Counter(),
    }

    file_summaries = {}

    for fname in files:
        fpath = os.path.join(JSON_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {fname}: {e}")
            continue

        if not isinstance(data, dict):
            print(f"File {fname} is not a dict.")
            continue

        rec_count = len(data)
        errors = 0
        successes = 0
        file_keys = Counter()
        file_errors = Counter()

        for pan, rec in data.items():
            overall_stats['total_records'] += 1
            if not isinstance(rec, dict):
                overall_stats['error_records'] += 1
                errors += 1
                continue

            if 'error' in rec or 'Error' in rec:
                overall_stats['error_records'] += 1
                errors += 1
                err_val = str(rec.get('error') or rec.get('Error'))
                overall_stats['error_types'][err_val] += 1
                file_errors[err_val] += 1
            else:
                overall_stats['success_records'] += 1
                successes += 1

            for k in rec.keys():
                overall_stats['all_keys'][k] += 1
                file_keys[k] += 1

            if 'PEMNDG' in rec:
                overall_stats['categories'][str(rec['PEMNDG'])] += 1
            if 'Category' in rec:
                overall_stats['categories'][str(rec['Category'])] += 1

            if 'BNKCODE' in rec:
                overall_stats['bank_codes'][str(rec['BNKCODE'])] += 1

            if 'ALLOT' in rec:
                overall_stats['alloted_counts'][str(rec['ALLOT'])] += 1
            elif 'All_Shares' in rec:
                overall_stats['alloted_counts'][str(rec['All_Shares'])] += 1

        file_summaries[fname] = {
            'total_records': rec_count,
            'success_records': successes,
            'error_records': errors,
            'top_keys': list(file_keys.keys()),
            'error_breakdown': dict(file_errors)
        }

    print("=== OVERALL AUDIT SUMMARY ===")
    print(f"Total IPO Files Processed: {overall_stats['total_files']}")
    print(f"Total PAN Records Scraped: {overall_stats['total_records']}")
    print(f"Successful Records: {overall_stats['success_records']}")
    print(f"Error Records: {overall_stats['error_records']}")
    print("\n--- Top Error Types Encountered ---")
    for err, cnt in overall_stats['error_types'].most_common(10):
        print(f"  - {err}: {cnt} occurrences")

    print("\n--- Keys Found Across All JSON Files ---")
    for k, cnt in overall_stats['all_keys'].most_common(30):
        print(f"  - {k}: {cnt} times")

    print("\n--- Investor Categories Found ---")
    for cat, cnt in overall_stats['categories'].most_common():
        print(f"  - {cat}: {cnt} records")

    print("\n--- Allotment Values Found ---")
    for val, cnt in overall_stats['alloted_counts'].most_common(10):
        print(f"  - Allotted Shares = {val}: {cnt} records")

    print("\n=== PER FILE SUMMARY ===")
    print(json.dumps(file_summaries, indent=2))

if __name__ == "__main__":
    audit_json_files()
