"""Hilton 공식 국가별 검색 페이지 → 호텔 링크 수집 → 기존 hotels.csv 병합.

실행 예시 (Windows PowerShell):
  py -m pip install playwright
  py -m playwright install chromium
  py collect_hilton_official.py --headed

참고: 사이트 접근 제한/페이지 구조 변경 시 수집이 불완전할 수 있습니다.
차단 우회나 로그인 자동화는 하지 않습니다. 작업 결과는 매 국가별로 저장됩니다.
"""
import argparse
import csv
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

COUNTRIES = {
    '대한민국': 'south-korea', '일본': 'japan', '대만': 'taiwan',
    '홍콩': 'hong-kong', '마카오': 'macao', '중국': 'china',
    '태국': 'thailand', '베트남': 'vietnam', '싱가포르': 'singapore',
    '말레이시아': 'malaysia', '인도네시아': 'indonesia',
}
CODE_RE = re.compile(r'/hotels/([a-z0-9]{7})-([^/?#]+)/?', re.I)


def brand_tier(name):
    n=name.lower()
    for word,b,t in [
        ('waldorf astoria','Waldorf Astoria','Luxury'),('conrad','Conrad','Luxury'),
        ('lxr','LXR','Luxury'),('slh','SLH','Luxury'),('nomad','NoMad','Luxury'),
        ('signia','Signia','Premium'),('curio','Curio','Premium'),
        ('tapestry','Tapestry','Premium'),('canopy','Canopy','Premium'),
        ('doubletree','DoubleTree','Premium'),('hilton garden inn','Hilton Garden Inn','Select'),
        ('hampton','Hampton','Select'),('tru by hilton','Tru','Select'),
        ('home2','Home2 Suites','Extended Stay'),('homewood','Homewood Suites','Extended Stay'),
        ('motto','Motto','Select'),('hilton grand vacations','Hilton Grand Vacations','Extended Stay'),
        ('hilton','Hilton','Premium'),
    ]:
        if word in n: return b,t
    return 'Hilton Partner','Premium'


def provisional_region(country,name):
    n=name.lower()
    if country=='싱가포르':return '싱가포르'
    if country=='홍콩':return '홍콩'
    if country=='마카오':return '마카오'
    if country=='일본':
        for key,region in [('tokyo','도쿄·수도권'),('yokohama','도쿄·수도권'),('osaka','교토·오사카·간사이'),('kyoto','교토·오사카·간사이'),('kobe','교토·오사카·간사이'),('okinawa','오키나와·규슈'),('fukuoka','오키나와·규슈'),('niseko','홋카이도'),('sapporo','홋카이도')]:
            if key in n:return region
    if country=='대한민국':
        for key,region in [('seoul','서울'),('pangyo','경기'),('gyeongju','경북'),('incheon','인천'),('busan','부산')]:
            if key in n:return region
    if country=='중국':
        for key,region in [('shanghai','상하이·장쑤'),('suzhou','상하이·장쑤'),('beijing','베이징·톈진·허베이'),('tianjin','베이징·톈진·허베이'),('guangzhou','광둥'),('shenzhen','광둥'),('sanya','하이난'),('haikou','하이난')]:
            if key in n:return region
    if country=='태국':
        for key,region in [('bangkok','방콕·중부'),('phuket','푸켓·안다만'),('chiang mai','치앙마이·북부'),('pattaya','파타야·동부'),('koh samui','코사무이·태국만')]:
            if key in n:return region
    if country=='베트남':
        for key,region in [('hanoi','하노이·북부'),('da nang','다낭·중부'),('hoi an','다낭·중부'),('ho chi minh','호치민·남부'),('phu quoc','푸꾸옥·남부')]:
            if key in n:return region
    if country=='인도네시아':
        if any(k in n for k in ['bali','ubud','nusa dua']):return '발리'
        if 'jakarta' in n:return '자카르타·서부자바'
    if country=='대만':
        if 'taipei' in n:return '타이베이·북부'
        if 'taichung' in n or 'nantou' in n:return '타이중·중부'
    if country=='말레이시아':
        if 'kuala lumpur' in n or 'petaling' in n:return '쿠알라룸푸르·수도권'
        if 'kota kinabalu' in n or 'kuching' in n:return '보르네오'
    return '기타·위치 확인 필요'


