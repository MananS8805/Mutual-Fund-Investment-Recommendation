import pandas as pd

# Load CSV files (make sure they are in the same folder)
df_master = pd.read_csv("mf_complete_dataset.csv")
df_perf = pd.read_csv("mftool_production_dataset.csv")

# Ensure scheme_code types match
df_master['scheme_code'] = df_master['scheme_code'].astype(str)
df_perf['scheme_code'] = df_perf['scheme_code'].astype(str)

# LEFT JOIN on scheme_code
merged_df = df_master.merge(
    df_perf,
    on="scheme_code",
    how="left",
    suffixes=("_master", "_perf")
)

# Print basic info
print("Merged dataset shape:", merged_df.shape)
print("\nColumns:")
print(merged_df.columns.tolist())

# Save merged file (use a new name to avoid permission issues)
merged_df.to_csv("mf_merged_raw.csv", index=False)

print("\n✅ Merge completed successfully")
