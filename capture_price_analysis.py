import os
import pandas as pd
import matplotlib.pyplot as plt
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
API_TOKEN = os.getenv('ENTSOE_TOKEN')

# Safety check for the token
if not API_TOKEN or API_TOKEN == 'paste_your_token_here_later':
    print("Waiting for ENTSO-E token. Please add it to your .env file once received!")
    exit()

client = EntsoePandasClient(api_key=API_TOKEN)

# 2. Define Parameters
country_code = 'FI'  # Finland Bidding Zone
# Let's analyze the full year of 2024 for a complete picture
start = pd.Timestamp('2024-01-01', tz='Europe/Helsinki')
end = pd.Timestamp('2025-01-01', tz='Europe/Helsinki')

print(f"Fetching data for {country_code} from {start.date()} to {end.date()}...")

try:
    # 3. Fetch Data
    # Day-Ahead Prices (EUR/MWh)
    df_prices = client.query_day_ahead_prices(country_code, start=start, end=end)
    df_prices = pd.DataFrame(df_prices, columns=['Spot_Price'])

    # Wind Generation (MW)
    generation = client.query_generation(country_code, start=start, end=end)
    
    # ENTSO-E can return complex multi-level data depending on the country. 
    # We isolate 'Wind Onshore' specifically.
    if isinstance(generation.columns, pd.MultiIndex):
        df_wind = generation.xs('Wind Onshore', level=1, axis=1)
    else:
        df_wind = pd.DataFrame(generation['Wind Onshore'])
    df_wind.columns = ['Wind_Production']

except Exception as e:
    print(f"An error occurred while fetching data: {e}")
    print("Check your API token and internet connection.")
    exit()

# 4. Clean and Merge
# Resample to hourly ('h') to ensure indices match perfectly before calculating
df_prices = df_prices.resample('h').mean()
df_wind = df_wind.resample('h').mean()

# Join the dataframes and drop any missing hours
df = df_prices.join(df_wind).dropna()

# 5. The Core Math: Revenue & Capture Price
# Hourly Revenue = Spot Price * Wind Production Volume
df['Hourly_Revenue'] = df['Spot_Price'] * df['Wind_Production']

# Group data by Month End ('ME')
monthly = df.resample('ME').agg({
    'Spot_Price': 'mean',          # Average Base Spot Price
    'Wind_Production': 'sum',      # Total Monthly Volume
    'Hourly_Revenue': 'sum'        # Total Monthly Revenue
})

# Capture Price = Total Revenue / Total Volume
monthly['Capture_Price'] = monthly['Hourly_Revenue'] / monthly['Wind_Production']

# Cannibalization Factor (%) = (Capture Price / Base Price) * 100
monthly['Capture_Rate_%'] = (monthly['Capture_Price'] / monthly['Spot_Price']) * 100

# Format the index to YYYY-MM for a cleaner Excel export
monthly.index = monthly.index.strftime('%Y-%m')

print("\n--- Monthly Summary (2024) ---")
print(monthly[['Spot_Price', 'Capture_Price', 'Capture_Rate_%']].round(2))

# 6. Export to Excel
output_file = 'wind_capture_analysis.xlsx'
monthly.to_excel(output_file, sheet_name='Data')
print(f"\nSuccess! Data exported to {output_file}")