"""Static audit of Marriott master; does not claim live booking verification.
Usage: python audit_marriott_codes.py marriott_hotels.csv
"""
import csv, re, sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

SOURCE = Path(sys.argv[1]) if len(sys.argv)>1 else Path('marriott_hotels.csv')
ROOT = SOURCE.parent
rows = list(csv.DictReader(SOURCE.open(encoding='utf-8-sig', newline='')))
required = ['brand_group','country','region','area','code','name','brand','tier','popular','hotel_url','star_rating']
if not rows or any(k not in rows[0] for k in required):
    raise SystemExit('Expected 11-column hotel master CSV')

# Alias records identified as the SAME physical hotel using official Marriott hotel pages.
# Store aliases separately instead of overwriting the canonical code.
aliases = {
    'OKAIL': ('OKALC','IRAPH SUI, a Luxury Collection Hotel, Miyako Okinawa', 'https://www.marriott.com/ko/hotels/okalc-iraph-sui-a-luxury-collection-hotel-miyako-okinawa/overview/'),
    'OSAFU': ('OSAUU','Four Points Flex by Sheraton Osaka Umeda', 'https://www.marriott.com/ko/hotels/osauu-four-points-flex-osaka-umeda/overview/'),
    'TYOAC': ('TYOAR','AC Hotel Tokyo Ginza', 'https://www.marriott.com/ko/hotels/tyoar-ac-hotel-tokyo-ginza/overview/'),
}
canonical_pages = {
    'OKALC': ('https://www.marriott.com/ko/hotels/okalc-iraph-sui-a-luxury-collection-hotel-miyako-okinawa/overview/', '2026-11-14: official Marriott overview verified'),
    'OSAUU': ('https://www.marriott.com/ko/hotels/osauu-four-points-flex-osaka-umeda/overview/', '2026-11-14: official Marriott overview verified'),
    'TYOAR': ('https://www.marriott.com/en-us/hotels/tyoar-ac-hotel-tokyo-ginza/overview/', '2026-11-14: official Marriott overview verified (ko redirected)'),
    'OSAFI': ('https://www.marriott.com/en-us/hotels/osafi-fairfield-hyogo-awaji-fukura/overview/', '2026-11-14: official Marriott overview verified'),
    'OKACR': ('https://www.marriott.com/en-us/hotels/okacr-courtyard-okinawa-resort/overview/', '2026-11-14: official Marriott overview verified'),
}
code_set = {r['code'].upper().strip() for r in rows}
changes = []
cleaned = []
audit=[]
for nr,r in enumerate(rows,2):
    r=dict(r)
    code=r['code'].upper().strip()
    rawurl=r['hotel_url'].strip()
    issues=[]
    official_status = '미확인'
    calendar_status = '미검증 (실제 브라우저 확인 필요)'
    if code in aliases and aliases[code][0] in code_set:
        canonical,name,url = aliases[code]
        changes.append({'source_row':nr,'removed_code':code,'removed_name':r['name'],'kept_code':canonical,'canonical_name':name,'official_url':url,'action':'중복 제거; 공식 호텔 페이지 기준 canonical code 유지'})
        audit.append({'csv_row':nr,'code':code,'name':r['name'],'country':r['country'],'official_page_url':url,'official_page_status':'공식 코드 중복 (제외)','calendar_status':'잘못된 코드 사용 위험','issues':f'중복 코드: {canonical} 유지','action':'삭제'})
        continue
    if not re.fullmatch('[A-Z0-9]{5}',code):issues.append('5자리 코드 규격 불일치')
    if not all(r.get(k,'').strip() for k in ['country','region','area','code','name']):issues.append('필수 정보 누락')
    if code in canonical_pages:
        url,note=canonical_pages[code]
        if rawurl != url:
            changes.append({'source_row':nr,'removed_code':'','removed_name':'','kept_code':code,'canonical_name':r['name'],'official_url':url,'action':'공식 상세 페이지 URL 보완'})
        r['hotel_url']=url
        official_status='공식 홈페이지 확인 (호텔 코드/명칭)'
    elif not rawurl:
        issues.append('공식 상세 URL 없음')
        official_status='URL 없음 (호텔 코드 검증 불가)'
    else:
        u=urlsplit(rawurl)
        m=re.search(r'/hotels/(?:travel/)?([A-Za-z0-9]{5})-',u.path,re.I)
        if m:
            if m.group(1).upper()!=code:
                issues.append(f'URL 코드 {m.group(1).upper()} != CSV 코드 {code}')
            elif u.netloc.lower() in ('www.marriott.com','marriott.com','www.ritzcarlton.com'):
                official_status='URL 형식 일치 (접속 미검증)'
            else:
                issues.append('비공식 도메인 URL')
        elif '/availabilityCalendar.mi' in u.path:
            qs=parse_qs(u.query)
            if qs.get('propertyCode',[''])[0].upper()!=code:issues.append('예약달력 URL 코드 불일치')
            issues.append('hotel_url에 달력 링크 저장됨; 공식 상세 링크 아님')
            official_status='상세 URL 없음 (달력 링크만 존재)'
            r['hotel_url']=''
        else:
            issues.append('공식 상세 URL 구문 인식 실패')
    cleaned.append(r)
    audit.append({'csv_row':nr,'code':code,'name':r['name'],'country':r['country'],'official_page_url':r['hotel_url'],'official_page_status':official_status,'calendar_status':calendar_status,'issues':'; '.join(issues),'action':'유지 (추가검증 필요)' if issues else '유지'})

if len({r['code'] for r in cleaned})!=len(cleaned):raise SystemExit('Duplicates remain')
out=ROOT/'marriott_hotels_audited.csv'
for fp,data,fields in [
    (out,cleaned,required),
    (ROOT/'marriott_link_audit_245.csv',audit,['csv_row','code','name','country','official_page_url','official_page_status','calendar_status','issues','action']),
    (ROOT/'marriott_duplicate_removals.csv',changes,['source_row','removed_code','removed_name','kept_code','canonical_name','official_url','action']),
]:
    with fp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader();w.writerows(data)
print('Input:',len(rows),'Clean:',len(cleaned),'Removed aliases:',[c['removed_code'] for c in changes if c['removed_code']])
from collections import Counter
print('Page status:',Counter(x['official_page_status'] for x in audit))
print('Output:',out)
