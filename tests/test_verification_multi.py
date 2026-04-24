"""Tests for multi-agent cross-verification (ticket 0059)."""

from unittest.mock import patch

from aedist.query_verification import verify_multi_cross


def _make_rows():
    """Create minimal plant rows for testing."""
    return [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"},
        {"name": "Ca Mau I", "fuel": "gas", "capacity_mwe": "771"},
        {"name": "Vinh Tan 2", "fuel": "coal", "capacity_mwe": "1244"},
    ]


def _fake_verify_cross(scores, matched=None):
    """Return a mock verify_cross that assigns given scores to rows.

    If matched is provided, it should be a list of bools parallel to scores.
    Plants with matched=False simulate a parse failure (fuzzy match missed).
    """

    def _mock(rows, verifier_model, subject=None):
        annotated = []
        for i, row in enumerate(rows):
            entry = dict(row)
            score = scores[i] if i < len(scores) else 1
            is_matched = matched[i] if matched and i < len(matched) else True
            entry["evidence_score"] = str(score)
            entry["verified"] = "True" if score >= 3 else "False"
            entry["source_1"] = f"Source from {verifier_model}" if is_matched else ""
            entry["source_1_type"] = (
                ("primary" if score >= 3 else "none") if is_matched else "none"
            )
            entry["source_2"] = ""
            entry["source_2_type"] = "none"
            entry["_matched"] = is_matched
            annotated.append(entry)
        summary = {
            "mode": "cross",
            "total_plants": len(annotated),
            "mean_evidence_score": sum(scores) / max(len(scores), 1),
            "score_distribution": {},
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
        }
        return annotated, summary

    return _mock


def _make_side_effect(score_sets, match_sets=None):
    """Build a side_effect for patching verify_cross with per-verifier scores.

    Each call to the returned function picks the next entry from score_sets
    (and match_sets if provided), simulating sequential verifier calls.
    """
    call_count = [0]

    def side_effect(rows, verifier_model, subject=None):
        idx = call_count[0]
        call_count[0] += 1
        matches = match_sets[idx] if match_sets else None
        return _fake_verify_cross(score_sets[idx], matches)(rows, verifier_model, subject)

    return side_effect


class TestVerifyMultiCrossReturnsMedian:
    """test_verify_multi_cross_returns_median"""

    def test_median_of_three_scores(self):
        """Median of [2, 3, 4] per row is 3."""
        rows = _make_rows()
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[2, 2, 2], [3, 3, 3], [4, 4, 4]]),
        ):
            annotated, summary = verify_multi_cross(rows, ["model-a", "model-b", "model-c"])

        assert len(annotated) == 3
        for row in annotated:
            assert row["evidence_score"] == "3"
            assert row["evidence_score_median"] == "3"

    def test_median_with_mixed_scores(self):
        """Median of [0, 3, 4] is 3; median of [1, 1, 4] is 1."""
        rows = [
            {"name": "Plant A", "fuel": "coal"},
            {"name": "Plant B", "fuel": "gas"},
        ]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[0, 1], [3, 1], [4, 4]]),
        ):
            annotated, summary = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert annotated[0]["evidence_score"] == "3"
        assert annotated[1]["evidence_score"] == "1"

    def test_summary_contains_expected_keys(self):
        """Summary dict has mode, mean_evidence_score, verifier_panel, usage."""
        rows = _make_rows()
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[3, 3, 3], [3, 3, 3], [3, 3, 3]]),
        ):
            _, summary = verify_multi_cross(rows, ["a", "b", "c"])

        assert summary["mode"] == "multi_cross"
        assert summary["total_plants"] == 3
        assert "mean_evidence_score" in summary
        assert "score_distribution" in summary
        assert summary["verifier_panel"] == ["a", "b", "c"]
        assert summary["usage"]["prompt_tokens"] == 3000  # 1000 * 3
        assert summary["usage"]["completion_tokens"] == 1500  # 500 * 3


