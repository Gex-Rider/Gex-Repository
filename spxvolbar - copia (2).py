import time
import os
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spx_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Ensure the output directory exists
os.makedirs("output", exist_ok=True)

def process_data():
    """Process SPX volume data and generate visualization"""
    try:
        # Read data file
        logger.info("Reading data from spx_vol.csv")
        df_raw = pd.read_csv("spx_vol.csv", header=None)
        
        # Extract spot price and data
        spot_price = float(df_raw.iloc[0, 0])
        df = df_raw.iloc[1:].copy()
        
        # Set column names for the new format with multiple volume columns
        df.columns = ["Strike", "Vol0DTE", "Vol1DTE", "OtroVol"]
        
        # Convert and clean data
        df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
        df["Vol0DTE"] = pd.to_numeric(df["Vol0DTE"], errors="coerce")
        df["Vol1DTE"] = pd.to_numeric(df["Vol1DTE"], errors="coerce")
        df["OtroVol"] = pd.to_numeric(df["OtroVol"], errors="coerce")
        df.dropna(inplace=True)
        
        # Calculate total volume for each strike
        df["TotalVol"] = df["Vol0DTE"] + df["Vol1DTE"] + df["OtroVol"]
        
        # Calculate filter range (±1.5% from spot)
        min_strike = spot_price * 0.985
        max_strike = spot_price * 1.015
        logger.info(f"Filtering strikes between {min_strike:.2f} and {max_strike:.2f}")
        
        # Filter data
        df_filtered = df[(df["Strike"] >= min_strike) & (df["Strike"] <= max_strike)]
        logger.info(f"Filtered: {len(df_filtered)} rows")
        
        # Skip if no data available
        if len(df_filtered) == 0:
            logger.warning("No data available after filtering. Skipping visualization.")
            return None
        
        # Generate timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/spx_volume_{timestamp}.png"
        
        # Find strikes with most significant volume concentration
        max_positive_strike = df_filtered[df_filtered["TotalVol"] > 0].groupby("Strike")["TotalVol"].sum().idxmax() if any(df_filtered["TotalVol"] > 0) else None
        max_negative_strike = df_filtered[df_filtered["TotalVol"] < 0].groupby("Strike")["TotalVol"].sum().idxmin() if any(df_filtered["TotalVol"] < 0) else None
        
        # Create figure
        fig = go.Figure()
        
        # Colors for different volume types (from lightest to darkest)
        positive_colors = ["#006400", "#32CD32", "#90EE90"]  # Light green, Lime green, Dark green
        negative_colors = ["#8B0000", "#FF0000", "#FFC0CB"]  # Pink, Red, Dark red
        
        # Add traces for positive volumes
        for i, col, color in zip(range(3), ["Vol0DTE", "Vol1DTE", "OtroVol"], positive_colors):
            positive_data = df_filtered[df_filtered[col] > 0]
            if not positive_data.empty:
                fig.add_trace(go.Bar(
                    x=positive_data[col],
                    y=positive_data["Strike"],
                    orientation='h',
                    name=f"+{col}",
                    marker_color=color,
                    legendgroup="positive",
                    showlegend=False
                ))
                
        # Add traces for negative volumes
        for i, col, color in zip(range(3), ["Vol0DTE", "Vol1DTE", "OtroVol"], negative_colors):
            negative_data = df_filtered[df_filtered[col] < 0]
            if not negative_data.empty:
                fig.add_trace(go.Bar(
                    x=negative_data[col],
                    y=negative_data["Strike"],
                    orientation='h',
                    name=f"-{col}",
                    marker_color=color,
                    legendgroup="negative",
                    showlegend=False
                ))
        
        # Add marker for spot price
        fig.add_hline(
            y=spot_price, 
            line_dash="dash", 
            line_color="yellow", 
            annotation_text="Spot",
            annotation_position="right"
        )
        
        # Add marker for max positive volume concentration
        if max_positive_strike is not None:
            max_pos_vol = df_filtered[df_filtered["Strike"] == max_positive_strike]["TotalVol"].values[0]
            fig.add_hline(
                y=max_positive_strike,
                line_dash="dot",
                line_color="lightgreen",
                annotation_text=f"Max+ ({max_positive_strike:.2f}, Vol: {max_pos_vol:.0f})",
                annotation_position="right"
            )
        
        # Add marker for max negative volume concentration
        if max_negative_strike is not None:
            max_neg_vol = df_filtered[df_filtered["Strike"] == max_negative_strike]["TotalVol"].values[0]
            fig.add_hline(
                y=max_negative_strike,
                line_dash="dot",
                line_color="pink",
                annotation_text=f"Max- ({max_negative_strike:.2f}, Vol: {max_neg_vol:.0f})",
                annotation_position="right"
            )
        
        # Format chart
        fig.update_layout(
            title=f"SPX Volume by Strike - Spot: {spot_price:.2f} ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            title_font=dict(size=20, color="white"),
            xaxis=dict(title="Volume", color="white"),
            yaxis=dict(title="Strike", color="white"),
            barmode='stack',  # Stack the bars for same strike
            legend_title="Volume Type",
            legend_font=dict(color="white"),
            legend_title_font=dict(color="white"),
            margin=dict(l=20, r=20, t=60, b=20),
            height=700,
            width=1000
        )
        
        # Save image
        logger.info(f"Saving chart to {output_path}")
        fig.write_image(output_path)
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}", exc_info=True)
        return None

