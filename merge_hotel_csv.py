"""Merge an incoming hotel CSV by (brand_group,code) and normalize regions.

Example:
  python merge_hotel_csv.py --base hotels.csv --incoming new_hotels.csv --output hotels_merged.csv

Safety: unmatched cities or missing identifiers are written to --review and not imported.
Existing rows remain unchanged except for non-empty incoming fields on matching keys.
"""
import argparse, csv
from pathlib import Path
from hotel_region_rules import region_for

BASE_REQUIRED=('brand_group','code','country')

def read(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        return list(reader), reader.fieldnames or []

def write(path,rows,fields):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def key(row):
    return ((row.get('brand_group') or '').strip(),(row.get('code') or '').strip().upper())

def merge(base, incoming, base_fields, incoming_fields):
    if not set(BASE_REQUIRED).issubset(incoming_fields):
        raise ValueError('Incoming CSV requires brand_group, code, country columns')
    if not set(BASE_REQUIRED).issubset(base_fields):
        raise ValueError('Base CSV requires brand_group, code, country columns')
    fields=list(dict.fromkeys(base_fields+incoming_fields))
    result=[r.copy() for r in base]
    index={}
    for i,r in enumerate(result):
        k=key(r)
        if k in index: raise ValueError(f'Duplicate base code: {k}')
        index[k]=i
    review=[]; audit=[]; seen=set()
    for n,new in enumerate(incoming,2):
        k=key(new)
        if not all(k) or not (new.get('country') or '').strip():
            review.append({'line':n,'brand_group':k[0],'code':k[1],'country':new.get('country',''),'region':new.get('region',''),'reason':'missing-identifier'});continue
        if k in seen:
            review.append({'line':n,'brand_group':k[0],'code':k[1],'country':new.get('country',''),'region':new.get('region',''),'reason':'duplicate-in-incoming'});continue
        seen.add(k)
        old=result[index[k]] if k in index else {}
        candidate=dict(old)
        for field in incoming_fields:
            value=(new.get(field) or '').strip()
            if value: candidate[field]=value
        # Always use source city if available and never silently accept an unknown mapped region.
        standard,rule=region_for(candidate)
        if not standard:
            review.append({'line':n,'brand_group':k[0],'code':k[1],'country':candidate.get('country',''),'region':candidate.get('region',''),'reason':rule});continue
        candidate['display_region']=standard
        action='updated' if k in index else 'added'
        if k in index: result[index[k]]=candidate
        else: index[k]=len(result);result.append(candidate)
        audit.append({'action':action,'brand_group':k[0],'code':k[1],'country':candidate.get('country',''), 'display_region':standard,'rule':rule})
    return result,fields,audit,review

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--incoming',required=True)
    p.add_argument('--output',default='hotels_merged.csv');p.add_argument('--audit',default='hotel_merge_audit.csv');p.add_argument('--review',default='hotel_merge_review.csv')
    a=p.parse_args();base,bf=read(a.base);incoming,nf=read(a.incoming)
    rows,fields,audit,review=merge(base,incoming,bf,nf)
    if Path(a.output).resolve() == Path(a.base).resolve():
        raise SystemExit('For safety --output must differ from --base. Review first, then replace base CSV.')
    write(a.output,rows,fields)
    write(a.audit,audit,['action','brand_group','code','country','display_region','rule'])
    write(a.review,review,['line','brand_group','code','country','region','reason'])
    print(f'Rows: {len(rows)}; imported: {len(audit)}; needs review: {len(review)}')

if __name__=='__main__':main()
