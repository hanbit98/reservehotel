import streamlit as st
import pandas as pd
from datetime import date, timedelta
from urllib.parse import urlencode

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="글로벌 호텔 통합 포인트 & 요금 대시보드",
    page_icon="🏨",
    layout="wide"
)

# 2. 통합 호텔 마스터 데이터 (메리어트, 힐튼, 아코르)
INTEGRATED_HOTELS = [
    # ==================== Ⓜ️ 메리어트 (Marriott) ====================
    {"brand_group": "Marriott", "country": "대한민국", "region": "서울", "code": "SELLC", "name": "조선 팰리스 서울 강남", "brand": "럭셔리 컬렉션"},
    {"brand_group": "Marriott", "country": "대한민국", "region": "서울", "code": "SELJW", "name": "JW 메리어트 호텔 서울", "brand": "JW 메리어트"},
    {"brand_group": "Marriott", "country": "일본", "region": "오사카", "code": "OSAWH", "name": "W 오사카", "brand": "W 호텔"},
    {"brand_group": "Marriott", "country": "일본", "region": "오사카", "code": "OSAMC", "name": "오사카 메리어트 미야코", "brand": "메리어트"},
    {"brand_group": "Marriott", "country": "태국", "region": "방콕", "code": "BKKXR", "name": "세인트 레지스 방콕", "brand": "세인트 레지스"},
    {"brand_group": "Marriott", "country": "태국", "region": "방콕", "code": "BKKQP", "name": "방콕 메리어트 마르퀴스 퀸즈 파크", "brand": "메리어트"},
    
    # ==================== ✨ 힐튼 (Hilton) ====================
    {"brand_group": "Hilton", "country": "대한민국", "region": "서울", "code": "SELCICI", "name": "콘래드 서울", "brand": "Conrad"},
    {"brand_group": "Hilton", "country": "대한민국", "region": "경기", "code": "SELPADI", "name": "더블트리 바이 힐튼 서울 판교", "brand": "DoubleTree"},
    {"brand_group": "Hilton", "country": "일본", "region": "오사카", "code": "OSACICI", "name": "콘래드 오사카", "brand": "Conrad"},
    {"brand_group": "Hilton", "country": "일본", "region": "도쿄", "code": "TYOCICI", "name": "콘래드 도쿄", "brand": "Conrad"},
    {"brand_group": "Hilton", "country": "태국", "region": "방콕", "code": "BKKWAWA", "name": "월도프 아스토리아 방콕", "brand": "Waldorf Astoria"},
    
    # ==================== 🪶 아코르 (Accor) ====================
    {"brand_group": "Accor", "country": "대한민국", "region": "서울", "code": "B275", "name": "페어몬트 앰배서더 서울", "brand": "Fairmont"},
    {"brand_group": "Accor", "country": "대한민국", "region": "서울", "code": "B6G5", "name": "소피텔 앰배서더 서울", "brand": "Sofitel"},
    {"brand_group": "Accor", "country": "일본", "region": "오사카", "code": "A0D7", "name": "스위소텔 난카이 오사카", "brand": "Swissotel"},
    {"brand_group": "Accor", "country": "태국", "region": "방콕", "code": "A585", "name": "소피텔 방콕 스쿰윗", "brand": "Sofitel"},
    {"brand_group": "Accor", "country": "싱가포르", "region": "싱가포르", "code": "A5B6", "name": "스위소텔 더 스탬포드", "brand": "Swissotel"},
    {"brand_group": "Accor", "country": "싱가포르", "region": "싱가포르", "code": "A4L5", "name": "소피텔 싱가포르 센토사", "brand": "Sofitel"},
]

# 3. URL 생성 함수들
def build_marriott_url(type, code, checkin, nights, adults, children, use_points):
    checkout = checkin + timedelta(days=nights)
    if type == "calendar":
        params = {
            "propertyCode": code.upper(), "isSearch": "true", "isInternalSearch": "true",
            "searchType": "InCity", "singleSearch": "true", "destinationAddress.type": "Hotel Name",
            "initialRequest": "true", "fromDate": checkin.strftime("%Y.%m.%d"),
            "toDate": checkout.strftime("%Y.%m.%d"), "flexibleDateSearch": "true",
            "lengthOfStay": str(nights), "roomCount": "1", "numAdultsPerRoom": str(adults),
            "childrenCount": str(children), "useRewardsPoints": "true" if use_points else "false",
        }
        return f"https://www.marriott.com/ko/search/availabilityCalendar.mi?{urlencode(params)}#/0/"
    else:
        params = {
            "propertyCode": code.upper(), "fromDate": checkin.strftime("%Y.%m.%d"),
            "toDate": checkout.strftime("%Y.%m.%d"), "flexibleDateSearch": "false",
            "lengthOfStay": str(nights), "roomCount": "1", "numAdultsPerRoom": str(adults),
            "childrenCount": str(children), "useRewardsPoints": "true" if use_points else "false",
        }
        return f"https://www.marriott.com/ko/reservation/rateListMenu.mi?{urlencode(params)}"

def build_hilton_url(type, code, checkin, nights, adults, use_points):
    checkout = checkin + timedelta(days=nights)
    params = {
        "ctyhocn": code.upper(), "arrivalDate": checkin.strftime("%Y-%m-%d"),
        "departureDate": checkout.strftime("%Y-%m-%d"), "room1NumAdults": str(adults),
    }
    if use_points: params["redeemPts"] = "true"
    base_path = "flexibledates" if type == "calendar" else "rooms"
    return f"https://www.hilton.com/ko/book/reservation/{base_path}/?{urlencode(params)}"

