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
    'ZERO':        {'color': 'Yellow',    'symbol': 'circle-open',  'mode': 'markers'},
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
            autosize=True
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

        html_temp += f"""
        <script>
            const STORAGE_KEY = 'plotly_visibility';
            const RANGE_STORAGE_KEY = 'plotly_axis_ranges_{base}';

            window.addEventListener('load', () => {{
                const gd = document.querySelector('.js-plotly-plot');
                const visibility = JSON.parse(localStorage.getItem(STORAGE_KEY));
                const savedLayout = JSON.parse(localStorage.getItem(RANGE_STORAGE_KEY));

                // Restaurar visibilidad común
                if (visibility && gd && gd.data) {{
                    Plotly.restyle(gd, 'visible', visibility);
                }}

                // Restaurar rango de ejes específico de este activo
                if (savedLayout && gd) {{
                    Plotly.relayout(gd, savedLayout);
                }}
            }});

            window.addEventListener('DOMContentLoaded', () => {{
                const gd = document.querySelector('.js-plotly-plot');
                if (!gd) return;

                // Guardar visibilidad común
                gd.on('plotly_legendclick', function(eventData) {{
                    const visibilities = gd.data.map(trace => trace.visible || true);
                    const i = eventData.curveNumber;
                    visibilities[i] = visibilities[i] === 'legendonly' ? true : 'legendonly';
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(visibilities));
                }});

                // Guardar rango de ejes específico de este activo
                gd.on('plotly_relayout', function(eventData) {{
                    const ranges = {{}};
                    for (const key in eventData) {{
                        if (key.includes('range')) {{
                            ranges[key] = eventData[key];
                        }}
                    }}
                    if (Object.keys(ranges).length > 0) {{
                        localStorage.setItem(RANGE_STORAGE_KEY, JSON.stringify(ranges));
                    }}
                }});
            }});
        </script>
        </body></html>
        """
       



        with open(nombre_html, "w", encoding="utf-8") as f:f.write(html_temp)

        total_generados += 1

# Generar índice HTML con estructura tabular
html_index = """<html>
<head>
    <title>GEX Dashboard - Índice</title>
    <style>
        body {
            background-color: black; 
            color: white; 
            font-family: Arial;
            margin: 20px;
        }
        h1 {
            color: cyan;
            text-align: center;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #333;
            color: white;
            padding: 10px;
            text-align: left;
        }
        td {
            padding: 8px;
            border-bottom: 1px solid #444;
            vertical-align: top;
        }
        tr:hover {
            background-color: #222;
        }
        a {
            color: cyan;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .file-list {
            list-style-type: none;
            padding-left: 5px;
        }
        .file-list li {
            margin-bottom: 5px;
        }
        .date-header {
            color: orange;
            font-weight: bold;
            margin-top: 15px;
        }
    </style>
</head>
<body>
<h1>GEX Dashboards por Día</h1>
<table>
    <thead>
        <tr>
            <th>Fecha</th>
            <th>GEX History</th>
            <th>Data Flow</th>
        </tr>
    </thead>
    <tbody>
"""

for carpeta in reversed(carpetas):
    # Archivos GEX History
    archivos_gex = sorted(glob.glob(f"{carpeta}/*gex_history.html"))
    # Archivos Data Flow
    archivos_flow = sorted(glob.glob(f"{carpeta}/*_data_flow.html"))
    
    html_index += f"""
    <tr>
        <td class="date-header">{carpeta}</td>
        <td>
            <ul class="file-list">"""
    
    for archivo in archivos_gex:
        nombre = os.path.basename(archivo).replace("_gex_history.html", "").upper()
        html_index += f'<li><a href="{archivo}">{nombre}</a></li>'
    
    html_index += """
            </ul>
        </td>
        <td>
            <ul class="file-list">"""
    
    for archivo in archivos_flow:
        nombre = os.path.basename(archivo).replace("_data_flow.html", "").upper()
        html_index += f'<li><a href="{archivo}">{nombre}</a></li>'
    
    html_index += """
            </ul>
        </td>
    </tr>"""

html_index += """
    </tbody>
</table>
<p style="color: gray; font-size: 12px; margin-top: 20px;">
Nota: Los gráficos incluyen un botón para alternar entre vista acumulada y directa<br>
GEX_BY_OI y GEX_BY_VOLUME solo disponibles en modo acumulado
</p>
</body></html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_index)

print(f"\n✔ {total_generados} nuevos gráficos generados")
print(f"✔ Índice actualizado: index_dataflow.html")
