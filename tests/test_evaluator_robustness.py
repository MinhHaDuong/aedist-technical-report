"""Regression tests for evaluator robustness to prompt_complete output formats.

Diagnosis (2026-05-05): three frontier models scored F1=None on prompt_complete
runs, not due to an evaluator bug but due to genuine non-attempts:
  - GPT-5.4, Grok 4.20: status=refusal (no tables at all in response)
  - Ernie 4.5 Thinking: status=error (aggregate capacity tables present, but
    no per-plant inventory table with a plant-name column)

The evaluator correctly classifies all three via `_classify_orphan()`.
These tests pin that behavior so any future regression is caught immediately.
"""

import json

from aedist.evaluate import _classify_orphan
from aedist.extract import ExtractStatus, extract_one


class TestRefusalClassification:
    """Pure refusal responses (no tables) must be classified as 'refusal'."""

    def test_gpt_style_refusal(self):
        """GPT-5.4 style: multi-sentence capability-decline prose, no tables."""
        raw = {
            "model": "openai/gpt-5.4",
            "response": (
                "I appreciate your request for information about Vietnam's thermal power plants. "
                "However, I'm not able to provide a structured inventory table of power plant "
                "data in the requested format. This type of detailed infrastructure data "
                "requires up-to-date official sources, and I cannot verify the accuracy of "
                "specific plant-level details such as current operational status, exact "
                "commissioned capacity, or province-level locations. I recommend consulting "
                "the Vietnam Electricity (EVN) annual reports or the Ministry of Industry and "
                "Trade's official power development plan documents for authoritative data."
            ),
        }
        assert _classify_orphan(raw) == "refusal"

    def test_grok_style_refusal(self):
        """Grok 4.20 style: policy-based decline with numbered concerns, no tables."""
        raw = {
            "model": "x-ai/grok-4.20",
            "response": (
                "I need to decline producing this inventory for the following reasons:\n\n"
                "1. Accuracy concerns: Power plant operational data changes frequently "
                "and a static table risks propagating stale information.\n"
                "2. Scope: A comprehensive list of all thermal plants in Vietnam would "
                "require access to current grid operator databases.\n"
                "3. Format: Producing a per-plant CSV without verified sources would be "
                "irresponsible given the policy implications of energy infrastructure data.\n\n"
                "I recommend using official PDP8 documentation or the Global Energy Monitor "
                "coal plant tracker for verified inventory data."
            ),
        }
        assert _classify_orphan(raw) == "refusal"


class TestAggregateTableError:
    """Ernie-style responses: aggregate capacity tables present, but no per-plant
    inventory table with a plant-name column → classified as 'error'."""

    def test_aggregate_fuel_table_is_error(self):
        """Aggregate pipe table (Fuel | Total Capacity) with no plant-name column.

        This is the Ernie 4.5 Thinking pattern: model produces a sector overview
        with aggregate statistics, not a per-plant inventory. The table is detected
        (so not 'refusal') but cannot be parsed as a plant inventory (hence 'error').
        """
        raw = {
            "model": "baidu/ernie-4.5-21b-a3b-thinking",
            "response": (
                "## Vietnam Thermal Power Sector Overview\n\n"
                "Vietnam's thermal power sector comprises coal, gas, and oil plants "
                "that together supply approximately 55% of national electricity.\n\n"
                "### Capacity by Fuel Type\n\n"
                "| Fuel Type | Total Capacity (MW) | Share (%) |\n"
                "|-----------|--------------------|-----------|\n"
                "| Coal      | 26,450             | 34.2      |\n"
                "| Natural Gas | 7,200            | 9.3       |\n"
                "| Oil       | 850                | 1.1       |\n\n"
                "**Source**: Ministry of Industry and Trade, PDP8 (2023)\n\n"
                "### Development Status\n\n"
                "| Status      | Count | Capacity (MW) |\n"
                "|-------------|-------|---------------|\n"
                "| Operational | 32    | 21,300        |\n"
                "| Constructing| 8     | 7,200         |\n"
                "| Planned     | 12    | 6,000         |\n\n"
                "**Note**: Individual plant details require verification against "
                "official EVN registry data.\n"
            ),
        }
        assert _classify_orphan(raw) == "error"

    def test_field_value_prose_with_table_is_error(self):
        """Ernie pattern: **Field**: value prose with an aggregate summary table."""
        raw = {
            "model": "baidu/ernie-4.5-21b-a3b-thinking",
            "response": (
                "**Country**: Vietnam\n"
                "**Sector**: Thermal power\n"
                "**Data Source**: PDP8, EVN Annual Report 2023\n\n"
                "Below is a summary of installed thermal capacity:\n\n"
                "| Province | Coal Capacity (MW) | Gas Capacity (MW) |\n"
                "|----------|--------------------|-------------------|\n"
                "| Quang Ninh | 4,800            | 0                 |\n"
                "| Hai Phong  | 2,400            | 0                 |\n"
                "| Ba Ria–Vung Tau | 0           | 2,300             |\n\n"
                "Note: These are provincial aggregates. Per-plant breakdown not available.\n"
            ),
        }
        # Province-level aggregate table: pipe table present → 'error', not 'refusal'
        assert _classify_orphan(raw) == "error"


