"""Tests for aedist.query_decomposed — CSV merging and extraction."""

from aedist.query_decomposed import extract_csv_text, merge_csvs

# --- merge_csvs ---


def test_merge_csvs_deduplicates_by_name():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\n"
    csv2 = "name,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\nVung Ang,coal,planned,,Ha Tinh,1200\n"
    merged = merge_csvs([csv1, csv2])
    lines = merged.strip().split("\n")
    assert len(lines) == 3  # header + 2 unique plants


def test_merge_csvs_case_insensitive_dedup():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPHA LAI,coal,,,Hai Duong,600\n"
    csv2 = "name,fuel,status,cod,province,capacity_mwe\npha lai,coal,,,Hai Duong,600\n"
    merged = merge_csvs([csv1, csv2])
    lines = merged.strip().split("\n")
    assert len(lines) == 2  # header + 1 plant (deduped)


def test_merge_csvs_preserves_header():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPlant A,coal,,,Hanoi,100\n"
    merged = merge_csvs([csv1])
    assert merged.startswith("name,fuel,status,cod,province,capacity_mwe")


def test_merge_csvs_empty_input():
    assert merge_csvs([]) == ""


def test_merge_csvs_skips_empty_names():
    csv1 = (
        "name,fuel,status,cod,province,capacity_mwe\n,coal,,,Hanoi,100\nPlant B,gas,,,HCMC,200\n"
    )
    merged = merge_csvs([csv1])
    lines = merged.strip().split("\n")
    assert len(lines) == 2  # header + Plant B only


def test_merge_csvs_multiple_fuels():
    coal = "name,fuel,status,cod,province,capacity_mwe\nPlant A,coal,,,Hanoi,100\nPlant B,coal,,,HCMC,200\n"
    gas = "name,fuel,status,cod,province,capacity_mwe\nPlant C,gas,,,Da Nang,300\n"
    other = "name,fuel,status,cod,province,capacity_mwe\nPlant D,oil,,,Hue,50\n"
    merged = merge_csvs([coal, gas, other])
    lines = merged.strip().split("\n")
    assert len(lines) == 5  # header + 4 plants


# --- extract_csv_text ---


def test_extract_csv_text_fenced_block():
    response = "Here are the plants:\n\n```csv\nname,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\n```\n"
    result = extract_csv_text(response)
    assert result is not None
    assert "Pha Lai" in result


def test_extract_csv_text_no_csv():
    result = extract_csv_text("I don't have that information.")
    assert result is None


def test_extract_csv_text_inline_csv():
    response = "Results:\nname,fuel,status,cod,province,capacity_mwe\nVung Ang,coal,planned,,Ha Tinh,1200\n\nEnd of data."
    result = extract_csv_text(response)
    assert result is not None
    assert "Vung Ang" in result


# --- query_decomposed ---


def _make_fake_response(fuel_label, plants):
    """Build a fake query_single_turn return dict with CSV content."""
    header = "name,fuel,status,cod,province,capacity_mwe"
    rows = "\n".join(
        f"{name},{fuel},{status},{cod},{province},{cap}"
        for name, fuel, status, cod, province, cap in plants
    )
    csv_block = f"```csv\n{header}\n{rows}\n```"
    content = f"Here are the {fuel_label} plants:\n\n{csv_block}\n"
    return {
        "content": content,
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "wall_seconds": 1.5,
    }


COAL_PLANTS = [
    ("Pha Lai", "coal", "operational", "1983", "Hai Duong", "600"),
    ("Vung Ang", "coal", "planned", "", "Ha Tinh", "1200"),
]
GAS_PLANTS = [
    ("Phu My", "gas", "operational", "2004", "Ba Ria", "750"),
]
OTHER_PLANTS = [
    ("Can Tho", "oil", "operational", "2000", "Can Tho", "100"),
]