def build_accor_url(type, code, checkin, nights, adults, children):
    # 아코르는 포인트 달력이 없으므로, calendar 뷰는 호텔 상세페이지로, exact 뷰는 요금 검색페이지로 연결
    checkout = checkin + timedelta(days=nights)
    if type == "calendar":
        return f"https://all.accor.com/hotel/{code.upper()}/index.ko.shtml"
    else:
        # 아코르 공홈 기본 요금 검색 URL 
        # (Accor Plus 할인 옵션 파라미터는 계정 로그인 상태에 따라 자동 적용되거나 별도 캠페인 코드 적용 필요)
        params = {
            "dateIn": checkin.strftime("%Y-%m-%d"), "nights": str(nights),
            "compositions": f"{adults}", "stayplus": "false", "snu": "false"
        }
        return f"https://all.accor.com/ssr/app/accor/rates/{code.upper()}/index.ko.shtml?{urlencode(params)}"


# 4. 사이드바: 통합 필터링
with st.sidebar:
    st.header("🔍 검색 및 필터링")
    
    # 공통 옵션
    default_checkin = date.today() + timedelta(days=30)
    checkin_date = st.date_input("체크인 날짜", value=default_checkin)
    nights = st.number_input("숙박 일수 (박)", min_value=1, max_value=14, value=1)
    
    col1, col2 = st.columns(2)
    with col1: adults = st.number_input("성인", min_value=1, max_value=4, value=2)
    with col2: children = st.number_input("어린이", min_value=0, max_value=4, value=0)
    
    use_points = st.toggle("💎 포인트 숙박 조회 (메리어트/힐튼)", value=True)
    
    st.divider()
    st.subheader("🏢 브랜드 선택")
    show_marriott = st.checkbox("Ⓜ️ 메리어트 (Marriott)", value=True)
    show_hilton = st.checkbox("✨ 힐튼 (Hilton)", value=True)
    show_accor = st.checkbox("🪶 아코르 (Accor)", value=True)
    
    selected_brands = []
    if show_marriott: selected_brands.append("Marriott")
    if show_hilton: selected_brands.append("Hilton")
    if show_accor: selected_brands.append("Accor")
    
    st.divider()
    df_master = pd.DataFrame(INTEGRATED_HOTELS)
    all_countries = df_master["country"].unique().tolist()
    selected_countries = st.multiselect("국가 선택", options=all_countries, default=["대한민국", "일본"])


# 5. 메인 화면: 통합 카드 그리드 뷰
st.title("🏨 글로벌 호텔 통합 대시보드")
st.markdown("선택한 지역에 있는 **메리어트, 힐튼, 아코르** 호텔들의 포인트 효율과 유상 요금을 한눈에 비교하세요.")

# 데이터 필터링 적용
filtered_df = df_master[
    (df_master["brand_group"].isin(selected_brands)) &
    (df_master["country"].isin(selected_countries))
].copy()

if filtered_df.empty:
    st.warning("선택한 조건에 맞는 호텔이 없습니다. 사이드바에서 필터를 조정해 주세요.")
else:
    # 국가별 -> 지역별 반복 렌더링
    for country in selected_countries:
        country_df = filtered_df[filtered_df["country"] == country]
        if country_df.empty: continue
        
        st.header(f"📍 {country}")
        
        for region in country_df["region"].unique():
            st.subheader(f"🏙️ {region}")
            region_df = country_df[country_df["region"] == region]
            
            cols = st.columns(3)
            for idx, (_, hotel) in enumerate(region_df.iterrows()):
                bg = hotel["brand_group"]
                
                # 브랜드별 뱃지 및 디자인 설정
                if bg == "Marriott":
                    badge = "Ⓜ️"
                    btn_type = "primary" # 메리어트는 핑크/레드 톤 강조
                    cal_icon, ext_icon = "📅", "🛏️"
                elif bg == "Hilton":
                    badge = "✨"
                    btn_type = "secondary"
                    cal_icon, ext_icon = "🟦", "🟦" # 힐튼 블루
                else: # Accor
                    badge = "🪶"
                    btn_type = "secondary"
                    cal_icon, ext_icon = "🟨", "🟨" # 아코르 골드
                
                # URL 생성 로직 분기
                if bg == "Marriott":
                    url_cal = build_marriott_url("calendar", hotel["code"], checkin_date, nights, adults, children, use_points)
                    url_ext = build_marriott_url("exact", hotel["code"], checkin_date, nights, adults, children, use_points)
                elif bg == "Hilton":
                    url_cal = build_hilton_url("calendar", hotel["code"], checkin_date, nights, adults, use_points)
                    url_ext = build_hilton_url("exact", hotel["code"], checkin_date, nights, adults, use_points)
                else: # Accor
                    url_cal = build_accor_url("calendar", hotel["code"], checkin_date, nights, adults, children)
                    url_ext = build_accor_url("exact", hotel["code"], checkin_date, nights, adults, children)
                
                # 카드 UI 렌더링
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{badge} {hotel['name']}**")
                        st.caption(f"`{hotel['code']}` | {hotel['brand']}")
                        
                        b1, b2 = st.columns(2)
                        with b1:
                            st.link_button(
                                f"{cal_icon} 달력 보기", url_cal,
                                use_container_width=True, type=btn_type
                            )
                        with b2:
                            st.link_button(
                                f"{ext_icon} 요금 조회", url_ext,
                                use_container_width=True, type="secondary"
                            )
            st.divider()

