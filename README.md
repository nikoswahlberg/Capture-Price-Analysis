# Finnish Wind Power: Capture Price & Cannibalization Analysis

## Overview
This project was developed to analyze the commercial performance of onshore wind power in the Finnish bidding zone (FI). As wind capacity in Finland has grown rapidly, the correlation between high wind generation and low spot prices has intensified the **cannibalization effect**. 

This Python-based data pipeline automatically fetches, cleans, and merges generation and price data to calculate the true **Capture Price** (volume-weighted average price) of Finnish wind, compared to the standard Baseload Spot Price (time-weighted average price).

## Why This Matters (The Business Case for Storage)
A standard baseload spot price is no longer an accurate benchmark for wind portfolio revenues. Understanding the capture rate (Capture Price / Spot Price) is critical for:
* Accurate financial modeling of wind power portfolios.
* Evaluating the profitability of **energy storage solutions** (e.g., batteries) to shift generation from negative/low-price hours to peak hours.
* Hedging strategies and PPA (Power Purchase Agreement) valuations.

## Technical Architecture
* **Data Source:** ENTSO-E Transparency Platform REST API
* **Data Pipeline:** Python (`entsoe-py`, `pandas`)
* **Transformations:** Resampling mixed-interval data (15-min and 60-min) to hourly standard, handling missing hours, and calculating volume-weighted revenues.
* **Output:** Cleaned `.xlsx` dataset ready for PowerBI/Excel dashboarding and portfolio analytics.

## How to Run
1. Clone this repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Request a free API token from `transparency@entsoe.eu` and place it in a `.env` file as `ENTSOE_TOKEN=your_token`.
4. Run `python capture_price_analysis.py`.