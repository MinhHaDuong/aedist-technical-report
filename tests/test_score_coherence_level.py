"""Tests for level-conditioned capacity coherence predicates (ticket 0402).

Coverage:
- capacity_plausible_for_level: per-row predicate, curated fixtures.
- level_consistent_with_name: per-row predicate, curated fixtures.
- score_capacity_plausible_for_level: run-level fraction scorer.
- score_level_consistent_with_name: run-level fraction scorer.

Ticket 0402 curated fixtures (from the ticket's "First failing test" section):

  F1: {name:"Cẩm Phả 1", level:"plant", fuel:"coal", capacity_mwe:6000}
      capacity_plausible_for_level → False  (Plant cap ≤ 3200 MW)

  F2: {name:"LNG Mỹ Giang", level:"complex", capacity_mwe:6000}
      capacity_plausible_for_level → True   (Complex has no upper cap)

  F3: {name:"Nhơn Trạch 3 & 4", level:"unit", capacity_mwe:1500}
      level_consistent_with_name → False    (R1: merge-marker ≠ Unit)

  F4: {name:"Vinh Tan 2", level:"unit", fuel:"coal", capacity_mwe:1244}
      capacity_plausible_for_level → True   (1244 ≤ 1350 MW Unit cap)
      level_consistent_with_name  → False   (R3: Site+number implies Plant)

F4 rationale: "Vinh Tan 2" is a Site+number name (no explicit unit token).
Per R3, such names structurally imply Plant level — declaring Unit is
incoherent even though the capacity passes the Unit cap.  The rule encodes
VN naming convention: Unit-grain names carry an explicit unit token
("Vinh Tan 2 Unit 1", "Tổ máy 1"), while "Vinh Tan 2" alone is a Plant.
"""


from aedist.score_coherence_level import (
    capacity_plausible_for_level,
    level_consistent_with_name,
    score_capacity_plausible_for_level,
    score_level_consistent_with_name,
)

# ---------------------------------------------------------------------------
# capacity_plausible_for_level
# ---------------------------------------------------------------------------


class TestCapacityPlausibleForLevel:
    def test_f1_cam_pha_plant_6000_mw_fails(self):
        """F1: 6000 MW declared Plant — exceeds Plant cap (3200 MW)."""
        assert capacity_plausible_for_level("plant", "coal", 6000.0) is False

    def test_f2_lng_my_giang_complex_6000_mw_passes(self):
        """F2: 6000 MW declared Complex — Complex has no upper cap."""
        assert capacity_plausible_for_level("complex", "imported lng", 6000.0) is True

    def test_f4_vinh_tan_2_unit_1244_mw_passes_cap(self):
        """F4: 1244 MW declared Unit — below Unit cap (1350 MW) → True."""
        assert capacity_plausible_for_level("unit", "coal", 1244.0) is True

    def test_unit_at_cap_boundary(self):
        """Unit at exactly 1350 MW — on the cap → passes."""
        assert capacity_plausible_for_level("unit", "coal", 1350.0) is True

    def test_unit_above_cap(self):
        """Unit above 1350 MW → fails."""
        assert capacity_plausible_for_level("unit", "coal", 1351.0) is False

    def test_plant_at_cap_boundary(self):
        """Plant at exactly 3200 MW — on the cap → passes."""
        assert capacity_plausible_for_level("plant", "imported lng", 3200.0) is True

    def test_plant_above_cap(self):
        """Plant above 3200 MW → fails."""
        assert capacity_plausible_for_level("plant", "coal", 3201.0) is False

    def test_plant_typical_operating(self):
        """Typical operating plant (600 MW) → passes."""
        assert capacity_plausible_for_level("plant", "coal", 600.0) is True

    def test_block_typical_ccgt(self):
        """CCGT block above 1300 MW → passes."""
        assert capacity_plausible_for_level("block", "gas", 1500.0) is True

    def test_block_too_small(self):
        """Block below 1300 MW → fails (not a multi-shaft CCGT assembly)."""
        assert capacity_plausible_for_level("block", "gas", 600.0) is False

    def test_unknown_level_returns_none(self):
        """Level.Unknown → cannot score → None."""
        assert capacity_plausible_for_level("unknown", "coal", 600.0) is None

    def test_absent_capacity_returns_none(self):
        """Missing capacity → cannot score → None."""
        assert capacity_plausible_for_level("plant", "coal", None) is None

    def test_complex_small_capacity_passes(self):
        """Complex at 600 MW (unusual but not disallowed) → passes."""
        assert capacity_plausible_for_level("complex", "gas", 600.0) is True

    def test_level_enum_accepted(self):
        """Level enum values accepted as well as strings."""
        from aedist.schema import Level

        assert capacity_plausible_for_level(Level.UNIT, "coal", 300.0) is True
        assert capacity_plausible_for_level(Level.PLANT, "coal", 6000.0) is False

    def test_invalid_level_string_returns_none(self):
        """Unrecognised level string → None."""
        assert capacity_plausible_for_level("mega-plant", "coal", 600.0) is None


# ---------------------------------------------------------------------------
# level_consistent_with_name
# ---------------------------------------------------------------------------


