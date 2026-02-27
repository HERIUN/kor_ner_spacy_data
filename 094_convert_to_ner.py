"""
관광 특화 말뭉치 라벨링 JSON → NER 학습 포맷 변환 스크립트

입력 JSON 구조:
  docu_info.sentences[].sentence       : 문장 텍스트
  docu_info.sentences[].annotations[]:
    .TagText   : 개체 텍스트
    .Tagclass  : 개체 대분류 (O, A, E)
    .TagCode   : 개체 코드   (LC, PS, OG, ...)
    .startPos  : 문자 단위 시작 인덱스 (inclusive)
    .endPos    : 문자 단위 종료 인덱스 (inclusive)

출력 포맷 (JSONL, 한 줄에 문장 하나):
  {"text": "홍길동이 서울에 산다.", "entities": [[0, 3, "PER"], [5, 7, "LOC"]]}

  - entities: [start, end, tag]
    - start : startPos (inclusive, 0-based)
    - end   : endPos + 1 (exclusive, Python slice 기준)
    - tag   : TAG_MAP에 따라 변환된 태그 문자열 (None이면 해당 개체 제외)
  - entities가 비어있는 문장은 출력하지 않음

태그 매핑 (TAG_MAP):
  O-PS → PER    O-LC → LOC    O-OG → ORG    O-DT → DAT
  A-AD → ADD    A-PO → ADD    A-TE → PHN    A-TI → TIM    A-DA → DAT
  O-QT → QT
  A-TM → URL (URL계열) / EML (이메일) / LOC (순수 지역명) / 제거 (garbage)
  E-*/O-AF/O-CV/O-AM/O-PT/O-TR/O-EV/A-ET/A-PR/A-TR/A-UN → 제거

사용법:
  python3 convert_to_ner.py [--input INPUT_DIR] [--output OUTPUT_FILE]

기본값:
  --input  : 094.관광_특화_말뭉치_데이터/.../Training/02.라벨링데이터
  --output : data_prepare/094_ner_dataset.jsonl
"""

import json
import re
import argparse
from pathlib import Path

DEFAULT_INPUT = Path(__file__).parent / (
    "094.관광_특화_말뭉치_데이터/3.개방데이터/1.데이터/Training/02.라벨링데이터"
)
DEFAULT_OUTPUT = Path(__file__).parent / "converted" / "094_ner_dataset.jsonl"

# None: 해당 태그 제거, 값 있음: 해당 태그로 변환, 키 없음: 원본 유지
TAG_MAP: dict[str, str | None] = {
    "O-PS": "PER",
    "O-LC": "LOC",
    "O-OG": "ORG",
    "O-DT": "DAT",
    "O-QT": "QT",
    "A-AD": "ADD",
    "A-PO": "ADD",
    # A-TE는 _ate_to_tag() 함수로 처리 (전화번호↔기관명 분리)
    # A-TM은 _atm_to_tag() 함수로 처리
    "A-TI": "TIM",
    "A-DA": "DAT",
    # 제거
    "E-P":  None, "E-NA": None, "E-N":  None, "E-QT": None,
    "O-AF": None, "O-CV": None, "O-AM": None,
    "O-PT": None, "O-TR": None, "O-EV": None,
    "A-ET": None, "A-PR": None, "A-TR": None, "A-UN": None,
}

def _ate_to_tag(text: str) -> str | None:
    """A-TE 텍스트 분류:
      - 숫자 포함          → 'PHN' (전화번호·내선번호)
      - 구분자·빈값        → None
      - ORG 접미사 패턴    → 'ORG' (기관·부서명)
      - LOC 접미사 패턴    → 'LOC' (지자체명)
      - 나머지 애매한 텍스트 → None (노이즈 방지)
    """
    _ATE_SEP = re.compile(r"^[/:\-~,\s]+$")
    _ATE_ORG = re.compile(r"(과|소|청|원|단|팀|센터|공원|공단|사무소|안내소|관리소|콜센터|공사|부|실|관)[)）]?$")
    _ATE_LOC = re.compile(r"(군|시|구|읍|면|리|도|동)$")

    clean = text.strip("()（） ")
    if not clean or _ATE_SEP.match(clean):
        return None
    if re.search(r"\d", clean):
        return "PHN"
    if _ATE_ORG.search(clean):
        return "ORG"
    if _ATE_LOC.search(clean):
        return "LOC"
    return None

def _atm_to_tag(text: str) -> str | None:
    """A-TM 텍스트 → 'EML'(이메일) / 'URL'(URL계열) / 'LOC'(순수 지역명) / None(제거)."""
    _DOMAIN_RE   = re.compile(r"[\w.-]+\.(kr|com|net|org|go\.kr|co\.kr|or\.kr|ne\.kr)", re.I)
    _NON_LOC     = re.compile(r"관광|여행|포털|없음|홈페이지|비짓|visit", re.I)
    _VERB_ENDING = re.compile(r"(하는|하다|이다|하며|하고|하면|이고|이며|하기|스러운|스럽다|올구양)$")

    if "@" in text:
        return "EML"
    if text.startswith(("http", "www.", "ftp", "ttp:", "ttps:")):
        return "URL"
    if _DOMAIN_RE.search(text):
        return "URL"
    # 순수 한글 텍스트이며 관광 복합어·동사형이 아닌 경우 → 지역명으로 간주
    if (re.fullmatch(r"[가-힣]+", text)
            and not _NON_LOC.search(text)
            and not _VERB_ENDING.search(text)):
        return "LOC"
    return None

