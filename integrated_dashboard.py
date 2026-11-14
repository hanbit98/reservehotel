"""메리어트 + 힐튼 + 아코르 아시아 호텔 예약 링크 대시보드.

기존 marriott_asia_dashboard.py의 메리어트 목록/URL 함수를 유지하고,
타 브랜드 식별코드, 예약 링크, 검색 및 내보내기를 통합한 독립 실행형 Streamlit 앱.
공식 예약 사이트가 URL 파라미터를 변경하거나 로그인/쿠키를 요구할 수 있음.
이 앱은 실시간 호텔 가격을 스크래핑하거나 예약 가능 여부를 판단하지 않음.
"""
import re
from datetime import date, timedelta
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="아시아 호텔 통합 포인트 & 요금 조회 대시보드",
    page_icon="🏨",
    layout="wide",
)

# 1) 원본 메리어트 호텔 147개 전체 보존 (기존 코드/권역/티어/인기 플래그)

MARRIOTT_HOTELS = [
    # ==================== 🇰🇷 대한민국 (39개) ====================
    {"country": "대한민국", "region": "서울", "area": "강남/역삼", "code": "SELLC", "name": "조선 팰리스 서울 강남", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "반포", "code": "SELJW", "name": "JW 메리어트 호텔 서울", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "동대문", "code": "SELDP", "name": "JW 메리어트 동대문 스퀘어 서울", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "소공동/시청", "code": "SELWI", "name": "웨스틴 조선 서울", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "삼성/코엑스", "code": "SELWG", "name": "웨스틴 서울 파르나스", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "시청", "code": "SELAK", "name": "더 플라자 서울", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "홍대", "code": "SELSA", "name": "라이즈(RYSE) 홍대", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "명동", "code": "SELMM", "name": "르메르디앙 서울 명동", "brand": "르메르디앙", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "여의도", "code": "SELER", "name": "여의도 파크 센터 서울 (MEA)", "brand": "이그제큐티브 아파트먼트", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "서울", "area": "신도림", "code": "SELTX", "name": "더 링크 서울", "brand": "트리뷰트 포트폴리오", "tier": "Premium", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "강남/역삼", "code": "SELAG", "name": "AC 호텔 바이 메리어트 서울 강남", "brand": "AC 호텔", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "명동/남대문", "code": "SELSN", "name": "코트야드 서울 명동", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "영등포", "code": "SELCY", "name": "코트야드 서울 타임스퀘어", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "마곡", "code": "SELCS", "name": "코트야드 서울 보타닉 파크", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "청담", "code": "SELAL", "name": "알로프트 서울 강남", "brand": "알로프트", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "명동", "code": "SELMO", "name": "알로프트 서울 명동", "brand": "알로프트", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "명동", "code": "SELMX", "name": "목시 서울 명동", "brand": "목시", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "종로/익선동", "code": "SELOX", "name": "목시 서울 인사동", "brand": "목시", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "서울역", "code": "SELFP", "name": "포포인츠 바이 쉐라톤 조선 서울역", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "을지로", "code": "SELFD", "name": "포포인츠 바이 쉐라톤 조선 서울 명동", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "신사", "code": "SELFG", "name": "포포인츠 바이 쉐라톤 서울 강남", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "구로", "code": "SELFU", "name": "포포인츠 바이 쉐라톤 서울 구로", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "서울", "area": "영등포", "code": "SELFI", "name": "페어필드 바이 메리어트 서울", "brand": "페어필드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "경기·인천", "area": "인천 송도", "code": "SELGI", "name": "쉐라톤 그랜드 인천 호텔", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "경기·인천", "area": "인천 영종도", "code": "SELNH", "name": "네스트 호텔 인천", "brand": "디자인 호텔스", "tier": "Premium", "popular": False},
    {"country": "대한민국", "region": "경기·인천", "area": "성남 판교", "code": "SELAY", "name": "그래비티 조선 서울 판교", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "경기·인천", "area": "성남 판교", "code": "SELPN", "name": "코트야드 서울 판교", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "경기·인천", "area": "수원 광교", "code": "SELCW", "name": "코트야드 수원", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "경기·인천", "area": "평택 고덕", "code": "CJJPY", "name": "코트야드 평택", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "경기·인천", "area": "수원 인계동", "code": "SELFO", "name": "포포인츠 바이 쉐라톤 수원", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "제주", "area": "서귀포", "code": "CJUJU", "name": "JW 메리어트 제주 리조트 & 스파", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "대한민국", "region": "제주", "area": "서귀포 안덕", "code": "CJUMJ", "name": "제주신화월드 메리어트 리조트", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "부산·지방", "area": "부산 해운대", "code": "PUSWI", "name": "웨스틴 조선 부산", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "부산·지방", "area": "부산 해운대", "code": "PUSAH", "name": "아늑 시그니처 부산 해운대", "brand": "시리즈 바이 메리어트", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "부산·지방", "area": "부산 해운대", "code": "PUSFI", "name": "페어필드 바이 메리어트 부산", "brand": "페어필드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "부산·지방", "area": "부산 송도", "code": "PUSFB", "name": "페어필드 바이 메리어트 부산 송도 비치", "brand": "페어필드", "tier": "Select", "popular": False},
    {"country": "대한민국", "region": "부산·지방", "area": "대구 동구", "code": "TAEMC", "name": "대구 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "부산·지방", "area": "대전 유성", "code": "CJJAK", "name": "호텔 오노마 대전", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},
    {"country": "대한민국", "region": "부산·지방", "area": "세종", "code": "CJJCY", "name": "코트야드 세종", "brand": "코트야드", "tier": "Select", "popular": False},

    # ==================== 🇯🇵 일본 (29개) ====================
    {"country": "일본", "region": "오사카", "area": "우메다", "code": "OSARZ", "name": "더 리츠칼튼 오사카", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "오사카", "area": "신사이바시/혼마치", "code": "OSAXR", "name": "세인트 레지스 오사카", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "오사카", "area": "신사이바시", "code": "OSAWH", "name": "W 오사카", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "오사카", "area": "텐노지/아베노", "code": "OSAMC", "name": "오사카 메리어트 미야코 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "오사카", "area": "우메다", "code": "OSAWI", "name": "웨스틴 호텔 오사카", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "오사카", "area": "우메다/도지마", "code": "OSAAK", "name": "오사카 스테이션 호텔 (오토그래프)", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "오사카", "area": "혼마치", "code": "OSACY", "name": "코트야드 오사카 혼마치", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "일본", "region": "오사카", "area": "신오사카", "code": "OSACS", "name": "코트야드 신오사카 스테이션", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "일본", "region": "오사카", "area": "우메다", "code": "OSAFU", "name": "포포인츠 플렉스 바이 쉐라톤 오사카 우메다", "brand": "포포인츠 플렉스", "tier": "Select", "popular": False},
    {"country": "일본", "region": "오사카", "area": "난바", "code": "OSAFI", "name": "페어필드 바이 메리어트 오사카 난바", "brand": "페어필드", "tier": "Select", "popular": False},
    {"country": "일본", "region": "교토·나라", "area": "교토 가모가와", "code": "UKYRZ", "name": "더 리츠칼튼 교토", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "교토·나라", "area": "교토 니조성", "code": "UKYLC", "name": "호테루 더 미츠이 교토", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "교토·나라", "area": "교토 히가시야마", "code": "UKYWI", "name": "웨스틴 미야코 교토", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "교토·나라", "area": "나라", "code": "OSAJP", "name": "JW 메리어트 호텔 나라", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 롯폰기", "code": "TYORZ", "name": "더 리츠칼튼 도쿄", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 도라노몬", "code": "TYOET", "name": "도쿄 에디션 도라노몬", "brand": "에디션", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 기오이초", "code": "TYOLC", "name": "더 프린스 갤러리 도쿄 기오이초", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 에비스", "code": "TYOWI", "name": "웨스틴 호텔 도쿄", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 다케시바", "code": "TYOAM", "name": "메즘 도쿄 (오토그래프 컬렉션)", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "요코하마 미나토미라이", "code": "TYOWY", "name": "웨스틴 호텔 요코하마", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "도쿄·요코하마", "area": "도쿄 긴자", "code": "TYOAC", "name": "AC 호텔 바이 메리어트 도쿄 긴자", "brand": "AC 호텔", "tier": "Select", "popular": False},
    {"country": "일본", "region": "홋카이도", "area": "니세코", "code": "CTSRZ", "name": "히가시야마 니세코 빌리지 리츠칼튼 리저브", "brand": "리츠칼튼 리저브", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "홋카이도", "area": "루스츠", "code": "CTSWR", "name": "웨스틴 루스츠 리조트", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "홋카이도", "area": "삿포로 나카지마공원", "code": "CTSCY", "name": "코트야드 바이 메리어트 삿포로", "brand": "코트야드", "tier": "Select", "popular": True},
    {"country": "일본", "region": "홋카이도", "area": "삿포로 스스키노", "code": "CTSFI", "name": "페어필드 바이 메리어트 삿포로", "brand": "페어필드", "tier": "Select", "popular": False},
    {"country": "일본", "region": "오키나와·규슈", "area": "오키나와 나고", "code": "OKARZ", "name": "더 리츠칼튼 오키나와", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "오키나와·규슈", "area": "오키나와 미야코지마", "code": "OKAIL", "name": "이라프 SUI 럭셔리 컬렉션 미야코 오키나와", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "일본", "region": "오키나와·규슈", "area": "오키나와 온나손", "code": "OKASI", "name": "쉐라톤 오키나와 선마리나 리조트", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "일본", "region": "오키나와·규슈", "area": "후쿠오카 텐진", "code": "FUKRZ", "name": "더 리츠칼튼 후쿠오카", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},

    # ==================== 🇹🇼 대만 (9개) ====================
    {"country": "대만", "region": "타이베이", "area": "신이구 (101 인근)", "code": "TPEWH", "name": "W 타이베이", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "대만", "region": "타이베이", "area": "다즈", "code": "TPEMC", "name": "타이베이 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "대만", "region": "타이베이", "area": "중정구", "code": "TPESI", "name": "쉐라톤 그랜드 타이베이 호텔", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "대만", "region": "타이베이", "area": "신이구", "code": "TPEMD", "name": "르메르디앙 타이베이", "brand": "르메르디앙", "tier": "Premium", "popular": True},
    {"country": "대만", "region": "타이베이", "area": "다안구", "code": "TPEAK", "name": "호텔 프로버브 타이베이 (디자인 호텔스)", "brand": "디자인 호텔스", "tier": "Premium", "popular": False},
    {"country": "대만", "region": "타이베이", "area": "난강역", "code": "TPECY", "name": "코트야드 타이베이", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대만", "region": "타이베이", "area": "중산/민성", "code": "TPECD", "name": "코트야드 타이베이 다운타운", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "대만", "region": "가오슝·기타", "area": "가오슝 구산구", "code": "KHHMC", "name": "가오슝 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "대만", "region": "가오슝·기타", "area": "타오위안 다시", "code": "TPEWI", "name": "웨스틴 타오위안 리조트", "brand": "웨스틴", "tier": "Premium", "popular": True},

    # ==================== 🇭🇰 홍콩 · 마카오 (13개) ====================
    {"country": "홍콩·마카오", "region": "홍콩", "area": "침사추이/구룡", "code": "HKGKW", "name": "더 리츠칼튼 홍콩", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "완차이", "code": "HKGXR", "name": "세인트 레지스 홍콩", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "구룡역", "code": "HKGWH", "name": "W 홍콩", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "애드미럴티", "code": "HKGDT", "name": "JW 메리어트 호텔 홍콩", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "침사추이", "code": "HKGSI", "name": "쉐라톤 홍콩 호텔 & 타워", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "완차이", "code": "HKGHV", "name": "르네상스 홍콩 하버 뷰 호텔", "brand": "르네상스", "tier": "Premium", "popular": True},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "오션파크", "code": "HKGOP", "name": "홍콩 오션파크 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": False},
    {"country": "홍콩·마카오", "region": "홍콩", "area": "사이잉푼", "code": "HKGCY", "name": "코트야드 홍콩", "brand": "코트야드", "tier": "Select", "popular": False},
    {"country": "홍콩·마카오", "region": "마카오", "area": "코타이 갤럭시", "code": "MFMJW", "name": "JW 메리어트 호텔 마카오", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "마카오", "area": "코타이 갤럭시", "code": "MFMRZ", "name": "더 리츠칼튼 마카오", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "마카오", "area": "코타이 런더너", "code": "MFMXR", "name": "세인트 레지스 마카오", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "마카오", "area": "코타이 스튜디오시티", "code": "MFMWH", "name": "W 마카오 - 스튜디오 시티", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "홍콩·마카오", "region": "마카오", "area": "코타이 런더너", "code": "MFMLC", "name": "더 런더너 그랜드 (럭셔리 컬렉션)", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},

    # ==================== 🇨🇳 중국 (10개) ====================
    {"country": "중국", "region": "상하이", "area": "푸동 루자쭈이", "code": "SHARZ", "name": "더 리츠칼튼 상하이 푸동", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "상하이", "area": "노스번드(와이탄)", "code": "SHAWH", "name": "W 상하이 - 더 번드", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "상하이", "area": "난징동루/와이탄", "code": "SHAEB", "name": "더 상하이 에디션", "brand": "에디션", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "상하이", "area": "인민광장", "code": "SHAJW", "name": "JW 메리어트 호텔 상하이 투모로우 스퀘어", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "상하이", "area": "와이탄", "code": "SHAWI", "name": "웨스틴 번드 센터 상하이", "brand": "웨스틴", "tier": "Premium", "popular": False},
    {"country": "중국", "region": "베이징", "area": "차오양", "code": "BJSRZ", "name": "더 리츠칼튼 베이징", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "베이징", "area": "젠궈먼", "code": "BJSXR", "name": "세인트 레지스 베이징", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "베이징", "area": "차오양", "code": "BJSJW", "name": "JW 메리어트 호텔 베이징", "brand": "JW 메리어트", "tier": "Luxury", "popular": False},
    {"country": "중국", "region": "하이난(싼야)", "area": "하이탕베이", "code": "SYXEB", "name": "더 싼야 에디션", "brand": "에디션", "tier": "Luxury", "popular": True},
    {"country": "중국", "region": "하이난(싼야)", "area": "야롱베이", "code": "SYXRZ", "name": "더 리츠칼튼 싼야, 야롱베이", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},

    # ==================== 🇹🇭 태국 (15개) ====================
    {"country": "태국", "region": "방콕", "area": "룸피니/원방콕", "code": "BKKRZ", "name": "더 리츠칼튼 방콕", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "방콕", "area": "랏차담리", "code": "BKKXR", "name": "세인트 레지스 방콕", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "방콕", "area": "수쿰윗 아속", "code": "BKKLC", "name": "쉐라톤 그랜드 수쿰윗 (럭셔리 컬렉션)", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "방콕", "area": "스쿰윗 나나", "code": "BKKDT", "name": "JW 메리어트 호텔 방콕", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "방콕", "area": "사톤", "code": "BKKWH", "name": "W 방콕", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "방콕", "area": "프롬퐁", "code": "BKKQP", "name": "방콕 메리어트 마르퀴스 퀸즈 파크", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "태국", "region": "방콕", "area": "수라웡", "code": "BKKSP", "name": "방콕 메리어트 호텔 더 수라웡세", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "태국", "region": "방콕", "area": "통로", "code": "BKKMS", "name": "방콕 메리어트 호텔 수쿰윗", "brand": "메리어트", "tier": "Premium", "popular": False},
    {"country": "태국", "region": "방콕", "area": "차오프라야 강변", "code": "BKKSI", "name": "로얄 오키드 쉐라톤 리버사이드 호텔", "brand": "쉐라톤", "tier": "Premium", "popular": False},
    {"country": "태국", "region": "치앙마이", "area": "나이트바자", "code": "CNXMC", "name": "치앙마이 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "태국", "region": "치앙마이", "area": "창클란", "code": "CNXMD", "name": "멜리아/르메르디앙 치앙마이 권역", "brand": "르메르디앙", "tier": "Premium", "popular": False},
    {"country": "태국", "region": "푸켓·코사무이", "area": "푸켓 마이카오", "code": "HKTJW", "name": "JW 메리어트 푸켓 리조트 & 스파", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "푸켓·코사무이", "area": "푸켓 카론/파통", "code": "HKTMD", "name": "르메르디앙 푸켓 비치 리조트", "brand": "르메르디앙", "tier": "Premium", "popular": True},
    {"country": "태국", "region": "푸켓·코사무이", "area": "코사무이", "code": "USMRZ", "name": "더 리츠칼튼 코사무이", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "태국", "region": "푸켓·코사무이", "area": "코사무이 매남", "code": "USMWH", "name": "W 코사무이", "brand": "W 호텔", "tier": "Luxury", "popular": True},

    # ==================== 🇻🇳 베트남 (9개) ====================
    {"country": "베트남", "region": "푸꾸옥·나트랑", "area": "푸꾸옥 켐비치", "code": "PQCJW", "name": "JW 메리어트 푸꾸옥 에메랄드 베이 리조트", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "베트남", "region": "푸꾸옥·나트랑", "area": "푸꾸옥 혼똔섬", "code": "PQCSI", "name": "쉐라톤 푸꾸옥 롱비치 리조트", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "베트남", "region": "푸꾸옥·나트랑", "area": "나트랑 혼트레섬", "code": "CXRMC", "name": "나트랑 메리어트 리조트 & 스파 (혼트레 아일랜드)", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "베트남", "region": "푸꾸옥·나트랑", "area": "나트랑 시내", "code": "CXRSI", "name": "쉐라톤 나트랑 호텔 & 스파", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "베트남", "region": "다낭", "area": "논누옥 비치", "code": "DADSI", "name": "쉐라톤 그랜드 다낭 리조트", "brand": "쉐라톤", "tier": "Premium", "popular": True},
    {"country": "베트남", "region": "다낭", "area": "논누옥 비치", "code": "DADMC", "name": "다낭 메리어트 리조트 & 스파", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "베트남", "region": "다낭", "area": "미케비치", "code": "DADFP", "name": "포포인츠 바이 쉐라톤 다낭", "brand": "포포인츠", "tier": "Select", "popular": False},
    {"country": "베트남", "region": "하노이·호치민", "area": "하노이 미딩", "code": "HANJW", "name": "JW 메리어트 호텔 하노이", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "베트남", "region": "하노이·호치민", "area": "호치민 1군", "code": "SGNAK", "name": "빈펄 랜드마크 81 오토그래프 컬렉션", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": True},

    # ==================== 🇸🇬 싱가포르 (8개) ====================
    {"country": "싱가포르", "region": "싱가포르", "area": "오차드/탕린", "code": "SINXR", "name": "세인트 레지스 싱가포르", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "오차드", "code": "SINEB", "name": "더 싱가포르 에디션", "brand": "에디션", "tier": "Luxury", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "사우스비치/시티홀", "code": "SINJW", "name": "JW 메리어트 호텔 싱가포르 사우스 비치", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "센토사 코브", "code": "SINWH", "name": "W 싱가포르 - 센토사 코브", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "마리나베이", "code": "SINWI", "name": "웨스틴 싱가포르", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "오차드 로드", "code": "SINDT", "name": "싱가포르 메리어트 탕 플라자 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},
    {"country": "싱가포르", "region": "싱가포르", "area": "차이나타운/부기스", "code": "SINAK", "name": "더 베가본드 클럽 / 맥스웰 리저브 (오토그래프)", "brand": "오토그래프 컬렉션", "tier": "Premium", "popular": False},
    {"country": "싱가포르", "region": "싱가포르", "area": "노베나", "code": "SINCY", "name": "코트야드 싱가포르 노베나", "brand": "코트야드", "tier": "Select", "popular": False},

    # ==================== 🇲🇾 말레이시아 (7개) ====================
    {"country": "말레이시아", "region": "쿠알라룸푸르", "area": "KL 센트럴", "code": "KULXR", "name": "세인트 레지스 쿠알라룸푸르", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "말레이시아", "region": "쿠알라룸푸르", "area": "부킷 빈탕", "code": "KULRZ", "name": "더 리츠칼튼 쿠알라룸푸르", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "말레이시아", "region": "쿠알라룸푸르", "area": "KLCC", "code": "KULWH", "name": "W 쿠알라룸푸르", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "말레이시아", "region": "쿠알라룸푸르", "area": "부킷 빈탕", "code": "KULDT", "name": "JW 메리어트 호텔 쿠알라룸푸르", "brand": "JW 메리어트", "tier": "Luxury", "popular": True},
    {"country": "말레이시아", "region": "쿠알라룸푸르", "area": "부킷 빈탕", "code": "KULWI", "name": "웨스틴 쿠알라룸푸르", "brand": "웨스틴", "tier": "Premium", "popular": False},
    {"country": "말레이시아", "region": "랑카위·코타키나발루", "area": "랑카위", "code": "LGKRZ", "name": "더 리츠칼튼 랑카위", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "말레이시아", "region": "랑카위·코타키나발루", "area": "코타키나발루", "code": "BKIMC", "name": "코타키나발루 메리어트 호텔", "brand": "메리어트", "tier": "Premium", "popular": True},

    # ==================== 🇮🇩 인도네시아 (8개) ====================
    {"country": "인도네시아", "region": "발리", "area": "우붓", "code": "DPSUB", "name": "만다파, 리츠칼튼 리저브 (우붓)", "brand": "리츠칼튼 리저브", "tier": "Luxury", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "누사두아", "code": "DPSXR", "name": "세인트 레지스 발리 리조트", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "누사두아", "code": "DPSAZ", "name": "더 리츠칼튼 발리", "brand": "리츠칼튼", "tier": "Luxury", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "스미냑", "code": "DPSWH", "name": "W 발리 - 스미냑", "brand": "W 호텔", "tier": "Luxury", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "누사두아", "code": "DPSLC", "name": "더 라구나 럭셔리 컬렉션 리조트 발리", "brand": "럭셔리 컬렉션", "tier": "Luxury", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "누사두아", "code": "DPSWI", "name": "웨스틴 리조트 누사두아 발리", "brand": "웨스틴", "tier": "Premium", "popular": True},
    {"country": "인도네시아", "region": "발리", "area": "꾸따", "code": "DPSSI", "name": "쉐라톤 발리 꾸따 리조트", "brand": "쉐라톤", "tier": "Premium", "popular": False},
    {"country": "인도네시아", "region": "자카르타", "area": "SCBD", "code": "JKTXR", "name": "세인트 레지스 자카르타", "brand": "세인트 레지스", "tier": "Luxury", "popular": True},
]

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


# 2) 힐튼/아코르 호텔. 호텔 식별코드는 각 체인의 공식 호텔 페이지와 대조.
# 체인별 대표 호텔의 표본이며, 전체 체인 호텔 목록을 의미하지 않습니다.
EXTRA_HOTELS = [
    {"brand_group":"Hilton", "country":"대한민국", "region":"서울", "area":"여의도", "code":"SELCICI", "name":"콘래드 서울", "brand":"Conrad", "tier":"Luxury", "popular":True, "hotel_url":"https://www.hilton.com/en/hotels/selcici-conrad-seoul/"},
    {"brand_group":"Hilton", "country":"대한민국", "region":"경기·인천", "area":"성남 판교", "code":"SELSEDI", "name":"더블트리 바이 힐튼 서울 판교", "brand":"DoubleTree", "tier":"Premium", "popular":False, "hotel_url":"https://www.hilton.com/en/hotels/selsedi-doubletree-seoul-pangyo/"},
    {"brand_group":"Hilton", "country":"일본", "region":"오사카", "area":"나카노시마", "code":"OSACICI", "name":"콘래드 오사카", "brand":"Conrad", "tier":"Luxury", "popular":True, "hotel_url":"https://www.hilton.com/en/hotels/osacici-conrad-osaka/"},
    {"brand_group":"Hilton", "country":"일본", "region":"도쿄·요코하마", "area":"도쿄 시오도메", "code":"TYOCICI", "name":"콘래드 도쿄", "brand":"Conrad", "tier":"Luxury", "popular":True, "hotel_url":"https://www.hilton.com/en/hotels/tyocici-conrad-tokyo/"},
    {"brand_group":"Hilton", "country":"태국", "region":"방콕", "area":"랏차담리", "code":"BKKWAWA", "name":"월도프 아스토리아 방콕", "brand":"Waldorf Astoria", "tier":"Luxury", "popular":True, "hotel_url":"https://www.hilton.com/en/hotels/bkkwawa-waldorf-astoria-bangkok/"},
    {"brand_group":"Accor", "country":"대한민국", "region":"서울", "area":"여의도", "code":"B200", "name":"페어몬트 앰배서더 서울", "brand":"Fairmont", "tier":"Luxury", "popular":True},
    {"brand_group":"Accor", "country":"대한민국", "region":"서울", "area":"잠실", "code":"B220", "name":"소피텔 앰배서더 서울", "brand":"Sofitel", "tier":"Luxury", "popular":True},
    {"brand_group":"Accor", "country":"일본", "region":"오사카", "area":"난바", "code":"A5C3", "name":"스위소텔 난카이 오사카", "brand":"Swissotel", "tier":"Premium", "popular":True},
    {"brand_group":"Accor", "country":"태국", "region":"방콕", "area":"수쿰윗", "code":"5213", "name":"소피텔 방콕 스쿰윗", "brand":"Sofitel", "tier":"Luxury", "popular":True},
    {"brand_group":"Accor", "country":"싱가포르", "region":"싱가포르", "area":"시티홀/마리나베이", "code":"A5D3", "name":"스위소텔 더 스탬포드", "brand":"Swissotel", "tier":"Premium", "popular":True},
    {"brand_group":"Accor", "country":"싱가포르", "region":"싱가포르", "area":"센토사", "code":"9474", "name":"소피텔 싱가포르 센토사", "brand":"Sofitel", "tier":"Luxury", "popular":True},
]

INTEGRATED_HOTELS = [dict(h, brand_group="Marriott") for h in MARRIOTT_HOTELS] + EXTRA_HOTELS
GROUP_LABELS = {"Marriott": "Ⓜ️ 메리어트", "Hilton": "✨ 힐튼", "Accor": "🪶 아코르"}
GROUP_ICONS = {"Marriott": "Ⓜ️", "Hilton": "✨", "Accor": "🪶"}
GROUPS = ["Marriott", "Hilton", "Accor"]

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
    return f"https://www.hilton.com/en/book/reservation/{destination}/?{urlencode(params)}"


def build_accor_url(kind, code, checkin, nights, rooms, adults, children):
    """Accor: 공식 호텔 페이지 + 날짜가 입력된 요금 검색 링크.

    Accor에는 Marriott와 같은 월간 포인트 달력을 가정하지 않음.
    comps는 사이트의 객실 인원 설정에 쓰이는 파라미터. 여러 객실/아동이
    포함된 예약은 링크 이동 후 공식 화면에서 객실/나이를 반드시 확인해야 함.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{4}", str(code)):
        raise ValueError("아코르 호텔 코드는 영숫자 4자리여야 합니다.")
    if kind == "calendar":
        return f"https://all.accor.com/hotel/{code.upper()}/index.en.shtml"
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
    return f"https://all.accor.com/ssr/app/accor/rates/{code.upper()}/index.en.shtml?{urlencode(params)}"


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
master = pd.DataFrame(INTEGRATED_HOTELS)
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
        if st.checkbox(GROUP_LABELS[group], value=True, key=f"show_{group}"):
            enabled_groups.append(group)

    all_countries = [country for country in COUNTRY_FLAGS if country in master["country"].values]
    selected_countries = st.multiselect(
        "국가", options=all_countries, default=["대한민국", "일본"],
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
                st.link_button("📅 달력/호텔 소개", u1, use_container_width=True)
                st.link_button("🛏️ 날짜별 요금 조회", u2, use_container_width=True)

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
    filtered_df["hotel_url"] = filtered_df["hotel_url"].fillna("") if "hotel_url" in filtered_df.columns else ""

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
                            st.markdown(f"**{GROUP_ICONS[group]} {hotel['name']}**")
                            st.caption(f"`{hotel['code']}` | {hotel['brand']} | {hotel['area']} | {hotel['tier']}")
                            left, right = st.columns(2)
                            with left:
                                st.link_button(
                                    "🏨 호텔 소개" if group == "Accor" else "📅 날짜 달력",
                                    hotel["calendar_url"],
                                    use_container_width=True,
                                    type="primary" if group == "Marriott" else "secondary",
                                )
                            with right:
                                st.link_button("🛏️ 요금 조회", hotel["exact_url"], use_container_width=True)
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
