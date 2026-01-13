from gradescope_analytics.io import load_and_normalize


def test_load_and_normalize_from_path(sample_truth_path):
    normalized, mapping_used, suggested = load_and_normalize(sample_truth_path, infer_mapping=False)
    assert mapping_used is None
    assert suggested is None
    assert not normalized.empty