class TestWellFormedPlantInventory:
    """A well-formed prompt_complete response with a per-plant inventory table
    must be extracted successfully by extract_one (ExtractStatus.WROTE)."""

    def test_pipe_table_inventory_extracted(self, tmp_path):
        """A markdown pipe table with Name, Province, Fuel, Status columns is
        extracted to CSV by extract_one without error.

        This is the success path that should never regress: if pipe-table
        extraction or parse_and_canonicalize breaks, this test fails first.
        """
        response_with_inventory = (
            "## Vietnam Thermal Power Plants — Inventory\n\n"
            "The following table lists operational and under-construction thermal "
            "plants based on PDP8 data.\n\n"
            "| Name | Province | Fuel | Status | Capacity (MWe) |\n"
            "|------|----------|------|--------|----------------|\n"
            "| Pha Lai 1 | Hai Duong | Coal | Operational | 440 |\n"
            "| Pha Lai 2 | Hai Duong | Coal | Operational | 600 |\n"
            "| Uong Bi   | Quang Ninh | Coal | Operational | 150 |\n"
            "| Quang Ninh 1 | Quang Ninh | Coal | Operational | 600 |\n"
            "| Quang Ninh 2 | Quang Ninh | Coal | Operational | 600 |\n"
            "| Nghi Son 1 | Thanh Hoa | Coal | Operational | 600 |\n"
            "| Ca Mau 1 | Ca Mau | Gas | Operational | 750 |\n"
            "| Ca Mau 2 | Ca Mau | Gas | Operational | 750 |\n\n"
            "Sources: EVN Annual Report 2023; Global Energy Monitor 2024.\n"
        )
        payload = {
            "model": "z-ai/glm-5-turbo",
            "response": response_with_inventory,
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 500, "completion_tokens": 1200},
        }
        json_path = tmp_path / "glm-5-turbo-run1.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")

        result = extract_one(json_path, tmp_path, overwrite=True)

        assert result.status is ExtractStatus.WROTE, (
            f"Expected WROTE but got {result.status}: {result.message}"
        )
        assert result.output_path is not None
        assert result.output_path.exists()

        # Verify the CSV has plant rows (not just a header)
        csv_text = result.output_path.read_text(encoding="utf-8")
        lines = [ln for ln in csv_text.splitlines() if ln.strip()]
        assert len(lines) >= 9, "Expected header + 8 data rows"
        # First data row should contain 'Pha Lai 1'
        assert "Pha Lai 1" in csv_text, "Expected plant name 'Pha Lai 1' in extracted CSV"

    def test_fenced_csv_inventory_extracted(self, tmp_path):
        """A fenced CSV block with per-plant rows is extracted correctly."""
        response_with_fenced = (
            "Here is the inventory of Vietnam thermal power plants:\n\n"
            "```csv\n"
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Pha Lai 1,Coal,Operational,1983,Hai Duong,440\n"
            "Pha Lai 2,Coal,Operational,2001,Hai Duong,600\n"
            "Uong Bi,Coal,Operational,1963,Quang Ninh,150\n"
            "Quang Ninh 1,Coal,Operational,2003,Quang Ninh,600\n"
            "Ca Mau 1,Gas,Operational,2008,Ca Mau,750\n"
            "```\n\n"
            "The above plants represent the main coal and gas facilities "
            "currently in operation as of 2024."
        )
        payload = {
            "model": "anthropic/claude-opus-4.6",
            "response": response_with_fenced,
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 500, "completion_tokens": 800},
        }
        json_path = tmp_path / "claude-opus-4.6-run1.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")

        result = extract_one(json_path, tmp_path, overwrite=True)

        assert result.status is ExtractStatus.WROTE, (
            f"Expected WROTE but got {result.status}: {result.message}"
        )
        csv_text = result.output_path.read_text(encoding="utf-8")
        assert "Pha Lai 1" in csv_text
        assert "Ca Mau 1" in csv_text