class TestLevelConsistentWithName:
    def test_f3_merge_marker_unit_fails_r1(self):
        """F3: 'Nhơn Trạch 3 & 4' declared Unit — merge marker ≠ Unit (R1)."""
        assert level_consistent_with_name("Nhơn Trạch 3 & 4", "unit") is False

    def test_f4_site_number_unit_fails_r3(self):
        """F4: 'Vinh Tan 2' declared Unit — Site+number implies Plant (R3)."""
        assert level_consistent_with_name("Vinh Tan 2", "unit") is False

    def test_site_number_declared_plant_passes(self):
        """'Vinh Tan 2' declared Plant — consistent with R3."""
        assert level_consistent_with_name("Vinh Tan 2", "plant") is True

    def test_merge_marker_plant_passes_r1(self):
        """'Nhơn Trạch 3 & 4' declared Plant is allowed (R1 only blocks Unit)."""
        assert level_consistent_with_name("Nhơn Trạch 3 & 4", "plant") is True

    def test_merge_marker_complex_passes(self):
        """'Nhơn Trạch 3 & 4' declared Complex — not blocked by R1."""
        assert level_consistent_with_name("Nhơn Trạch 3 & 4", "complex") is True

    def test_explicit_unit_token_declared_unit_passes(self):
        """'Vinh Tan 2 Unit 1' declared Unit — has explicit unit token → consistent."""
        assert level_consistent_with_name("Vinh Tan 2 Unit 1", "unit") is True

    def test_bare_site_declared_unit_fails_r2(self):
        """'Cà Mau' declared Unit — bare site ≠ Unit (R2)."""
        assert level_consistent_with_name("Cà Mau", "unit") is False

    def test_bare_site_declared_plant_fails_r2(self):
        """'Hải Phòng' declared Plant — bare site ≠ Plant (R2)."""
        assert level_consistent_with_name("Hải Phòng", "plant") is False

    def test_bare_site_declared_complex_passes_r2(self):
        """'Cà Mau' declared Complex — bare site is consistent with Complex."""
        assert level_consistent_with_name("Cà Mau", "complex") is True

    def test_lng_complex_name_declared_complex_passes(self):
        """'LNG Mỹ Giang' declared Complex — passes (has no number, no merge marker)."""
        # "LNG" makes it not a bare site per the digit check (no digit) ...
        # but "LNG" contains letters only — this is a bare-site-like name.
        # Per R2, bare sites cannot be Plant or Unit; Complex is fine.
        assert level_consistent_with_name("LNG Mỹ Giang", "complex") is True

    def test_unknown_level_returns_none(self):
        """Level.Unknown → cannot score → None."""
        assert level_consistent_with_name("Vinh Tan 2", "unknown") is None

    def test_empty_name_returns_none(self):
        """Empty name → cannot score → None."""
        assert level_consistent_with_name("", "plant") is None

    def test_cam_pha_1_plant_consistent(self):
        """'Cẩm Phả 1' declared Plant — Site+number is consistent with Plant."""
        assert level_consistent_with_name("Cẩm Phả 1", "plant") is True

    def test_nhon_trach_3_and_4_complex_passes(self):
        """Merge-marker name declared Complex — not blocked by any rule."""
        assert level_consistent_with_name("Nhơn Trạch 3 & 4", "complex") is True

    def test_vietnamese_range_unit_fails_r1(self):
        """'Cẩm Phả 1 & 2' declared Unit — merge marker ≠ Unit."""
        assert level_consistent_with_name("Cẩm Phả 1 & 2", "unit") is False

    def test_roman_numeral_range_unit_fails_r1(self):
        """'Phả Lại I & II' declared Unit — merge marker ≠ Unit."""
        assert level_consistent_with_name("Phả Lại I & II", "unit") is False

    def test_level_enum_accepted(self):
        """Level enum values accepted."""
        from aedist.schema import Level

        assert level_consistent_with_name("Vinh Tan 2", Level.PLANT) is True
        assert level_consistent_with_name("Vinh Tan 2", Level.UNIT) is False

    def test_invalid_level_returns_none(self):
        """Unrecognised level string → None."""
        assert level_consistent_with_name("Vinh Tan 2", "mega-plant") is None


# ---------------------------------------------------------------------------
# score_capacity_plausible_for_level (run-level)
# ---------------------------------------------------------------------------


