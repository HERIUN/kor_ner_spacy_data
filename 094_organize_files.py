"""
파일명 기준으로 원천데이터/라벨링데이터 폴더 내 파일을 하위 폴더로 정리하는 스크립트.

파일명 구조:
  관광 콘텐츠_관광지_자연관광_[수집방법]_[출처]_[장소명]_[언어]_[번호]_[날짜].[확장자]

정리 기준:
  [수집방법] (4번째 필드) → [출처] (5번째 필드) 2단계 하위 폴더 생성 후 이동

사용법:
  python3 organize_files.py
"""

import os

BASE = os.path.join(
    os.path.dirname(__file__),
    "094.관광_특화_말뭉치_데이터",
    "3.개방데이터",
    "1.데이터",
    "Training",
)

TARGET_DIRS = [
    os.path.join(BASE, "01.원천데이터",  "TS_1.관광콘텐츠_1.관광지_1.자연관광"),
    os.path.join(BASE, "02.라벨링데이터", "TL_1.관광콘텐츠_1.관광지_1.자연관광"),
]


def organize(base_dir: str) -> None:
    label = os.path.basename(base_dir)
    files = [f for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
    total = len(files)
    moved = skipped = 0

    print(f"\n[{label}] 파일 {total}개 정리 시작...")

    for fname in files:
        parts = fname.split("_")
        if len(parts) < 5:
            print(f"  건너뜀 (필드 부족): {fname}")
            skipped += 1
            continue

        collect_method = parts[3]   # 온라인 / 오프라인
        source = parts[4]           # 출처명

        dest_dir = os.path.join(base_dir, collect_method, source)
        os.makedirs(dest_dir, exist_ok=True)

        src = os.path.join(base_dir, fname)
        dst = os.path.join(dest_dir, fname)
        os.rename(src, dst)
        moved += 1

        if moved % 10000 == 0:
            print(f"  {moved}/{total} 완료...")

    print(f"  완료: {moved}개 이동, {skipped}개 건너뜀")


if __name__ == "__main__":
    for d in TARGET_DIRS:
        if not os.path.isdir(d):
            print(f"디렉토리 없음, 건너뜀: {d}")
            continue
        organize(d)

    print("\n전체 완료!")
