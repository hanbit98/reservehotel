"""Normalize hotels.csv with a shared location vocabulary for five countries.

Usage: python normalize_hotel_regions.py --input hotels.csv --output hotels.csv
       python normalize_hotel_regions.py --input hotels.csv --output hotels_new.csv --strict
"""
import argparse
import csv
from pathlib import Path
from hotel_region_rules import normalize_rows

def write_csv(path, rows, fields):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default='hotels.csv');p.add_argument('--output',default='hotels.csv')
    p.add_argument('--audit',default='hotel_region_changes.csv');p.add_argument('--review',default='hotel_region_review.csv')
    p.add_argument('--strict',action='store_true');args=p.parse_args()
    with open(args.input,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames; rows=list(reader)
    changes,issues=normalize_rows(rows)
    if issues and args.strict: raise SystemExit(f'Unmapped locations: {len(issues)}. No output written. {issues[:5]}')
    write_csv(args.output,rows,fields)
    write_csv(args.audit,changes,['brand_group','country','code','region','previous_display_region','new_display_region','rule'])
    write_csv(args.review,issues,['brand_group','country','code','region','area','current_display_region','reason'])
    print(f'Rows: {len(rows)}; changes: {len(changes)}; issues: {len(issues)}; output: {args.output}')

if __name__=='__main__':main()
