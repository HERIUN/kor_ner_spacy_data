"""
전시 공연 도슨트 데이터 라벨링 JSON → NER 학습 포맷 변환 스크립트

입력 JSON 구조:
  explain          : 개체 태그 제거된 순수 텍스트 (tokens를 join한 것과 동일)
  taglist[]:
    .Keyword : 개체 텍스트
    .Type    : 개체 유형 번호 (0~6)

Type 번호 → 태그 매핑 (aihub_data.md 기준):
  0: DAT (날짜)   1: LOC (장소)   2: ORG (기관)
  3: PER (인물)   4: QT  (수량)   5: TIM (시간)   6: DAT (기간→날짜 통합)

출력 포맷 (JSONL, 한 줄에 문서 하나):
  {"text": "...", "entities": [[start, end, "PS"], [start, end, "LC"], ...]}

  - entities: [start, end, tag]
    - start : explain 내 시작 인덱스 (inclusive, 0-based)
    - end   : 시작 + len(Keyword) (exclusive, Python slice 기준)
    - tag   : Type에 대응하는 태그 문자열

  * 같은 Keyword가 여러 번 등장할 경우 앞에서부터 순서대로 매핑
  * explain에 Keyword가 없으면 해당 항목 건너뜀

사용법:
  python3 208_convert_to_ner.py [--input INPUT_DIR] [--output OUTPUT_FILE]

기본값:
  --input  : 208.전시_공연_도슨트_데이터/.../Training/02.라벨링데이터
  --output : converted/208_ner_dataset.jsonl
"""

import json
import argparse
from pathlib import Path

DEFAULT_INPUT = Path(__file__).parent / (
    "208.전시_공연_도슨트_데이터/01-1.정식개방데이터/Training/02.라벨링데이터"
)
DEFAULT_OUTPUT = Path(__file__).parent / "converted" / "208_ner_dataset.jsonl"

TYPE_LABELS = {0: "DAT", 1: "LOC", 2: "ORG", 3: "PER", 4: "QT", 5: "TIM", 6: "DAT"}


def _merge_adjacent(text: str, entities: list) -> list:
    """같은 라벨의 연속 엔티티 중 사이 갭이 공백만 있으면 하나로 병합."""
    if len(entities) < 2:
        return entities
    sorted_ents = sorted(entities, key=lambda e: e[0])
    merged = [list(sorted_ents[0])]
    for s, e, lbl in sorted_ents[1:]:
        prev = merged[-1]
        gap = text[prev[1]:s]
        if prev[2] == lbl and gap.strip() == "":
            merged[-1][1] = e
        else:
            merged.append([s, e, lbl])
    return merged


def convert_file(json_path: Path) -> dict:
    """JSON 파일 하나를 NER 포맷 레코드로 변환."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("explain", "")
    taglist = data.get("taglist") or []

    entities = []
    used: set[tuple[int, int]] = set()

    for item in taglist:
        keyword = item.get("Keyword", "")
        type_id = item.get("Type")

        if not keyword or type_id not in TYPE_LABELS:
            continue

        # 첫 번째 미사용 위치 탐색
        start = 0
        pos = -1
        while True:
            idx = text.find(keyword, start)
            if idx == -1:
                break
            end_idx = idx + len(keyword)
            if not any(idx < u_end and end_idx > u_start for u_start, u_end in used):
                pos = idx
                break
            start = idx + 1

        if pos == -1:
            continue

        start = pos
        end = pos + len(keyword)
        tag = TYPE_LABELS[type_id]
        entities.append([start, end, tag])
        used.add((start, end))

    return {"text": text, "entities": _merge_adjacent(text, entities)}


def convert_directory(input_dir: Path, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_files = skipped = 0

    with open(output_file, "w", encoding="utf-8") as out:
        for json_path in sorted(input_dir.rglob("*.json")):
            try:
                record = convert_file(json_path)
            except Exception as e:
                print(f"  [오류] {json_path.name}: {e}")
                skipped += 1
                continue

            if not record["entities"]:
                continue
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_files += 1

            if total_files % 100 == 0:
                print(f"  {total_files}개 파일 처리 완료...")

    print(f"\n완료: {total_files}개 파일 변환 (건너뜀: {skipped}개)")
    print(f"출력 파일: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="전시 공연 도슨트 JSON → NER JSONL 변환")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="라벨링 JSON 디렉토리 (default: 기본 경로)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="출력 JSONL 파일 경로 (default: docent_ner_dataset.jsonl)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[오류] 입력 경로가 존재하지 않습니다: {args.input}")
        return

    print(f"입력: {args.input}")
    print(f"출력: {args.output}")
    convert_directory(args.input, args.output)


if __name__ == "__main__":
    main()
