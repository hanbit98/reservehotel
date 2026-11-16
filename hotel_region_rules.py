"""Country-level canonical hotel regions; keyed by original city, not hotel chain.

Do not silently map unknown cities to a plausible-sounding region: send them to review.
The source `region`/`area` fields are not changed by normalization.
"""
from __future__ import annotations
import re

REGION_CITIES = {
 '태국': {
  '방콕·중부': ['방콕','아유타야'],
  '파타야·기타': ['파타야','라용','트랫','페치부리','후아힌','프란부리'],
  '치앙마이·북부': ['치앙마이','치앙라이'],
  '푸켓·안다만': ['푸켓','푸껫','팡응아','카오락','끄라비'],
  '코사무이': ['코사무이'],
 },
 '베트남': {
  '하노이·북부': ['하노이','하장','랑선','하이퐁','꽝닌','닌빈','남딘','라오카이','박닌','푸토','흥옌'],
  '다낭·중부': ['다낭','호이안','후에','빈','땀끼','탐끼','닌빈 아님'],
  '나트랑': ['나트랑','깜람','뮤이네','닥락'],
  '호치민·남부': ['호치민','빈즈엉','껀터'],
  '푸꾸옥': ['푸꾸옥'],
 },
 '말레이시아': {
  '쿠알라룸푸르·수도권': ['쿠알라룸푸르','샤알람','푸총','푸트라자야','프탈링자야','세티아알람','스팡','수방'],
  '조호르·남부': ['조호르바루','데사루','말라카'],
  '페낭·북부·도서': ['페낭','랑카위','판타이콕','루무트','이포','팡코르'],
  '보르네오': ['코타키나발루','투아란','쿠칭','빈툴루','미리','물루'],
  '동해안·고원': ['던건','파항','쿠안탄','쿠알라브숫','프헨티안','카메론하이랜드'],
 },
 '인도네시아': {
  '발리': ['발리'],
  '자카르타·서부자바': ['자카르타','반둥','브카시','탕게랑','족자카르타','파달라랑'],
  '동부·중부자바': ['수라바야','젬버','솔로'],
  '롬복·리우제도': ['롬복','리아우 제도','바탐','라부안바조','숨바','빈탄섬'],
  '인도네시아 기타': ['발릭파판','메단','마나도','폰티아낙','벨리퉁','람풍','마카사르'],
 },
 '대만': {
  '타이베이·북부': ['타이베이','신베이','신주','타오위안'],
  '타이중·중부': ['타이중','장화','난터우'],
  '가오슝·남부': ['가오슝','컨딩','타이난'],
  '대만 동부·도서': ['화롄','펑후','이란','타이둥'],
 },
}
# Explicit corrections for source-region errors (e.g. a Hoi An listing given a Da Nang region).
CODE_OVERRIDE = {
 ('베트남','Hilton','VDHTHRU'): '하노이·북부',  # Nam Dinh name, region erroneously Ninh Binh
 ('베트남','Hilton','HANBGRU'): '하노이·북부',  # Bac Giang in name, region Bac Ninh
 ('베트남','Hilton','HANHBRU'): '하노이·북부',  # Hoa Binh, region Phu Tho
 ('베트남','Hilton','VDHRURU'): '하노이·북부',  # Thai Binh name, region Hung Yen
 ('베트남','Hilton','TMKTKRU'): '다낭·중부',  # Tam Ky city
 ('인도네시아','Hilton','BDOPAHI'): '자카르타·서부자바',  # Padalarang/Bandung, region Jakarta
}

def clean_city(value: str) -> str:
    s = str(value or '').strip()
    s = re.split(r'\s*\(', s, maxsplit=1)[0].strip()
    return s

def _lookup():
    output = {}
    for country, groups in REGION_CITIES.items():
        table = {}
        for canonical, cities in groups.items():
            for city in cities:
                if city in table:
                    raise ValueError(f'Duplicate city {country}/{city}')
                table[city] = canonical
        output[country] = table
    return output

CITY_LOOKUP = _lookup()
CANONICAL = {country: set(groups) for country, groups in REGION_CITIES.items()}

def region_for(row):
    """Returns (region, rule) or (None, diagnostic)."""
    country = (row.get('country') or '').strip()
    if country not in CANONICAL:
        # Countries outside this scope retain an existing classification.
        existing = (row.get('display_region') or '').strip()
        return (existing, 'other-country-preserved') if existing else (None, 'missing-display-region')
    code = (row.get('code') or '').strip().upper()
    chain = (row.get('brand_group') or '').strip()
    override = CODE_OVERRIDE.get((country, chain, code))
    if override:
        return override, 'code-override'
    for field in ('region', 'area'):
        city = clean_city(row.get(field))
        match = CITY_LOOKUP[country].get(city)
        if match:
            return match, f'{field}-city'
    # Existing canonical label only valid when there is no source city.
    existing = (row.get('display_region') or '').strip()
    if not clean_city(row.get('region')) and not clean_city(row.get('area')) and existing in CANONICAL[country]:
        return existing, 'canonical-without-city'
    return None, 'unknown-city-review'


def normalize_rows(rows, strict=False):
    changes, issues = [], []
    for r in rows:
        new, rule = region_for(r)
        if not new:
            issues.append({'brand_group':r.get('brand_group',''), 'country':r.get('country',''),
                           'code':r.get('code',''), 'region':r.get('region',''),
                           'area':r.get('area',''), 'current_display_region':r.get('display_region',''), 'reason':rule})
            continue
        old = r.get('display_region','')
        if old != new:
            changes.append({'brand_group':r.get('brand_group',''), 'country':r.get('country',''),
                            'code':r.get('code',''), 'region':r.get('region',''),
                            'previous_display_region':old, 'new_display_region':new, 'rule':rule})
            r['display_region'] = new
    if strict and issues:
        raise ValueError(f'{len(issues)} locations unmapped: {issues[:5]}')
    return changes, issues
