import pandas as pd
import re


def normalize_plant_name(name: str) -> str:
    """
    Normalize plant names by removing unit-specific suffixes.
    For example, "PLANTNAME Unit 1" becomes "PLANTNAME".
    """
    # Remove common unit-specific suffixes
    name = re.sub(r" unit \d+", "", name, flags=re.IGNORECASE)
    return name.strip()


def aggregate_units_to_plants(file_path: str) -> pd.DataFrame:
    """
    Aggregates unit-level data to plant-level data while preserving column order.

    Args:
        file_path (str): Path to the input CSV file.

    Returns:
        pd.DataFrame: Aggregated plant-level DataFrame.
    """
    # Load the data
    df = pd.read_csv(file_path)

    # Normalize plant names by removing unit-specific suffixes
    df["Normalized Name"] = df["Name"].apply(normalize_plant_name)

    # Group by Normalized Name and Status, aggregate capacity, and merge other columns
    aggregated = (
        df.groupby(["Normalized Name", "Status", "Province", "Fuel"])
        .agg(
            {
                "Capacity": "sum",  # Sum capacities
                "Name": lambda x: ", ".join(x),  # Combine original unit names
            }
        )
        .reset_index()
    )

    # Rename columns for clarity
    aggregated.rename(
        columns={"Normalized Name": "Name", "Name": "Units Included"}, inplace=True
    )

    # Preserve column order
    column_order = ["Name", "Province", "Fuel", "Capacity", "Status", "Units Included"]
    aggregated = aggregated[column_order]

    return aggregated


if __name__ == "__main__":
    # Input file
    input_file = "HDM.csv"

    # Aggregate units to plant-level
    plant_level_data = aggregate_units_to_plants(input_file)

    # Save the output to a new CSV file
    output_file = "HDM_aggregated.csv"
    plant_level_data.to_csv(output_file, index=False)

    print(f"Aggregated data saved to {output_file}")
