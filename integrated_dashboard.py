"""메리어트 + 힐튼 + 아코르 아시아 호텔 예약 링크 대시보드.

기존 marriott_asia_dashboard.py의 메리어트 목록/URL 함수를 유지하고,
타 브랜드 식별코드, 예약 링크, 검색 및 내보내기를 통합한 독립 실행형 Streamlit 앱.
공식 예약 사이트가 URL 파라미터를 변경하거나 로그인/쿠키를 요구할 수 있음.
이 앱은 실시간 호텔 가격을 스크래핑하거나 예약 가능 여부를 판단하지 않음.
"""
import base64
from html import escape as html_escape
import re
from pathlib import Path
from datetime import date, timedelta
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="아시아 호텔 통합 포인트 & 요금 조회 대시보드",
    page_icon="🏨",
    layout="wide",
)

# 1) 국가 아이콘과 국가 표시 순서
COUNTRY_FLAGS = {
    "대한민국": "🇰🇷",
    "일본": "🇯🇵",
    "대만": "🇹🇼",
    "홍콩": "🇭🇰",
    "마카오": "🇲🇴",
    "중국": "🇨🇳",
    "태국": "🇹🇭",
    "베트남": "🇻🇳",
    "싱가포르": "🇸🇬",
    "말레이시아": "🇲🇾",
    "인도네시아": "🇮🇩", "필리핀": "🇵🇭", "캄보디아": "🇰🇭", "라오스": "🇱🇦", "미얀마": "🇲🇲",
    "인도": "🇮🇳", "몰디브": "🇲🇻", "스리랑카": "🇱🇰", "네팔": "🇳🇵", "부탄": "🇧🇹",
    "파키스탄": "🇵🇰", "카자흐스탄": "🇰🇿", "우즈베키스탄": "🇺🇿", "키르기스스탄": "🇰🇬", "타지키스탄": "🇹🇯",
}


# 국기는 실제 PNG 이미지를 사용합니다. 네트워크가 막히면 이모지로 대체합니다.
COUNTRY_FLAG_CODES = {
    "대한민국": "kr", "일본": "jp", "대만": "tw", "홍콩": "hk", "마카오": "mo",
    "중국": "cn", "태국": "th", "베트남": "vn", "싱가포르": "sg",
    "말레이시아": "my", "인도네시아": "id",
    "필리핀": "ph", "캄보디아": "kh", "라오스": "la", "미얀마": "mm",
    "인도": "in", "몰디브": "mv", "스리랑카": "lk", "네팔": "np", "부탄": "bt",
    "파키스탄": "pk", "카자흐스탄": "kz", "우즈베키스탄": "uz", "키르기스스탄": "kg", "타지키스탄": "tj",
}


def country_heading(country: str, count: int) -> str:
    """국가 제목 옆에 PNG 국기 표시, 실패하면 국기 이모지 노출."""
    safe_country = html_escape(country)
    code = COUNTRY_FLAG_CODES.get(country)
    if code:
        flag = (
            f'<img src="https://flagcdn.com/w80/{code}.png" '
            f'alt="{safe_country} 국기" loading="lazy" '
            f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline\'" '
            f'style="height:29px;width:44px;object-fit:cover;border:1px solid rgba(120,120,120,.18);border-radius:4px;" />'
            f'<span style="display:none;font-size:29px;">{COUNTRY_FLAGS.get(country, "🌐")}</span>'
        )
    else:
        flag = f'<span style="font-size:29px;">{COUNTRY_FLAGS.get(country, "🌐")}</span>'
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin:0.3rem 0 0.8rem;">'
        f'{flag}<span style="font-size:1.65rem;font-weight:750;line-height:1.3;">'
        f'{safe_country} · {count:,}개 호텔</span></div>'
    )


# 2) 호텔 마스터 데이터: hotels.csv 하나로 전 체인을 관리합니다.
# 배포 시 integrated_dashboard.py + hotels.csv + assets/ 폴더만 필요합니다.
DATA_DIR = Path(__file__).resolve().parent
HOTELS_CSV = DATA_DIR / "hotels.csv"
HOTEL_COLUMNS = [
    "brand_group", "country", "region", "area", "code",
    "name", "brand", "tier", "popular", "hotel_url",
]
EXTRA_COLUMNS = [
    "display_region", "name_en", "province", "address", "phone", "review_rating",
    "review_count", "brand_code", "source_date", "location_status", "tier_source", "opening_status",
]
SUPPORTED_GROUPS = {"Marriott": 5, "Hilton": 7, "Accor": 4}


def display_hotel_name(hotel) -> str:
    """Domestic: Korean only; overseas: English and optionally Korean."""
    country = str(hotel.get("country", "")).strip()
    name = str(hotel.get("name", "")).strip()
    english = str(hotel.get("name_en", "")).strip()
    if country == "대한민국":
        return name or english
    if english:
        if name and name.casefold() != english.casefold() and re.search(r"[가-힣]", name):
            return f"{english} ({name})"
        return english
    # Legacy Hilton/Accor entries without verified English names retain the source name.
    return name