def post_to_discord(image_path, webhook_url):
    """Post image to Discord webhook"""
    try:
        if not image_path:
            logger.error("No image file to post to Discord")
            return False
            
        logger.info(f"Posting to Discord: {image_path}")
        
        with open(image_path, "rb") as file:
            now = datetime.now()
            market_status = "Market Hours" if (
                now.weekday() < 5 and 
                9 <= now.hour < 16 or 
                (now.hour == 9 and now.minute >= 30) or 
                (now.hour == 16 and now.minute == 0)
            ) else "After Hours"
            
            # Create payload with more detailed message
            payload = {
                "content": f"📊 **SPX Volume Distribution** | {now.strftime('%Y-%m-%d %H:%M')} | {market_status}"
            }
            
            files = {"file": (os.path.basename(image_path), file, "image/png")}
            response = requests.post(webhook_url, data=payload, files=files)
        
        if response.status_code == 204:
            logger.info("✅ Image successfully posted to Discord")
            return True
        else:
            logger.error(f"❌ Error posting to Discord: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error posting to Discord: {str(e)}", exc_info=True)
        return False

def main():
    """Main execution function"""
    # Discord webhook URL
    webhook_url = "https://discord.com/api/webhooks/1372226488463659188/iMkVFj6sYi4FjUiDbE6hM_eRh9mJPRUENDPnrqlq3UH-2Qk-ub7c4gYEe-H5lYeq--7m"
    
    # Set Plotly's image export format
    pio.kaleido.scope.default_format = "png"
    
    # Process and visualize data
    image_path = process_data()
    
    # Post to Discord if image was created
    if image_path:
        post_to_discord(image_path, webhook_url)
    else:
        logger.warning("No image generated to post to Discord")

# Main execution loop
if __name__ == "__main__":
    logger.info("=== SPX Volume Monitor Started ===")
    
    try:
        # Run continuously with error handling
        while True:
            try:
                logger.info("--- Starting monitoring cycle ---")
                main()
                logger.info("--- Cycle completed, waiting for next run ---")
            except Exception as e:
                logger.error(f"❌ Error in execution cycle: {str(e)}", exc_info=True)
                
            # Wait for next cycle
            time.sleep(300)  # 5 minutes
    
    except KeyboardInterrupt:
        logger.info("=== SPX Volume Monitor stopped by user ===")