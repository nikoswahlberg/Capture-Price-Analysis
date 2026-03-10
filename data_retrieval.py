"""
Wind Energy Capture Price & Cannibalization Analysis
Target: Finland (FI) Bidding Zone
"""

import os
import logging
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

# --- SUPPRESS MATPLOTLIB FONT WARNINGS ---
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

# --- CONFIGURATION ---
COUNTRY_CODE = 'FI'
START_DATE = '2024-01-01'
END_DATE = '2025-01-01'
TIMEZONE = 'Europe/Helsinki'
CACHE_FILE = f'raw_entsoe_cache_{COUNTRY_CODE}_{START_DATE[:4]}.csv'
PRIMARY_COLOR = '#00653D'  # Deep corporate green

def get_api_client() -> EntsoePandasClient:
    """Loads the ENTSO-E API token from the .env file and returns a client."""
    load_dotenv()
    api_token = os.getenv('ENTSOE_TOKEN')
    
    if not api_token or api_token == 'paste_your_token_here_later':
        raise ValueError("Missing ENTSO-E API token. Please add it to your .env file.")
    
    return EntsoePandasClient(api_key=api_token)

def fetch_or_load_data(client: EntsoePandasClient) -> pd.DataFrame:
    """Loads data from a local CSV cache if available, otherwise fetches from ENTSO-E API."""
    start = pd.Timestamp(START_DATE, tz=TIMEZONE)
    end = pd.Timestamp(END_DATE, tz=TIMEZONE)

    if os.path.exists(CACHE_FILE):
        print(f"[*] Found local cache '{CACHE_FILE}'. Loading data from disk...")
        df = pd.read_csv(CACHE_FILE, index_col=0)
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(TIMEZONE)
        return df

    print(f"[*] Fetching fresh data for {COUNTRY_CODE} from {start.date()} to {end.date()} via API...")
    
    # 1. Fetch Day-Ahead Prices
    df_prices = client.query_day_ahead_prices(COUNTRY_CODE, start=start, end=end)
    df_prices = pd.DataFrame(df_prices, columns=['Spot_Price'])

    # 2. Fetch Wind Generation
    generation = client.query_generation(COUNTRY_CODE, start=start, end=end)
    if isinstance(generation.columns, pd.MultiIndex):
        df_wind = generation.xs('Wind Onshore', level=1, axis=1)
    else:
        df_wind = pd.DataFrame(generation['Wind Onshore'])
    df_wind.columns = ['Wind_Production']
    
    # 3. Resample and Merge
    df_prices = df_prices.resample('h').mean()
    df_wind = df_wind.resample('h').mean()
    df = df_prices.join(df_wind).dropna()

    # Save to cache
    df.to_csv(CACHE_FILE)
    print(f"[*] Data successfully downloaded and cached to '{CACHE_FILE}'.")
    
    return df

def calculate_metrics(df: pd.DataFrame) -> tuple:
    """Calculates Hourly Revenue, and aggregates Monthly and Daily Capture Prices."""
    df['Hourly_Revenue'] = df['Spot_Price'] * df['Wind_Production']

    def aggregate_data(data: pd.DataFrame, freq: str, date_format: str) -> pd.DataFrame:
        agg_df = data.resample(freq).agg({
            'Spot_Price': 'mean', 
            'Wind_Production': 'sum', 
            'Hourly_Revenue': 'sum'
        })
        agg_df['Capture_Price'] = agg_df['Hourly_Revenue'] / agg_df['Wind_Production']
        agg_df['Capture_Rate_%'] = (agg_df['Capture_Price'] / agg_df['Spot_Price']) * 100
        agg_df.index = agg_df.index.strftime(date_format)
        return agg_df

    monthly = aggregate_data(df, 'ME', '%Y-%m')
    daily = aggregate_data(df, 'D', '%Y-%m-%d')

    return df, monthly, daily

