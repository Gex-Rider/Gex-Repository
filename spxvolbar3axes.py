import time
import os
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import requests
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.ticker import FuncFormatter
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
    """Process SPX volume data and generate visualization using Matplotlib"""
    carpeta_csv = r"E:\GEX\Sync"
    csv_file = os.path.join(carpeta_csv, f"spx_vol.csv")
    try:
        # Verify file exists first
        if not os.path.exists(csv_file):
            logger.error("Data file spx_vol.csv not found")
            return None

        # Read and extract data
        logger.info("Reading data from spx_vol.csv")
        df_raw = pd.read_csv(csv_file, header=None)
        
        # Extract spot prices
        spotSPX = float(df_raw.iloc[0, 0])
        spotES = float(df_raw.iloc[0, 1])
        spotSPY = float(df_raw.iloc[0, 2]) if len(df_raw.iloc[0]) > 2 else None
        
        # Si no se proporciona spotSPY, usar una aproximación (SPX/10)
        if spotSPY is None:
            spotSPY = spotSPX / 10
            logger.warning(f"SPY spot price not provided, using approximation: {spotSPY:.2f}")
        
        df = df_raw.iloc[1:].copy()
        
        # Set column names
        df.columns = ["Strike", "Vol0DTE", "Vol1DTE", "OtherVol"]
        
        # Convert and clean data
        numeric_cols = ["Strike", "Vol0DTE", "Vol1DTE", "OtherVol"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        df.dropna(inplace=True)
        
        # Calculate total volume
        df["TotalVol"] = df["Vol0DTE"] + df["Vol1DTE"] + df["OtherVol"]
        
        # Filter strikes (±2% from spot)
        min_strike = spotSPX * 0.985  # Cambiado a ±2%
        max_strike = spotSPX * 1.015
        logger.info(f"Filtering strikes between {min_strike:.2f} and {max_strike:.2f}")
        df_filtered = df[(df["Strike"] >= min_strike) & (df["Strike"] <= max_strike)].copy()
        
        if len(df_filtered) == 0:
            logger.warning("No data available after filtering")
            return None
            
        # Calculate ES equivalent values
        df_filtered["ES_Equivalent"] = (df_filtered["Strike"] * (spotES / spotSPX)).round(2)
        
        # Sort by Strike for proper plotting
        df_filtered = df_filtered.sort_values("Strike")
        
        # Create figure
        plt.style.use('dark_background')
        width_inches = 8   # Ancho deseado en pulgadas
        height_inches = 12  # Alto deseado en pulgadas
        dpi = 100           # Resolución

        fig, ax = plt.subplots(figsize=(width_inches, height_inches))
        
        # Colors for different volume types (from lightest to darkest)
        positive_colors = ["#006400", "#32CD32", "#90EE90"]  # Dark green, Lime green, Light green
        negative_colors = ["#8B0000", "#FF0000", "#FFC0CB"]  # Dark red, Red, Pink
        
        # Get the full strike range for plotting
        strikes = df_filtered["Strike"].values
        es_equiv = df_filtered["ES_Equivalent"].values
        
        # Plot positive volumes (stacked to the right)
        bottom_pos = np.zeros(len(df_filtered))
        for i, col in enumerate(["Vol0DTE", "Vol1DTE", "OtherVol"]):
            pos_data = df_filtered[col].where(df_filtered[col] > 0, 0)
            ax.barh(
                strikes, 
                pos_data, 
                left=bottom_pos, 
                color=positive_colors[i],
                height=4.0  # Ancho de barra de 5 unidades
            )
            bottom_pos += pos_data
        
        # Plot negative volumes (stacked to the left)
        bottom_neg = np.zeros(len(df_filtered))
        for i, col in enumerate(["Vol0DTE", "Vol1DTE", "OtherVol"]):
            neg_data = -abs(df_filtered[col].where(df_filtered[col] < 0, 0))  # Negative value for proper left position
            ax.barh(
                strikes, 
                neg_data, 
                left=bottom_neg,  # Start from 0 or previous bar's position
                color=negative_colors[i],
                height=4.0  # Ancho de barra de 5 unidades
            )
            bottom_neg += neg_data
        
        # Add spot price line
        ax.axhline(spotSPX, color='yellow', linestyle='--', alpha=0.7)
        
        # Set x-axis symmetric
        max_vol = max(bottom_pos.max(), abs(bottom_neg.min()) if len(bottom_neg) > 0 else 0)
        ax.set_xlim(-max_vol*1.1, max_vol*1.1)
        
        # Add max volume concentration lines
        if not df_filtered.empty:
            max_pos_idx = df_filtered["TotalVol"].idxmax()
            max_neg_idx = df_filtered["TotalVol"].idxmin()
            
            max_pos_strike = df_filtered.loc[max_pos_idx, "Strike"]
            max_neg_strike = df_filtered.loc[max_neg_idx, "Strike"]
            
            ax.axhline(max_pos_strike, color='lightgreen', linestyle=':', alpha=0.7)
            ax.axhline(max_neg_strike, color='pink', linestyle=':', alpha=0.7)
        
        # Configurar el eje principal para mostrar strikes en incrementos de 5
        min_strike_rounded = int(min_strike - (min_strike % 5))
        max_strike_rounded = int(max_strike + (5 - max_strike % 5))
        strike_ticks = np.arange(min_strike_rounded, max_strike_rounded + 1, 5)
        ax.set_yticks(strike_ticks)
        
        # Asegurar que las barras estén centradas en los valores de strike
        ax.set_ylim(min_strike_rounded - 2.5, max_strike_rounded + 2.5)
        
        # Set up secondary axis for ES equivalents
        ax2 = ax.twinx()
        
        # Asegurarnos que el eje secundario tenga el mismo rango que el eje principal
        ax2.set_ylim(ax.get_ylim())
        
        # Calcular equivalentes ES para cada tick de strike
        es_ticks = [(strike * (spotES / spotSPX)).round(2) for strike in strike_ticks]
        
        # Configurar eje secundario con las mismas posiciones que el eje principal
        ax2.set_yticks(strike_ticks)
        ax2.set_yticklabels([f"{es:.2f}" for es in es_ticks])
        
        # Crear un tercer eje para SPY (a la derecha)
        par1 = ax.twiny().twinx()
        # Mover el tercer eje a la izquierda
        par1.spines["left"].set_position(("axes", -0.15))  # Posición -15% del ancho del gráfico
        # Hacer visible el eje izquierdo
        par1.spines["left"].set_visible(True)
        par1.spines["right"].set_visible(False)
        par1.yaxis.set_label_position('left')
        par1.yaxis.set_ticks_position('left')
        
        # Asegurarnos que el tercer eje tenga el mismo rango que el eje principal
        par1.set_ylim(ax.get_ylim())
        
        # Calcular equivalentes SPY para cada tick de strike
        spy_ticks = [(strike * (spotSPY / spotSPX)).round(2) for strike in strike_ticks]
        
        # Configurar tercer eje con las mismas posiciones que el eje principal
        par1.set_yticks(strike_ticks)
        par1.set_yticklabels([f"{spy:.2f}" for spy in spy_ticks])
        par1.tick_params(axis='y', colors='orange',labelsize=12)  # Usar color naranja para SPY

        
        # Formatting
        ax.set_title(
            f"SPX Volume by Strike - Spot: {spotSPX:.2f}  ({datetime.now().strftime('%Y-%m-%d %H:%M')})", 
            pad=20, fontsize=14
        )
        ax.set_xlabel("Volume", fontsize=12)

        # Ocultar el eje X superior (si existe)
        # ax.xaxis.set_visible(False)

        # Configurar formateador para el eje X inferior (volumen)
        def format_vol(x, pos):
            return f'{x/1000:.0f}K' if x != 0 else '0'

        ax.xaxis.set_major_formatter(FuncFormatter(format_vol))



        #ax.set_ylabel("SPX Strike Price", fontsize=12)
        ax.tick_params(axis='both', labelsize=12)
        ax2.set_ylabel("/ES Equivalent", color='cyan', fontsize=12)
        ax2.tick_params(axis='y', colors='cyan', labelsize=12)
        par1.set_ylabel("SPY Equivalent", color='orange', fontsize=12)

       
        # Grid con incrementos de 5
        #ax.grid(True, axis='y', alpha=0.3)
        ax.grid(False, axis='y')
        # Eliminar la leyenda (como solicitado)
        
        # Save output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/spx_volume_{timestamp}.png"
        os.makedirs("output", exist_ok=True)
        plt.tight_layout(rect=[0.05, 0, 1, 1])  # Ajustar para dejar espacio para el eje SPY



        # Tamaño en píxeles será: width_inches*dpi × height_inches*dpi (1000×1600 px en este caso)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Chart saved to {output_path}")
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