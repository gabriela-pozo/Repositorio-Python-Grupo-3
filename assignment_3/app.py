"""Dashboard – ¿El Estado declara emergencia donde más llueve? (Perú, temporadas ene–may 2022-2025)

Assignment 3 – Parte 3. Se ejecuta desde la carpeta assignment_3/ con:
    uv run streamlit run app.py        (o)        streamlit run app.py
"""
import json
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Rutas relativas a ESTE archivo (no al directorio desde donde se lance la app):
# así funcionan igual en la laptop y en Streamlit Community Cloud.
BASE = Path(__file__).parent
RUTA_CSV = BASE / "datos" / "tabla_final_2022_2025.csv"
RUTA_GEOJSON = BASE / "datos" / "departamentos_peru.geojson"

FUENTE = ("Fuente: PCM – decretos supremos (gob.pe), Open-Meteo (lluvia diaria en la capital) "
          "e INEI (ubigeos). Temporadas ene–may. Elaboración propia.")

METRICAS_MAPA = {
    "Declaratorias de emergencia": "declaratorias",
    "Prórrogas": "prorrogas",
    "Lluvia promedio por temporada (mm)": "lluvia_promedio_mm",
    "Días con lluvia fuerte (≥ 20 mm)": "dias_lluvia_fuerte",
}

st.set_page_config(page_title="Lluvias y declaratorias de emergencia – Perú", layout="wide")


def normalizar(texto):
    """MAYÚSCULAS y sin tildes, para enlazar el nombre del GeoJSON con la tabla."""
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip()


@st.cache_data
def cargar_datos():
    # ubigeo como texto para conservar el cero inicial ("01"); utf-8-sig por el BOM del CSV
    df = pd.read_csv(RUTA_CSV, dtype={"ubigeo": str}, encoding="utf-8-sig")
    df["temporada"] = df["temporada"].astype(int)
    return df


@st.cache_data
def cargar_geojson(codigos):
    """Lee el GeoJSON (solo trae el nombre del departamento) y le agrega el ubigeo de texto.

    `codigos` es un diccionario {NOMBRE NORMALIZADO: ubigeo}; se pasa como tupla de pares
    para que st.cache_data pueda usarlo como clave.
    """
    codigos = dict(codigos)
    with open(RUTA_GEOJSON, encoding="utf-8") as f:
        geo = json.load(f)
    sin_codigo = []
    for feat in geo["features"]:
        nombre = feat["properties"]["departamento"]
        ubigeo = codigos.get(normalizar(nombre))
        feat["properties"]["ubigeo"] = ubigeo
        if ubigeo is None:
            sin_codigo.append(nombre)
    return geo, sin_codigo


df = cargar_datos()
codigos = tuple(sorted({(normalizar(d), u) for d, u in zip(df["departamento"], df["ubigeo"])}))
geo, poligonos_sin_dato = cargar_geojson(codigos)

# ---------------------------------------------------------------- Barra lateral
st.sidebar.header("Filtros")
temporadas = sorted(df["temporada"].unique())
sel_temporadas = st.sidebar.multiselect("Temporadas (ene–may)", temporadas, default=temporadas)

lluvia_min, lluvia_max = int(df["lluvia_total_mm"].min()), int(df["lluvia_total_mm"].max()) + 1
sel_lluvia = st.sidebar.slider("Lluvia acumulada en la capital (mm)", lluvia_min, lluvia_max,
                               (lluvia_min, lluvia_max))

sel_depto = st.sidebar.multiselect("Departamentos (vacío = todos)", sorted(df["departamento"].unique()))

nombre_metrica = st.sidebar.selectbox("Variable que se pinta en el mapa", list(METRICAS_MAPA))
col_metrica = METRICAS_MAPA[nombre_metrica]

# ---------------------------------------------------------------- Filtrado
filtrado = df[df["temporada"].isin(sel_temporadas)
              & df["lluvia_total_mm"].between(*sel_lluvia)]
if sel_depto:
    filtrado = filtrado[filtrado["departamento"].isin(sel_depto)]

st.title("¿El Estado declara emergencia donde más llueve?")
st.caption("Declaratorias de emergencia por lluvias (PCM) frente a la lluvia acumulada en la capital de "
           "cada departamento, temporadas de enero a mayo de 2022 a 2025.")

if filtrado.empty:
    st.warning("Ningún departamento cumple los filtros elegidos. Amplía las temporadas o el rango de lluvia.")
    st.stop()

# Una fila por departamento (suma de declaratorias; promedio de lluvia por temporada)
por_depto = (filtrado.groupby(["ubigeo", "departamento"], as_index=False)
             .agg(lluvia_promedio_mm=("lluvia_total_mm", "mean"),
                  dias_lluvia_fuerte=("dias_lluvia_fuerte", "sum"),
                  declaratorias=("declaratorias", "sum"),
                  prorrogas=("prorrogas", "sum")))
por_depto["lluvia_promedio_mm"] = por_depto["lluvia_promedio_mm"].round(1)

# ---------------------------------------------------------------- Métricas
lider = por_depto.loc[por_depto["declaratorias"].idxmax()]
if len(filtrado) >= 3 and filtrado["lluvia_total_mm"].nunique() > 1 and filtrado["declaratorias"].nunique() > 1:
    corr = filtrado["lluvia_total_mm"].corr(filtrado["declaratorias"])
    texto_corr = f"{corr:.2f}"
else:
    corr, texto_corr = None, "—"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Declaratorias", f"{int(filtrado['declaratorias'].sum()):,}")
c2.metric("Prórrogas", f"{int(filtrado['prorrogas'].sum()):,}")
c3.metric("Lluvia promedio (mm)", f"{filtrado['lluvia_total_mm'].mean():,.0f}")
c4.metric("Más declaratorias", str(lider["departamento"]), f"{int(lider['declaratorias'])} decretos",
          delta_color="off")