class TestMultiCrossPreservesAllVerifierScores:
    """test_multi_cross_preserves_all_verifier_scores"""

    def test_individual_score_columns_present(self):
        """evidence_score_v1, v2, v3 columns exist with correct values."""
        rows = [{"name": "X", "fuel": "coal"}]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[2], [3], [4]]),
        ):
            annotated, _ = verify_multi_cross(rows, ["v1", "v2", "v3"])

        row = annotated[0]
        assert row["evidence_score_v1"] == "2"
        assert row["evidence_score_v2"] == "3"
        assert row["evidence_score_v3"] == "4"
        assert row["evidence_score_median"] == "3"
        assert row["evidence_score"] == "3"  # median for compatibility

    def test_verified_flag_uses_median(self):
        """verified field is set based on median score."""
        rows = [{"name": "A", "fuel": "coal"}, {"name": "B", "fuel": "gas"}]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[1, 3], [2, 3], [4, 4]]),
        ):
            annotated, _ = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert annotated[0]["verified"] == "False"
        assert annotated[1]["verified"] == "True"


class TestMultiCrossExcludesParseFailures:
    """Parse failures (_matched=False) are excluded from median."""

    def test_unmatched_verifier_excluded_from_median(self):
        """One verifier fails to match -> median uses only matched scores."""
        rows = [{"name": "Pha Lai", "fuel": "coal"}]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[4], [1], [4]], [[True], [False], [True]]),
        ):
            annotated, summary = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert annotated[0]["evidence_score"] == "4"
        assert annotated[0]["matched_v1"] == "True"
        assert annotated[0]["matched_v2"] == "False"
        assert annotated[0]["matched_v3"] == "True"
        assert annotated[0]["matched_verifiers"] == "2"

    def test_all_unmatched_falls_back_to_all_scores(self):
        """If no verifier matched, fall back to all scores (conservative)."""
        rows = [{"name": "X", "fuel": "coal"}]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[1], [1], [1]], [[False], [False], [False]]),
        ):
            annotated, _ = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert annotated[0]["evidence_score"] == "1"
        assert annotated[0]["matched_verifiers"] == "0"

    def test_parse_failure_changes_median(self):
        """Two verifiers fail: old median([4,1,1])=1, new median([4])=4."""
        rows = [{"name": "Pha Lai", "fuel": "coal"}]
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect([[4], [1], [1]], [[True], [False], [False]]),
        ):
            annotated, _ = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert annotated[0]["evidence_score"] == "4"
        assert annotated[0]["matched_verifiers"] == "1"

    def test_summary_includes_match_rates(self):
        """Summary has match_rates showing per-verifier match counts."""
        rows = _make_rows()
        with patch(
            "aedist.query_verification.verify_cross",
            side_effect=_make_side_effect(
                [[3, 3, 3], [3, 3, 3], [1, 1, 1]],
                [[True, True, True], [True, True, True], [False, False, False]],
            ),
        ):
            _, summary = verify_multi_cross(rows, ["v1", "v2", "v3"])

        assert summary["match_rates"] == ["3/3", "3/3", "0/3"]


class TestMultiCrossEmptyPanel:
    """test_multi_cross_empty_panel"""

    def test_empty_panel_returns_rows_unchanged(self):
        """Empty verifier panel returns rows with default score 1."""
        rows = _make_rows()
        annotated, summary = verify_multi_cross(rows, [])

        assert len(annotated) == 3
        for row in annotated:
            assert row["evidence_score"] == "1"
        assert summary["mode"] == "multi_cross"
        assert summary["verifier_panel"] == []

    def test_empty_panel_preserves_existing_scores(self):
        """If rows already have evidence_score, it is preserved (not overwritten)."""
        rows = [{"name": "X", "fuel": "coal", "evidence_score": "4"}]
        annotated, _ = verify_multi_cross(rows, [])
        assert annotated[0]["evidence_score"] == "4"

    def test_empty_panel_empty_rows(self):
        """Empty panel + empty rows returns empty list."""
        annotated, summary = verify_multi_cross([], [])
        assert annotated == []
        assert summary["total_plants"] == 0


