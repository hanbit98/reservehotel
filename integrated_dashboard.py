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
    "인도네시아": "🇮🇩",
}


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
    "review_count", "brand_code", "source_date", "location_status",
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
    return part

master = load_hotel_data()
INTEGRATED_HOTELS = master.to_dict("records")
GROUP_LABELS = {"Marriott": "메리어트", "Hilton": "힐튼", "Accor": "아코르"}
GROUP_ICONS = {"Marriott": "Ⓜ️", "Hilton": "✨", "Accor": "🪶"}
GROUPS = ["Marriott", "Hilton", "Accor"]
SIDEBAR_LOGO_SIZE = 40  # 원본 200×200, 사이드바에서는 40×40px로 표시
BRAND_COLORS = {"Marriott": "#C73A4A", "Hilton": "#004B87", "Accor": "#9C7B2F"}
BRAND_TEXT_COLORS = {"Marriott": "#FFFFFF", "Hilton": "#FFFFFF", "Accor": "#FFFFFF"}
SIDEBAR_LOGO_PATHS = {
    "Marriott": DATA_DIR / "assets" / "marriott_sidebar.png",
    "Hilton": DATA_DIR / "assets" / "hilton_sidebar.png",
    "Accor": DATA_DIR / "assets" / "accor_sidebar.png",
}
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
    return f"""
    <a href="{html_escape(url, quote=True)}" target="_blank"
       style="display:block; width:100%; text-align:center; padding:0.6rem 0.75rem;
              border-radius:0.55rem; text-decoration:none; font-weight:600;
              background:{bg_color}; color:{text_color}; border:1px solid rgba(0,0,0,0.08);
              box-sizing:border-box;">
       {label}
    </a>
    """


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


def filter_hotels(df, selected_groups, countries, regions, tiers, popular_only, keyword):
    filtered = df[
        df["brand_group"].isin(selected_groups)
        & df["country"].isin(countries)
        & df["display_region"].isin(regions)
        & df["tier"].isin(tiers)
    ].copy()
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


# 4) 사이드바: 호텔 체인 및 국가/지역 필터
with st.sidebar:
    st.header("🔍 숙박 및 조회 조건")
    use_points = st.toggle("💎 메리어트/힐튼 포인트 모드", value=True)
    checkin_date = st.date_input("체크인 날짜", value=date.today() + timedelta(days=30), min_value=date.today())
    nights = int(st.number_input("숙박 일수 (박)", min_value=1, max_value=14, value=1))
    col_r, col_a, col_c = st.columns(3)
    with col_r:
        rooms = int(st.number_input("객실", min_value=1, max_value=3, value=1))
    with col_a:
        adults = int(st.number_input("성인/객실", min_value=1, max_value=4, value=2))
    with col_c:
        children = int(st.number_input("어린이/객실", min_value=0, max_value=4, value=0))
    child_ages = []
    if children:
        with st.expander("👶 어린이 나이 입력 (힐튼 예약에 필요)", expanded=True):
            st.caption("각 객실의 어린이 나이가 같다고 가정합니다. 실제 예약 화면에서 확인하세요.")
            for i in range(children):
                child_ages.append(int(st.number_input(f"어린이 {i+1} 나이", min_value=0, max_value=17, value=8, key=f"child_age_{i}")))

    st.divider()
    st.header("🏢 호텔 체인 및 지역")
    enabled_groups = []
    for group in GROUPS:
        logo_col, check_col = st.columns([0.9, 4.1], gap="small", vertical_alignment="center")
        with logo_col:
            logo_path = SIDEBAR_LOGO_PATHS.get(group)
            if logo_path and logo_path.is_file():
                st.image(str(logo_path), width=SIDEBAR_LOGO_SIZE)
            else:
                st.markdown(GROUP_ICONS[group])
        with check_col:
            if st.checkbox(GROUP_LABELS[group], value=True, key=f"show_{group}"):
                enabled_groups.append(group)

    all_countries = [country for country in COUNTRY_FLAGS if country in master["country"].values]
    all_countries += [country for country in master["country"].drop_duplicates() if country not in all_countries]
    # 국가를 하나만 선택하도록 변경합니다. 국가 변경 시 권역 필터는 자동으로 갱신됩니다.
    selected_country = st.selectbox(
        "국가 선택", options=all_countries,
        index=all_countries.index("대한민국") if "대한민국" in all_countries else 0,
        format_func=lambda c: f"{COUNTRY_FLAGS.get(c, '')} {c}",
    )
    available_region_data = master[
        master["brand_group"].isin(enabled_groups) & master["country"].eq(selected_country)
    ]
    # 국가 및 체인 기준 호텔 수가 많은 권역부터 표시합니다.
    available_regions = available_region_data["display_region"].value_counts().index.tolist()
    selected_regions = st.multiselect(
        "표시용 권역 (호텔 수 순)", options=available_regions,
        default=available_regions, key=f"regions_{selected_country}",
        format_func=lambda r: f"{r} ({(available_region_data['display_region'] == r).sum()}개)",
    )
    tiers = ["Luxury", "Premium", "Select", "Extended Stay"]
    selected_tiers = st.multiselect("등급", options=tiers, default=tiers)
    popular_only = st.checkbox(
        "⭐ 추천 호텔만 보기", value=False,
        help="CSV의 popular=TRUE로 수동 선택한 호텔입니다. 공식 인기 순위 또는 성급과는 무관합니다.",
    )
    keyword = st.text_input("호텔명 / 코드 / 지역 검색", placeholder="예: 콘래드, 오사카, SELCICI, 발리")

    st.divider()
    with st.expander("🛠️ 직접 호텔 코드로 조회"):
        custom_group = st.selectbox("체인", GROUPS, format_func=lambda g: GROUP_LABELS[g])
        custom_code = st.text_input("호텔 코드", placeholder="메리어트 5자리 / 힐튼 7자리 / 아코르 4자리").strip().upper()
        lengths = {"Marriott": 5, "Hilton": 7, "Accor": 4}
        if custom_code:
            if len(custom_code) != lengths[custom_group] or not custom_code.isalnum():
                st.warning(f"{custom_group} 호텔 코드는 영숫자 {lengths[custom_group]}자리입니다.")
            else:
                custom_hotel = {"brand_group": custom_group, "code": custom_code, "name": custom_code}
                u1, u2 = make_links(custom_hotel, checkin_date, nights, rooms, adults, children, child_ages, use_points)
                x1, x2 = st.columns(2)
                with x1:
                    st.markdown(
                        render_anchor_button(
                            "📅 달력/호텔 소개",
                            u1,
                            BRAND_COLORS[custom_group],
                            BRAND_TEXT_COLORS[custom_group],
                        ),
                        unsafe_allow_html=True,
                    )
                with x2:
                    st.markdown(render_anchor_button("🛏️ 날짜별 요금 조회", u2, "#F7F7F7", "#222222"), unsafe_allow_html=True)

