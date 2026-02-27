"""
말뭉치 - 형태소_개체명 (*_NER.txt) → NER JSONL 변환 스크립트

입력 파일 구조 (각 *_NER.txt):
  ## N               ← 문장 번호
  ## 원문 텍스트      ← plain text (개체명 마커 없음)
  ## 주석 텍스트      ← <entity_text:LABEL> 마커 포함 텍스트
  형태소 탭 구분 줄...
  (빈 줄)            ← 문장 구분자

변환 방식:
  3번째 ## 줄(주석 텍스트)에서 <entity_text:LABEL> 패턴을 파싱해
  원문 문자열과 character offset 기반 엔티티 목록 생성.
  형태소 라인은 사용하지 않음.

태그 매핑:
  PER → PER    ORG → ORG    LOC → LOC    DAT → DAT    TIM → TIM
  NOH → QT (수량)    MNY → QT (금액)    PNT → QT (퍼센트)
  DUR → DAT (기간)   POH → 제거 (기타 고유명사)

출력 포맷 (JSONL):
  {"text": "...", "entities": [[start, end, "LABEL"], ...]}
  - start : 0-based, inclusive
  - end   : exclusive (Python slice 기준)
  - 엔티티 없는 문장은 출력하지 않음

사용법:
  python3 etri_kmou_convert.py [--input INPUT_DIR] [--output OUTPUT_FILE]

기본값:
  --input  : data_prepare/NER/말뭉치 - 형태소_개체명
  --output : data_prepare/converted/morpheme_ner_dataset.jsonl
"""

import re
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent

DEFAULT_INPUT  = BASE_DIR / "NER/말뭉치 - 형태소_개체명"
DEFAULT_OUTPUT = BASE_DIR / "converted" / "morpheme_ner_dataset.jsonl"

# None: 제거, 값 있음: 해당 레이블로 변환
TAG_MAP: dict[str, str | None] = {
    "PER": "PER",   # 인물
    "ORG": "ORG",   # 기관
    "LOC": "LOC",   # 장소
    "DAT": "DAT",   # 날짜
    "TIM": "TIM",   # 시간
    "NOH": "QT",    # 수량 → QT
    "MNY": "QT",    # 금액 → QT
    "PNT": "QT",    # 퍼센트 → QT
    "DUR": "DAT",   # 기간 → DAT
    "POH": None,    # 기타 고유명사 → 제거
}

# <entity_text:LABEL> 패턴 (LABEL = 2~4자리 대문자)
_ENTITY_RE = re.compile(r"<(.+?):([A-Z]{2,4})>")


def _parse_annotated(annotated: str) -> tuple[str, list[list]]:
    """주석 텍스트에서 plain text와 character offset 기반 엔티티 목록 추출.

    Parameters
    ----------
    annotated : str
        '<entity:LABEL> ... <entity:LABEL> ...' 형태의 주석 텍스트

    Returns
    -------
    (plain_text, entities)
        entities : [[start, end, label], ...]  (매핑된 라벨만 포함)
    """
    parts: list[str] = []
    entities: list[list] = []
    cursor = 0
    last_end = 0

    for m in _ENTITY_RE.finditer(annotated):
        # 엔티티 앞 일반 텍스트
        prefix = annotated[last_end:m.start()]
        parts.append(prefix)
        cursor += len(prefix)

        entity_text = m.group(1)
        raw_label   = m.group(2)
        label       = TAG_MAP.get(raw_label)  # None이면 제거 대상

        if label is not None:
            entities.append([cursor, cursor + len(entity_text), label])

        parts.append(entity_text)
        cursor  += len(entity_text)
        last_end = m.end()

    # 나머지 텍스트
    parts.append(annotated[last_end:])

    plain_text = "".join(parts)
    return plain_text, entities


def _parse_file(file_path: Path) -> list[dict]:
    """*_NER.txt 파일 하나를 파싱해 레코드 리스트 반환."""
    records: list[dict] = []
    header_buf: list[str] = []   # ## 줄 버퍼 (최대 3개)

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            content = line[3:]   # "## " 이후 내용
            header_buf.append(content)

            # 3번째 ## 줄 = 주석 텍스트
            if len(header_buf) == 3:
                annotated = header_buf[2]
                plain_text, entities = _parse_annotated(annotated)

                if entities:
                    records.append({"text": plain_text, "entities": entities})

        elif line == "":
            # 문장 경계 → 헤더 버퍼 초기화
            header_buf = []

    return records


def convert(input_dir: Path, output_file: Path) -> None:
    txt_files = sorted(input_dir.glob("*_NER.txt"))
    if not txt_files:
        print(f"[오류] *_NER.txt 파일을 찾을 수 없습니다: {input_dir}")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    total_records = 0

    with open(output_file, "w", encoding="utf-8") as out:
        for i, txt_path in enumerate(txt_files, 1):
            try:
                records = _parse_file(txt_path)
            except Exception as e:
                print(f"  [오류] {txt_path.name}: {e}")
                continue

            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_records += len(records)

            if i % 200 == 0:
                print(f"  {i}/{len(txt_files)}개 파일 처리 완료 ({total_records}개 레코드)...")

    print(f"\n완료: {len(txt_files)}개 파일 → {total_records}개 레코드")
    print(f"출력 파일: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="말뭉치 형태소_개체명 NER.txt → JSONL 변환")
    parser.add_argument("--input",  type=Path, default=DEFAULT_INPUT,
                        help=f"입력 디렉토리 (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"출력 JSONL 파일 (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[오류] 입력 경로가 존재하지 않습니다: {args.input}")
        return

    print(f"입력: {args.input}")
    print(f"출력: {args.output}\n")
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