@st.cache_data(show_spinner=False)
def read_hotels_csv(path: str, modified_ns: int) -> pd.DataFrame:
    """CSV가 바뀌면 수정시각을 캐시 키로 사용해 다시 읽습니다."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def load_hotel_data() -> pd.DataFrame:
    """통합 hotels.csv를 읽어 체인별 코드와 데이터 무결성을 확인합니다."""
    if not HOTELS_CSV.is_file():
        st.error("hotels.csv 파일이 없습니다. integrated_dashboard.py와 같은 폴더에 올려주세요.")
        st.stop()

    try:
        part = read_hotels_csv(str(HOTELS_CSV), HOTELS_CSV.stat().st_mtime_ns)
    except Exception as exc:
        st.error(f"hotels.csv 읽기 오류: {exc}")
        st.stop()

    missing = sorted(set(HOTEL_COLUMNS) - set(part.columns))
    if missing:
        st.error("hotels.csv 필수 열 누락: " + ", ".join(missing))
        st.stop()

    if "star_rating" not in part.columns:
        part["star_rating"] = ""
    for col in EXTRA_COLUMNS:
        if col not in part.columns:
            part[col] = ""
    part = part[HOTEL_COLUMNS + ["star_rating"] + EXTRA_COLUMNS].copy()
    for col in part.columns:
        part[col] = part[col].fillna("").astype(str).str.strip()
    part["brand_group"] = part["brand_group"].str.strip()
    part["code"] = part["code"].str.upper()

    issues = []
    invalid_group = ~part["brand_group"].isin(SUPPORTED_GROUPS)
    if invalid_group.any():
        cases = part.index[invalid_group][:5].tolist()
        issues.append(f"지원하지 않는 brand_group 행: {[i+2 for i in cases]} (Marriott/Hilton/Accor 사용)")

    for group, code_length in SUPPORTED_GROUPS.items():
        mask = part["brand_group"].eq(group)
        invalid_code = mask & ~part["code"].str.fullmatch(rf"[A-Z0-9]{{{code_length}}}")
        if invalid_code.any():
            rows = [int(i)+2 for i in part.index[invalid_code][:5]]
            issues.append(f"{group} 호텔 코드 형식 오류: CSV 행 {rows} (영숫자 {code_length}자리)")

    required = ["brand_group", "country", "display_region", "region", "area", "code", "name", "brand", "tier"]
    missing_values = part[required].eq("")
    if missing_values.any().any():
        detail = []
        for i in part.index[missing_values.any(axis=1)][:8]:
            empty_columns = missing_values.columns[missing_values.loc[i]].tolist()
            detail.append(f"{i+2}행 {part.at[i, 'code'] or '(코드 없음)'}: {', '.join(empty_columns)}")
        issues.append("필수 정보 빈칸 - " + " / ".join(detail))

    truthy = {"true", "1", "yes", "y"}
    falsy = {"false", "0", "no", "n"}
    popular_lower = part["popular"].str.lower()
    invalid_popular = ~popular_lower.isin(truthy | falsy)
    if invalid_popular.any():
        rows = [int(i)+2 for i in part.index[invalid_popular][:5]]
        issues.append(f"popular은 TRUE/FALSE를 입력하세요: CSV 행 {rows}")
    part["popular"] = popular_lower.isin(truthy)

    invalid_stars = ~part["star_rating"].isin(["", "1", "2", "3", "4", "5"])
    if invalid_stars.any():
        rows = [int(i)+2 for i in part.index[invalid_stars][:5]]
        issues.append(f"star_rating은 공란 또는 1~5 정수만 허용합니다: CSV 행 {rows}")

    duplicates = part.duplicated(["brand_group", "code"], keep=False)
    if duplicates.any():
        dup_rows = part.loc[duplicates, ["brand_group", "code"]].head(8).to_dict("records")
        issues.append(f"같은 체인 내 호텔 코드 중복: {dup_rows}")

    if issues:
        for issue in issues:
            st.error("hotels.csv: " + issue)
        st.stop()

    part.loc[part["brand_group"] == "Hilton", "hotel_url"] = (
        part.loc[part["brand_group"] == "Hilton", "hotel_url"].str.replace("/en/", "/ko/", regex=False)
    )
    part["display_name"] = part.apply(display_hotel_name, axis=1)
    part["hilton_affiliation"] = part.apply(
        lambda h: "SLH 제휴" if h["brand_group"] == "Hilton" and bool(re.search(r"\bSLH\b|Small Luxury Hotels", h["brand"], re.IGNORECASE))
        else ("힐튼 일반·계열" if h["brand_group"] == "Hilton" else ""), axis=1
    )
    return part

master = load_hotel_data()
INTEGRATED_HOTELS = master.to_dict("records")
GROUP_LABELS = {"Marriott": "메리어트", "Hilton": "힐튼", "Accor": "아코르"}
GROUP_ICONS = {"Marriott": "Ⓜ️", "Hilton": "✨", "Accor": "🪶"}
GROUPS = ["Marriott", "Hilton", "Accor"]
BRAND_COLORS = {"Marriott": "#C73A4A", "Hilton": "#004B87", "Accor": "#9C7B2F"}
BRAND_TEXT_COLORS = {"Marriott": "#FFFFFF", "Hilton": "#FFFFFF", "Accor": "#FFFFFF"}

# 브랜드 개수는 각 체인 고유색을 연한 배지로 표시합니다.
BRAND_PILL_STYLES = {
    "Marriott": ("#B42335", "#FFF1F2"),
    "Hilton": ("#07569B", "#ECF4FF"),
    "Accor": ("#795D13", "#FFF7DB"),
}
TIER_PILL_STYLES = {
    "Luxury": ("#805B17", "#FFF2CA", "◆"),
    "Premium": ("#28569D", "#E9F1FF", "●"),
    "Lifestyle": ("#9346AB", "#F8EAFE", "✦"),
    "Select": ("#18704D", "#E4F6ED", "●"),
    "Extended Stay": ("#6847A3", "#F1EBFF", "■"),
}


def render_region_brand_counts(counts) -> str:
    pills = []
    for group in GROUPS:
        color, background = BRAND_PILL_STYLES[group]
        label = html_escape(GROUP_LABELS[group])
        count = int(counts.get(group, 0))
        pills.append(
            f'<span style="display:inline-block;white-space:nowrap;font-size:12px;'
            f'font-weight:700;color:{color};background:{background};'
            f'padding:5px 8px;border-radius:7px;">{label} {count:,}</span>'
        )
    return '<div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;min-height:37px;">' + ''.join(pills) + '</div>'


def render_tier_badge(tier: str) -> str:
    color, background, symbol = TIER_PILL_STYLES.get(str(tier), ("#495567", "#E9EDF1", "•"))
    return (
        f'<span style="display:inline-block;white-space:nowrap;font-size:12px;'
        f'font-weight:750;letter-spacing:0.2px;color:{color};background:{background};'
        f'padding:4px 9px;border-radius:6px;">{symbol} {html_escape(str(tier))}</span>'
    )
LOGO_PATHS = {
    "Marriott": DATA_DIR / "assets" / "marriott.png",
    "Hilton": DATA_DIR / "assets" / "hilton.png",
    "Accor": DATA_DIR / "assets" / "accor.png",
}


def img_to_base64(path_str: str) -> str:
    p = Path(path_str)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


LOGO_BASE64 = {group: img_to_base64(path) for group, path in LOGO_PATHS.items()}


def render_logo_label(group: str, text: str, logo_height: int = 18) -> str:
    logo_b64 = LOGO_BASE64.get(group, "")
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:{logo_height}px; width:auto; max-width:72px; object-fit:contain; border-radius:2px;" />'
    else:
        logo_html = f'<span>{GROUP_ICONS.get(group, "🏨")}</span>'
    return (
        f'<div style="display:flex; align-items:center; gap:8px; min-height:24px;">'
        f'{logo_html}'
        f'<span style="font-weight:700; line-height:1.2;">{html_escape(str(text))}</span>'
        f'</div>'
    )


def star_rating_label(value) -> str:
    """공식 성급을 별도로 확인하여 CSV에 넣은 경우에만 별을 표시합니다."""
    value = str(value or "").strip()
    return "★" * int(value) if value in {"1", "2", "3", "4", "5"} else "성급 미확인"


def render_anchor_button(label: str, url: str, bg_color: str, text_color: str = "#FFFFFF") -> str:
    """Use exactly the same dimensions for both external booking links."""
    return f"""<a href="{html_escape(str(url), quote=True)}" target="_blank" rel="noopener noreferrer"
        style="display:flex;width:100%;height:44px;min-height:44px;min-width:0;
        align-items:center;justify-content:center;text-align:center;padding:4px 6px;
        box-sizing:border-box;line-height:1.2;font-size:.76rem;font-weight:650;
        border-radius:9px;text-decoration:none;overflow-wrap:anywhere;
        background:{bg_color};color:{text_color};border:1px solid rgba(0,0,0,.08);">
        {html_escape(str(label))}</a>"""


def localize_hilton_hotel_url(url: str) -> str:
    if not url:
        return ""
    return url.replace("/en/", "/ko/")


def localize_accor_url(url: str) -> str:
    if not url:
        return ""
    return url.replace(".en.shtml", ".ko.shtml")

# 기존 메리어트 달력 URL/정확한 날짜 URL 로직을 그대로 유지함.

def build_calendar_url(
    property_code: str,
    hotel_name: str,
    checkin: date,
    nights: int,
    rooms: int,
    adults: int,
    children: int,
    use_points: bool,
) -> str:
    """월간 가용성 달력(availabilityCalendar.mi) URL 생성"""
    checkout = checkin + timedelta(days=nights)
    params = {
        "propertyCode": property_code.upper(),
        "isSearch": "true",
        "currency": "",
        "costTab": "total",
        "isInternalSearch": "true",
        "vsInitialRequest": "false",
        "searchType": "InCity",
        "for-hotels-nearme": "Near",
        "collapseAccordian": "is-hidden",
        "singleSearch": "true",
        "singleSearchAutoSuggest": "Unmatched",
        "flexibleDateSearchRateDisplay": "false",
        "recordsPerPage": "40",
        "destinationAddress.location": hotel_name,
        "searchRadius": "50",
        "isTransient": "true",
        "destinationAddress.type": "Hotel Name",
        "initialRequest": "true",
        "fromToDate": date.today().strftime("%m/%d/%Y"),
        "fromToDate_submit": checkout.strftime("%m/%d/%Y"),
        "fromDate": checkin.strftime("%Y.%m.%d"),
        "toDate": checkout.strftime("%Y.%m.%d"),
        "toDateDefaultFormat": checkout.strftime("%m/%d/%Y"),
        "fromDateDefaultFormat": checkin.strftime("%m/%d/%Y"),
        "flexibleDateSearch": "true",
        "isHideFlexibleDateCalendar": "false",
        "t-start": checkin.strftime("%Y-%m-%d"),
        "t-end": checkout.strftime("%Y-%m-%d"),
        "isFlexibleDatesOptionSelected": "true",
        "lengthOfStay": str(nights),
        "roomCount": str(rooms),
        "numAdultsPerRoom": str(adults),
        "childrenCount": str(children),
        "clusterCode": "none",
        "numberOfRooms": str(rooms),
        "useRewardsPoints": "true" if use_points else "false",
    }
    return f"https://www.marriott.com/ko/search/availabilityCalendar.mi?{urlencode(params)}#/0/"

def build_exact_date_url(
    property_code: str,
    checkin: date,
    nights: int,
    rooms: int,
    adults: int,
    children: int,
    use_points: bool,
) -> str:
    """특정일 객실 선택(rateListMenu.mi) 다이렉트 URL 생성"""
    checkout = checkin + timedelta(days=nights)
    params = {
        "propertyCode": property_code.upper(),
        "fromDate": checkin.strftime("%Y.%m.%d"),
        "toDate": checkout.strftime("%Y.%m.%d"),
        "fromDateDefaultFormat": checkin.strftime("%m/%d/%Y"),
        "toDateDefaultFormat": checkout.strftime("%m/%d/%Y"),
        "flexibleDateSearch": "false",
        "t-start": checkin.strftime("%Y.%m.%d"),
        "t-end": checkout.strftime("%Y.%m.%d"),
        "lengthOfStay": str(nights),
        "roomCount": str(rooms),
        "numAdultsPerRoom": str(adults),
        "childrenCount": str(children),
        "useRewardsPoints": "true" if use_points else "false",
        "clusterCode": "none",
        "isTransient": "true",
    }
    return f"https://www.marriott.com/ko/reservation/rateListMenu.mi?{urlencode(params)}"



def build_hilton_url(kind, code, checkin, nights, rooms, adults, children, child_ages, use_points):
    """Hilton 예약화면 링크: 7자리 ctyhocn, 날짜 및 객실별 인원 설정.

    아동 연령은 예약 요금에 영향을 주므로 기본값을 임의로 결정하지 않고
    사이드바에서 받은 나이를 그대로 넘깁니다. 최종 예약 화면에서 재확인 필요.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{7}", str(code)):
        raise ValueError("힐튼 코드는 영숫자 7자리여야 합니다.")
    checkout = checkin + timedelta(days=int(nights))
    params = {
        "ctyhocn": code.upper(),
        "arrivalDate": checkin.strftime("%Y-%m-%d"),
        "departureDate": checkout.strftime("%Y-%m-%d"),
        "numRooms": str(rooms),
    }
    for room_num in range(1, int(rooms) + 1):
        params[f"room{room_num}NumAdults"] = str(adults)
        if children:
            params[f"room{room_num}NumChildren"] = str(children)
            params[f"room{room_num}ChildAges"] = ",".join(str(a) for a in child_ages)
    if use_points:
        # Hilton UI에서 포인트 선택이 초기화될 수 있으므로 결과 화면에서 확인.
        params["redeemPts"] = "true"
    destination = "flexibledates" if kind == "calendar" else "rooms"
    return f"https://www.hilton.com/ko/book/reservation/{destination}/?{urlencode(params)}"


