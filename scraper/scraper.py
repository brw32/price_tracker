import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import os
import json
import re
import random
import pprint # Make sure this is imported

# --- Configuration ---
# IMPORTANT: Replace with actual product URLs and adjust CSS selectors.
# You will need to inspect the HTML of the specific product pages to find
# the correct selectors for title, price, and availability.
PRODUCTS_TO_TRACK = [
    {
        "name": "Dyson Gen5detect Cordless Vacuum Cleaner",
        "url": "https://www.amazon.com/Dyson-Gen5detect-Cordless-Vacuum-Cleaner/dp/B0C2JD5H7D/ref=sr_1_1?crid=301ALWVE6VNJ6&dib=eyJ2IjoiMSJ9.f03GhTUdsx1FcQ6-ZSQrbZPO6QknBRWdSCRsxRngewW8y-x823uzriTKhSVcGekV8qH1LrLppkh6meYkUIGqOiXdA0bfsULpfz5VE1PKPywt-c6TV-S8IlT-Ro8h3TpulLd-id3VSAB0-xv-AfpmyHYkBnWNqHfeAl5UaywXyRMvJcaUqmXrI2Ybe_x_z8kXrzkDS9GIELXqFIRiiSiC-_ovj6b4tiBZUU.MC0AyiZwUwaceqXFHvjbvRZfA6pKWDyPokzsajBGpVY&dib_tag=se&keywords=dyson%2Bcordless%2Bvacuum%2Bgen5&qid=1750100998&sprefix=dyson%2Bcordless%2Bvacuum%2Bge%2Caps%2C101&sr=8-1&th=1",
        "selectors": {
            "title": "#productTitle",
            "price": ".a-price-whole", # Amazon example, might need refinement
            "availability": "#availability span" # Amazon example
        },
        "site": "amazon"
    },
    {
        "name": "Apple - AirPods Pro 2, Wireless Active Noise Cancelling Earbuds with Hearing Aid Feature - White",
        "url": "https://www.bestbuy.com/site/apple-airpods-pro-2-wireless-active-noise-cancelling-earbuds-with-hearing-aid-feature-white/6447382.p?skuId=6447382",
        "selectors": {
           # These selectors are no longer primarily used for BestBuy due to JSON parsing
           "title": "h1.heading-3",
           "price": ".priceView-hero-price.priceView-customer-price span[aria-hidden='true']",
           "availability": ".fulfillment-fulfillment-summary"
        },
        "site": "bestbuy"
    },
     # Add more products here.
     # {"name": "Example GPU", "url": "https://www.newegg.com/...", "selectors": {"title": "", "price": "", "availability": ""}, "site": "newegg"}
]

# Path to store historical data
DATA_FILE = os.path.join("data", "prices.csv")
# Path for BestBuy debug JSON output
BESTBUY_DEBUG_JSON_FILE = "bestbuy_debug_data.json"

# Headers to mimic a browser request and avoid bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "DNT": "1", # Do Not Track request header
    "Upgrade-Insecure-Requests": "1" # Request secure connection
}

# --- Utility Functions ---

