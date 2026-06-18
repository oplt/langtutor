from backend.app.modules.knowledge.cefr_filters import chunk_matches_cefr, rank_bounds_for_cefr


def test_rank_bounds_for_a1() -> None:
    bounds = rank_bounds_for_cefr("A1")
    assert bounds == (1, 200)


def test_chunk_matches_cefr_filters_by_rank() -> None:
    assert chunk_matches_cefr({"rank": 50}, cefr_level="A1") is True
    assert chunk_matches_cefr({"rank": 900}, cefr_level="A1") is False


def test_a1_path_rank_ranges_align_with_engine() -> None:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "app/modules/learning/paths/a1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    rank_min, rank_max = rank_bounds_for_cefr("A1")
    assert rank_min == 1
    assert rank_max == 200
    for module in payload.get("modules", []):
        for kp in module.get("knowledge_points", []):
            kp_min = int(kp.get("rank_min") or 0)
            kp_max = int(kp.get("rank_max") or 0)
            if kp_min <= 0 or kp_max <= 0:
                continue
            assert kp_min >= rank_min
            assert kp_max <= rank_max