# 5) 검색 결과 + 공통 링크 생성
st.title("🏨 아시아 호텔 통합 포인트 & 요금 대시보드")
checkout = checkin_date + timedelta(days=nights)
st.markdown(
    f"**숙박:** {checkin_date:%Y-%m-%d} ~ {checkout:%Y-%m-%d} ({nights}박)  |  "
    f"**객실:** {rooms}개 (객실당 성인 {adults}명, 어린이 {children}명)  |  "
    f"**메리어트/힐튼:** {'💎 포인트 검색' if use_points else '💳 일반 요금 검색'}"
)
st.caption("호텔 목록은 hotels.csv에서 통합 관리합니다. 메리어트 데이터는 2026-11-16 제공 수집본 기준이며, 힐튼·아코르는 기존 목록입니다. 평점·리뷰·미확인 성급은 표시하지 않습니다. 예약 링크 작동은 전수 검증되지 않았습니다.")

filtered_df = filter_hotels(master, enabled_groups, [selected_country], selected_regions, selected_tiers, popular_only, keyword)
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

if any(g in enabled_groups for g in ["Hilton", "Accor"]):
    with st.expander("ℹ️ 체인별 예약 링크 주의사항", expanded=False):
        st.markdown(
            "- **메리어트:** 원래 사용하던 월간 가용성 달력과 특정일 요금 링크를 유지했습니다.\n"
            "- **힐튼:** 유연한 날짜 검색 및 객실 검색 링크입니다. 포인트 모드는 공식 사이트에서 다시 선택해야 할 수 있습니다.\n"
            "- **아코르:** 메리어트식 포인트 달력이 없어 첫 번째 링크는 호텔 소개입니다. 날짜별 요금 검색만 연결합니다.\n"
            "- **어린이·다객실 예약:** 힐튼 아동 나이는 전달하지만, 브랜드별 예약 화면에서 인원과 연령을 재확인해야 합니다. 아코르는 객실 인원을 다시 지정할 수 있습니다."
        )

