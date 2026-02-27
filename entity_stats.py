"""converted/ 폴더의 JSONL 파일에서 엔티티 타입 통계를 출력하는 스크립트"""

import json
from collections import defaultdict
from pathlib import Path

CONVERTED_DIR = Path(__file__).parent / "converted"

def count_entities(jsonl_path: Path):
    entity_counts = defaultdict(int)
    sentence_count = 0
    sentence_with_entity = 0

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            sentence_count += 1
            entities = data.get("entities", [])
            if entities:
                sentence_with_entity += 1
            for ent in entities:
                entity_counts[ent[2]] += 1

    return sentence_count, sentence_with_entity, dict(entity_counts)


def print_stats(name, sentence_count, sentence_with_entity, entity_counts):
    total = sum(entity_counts.values())
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  문장 수       : {sentence_count:,}")
    print(f"  엔티티 있는 문장: {sentence_with_entity:,}")
    print(f"  전체 엔티티 수 : {total:,}")
    print(f"  {'태그':<8} {'건수':>10}  {'비율':>7}")
    print(f"  {'-'*30}")
    for tag, cnt in sorted(entity_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag:<8} {cnt:>10,}  {cnt/total*100:>6.2f}%")
    print(f"  {'-'*30}")
    print(f"  {'합계':<8} {total:>10,}  100.00%")


def main():
    files = sorted(CONVERTED_DIR.glob("*.jsonl"))
    if not files:
        print("converted/ 폴더에 JSONL 파일이 없습니다.")
        return

    all_entity_counts = defaultdict(int)
    all_sentences = 0
    all_with_entity = 0

    for path in files:
        sc, swe, ec = count_entities(path)
        print_stats(path.name, sc, swe, ec)
        all_sentences += sc
        all_with_entity += swe
        for tag, cnt in ec.items():
            all_entity_counts[tag] += cnt

    if len(files) > 1:
        print_stats("전체 합계", all_sentences, all_with_entity, dict(all_entity_counts))


if __name__ == "__main__":
    main()
