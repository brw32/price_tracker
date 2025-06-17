from flask import Flask, render_template, send_from_directory
import pandas as pd
import os
import glob # For finding chart images
import re # Import regex module

app = Flask(__name__)

# Get the base directory of the project (one level up from 'app')
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_FILE = os.path.join(PROJECT_ROOT, "data", "prices.csv")
CHARTS_DIR_ABSOLUTE = os.path.join(PROJECT_ROOT, "visuals")

print(f"DEBUG: PROJECT_ROOT is: {PROJECT_ROOT}")
print(f"DEBUG: DATA_FILE path is: {DATA_FILE}")
print(f"DEBUG: CHARTS_DIR_ABSOLUTE path is: {CHARTS_DIR_ABSOLUTE}")

def _get_safe_filename_base(product_name):
    """
    Generates a filesystem-safe and consistent base name for a product chart file.
    It removes non-alphanumeric/non-space characters, then replaces spaces with underscores.
    This function should be identical to the one in plotter.py for consistency.
    """
    # Replace any character that is NOT a word character (alphanumeric + underscore) or a space
    # with an empty string. This removes characters like commas, hyphens etc.
    temp_name = re.sub(r'[^\w\s]', '', product_name)
    # Replace one or more whitespace characters with a single underscore, then strip leading/trailing underscores
    safe_name = re.sub(r'\s+', '_', temp_name).strip('_')
    return safe_name

@app.route('/')
def index():
    """
    Displays the latest product prices and historical charts.
    """
    product_data = []
    latest_prices = {}

    print(f"DEBUG: Checking if DATA_FILE exists at: {DATA_FILE}")
    if os.path.exists(DATA_FILE):
        print(f"DEBUG: DATA_FILE found.")
        try:
            df = pd.read_csv(DATA_FILE)
            print(f"DEBUG: DataFrame loaded. Initial rows:\n{df.head()}")

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            print(f"DEBUG: Timestamp column converted.")

            # Ensure 'price' column is numeric
            df["price"] = pd.to_numeric(df["price"], errors='coerce')
            print(f"DEBUG: Price column converted to numeric. Rows with NaN prices (before dropna):\n{df[df['price'].isna()].head()}")
            
            df.dropna(subset=['price'], inplace=True) # Drop rows where price is NaN after conversion
            print(f"DEBUG: After dropna, DataFrame rows remaining: {len(df)}")

            if not df.empty:
                print(f"DEBUG: DataFrame is not empty. Processing latest entries.")
                # Get the latest entry for each product
                # Sort by timestamp descending and keep the first unique product entry
                latest_entries = df.sort_values(by="timestamp", ascending=False).drop_duplicates(subset=["product_name"])
                print(f"DEBUG: Latest entries found:\n{latest_entries}")

                for index, row in latest_entries.iterrows():
                    latest_prices[row["product_name"]] = {
                        "price": f"${row['price']:.2f}" if pd.notna(row['price']) else "N/A",
                        "availability": row["availability"],
                        "url": row["url"],
                        "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    }
                print(f"DEBUG: latest_prices dictionary:\n{latest_prices}")
            else:
                print(f"DEBUG: Warning: {DATA_FILE} is empty after dropping non-numeric prices. No product data to display.")

        except Exception as e:
            print(f"ERROR: Error loading or processing data from {DATA_FILE}: {e}")
            # Continue with empty data if there's an error
    else:
        print(f"ERROR: Data file not found at {DATA_FILE}. No price data available.")


    # Combine data for rendering - REVISED LOGIC
    for product_name_key, details in latest_prices.items():
        # Generate the expected chart filename base for this product using the consistent helper function
        expected_filename_base = _get_safe_filename_base(product_name_key)
        chart_filename = f"{expected_filename_base}_price_chart.png"
        chart_url = f"/visuals/{chart_filename}"

        # Check if the generated chart file actually exists on disk
        full_chart_path = os.path.join(CHARTS_DIR_ABSOLUTE, chart_filename)
        if os.path.exists(full_chart_path):
            product_data.append({
                "name": product_name_key,
                "latest_price": details["price"],
                "availability": details["availability"],
                "url": details["url"],
                "timestamp": details["timestamp"],
                "chart_image": chart_url # Use the dynamically generated URL
            })
        else:
            print(f"DEBUG: Chart file not found for '{product_name_key}' at expected path: {full_chart_path}")
            product_data.append({
                "name": product_name_key,
                "latest_price": details["price"],
                "availability": details["availability"],
                "url": details["url"],
                "timestamp": details["timestamp"],
                "chart_image": "" # No chart image if file doesn't exist
            })

    # Sort product_data by product name for consistent display
    product_data.sort(key=lambda x: x['name'])

    print(f"DEBUG: Final product_data for rendering: {product_data}")
    return render_template('index.html', product_data=product_data)

# NEW ROUTE: Explicitly serve static files from the 'visuals' directory
@app.route('/visuals/<path:filename>')
def serve_visuals(filename):
    """
    Serves static files (charts) from the visuals directory.
    """
    print(f"DEBUG: Request for static file: {filename} in directory: {CHARTS_DIR_ABSOLUTE}")
    return send_from_directory(CHARTS_DIR_ABSOLUTE, filename)

if __name__ == '__main__':
    # Removed app.static_folder and app.static_url_path as they are now superseded
    # by the explicit @app.route('/visuals/<path:filename>') for chart serving.
    app.run(debug=True)