class TestScoreCapacityPlausibleForLevel:
    def test_empty_rows_returns_none(self):
        frac, ann = score_capacity_plausible_for_level([])
        assert frac is None
        assert ann == "no_rows"

    def test_no_level_column_returns_none(self):
        rows = [{"name": "Plant A", "capacity_mwe": "600"}]
        frac, ann = score_capacity_plausible_for_level(rows)
        assert frac is None
        assert ann == "column_missing"

    def test_all_plausible(self):
        rows = [
            {"name": "Vinh Tan 2", "level": "plant", "capacity_mwe": "600"},
            {"name": "LNG Mỹ Giang", "level": "complex", "capacity_mwe": "6000"},
        ]
        frac, ann = score_capacity_plausible_for_level(rows)
        assert frac == 1.0
        assert ann is None

    def test_one_implausible_plant(self):
        rows = [
            {"name": "Cẩm Phả 1", "level": "plant", "fuel": "coal", "capacity_mwe": "6000"},
            {"name": "Vinh Tan 2", "level": "plant", "fuel": "coal", "capacity_mwe": "600"},
        ]
        frac, ann = score_capacity_plausible_for_level(rows)
        assert frac == 0.5
        assert ann is None

    def test_unknown_level_rows_skipped(self):
        """Rows with level=unknown are excluded from the fraction denominator."""
        rows = [
            {"name": "Plant A", "level": "unknown", "capacity_mwe": "600"},
            {"name": "Plant B", "level": "plant", "capacity_mwe": "500"},
        ]
        frac, ann = score_capacity_plausible_for_level(rows)
        assert frac == 1.0  # Only Plant B is scoreable

    def test_missing_capacity_rows_skipped(self):
        """Rows without capacity are excluded from the denominator."""
        rows = [
            {"name": "Plant A", "level": "plant"},
            {"name": "Plant B", "level": "plant", "capacity_mwe": "500"},
        ]
        frac, ann = score_capacity_plausible_for_level(rows)
        assert frac == 1.0  # Only Plant B is scoreable


# ---------------------------------------------------------------------------
# score_level_consistent_with_name (run-level)
# ---------------------------------------------------------------------------


class TestScoreLevelConsistentWithName:
    def test_empty_rows_returns_none(self):
        frac, ann = score_level_consistent_with_name([])
        assert frac is None
        assert ann == "no_rows"

    def test_no_level_column_returns_none(self):
        rows = [{"name": "Vinh Tan 2"}]
        frac, ann = score_level_consistent_with_name(rows)
        assert frac is None
        assert ann == "column_missing"

    def test_all_consistent(self):
        rows = [
            {"name": "Vinh Tan 2", "level": "plant"},
            {"name": "LNG Mỹ Giang", "level": "complex"},
        ]
        frac, ann = score_level_consistent_with_name(rows)
        assert frac == 1.0
        assert ann is None

    def test_one_inconsistent(self):
        rows = [
            {"name": "Nhơn Trạch 3 & 4", "level": "unit"},  # R1 violation
            {"name": "Vinh Tan 2", "level": "plant"},
        ]
        frac, ann = score_level_consistent_with_name(rows)
        assert frac == 0.5
        assert ann is None

    def test_unknown_level_rows_skipped(self):
        rows = [
            {"name": "Plant A", "level": "unknown"},
            {"name": "Vinh Tan 2", "level": "plant"},
        ]
        frac, ann = score_level_consistent_with_name(rows)
        assert frac == 1.0

    def test_empty_name_rows_skipped(self):
        rows = [
            {"name": "", "level": "plant"},
            {"name": "Vinh Tan 2", "level": "plant"},
        ]
        frac, ann = score_level_consistent_with_name(rows)
        assert frac == 1.0


# ---------------------------------------------------------------------------
# Integration: score_coherence() populates new fields (ticket 0402)
# ---------------------------------------------------------------------------


class TestScoreCoherenceIntegration:
    """Verify that score_coherence() in score_mechanical correctly delegates
    capacity_plausible_for_level and level_consistent_with_name to the
    canonical implementations in score_coherence_level.py."""

    def test_coherence_populates_capacity_plausible_for_level(self):
        """score_coherence() populates capacity_plausible_for_level when level present."""
        from aedist.score_mechanical import score_coherence

        rows = [
            {"name": "Vinh Tan 2", "fuel": "coal", "status": "operating",
             "level": "plant", "capacity_mwe": "600"},
            {"name": "Cẩm Phả 1", "fuel": "coal", "status": "operating",
             "level": "plant", "capacity_mwe": "6000"},  # Plant cap violation
        ]
        result = score_coherence(rows)
        # One of two rows is plausible for level (600 MW Plant = OK; 6000 MW Plant = fail)
        assert result.capacity_plausible_for_level == 0.5

    def test_coherence_populates_level_consistent_with_name(self):
        """score_coherence() populates level_consistent_with_name when level present."""
        from aedist.score_mechanical import score_coherence

        rows = [
            {"name": "Vinh Tan 2", "fuel": "coal", "status": "operating",
             "level": "plant", "capacity_mwe": "600"},
            {"name": "Nhơn Trạch 3 & 4", "fuel": "gas", "status": "operating",
             "level": "unit", "capacity_mwe": "1500"},  # R1 violation
        ]
        result = score_coherence(rows)
        assert result.level_consistent_with_name == 0.5

    def test_coherence_none_when_no_level_column(self):
        """score_coherence() returns None for level fields when level key absent."""
        from aedist.score_mechanical import score_coherence

        rows = [
            {"name": "Vinh Tan 2", "fuel": "coal", "status": "operating",
             "capacity_mwe": "600"},
        ]
        result = score_coherence(rows)
        assert result.capacity_plausible_for_level is None
        assert result.capacity_plausible_for_level_annotation == "column_missing"
        assert result.level_consistent_with_name is None