def export_to_excel(df: pd.DataFrame, monthly: pd.DataFrame, daily: pd.DataFrame, filename: str = 'wind_capture_analysis.xlsx'):
    """Exports the DataFrames to a multi-sheet Excel workbook."""
    df_export = df.copy()
    df_export.index = df_export.index.tz_localize(None) 

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        monthly.to_excel(writer, sheet_name='Monthly Summary')
        daily.to_excel(writer, sheet_name='Daily Summary')
        df_export.to_excel(writer, sheet_name='Hourly Raw Data') 
    
    print(f"[*] Success! Data exported to {filename}.")

def print_strategic_insights(df: pd.DataFrame):
    """Calculates and prints key portfolio insights for the dashboard."""
    print("\n" + "="*50)
    print("🎯 STRATEGIC MARKET INSIGHTS 🎯")
    print("="*50)

    negative_hours = (df['Spot_Price'] < 0).sum()
    total_hours = len(df)
    negative_volume = df[df['Spot_Price'] < 0]['Wind_Production'].sum()
    total_volume = df['Wind_Production'].sum()

    print(f"- Total Hours with Negative Prices: {negative_hours} hours ({(negative_hours/total_hours)*100:.1f}% of the year)")
    print(f"- Wind Volume Sold at Negative Prices: {(negative_volume/total_volume)*100:.1f}% of total annual generation")

    daily_spreads = df['Spot_Price'].resample('D').agg(lambda x: x.max() - x.min())
    max_spread_day = daily_spreads.idxmax()
    max_spread_value = daily_spreads.max()

    print(f"- Highest Intra-day Price Spread: {max_spread_value:.2f} €/MWh (Occurred on {max_spread_day.strftime('%Y-%m-%d')})")
    print("="*50 + "\n")

def generate_visuals(df: pd.DataFrame):
    """Generates and saves the analytical charts."""
    print("[*] Generating visual charts...")
    
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'sans-serif']
    sns.set_theme(style="whitegrid", rc={"font.family": "sans-serif"})

    # --- Chart 1: Cannibalization Curve ---
    plt.figure(figsize=(12, 7))
    sns.regplot(
        data=df, x='Wind_Production', y='Spot_Price',
        scatter_kws={'alpha': 0.15, 's': 15, 'color': PRIMARY_COLOR}, 
        line_kws={'color': '#d9534f', 'linewidth': 3}
    )
    plt.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
    plt.title(f'The Cannibalization Curve: {COUNTRY_CODE} Wind Production vs. Spot Price ({START_DATE[:4]})', 
              fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('Hourly Wind Production (MW)', fontsize=12, fontweight='bold')
    plt.ylabel('Hourly Spot Price (€/MWh)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig('cannibalization_curve.png', dpi=300)

    # --- Chart 2: Hourly Price Heatmap ---
    heatmap_df = df.copy()
    heatmap_df['Month'] = heatmap_df.index.strftime('%b') 
    heatmap_df['Hour'] = heatmap_df.index.hour
    pivot_data = heatmap_df.pivot_table(values='Spot_Price', index='Hour', columns='Month', aggfunc='mean')
    
    months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pivot_data = pivot_data[[m for m in months_order if m in pivot_data.columns]]

    plt.figure(figsize=(14, 8))
    sns.heatmap(
        pivot_data, cmap='RdYlGn_r', annot=True, fmt=".0f", linewidths=.5, 
        cbar_kws={'label': 'Average Spot Price (€/MWh)'},
        annot_kws={"size": 10} 
    )
    plt.title('Average Hourly Spot Price by Month (€/MWh)\nIdentifying Battery Storage (BESS) Opportunities', 
              fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('Month', fontsize=12, fontweight='bold')
    plt.ylabel('Hour of the Day (00:00 - 23:00)', fontsize=12, fontweight='bold')
    plt.yticks(rotation=0) 
    plt.tight_layout()
    plt.savefig('hourly_price_heatmap.png', dpi=300)
    
    print("[*] Charts successfully saved!")

def main():
    """Main execution workflow."""
    try:
        client = get_api_client()
        df = fetch_or_load_data(client)
        df, monthly, daily = calculate_metrics(df)
        export_to_excel(df, monthly, daily)
        print_strategic_insights(df)
        generate_visuals(df)
    except Exception as e:
        print(f"\n[!] An error occurred: {e}")

if __name__ == "__main__":
    main()