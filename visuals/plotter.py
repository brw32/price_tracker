import pandas as pd
import matplotlib.pyplot as plt
import os
import re # Import regex module

# Path to the data file
DATA_FILE = os.path.join("data", "prices.csv")
# Directory to save charts
CHARTS_DIR = "visuals"

def _get_safe_filename_base(product_name):
    """
    Generates a filesystem-safe and consistent base name for a product chart file.
    It removes non-alphanumeric/non-space characters, then replaces spaces with underscores.
    """
    # Replace any character that is NOT a word character (alphanumeric + underscore) or a space
    # with an empty string. This removes characters like commas, hyphens etc.
    temp_name = re.sub(r'[^\w\s]', '', product_name)
    # Replace one or more whitespace characters with a single underscore, then strip leading/trailing underscores
    safe_name = re.sub(r'\s+', '_', temp_name).strip('_')
    return safe_name

def generate_price_charts():
    """
    Generates and saves historical price charts for each unique product
    found in the DATA_FILE.
    """
    if not os.path.exists(DATA_FILE):
        print(f"Error: Data file not found at {DATA_FILE}. Please run scraper.py first.")
        return

    try:
        df = pd.read_csv(DATA_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # Ensure 'price' column is numeric, coercing errors to NaN
        df["price"] = pd.to_numeric(df["price"], errors='coerce')
        # Drop rows where price is NaN (e.g., if scraping failed for a price)
        df.dropna(subset=['price'], inplace=True)

    except Exception as e:
        print(f"Error loading or processing data from {DATA_FILE}: {e}")
        return

    if df.empty:
        print("No valid price data to plot.")
        return

    os.makedirs(CHARTS_DIR, exist_ok=True)

    # Get unique product names
    product_names = df["product_name"].unique()

    for product_name in product_names:
        product_df = df[df["product_name"] == product_name].sort_values("timestamp")

        if product_df.empty:
            print(f"No data for product: {product_name}. Skipping chart generation.")
            continue

        plt.figure(figsize=(12, 6))
        plt.plot(product_df["timestamp"], product_df["price"], marker='o', linestyle='-')
        plt.title(f"Historical Price for {product_name}")
        plt.xlabel("Date")
        plt.ylabel("Price ($)")
        plt.grid(True)
        plt.tight_layout()

        # Format x-axis dates
        plt.gcf().autofmt_xdate()

        # Generate filename using the consistent helper function
        filename_base = _get_safe_filename_base(product_name)
        chart_path = os.path.join(CHARTS_DIR, f"{filename_base}_price_chart.png")

        try:
            plt.savefig(chart_path)
            print(f"Saved chart for '{product_name}' to {chart_path}")
        except Exception as e:
            print(f"Error saving chart for {product_name}: {e}")
        plt.close() # Close the plot to free memory

if __name__ == "__main__":
    generate_price_charts()
