"""data_prepare 공통 유틸리티"""


def merge_adjacent(text: str, entities: list) -> list:
    """같은 라벨의 연속 엔티티 중 사이 갭이 공백만 있으면 하나로 병합.

    Parameters
    ----------
    text : str
        원문 텍스트 (갭 내용 확인에 사용)
    entities : list
        [[start, end, label], ...] 형식의 엔티티 목록

    Returns
    -------
    list
        병합된 엔티티 목록. 라벨이 다른 인접 엔티티는 그대로 유지.
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
        else:
            merged.append([s, e, lbl])
    return merged