class TestRunConditionMultiCross:
    """Integration: run_condition dispatches to verify_multi_cross."""

    def test_run_condition_multi_cross_mode(self, tmp_path):
        """run_condition with 'multi_cross' calls verify_multi_cross."""
        import csv

        from aedist.query_verification import run_condition
        from aedist.schema import RunRecord

        ref_path = tmp_path / "reference.csv"
        with open(ref_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "province", "fuel", "capacity_mwe", "status"])
            w.writerow(["Pha Lai", "Hai Duong", "coal", "600", "operational"])

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        rows = [{"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"}]
        base_config = {
            "model": "deepseek/deepseek-v3.2",
            "method": "decomposed",
            "result_file": "test.json",
        }

        fake_annotated = [
            {
                "name": "Pha Lai",
                "fuel": "coal",
                "capacity_mwe": "600",
                "evidence_score": "3",
                "evidence_score_v1": "3",
                "evidence_score_v2": "3",
                "evidence_score_v3": "3",
                "evidence_score_median": "3",
                "verified": "True",
                "source_1": "PDP8",
                "source_1_type": "primary",
                "source_2": "",
                "source_2_type": "none",
            },
        ]
        fake_summary = {
            "mode": "multi_cross",
            "total_plants": 1,
            "mean_evidence_score": 3.0,
            "score_distribution": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 0},
            "verifier_panel": ["a", "b", "c"],
            "usage": {"prompt_tokens": 3000, "completion_tokens": 1500},
        }

        with patch(
            "aedist.query_verification.verify_multi_cross",
            return_value=(fake_annotated, fake_summary),
        ):
            record = run_condition(
                rows=rows,
                base_config=base_config,
                mode="multi_cross",
                run=1,
                output_dir=output_dir,
                reference_path=ref_path,
                ref_plants_cache={},
                verifier_panel=["a", "b", "c"],
            )

        assert isinstance(record, RunRecord)
        assert record.method_params.extra["verification_mode"] == "multi_cross"
        assert record.method_params.extra["verifier_panel"] == ["a", "b", "c"]
        assert record.resource_use.cost_usd > 0

    def test_run_condition_multi_cross_no_panel(self, tmp_path):
        """run_condition returns None for multi_cross without verifier_panel."""
        import csv

        from aedist.query_verification import run_condition

        ref_path = tmp_path / "reference.csv"
        with open(ref_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "province", "fuel", "capacity_mwe", "status"])
            w.writerow(["Pha Lai", "Hai Duong", "coal", "600", "operational"])

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = run_condition(
            rows=[{"name": "X", "fuel": "coal"}],
            base_config={"model": "m", "method": "single", "result_file": "f.json"},
            mode="multi_cross",
            run=1,
            output_dir=output_dir,
            reference_path=ref_path,
            ref_plants_cache={},
            verifier_panel=None,
        )

        assert result is None


class TestSweepConfig:
    """Verify the verification_multi sweep config loads correctly."""

    def test_verification_multi_config_exists(self, experiments):
        """verification_multi sweep is in experiments.toml."""
        config = experiments["sweeps"]["sweep_rag_verification_multi"]
        assert config["repeat"] == 3
        assert config["budget_usd"] == 5
        assert "multi_cross" in config["verification_modes"]
        assert "unverified" in config["verification_modes"]
        assert len(config["verifier_panel"]) == 3
        assert len(config["base_configs"]) >= 1

    def test_verifier_panel_diversity(self, experiments):
        """Panel has 3 distinct providers."""
        config = experiments["sweeps"]["sweep_rag_verification_multi"]
        panel = config["verifier_panel"]
        providers = {m.split("/")[0] for m in panel}
        assert len(providers) == 3  # anthropic, openai, deepseek
