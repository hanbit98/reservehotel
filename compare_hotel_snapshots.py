"""두 시점의 통합 hotels.csv 비교: 신규/삭제 후보/정보 변경/국가별 증감.

예: py compare_hotel_snapshots.py --old snapshots/hotels_2026-11-16.csv --new hotels.csv
이 도구는 원본 데이터를 자동 수집하지 않습니다. 신규 수집본이 필요합니다.
"""
import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path

KEY = ('brand_group', 'code')
WATCH_FIELDS = ('country','display_region','region','area','name','name_en','brand','tier',
                'tier_source','opening_status','hotel_url','address','province')


def read(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not set(KEY).issubset(reader.fieldnames or []):
            raise ValueError(f'{path}: brand_group/code 필수')
        rows = list(reader)
    result = {}
    for row in rows:
        key = (row['brand_group'].strip(), row['code'].strip().upper())
        if not all(key):
            raise ValueError(f'{path}: 코드 또는 체인 빈 값')
        if key in result:
            raise ValueError(f'{path}: 중복 코드 {key}')
        result[key] = row
    return result


def write_csv(path, rows, fields):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description='이전 호텔 데이터와 최신 수집본의 증감을 비교합니다.')
    parser.add_argument('--old',required=True,help='직전 기준본 CSV')
    parser.add_argument('--new',required=True,help='새로 수집한 최신 CSV')
    parser.add_argument('--output-dir',default='hotel_change_reports')
    args=parser.parse_args()
    old,new=read(args.old),read(args.new)
    dest=Path(args.output_dir);dest.mkdir(parents=True,exist_ok=True)
    newkeys=new.keys()-old.keys(); lostkeys=old.keys()-new.keys(); common=old.keys()&new.keys()
    fields=list(dict.fromkeys(['brand_group','code','country','display_region','name','hotel_url']+list(next(iter(new.values())).keys())+list(next(iter(old.values())).keys())))
    added=[new[k] for k in sorted(newkeys)]
    missing=[dict(old[k], review_status='이전 데이터에 존재 / 신규 수집본에 미발견 (폐업 단정 금지)') for k in sorted(lostkeys)]
    changes=[]
    for key in sorted(common):
        for col in WATCH_FIELDS:
            a=old[key].get(col,'').strip();b=new[key].get(col,'').strip()
            if a!=b:
                changes.append({'brand_group':key[0],'code':key[1],'name':new[key].get('name',''),
                                'field':col,'old_value':a,'new_value':b})
    write_csv(dest/'new_hotels.csv',added,fields)
    write_csv(dest/'missing_candidates.csv',missing,fields+['review_status'])
    write_csv(dest/'changed_details.csv',changes,['brand_group','code','name','field','old_value','new_value'])
    oldcounts=Counter((r.get('country',''),r['brand_group']) for r in old.values())
    newcounts=Counter((r.get('country',''),r['brand_group']) for r in new.values())
    stats=[{'country':k[0],'brand_group':k[1],'previous':oldcounts[k],
            'current':newcounts[k],'difference':newcounts[k]-oldcounts[k]}
            for k in sorted(oldcounts.keys()|newcounts.keys())]
    write_csv(dest/'country_brand_delta.csv',stats,['country','brand_group','previous','current','difference'])
    with open(dest/'summary.txt','w',encoding='utf-8') as f:
        f.write(f'비교일: {date.today()}\n이전: {len(old)} / 신규: {len(new)}\n')
        f.write(f'신규 코드: {len(added)}\n미발견 후보: {len(missing)}\n정보 변경 필드: {len(changes)}\n')
        f.write('※ 미발견은 폐업·탈퇴의 확정 증거가 아닙니다. 페이지 누락, 개장 상태, 수집범위 변경 가능성을 먼저 확인하세요.\n')
    print(f'기존 {len(old)} → 최신 {len(new)} | 신규 {len(added)} | 미발견 {len(missing)} | 정보 변경 {len(changes)} | 결과: {dest}')

if __name__=='__main__':
    main()