class TestQueryDecomposed:
    """Tests for the query_decomposed() orchestrator."""

    def test_basic_merge(self, monkeypatch):
        """3 sub-queries produce a merged CSV with all plants."""
        from aedist.harness import BudgetTracker
        from aedist import query_decomposed as qd_mod

        call_count = 0

        def fake_query_single_turn(client, model_id, messages, **kwargs):
            nonlocal call_count
            fuel_responses = [
                _make_fake_response("coal", COAL_PLANTS),
                _make_fake_response("gas", GAS_PLANTS),
                _make_fake_response("other", OTHER_PLANTS),
            ]
            resp = fuel_responses[call_count]
            call_count += 1
            return resp

        monkeypatch.setattr(qd_mod, "query_single_turn", fake_query_single_turn)
        monkeypatch.setattr(qd_mod, "compute_cost", lambda usage, model: 0.001)

        budget = BudgetTracker(budget_usd=10.0)
        model = {"id": "test-model", "price_per_mtok_in": 0, "price_per_mtok_out": 0}
        result = qd_mod.query_decomposed(
            client=None,
            model_id="test-model",
            corpus_text="test corpus",
            budget=budget,
            model=model,
        )

        assert result is not None
        assert result["strategy"] == "decomposed"
        assert result["n_merged_plants"] == 4  # 2 coal + 1 gas + 1 other
        assert "Pha Lai" in result["merged_csv"]
        assert "Phu My" in result["merged_csv"]
        assert "Can Tho" in result["merged_csv"]
        assert len(result["sub_queries"]) == 3
        assert result["total_cost_usd"] == pytest.approx(0.003)
        assert result["total_wall_seconds"] == pytest.approx(4.5)
        assert result["total_usage"]["prompt_tokens"] == 300
        assert result["total_usage"]["completion_tokens"] == 150

    def test_budget_exceeded_returns_none(self, monkeypatch):
        """Returns None when budget is already exceeded."""
        from aedist.harness import BudgetTracker
        from aedist import query_decomposed as qd_mod

        budget = BudgetTracker(budget_usd=0.001)
        budget.add(0.002)  # exceed the budget

        model = {"id": "test-model"}
        result = qd_mod.query_decomposed(
            client=None,
            model_id="test-model",
            corpus_text="test corpus",
            budget=budget,
            model=model,
        )
        assert result is None

    def test_api_error_returns_none(self, monkeypatch):
        """Returns None when an API error occurs on a sub-query."""
        import openai
        from aedist.harness import BudgetTracker
        from aedist import query_decomposed as qd_mod

        def fake_query_error(client, model_id, messages, **kwargs):
            raise openai.APIError(
                message="rate limit",
                request=None,
                body=None,
            )

        monkeypatch.setattr(qd_mod, "query_single_turn", fake_query_error)

        budget = BudgetTracker(budget_usd=10.0)
        model = {"id": "test-model"}
        result = qd_mod.query_decomposed(
            client=None,
            model_id="test-model",
            corpus_text="test corpus",
            budget=budget,
            model=model,
        )
        assert result is None

    def test_no_csv_in_response(self, monkeypatch):
        """Handles sub-queries that return no extractable CSV gracefully."""
        from aedist.harness import BudgetTracker
        from aedist import query_decomposed as qd_mod

        def fake_query_no_csv(client, model_id, messages, **kwargs):
            return {
                "content": "Sorry, I don't have that information.",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
                "wall_seconds": 0.5,
            }

        monkeypatch.setattr(qd_mod, "query_single_turn", fake_query_no_csv)
        monkeypatch.setattr(qd_mod, "compute_cost", lambda usage, model: 0.0001)

        budget = BudgetTracker(budget_usd=10.0)
        model = {"id": "test-model"}
        result = qd_mod.query_decomposed(
            client=None,
            model_id="test-model",
            corpus_text="test corpus",
            budget=budget,
            model=model,
        )
        assert result is not None
        assert result["merged_csv"] == ""
        assert result["n_merged_plants"] == 0

    def test_dedup_across_subqueries(self, monkeypatch):
        """Plants appearing in multiple sub-queries are deduplicated."""
        from aedist.harness import BudgetTracker
        from aedist import query_decomposed as qd_mod

        call_count = 0

        # Pha Lai appears in both coal and "other" sub-queries
        def fake_query_dup(client, model_id, messages, **kwargs):
            nonlocal call_count
            if call_count == 0:
                resp = _make_fake_response("coal", COAL_PLANTS)
            elif call_count == 1:
                resp = _make_fake_response("gas", GAS_PLANTS)
            else:
                # Duplicate Pha Lai in "other"
                resp = _make_fake_response("other", [
                    ("Pha Lai", "coal", "operational", "1983", "Hai Duong", "600"),
                    ("Can Tho", "oil", "operational", "2000", "Can Tho", "100"),
                ])
            call_count += 1
            return resp

        monkeypatch.setattr(qd_mod, "query_single_turn", fake_query_dup)
        monkeypatch.setattr(qd_mod, "compute_cost", lambda usage, model: 0.001)

        budget = BudgetTracker(budget_usd=10.0)
        model = {"id": "test-model"}
        result = qd_mod.query_decomposed(
            client=None,
            model_id="test-model",
            corpus_text="test corpus",
            budget=budget,
            model=model,
        )
        assert result is not None
        # 2 coal + 1 gas + 1 other (Pha Lai deduped)
        assert result["n_merged_plants"] == 4


