import streamlit as st
import pandas as pd
from datetime import date, timedelta
from urllib.parse import urlencode

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="아시아 메리어트 포인트 & 요금 조회 대시보드",
    page_icon="🌏",
    layout="wide"
)

# 2. 아시아 10개국 메리어트 호텔 마스터 데이터 (MARSHA 코드 기준)
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


# 3. URL 생성 함수
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


# 4. 사이드바: 검색 조건 및 필터 설정
df_master = pd.DataFrame(MARRIOTT_HOTELS)

with st.sidebar:
    st.header("🔍 숙박 및 조회 조건")

    use_points = st.toggle("💎 포인트 숙박(Rewards Points) 조회", value=True)

    default_checkin = date.today() + timedelta(days=30)
    checkin_date = st.date_input("기준 체크인 날짜", value=default_checkin)
    nights = st.number_input("숙박 일수 (박)", min_value=1, max_value=14, value=1)

    # 기본값: 객실 1개, 성인 2명, 어린이 0명 고정
    col_r, col_a, col_c = st.columns(3)
    with col_r:
        rooms = st.number_input("객실 수", min_value=1, max_value=3, value=1)
    with col_a:
        adults = st.number_input("성인", min_value=1, max_value=4, value=2)
    with col_c:
        children = st.number_input("어린이", min_value=0, max_value=4, value=0)

    st.divider()
    st.header("🌏 국가 및 호텔 필터링")

    all_countries = list(COUNTRY_FLAGS.keys())
    selected_countries = st.multiselect(
        "국가 선택",
        options=all_countries,
        default=["대한민국", "일본"],
        format_func=lambda c: f"{COUNTRY_FLAGS.get(c, '')} {c}"
    )

    available_regions = df_master[df_master["country"].isin(selected_countries)]["region"].unique().tolist()
    selected_regions = st.multiselect(
        "도시 / 권역 선택",
        options=available_regions,
        default=available_regions
    )

    all_tiers = ["Luxury", "Premium", "Select"]
    selected_tiers = st.multiselect("등급(Tier) 선택", options=all_tiers, default=all_tiers)

    only_popular = st.checkbox("⭐ 주요 5성급/인기 리조트만 보기", value=False)
    keyword = st.text_input("호텔명 / 코드 / 지역 검색", placeholder="예: 리츠칼튼, 오사카, CJUJU, 발리")

    st.divider()
    with st.expander("🛠️ 직접 코드(MARSHA) 입력 조회"):
        custom_code = st.text_input("5자리 호텔 코드 입력", max_chars=5, placeholder="예: OKARZ").strip().upper()
        if len(custom_code) == 5:
            c_cal_url = build_calendar_url(custom_code, custom_code, checkin_date, nights, rooms, adults, children, use_points)
            c_ext_url = build_exact_date_url(custom_code, checkin_date, nights, rooms, adults, children, use_points)
            st.link_button(f"📅 [{custom_code}] 월간 달력 열기", c_cal_url, use_container_width=True, type="primary")
            st.link_button(f"🛏️ [{custom_code}] 해당일 객실 열기", c_ext_url, use_container_width=True)


# 5. 메인 화면 구성
st.title("🌏 아시아 메리어트 본보이 포인트 & 요금 스캐너")
checkout_date = checkin_date + timedelta(days=nights)
mode_badge = "💎 포인트 차감 조회" if use_points else "💳 일반 유상 요금 조회"

st.markdown(
    f"**기준 일정:** `{checkin_date.strftime('%Y-%m-%d')}` ~ `{checkout_date.strftime('%Y-%m-%d')}` ({nights}박) &nbsp;|&nbsp; "
    f"**인원:** 성인 **{adults}명**, 어린이 {children}명 (객실 {rooms}개) &nbsp;|&nbsp; "
    f"**모드:** `{mode_badge}`"
)

# 데이터 필터링
filtered_df = df_master[
    (df_master["country"].isin(selected_countries)) &
    (df_master["region"].isin(selected_regions)) &
    (df_master["tier"].isin(selected_tiers))
].copy()

