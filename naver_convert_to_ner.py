"""
naver_ner 학습 데이터 → NER JSONL 변환 스크립트

입력 포맷 (tab-separated, 빈 줄로 문장 구분):
  {idx}\t{word}\t{NER_tag}

  NER 태그 포맷:
    {LABEL}_B  - 개체 시작 (Beginning)
    {LABEL}_I  - 개체 내부 (Inside)
    -          - 비개체

출력 포맷 (JSONL, 한 줄에 문장 하나):
  {"text": "word1 word2 ...", "entities": [[start, end, "LABEL"], ...]}

  - text    : 어절을 공백으로 이어붙인 문장
  - entities: [start, end, label]
    - start : 0-based, inclusive
    - end   : exclusive (Python slice 기준)
  - 유효한 엔티티가 없는 문장은 출력하지 않음

태그 매핑 (TAG_MAP):
  PER → PER    ORG → ORG    LOC → LOC    DAT → DAT
  NUM → QT     TIM → TIM
  CVL / TRM / EVT / ANM / AFW / FLD / PLT / MAT → 제거

사용법:
  python3 naver_ner_convert.py [--input INPUT_FILE] [--output OUTPUT_FILE]

기본값:
  --input  : data_prepare/naver_ner/data/train/train_data
  --output : data_prepare/converted/naver_ner_dataset.jsonl
"""

import json
import argparse
from pathlib import Path

DEFAULT_INPUT  = Path(__file__).parent / "naver_ner" / "data" / "train" / "train_data"
DEFAULT_OUTPUT = Path(__file__).parent / "converted" / "naver_ner_dataset.jsonl"

# None: 해당 태그 제거, 값 있음: 해당 레이블로 변환
TAG_MAP: dict[str, str | None] = {
    "PER": "PER",   # 인물
    "ORG": "ORG",   # 기관
    "LOC": "LOC",   # 장소
    "DAT": "DAT",   # 날짜
    "NUM": "QT",    # 수량/숫자 → QT
    "TIM": "TIM",   # 시간
    # 제거 태그
    "CVL": None,    # 직위/직책
    "TRM": None,    # 전문용어
    "EVT": None,    # 사건/행사
    "ANM": None,    # 동물
    "AFW": None,    # 인공물
    "FLD": None,    # 분야
    "PLT": None,    # 식물
    "MAT": None,    # 재료/물질
}


def _parse_sentences(file_path: Path) -> list[tuple[list[str], list[str]]]:
    """파일을 읽어 문장 단위 (words, tags) 리스트로 반환.

    빈 줄을 문장 구분자로 사용. 각 줄은 `idx\tword\ttag` 형식.
    """
    sentences: list[tuple[list[str], list[str]]] = []
    words: list[str] = []
    tags:  list[str] = []

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if words:
                    sentences.append((words, tags))
                    words, tags = [], []
            else:
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                _, word, tag = parts
                words.append(word)
                tags.append(tag)

    if words:
        sentences.append((words, tags))

    return sentences


def _extract_entities(text: str, words: list[str], tags: list[str]) -> list[list]:
    """B/I 태그에서 character offset 기반 엔티티 스팬 추출.

    어절은 공백으로 구분되므로 각 어절의 시작 오프셋을 누적 계산.
    같은 레이블의 B → I 연속은 공백 포함한 하나의 스팬으로 병합.
    """
    # 각 어절의 시작 오프셋 계산
    offsets: list[int] = []
    cursor = 0
    for word in words:
        offsets.append(cursor)
        cursor += len(word) + 1  # +1: 어절 사이 공백

    entities: list[list] = []
    cur_label: str | None = None
    cur_start: int = 0
    cur_end:   int = 0

    def _flush():
        nonlocal cur_label
        if cur_label is not None:
            mapped = TAG_MAP.get(cur_label)
            if mapped is not None:
                entities.append([cur_start, cur_end, mapped])
            cur_label = None

    for i, (word, tag) in enumerate(zip(words, tags)):
        if tag == "-" or "_" not in tag:
            _flush()
            continue

        label, bio = tag.rsplit("_", 1)
        w_start = offsets[i]
        w_end   = w_start + len(word)

        if bio == "B":
            _flush()
            cur_label = label
            cur_start = w_start
            cur_end   = w_end

        elif bio == "I":
            if cur_label == label:
                # 같은 레이블 연속 → 공백 포함 확장
                cur_end = w_end
            else:
                # 다른 레이블의 I → 이전 엔티티 저장 후 새 엔티티 시작
                _flush()
                cur_label = label
                cur_start = w_start
                cur_end   = w_end

    _flush()
    return entities


def convert(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sentences = _parse_sentences(input_path)
    total_records = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for words, tags in sentences:
            if not words:
                continue

            text = " ".join(words)
            entities = _extract_entities(text, words, tags)

            if not entities:
                continue

            out.write(json.dumps({"text": text, "entities": entities}, ensure_ascii=False) + "\n")
            total_records += 1

    print(f"완료: {len(sentences)}개 문장 → {total_records}개 레코드 (엔티티 없는 문장 제외)")
    print(f"출력 파일: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="naver_ner 학습 데이터 → NER JSONL 변환")
    parser.add_argument("--input",  type=Path, default=DEFAULT_INPUT,
                        help=f"입력 파일 (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"출력 JSONL 파일 (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[오류] 입력 파일이 존재하지 않습니다: {args.input}")
        return

    print(f"입력: {args.input}")
    print(f"출력: {args.output}")
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
