# -*- coding: utf-8 -*-
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

import plotly.graph_objects as go
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

# Configuración
activos = ['spy', 'spx', 'qqq', 'ndx']
columnas = [
    "Time", "MAXGEX", "MINGEX", "MAXVEX", "MINVEX",
    "MAXDEX", "MINDEX", "ZERO", "BAC", "SAC", "BAP", "SAP",
    "MAXCP", "MINCP", "LONGGAMMA", "SHORTGAMMA", "SPOT"
]

estilos = {
    'SPOT':        {'color': 'blue',     'symbol': None,           'mode': 'lines'},
    'MAXGEX':      {'color': 'red',      'symbol': 'square-open',  'mode': 'markers'},
    'MINGEX':      {'color': 'green',    'symbol': 'square-open',  'mode': 'markers'},
    'MAXVEX':      {'color': 'red',      'symbol': 'x',            'mode': 'markers'},
    'MINVEX':      {'color': 'green',    'symbol': 'x',            'mode': 'markers'},
    'MAXDEX':      {'color': 'red',      'symbol': 'diamond',      'mode': 'markers'},
    'MINDEX':      {'color': 'green',    'symbol': 'diamond',      'mode': 'markers'},
    'ZERO':        {'color': 'yellow',    'symbol': 'circle-open',  'mode': 'markers'},
    'MAXCP':       {'color': 'red',      'symbol': 'circle',       'mode': 'markers'},
    'MINCP':       {'color': 'green',    'symbol': 'circle',       'mode': 'markers'},
    'BAC':         {'color': 'cyan',     'symbol': 'triangle-down','mode': 'markers', 'size': 14},
    'SAC':         {'color': 'magenta',  'symbol': 'triangle-down','mode': 'markers', 'size': 14},
    'BAP':         {'color': 'cyan',     'symbol': 'triangle-up',  'mode': 'markers', 'size': 14},
    'SAP':         {'color': 'magenta',  'symbol': 'triangle-up',  'mode': 'markers', 'size': 14},
    'LONGGAMMA':   {'color': 'cyan',     'symbol': 'cross',        'mode': 'markers'},
    'SHORTGAMMA':  {'color': 'magenta',  'symbol': 'cross',        'mode': 'markers'},
}

# Ruta personalizada para archivos CSV
carpeta_csv = r"E:\GEX\Sync"

# Ruta donde guardar los HTML (puede ser diferente si quieres)
carpeta_salida = os.getcwd()

def graficar_archivo(ruta_csv):
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    nombre_html = os.path.join(carpeta_salida, f"{base}.html")

    try:
        # Leer CSV usando un parser de fechas más flexible
        df = pd.read_csv(ruta_csv, header=None, names=columnas)
        
        # Intentar convertir la columna Time a datetime con manejo de errores
        try:
            # Intentar el formato específico primero
            df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S')
        except ValueError:
            # Si falla, intentar con formato inferido
            try:
                df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d')
            except ValueError:
                # Si todo falla, intentar con el formato más flexible
                df['Time'] = pd.to_datetime(df['Time'], format='mixed')
                
        df.set_index('Time', inplace=True)

        # df = df.between_time("08:30", "15:15")  # opcional

    except Exception as e:
        print(f"❌ Error leyendo {ruta_csv}: {e}")
        return

    fig = go.Figure()

    for col in df.columns:
        estilo = estilos.get(col, {'color': 'gray', 'symbol': 'circle', 'mode': 'markers'})
        marker_props = {
            'color': estilo['color'],
            'symbol': estilo['symbol'],
        }
        if 'size' in estilo:
            marker_props['size'] = estilo['size']

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[col],
            mode=estilo['mode'],
            name=col,
            marker=marker_props,
            line=dict(color=estilo['color']) if estilo['mode'] == 'lines' else None,
            visible=True if col == 'SPOT' else 'legendonly'
        ))

    fig.update_layout(
        title=f"GEX History: {base.upper()}",
        xaxis_title="Tiempo",
        yaxis_title="Valor",
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        autosize=True,
        margin=dict(l=20, r=20, t=40, b=20),
        height=None,
    )

    html_temp = """<!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="30">
        <style>
            html, body {
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: black;
                overflow: hidden;
            }
            #chart {
                width: 100vw;
                height: 100vh;
            }
        </style>
    </head>
    <body>
    <div id="chart">
    """
    html_temp += fig.to_html(full_html=False, include_plotlyjs='cdn', div_id='chart')
    html_temp += "</div>"

    html_temp += """
    <script>
        const STORAGE_KEY = 'plotly_visibility';

        window.addEventListener('load', () => {
            const gd = document.querySelector('.js-plotly-plot');
            const visibility = JSON.parse(localStorage.getItem(STORAGE_KEY));
            if (visibility && gd && gd.data) {
                Plotly.restyle(gd, 'visible', visibility);
            }
        });

        window.addEventListener('DOMContentLoaded', () => {
            const gd = document.querySelector('.js-plotly-plot');
            if (!gd) return;

            gd.on('plotly_legendclick', function(eventData) {
                const visibilities = gd.data.map(trace => trace.visible || true);
                const i = eventData.curveNumber;
                visibilities[i] = visibilities[i] === 'legendonly' ? true : 'legendonly';
                localStorage.setItem(STORAGE_KEY, JSON.stringify(visibilities));
            });
        });
    </script>
    </body></html>
    """

    with open(nombre_html, "w", encoding="utf-8") as f:
        f.write(html_temp)

    print(f"✅ Gráfico generado: {nombre_html}")


class CSVHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        nombre = os.path.basename(event.src_path).lower()
        if any(nombre.startswith(activo) and nombre.endswith("_gex_history.csv") for activo in activos):
            print(f"📊 Procesando archivo: {event.src_path}")
            graficar_archivo(event.src_path)


if __name__ == "__main__":
    # Procesar archivos existentes al inicio
    print(f"🔍 Buscando archivos existentes en: {carpeta_csv}")
    for activo in activos:
        csv_file = os.path.join(carpeta_csv, f"{activo}_gex_history.csv")
        if os.path.exists(csv_file):
            print(f"📊 Procesando archivo existente: {csv_file}")
            graficar_archivo(csv_file)

    # Configurar observador para cambios en archivos
    event_handler = CSVHandler()
    observer = Observer()
    observer.schedule(event_handler, path=carpeta_csv, recursive=False)
    observer.start()

    print(f"🔍 Monitoreando archivos en: {carpeta_csv}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()