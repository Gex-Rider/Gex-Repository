# -*- coding: utf-8 -*-
import pandas as pd
import plotly.graph_objects as go
import os
import glob

# Columnas del CSV
columnas = [
    "Time", "MAXGEX", "MINGEX", "MAXVEX", "MINVEX",
    "MAXDEX", "MINDEX", "ZERO", "BAC", "SAC", "BAP", "SAP",
    "MAXCP", "MINCP", "LONGGAMMA", "SHORTGAMMA", "SPOT"
]

# Estilos para cada señal
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

# Buscar carpetas con nombre de fecha
carpetas = sorted([f for f in os.listdir() if os.path.isdir(f) and f[:4].isdigit()])

total_generados = 0

for carpeta in carpetas:
    archivos_csv = glob.glob(f"{carpeta}/*_gex_history.csv")

    for ruta_csv in archivos_csv:
        base = os.path.splitext(os.path.basename(ruta_csv))[0]  # ej: spy_gex_history
        nombre_html = os.path.join(carpeta, f"{base}.html")

        if os.path.exists(nombre_html):
            continue  # ya existe, saltar

        print(f"??? Generando: {nombre_html}")

        # Leer CSV
        try:
            df = pd.read_csv(ruta_csv, header=None, names=columnas)
            df['Time'] = pd.to_datetime(df['Time'], dayfirst=True)
            df.set_index('Time', inplace=True)

            # Filtrar datos entre las 08:30 y las 15:15
            hora_inicio = pd.to_datetime("08:30").time()
            hora_fin = pd.to_datetime("15:15").time()
            df = df.between_time(hora_inicio, hora_fin)

        except Exception as e:
            print(f"? Error leyendo {ruta_csv}: {e}")
            continue

        # Crear figura
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
            title=f"Evolución indicadores: {base.upper()}",
            xaxis_title="Tiempo",
            yaxis_title="Valor",
            plot_bgcolor="black",
            paper_bgcolor="black",
            font=dict(color="white"),
            height=800,
        )

        fig.write_html(nombre_html, include_plotlyjs="cdn")
        total_generados += 1

# Generar índice HTML
html_index = """<html>
<head><title>GEX Dashboard - Índice</title></head>
<body style="background-color: black; color: white; font-family: Arial">
<h1>GEX Dashboards por Día</h1>
<ul>
"""

for carpeta in reversed(carpetas):
    archivos_html = sorted(glob.glob(f"{carpeta}/*_gex_history.html"))
    for archivo in archivos_html:
        nombre = os.path.basename(archivo).replace("_gex_history.html", "").upper()
        html_index += f'<li><a href="{archivo}" style="color: cyan;">{carpeta} - {nombre}</a></li>\n'

html_index += "</ul></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_index)

print(f"? {total_generados} nuevos gráficos generados.")
print("? Índice actualizado: index.html")