def build_accor_url(kind, code, checkin, nights, rooms, adults, children):
    """Accor: 공식 호텔 페이지 + 날짜가 입력된 요금 검색 링크.

    Accor에는 Marriott와 같은 월간 포인트 달력을 가정하지 않음.
    comps는 사이트의 객실 인원 설정에 쓰이는 파라미터. 여러 객실/아동이
    포함된 예약은 링크 이동 후 공식 화면에서 객실/나이를 반드시 확인해야 함.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{4}", str(code)):
        raise ValueError("아코르 호텔 코드는 영숫자 4자리여야 합니다.")
    if kind == "calendar":
        return f"https://all.accor.com/hotel/{code.upper()}/index.ko.shtml"
    params = {
        "dateIn": checkin.strftime("%Y-%m-%d"),
        "nights": str(nights),
        "compositions": str(adults),
        "stayplus": "false",
        "snu": "false",
        "accessibleRooms": "false",
        "hideWDR": "false",
        "hideHotelDetails": "false",
    }
    return f"https://all.accor.com/ssr/app/accor/rates/{code.upper()}/index.ko.shtml?{urlencode(params)}"


def make_links(hotel, checkin, nights, rooms, adults, children, child_ages, use_points):
    group = hotel["brand_group"]
    code = str(hotel["code"])
    if group == "Marriott":
        return (
            build_calendar_url(code, hotel["name"], checkin, nights, rooms, adults, children, use_points),
            build_exact_date_url(code, checkin, nights, rooms, adults, children, use_points),
        )
    if group == "Hilton":
        return (
            build_hilton_url("calendar", code, checkin, nights, rooms, adults, children, child_ages, use_points),
            build_hilton_url("exact", code, checkin, nights, rooms, adults, children, child_ages, use_points),
        )
    if group == "Accor":
        return (
            build_accor_url("calendar", code, checkin, nights, rooms, adults, children),
            build_accor_url("exact", code, checkin, nights, rooms, adults, children),
        )
    raise ValueError(f"지원하지 않는 체인: {group}")


def is_slh_partner(brand) -> bool:
    """SLH 제휴 여부는 제공받은 brand 원문을 기준으로 판단합니다."""
    return bool(re.search(r"\bSLH\b|Small Luxury Hotels", str(brand), re.IGNORECASE))


def country_brand_summary(df, include_upcoming=False):
    """데이터에 등록된 국가별 체인 수. 미수집 국가를 0개로 오해하면 안 됩니다."""
    source = df.copy()
    if not include_upcoming:
        source = source[~((source["brand_group"] == "Hilton") & source["opening_status"].str.startswith("개관 예정"))]
    count = source.groupby(["country", "brand_group"]).size().unstack(fill_value=0)
    for group in GROUPS:
        if group not in count.columns:
            count[group] = 0
    count = count[GROUPS].reset_index()
    count["합계"] = count[GROUPS].sum(axis=1)
    order = {c: i for i, c in enumerate(COUNTRY_FLAGS)}
    return count.sort_values("country", key=lambda col: col.map(lambda c: order.get(c, 999)), kind="stable").reset_index(drop=True)


def filter_hotels(df, selected_groups, countries, regions, tiers, popular_only, keyword, hilton_tiers=None, include_upcoming=False, slh_mode="전체"):

    filtered = df[
        df["brand_group"].isin(selected_groups)
        & df["country"].isin(countries)
        & df["tier"].isin(tiers)
    ].copy()
    # 권역 필터는 제거했습니다. 권역은 결과 화면의 접기·펼치기에만 사용합니다.
    if regions is not None:
        filtered = filtered[filtered["display_region"].isin(regions)]
    if not include_upcoming:
        filtered = filtered[~((filtered["brand_group"] == "Hilton") & filtered["opening_status"].str.startswith("개관 예정"))]
    if hilton_tiers is not None:
        filtered = filtered[(filtered["brand_group"] != "Hilton") | filtered["tier_source"].isin(hilton_tiers)]
    if slh_mode != "전체":
        slh = filtered["brand"].map(is_slh_partner)
        if slh_mode == "SLH 제휴만":
            filtered = filtered[(filtered["brand_group"] != "Hilton") | slh]
        else:
            filtered = filtered[(filtered["brand_group"] != "Hilton") | ~slh]
    if popular_only:
        filtered = filtered[filtered["popular"] == True]
    kw = keyword.strip()
    if kw:
        searchable = ["name", "name_en", "display_name", "code", "brand", "country", "display_region", "region", "area", "province", "address"]
        mask = pd.Series(False, index=filtered.index)
        for col in searchable:
            mask |= filtered[col].fillna("").astype(str).str.contains(kw, case=False, regex=False)
        filtered = filtered[mask]
    return filtered


# 호텔 검색 필터는 「호텔 검색」 버튼으로 적용합니다.
# 날짜·인원·포인트 모드는 변경 즉시 예약 링크에 반영합니다.
def current_filter_snapshot(groups, country, tiers, hilton_tiers, slh, upcoming, popular, query):
    return {
        "groups": list(groups), "country": country,
        "tiers": list(tiers), "hilton_tiers": None if hilton_tiers is None else list(hilton_tiers),
        "slh": slh, "upcoming": bool(upcoming), "popular": bool(popular), "query": query,
    }


def reservation_button_labels(group: str, use_points: bool):
    if group == "Accor":
        return "🏨 호텔 소개", "🛏️ 선택일 객실 조회"
    return ("📅 포인트 달력" if use_points else "📅 유상요금 달력", "🛏️ 선택일 객실 조회")


def render_equal_height_hotel_card(hotel, use_points: bool) -> str:
    """Compact, equal-height card. Tier appears inline directly after the hotel name."""
    group = str(hotel["brand_group"])
    safe = lambda value: html_escape(str(value if value is not None else ""), quote=True)
    logo_b64 = LOGO_BASE64.get(group, "")
    logo = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="{safe(group)}" '
        f'style="height:18px;max-width:64px;width:auto;object-fit:contain;'
        f'vertical-align:middle;margin-right:7px;" />'
        if logo_b64 else f'<span style="margin-right:7px;">{GROUP_ICONS.get(group, "🏨")}</span>'
    )
    badge = render_tier_badge(hotel["tier"])
    code = safe(hotel["code"])
    brand = safe(hotel["brand"])
    area = safe(hotel["area"])
    is_slh = group == "Hilton" and str(hotel.get("hilton_affiliation", "")) == "SLH 제휴"
    extra = []
    if is_slh:
        extra.append('<span style="font-weight:650;color:#76618b;white-space:nowrap;">SLH 제휴</span>')
    if group == "Hilton" and str(hotel.get("opening_status", "")).startswith("개관 예정"):
        extra.append('🏗️ 개관 예정')
    if group == "Marriott" and hotel.get("location_status") == "위치 미확인":
        extra.append('지역 정보 미확인')
    extra_html = (' &nbsp;·&nbsp; ' + ' &nbsp;·&nbsp; '.join(extra)) if extra else ''

    calendar_label, room_label = reservation_button_labels(group, use_points)
    calendar = render_anchor_button(calendar_label, str(hotel["calendar_url"]), BRAND_COLORS[group], BRAND_TEXT_COLORS[group])
    rooms = render_anchor_button(room_label, str(hotel["exact_url"]), "#F7F7F7", "#222222")
    hotel_url = str(hotel.get("hotel_url", "") or "").strip()
    official = (
        f'<a href="{safe(hotel_url)}" target="_blank" rel="noopener noreferrer" '
        f'style="font-size:.70rem;text-decoration:none;color:#777;white-space:nowrap;">🔗 호텔 공홈</a>'
        if hotel_url else ""
    )
    return f"""
