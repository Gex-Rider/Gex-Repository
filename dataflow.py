# -*- coding: utf-8 -*-
import pandas as pd
import plotly.graph_objects as go
import os
import glob
from datetime import datetime

# Configuración
columnas = [
    "TIME_STAMP", "GEX_BY_OI", "GEX_BY_VOLUME", "NETPRESS", 
    "NETFLOW", "PREM_PRESS", "PREM_FLOW", "GAMMA_FLOW", 
    "DELTA_FLOW", "SPOT"
]

colores_flujo = {
    "GEX_BY_OI": "white",
    "GEX_BY_VOLUME": "white",
    "NETPRESS": "red",
    "NETFLOW": "yellow",
    "PREM_PRESS": "orange",
    "PREM_FLOW": "blue",
    "GAMMA_FLOW": "purple",
    "DELTA_FLOW": "green",
    "SPOT": "cyan"
}

# Buscar carpetas con fecha
carpetas = sorted([f for f in os.listdir() if os.path.isdir(f) and f[:4].isdigit()])
total_generados = 0

def crear_grafico(df, base, carpeta):
    """Crea el gráfico interactivo con opción de acumulado"""
    fig = go.Figure()
    
    # SPOT (siempre en eje Y1)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["SPOT"],
        mode="lines",
        name="SPOT",
        line=dict(color=colores_flujo["SPOT"], width=2),
        yaxis="y1",
        visible=True
    ))
    
    # Trazas para modo NORMAL (barras)
    for col in ["NETPRESS", "NETFLOW", "PREM_PRESS", "PREM_FLOW", "GAMMA_FLOW", "DELTA_FLOW"]:
        if col not in df.columns:
            continue
            
        fig.add_trace(go.Bar(
            x=df.index,
            y=df[col],
            name=col,
            marker_color=colores_flujo[col],
            opacity=0.7,
            yaxis="y2",
            visible='legendonly'    # Visible en modo normal
        ))
    
    # Trazas para modo ACUMULADO (líneas + marcadores)
    for col in df.columns:
        if col == "SPOT" or col not in colores_flujo:
            continue
            
        # Solo GEX_BY_OI y GEX_BY_VOLUME en modo acumulado
        if col in ["GEX_BY_OI", "GEX_BY_VOLUME"]:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[col].cumsum() if col not in ["GEX_BY_OI", "GEX_BY_VOLUME"] else df[col],
                mode="lines+markers",
                name=f"{col} (Acum)",
                line=dict(color=colores_flujo[col], width=2),
                marker=dict(color=colores_flujo[col], size=6),
                yaxis="y2",
                visible=True if col == 'SPOT' else 'legendonly'  # Oculto inicialmente
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[col].cumsum(),
                mode="lines+markers",
                name=f"{col} (Acum)",
                line=dict(color=colores_flujo[col], width=2),
                marker=dict(color=colores_flujo[col], size=6),
                yaxis="y2",
                visible=True if col == 'SPOT' else 'legendonly'  # Oculto inicialmente
            ))
    
    # Botones para cambiar entre modos
    fig.update_layout(
        title=f"DATAFLOW - {base.replace('_', ' ').upper()}",
        xaxis=dict(title="Hora", showgrid=True, gridcolor='gray'),
        yaxis=dict(title="SPOT", side="left", showgrid=False, tickformat=".2f"),
        yaxis2=dict(title="Flujos GEX", overlaying="y", side="right", showgrid=True, gridcolor='rgba(100,100,100,0.2)'),
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        autosize=True,  # Añadido para ajuste automático
        margin=dict(l=50, r=50, b=50, t=50, pad=4),  # Márgenes ajustados
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group" # Para las barras en modo normal
        
    )
    

    return fig

# Procesar archivos
for carpeta in carpetas:
    archivos_csv = glob.glob(f"{carpeta}/*_data_flow.csv")

    for ruta_csv in archivos_csv:
        base = os.path.splitext(os.path.basename(ruta_csv))[0]
        nombre_html = os.path.join(carpeta, f"{base}.html")

        if os.path.exists(nombre_html):
            continue

        print(f"Procesando: {ruta_csv}")

        try:
            # Leer y limpiar datos
            df = pd.read_csv(ruta_csv, header=None, names=columnas)
            df['TIME_STAMP'] = pd.to_datetime(df['TIME_STAMP'])
            df.set_index('TIME_STAMP', inplace=True)
            df = df.between_time("08:30", "15:15").dropna(how='all')

            # Crear gráfico
            fig = crear_grafico(df, base, carpeta)
            fig.write_html(nombre_html, 
              include_plotlyjs="cdn",
              full_html=True,
              auto_open=False)
            total_generados += 1

        except Exception as e:
            print(f"Error procesando {ruta_csv}: {e}")
            continue

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
print(f"✔ Hora de finalización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