if only_popular:
    filtered_df = filtered_df[filtered_df["popular"] == True]

if keyword.strip():
    kw = keyword.strip().lower()
    filtered_df = filtered_df[
        filtered_df["name"].str.lower().str.contains(kw) |
        filtered_df["code"].str.lower().str.contains(kw) |
        filtered_df["area"].str.lower().str.contains(kw) |
        filtered_df["region"].str.lower().str.contains(kw) |
        filtered_df["brand"].str.lower().str.contains(kw)
    ]

# 각 행별 URL 생성
if not filtered_df.empty:
    filtered_df["calendar_url"] = filtered_df.apply(
        lambda row: build_calendar_url(
            row["code"], row["name"], checkin_date, nights, rooms, adults, children, use_points
        ),
        axis=1
    )
    filtered_df["exact_url"] = filtered_df.apply(
        lambda row: build_exact_date_url(
            row["code"], checkin_date, nights, rooms, adults, children, use_points
        ),
        axis=1
    )

st.caption(f"전체 {len(df_master)}개 호텔 중 현재 필터 조건에 **{len(filtered_df)}개**의 호텔이 일치합니다.")

# 6. 탭 구성: 카드 그리드 뷰 vs 테이블 뷰
tab1, tab2 = st.tabs(["🗂️ 국가·도시별 카드 뷰 (빠른 이동)", "📊 전체 테이블 뷰 (비교 및 CSV 다운로드)"])

with tab1:
    if filtered_df.empty:
        st.warning("선택한 필터 조건에 맞는 호텔이 없습니다. 좌측 사이드바에서 국가나 도시를 추가해 주세요.")
    else:
        for country in [c for c in all_countries if c in filtered_df["country"].unique()]:
            flag = COUNTRY_FLAGS.get(country, "🏳️")
            st.markdown(f"## {flag} {country}")
            country_df = filtered_df[filtered_df["country"] == country]

            for region in country_df["region"].unique():
                st.markdown(f"#### 📍 {region}")
                region_hotels = country_df[country_df["region"] == region]

                cols = st.columns(3)
                for idx, (_, hotel) in enumerate(region_hotels.iterrows()):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            tier_emoji = "👑" if hotel["tier"] == "Luxury" else ("✨" if hotel["tier"] == "Premium" else "🏢")
                            st.markdown(f"**{tier_emoji} {hotel['name']}**")
                            st.caption(f"`{hotel['code']}` | {hotel['brand']} | {hotel['area']}")

                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                st.link_button(
                                    "📅 월간 달력",
                                    hotel["calendar_url"],
                                    use_container_width=True,
                                    type="primary"
                                )
                            with btn_col2:
                                st.link_button(
                                    "🛏️ 객실 조회",
                                    hotel["exact_url"],
                                    use_container_width=True
                                )
            st.divider()

with tab2:
    if not filtered_df.empty:
        st.dataframe(
            filtered_df[["country", "region", "area", "tier", "brand", "name", "code", "calendar_url", "exact_url"]],
            column_config={
                "country": st.column_config.TextColumn("국가", width="small"),
                "region": st.column_config.TextColumn("도시/권역", width="small"),
                "area": st.column_config.TextColumn("상세 위치", width="small"),
                "tier": st.column_config.TextColumn("등급", width="small"),
                "brand": st.column_config.TextColumn("브랜드", width="medium"),
                "name": st.column_config.TextColumn("호텔명", width="medium"),
                "code": st.column_config.TextColumn("코드", width="small"),
                "calendar_url": st.column_config.LinkColumn(
                    "월간 포인트/요금 달력",
                    display_text="📅 달력 열기",
                    width="small"
                ),
                "exact_url": st.column_config.LinkColumn(
                    "특정일 객실 조회",
                    display_text="🛏️ 객실 조회",
                    width="small"
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=650
        )

        csv_data = filtered_df[["country", "region", "area", "tier", "brand", "name", "code", "calendar_url", "exact_url"]].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 현재 필터링된 호텔 및 URL 목록 CSV 다운로드",
            data=csv_data,
            file_name=f"marriott_asia_links_{checkin_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