<div class="hotel-equal-card" style="box-sizing:border-box;border:1px solid rgba(120,120,120,.23);
    border-radius:12px;padding:12px;height:228px;display:flex;flex-direction:column;
    margin-bottom:12px;overflow:hidden;background:transparent;">
    <div style="font-size:1rem;font-weight:750;line-height:1.35;max-height:76px;
        overflow:hidden;overflow-wrap:anywhere;">
        {logo}<span>{safe(hotel["display_name"])}</span> <span style="display:inline-block;vertical-align:baseline;white-space:nowrap;">{badge}</span>
        <span title="호텔 코드: {code}" style="font-size:8px;color:#fff;">{code}</span>
    </div>
    <div style="font-size:.76rem;color:#70747a;line-height:1.35;max-height:43px;
        margin-top:4px;overflow:hidden;overflow-wrap:anywhere;">
        <b>브랜드</b> : {brand} &nbsp;/&nbsp; <b>위치</b> : {area}{extra_html}
    </div>
    <div style="flex:1;min-height:2px;"></div>
    <div style="min-height:18px;display:flex;align-items:center;justify-content:flex-end;margin-bottom:3px;">{official}</div>
    <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:7px;
       width:100%;height:44px;min-height:44px;align-items:stretch;">{calendar}{rooms}</div>
