import pandas as pd

# Load the CSV file
file_path = "GEM.csv"  # Replace with the actual file path
df = pd.read_csv(file_path)


# Data aggregation logic
def aggregate_table(dataframe):
    # Extract Phase information (supports both Arabic and Roman numerals) from the Unit name
    dataframe["Phase"] = dataframe["Unit name"].str.extract(r"(Phase [IVXLCDM0-9]+)")
    dataframe["Extension"] = dataframe["Unit name"].str.contains(
        "Extension", case=False, na=False
    )

    # Append Phase name to Plant name (if Phase exists), ensuring a space is added
    dataframe["Plant name"] = dataframe["Plant name"] + dataframe["Phase"].fillna(
        ""
    ).apply(lambda x: f" {x}" if x else "")

    # Identify rows that should be grouped
    # - "Unit X"
    # - "Phase X"
    # - "Extension"
    # - "CCX"
    # - Plain numeric strings (^\d+$)
    dataframe["Groupable"] = dataframe["Unit name"].str.contains(
        r"(?:^\d+$|Unit \d+|Phase [IVXLCDM0-9]+|Extension|CC\d+)", case=False, na=False
    )

    # Separate groupable and non-groupable rows
    non_groupable = dataframe[~dataframe["Groupable"]].copy()
    non_groupable.rename(columns={"Unit name": "Aggregated Units"}, inplace=True)

    # Group groupable rows by Plant name, Province, Fuel, and Status
    groupable = dataframe[dataframe["Groupable"]]
    aggregated_groupable = (
        groupable.groupby(
            ["Plant name", "Province", "Fuel", "Status", "Extension"], dropna=False
        )
        .agg(
            {
                "Capacity": "sum",  # Sum the capacity
                "Unit name": lambda x: ", ".join(x),  # List all units aggregated
            }
        )
        .reset_index()
    )

    # Drop the intermediate column
    aggregated_groupable.drop(columns=["Extension"], inplace=True)

    # Rename the "Unit name" column to "Aggregated Units" for clarity
    aggregated_groupable.rename(columns={"Unit name": "Aggregated Units"}, inplace=True)

    # Reorder the columns for groupable
    aggregated_groupable = aggregated_groupable[
        ["Plant name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"]
    ]

    # For non-groupable rows, rename "Unit name" to "Aggregated Units" for consistency
    non_groupable = non_groupable[
        ["Plant name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"]
    ]

    # Combine groupable and non-groupable rows
    final_df = pd.concat([aggregated_groupable, non_groupable], ignore_index=True)

    # Rename the first column to "Name"
    final_df.rename(columns={"Plant name": "Name"}, inplace=True)

    # Sort the final DataFrame for better readability
    final_df = final_df.sort_values(by=["Name", "Province", "Status"]).reset_index(
        drop=True
    )
    return final_df


# Apply the aggregation to the DataFrame
aggregated_df = aggregate_table(df)

# Save the aggregated table to a new CSV file
output_file = "GEM_aggregated.csv"
aggregated_df.to_csv(output_file, index=False)

# Print the output location
print(f"Aggregated data saved to {output_file}")
