"""Open Marriott availability calendars in an actual Chromium browser.

Install:
    pip install playwright
    python -m playwright install chromium
Run a small sample:
    python check_marriott_calendar_browser.py marriott_hotels_audited.csv --limit 10
Run all:
    python check_marriott_calendar_browser.py marriott_hotels_audited.csv

The test DOES NOT certify points availability, nor does a page response 200
prove the correct hotel loaded. Statuses distinguish these cases.

For bot protection/captcha, results are INCONCLUSIVE; do not bypass protection.
"""
import argparse
import asyncio
import csv
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlencode

ERROR_WORDS = [
    'property not found', 'hotel not found', 'no longer available',
    'we could not find', 'we couldn\'t find',
    '호텔을 찾을 수 없습니다', '호텔을 찾을 수 없',
    '존재하지 않는 호텔', '호텔이 없습니다',
]
BLOCK_WORDS = ['access denied', 'verify you are human', 'captcha', 'robot check', 'automated access']

def calendar_url(code, checkin, nights):
    checkout=checkin+timedelta(days=nights)
    query={
        'propertyCode':code.upper(), 'isSearch':'true',
        'isInternalSearch':'true', 'initialRequest':'true',
        'isRateCalendar':'true', 'flexibleDateSearch':'true',
        'isFlexibleDatesOptionSelected':'true',
        'fromDate':checkin.strftime('%Y.%m.%d'),
        'toDate':checkout.strftime('%Y.%m.%d'),
        'fromDateDefaultFormat':checkin.strftime('%m/%d/%Y'),
        'toDateDefaultFormat':checkout.strftime('%m/%d/%Y'),
        't-start':checkin.isoformat(), 't-end':checkout.isoformat(),
        'lengthOfStay':str(nights), 'roomCount':'1',
        'numAdultsPerRoom':'2', 'childrenCount':'0',
        'useRewardsPoints':'true',
    }
    return 'https://www.marriott.com/ko/search/availabilityCalendar.mi?'+urlencode(query)+'#/0/'

async def main():
    p=argparse.ArgumentParser()
    p.add_argument('csv',type=Path)
    p.add_argument('--limit',type=int,default=0,help='0: all')
    p.add_argument('--checkin',default=(date.today()+timedelta(days=30)).isoformat())
    p.add_argument('--nights',type=int,default=1)
    p.add_argument('--delay',type=float,default=1.2)
    p.add_argument('--headed',action='store_true',help='show Chrome window')
    args=p.parse_args()
    from playwright.async_api import async_playwright, TimeoutError as BrowserTimeout
    hotels=list(csv.DictReader(args.csv.open(encoding='utf-8-sig',newline='')))
    if args.limit:hotels=hotels[:args.limit]
    out=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=not args.headed)
        context=await browser.new_context(locale='ko-KR', viewport={'width':1280,'height':900})
        page=await context.new_page()
        for i,r in enumerate(hotels,1):
            code=r['code'].strip().upper()
            url=calendar_url(code,date.fromisoformat(args.checkin),args.nights)
            status='판정 불가'
            http=''
            title=''
            final_url=''
            note=''
            try:
                response=await page.goto(url,wait_until='domcontentloaded',timeout=25000)
                await page.wait_for_timeout(2200)
                http=str(response.status) if response else ''
                final_url=page.url
                title=(await page.title())[:200]
                body=(await page.locator('body').inner_text(timeout=8000)).lower()[:20000]
                if any(s in body for s in BLOCK_WORDS) or http in ('403','429'):
                    status='접근 제한 (미검증)'
                elif any(s in body for s in ERROR_WORDS) or http=='404':
                    status='호텔 없음 또는 오류 가능 (수동 확인)'
                elif http=='200':
                    status='페이지 응답 200 (호텔/달력 표시 미확인)'
                    note='HTTP 200은 예약 달력 정상 동작을 보장하지 않습니다.'
                else:
                    status='다른 응답 (미검증)'
            except BrowserTimeout:
                status='타임아웃 (미검증)'
            except Exception as exc:
                status='브라우저 오류 (미검증)'
                note=str(exc)[:250]
            out.append({'code':code,'name':r['name'],'calendar_url':url,
                        'http_status':http,'result':status,'final_url':final_url,
                        'page_title':title,'note':note})
            print(f'{i}/{len(hotels)} {code}: {status}',flush=True)
            await asyncio.sleep(args.delay)
        await browser.close()
    dst=args.csv.with_name('marriott_calendar_browser_results.csv')
    with dst.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print('Saved:',dst)

if __name__=='__main__':
    asyncio.run(main())
