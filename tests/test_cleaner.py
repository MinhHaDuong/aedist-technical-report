import pytest
import pandas as pd
import json
from aedist.cleaner import PowerPlantDataframeCleaner


@pytest.fixture
def cleaner():
    """Fixture to initialize the cleaner with a test JSON configuration."""
    return PowerPlantDataframeCleaner("src/aedist/cleaner/config.json")


def test_validate_dataframe_valid(cleaner):
    """Test DataFrame validation with all required columns."""
    df = pd.DataFrame(
        {
            "name": ["Plant A"],
            "province": ["Ho Chi Minh City"],
            "fuel": ["Coal"],
            "capacity": ["500 MW"],
            "status": ["operating"],
        }
    )
    try:
        cleaner.validate_dataframe(df)
    except Exception:
        pytest.fail("validate_dataframe() raised an unexpected exception!")


def test_validate_dataframe_missing_name(cleaner):
    """Test DataFrame validation when 'name' is created from 'Plant name' and 'Unit name'."""
    df = pd.DataFrame(
        {
            "Plant name": ["Plant A"],
            "Unit name": ["Unit 1"],
            "province": ["Ho Chi Minh City"],
            "fuel": ["Coal"],
            "capacity": ["500 MW"],
            "status": ["operating"],
        }
    )
    cleaner.validate_dataframe(df)
    assert "name" in df.columns
    assert df["name"].iloc[0] == "Plant A Unit 1"


def test_validate_dataframe_missing_columns(cleaner):
    """Test DataFrame validation with missing required columns."""
    df = pd.DataFrame({"province": ["Ho Chi Minh City"], "fuel": ["Coal"]})
    with pytest.raises(ValueError, match=r"DataFrame missing required columns: \{.*\}"):
        cleaner.validate_dataframe(df)


def test_clean_text_drops(cleaner):
    """Test text cleaning with drops."""
    text = "TBKHH Plant A Thermal (Local)"
    cleaned = cleaner.clean_text(text, drops=cleaner.name_drops)
    assert cleaned == "plant a"


def test_clean_text_substitutions(cleaner):
    """Test text cleaning with substitutions."""
    text = "Ho Chi Minh City"
    cleaned = cleaner.clean_text(text, substitutions=cleaner.province_substitutions)
    assert cleaned == "tp ho chi minh"


def test_clean_name(cleaner):
    """Test cleaning of the 'name' column."""
    name = "TBKHH Plant A Thermal"
    cleaned = cleaner.clean_name(name)
    assert cleaned == "plant a"


def test_clean_province(cleaner):
    """Test cleaning of the 'province' column."""
    province = "Ho Chi Minh City"
    cleaned = cleaner.clean_province(province)
    assert cleaned == "tp ho chi minh"


def test_clean_capacity(cleaner):
    """Test cleaning of the 'capacity' column."""
    assert cleaner.clean_capacity("500 MW") == 500.0
    assert cleaner.clean_capacity("300") == 300.0
    assert cleaner.clean_capacity("N/A") is None


def test_clean_status(cleaner):
    """Test cleaning of the 'status' column."""
    assert cleaner.clean_status("Operating") == "operating"
    assert cleaner.clean_status("Construction") == "construction"
    assert cleaner.clean_status("123 Operating") == "operating"


def test_clean_dataframe(cleaner):
    """Test cleaning of the entire DataFrame."""
    df = pd.DataFrame(
        {
            "name": ["TBKHH Plant A Thermal"],
            "province": ["Ho Chi Minh City"],
            "fuel": ["Coal (Local)"],
            "capacity": ["500 MW"],
            "status": ["123 Operating"],
        }
    )
    cleaned_df = cleaner.clean_dataframe(df)
    assert cleaned_df["name_clean"].iloc[0] == "plant a"
    assert cleaned_df["province_clean"].iloc[0] == "tp ho chi minh"
    assert cleaned_df["capacity_clean"].iloc[0] == 500.0
    assert cleaned_df["fuel_clean"].iloc[0] == "coal"
    assert cleaned_df["status_clean"].iloc[0] == "operating"


def test_clean_capacity_edge_cases(cleaner):
    """Test capacity cleaning with unusual formats."""
    assert cleaner.clean_capacity("approx. 500 MW") == 500.0
    assert cleaner.clean_capacity("~300 MW") == 300.0
    assert cleaner.clean_capacity(None) is None
    assert cleaner.clean_capacity("") is None


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        PowerPlantDataframeCleaner("missing_file.json")


def test_invalid_json_file(tmp_path):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{invalid_json}")  # Malformed JSON
    with pytest.raises(json.JSONDecodeError):
        PowerPlantDataframeCleaner(str(invalid_json))