c5.metric("Correlación lluvia–declaratorias", texto_corr,
          help="Pearson entre la lluvia de la capital y las declaratorias (fila = departamento y temporada). "
               "Menos de 0.3 en valor absoluto es una relación débil.")

# ---------------------------------------------------------------- Gráficos
st.subheader("1. ¿Dónde se declara más emergencia?")
top = por_depto.nlargest(10, "declaratorias").sort_values("declaratorias")
fig_barras = px.bar(
    top, x="declaratorias", y="departamento", orientation="h", text="declaratorias",
    hover_data={"lluvia_promedio_mm": True, "prorrogas": True},
    labels={"declaratorias": "Declaratorias de emergencia por lluvias", "departamento": "",
            "lluvia_promedio_mm": "Lluvia promedio (mm)", "prorrogas": "Prórrogas"},
    title=f"{lider['departamento']} lidera las declaratorias con {int(lider['declaratorias'])} decretos",
    color_discrete_sequence=["#2468a9"],
)
fig_barras.update_layout(template="plotly_white", height=460)
st.plotly_chart(fig_barras)

st.subheader("2. ¿Más lluvia, más declaratorias?")
disp = filtrado.assign(temporada=filtrado["temporada"].astype(str))
if corr is None:
    titulo_disp = "Con estos filtros hay muy pocos puntos para medir la relación"
elif abs(corr) < 0.3:
    titulo_disp = f"Más lluvia no significa más declaratorias (correlación {corr:.2f}, débil)"
else:
    titulo_disp = f"En esta selección, más lluvia sí se asocia a más declaratorias (correlación {corr:.2f})"
fig_disp = px.scatter(
    disp, x="lluvia_total_mm", y="declaratorias", color="temporada", hover_name="departamento",
    hover_data={"capital": True, "dias_lluvia_fuerte": True, "prorrogas": True, "temporada": False},
    category_orders={"temporada": [str(t) for t in temporadas]},
    color_discrete_sequence=["#7fb6dc", "#4c94c8", "#2468a9", "#083b72"],
    labels={"lluvia_total_mm": "Lluvia acumulada en la capital, enero–mayo (mm)",
            "declaratorias": "Declaratorias de emergencia por lluvias", "temporada": "Temporada",
            "capital": "Capital", "dias_lluvia_fuerte": "Días con 20 mm o más", "prorrogas": "Prórrogas"},
    title=titulo_disp,
)
fig_disp.update_traces(marker=dict(size=10, line=dict(width=1, color="white")))
fig_disp.update_layout(template="plotly_white", height=500)
st.plotly_chart(fig_disp)

st.subheader("3. Mapa del Perú por departamento")
fig_mapa = px.choropleth_map(
    por_depto, geojson=geo, locations="ubigeo", featureidkey="properties.ubigeo",
    color=col_metrica, color_continuous_scale="Reds" if col_metrica != "lluvia_promedio_mm" else "Blues",
    hover_name="departamento",
    hover_data={"ubigeo": False, "declaratorias": True, "prorrogas": True, "lluvia_promedio_mm": True,
                "dias_lluvia_fuerte": True},
    labels={"declaratorias": "Declaratorias", "prorrogas": "Prórrogas",
            "lluvia_promedio_mm": "Lluvia promedio (mm)", "dias_lluvia_fuerte": "Días lluvia fuerte",
            col_metrica: nombre_metrica},
    map_style="carto-positron", center={"lat": -9.2, "lon": -75.0}, zoom=3.6, opacity=0.8,
    title=f"{nombre_metrica} por departamento ({', '.join(str(t) for t in sorted(sel_temporadas))})",
)
fig_mapa.update_layout(height=640, margin=dict(l=0, r=0, t=50, b=0))
st.plotly_chart(fig_mapa)

# Reporte de cruce con el GeoJSON (lo que no cruzó se dice, no se oculta)
ubigeos_con_dato = set(por_depto["ubigeo"])
nombre_por_ubigeo = dict(zip(df["ubigeo"], df["departamento"]))   # con tildes, como en la tabla
sin_dato_en_mapa = sorted(nombre_por_ubigeo[f["properties"]["ubigeo"]] for f in geo["features"]
                          if f["properties"]["ubigeo"] in nombre_por_ubigeo
                          and f["properties"]["ubigeo"] not in ubigeos_con_dato)
st.caption(
    f"Cruce tabla–GeoJSON por ubigeo (texto): {por_depto['ubigeo'].nunique()} de {len(geo['features'])} "
    f"polígonos con datos con los filtros actuales. "
    + ("Polígonos sin ubigeo en la tabla: ninguno. " if not poligonos_sin_dato
       else f"Polígonos sin ubigeo en la tabla: {', '.join(poligonos_sin_dato)}. ")
    + ("" if not sin_dato_en_mapa
       else f"Sin datos por los filtros: {', '.join(sin_dato_en_mapa)}." if len(sin_dato_en_mapa) <= 6
       else f"Sin datos por los filtros: {len(sin_dato_en_mapa)} departamentos.")
)

# ---------------------------------------------------------------- Tabla
st.subheader("4. Datos filtrados")
tabla = (filtrado[["temporada", "ubigeo", "departamento", "capital", "lluvia_total_mm",
                   "dias_lluvia_fuerte", "declaratorias", "prorrogas"]]
         .sort_values(["temporada", "declaratorias"], ascending=[True, False]))
st.dataframe(tabla, hide_index=True)
st.download_button("Descargar la tabla filtrada (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                   file_name="datos_filtrados.csv", mime="text/csv")

st.caption(FUENTE)
