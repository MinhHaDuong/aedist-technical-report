import importlib
import pytest
import pandas as pd

# Parameterize the fixture over both implementations to run after this change.
@pytest.fixture(params=["lp", "phased"])
def reconcile(request):
    module = importlib.import_module(f"aedist.matching.{request.param}")
    return module.reconcile

def test_exact_match(reconcile):
    """Test when group1 and group2 contain exactly matching rows."""
    group1 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 50}
    ])
    group2 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 50}
    ])

    result = reconcile(group1, group2)

    # Expect a single match with exactly equal capacities.
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched"
    assert row["capacity_file1"] == 50
    assert row["capacity_file2"] == 50
    assert row["capacity_difference"] == 0

def test_only_in_file1(reconcile):
    """Test when group2 is empty, so all group1 capacity is unmatched."""
    group1 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}
    ])
    group2 = pd.DataFrame(columns=["name", "name_clean", "capacity_clean"])

    result = reconcile(group1, group2)

    # Expect a single row flagged as "Only in file1".
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Only in file1"
    assert row["capacity_file1"] == 100
    assert row["name_file2"] is None

def test_only_in_file2(reconcile):
    """Test when group1 is empty, so all group2 capacity is unmatched."""
    group1 = pd.DataFrame(columns=["name", "name_clean", "capacity_clean"])
    group2 = pd.DataFrame([
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 80}
    ])

    result = reconcile(group1, group2)

    # Expect a single row flagged as "Only in file2".
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Only in file2"
    assert row["capacity_file2"] == 80
    assert row["name_file1"] is None

def test_fuzzy_match_name(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    within the allowed tolerance.
    """
    group1 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}
    ])
    group2 = pd.DataFrame([
        {
            "name": "Plant A Incorporated",
            "name_clean": "plant a incorporated",
            "capacity_clean": 100,
        }
    ])

    result = reconcile(group1, group2)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy)"

def test_fuzzy_match_within_tolerance(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    within the allowed tolerance.
    """
    group1 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}
    ])
    group2 = pd.DataFrame([
        {
            "name": "Plant A Incorporated",
            "name_clean": "plant a incorporated",
            "capacity_clean": 145,
        }
    ])

    result = reconcile(group1, group2, capacity_tolerance=50)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy)"
    assert row["capacity_file1"] == 100
    assert row["capacity_file2"] == 145

def test_fuzzy_match_outside_tolerance(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    outside of the allowed tolerance.
    """
    group1 = pd.DataFrame([
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}
    ])
    group2 = pd.DataFrame([
        {
            "name": "Plant A Incorporated",
            "name_clean": "plant a incorporated",
            "capacity_clean": 145,
        }
    ])

    result = reconcile(group1, group2, capacity_tolerance=0)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy) (Diff)"
    assert row["capacity_file1"] == 100
    assert row["capacity_file2"] == 145

def test_main_example(reconcile):
    """
    Test the demo example originally run in the main() block.
    We expect two matches:
      - "Plant A" from file1 should be matched to "Plant A Incorporated" in file2 with a capacity difference of -5 and status "Matched (Fuzzy)".
      - "Plant B" should be exactly matched.
    """
    data1 = [
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100},
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
    ]
    data2 = [
        {"name": "Plant A Incorporated", "name_clean": "plant a incorporated", "capacity_clean": 105},
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
    ]
    file1_df = pd.DataFrame(data1)
    file2_df = pd.DataFrame(data2)
    result = reconcile(
        file1_df,
        file2_df,
        similarity_threshold=90,
        capacity_tolerance=10,
        mismatch_penalty=1000,
    )
    
    # There should be exactly two rows of matches.
    assert len(result) == 2

    # Identify the matched pairs based on file1's name.
    row_a = result[result["name_file1"] == "Plant A"].iloc[0]
    row_b = result[result["name_file1"] == "Plant B"].iloc[0]
    
    # For Plant A: capacity difference = 100 - 105 = -5 (fuzzy match within tolerance)
    assert row_a["capacity_difference"] == -5
    assert row_a["status"] == "Matched (Fuzzy)"
    
    # For Plant B: capacity difference = 200 - 200 = 0 (exact match)
    assert row_b["capacity_difference"] == 0
    assert row_b["status"] == "Matched"

if __name__ == "__main__":
    pytest.main()
