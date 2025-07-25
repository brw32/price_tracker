﻿# E-commerce Price Tracker

A Python-based tool to monitor product prices from e-commerce websites (e.g., Amazon, Newegg, BestBuy), and generate price trend charts using Matplotlib. Includes an optional Flask web app to display live prices and charts.

## Features
- Scrapes product title, price, and availability
- Generates price trend charts with Matplotlib
- Exports data to CSV and charts to PNG
- Optional Flask app for live price and graph display
- Handles bot protection with headers and retries

## Requirements
- Python 3.8+
- Libraries: `requests`, `beautifulsoup4`, `pandas`, `matplotlib`, `flask`, `retry`

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/price_tracker.git
   cd price_tracker
