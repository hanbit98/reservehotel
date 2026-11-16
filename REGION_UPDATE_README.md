# 호텔 권역 통일 + 자동 CSV 병합 (2026-11-16)

## 변경 사항
- 태국, 베트남, 말레이시아, 인도네시아, 대만: 메리어트·힐튼·아코르의 `display_region`을 국가별 여행 권역명으로 통일
- 총 2,854개 호텔 / 호텔 코드와 기존 `region`·`area` 값은 보존
- 말레이시아 동해안(쿠안탄, 프헨티안, 던건, 파항)은 `동해안·고원` 그룹 신설
- 대시보드 국가별 카드 화면에 권역 정렬: 전체 호텔 수 / 메리어트 호텔 수 / 힐튼 호텔 수

## 재수집 후 권역 통일
```
python normalize_hotel_regions.py --input hotels.csv --output hotels_normalized.csv --strict
```
`hotel_region_changes.csv`: 변경된 권역 / `hotel_region_review.csv`: 지도에 없는 도시 확인용.
원본 `region`과 `area`는 보존합니다. 같은 코드가 달라도 표준화를 위해 `brand_group`에 의존하지 않습니다.

## 새 호텔 CSV 병합 (권장)
```
python merge_hotel_csv.py --base hotels.csv --incoming incoming_hotels.csv --output hotels_merged.csv
```
- 기준: (brand_group, code) — 기존 호텔은 코드로 갱신, 새 호텔은 추가
- 새 파일에 없는 기존 호텔은 삭제하지 않음
- `hotel_merge_audit.csv`: 반영된 신규/갱신 호텔
- `hotel_merge_review.csv`: 도시 불명/코드 누락/신규 CSV 중복 (반영 보류)
- 안전장치: 기존 hotels.csv를 직접 덮어쓸 수 없음. 결과 확인 후 교체
- 신규 CSV에는 `brand_group`, `code`, `country` 컬럼 필수. 도시명 `region` 또는 `area`가 있으면 가장 정확합니다.

**중요:** 같은 이름의 도시 또는 원본 지명 오입력일 경우 도시 규칙만으로 충분하지 않을 수 있습니다. 새 지역 발생 시 `hotel_region_rules.py`의 국가별 CITY 목록을 업데이트 후 재시도하세요. 기존 국내·일본·중국 권역은 이번 규칙 변경 대상이 아닙니다.
