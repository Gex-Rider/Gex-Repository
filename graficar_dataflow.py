import pandas as pd
import plotly.graph_objects as go
import os


# Ruta al archivo CSV
archivo_csv = "spy_data_flow.csv"

# Nombres de columnas
columnas = [
    "Time", "GEX_BY_OI", "GEX_BY_VOLUME", "NET_PRESS", "NET_FLOW",
    "PREM_PRESS", "PREM_FLOW", "GAMMA_FLOW", "DELTA_FLOW", "SPOT"
]

# Leer el archivo
try:
    df = pd.read_csv(archivo_csv, header=None, names=columnas)
    df["Time"] = pd.to_datetime(df["Time"])
    df.set_index("Time", inplace=True)
except Exception as e:
    print(f"Error al leer {archivo_csv}: {e}")
    exit(1)

# Selección de modo: 'barras' o 'acumulado'
modo = input("Selecciona modo ('barras' o 'acumulado'): ").strip().lower()
acumulado = modo == "acumulado"

# Columnas a graficar sobre segundo eje Y
columnas_dataflow = [
    "NET_PRESS", "NET_FLOW", "PREM_PRESS", "PREM_FLOW",
    "GAMMA_FLOW", "DELTA_FLOW"
]

if acumulado:
    df[columnas_dataflow] = df[columnas_dataflow].cumsum()

# Crear figura
fig = go.Figure()

# Línea SPOT en eje Y primario
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["SPOT"],
    name="SPOT",
    yaxis="y1",
    line=dict(color="blue"),
    mode="lines"
))

# Dataflow sobre eje Y2
for col in columnas_dataflow:
    if acumulado:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[col],
            name=col,
            yaxis="y2",
            mode="lines",
            line=dict(shape="hv")
        ))
    else:
        colores = {"NET_PRESS": "red", "NET_FLOW": "green", "PREM_PRESS": "magenta",
                   "PREM_FLOW": "cyan", "GAMMA_FLOW": "orange", "DELTA_FLOW": "yellow"}
        fig.add_trace(go.Bar(
            x=df.index,
            y=df[col],
            name=col,
            marker_color=colores.get(col, "gray"),
            yaxis="y2"
        ))

# Configuración layout con dos ejes Y
fig.update_layout(
    title="Data Flow vs Spot",
    xaxis=dict(title="Tiempo"),
    yaxis=dict(title="SPOT", side="left"),
    yaxis2=dict(title="Indicadores DataFlow", overlaying="y", side="right"),
    plot_bgcolor="black",
    paper_bgcolor="black",
    font=dict(color="white"),
    height=800,
    barmode="relative" if not acumulado else "overlay"
)

# Guardar como HTML
fig.write_html("dataflow_dashboard.html", include_plotlyjs="cdn")
print("? Gráfico guardado como 'dataflow_dashboard.html'")
