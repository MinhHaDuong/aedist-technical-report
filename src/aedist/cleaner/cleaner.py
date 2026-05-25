import json
import logging
import re
import sys
import traceback
import unicodedata
from pathlib import Path
from typing import ClassVar

import pandas as pd

log = logging.getLogger(__name__)


class PowerPlantDataframeCleaner:
    """
    A utility class for cleaning power plant data in a DataFrame.

    It dynamically loads cleaning patterns from a JSON file and standardizes
    columns 'name', 'province', 'fuel', 'capacity', and 'status'.
    """

    REQUIRED_COLUMNS: ClassVar[set[str]] = {"name", "province", "fuel", "capacity", "status"}

    def __init__(self, config_path: str | None = None) -> None:
        """
        Initialize the cleaner by loading patterns from a JSON configuration file.

        Args:
            config_path: Path to the JSON configuration file.
                         Defaults to config.json in the module directory.
        """
        if config_path is None:
            config_path = str(Path(__file__).parent / "config.json")
        try:
            with open(config_path) as file:
                config = json.load(file)
            self.name_drops: list[str] = config.get("name_drops", [])
            self.name_substitutions: dict[str, str] = config.get("name_substitutions", {})
            self.province_substitutions: dict[str, str] = config.get("province_substitutions", {})
            self.fuel_substitutions: dict[str, str] = config.get("fuel_substitutions", {})
            self.status_substitutions: dict[str, str] = config.get("status_substitutions", {})
            log.info("Cleaning patterns loaded successfully from JSON.")
        except FileNotFoundError:
            log.error(f"Configuration file '{config_path}' not found.")
            raise
        except json.JSONDecodeError as e:
            log.error(f"Error decoding JSON configuration file '{config_path}': {e}")
            raise

    def validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate that the input DataFrame is not empty and contains the required columns.

        If the 'name' column is missing but both 'Plant name' and 'Unit name' columns are present,
        it creates the 'name' column by concatenating 'Plant name' and 'Unit name' (space-separated).

        Args:
            df (pd.DataFrame): The input DataFrame.

        Raises:
            ValueError: If the DataFrame is empty or required columns are missing.
        """
        log.info(f"Validating DataFrame with shape: {df.shape}")
        if df.empty:
            log.error("The input DataFrame is empty.")
            raise ValueError("The input DataFrame is empty.")

        df_cols = set(df.columns.str.lower())
        log.debug(f"Columns in DataFrame: {df_cols}")

        # Check if 'name' is missing but 'Plant name' and 'Unit name' exist
        if "name" not in df_cols and "plant name" in df_cols and "unit name" in df_cols:
            log.info(
                "The 'name' column is missing but 'Plant name' and 'Unit name' columns are found. "
                "Creating 'name' column by concatenating 'Plant name' and 'Unit name'."
            )
            df["name"] = df["Plant name"].astype(str) + " " + df["Unit name"].astype(str)
            df_cols.add("name")

        missing_cols = self.REQUIRED_COLUMNS - df_cols
        if missing_cols:
            log.error(f"Missing required columns: {missing_cols}")
            raise ValueError(
                f"DataFrame missing required columns: {missing_cols}\n"
                f"Required: {self.REQUIRED_COLUMNS}\n"
                f"Found: {df_cols}"
            )

        log.info("DataFrame validation completed successfully.")

    def clean_text(self, text: str, drops=None, substitutions=None) -> str | None:
        """
        Clean a text string by removing patterns, applying substitutions, and standardizing whitespace.

        Args:
            text (str): The input text to clean.
            drops (Optional[list[str]]): Regex patterns to drop from the text.
            substitutions (Optional[dict[str, str]]): Regex substitution patterns.

        Returns:
            str | None: The cleaned text, or None if the input was NaN.
        """
        if pd.isna(text):
            log.debug("Encountered NaN value during text cleaning.")
            return None

        s = str(text).lower().strip()
        log.debug(f"Initial text: '{text}', normalized to: '{s}'")

        # Remove diacritics
        # đ/Đ (U+0111/U+0110) is precomposed and not NFD-decomposable; strip explicitly.
        s = s.replace("đ", "d")
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

        # Drop specified patterns
        if drops:
            for pattern in drops:
                s_before = s
                s = re.sub(pattern, "", s, flags=re.IGNORECASE)
                log.debug(f"Dropped pattern '{pattern}': '{s_before}' -> '{s}'")

        # Apply substitutions
        if substitutions:
            for pattern, replacement in substitutions.items():
                s_before = s
                s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
                log.debug(f"Substituted '{pattern}' with '{replacement}': '{s_before}' -> '{s}'")

        # Clean up whitespace
        s = re.sub(r"\s+", " ", s).strip()
        log.debug(f"Final cleaned text: '{s}'")
        return s

    def clean_name(self, name: str) -> str:
        """
        Clean the 'name' column by removing unwanted patterns and normalizing
        any Roman numerals (I, II, III, IV) to Arabic numerals using regex substitutions.

        Args:
            name (str): The input plant name.

        Returns:
            str: The cleaned plant name.
        """
        cleaned = self.clean_text(
            name, drops=self.name_drops, substitutions=self.name_substitutions
        )
        return cleaned

    def clean_province(self, province: str) -> str:
        """Clean the 'province' column."""
        return self.clean_text(province, substitutions=self.province_substitutions)

    def clean_capacity(self, value: str | float | int) -> float | None:
        """
        Clean the 'capacity' column by extracting the first numeric value.

        Args:
            value (str | float | int): The capacity value.

        Returns:
            float | None: The cleaned capacity as a float, or None if invalid.
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip().lower()
        if value_str in ["n/a", "na", ""]:
            return None

        numbers = re.findall(r"\d*\.?\d+", value_str)
        return float(numbers[0]) if numbers else None

    def clean_fuel(self, fuel: str) -> str | None:
        """
        Clean the 'fuel' column and handle multiple fuel types.

        Args:
            fuel (str): The fuel value.

        Returns:
            str | None: The cleaned and standardized fuel value.
        """
        cleaned = self.clean_text(fuel, substitutions=self.fuel_substitutions)
        if cleaned is None:
            return None

        if "/" in cleaned:
            fuels = [f.strip() for f in cleaned.split("/")]
            return "/".join(sorted(fuels))

        return cleaned

    def clean_status(self, status: str) -> str | None:
        """Clean the 'status' column."""
        return self.clean_text(status, substitutions=self.status_substitutions)

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean a power plant DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with required columns (name, province, fuel, capacity, status).

        Returns:
            pd.DataFrame: DataFrame with additional cleaned columns.

        Raises:
            ValueError: If required columns are missing or the DataFrame is empty.
        """
        try:
            self.validate_dataframe(df)
            log.info("Starting DataFrame cleaning process.")

            df = df.copy()
            df.columns = df.columns.str.lower()

            df["name_clean"] = df["name"].apply(self.clean_name)
            df["province_clean"] = df["province"].apply(self.clean_province)
            df["capacity_clean"] = df["capacity"].apply(self.clean_capacity)
            df["status_clean"] = df["status"].apply(self.clean_status)
            df["fuel_clean"] = df["fuel"].apply(self.clean_fuel)

            log.info(f"DataFrame cleaning completed. Final shape: {df.shape}")
            return df

        except Exception as e:
            log.error(f"An error occurred during DataFrame cleaning: {e}")
            log.debug(traceback.format_exc())
            raise


if __name__ == "__main__":
    """
    This script reads a CSV from stdin, cleans the power plant data,
    and writes the cleaned CSV to stdout.

    Usage:
        cat input.csv | python PowerPlantDataframeCleaner.py > cleaned_output.csv
    """
    try:
        input_df = pd.read_csv(sys.stdin)
        cleaner = PowerPlantDataframeCleaner()
        cleaned_df = cleaner.clean_dataframe(input_df)
        cleaned_df.to_csv(sys.stdout, index=False)
        log.info("Data cleaning completed successfully.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
        sys.exit(1)