</div>"""


# 4) 사이드바: 국가 → 포인트 모드 → 날짜·인원 → 공통 유형 → 검색 → 추가조건.
# 메리어트·힐튼·아코르 로고는 사이드바에 표시하지 않습니다.
with st.sidebar:
    st.markdown("""
    <style>
    /* Only booking buttons get button dimensions; never override the official-site link. */
    .hotel-equal-card > div:last-child > a {height:44px !important;min-height:44px !important;padding:4px 6px !important;}
    div[class*="st-key-toggle_"] button,
    div[class*="st-key-toggle_"] button p {font-size:1.08rem !important;font-weight:750 !important;}
    .hotel-equal-card a:hover {filter:brightness(.94);}
    /* 검색 조건에서는 브랜드 전용 컬러를 쓰지 않습니다. */
    [data-testid="stSidebar"] .st-key-apply_hotel_search button {
        background-color: #44484e !important;
        border-color: #44484e !important;
        color: #fff !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] .st-key-apply_hotel_search button:hover {
        background-color: #292d32 !important;
        border-color: #292d32 !important;
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: #e9eaec !important;
        color: #30343a !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] span,
    [data-testid="stSidebar"] [data-baseweb="tag"] svg {
        color: #30343a !important;
        fill: #30343a !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 최상단 국가 → 예약 조건 → 공통 유형 → 검색 → 상세 검색.
    all_countries = [c for c in COUNTRY_FLAGS if c in master["country"].values]
    all_countries += [c for c in master["country"].drop_duplicates() if c not in all_countries]
    selected_country = st.selectbox(
        "🌏 국가 선택", options=all_countries,
        index=all_countries.index("대한민국") if "대한민국" in all_countries else 0,
        format_func=lambda c: f"{COUNTRY_FLAGS.get(c, '')} {c}",
    )
    use_points = st.toggle(
        "💎 메리어트/힐튼 포인트 숙박", value=True,
        help="끄면 유상 숙박으로 조회합니다.",
    )
    date_col, nights_col = st.columns([1.65, 1], gap="small")
    with date_col:
        checkin_date = st.date_input(
            "체크인 날짜", value=date.today() + timedelta(days=30), min_value=date.today(),
        )
    with nights_col:
        nights = int(st.number_input("숙박 일수(박)", min_value=1, max_value=14, value=1))
    col_r, col_a, col_c = st.columns(3, gap="small")
    with col_r:
        rooms = int(st.number_input("객실", min_value=1, max_value=3, value=1))
    with col_a:
        adults = int(st.number_input("성인/객실", min_value=1, max_value=4, value=2))
    with col_c:
        children = int(st.number_input("어린이/객실", min_value=0, max_value=4, value=0))
    child_ages = []
    if children:
        with st.expander("👶 어린이 나이 입력 (힐튼 예약에 필요)", expanded=True):
            st.caption("각 객실의 어린이 나이가 같다고 가정하며 실제 예약 화면에서 확인하세요.")
            for i in range(children):
                child_ages.append(int(st.number_input(
                    f"어린이 {i+1} 나이", min_value=0, max_value=17,
                    value=8, key=f"child_age_{i}"
                )))

    tiers = ["Luxury", "Premium", "Lifestyle", "Select", "Extended Stay"]
    selected_tiers = st.multiselect(
        "호텔 유형 (체인 공통)", options=tiers, default=tiers,
        help="호텔 공식 성급이 아닌 검색용 공통 분류입니다.",
    )
    # UI에서는 검색 버튼을 먼저 보여주고, 하단의 추가조건까지 읽은 뒤 적용합니다.
    search_clicked = st.button(
        "🔎 호텔 검색", type="secondary", use_container_width=True, key="apply_hotel_search"
    )

    enabled_groups = []
    hilton_source_tiers = None
    slh_mode = "전체"
    include_upcoming = False
    popular_only = False
    keyword = ""
    with st.expander("⚙️ 추가 검색 조건", expanded=False):
        st.caption("호텔 체인 · 힐튼 세부 분류 · SLH · 영업 상태 · 검색어")
        for group in GROUPS:
            if st.checkbox(GROUP_LABELS[group], value=True, key=f"show_{group}"):
                enabled_groups.append(group)
        if "Hilton" in enabled_groups:
            hilton_options = ["럭셔리", "프리미엄·풀서비스", "라이프스타일", "셀렉트"]
            hilton_source_tiers = st.multiselect(
                "힐튼 세부 분류", options=hilton_options, default=hilton_options,
                help="힐튼 원본 등급이며 공통 호텔 유형과 구분됩니다.",
            )
            slh_mode = st.radio(
                "힐튼 SLH 제휴 필터", ["전체", "힐튼 일반·계열만", "SLH 제휴만"],
                help="힐튼 원본의 SLH 제휴 표기를 기준으로 구분합니다.",
            )
        include_upcoming = st.checkbox(
            "🏗️ 힐튼 개관 예정 호텔도 보기", value=False,
            help="기본값은 운영 중인 호텔만 표시합니다.",
        )
        popular_only = st.checkbox(
            "⭐ 추천 호텔만 보기", value=False,
            help="CSV에서 popular=TRUE로 표시된 호텔입니다.",
        )
        keyword = st.text_input(
            "호텔명 / 코드 / 지역 검색", placeholder="예: 콘래드, 오사카, SELCICI, 발리"
        )

    draft_filters = current_filter_snapshot(
        enabled_groups, selected_country, selected_tiers,
        hilton_source_tiers, slh_mode, include_upcoming, popular_only, keyword,
    )
    if "applied_hotel_filters" not in st.session_state:
        st.session_state["applied_hotel_filters"] = draft_filters.copy()
    if search_clicked:
        st.session_state["applied_hotel_filters"] = draft_filters.copy()
    if draft_filters != st.session_state["applied_hotel_filters"]:
        st.caption("검색 조건 변경됨 · **호텔 검색**을 눌러 적용")

    with st.expander("🛠️ 직접 호텔 코드로 조회", expanded=False):
        custom_group = st.selectbox("체인", GROUPS, format_func=lambda g: GROUP_LABELS[g])
        custom_code = st.text_input(
            "호텔 코드", placeholder="메리어트 5자리 / 힐튼 7자리 / 아코르 4자리"
        ).strip().upper()
        lengths = {"Marriott": 5, "Hilton": 7, "Accor": 4}
        if custom_code:
            if len(custom_code) != lengths[custom_group] or not custom_code.isalnum():
                st.warning(f"{custom_group} 호텔 코드는 영숫자 {lengths[custom_group]}자리입니다.")
            else:
                custom_hotel = {"brand_group": custom_group, "code": custom_code, "name": custom_code}
                u1, u2 = make_links(custom_hotel, checkin_date, nights, rooms, adults, children, child_ages, use_points)
                x1, x2 = st.columns(2)
                with x1:
                    st.markdown(render_anchor_button(
                        reservation_button_labels(custom_group, use_points)[0], u1,
                        BRAND_COLORS[custom_group], BRAND_TEXT_COLORS[custom_group],
                    ), unsafe_allow_html=True)
                with x2:
                    st.markdown(render_anchor_button(
                        reservation_button_labels(custom_group, use_points)[1], u2,
                        "#F7F7F7", "#222222",
                    ), unsafe_allow_html=True)

# 5) 검색 결과 + 공통 링크 생성
st.title("🏨 아시아 호텔 통합 포인트 & 요금 대시보드")
checkout = checkin_date + timedelta(days=nights)
st.markdown(
    f"**숙박:** {checkin_date:%Y-%m-%d} ~ {checkout:%Y-%m-%d} ({nights}박)  |  "
    f"**객실:** {rooms}개 (객실당 성인 {adults}명, 어린이 {children}명)  |  "
    f"**메리어트/힐튼:** {'💎 포인트 검색' if use_points else '💳 일반 요금 검색'}"
)
st.caption("호텔 목록은 hotels.csv에서 통합 관리합니다. 메리어트 데이터는 2026-11-16 제공 수집본 기준이며, 힐튼 데이터는 제공된 2026-11-16 아시아 25개국 엑셀 기준(개관 예정 포함), 아코르는 기존 목록입니다. 평점·리뷰·미확인 성급은 표시하지 않습니다. 예약 링크 작동은 전수 검증되지 않았습니다.")

applied_filters = st.session_state["applied_hotel_filters"]
applied_country = applied_filters["country"]
filtered_df = filter_hotels(
    master, applied_filters["groups"], [applied_country], None,
    applied_filters["tiers"], applied_filters["popular"], applied_filters["query"],
    applied_filters["hilton_tiers"], applied_filters["upcoming"], applied_filters["slh"],
)
if not filtered_df.empty:
    links = filtered_df.apply(
        lambda row: make_links(row, checkin_date, nights, rooms, adults, children, child_ages, use_points),
        axis=1,
    )
    filtered_df["calendar_url"] = links.apply(lambda pair: pair[0])
    filtered_df["exact_url"] = links.apply(lambda pair: pair[1])
    if "hotel_url" in filtered_df.columns:
        filtered_df["hotel_url"] = filtered_df["hotel_url"].fillna("")
    else:
        filtered_df["hotel_url"] = ""

summary = " / ".join(f"{GROUP_LABELS[g]} {len(master[master['brand_group'] == g])}개" for g in GROUPS)
st.caption(f"등록 호텔: **{len(master)}개** ({summary}) | 현재 검색 결과: **{len(filtered_df)}개**")

if any(g in applied_filters["groups"] for g in ["Hilton", "Accor"]):
    with st.expander("ℹ️ 체인별 예약 링크 주의사항", expanded=False):
        st.markdown(
            "- **메리어트:** 원래 사용하던 월간 가용성 달력과 특정일 요금 링크를 유지했습니다.\n"
            "- **힐튼:** 유연한 날짜 검색 및 객실 검색 링크입니다. 힐튼 공식 안내에서는 포인트 사용을 별도로 선택하도록 안내하므로 결과 화면에서 반드시 확인하세요.\n"
            "- **아코르:** 메리어트식 포인트 달력이 없어 첫 번째 링크는 호텔 소개입니다. 날짜별 요금 검색만 연결합니다.\n"
            "- **어린이·다객실 예약:** 힐튼 아동 나이는 전달하지만, 브랜드별 예약 화면에서 인원과 연령을 재확인해야 합니다. 아코르는 객실 인원을 다시 지정할 수 있습니다."
        )

tab_cards, tab_table, tab_summary = st.tabs(["🗂️ 국가·도시별 카드", "📊 전체 테이블·CSV 다운로드", "🌏 국가별 체인 비교"])
with tab_cards:
    if filtered_df.empty:
        st.warning("현재 조건에 일치하는 호텔이 없습니다. 국가, 호텔 유형 또는 추가 검색 조건을 변경하세요.")
    else:
        st.markdown(country_heading(applied_country, len(filtered_df)), unsafe_allow_html=True)
        # Streamlit의 st.expander는 닫힌 상태에서도 내부 위젯을 모두 생성합니다.
        # 따라서 지역별 버튼+session_state로 구현하여 열린 권역만 카드를 렌더링합니다.
        # 한 국가의 모든 권역은 이 화면에 표시되며, 별도의 페이지 분할은 없습니다.
        # 실제 필터된 호텔 수로 정렬하며, 동률에서는 전체 호텔 수와 권역명을 사용합니다.
        region_sort_choice = st.radio(
            "권역 정렬 기준", ["전체 호텔 수", "메리어트 호텔 수", "힐튼 호텔 수"],
            horizontal=True, key="region_sort_choice",
            help="선택한 체인의 호텔 수를 우선하고 동률이면 전체 호텔 수순으로 표시합니다.",
        )
        region_counts = filtered_df.groupby("display_region").size()
        region_chain_counts = filtered_df.groupby(["display_region", "brand_group"]).size().unstack(fill_value=0)
        selected_chain = {"전체 호텔 수": None, "메리어트 호텔 수": "Marriott", "힐튼 호텔 수": "Hilton"}[region_sort_choice]
        regions_in_order = sorted(
            region_counts.index.tolist(),
            key=lambda region: (
                -int(region_counts[region]) if selected_chain is None else -int(region_chain_counts[selected_chain].get(region, 0)) if selected_chain in region_chain_counts.columns else 0,
                -int(region_counts[region]), region,
            ),
        )
        region_keys = {
            region: f"region_open_{applied_country}_{region}" for region in regions_in_order
        }

        # 첫 방문·국가 변경·호텔 검색 버튼 클릭 시 모든 권역을 접습니다.
        # 같은 국가에서 예약일·포인트 조건만 바꾸면 펼침 상태를 유지합니다.
        if search_clicked or st.session_state.get("active_region_country") != applied_country:
            for key in list(st.session_state.keys()):
                if key.startswith("region_open_"):
                    del st.session_state[key]
            st.session_state["active_region_country"] = applied_country
        for state_key in region_keys.values():
            if state_key not in st.session_state:
                st.session_state[state_key] = False

        st.caption("호텔 검색 후에는 모든 권역이 접힌 상태로 표시됩니다. 보고 싶은 권역을 클릭하여 펼치세요.")
        ctl1, ctl2, _ = st.columns([1, 1, 3])
        with ctl1:
            if st.button("모두 펼치기", key=f"expand_regions_{applied_country}", use_container_width=True):
                for state_key in region_keys.values():
                    st.session_state[state_key] = True
                st.rerun()
        with ctl2:
            if st.button("모두 접기", key=f"collapse_regions_{applied_country}", use_container_width=True):
                for state_key in region_keys.values():
                    st.session_state[state_key] = False
                st.rerun()

        tier_order = {"Luxury": 0, "Premium": 1, "Lifestyle": 2, "Select": 3, "Extended Stay": 4}
        for region in regions_in_order:
            state_key = region_keys[region]
            is_open = st.session_state[state_key]
            arrow = "▼" if is_open else "▶"
            region_df = filtered_df[filtered_df["display_region"] == region]
            chain_counts = region_df["brand_group"].value_counts()
            label = f"{arrow}  {region}  ({int(region_counts[region]):,}개)"
            # st.button은 HTML을 렌더링하지 않으므로, 버튼과 색상 배지를 나란히 배치합니다.
            region_button_col, region_brand_col = st.columns([3, 2], gap="small", vertical_alignment="center")
            with region_button_col:
                if st.button(label, key=f"toggle_{applied_country}_{region}", use_container_width=True):
                    st.session_state[state_key] = not is_open
                    st.rerun()
            with region_brand_col:
                st.markdown(render_region_brand_counts(chain_counts), unsafe_allow_html=True)
            if not is_open:
                continue

            # 호텔 등급: Luxury → Premium → Select → Extended Stay.
            # 같은 등급 안에서는 호텔명을 기준으로 정렬합니다.
            region_df = (
                region_df.assign(_tier_order=region_df["tier"].map(tier_order).fillna(99))
                .sort_values(["_tier_order", "display_name", "code"], kind="stable")
                .drop(columns="_tier_order")
            )
            # 세 장을 한 행으로 묶어 동일한 높이의 카드로 표시합니다.
            # 사진은 추후 검증된 이미지 URL을 확보한 뒤 선택적으로 추가합니다.
            rows = [hotel for _, hotel in region_df.iterrows()]
            for row_start in range(0, len(rows), 3):
                cols = st.columns(3, gap="medium")
                for col_idx, hotel in enumerate(rows[row_start:row_start + 3]):
                    with cols[col_idx]:
                        st.markdown(render_equal_height_hotel_card(hotel, use_points), unsafe_allow_html=True)

with tab_table:
    if filtered_df.empty:
        st.info("테이블에 표시할 호텔이 없습니다.")
    else:
        columns = ["brand_group", "country", "display_region", "area", "tier", "tier_source", "hilton_affiliation", "opening_status", "brand", "display_name", "code", "hotel_url", "calendar_url", "exact_url"]
        view = filtered_df[columns].copy()
        st.dataframe(
            view,
            column_config={
                "brand_group": st.column_config.TextColumn("체인", width="small"),
                "country": st.column_config.TextColumn("국가", width="small"),
                "display_region": st.column_config.TextColumn("표시용 권역", width="medium"),
                "area": st.column_config.TextColumn("위치(원본)", width="medium"),
                "tier": st.column_config.TextColumn("공통 호텔 유형", width="small"),
                "tier_source": st.column_config.TextColumn("원본 브랜드 분류", width="medium"),
                "hilton_affiliation": st.column_config.TextColumn("힐튼 제휴 유형", width="medium"),
                "opening_status": st.column_config.TextColumn("영업 상태", width="medium"),
                "brand": st.column_config.TextColumn("브랜드", width="medium"),
                "display_name": st.column_config.TextColumn("호텔명", width="large"),
                "code": st.column_config.TextColumn("호텔 코드", width="small"),
                "hotel_url": st.column_config.LinkColumn("공식 호텔 페이지", display_text="🔗 열기", width="small"),
                "calendar_url": st.column_config.LinkColumn("포인트/유상 달력 · 호텔 소개", display_text="📅 열기", width="small"),
                "exact_url": st.column_config.LinkColumn("선택일 객실 조회", display_text="🛏️ 열기", width="small"),
            },
            hide_index=True,
            use_container_width=True,
            height=650,
        )
        csv_data = view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 현재 필터링된 호텔 및 URL 목록 CSV 다운로드",
            data=csv_data,
            file_name=f"asia_hotel_links_{checkin_date:%Y%m%d}.csv",
            mime="text/csv",
        )


with tab_summary:
    st.subheader("🌏 국가별 메리어트·힐튼·아코르 등록 호텔 수")
    st.caption("통합 hotels.csv에 등록된 호텔 수입니다. 국가별 수집 범위가 다르므로 시장 전체의 호텔 수나 시장 점유율을 의미하지 않습니다. 메리어트는 일부 국가만 수집되어 있습니다.")
    show_future_summary = st.checkbox("개관 예정 힐튼 호텔도 집계", value=False, key="summary_future")
    counts = country_brand_summary(master, include_upcoming=show_future_summary)
    total_m, total_h, total_a = st.columns(3)
    with total_m:
        st.metric("메리어트 등록", f"{int(counts['Marriott'].sum()):,}개")
    with total_h:
        st.metric("힐튼 등록", f"{int(counts['Hilton'].sum()):,}개")
    with total_a:
        st.metric("아코르 등록", f"{int(counts['Accor'].sum()):,}개")
    st.dataframe(
        counts.rename(columns={"country":"국가·지역", "Marriott":"메리어트", "Hilton":"힐튼", "Accor":"아코르"}),
        hide_index=True, use_container_width=True,
    )
    st.bar_chart(counts.set_index("country")[["Marriott", "Hilton", "Accor"]], stack=False)
    st.download_button(
        "📥 국가별 체인 수 CSV 다운로드",
        data=counts.to_csv(index=False).encode("utf-8-sig"),
        file_name="hotel_country_brand_counts.csv", mime="text/csv",
        key="download_country_brand_summary",
    )