# --- main (CLI integration) ---


import pytest


class TestQueryDecomposedMain:
    """Tests for main() CLI entry point."""

    def test_dry_run(self, monkeypatch, tmp_path, capsys):
        """--dry-run shows what would run without querying."""
        from aedist import query_decomposed as qd_mod

        # Create minimal corpus dir
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "doc.md").write_text("Vietnam power plants data.")

        # Create minimal prompt file
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("List all thermal power plants in Vietnam.")

        # Create minimal models.yaml
        models_file = tmp_path / "models.yaml"
        models_file.write_text(
            "- id: test-model\n"
            "  name: Test Model\n"
            "  context_window: 100000\n"
            "  price_per_mtok_in: 1.0\n"
            "  price_per_mtok_out: 2.0\n"
        )

        output_dir = tmp_path / "output"

        monkeypatch.setattr(
            "sys.argv",
            [
                "query_decomposed",
                "--prompt", str(prompt_file),
                "--corpus", str(corpus_dir),
                "--models", str(models_file),
                "--output", str(output_dir),
                "--repeat", "2",
                "--dry-run",
            ],
        )

        qd_mod.main()

    def test_single_model_filter(self, monkeypatch, tmp_path):
        """--model filters to a single model."""
        from aedist import query_decomposed as qd_mod

        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "doc.md").write_text("data")

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("prompt text")

        models_file = tmp_path / "models.yaml"
        models_file.write_text(
            "- id: model-a\n"
            "  name: A\n"
            "  context_window: 100000\n"
            "  price_per_mtok_in: 1.0\n"
            "  price_per_mtok_out: 2.0\n"
            "- id: model-b\n"
            "  name: B\n"
            "  context_window: 100000\n"
            "  price_per_mtok_in: 1.0\n"
            "  price_per_mtok_out: 2.0\n"
        )

        output_dir = tmp_path / "output"

        monkeypatch.setattr(
            "sys.argv",
            [
                "query_decomposed",
                "--prompt", str(prompt_file),
                "--corpus", str(corpus_dir),
                "--models", str(models_file),
                "--output", str(output_dir),
                "--model", "model-a",
                "--dry-run",
            ],
        )

        qd_mod.main()

    def test_model_not_found_exits(self, monkeypatch, tmp_path):
        """--model with nonexistent model raises SystemExit."""
        from aedist import query_decomposed as qd_mod

        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "doc.md").write_text("data")

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("prompt text")

        models_file = tmp_path / "models.yaml"
        models_file.write_text(
            "- id: model-a\n"
            "  name: A\n"
            "  context_window: 100000\n"
        )

        output_dir = tmp_path / "output"

        monkeypatch.setattr(
            "sys.argv",
            [
                "query_decomposed",
                "--prompt", str(prompt_file),
                "--corpus", str(corpus_dir),
                "--models", str(models_file),
                "--output", str(output_dir),
                "--model", "nonexistent-model",
            ],
        )

        with pytest.raises(SystemExit):
            qd_mod.main()
