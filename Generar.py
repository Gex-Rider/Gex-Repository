# -*- coding: utf-8 -*-
import os
import time
import pandas as pd
import plotly.graph_objects as go
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
    'ZERO':        {'color': 'white',    'symbol': 'circle-open',  'mode': 'markers'},
    'MAXCP':       {'color': 'red',      'symbol': 'circle',       'mode': 'markers'},
    'MINCP':       {'color': 'green',    'symbol': 'circle',       'mode': 'markers'},
    'BAC':         {'color': 'cyan',     'symbol': 'triangle-down','mode': 'markers', 'size': 14},
    'SAC':         {'color': 'magenta',  'symbol': 'triangle-down','mode': 'markers', 'size': 14},
    'BAP':         {'color': 'cyan',     'symbol': 'triangle-up',  'mode': 'markers', 'size': 14},
    'SAP':         {'color': 'magenta',  'symbol': 'triangle-up',  'mode': 'markers', 'size': 14},
    'LONGGAMMA':   {'color': 'cyan',     'symbol': 'cross',        'mode': 'markers'},
    'SHORTGAMMA':  {'color': 'magenta',  'symbol': 'cross',        'mode': 'markers'},
}

# Ruta actual
carpeta_actual = os.getcwd()

def graficar_archivo(ruta_csv):
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    nombre_html = os.path.join(carpeta_actual, f"{base}.html")

    try:
        df = pd.read_csv(ruta_csv, header=None, names=columnas)
        df['Time'] = pd.to_datetime(df['Time'], dayfirst=True)
        df.set_index('Time', inplace=True)

        # Filtrar entre 08:30 y 15:15
        # df = df.between_time("08:30", "15:15")

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
        autosize=True,
        margin=dict(l=20, r=20, t=40, b=20),
        height=None,  # Dejar que el contenedor lo defina
    )

    # HTML con auto-refresh cada 30 segundos y estilo de pantalla completa
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

    # 🔁 Insertar el JS personalizado justo antes de cerrar el <body>
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

    # Escribir archivo HTML
    with open(nombre_html, "w", encoding="utf-8") as f:
        f.write(html_temp)

class CSVHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        nombre = os.path.basename(event.src_path).lower()
        if any(nombre.startswith(activo) and nombre.endswith("_gex_history.csv") for activo in activos):
            graficar_archivo(event.src_path)

# Inicializar observador
if __name__ == "__main__":
    path = os.getcwd()
    event_handler = CSVHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()

    print("🔍 Monitoreando archivos CSV en tiempo real...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
