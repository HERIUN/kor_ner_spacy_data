#!/usr/bin/env python
"""JSONL → HuggingFace token classification 포맷 변환 스크립트.

data_prepare/converted/ 의 JSONL 파일들을 HuggingFace Trainer 학습에 맞는
포맷으로 변환합니다.

사용법:
    python scripts/prepare_hf_dataset.py
    python scripts/prepare_hf_dataset.py --input-dir data_prepare/converted --output-dir data/hf_dataset

출력 파일:
    data/hf_dataset/train.jsonl
    data/hf_dataset/dev.jsonl
    data/hf_dataset/test.jsonl
    data/hf_dataset/label2id.json

출력 JSONL 포맷 (한 줄 = 한 문장):
    {"tokens": ["나는", "서울에", "산다"], "ner_tags": [0, 1, 0], "source": "AIHUB_094"}

HuggingFace 로드 예:
    from datasets import load_dataset
    ds = load_dataset("json", data_files={"train": "data/hf_dataset/train.jsonl", ...})
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Iterator


# ── BIO 태깅 ─────────────────────────────────────────────────────────────────

def _char_offsets_to_word_bio(
    text: str,
    entities: list[tuple[int, int, str]],
) -> tuple[list[str], list[str]]:
    """공백 기준 토크나이징 후 문자 오프셋 → 단어 단위 BIO 태그 변환.

    Parameters
    ----------
    text     : 원문 텍스트
    entities : [(start_char, end_char, label), ...]  # end_char는 exclusive

    Returns
    -------
    (tokens, bio_tags)
    """
    tokens: list[str] = []
    offsets: list[tuple[int, int]] = []

    for m in re.finditer(r"\S+", text):
        tokens.append(m.group())
        offsets.append((m.start(), m.end()))

    if not tokens:
        return [], []

    bio_tags = ["O"] * len(tokens)

    for ent_start, ent_end, label in entities:
        first = True
        for i, (tok_start, tok_end) in enumerate(offsets):
            if tok_end <= ent_start or tok_start >= ent_end:
                continue
            bio_tags[i] = f"B-{label}" if first else f"I-{label}"
            first = False

    return tokens, bio_tags


# ── JSONL 로드 ───────────────────────────────────────────────────────────────

_SOURCE_MAP: dict[str, str] = {
    "094": "AIHUB_094",
    "208": "AIHUB_208",
    "naver": "naver",
    "kmou": "kmou",
}

def _source_from_filename(name: str) -> str:
    for prefix, source in _SOURCE_MAP.items():
        if name.startswith(prefix):
            return source
    return name.removesuffix(".jsonl")


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[경고] {path.name}:{lineno} 파싱 오류: {e}")


def load_all_jsonl(input_dir: Path) -> list[dict]:
    """디렉토리 내 모든 .jsonl 파일을 읽어 합칩니다."""
    all_samples: list[dict] = []
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"{input_dir} 에서 .jsonl 파일을 찾을 수 없습니다.")
    for jsonl_file in jsonl_files:
        source = _source_from_filename(jsonl_file.name)
        before = len(all_samples)
        for sample in _iter_jsonl(jsonl_file):
            sample["source"] = source
            all_samples.append(sample)
        print(f"[로드] {jsonl_file.name}: {len(all_samples) - before:,}건 (source={source})")
    print(f"[로드] 합계: {len(all_samples):,}건")
    return all_samples


# ── 레이블 수집 ───────────────────────────────────────────────────────────────

def collect_label_list(samples: list[dict]) -> list[str]:
    """전체 샘플에서 BIO 레이블 목록을 수집합니다. (O, B-X, I-X, ... 순)"""
    raw_labels: set[str] = set()
    for obj in samples:
        for entity in obj.get("entities", []):
            raw_labels.add(entity[2])

    bio_labels = ["O"]
    for label in sorted(raw_labels):
        bio_labels.append(f"B-{label}")
        bio_labels.append(f"I-{label}")
    return bio_labels


# ── 변환 & 저장 ───────────────────────────────────────────────────────────────

def convert_sample(obj: dict, label2id: dict[str, int]) -> dict | None:
    text: str = obj.get("text", "")
    entities = [tuple(e) for e in obj.get("entities", [])]

    tokens, bio_tags = _char_offsets_to_word_bio(text, entities)
    if not tokens:
        return None

    return {
        "tokens": tokens,
        "ner_tags": [label2id.get(tag, 0) for tag in bio_tags],
        "source": obj.get("source", ""),
    }


def split_convert_save(
    samples: list[dict],
    label2id: dict[str, int],
    output_dir: Path,
    train_ratio: float,
    dev_ratio: float,
    seed: int,
) -> None:
    rng = random.Random(seed)
    rng.shuffle(samples)

    n = len(samples)
    train_end = int(n * train_ratio)
    dev_end = train_end + int(n * dev_ratio)

    splits = {
        "train": samples[:train_end],
        "dev": samples[train_end:dev_end],
        "test": samples[dev_end:],
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_samples in splits.items():
        out_path = output_dir / f"{split_name}.jsonl"
        converted = skipped = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for obj in split_samples:
                result = convert_sample(obj, label2id)
                if result is None:
                    skipped += 1
                    continue
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                converted += 1
        print(f"[저장] {out_path.name}: {converted:,}건" + (f" (빈 샘플 스킵 {skipped}건)" if skipped else ""))

    # 레이블 매핑 저장
    id2label = {str(v): k for k, v in label2id.items()}
    label_path = output_dir / "label2id.json"
    with open(label_path, "w", encoding="utf-8") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, ensure_ascii=False, indent=2)
    print(f"[저장] {label_path.name}: {len(label2id)}개 레이블 → {list(label2id.keys())}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="JSONL → HuggingFace token classification 포맷 변환")
    ap.add_argument("--input-dir",   default="data_prepare/converted", type=Path, metavar="DIR",
                    help="JSONL 파일이 있는 디렉토리 (기본: data_prepare/converted)")
    ap.add_argument("--output-dir",  default="data/hf_dataset", type=Path, metavar="DIR",
                    help="출력 디렉토리 (기본: data/hf_dataset)")
    ap.add_argument("--train-ratio", default=0.8, type=float, metavar="F",
                    help="학습 비율 (기본: 0.8)")
    ap.add_argument("--dev-ratio",   default=0.1, type=float, metavar="F",
                    help="검증 비율 (기본: 0.1)")
    ap.add_argument("--seed",        default=42,  type=int,
                    help="셔플 시드 (기본: 42)")
    args = ap.parse_args()

    if args.train_ratio + args.dev_ratio >= 1.0:
        ap.error("train-ratio + dev-ratio 는 1.0 미만이어야 합니다.")

    print(f"▶ 입력: {args.input_dir}")
    print(f"▶ 출력: {args.output_dir}")
    print(f"▶ 분할: train {args.train_ratio*100:.0f}% / dev {args.dev_ratio*100:.0f}% / "
          f"test {(1-args.train_ratio-args.dev_ratio)*100:.0f}%")
    print()

    samples = load_all_jsonl(args.input_dir)

    label_list = collect_label_list(samples)
    label2id = {label: i for i, label in enumerate(label_list)}
    print(f"[레이블] {label_list}\n")

    split_convert_save(samples, label2id, args.output_dir,
                       args.train_ratio, args.dev_ratio, args.seed)

    print(f"\n✔ 완료! HuggingFace 로드 예:")
    print(f"    from datasets import load_dataset")
    print(f"    ds = load_dataset('json', data_files={{")
    print(f"        'train': '{args.output_dir}/train.jsonl',")
    print(f"        'validation': '{args.output_dir}/dev.jsonl',")
    print(f"        'test': '{args.output_dir}/test.jsonl',")
    print(f"    }})")


if __name__ == "__main__":
    main()
