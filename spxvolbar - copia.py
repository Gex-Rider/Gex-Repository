import time
import os
import logging
import pandas as pd
import plotly.express as px
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
        df.columns = ["Strike", "Volume"]
        
        # Convert and clean data
        df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        df.dropna(inplace=True)
        
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
        
        # Find strikes with max positive and max negative volume
        max_positive_volume_row = df_filtered[df_filtered["Volume"] > 0].loc[df_filtered["Volume"].idxmax()] if any(df_filtered["Volume"] > 0) else None
        max_negative_volume_row = df_filtered[df_filtered["Volume"] < 0].loc[df_filtered["Volume"].idxmin()] if any(df_filtered["Volume"] < 0) else None
        
        # Create visualization with binary color scale (green/red)
        fig = px.bar(
            df_filtered,
            x="Volume",
            y="Strike",
            orientation="h",
            title=f"SPX Volume by Strike - Spot: {spot_price:.2f} ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            color=df_filtered["Volume"] > 0,
            color_discrete_map={True: "green", False: "red"}
        )
        
        # Add marker for spot price
        fig.add_hline(
            y=spot_price, 
            line_dash="dash", 
            line_color="yellow", 
            annotation_text="Spot Price",
            annotation_position="right"
        )
        
        # Add marker for max positive volume strike if exists
        if max_positive_volume_row is not None:
            fig.add_hline(
                y=max_positive_volume_row["Strike"],
                line_dash="dot",
                line_color="lightgreen",
                annotation_text=f"Max+ ({max_positive_volume_row['Strike']:.2f})",
                annotation_position="left"
            )
        
        # Add marker for max negative volume strike if exists
        if max_negative_volume_row is not None:
            fig.add_hline(
                y=max_negative_volume_row["Strike"],
                line_dash="dot",
                line_color="pink",
                annotation_text=f"Max- ({max_negative_volume_row['Strike']:.2f})",
                annotation_position="left"
            )
        
        # Format chart
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            title_font=dict(size=20, color="white"),
            xaxis=dict(title="Volume", color="white"),
            yaxis=dict(title="Strike", color="white"),
            showlegend=False,
            margin=dict(l=20, r=20, t=60, b=20),
            height=600,
            width=900
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