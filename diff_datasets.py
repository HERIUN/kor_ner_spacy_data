#!/usr/bin/env python3
"""
diff_datasets.py
----------------
두 JSONL 파일을 비교하여 엔티티가 변경된 항목만 출력합니다.

사용법:
    python data_prepare/diff_datasets.py \
        --original data/ner_dataset.jsonl \
        --cleaned  data/ner_dataset_clean.jsonl \
        --output   data/diff_entities.jsonl
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="두 JSONL 엔티티 비교")
    parser.add_argument("--original", required=True, help="원본 JSONL")
    parser.add_argument("--cleaned",  required=True, help="클린 JSONL")
    parser.add_argument("--output",   help="차이 결과 저장 JSONL (생략 시 출력만)")
    args = parser.parse_args()

    orig_path  = Path(args.original)
    clean_path = Path(args.cleaned)

    diffs = []
    total_changed = 0
    label_stats = {}

    with open(orig_path, encoding="utf-8") as fo, \
         open(clean_path, encoding="utf-8") as fc:

        for line_no, (lo, lc) in enumerate(zip(fo, fc), start=1):
            lo, lc = lo.strip(), lc.strip()
            if not lo or not lc:
                continue

            orig_obj  = json.loads(lo)
            clean_obj = json.loads(lc)

            orig_ents  = orig_obj.get("entities", [])
            clean_ents = clean_obj.get("entities", [])
            text       = orig_obj.get("text", "")

            changed = []
            for oe, ce in zip(orig_ents, clean_ents):
                if oe != ce:
                    label = oe[2]
                    before_text = text[oe[0]:oe[1]]
                    after_text  = text[ce[0]:ce[1]]
                    changed.append({
                        "label":  label,
                        "before": before_text,
                        "after":  after_text,
                    })
                    label_stats.setdefault(label, 0)
                    label_stats[label] += 1
                    total_changed += 1

            if changed:
                diffs.append({
                    "line":    line_no,
                    "text":    text,
                    "changes": changed,
                })

    # 출력
    print(f"\n{'='*60}")
    print(f"총 변경 엔티티: {total_changed:,}")
    print(f"변경된 문장 수: {len(diffs):,}")
    print(f"\n{'레이블':8} {'변경수':>8}")
    print("-" * 20)
    for label, cnt in sorted(label_stats.items(), key=lambda x: -x[1]):
        print(f"{label:8} {cnt:>8,}")
    print("=" * 60)

    # 라벨별 샘플 출력
    sample_seen = {}
    print("\n[변경 샘플 (라벨별 최대 10개)]")
    for diff in diffs:
        for ch in diff["changes"]:
            label = ch["label"]
            if sample_seen.get(label, 0) >= 10:
                continue
            sample_seen.setdefault(label, 0)
            sample_seen[label] += 1
            print(f"  [{label}] '{ch['before']}' → '{ch['after']}'")

    # JSONL 저장
    if args.output:
        out_path = Path(args.output)
        with open(out_path, "w", encoding="utf-8") as fw:
            for d in diffs:
                fw.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"\n저장 완료: {out_path}  ({len(diffs):,} 줄)")


if __name__ == "__main__":
    main()