tab_cards, tab_table = st.tabs(["🗂️ 국가·도시별 카드", "📊 전체 테이블·CSV 다운로드"])
with tab_cards:
    if filtered_df.empty:
        st.warning("현재 조건에 일치하는 호텔이 없습니다. 체인, 국가, 지역, 등급을 변경하세요.")
    else:
        st.header(f"{COUNTRY_FLAGS.get(selected_country, '🌐')} {selected_country} · {len(filtered_df):,}개 호텔")
        # Streamlit의 st.expander는 닫힌 상태에서도 내부 위젯을 모두 생성합니다.
        # 따라서 지역별 버튼+session_state로 구현하여 열린 권역만 카드를 렌더링합니다.
        # 한 국가의 모든 권역은 이 화면에 표시되며, 별도의 페이지 분할은 없습니다.
        region_counts = filtered_df["display_region"].value_counts()
        regions_in_order = region_counts.index.tolist()  # 검색 결과 호텔 수 내림차순
        region_keys = {
            region: f"region_open_{selected_country}_{region}" for region in regions_in_order
        }
        for state_key in region_keys.values():
            if state_key not in st.session_state:
                st.session_state[state_key] = False

        st.caption("권역 제목을 클릭하면 호텔 카드가 표시됩니다. 닫힌 권역의 카드는 렌더링하지 않아 화면이 가벼워집니다.")
        ctl1, ctl2, _ = st.columns([1, 1, 3])
        with ctl1:
            if st.button("모두 펼치기", key=f"expand_regions_{selected_country}", use_container_width=True):
                for state_key in region_keys.values():
                    st.session_state[state_key] = True
                st.rerun()
        with ctl2:
            if st.button("모두 접기", key=f"collapse_regions_{selected_country}", use_container_width=True):
                for state_key in region_keys.values():
                    st.session_state[state_key] = False
                st.rerun()

        for region in regions_in_order:
            state_key = region_keys[region]
            is_open = st.session_state[state_key]
            arrow = "▼" if is_open else "▶"
            label = f"{arrow}  {region}  ({int(region_counts[region]):,}개 호텔)"
            if st.button(label, key=f"toggle_{selected_country}_{region}", use_container_width=True):
                st.session_state[state_key] = not is_open
                st.rerun()
            if not is_open:
                continue

            region_df = filtered_df[filtered_df["display_region"] == region]
            cols = st.columns(3)
            for card_index, (_, hotel) in enumerate(region_df.iterrows()):
                group = hotel["brand_group"]
                with cols[card_index % 3]:
                    with st.container(border=True):
                        st.markdown(render_logo_label(group, hotel["display_name"], logo_height=18), unsafe_allow_html=True)
                        st.caption(f"`{hotel['code']}` | {hotel['brand']} | {hotel['area']} | {hotel['tier']}")
                        if group == "Marriott" and hotel.get("location_status") == "위치 미확인":
                            st.caption("📍 지역 정보 미확인 (원본 누락)")
                        left, right = st.columns(2)
                        with left:
                            primary_label = "🏨 호텔 소개" if group == "Accor" else "📅 날짜 달력"
                            st.markdown(
                                render_anchor_button(primary_label, hotel["calendar_url"], BRAND_COLORS[group], BRAND_TEXT_COLORS[group]),
                                unsafe_allow_html=True,
                            )
                        with right:
                            st.markdown(
                                render_anchor_button("🛏️ 요금 조회", hotel["exact_url"], "#F7F7F7", "#222222"),
                                unsafe_allow_html=True,
                            )
                        if hotel.get("hotel_url"):
                            st.markdown(f"[공식 호텔 상세 페이지]({hotel['hotel_url']})")

with tab_table:
    if filtered_df.empty:
        st.info("테이블에 표시할 호텔이 없습니다.")
    else:
        columns = ["brand_group", "country", "display_region", "area", "tier", "brand", "display_name", "code", "hotel_url", "calendar_url", "exact_url"]
        view = filtered_df[columns].copy()
        st.dataframe(
            view,
            column_config={
                "brand_group": st.column_config.TextColumn("체인", width="small"),
                "country": st.column_config.TextColumn("국가", width="small"),
                "display_region": st.column_config.TextColumn("표시용 권역", width="medium"),
                "area": st.column_config.TextColumn("위치(원본)", width="medium"),
                "tier": st.column_config.TextColumn("브랜드 등급", width="small"),
                "brand": st.column_config.TextColumn("브랜드", width="medium"),
                "display_name": st.column_config.TextColumn("호텔명", width="large"),
                "code": st.column_config.TextColumn("호텔 코드", width="small"),
                "hotel_url": st.column_config.LinkColumn("공식 호텔 페이지", display_text="🔗 열기", width="small"),
                "calendar_url": st.column_config.LinkColumn("달력 / 호텔 소개", display_text="📅 열기", width="small"),
                "exact_url": st.column_config.LinkColumn("특정일 요금", display_text="🛏️ 열기", width="small"),
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
