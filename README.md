# 데이터 준비 (data_prepare)

> 변환된 데이터셋: [🤗 HERIUN/kor-ner-spacy-data](https://huggingface.co/datasets/HERIUN/kor-ner-spacy-data)

## 데이터셋 목록

| # | 데이터셋 | 변환 스크립트 | 출력 파일 |
|:-:|---------|--------------|----------|
| 1 | 관광 특화 말뭉치 (AIHub 094) | `094_convert_to_ner.py` | `converted/094_ner_dataset.jsonl` |
| 2 | 전시 공연 도슨트 (AIHub 208) | `208_convert_to_ner.py` | `converted/208_ner_dataset.jsonl` |
| 3 | naver_ner (네이버 NER) | `naver_convert_to_ner.py` | `converted/naver_ner_dataset.jsonl` |
| 4 | 한국해양대 말뭉치 - 형태소_개체명 | `kmou_convert_to_ner.py` | `converted/kmou_ner_dataset.jsonl` |

---

## 데이터셋 상세

### 1. 관광 특화 말뭉치 (AIHub 094)

- 링크: [AIHub - 관광 특화 말뭉치 데이터](https://aihub.or.kr/aihubdata/data/view.do?pageIndex=1&currMenu=115&topMenu=100&srchOptnCnd=OPTNCND001&searchKeyword=%EA%B0%9C%EC%B2%B4%EB%AA%85&srchDetailCnd=DETAILCND001&srchOrder=ORDER001&srchPagePer=20&aihubDataSe=data&dataSetSn=71714)
- 로컬 경로: `094.관광_특화_말뭉치_데이터/`

#### 다운로드

```bash
aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71714 -filekey 524644
aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71714 -filekey 524653
```

#### 태그 매핑

라벨링 JSON의 `annotations`은 `Tagclass`(`O`/`A`/`E`) + `TagCode` 조합으로 raw tag를 구성.
감성(`E-*`) 태그 전부 제거. TAG_MAP에 없는 태그도 제거.

**O — 개체명 (Object)**

| raw tag | 의미 | 변환 태그 |
|:-------:|------|:---------:|
| `O-PS` | 사람 | `PER` |
| `O-LC` | 지역 | `LOC` |
| `O-OG` | 기관 | `ORG` |
| `O-DT` | 날짜 | `DAT` |
| `O-QT` | 수량 | `QT` |
| `O-AF` `O-CV` `O-AM` `O-PT` `O-TR` `O-EV` | 인공물·문명·동물·식물·이론·사건 | 제거 |

**A — 속성 (Attribute)**

| raw tag | 의미 | 변환 태그 |
|:-------:|------|:---------:|
| `A-AD` `A-PO` | 주소·우편번호 | `ADD` |
| `A-TI` | 시간 | `TIM` |
| `A-DA` | 일정 | `DAT` |
| `A-TR` `A-PR` `A-UN` `A-ET` | 교통·가격·부대정보·기타 | 제거 |

**A-TE (전화번호/기관/지역 복합) — `_ate_to_tag()` 로 분류**

괄호 제거 후 아래 순서로 판단.

| 조건 | 변환 태그 |
|------|:---------:|
| 숫자 포함 | `PHN` |
| ORG 접미사 (`과·소·청·원·단·팀·센터·공원·공단·사무소·안내소·관리소·콜센터·공사·부·실·관`) | `ORG` |
| LOC 접미사 (`군·시·구·읍·면·리·도·동`) | `LOC` |
| 구분자만 or 빈값, 나머지 애매한 텍스트 | 제거 |

**A-TM (홈페이지/이메일/지역) — `_atm_to_tag()` 로 분류**

| 조건 | 변환 태그 |
|------|:---------:|
| `@` 포함 (이메일) | 제거 |
| `http` `www.` `ftp` 등으로 시작 | `URL` |
| 도메인 패턴 (`.kr` `.com` `.net` `.org` 등) 포함 | `URL` |
| 순수 한글 & 관광 복합어·동사형 아님 | `LOC` |
| 나머지 | 제거 |

---

### 2. 전시 공연 도슨트 (AIHub 208)

- 링크: [AIHub - 전시 공연 도슨트 데이터](https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&searchKeyword=%EC%A0%84%EC%8B%9C%20%EA%B3%B5%EC%97%B0%20%EB%8F%84%EC%8A%A8%ED%8A%B8%20%EB%8D%B0%EC%9D%B4%ED%84%B0&aihubDataSe=data&dataSetSn=71323)
- 로컬 경로: `208.전시_공연_도슨트_데이터/`

#### 다운로드

```bash
# filekey 441710 ~ 441722 (datasetkey 71323)
for key in $(seq 441710 441722); do
    aihubshell -aihubapikey $AIHUB_API_KEY -mode d -datasetkey 71323 -filekey $key
done
```

#### 태그 매핑

`taglist[].Type` **숫자** 기준. (`ner_tags` 필드는 character-level index라 부정확하여 미사용)

| Type 번호 | 의미 | 변환 태그 |
|:---------:|------|:---------:|
| `0` | 날짜 | `DAT` |
| `1` | 장소 | `LOC` |
| `2` | 기관 | `ORG` |
| `3` | 인물 | `PER` |
| `4` | 수량 | `QT` |
| `5` | 시간 | `TIM` |
| `6` | 기간 (날짜로 통합) | `DAT` |

엔티티 위치는 `taglist[].Keyword`를 `explain` 텍스트에서 순서대로 탐색해 character offset 결정.

---

### 3. naver_ner (네이버 NER)

- 링크: [GitHub - naver/nlp-challenge NER](https://github.com/naver/nlp-challenge/tree/master/missions/ner)
- 로컬 경로: `naver_ner/data/train/train_data`

#### 포맷

탭 구분 (`idx\tword\ttag`), 빈 줄로 문장 구분. 태그는 `{LABEL}_B` / `{LABEL}_I` / `-` 형식.

#### 태그 매핑

| 원본 태그 | 의미 | 변환 태그 |
|:---------:|------|:---------:|
| `PER` | 인물 | `PER` |
| `ORG` | 기관 | `ORG` |
| `LOC` | 장소 | `LOC` |
| `DAT` | 날짜 | `DAT` |
| `NUM` | 수량/숫자 | `QT` |
| `TIM` | 시간 | `TIM` |
| `CVL` `TRM` `EVT` `ANM` `AFW` `FLD` `PLT` `MAT` | 직위·용어·사건·동물·인공물·분야·식물·재료 | 제거 |

---

### 4. 말뭉치 - 형태소_개체명
- 링크: [GitHub - 한국해양대 ner데이터](https://github.com/kmounlp/NER)
- 로컬 경로: `NER/말뭉치 - 형태소_개체명/`

#### 포맷

각 `*_NER.txt` 파일, 빈 줄로 문장 구분.

```
## N                        ← 문장 번호
## 원문 텍스트               ← plain text
## <entity_text:LABEL> ...  ← 개체명 마커 포함 주석 텍스트
형태소\t원형\tPOS\tNER_tag  ← 형태소 라인 (변환 시 미사용)
```

변환 시 3번째 `##` 줄의 `<entity_text:LABEL>` 마커를 파싱해 character offset 계산.

#### 태그 매핑

| 원본 태그 | 의미 | 변환 태그 |
|:---------:|------|:---------:|
| `PER` | 인물 | `PER` |
| `ORG` | 기관 | `ORG` |
| `LOC` | 장소 | `LOC` |
| `DAT` | 날짜 | `DAT` |
| `TIM` | 시간 | `TIM` |
| `NOH` `MNY` `PNT` | 수량·금액·퍼센트 | `QT` |
| `DUR` | 기간 | `DAT` |
| `POH` | 기타 고유명사 | 제거 |

---

## 공통 후처리 규칙

### 오프셋 유효성 검사 (094)

- `start < 0` 또는 `end > len(text)` 또는 `start >= end` → 제거
- `TagText`와 실제 슬라이스 불일치 → 제거
- 앞뒤 괄호(`()（）[]` 등) 는 trim 후 오프셋 보정

---

## 출력 태그 타입

| 태그 | 의미 | 데이터 출처 |
|:----:|------|:----------:|
| `PER` | 인물 (성명, 별명 등) | 전체 |
| `ORG` | 기관·단체명 | 전체 |
| `LOC` | 장소·지역명·건물명 | 전체 |
| `DAT` | 날짜·기간 | 전체 |
| `TIM` | 시간 | 전체 |
| `QT` | 수량·금액·퍼센트 | 전체 |
| `ADD` | 주소·우편번호 | 094 전용 |
| `PHN` | 전화번호·내선번호 | 094 전용 |
| `URL` | 웹 주소 | 094 전용 |
| `RRN` `ACC` `ID` `PW` `IP` | PII 식별자 | 미등장 — 추후 수집/어노테이션 대상 |

---

## 엔티티 통계 (converted JSONL 기준)

### 데이터셋별

| 데이터셋 | 레코드 수 | LOC | QT | DAT | ORG | PER | ADD | PHN | URL | TIM | 합계 |
|---------|----------:|----:|---:|----:|----:|----:|----:|----:|----:|----:|-----:|
| 094 | 907,787 | 693,280 | 151,680 | 133,043 | 59,955 | 29,864 | 129,320 | 91,674 | 67,166 | 26,876 | 1,382,858 |
| 208 | 981 | 2,699 | 2,441 | 3,127 | 1,949 | 5,096 | — | — | — | 111 | 15,423 |
| naver_ner | 67,800 | 20,888 | 56,239 | 25,907 | 41,080 | 43,174 | — | — | — | 3,293 | 190,581 |
| kmou_ner | 18,659 | 6,332 | 14,236 | 6,593 | 13,137 | 13,867 | — | — | — | 371 | 54,536 |
| **합계** | **995,227** | **723,199** | **224,596** | **168,670** | **116,121** | **92,001** | **129,320** | **91,674** | **67,166** | **30,651** | **1,643,398** |

### 전체 분포

| 태그 | 건수 | 비율 |
|:----:|-----:|-----:|
| `LOC` | 723,199 | 44.00% |
| `QT` | 224,596 | 13.67% |
| `DAT` | 168,670 | 10.26% |
| `ADD` | 129,320 | 7.87% |
| `ORG` | 116,121 | 7.07% |
| `PHN` | 91,674 | 5.58% |
| `PER` | 92,001 | 5.60% |
| `URL` | 67,166 | 4.09% |
| `TIM` | 30,651 | 1.87% |
| **합계** | **1,643,398** | **100%** |
