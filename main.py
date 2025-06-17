import json
import time
import schedule
import logging
from src.scraper import Scraper
from src.database import Database
from src.plotter import Plotter

logging.basicConfig(
    level=logging.INFO,
    filename='price_tracker.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    print("Loading config.json...")
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Config content: {content}")
            if not content.strip():
                raise ValueError("config.json is empty")
            return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to load config.json: {e}")
        print(f"Error loading config.json: {e}")
        raise

def scrape_and_update():
    print("Starting scrape_and_update...")
    config = load_config()
    scraper = Scraper()
    db = Database()
    plotter = Plotter()

    for product in config['products']:
        print(f"Scraping {product['name']} ({product['url']})...")
        try:
            data = scraper.scrape_product(product)
            print(f"Scraped data: {data}")
            db.insert_data(data)
            print(f"Inserted data for {product['name']} into database")
            df = db.get_data(product['url'])
            print(f"DataFrame for {product['name']}: {df}")
            if not df.empty:
                db.export_to_csv(product['url'])
                print(f"Exported CSV for {product['name']}")
                chart_path = f'data/exports/price_chart_{product["name"].replace(" ", "_")}.png'
                plotter.plot_price_history(df, product['name'], chart_path)
                print(f"Generated chart for {product['name']} at {chart_path}")
            else:
                print(f"No data to plot for {product['name']}")
            logging.info(f"Scraped {product['name']} successfully")
        except Exception as e:
            logging.error(f"Error processing {product['name']}: {e}")
            print(f"Error processing {product['name']}: {e}")

def main():
    print("Starting main function...")
    config = load_config()
    scrape_interval_hours = config.get('scrape_interval_hours', 24)

    schedule.every(scrape_interval_hours).hours.do(scrape_and_update)
    print(f"Scheduled scraping every {scrape_interval_hours} hours")

    scrape_and_update()

    logging.info(f"Starting price tracker with {scrape_interval_hours}-hour interval")
    print(f"Entering scheduler loop. Press Ctrl+C to stop.")
    while True:
        try:
            schedule.run_pending()
            print("Checked for pending tasks...")
            time.sleep(60)
        except KeyboardInterrupt:
            logging.info("Price tracker stopped by user")
            print("Stopped by user")
            break
        except Exception as e:
            logging.error(f"Error in scheduler: {e}")
            print(f"Error in scheduler: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()