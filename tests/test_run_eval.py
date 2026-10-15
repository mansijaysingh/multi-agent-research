from evals.run_eval import COLUMNS, load_results, save_results


def _row(i, status):
    return {c: "" for c in COLUMNS} | {"id": i, "status": status}


def test_results_merge_by_id(tmp_path):
    path = tmp_path / "results.csv"
    assert load_results(path) == {}

    save_results({1: _row(1, "report"), 2: _row(2, "report")}, path)

    # A later batch re-runs topic 2 and adds topic 3; topic 1 must survive untouched
    rows = load_results(path)
    rows[2] = _row(2, "fail")
    rows[3] = _row(3, "report")
    save_results(rows, path)

    merged = load_results(path)
    assert sorted(merged) == [1, 2, 3]
    assert [merged[i]["status"] for i in (1, 2, 3)] == ["report", "fail", "report"]
