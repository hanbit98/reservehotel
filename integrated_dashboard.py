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
    "홍콩·마카오": "🇭🇰",
    "중국": "🇨🇳",
    "태국": "🇹🇭",
    "베트남": "🇻🇳",
    "싱가포르": "🇸🇬",
    "말레이시아": "🇲🇾",
    "인도네시아": "🇮🇩",
}


# 2) 호텔 마스터 데이터는 대시보드 파일과 같은 폴더의 CSV로 관리합니다.
# 배포 시 .py + CSV 3개 + assets 폴더를 함께 업로드하세요.
DATA_DIR = Path(__file__).resolve().parent
CSV_FILES = {
    "Marriott": DATA_DIR / "marriott_hotels.csv",
    "Hilton": DATA_DIR / "hilton_hotels.csv",
    "Accor": DATA_DIR / "accor_hotels.csv",
}
HOTEL_COLUMNS = [
    "brand_group", "country", "region", "area", "code",
    "name", "brand", "tier", "popular", "hotel_url",
]


def load_hotel_data() -> pd.DataFrame:
    """체인별 CSV를 병합하고 필수값·코드·중복을 점검합니다.

    CSV는 UTF-8 / UTF-8 BOM 모두 지원합니다. 코드를 문자로 읽어
    숫자로 시작하는 코드의 앞자리 0을 보존합니다.
    """
    data_frames = []
    issues = []
    for group, csv_path in CSV_FILES.items():
        if not csv_path.is_file():
            issues.append(f"{csv_path.name}: 파일이 없습니다.")
            continue
        try:
            part = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except Exception as exc:
            issues.append(f"{csv_path.name}: CSV 읽기 오류 - {exc}")
            continue
        missing = sorted(set(HOTEL_COLUMNS) - set(part.columns))
        if missing:
            issues.append(f"{csv_path.name}: 필수 열 누락 - {', '.join(missing)}")
            continue
        part = part[HOTEL_COLUMNS].copy()
        for col in HOTEL_COLUMNS:
            part[col] = part[col].astype(str).str.strip()
        part["brand_group"] = part["brand_group"].replace("", group)
        invalid_groups = part[part["brand_group"] != group]
        if not invalid_groups.empty:
            issues.append(f"{csv_path.name}: brand_group은 모든 행에서 {group}이어야 합니다.")
        part["code"] = part["code"].str.upper()
        expected_len = {"Marriott": 5, "Hilton": 7, "Accor": 4}[group]
        valid_codes = part["code"].str.fullmatch(rf"[A-Z0-9]{{{expected_len}}}")
        if (~valid_codes).any():
            issues.append(f"{csv_path.name}: 잘못된 호텔 코드 - {part.loc[~valid_codes, 'code'].head(5).tolist()}")
        required = ["country", "region", "area", "code", "name", "brand", "tier"]
        if part[required].eq("").any().any():
            issues.append(f"{csv_path.name}: 국가, 지역, 호텔 코드/명 등 필수 정보에 빈 칸이 있습니다.")
        popular_lower = part["popular"].str.lower()
        if (~popular_lower.isin(["true", "false", "1", "0", "yes", "no", "y", "n"])).any():
            issues.append(f"{csv_path.name}: popular 열은 TRUE 또는 FALSE를 사용하세요.")
        part["popular"] = popular_lower.isin(["true", "1", "yes", "y"])
        if group == "Hilton":
            part["hotel_url"] = part["hotel_url"].str.replace("/en/", "/ko/", regex=False)
        data_frames.append(part)
    if issues:
        for issue in issues:
            st.error(issue)
        st.stop()
    result = pd.concat(data_frames, ignore_index=True)
    if result.duplicated(["brand_group", "code"]).any():
        duplicates = result[result.duplicated(["brand_group", "code"], keep=False)]
        st.error("중복 호텔 코드가 있습니다: " + ", ".join(duplicates["code"].tolist()))
        st.stop()
    return result


master = load_hotel_data()
INTEGRATED_HOTELS = master.to_dict("records")
GROUP_LABELS = {"Marriott": "Ⓜ️ 메리어트", "Hilton": "✨ 힐튼", "Accor": "🪶 아코르"}
GROUP_ICONS = {"Marriott": "Ⓜ️", "Hilton": "✨", "Accor": "🪶"}
GROUPS = ["Marriott", "Hilton", "Accor"]
BRAND_COLORS = {"Marriott": "#C73A4A", "Hilton": "#004B87", "Accor": "#9C7B2F"}
BRAND_TEXT_COLORS = {"Marriott": "#FFFFFF", "Hilton": "#FFFFFF", "Accor": "#FFFFFF"}
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
        & df["region"].isin(regions)
        & df["tier"].isin(tiers)
    ].copy()
    if popular_only:
        filtered = filtered[filtered["popular"] == True]
    kw = keyword.strip()
    if kw:
        searchable = ["name", "code", "brand", "country", "region", "area"]
        mask = pd.Series(False, index=filtered.index)
        for col in searchable:
            mask |= filtered[col].fillna("").astype(str).str.contains(kw, case=False, regex=False)
        filtered = filtered[mask]
    return filtered


