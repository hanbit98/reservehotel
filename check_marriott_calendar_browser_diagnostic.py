"""Marriott calendar browser diagnostic (does not bypass access restrictions).

Usage:
    py check_marriott_calendar_browser_diagnostic.py marriott_hotels.csv --limit 3 --headed
    py check_marriott_calendar_browser_diagnostic.py marriott_hotels.csv --limit 10 --headed --delay 4

Creates marriott_calendar_diagnostic_results.csv and diagnostic screenshots for
ambiguous/blocked pages. Stops after 2 consecutive confirmed access blocks.
"""
import argparse
import asyncio
import csv
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

ERROR_PATTERNS = [
    r"property not found", r"hotel not found", r"we could(?: not|n't) find",
    r"호텔을 찾을 수 없", r"존재하지 않는 호텔",
]
BLOCK_PATTERNS = [
    r"access denied", r"verify you are human", r"captcha",
    r"robot check", r"automated access", r"request blocked",
]


def calendar_url(code: str, checkin: date, nights: int) -> str:
    checkout = checkin + timedelta(days=nights)
    query = {
        "propertyCode": code.upper(), "isSearch": "true",
        "isInternalSearch": "true", "initialRequest": "true",
        "isRateCalendar": "true", "flexibleDateSearch": "true",
        "isFlexibleDatesOptionSelected": "true",
        "fromDate": checkin.strftime("%Y.%m.%d"),
        "toDate": checkout.strftime("%Y.%m.%d"),
        "fromDateDefaultFormat": checkin.strftime("%m/%d/%Y"),
        "toDateDefaultFormat": checkout.strftime("%m/%d/%Y"),
        "t-start": checkin.isoformat(), "t-end": checkout.isoformat(),
        "lengthOfStay": str(nights), "roomCount": "1",
        "numAdultsPerRoom": "2", "childrenCount": "0",
        "useRewardsPoints": "true",
    }
    return "https://www.marriott.com/ko/search/availabilityCalendar.mi?" + urlencode(query) + "#/0/"


def match_patterns(text, patterns):
    return [p for p in patterns if re.search(p, text, re.I)]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--checkin", default=(date.today() + timedelta(days=30)).isoformat())
    parser.add_argument("--nights", type=int, default=1)
    parser.add_argument("--delay", type=float, default=4.0)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--stop-after-blocks", type=int, default=2)
    args = parser.parse_args()

    from playwright.async_api import async_playwright, TimeoutError as BrowserTimeout
    with args.csv.open(encoding="utf-8-sig", newline="") as source:
        hotels = list(csv.DictReader(source))
    if args.limit:
        hotels = hotels[:args.limit]
    if not hotels:
        raise SystemExit("CSV에서 호텔을 찾지 못했습니다.")
    screenshot_dir = args.csv.parent / "marriott_diagnostic_screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    rows = []
    blocked_streak = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        context = await browser.new_context(locale="ko-KR", viewport={"width": 1280, "height": 900})
        for idx, hotel in enumerate(hotels, 1):
            code = str(hotel.get("code", "")).strip().upper()
            target = calendar_url(code, date.fromisoformat(args.checkin), args.nights)
            page = await context.new_page()
            result = {
                "code": code, "csv_name": hotel.get("name", ""),
                "http_status": "", "result": "미검증", "page_title": "",
                "final_url": "", "block_patterns": "", "error_patterns": "",
                "body_excerpt": "", "screenshot": "", "calendar_url": target,
                "note": "",
            }
            try:
                response = await page.goto(target, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                result["http_status"] = str(response.status) if response else ""
                result["final_url"] = page.url
                result["page_title"] = (await page.title())[:200]
                body = (await page.locator("body").inner_text(timeout=10000))[:50000]
                result["body_excerpt"] = re.sub(r"\s+", " ", body)[:450]
                block_matches = match_patterns(body[:20000] + " " + result["page_title"], BLOCK_PATTERNS)
                error_matches = match_patterns(body[:20000] + " " + result["page_title"], ERROR_PATTERNS)
                result["block_patterns"] = "; ".join(block_matches)
                result["error_patterns"] = "; ".join(error_matches)
                if result["http_status"] in ("403", "429"):
                    result["result"] = "HTTP 접근 제한"
                    blocked_streak += 1
                elif block_matches:
                    result["result"] = "차단 문구 감지 (화면 확인 필요)"
                    blocked_streak += 1
                elif result["http_status"] == "404" or error_matches:
                    result["result"] = "호텔/예약 오류 문구 (수동 확인)"
                    blocked_streak = 0
                elif result["http_status"] == "200":
                    result["result"] = "HTTP 200 (달력 및 호텔명 미검증)"
                    blocked_streak = 0
                else:
                    result["result"] = "그 밖의 응답 (미검증)"
                    blocked_streak = 0
                if idx <= 3 or result["result"] != "HTTP 200 (달력 및 호텔명 미검증)":
                    file = screenshot_dir / f"{idx:03d}_{code}.png"
                    await page.screenshot(path=str(file), full_page=False, timeout=10000)
                    result["screenshot"] = str(file)
            except BrowserTimeout:
                result["result"] = "타임아웃 (미검증)"
                blocked_streak = 0
            except Exception as exc:
                result["result"] = "검사 오류 (미검증)"
                result["note"] = str(exc)[:300]
                blocked_streak = 0
            finally:
                await page.close()
            rows.append(result)
            print(f"{idx}/{len(hotels)} {code}: {result['result']} (HTTP {result['http_status'] or '-'})", flush=True)
            if blocked_streak >= args.stop_after_blocks:
                print("연속 접근 제한 감지: 서버에 반복 요청하지 않도록 검사 중단", flush=True)
                break
            await asyncio.sleep(max(args.delay, 0))
        await browser.close()
    output = args.csv.parent / "marriott_calendar_diagnostic_results.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {output}")
    print(f"Screenshots: {screenshot_dir}")
    print("주의: HTTP 200은 예약 달력과 호텔명의 정상 일치를 증명하지 않습니다.")

if __name__ == "__main__":
    asyncio.run(main())