def create_data_file_if_not_exists():
    """Creates the CSV data file with headers if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        df = pd.DataFrame(columns=["timestamp", "product_name", "price", "availability", "url"])
        df.to_csv(DATA_FILE, index=False)
        print(f"Created new data file: {DATA_FILE}")

def get_page_content(url, retries=3, backoff_factor=0.5, local_html_path=None):
    """
    Fetches the content of a given URL with retries and backoff.
    Handles basic bot protection by using custom headers.
    If local_html_path is provided, reads from the local file instead.
    """
    if local_html_path:
        # Construct the absolute path to the local HTML file, assuming it's in the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        full_local_path = os.path.join(project_root, local_html_path)
        print(f"DEBUG: Reading content from local file: {full_local_path}")
        try:
            with open(full_local_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"ERROR: Local HTML file not found at {full_local_path}")
            return None
        except Exception as e:
            print(f"ERROR: Could not read local HTML file {full_local_path}: {e}")
            return None

    # Original web fetching logic if local_html_path is not provided
    for i in range(retries):
        try:
            # Introduce a random delay before making the request
            delay = random.uniform(2, 5) # Random delay between 2 and 5 seconds
            print(f"DEBUG: Waiting for {delay:.2f} seconds before fetching {url} (Attempt {i + 1}/{retries})...")
            time.sleep(delay)

            print(f"Fetching: {url} (Attempt {i + 1}/{retries})")
            # Increased timeout to 20 seconds
            response = requests.get(url, headers=HEADERS, timeout=20) # Changed timeout from 15 to 20
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if i < retries - 1:
                sleep_time = backoff_factor * (2 ** i)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"Failed to fetch {url} after {retries} attempts.")
                return None

def parse_amazon(soup, selectors):
    """Parses Amazon product page content."""
    title_element = soup.select_one(selectors["title"])
    price_element = soup.select_one(selectors["price"])
    availability_element = soup.select_one(selectors["availability"])

    title = title_element.get_text(strip=True) if title_element else "N/A"
    price = price_element.get_text(strip=True).replace('$', '').replace(',', '') if price_element else "N/A"
    availability = availability_element.get_text(strip=True) if availability_element else "N/A"

    try:
        price = float(price)
    except ValueError:
        price = None # Or keep as string "N/A"

    return title, price, availability

def parse_bestbuy(soup, selectors):
    """Parses BestBuy product page content by extracting data from embedded JSON."""
    title, price, availability = "N/A", None, "N/A"
    print("DEBUG: Starting BestBuy parsing...")

    # Find the script tag that contains "ApolloSSRDataTransport" and typically has a 'push' method
    script_tag = soup.find('script', string=re.compile(r'window\[Symbol\.for\(\"ApolloSSRDataTransport\"\)\].*push'))
    
    if script_tag:
        print("DEBUG: Found ApolloSSRDataTransport script tag.")
        script_content = script_tag.string
        print(f"DEBUG: Script content starts with (first 200 chars): {script_content[:200]}...")

        # Locate the start of the 'rehydrate' JSON within the push method's arguments
        json_start_indicator = '"rehydrate":'
        start_index = script_content.find(json_start_indicator)

        if start_index != -1:
            # Adjust to start exactly at the opening brace of the JSON object
            json_start_index = start_index + len(json_start_indicator)

            # Manually find the end of the JSON object by counting braces
            brace_count = 0
            json_str_end_index = -1
            # Start search from the first character of the JSON object
            for i in range(json_start_index, len(script_content)):
                char = script_content[i]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                
                # When brace_count is 0, we've found the matching closing brace for the initial '{'
                if brace_count == 0 and char == '}':
                    json_str_end_index = i + 1 # Include the closing brace
                    break
            
            if json_str_end_index != -1:
                json_str = script_content[json_start_index:json_str_end_index]
                
                # --- CRITICAL FIX: Replace 'undefined' with 'null' for valid JSON parsing ---
                json_str = json_str.replace(':undefined', ':null')
                print(f"DEBUG: Replaced ':undefined' with ':null' in JSON string.")
                
                print(f"DEBUG: Extracted JSON string portion (first 500 chars): {json_str[:500]}...")
                try:
                    data = json.loads(json_str)
                    print(f"DEBUG: Successfully decoded BestBuy JSON.")
                    
                    # --- Save the entire 'data' object to a file for detailed debugging ---
                    try:
                        with open(BESTBUY_DEBUG_JSON_FILE, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4) # Use json.dump for cleaner JSON output
                        print(f"DEBUG: Full decoded 'data' object saved to {BESTBUY_DEBUG_JSON_FILE}")
                    except Exception as file_e:
                        print(f"ERROR: Could not save debug JSON to file: {file_e}")
                    
                    # --- IMPORTANT: Print the entire 'data' object for deep debugging ---
                    print("DEBUG: --- Full decoded 'data' object content (for analysis) ---")
                    pprint.pprint(data)
                    print("DEBUG: --- End decoded 'data' object content ---")

                    product_data_node = None
                    # Search for 'productBySkuId' within the data that contains the relevant price and availability info
                    # We are looking for a node that has 'buyingOptions' and 'fulfillmentOptions'
                    for top_level_key, top_level_value in data.items():
                        print(f"DEBUG: Evaluating top-level key: {top_level_key}")
                        if isinstance(top_level_value, dict) and 'data' in top_level_value and top_level_value['data'] is not None: # ADDED check for top_level_value['data']
                            if 'productBySkuId' in top_level_value['data'] and \
                               isinstance(top_level_value['data']['productBySkuId'], dict):
                                
                                candidate_node = top_level_value['data']['productBySkuId']
                                print(f"DEBUG: Found candidate 'productBySkuId' node under {top_level_key}")
                                
                                # Check for the presence of both 'buyingOptions' and 'fulfillmentOptions'
                                if 'buyingOptions' in candidate_node and 'fulfillmentOptions' in candidate_node:
                                    product_data_node = candidate_node
                                    print(f"DEBUG: Selected primary 'productBySkuId' node with buyingOptions and fulfillmentOptions under: {top_level_key}")
                                    print("DEBUG: --- Selected product_data_node content (for analysis) ---")
                                    pprint.pprint(product_data_node)
                                    print("DEBUG: --- End selected product_data_node content ---")
                                    break # Found the correct comprehensive node, stop searching
                                else:
                                    print(f"DEBUG: Candidate 'productBySkuId' node under {top_level_key} lacks 'buyingOptions' or 'fulfillmentOptions'. Skipping.")
                            else:
                                print(f"DEBUG: 'productBySkuId' not found or not a dictionary under 'data' for key {top_level_key}.")
                        else:
                            print(f"DEBUG: Top-level key {top_level_key} does not contain 'data' or is not a dictionary or 'data' is None.")

                    if product_data_node:
                        print("DEBUG: Final 'product_data_node' selected for parsing price/availability.")
                        # Extract Title - This path appears correct
                        name_node = product_data_node.get('name')
                        if name_node and isinstance(name_node, dict) and 'short' in name_node:
                            title = name_node['short']
                            print(f"DEBUG: Extracted title: {title}")
                        else:
                            print("DEBUG: Title not found or not expected type in JSON path 'name.short' in final node.")
                        
                        # Extract Price from 'buyingOptions' - Adjusted path based on debug
                        price = None
                        buying_options = product_data_node.get('buyingOptions')
                        if buying_options and isinstance(buying_options, list):
                            for option in buying_options:
                                if isinstance(option, dict) and option.get('type') == 'New':
                                    product_detail = option.get('product')
                                    if product_detail and isinstance(product_detail, dict):
                                        price_info = product_detail.get('price')
                                        if price_info and isinstance(price_info, dict) and 'customerPrice' in price_info:
                                            price = price_info['customerPrice']
                                            try:
                                                price = float(price)
                                                print(f"DEBUG: Extracted price from buyingOptions: {price}")
                                            except ValueError:
                                                price = None
                                                print(f"DEBUG: Could not convert extracted price '{price_info['customerPrice']}' to float from buyingOptions.")
                                            break # Found new price, break the loop
                                        else:
                                            print("DEBUG: 'customerPrice' not found in price_info for 'New' buying option.")
                                    else:
                                        print("DEBUG: 'product' not found or not a dict in 'New' buying option.")
                                else:
                                    print(f"DEBUG: Skipping buying option type: {option.get('type')}")
                            if price is None:
                                print("DEBUG: Price for 'New' condition not found or not parsable in 'buyingOptions'.")
                        else:
                            print("DEBUG: 'buyingOptions' not found or not a list in product_data_node.")
                                    
                        # Extract Availability from 'fulfillmentOptions' - Adjusted logic
                        availability_parts = []
                        fulfillment_options = product_data_node.get('fulfillmentOptions')
                        if fulfillment_options and isinstance(fulfillment_options, dict):
                            ispu_details = fulfillment_options.get('ispuDetails')
                            if ispu_details and isinstance(ispu_details, list) and len(ispu_details) > 0:
                                # Check if any of the ISPU details indicate availability
                                for detail in ispu_details:
                                    if isinstance(detail, dict) and detail.get('ispuAvailability'):
                                        for avail in detail['ispuAvailability']:
                                            if isinstance(avail, dict) and avail.get('instoreInventoryAvailable') == True:
                                                availability_parts.append("In Stock (Pickup)")
                                                print("DEBUG: Found In Stock (Pickup) via ispuDetails.")
                                                break # Found, move to next detail type
                                        if "In Stock (Pickup)" in availability_parts: break # Found for pickup, no need to loop further
                            
                            shipping_details = fulfillment_options.get('shippingDetails')
                            if shipping_details and isinstance(shipping_details, list) and len(shipping_details) > 0:
                                # Check if any of the shipping details indicate availability
                                for detail in shipping_details:
                                    if isinstance(detail, dict) and detail.get('shippingAvailability'):
                                        for avail in detail['shippingAvailability']:
                                            if isinstance(avail, dict) and avail.get('shippingEligible') == True:
                                                availability_parts.append("Available for Shipping")
                                                print("DEBUG: Found Available for Shipping via shippingDetails.")
                                                break # Found, move to next detail type
                                        if "Available for Shipping" in availability_parts: break # Found for shipping, no need to loop further

                            if availability_parts:
                                availability = " and ".join(availability_parts)
                            else:
                                availability = "Out of Stock or Check Store/Shipping"
                                print("DEBUG: No specific availability found in fulfillmentOptions, defaulting to 'Out of Stock or Check Store/Shipping'.")
                        else:
                            availability = "Out of Stock or Check Store/Shipping (fulfillmentOptions not found or not a dict)"
                            print("DEBUG: 'fulfillmentOptions' not found or not a dictionary in product_data_node.")
                        
                        print(f"DEBUG: Final Availability string after parsing: {availability}")


                    else: # product_data_node was not found or was not a dict
                        print("DEBUG: Comprehensive 'productBySkuId' node not found within BestBuy JSON data after decoding, or did not contain 'buyingOptions' and 'fulfillmentOptions'.")
                except json.JSONDecodeError as e:
                    print(f"ERROR: Could not decode JSON from BestBuy script tag: {e}")
                    print(f"DEBUG: Raw JSON string that caused error (first 1000 chars): {json_str[:1000]}...") # Increased raw string print
                except TypeError as e: # Catch TypeError specifically for more granular debugging
                    print(f"ERROR: TypeError during BestBuy JSON parsing: {e}")
                    import traceback
                    traceback.print_exc() # Print full traceback to see exact line of NoneType error
                except Exception as e:
                    print(f"ERROR: An unexpected general error occurred during BestBuy JSON parsing: {e}")
            else:
                print("DEBUG: Could not find matching closing brace for 'rehydrate' JSON object.")
        else:
            print("DEBUG: 'rehydrate' JSON start indicator not found in script content.")
    else:
        print("DEBUG: ApolloSSRDataTransport script tag not found for BestBuy.")

    # Fallback to direct CSS selectors for title if JSON extraction fails
    if title == "N/A":
        title_element = soup.select_one(selectors["title"])
        if title_element:
            title = title_element.get_text(strip=True)
            print(f"DEBUG: Fallback title extracted: {title}")
        else:
            print("DEBUG: Fallback title selector also failed to find title.")
    
    print(f"DEBUG: parse_bestbuy returning -> Title: {title}, Price: {price}, Availability: {availability}")
    return title, price, availability


def scrape_product(product_info):
    """
    Scrapes product details from the given URL.
    """
    url = product_info["url"]
    selectors = product_info["selectors"]
    site = product_info["site"]

    # For Best Buy, use the uploaded local HTML file for testing
    if site == "bestbuy" and product_info["name"] == "Apple - AirPods Pro 2, Wireless Active Noise Cancelling Earbuds with Hearing Aid Feature - White":
        # Ensure 'Apple AirPods Pro 2, Wireless Active Noise Cancelling Earbuds with Hearing Aid Feature White MTJV3LL_A_MTJV3AM_A - Best Buy.html'
        # is placed in the project's root directory (e.g., C:\Users\brian\price_tracker\)
        html_content = get_page_content(url, local_html_path='Apple AirPods Pro 2, Wireless Active Noise Cancelling Earbuds with Hearing Aid Feature White MTJV3LL_A_MTJV3AM_A - Best Buy.html')
    else:
        html_content = get_page_content(url)
    
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, "html.parser")

    title, price, availability = "N/A", None, "N/A"

    if site == "amazon":
        title, price, availability = parse_amazon(soup, selectors)
    elif site == "bestbuy":
        title, price, availability = parse_bestbuy(soup, selectors)
    # elif site == "newegg": # Commented out Newegg parsing
    #    title, price, availability = parse_newegg(soup, selectors)
    else:
        print(f"Unsupported site: {site}")
        return None

    return {
        "timestamp": datetime.now().isoformat(),
        "product_name": product_info["name"],
        "price": price,
        "availability": availability,
        "url": url,
    }

def main():
    """Main function to run the scraping process."""
    create_data_file_if_not_exists()
    all_scraped_data = []

    for product in PRODUCTS_TO_TRACK:
        print(f"\nScraping {product['name']} from {product['url']}...")
        data = scrape_product(product)
        if data:
            all_scraped_data.append(data)
            print(f"Scraped: {data}")
        else:
            print(f"Could not scrape data for {product['name']}.")
        
        # Add a delay after each product scrape to be less aggressive
        # You can adjust this value (e.g., 2 for 2 seconds, 5 for 5 seconds)
        time.sleep(3) # Wait for 3 seconds after each product scrape

    if all_scraped_data:
        try:
            # Load existing data
            existing_df = pd.read_csv(DATA_FILE)
            # Create a DataFrame from new data
            new_df = pd.DataFrame(all_scraped_data)
            # Concatenate and save
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_csv(DATA_FILE, index=False)
            print(f"\nSuccessfully saved {len(all_scraped_data)} new entries to {DATA_FILE}")
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
    else:
        print("\nNo new data was scraped to save.")

if __name__ == "__main__":
    main()