def _merge_adjacent(text: str, entities: list) -> list:
    """같은 라벨의 연속 엔티티 중 사이 갭이 공백만 있으면 하나로 병합.

    추가: LOC + ORG 또는 ORG + LOC 조합도 공백만 있으면 ORG로 병합.
    (예: '경기도 수원시' LOC + '문화관광과' ORG → '경기도 수원시 문화관광과' ORG)
    """
    if len(entities) < 2:
        return entities
    sorted_ents = sorted(entities, key=lambda e: e[0])
    merged = [list(sorted_ents[0])]
    for s, e, lbl in sorted_ents[1:]:
        prev = merged[-1]
        gap = text[prev[1]:s]
        if gap.strip() != "":
            merged.append([s, e, lbl])
            continue
        if prev[2] == lbl:
            merged[-1][1] = e
        elif prev[2] == "LOC" and lbl == "ORG":
            merged[-1][1] = e
            merged[-1][2] = "ORG"
        else:
            merged.append([s, e, lbl])
    return merged

def convert_file(json_path: Path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """JSON 라벨링 파일 하나를 NER 포맷 레코드 리스트로 변환.

    Returns
    -------
    (records, dropped, atm_log, ate_log)
        records : 변환된 레코드 리스트
        dropped : 제거된 엔티티 리스트 (E-* 태그 제외)
        atm_log : A-TM 변환 결과 로그 {"text", "entity", "mapped_tag", "start", "end"}
        ate_log : A-TE 변환 결과 로그 {"text", "entity", "mapped_tag", "start", "end"}
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    records = []
    dropped = []
    atm_log = []
    ate_log = []
    sentences = data.get("docu_info", {}).get("sentences") or []

    for sent in sentences:
        text = sent.get("sentence", "")
        entities = []

        for ann in sent.get("annotations") or []:
            start = ann.get("startPos")
            end_inclusive = ann.get("endPos")
            tagclass = ann.get("Tagclass", "")
            tagcode = ann.get("TagCode", "")

            if start is None or end_inclusive is None:
                continue

            end = end_inclusive + 1  # Python exclusive end

            # 범위 검증
            if start < 0 or end > len(text) or start >= end:
                continue

            # TagText와 실제 슬라이스 일치 여부 확인 (데이터 오류 방어)
            extracted = text[start:end]
            if extracted != ann.get("TagText", extracted):
                continue

            # 앞뒤 괄호 제거 후 오프셋 보정
            _BRACKETS = "()（）[]［］【】"
            while extracted and extracted[0] in _BRACKETS:
                extracted = extracted[1:]
                start += 1
            while extracted and extracted[-1] in _BRACKETS:
                extracted = extracted[:-1]
                end -= 1
            if not extracted or start >= end:
                continue

            raw_tag = f"{tagclass}-{tagcode}"
            if raw_tag == "A-TM":
                tag = _atm_to_tag(extracted)
                atm_log.append({"text": text, "entity": extracted, "mapped_tag": tag, "start": start, "end": end})
            elif raw_tag == "A-TE":
                tag = _ate_to_tag(extracted)
                ate_log.append({"text": text, "entity": extracted, "mapped_tag": tag, "start": start, "end": end})
            elif tagclass == "E":
                tag = None  # E-* 전체 제거
            else:
                tag = TAG_MAP.get(raw_tag, None)  # 미등록 태그는 제거

            if tag is None:
                # 의도적 제거 태그는 기록하지 않음
                if tagclass != "E" and raw_tag not in {
                    "O-AF", "O-CV", "O-AM", "O-PT", "O-TR", "O-EV",
                }:
                    dropped.append({
                        "text": text,
                        "entity": extracted,
                        "raw_tag": raw_tag,
                        "start": start,
                        "end": end,
                    })
                continue

            entities.append([start, end, tag])

        if entities:
            records.append({"text": text, "entities": _merge_adjacent(text, entities)})

    return records, dropped, atm_log, ate_log


def convert_directory(input_dir: Path, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    dropped_file = output_file.with_name(output_file.stem + "_dropped.jsonl")
    atm_file     = output_file.with_name(output_file.stem + "_atm.jsonl")
    ate_file     = output_file.with_name(output_file.stem + "_ate.jsonl")

    total_files = total_records = total_dropped = skipped = 0

    with open(output_file, "w", encoding="utf-8") as out, \
         open(dropped_file, "w", encoding="utf-8") as drop_out, \
         open(atm_file,     "w", encoding="utf-8") as atm_out, \
         open(ate_file,     "w", encoding="utf-8") as ate_out:
        for json_path in sorted(input_dir.rglob("*.json")):
            try:
                records, dropped, atm_log, ate_log = convert_file(json_path)
            except Exception as e:
                print(f"  [오류] {json_path.name}: {e}")
                skipped += 1
                continue

            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            for entry in dropped:
                drop_out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            for entry in atm_log:
                atm_out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            for entry in ate_log:
                ate_out.write(json.dumps(entry, ensure_ascii=False) + "\n")

            total_files += 1
            total_records += len(records)
            total_dropped += len(dropped)

            if total_files % 1000 == 0:
                print(f"  {total_files}개 파일 처리 완료 ({total_records}개 문장)...")

    print(f"\n완료: {total_files}개 파일 → {total_records}개 문장 (건너뜀: {skipped}개)")
    print(f"제거된 엔티티: {total_dropped}개 → {dropped_file}")
    print(f"A-TM 변환 로그: {atm_file}")
    print(f"A-TE 변환 로그: {ate_file}")
    print(f"출력 파일: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="관광 말뭉치 JSON → NER JSONL 변환")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="라벨링 JSON 디렉토리 (default: 기본 경로)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="출력 JSONL 파일 경로 (default: ner_dataset.jsonl)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[오류] 입력 경로가 존재하지 않습니다: {args.input}")
        return

    print(f"입력: {args.input}")
    print(f"출력: {args.output}")
    convert_directory(args.input, args.output)


if __name__ == "__main__":
    main()