# 4) 사이드바: 기존 필터와 직접 코드 조회 모두 복구
if "hotel_url" in master.columns:
    master["hotel_url"] = master.apply(
        lambda row: localize_hilton_hotel_url(row["hotel_url"]) if row["brand_group"] == "Hilton" else row["hotel_url"],
        axis=1,
    )
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
    st.caption("체인 로고와 함께 표시됩니다.")
    enabled_groups = []
    for group in GROUPS:
        c1, c2 = st.columns([1, 4])
        with c1:
            logo_path = LOGO_PATHS.get(group)
            if logo_path and Path(logo_path).exists():
                st.image(logo_path, width=58)
            else:
                st.markdown(GROUP_ICONS[group])
        with c2:
            if st.checkbox(GROUP_LABELS[group], value=True, key=f"show_{group}"):
                enabled_groups.append(group)

    all_countries = [country for country in COUNTRY_FLAGS if country in master["country"].values]
    all_countries += [country for country in master["country"].drop_duplicates() if country not in all_countries]
    selected_countries = st.multiselect(
        "국가", options=all_countries, default=[c for c in ("대한민국", "일본") if c in all_countries],
        format_func=lambda c: f"{COUNTRY_FLAGS.get(c, '')} {c}",
    )
    available_regions = master[
        master["brand_group"].isin(enabled_groups) & master["country"].isin(selected_countries)
    ]["region"].drop_duplicates().tolist()
    selected_regions = st.multiselect("도시 / 권역", options=available_regions, default=available_regions)
    tiers = ["Luxury", "Premium", "Select"]
    selected_tiers = st.multiselect("등급", options=tiers, default=tiers)
    popular_only = st.checkbox("⭐ 주요 인기 호텔만 보기", value=False)
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
st.caption("예약 페이지로 이동하는 링크 모음입니다. 실시간 포인트/요금을 앱 자체에서 수집·비교하지 않습니다. 최종 조건·금액은 각 호텔 공식 예약 화면에서 확인하세요.")

filtered_df = filter_hotels(master, enabled_groups, selected_countries, selected_regions, selected_tiers, popular_only, keyword)
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
        for country in selected_countries:
            country_df = filtered_df[filtered_df["country"] == country]
            if country_df.empty:
                continue
            st.header(f"{COUNTRY_FLAGS.get(country, '🌐')} {country}")
            for region in country_df["region"].drop_duplicates():
                st.subheader(f"📍 {region}")
                region_df = country_df[country_df["region"] == region]
                cols = st.columns(3)
                for card_index, (_, hotel) in enumerate(region_df.iterrows()):
                    group = hotel["brand_group"]
                    with cols[card_index % 3]:
                        with st.container(border=True):
                            st.markdown(render_logo_label(group, hotel["name"], logo_height=18), unsafe_allow_html=True)
                            st.caption(f"`{hotel['code']}` | {hotel['brand']} | {hotel['area']} | {hotel['tier']}")
                            left, right = st.columns(2)
                            with left:
                                primary_label = "🏨 호텔 소개" if group == "Accor" else "📅 날짜 달력"
                                st.markdown(
                                    render_anchor_button(
                                        primary_label,
                                        hotel["calendar_url"],
                                        BRAND_COLORS[group],
                                        BRAND_TEXT_COLORS[group],
                                    ),
                                    unsafe_allow_html=True,
                                )
                            with right:
                                st.markdown(
                                    render_anchor_button("🛏️ 요금 조회", hotel["exact_url"], "#F7F7F7", "#222222"),
                                    unsafe_allow_html=True,
                                )
                            if hotel.get("hotel_url"):
                                st.markdown(f"[공식 호텔 상세 페이지]({hotel['hotel_url']})")
                st.divider()

with tab_table:
    if filtered_df.empty:
        st.info("테이블에 표시할 호텔이 없습니다.")
    else:
        columns = ["brand_group", "country", "region", "area", "tier", "brand", "name", "code", "calendar_url", "exact_url"]
        view = filtered_df[columns].copy()
        st.dataframe(
            view,
            column_config={
                "brand_group": st.column_config.TextColumn("체인", width="small"),
                "country": st.column_config.TextColumn("국가", width="small"),
                "region": st.column_config.TextColumn("도시/권역", width="small"),
                "area": st.column_config.TextColumn("상세 위치", width="medium"),
                "tier": st.column_config.TextColumn("등급", width="small"),
                "brand": st.column_config.TextColumn("브랜드", width="medium"),
                "name": st.column_config.TextColumn("호텔명", width="large"),
                "code": st.column_config.TextColumn("호텔 코드", width="small"),
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
