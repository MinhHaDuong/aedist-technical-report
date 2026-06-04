#!/bin/sh -e
# Build the _v1_fix1 reference files from the frozen v1 (ticket 0394).
#
# Four line-edits, author-adjudicated 2026-06-03/04 — see PROVENANCE.md §fix1:
#   plants: drop the 'Duyen Hai 2' 600 MW romanization duplicate;
#           fix the 'Quảng Trị 1' units_included typo ("Unit 2, Unit 2").
#   units:  drop the 'Duyen Hai 2 Unit 1' duplicate;
#           rename the FIRST of the two identical 'Quảng Trị 1 Unit 2' rows.
#
# Plain text filters: untouched lines are byte-identical by construction
# (no spreadsheet, no csv round-trip — leading zeros in ires_code survive).
# The guards below fail loudly if any edit did not land exactly once.
# Run from the repo root. Usage: build_reference_v1_fix1.sh [reference_dir]

ref=${1:-data/reference}

grep -vF 'Duyen Hai 2,Tra Vinh,coal,600.0,' "$ref/vietnam_thermal_v1.csv" |
sed 's/"Quảng Trị 1 Unit 2, Quảng Trị 1 Unit 2"/"Quảng Trị 1 Unit 1, Quảng Trị 1 Unit 2"/' \
  > "$ref/vietnam_thermal_v1_fix1.csv"

grep -vF 'Duyen Hai 2 Unit 1,' "$ref/vietnam_thermal_units_v1.csv" |
awk '!d && /^Quảng Trị 1 Unit 2,/ {sub(/Unit 2/, "Unit 1"); d=1} 1' \
  > "$ref/vietnam_thermal_units_v1_fix1.csv"

# Loud guards: exact expected counts, else fail.
test "$(wc -l < "$ref/vietnam_thermal_v1_fix1.csv")" -eq 163          # header + 162 rows
test "$(grep -c 'Quảng Trị 1 Unit 1' "$ref/vietnam_thermal_v1_fix1.csv")" -eq 1
test "$(wc -l < "$ref/vietnam_thermal_units_v1_fix1.csv")" -eq 250    # header + 249 rows
test "$(grep -cF 'Quảng Trị 1 Unit 1,' "$ref/vietnam_thermal_units_v1_fix1.csv")" -eq 1
test "$(grep -cF 'Quảng Trị 1 Unit 2,' "$ref/vietnam_thermal_units_v1_fix1.csv")" -eq 1

echo "fix1 built: $ref/vietnam_thermal_v1_fix1.csv (162 rows), $ref/vietnam_thermal_units_v1_fix1.csv (249 rows)"
