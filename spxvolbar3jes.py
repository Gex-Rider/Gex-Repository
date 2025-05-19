import time
import os
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import plotly.subplots as sp
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
    """Process SPX, ES and SPY volume data and generate visualization"""
    try:
        # Read data file
        logger.info("Reading data from spx_vol.csv")
        df_raw = pd.read_csv("spx_vol.csv", header=None)
        
        # Extract spot prices from the first row
        # The first row should contain SPX, ES, SPY spot prices in that order
        spx_spot = float(df_raw.iloc[0, 0])
        es_spot = float(df_raw.iloc[0, 1])
        spy_spot = float(df_raw.iloc[0, 2])
        
        logger.info(f"Spot prices - SPX: {spx_spot}, ES: {es_spot}, SPY: {spy_spot}")
        
        # Calculate scaling factors between indices
        # These will be used to align the different axes
        es_to_spx_factor = spx_spot / es_spot if es_spot != 0 else 1
        spy_to_spx_factor = spx_spot / spy_spot if spy_spot != 0 else 1
        
        logger.info(f"Scaling factors - ES to SPX: {es_to_spx_factor}, SPY to SPX: {spy_to_spx_factor}")
        
        # Extract volume data starting from the second row
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
        
        # Calculate filter range (SPX spot ±150 points)
        min_strike = spx_spot - 150
        max_strike = spx_spot + 150
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
        output_path = f"output/multi_index_volume_{timestamp}.png"
        
        # Find strikes with most significant volume concentration
        max_positive_strike = df_filtered[df_filtered["TotalVol"] > 0].groupby("Strike")["TotalVol"].sum().idxmax() if any(df_filtered["TotalVol"] > 0) else None
        max_negative_strike = df_filtered[df_filtered["TotalVol"] < 0].groupby("Strike")["TotalVol"].sum().idxmin() if any(df_filtered["TotalVol"] < 0) else None
        
        # Create figure with multiple y-axes
        fig = go.Figure()
        
        # Add invisible traces to enable secondary y-axes
        # For ES axis
        fig.add_trace(go.Scatter(
            x=[0],
            y=[es_spot * es_to_spx_factor],  # Scaled to align with SPX axis
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),  # Invisible marker
            showlegend=False,
            yaxis="y2"
        ))
        
        # For SPY axis
        fig.add_trace(go.Scatter(
            x=[0],
            y=[spy_spot * spy_to_spx_factor],  # Scaled to align with SPX axis
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),  # Invisible marker
            showlegend=False,
            yaxis="y3"
        ))
        
       # Colors for different volume types (from lightest to darkest)
        positive_colors = ["#006400", "#32CD32", "#90EE90"]  # Light green, Lime green, Dark green
        negative_colors = ["#8B0000", "#FF0000", "#FFC0CB"]  # Pink, Red, Dark red
        

        # Add traces for volume data
        volume_columns = ["OtroVol", "Vol1DTE", "Vol0DTE"]  # Order matters for stacking
        volume_display_names = ["+OtroVol", "+Vol1DTE", "+Vol0DTE", "-OtroVol", "-Vol1DTE", "-Vol0DTE"]
        
        # First positive volumes (stacked from bottom to top)
        for i, col in enumerate(volume_columns):
            positive_data = df_filtered[df_filtered[col] > 0]
            if not positive_data.empty:
                fig.add_trace(go.Bar(
                    x=positive_data[col],
                    y=positive_data["Strike"],
                    orientation='h',
                    name=volume_display_names[i],
                    marker_color=positive_colors[i],
                    legendgroup="positive",
                    showlegend=True
                ))
                
        # Then negative volumes (stacked from bottom to top)
        for i, col in enumerate(volume_columns):
            negative_data = df_filtered[df_filtered[col] < 0]
            if not negative_data.empty:
                fig.add_trace(go.Bar(
                    x=negative_data[col],
                    y=negative_data["Strike"],
                    orientation='h',
                    name=volume_display_names[i+3],
                    marker_color=negative_colors[i],
                    legendgroup="negative",
                    showlegend=True
                ))
        
        # Add reference lines for key SPX price levels
        # Find round numbers close to max positive and negative volume concentrations
        key_levels = []
        
        # Add round SPX levels every 50 points within our range
        base_level = int(spx_spot / 50) * 50  # Closest 50-point level
        for i in range(-3, 4):
            level = base_level + (i * 50)
            if min_strike <= level <= max_strike:
                key_levels.append(level)
        
        # Add reference lines for key levels
        for level in key_levels:
            # Only add horizontal line for SPX levels
            line_style = "dot" if level != key_levels[len(key_levels)//2] else "dash"
            line_width = 1 if level != key_levels[len(key_levels)//2] else 1.5
            
            fig.add_hline(
                y=level,
                line_dash=line_style,
                line_width=line_width,
                line_color="rgba(255, 255, 0, 0.3)",
                annotation_text=f"{level}",
                annotation_position="right",
                annotation_font_color="yellow"
            )
            
        # Add marker for spot prices
        # SPX spot (yellow)
        fig.add_hline(
            y=spx_spot, 
            line_dash="dash", 
            line_width=2,
            line_color="yellow", 
            annotation_text=f"SPX: {spx_spot:.2f}",
            annotation_position="right",
            annotation_font_color="yellow"
        )
        
        # ES spot (cyan) - Add only the annotation at the left edge
        fig.add_annotation(
            x=0,
            y=spx_spot,  # We use SPX spot for y position since that's our reference axis
            text=f"ES: {es_spot:.2f}",
            showarrow=False,
            font=dict(color="cyan"),
            xanchor="right",
            yanchor="middle",
            xshift=-40
        )
        
        # SPY spot (magenta) - Add only the annotation at the left edge
        fig.add_annotation(
            x=0,
            y=spx_spot,  # We use SPX spot for y position since that's our reference axis
            text=f"SPY: {spy_spot:.2f}",
            showarrow=False,
            font=dict(color="magenta"),
            xanchor="right",
            yanchor="middle",
            xshift=-100
        )
        
        # Format chart
        fig.update_layout(
            title=f"Multi-Index Volume - SPX: {spx_spot:.2f} | ES: {es_spot:.2f} | SPY: {spy_spot:.2f} ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            title_font=dict(size=20, color="white"),
            xaxis=dict(title="Volume", color="white"),
            
            # Primary y-axis (SPX)
            yaxis=dict(
                title="SPX Strike",
                color="yellow",
                titlefont=dict(color="yellow"),
                tickfont=dict(color="yellow"),
                side="left",
                showgrid=True,
                gridcolor="rgba(255, 255, 0, 0.1)",
                dtick=50,  # Set tick interval to 50 points
                # Only show SPX values on the grid lines
                tickvals=[i for i in range(int(min_strike), int(max_strike)+50, 50)],
                ticktext=[f"{i}" for i in range(int(min_strike), int(max_strike)+50, 50)]
            ),
            
            # Secondary y-axis (ES)
            yaxis2=dict(
                title="ES Strike",
                color="cyan",
                titlefont=dict(color="cyan"),
                tickfont=dict(color="cyan"),
                side="right",
                position=0.95,  # Position to the right of primary y-axis but within limits [0,1]
                overlaying="y",
                showgrid=True,
                dtick=50 / es_to_spx_factor,  # Set tick interval to 50 points in ES scale
                # Calculate ES equivalent values at 50-point intervals in the SPX scale
                tickvals=[spx_spot + i * 50 for i in range(-3, 4)],
                ticktext=[f"{(spx_spot + i * 50)/es_to_spx_factor:.2f}" for i in range(-3, 4)]
            ),
            
            # Tertiary y-axis (SPY)
            #yaxis3=dict(
            #    title="SPY Strike",
             #   color="magenta",
            #    titlefont=dict(color="magenta"),
             #   tickfont=dict(color="magenta"),
            #    side="left",
           #     position=0,  # Position at left edge
            #    overlaying="y",
            ##    dtick=1 / spy_to_spx_factor,  # Set tick interval to 1 point in SPY scale
                # Calculate SPY equivalent values at key SPX points
            #    tickvals=[spx_spot + i * 10 for i in range(-15, 16)],
            #    ticktext=[f"{(spx_spot + i * 10)/spy_to_spx_factor:.2f}" for i in range(-15, 16, 5)]
            #),
            
            barmode='stack',  # Stack the bars for same strike
            legend_title="Volume Type",
            legend_font=dict(color="white"),
            legend_title_font=dict(color="white"),
            margin=dict(l=120, r=120, t=80, b=20),  # Increased margins to accommodate multiple axes
            height=1000,
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
                "content": f"📊 **Multi-Index Volume Distribution (SPX/ES/SPY)** | {now.strftime('%Y-%m-%d %H:%M')} | {market_status}"
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
    logger.info("=== Multi-Index Volume Monitor Started ===")
    
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
        logger.info("=== Multi-Index Volume Monitor stopped by user ===")