def extract_visible(page, country):
    anchors=page.locator('a[href*="/hotels/"]').evaluate_all('''elements => elements.map(a => ({
        href:a.href, name:(a.innerText || a.getAttribute('aria-label') || '').trim(),
        context:(a.closest('article,[data-testid*="hotel"],[class*="HotelCard"]')?.innerText || '').slice(0,600)
    }))''')
    found={}
    for a in anchors:
        m=CODE_RE.search(a.get('href',''))
        if not m:continue
        code=m.group(1).upper()
        name=re.sub(r',?\s*Opens new tab\s*$', '', a.get('name',''),flags=re.I).strip()
        if not name or len(name)>140 or len(name)<5 or name.lower().startswith('view hotel'):
            continue
        context=a.get('context','')
        upcoming=('coming soon' in context.lower() or "aren't accepting reservations" in context.lower())
        found[code]=dict(country=country,code=code,name_en=name,url='https://www.hilton.com/en/hotels/'+code.lower()+'-'+m.group(2)+'/',upcoming=upcoming)
    return list(found.values())


def save_csv(path,rows,fields):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def crawl(args):
    from playwright.sync_api import sync_playwright
    raw=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=not args.headed)
        context=browser.new_context(locale='en-US')
        for country,slug in COUNTRIES.items():
            page=context.new_page()
            try:
                r=page.goto(f'https://www.hilton.com/en/locations/{slug}/',wait_until='domcontentloaded',timeout=35000)
                if r and r.status in (403,429):
                    print(country,'HTTP 차단:',r.status,'- 이 국가 보류');continue
                page.wait_for_timeout(2800)
                seen=set();country_rows=[]
                for ix in range(args.max_pages):
                    current=extract_visible(page,country)
                    for row in current:
                        if row['code'] not in seen:
                            seen.add(row['code']);country_rows.append(row)
                    print(country,f'페이지 {ix+1}: {len(current)}개, 누적 {len(country_rows)}개')
                    next_button=None
                    for selector in [
                        'button[aria-label="Next Page"]','button[aria-label*="Next Page"]',
                        '[aria-label="Next Page"]', 'button:has-text("Next Page")',
                        'button:has-text("Next page")',
                    ]:
                        loc=page.locator(selector)
                        if loc.count() and loc.first.is_visible() and loc.first.is_enabled():
                            next_button=loc.first;break
                    if next_button is None:break
                    before='|'.join(sorted(seen))
                    try:
                        next_button.click(timeout=5000)
                        page.wait_for_timeout(1800)
                        later=extract_visible(page,country)
                        if not any(x['code'] not in seen for x in later):
                            print(country,'다음 페이지 갱신 확인 불가: 중단');break
                    except Exception as exc:
                        print(country,'페이지 이동 중단',str(exc)[:100]);break
                raw.extend(country_rows)
                save_csv(args.raw,raw,['country','code','name_en','url','upcoming'])
            except Exception as exc:print(country,'수집 보류:',str(exc)[:140])
            finally:page.close()
        browser.close()
    print('원본 추출 총',len(raw),'건 /',args.raw)


def merge(args):
    with open(args.base,encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f);columns=rd.fieldnames;base=list(rd)
    with open(args.raw,encoding='utf-8-sig',newline='') as f:raw=list(csv.DictReader(f))
    seen={(r['brand_group'],r['code'].upper()) for r in base}
    new=[];upcoming=[];invalid=[]
    for r in raw:
        code=r['code'].upper()
        if r.get('upcoming','').lower() in ('true','1','yes'):
            upcoming.append(r);continue
        if not re.fullmatch(r'[A-Z0-9]{7}',code) or r.get('country') not in COUNTRIES or not r.get('url','').startswith('https://www.hilton.com/'):
            invalid.append(r);continue
        if ('Hilton',code) in seen:continue
        brand,tier=brand_tier(r['name_en']);country=r['country'];name_en=r['name_en']
        dr=provisional_region(country,name_en)
        record=dict.fromkeys(columns,'')
        record.update(brand_group='Hilton',country=country,display_region=dr,region=dr,area=dr,
                      code=code,name=name_en,name_en=name_en,brand=brand,tier=tier,popular='False',
                      hotel_url=r['url'].replace('/en/','/ko/'),location_status='공식 목록 URL 확인 · 상세 위치 검토 필요')
        new.append(record);seen.add(('Hilton',code))
    save_csv(args.output,base+new,columns)
    save_csv('hilton_new_collected.csv',new,columns)
    save_csv('hilton_upcoming_review.csv',upcoming,['country','code','name_en','url','upcoming'])
    save_csv('hilton_invalid_review.csv',invalid,['country','code','name_en','url','upcoming'])
    print(f'기존 {len(base)}개 + 신규 {len(new)}개 = {len(base)+len(new)}개; 개장 예정 {len(upcoming)}, 이상 {len(invalid)}')
    print('출력 파일:',args.output)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',default='hotels.csv');ap.add_argument('--raw',default='hilton_official_extracted.csv')
    ap.add_argument('--output',default='hotels_hilton_all_candidates.csv')
    ap.add_argument('--max-pages',type=int,default=100)
    ap.add_argument('--headed',action='store_true')
    ap.add_argument('--merge-only',action='store_true')
    args=ap.parse_args()
    if not args.merge_only:crawl(args)
    merge(args)
