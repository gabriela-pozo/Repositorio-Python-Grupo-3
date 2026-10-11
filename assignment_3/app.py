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

# Etiquetas comunes para ejes y tooltips de todos los gráficos
ETIQUETAS = {
    "declaratorias": "Declaratorias de emergencia por lluvias", "prorrogas": "Prórrogas",
    "lluvia_total_mm": "Lluvia acumulada en la capital, enero–mayo (mm)",
    "lluvia_promedio_mm": "Lluvia promedio (mm)", "dias_lluvia_fuerte": "Días con 20 mm o más",
    "temporada": "Temporada", "capital": "Capital", "departamento": "",
    "correlacion": "Correlación lluvia–declaratorias",
}

st.set_page_config(page_title="Lluvias y declaratorias de emergencia – Perú", layout="wide")


def normalizar(texto):
    """MAYÚSCULAS y sin tildes, para enlazar el nombre del GeoJSON con la tabla."""
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip()


@st.cache_data
def cargar_datos():
    # ubigeo como texto para conservar el cero inicial ("01"); utf-8-sig por el BOM del CSV
    return pd.read_csv(RUTA_CSV, dtype={"ubigeo": str}, encoding="utf-8-sig")


@st.cache_data
def cargar_geojson():
    """Lee el GeoJSON (solo trae el nombre) y le agrega el ubigeo de la tabla por nombre normalizado."""
    datos = cargar_datos()
    codigos = dict(zip(datos["departamento"].map(normalizar), datos["ubigeo"]))
    with open(RUTA_GEOJSON, encoding="utf-8") as f:
        geo = json.load(f)
    for feat in geo["features"]:
        feat["properties"]["ubigeo"] = codigos.get(normalizar(feat["properties"]["departamento"]))
    sin_codigo = [f["properties"]["departamento"] for f in geo["features"] if f["properties"]["ubigeo"] is None]
    return geo, sin_codigo


df = cargar_datos()
geo, poligonos_sin_dato = cargar_geojson()

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
filtrado = df[df["temporada"].isin(sel_temporadas) & df["lluvia_total_mm"].between(*sel_lluvia)]
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
                  prorrogas=("prorrogas", "sum"))
             .round({"lluvia_promedio_mm": 1}))

# ---------------------------------------------------------------- Métricas
lider = por_depto.loc[por_depto["declaratorias"].idxmax()]
def correlacion(d):
    """Pearson lluvia–declaratorias; NaN con menos de 3 filas (con 2 puntos siempre da ±1) o valores constantes."""
    return d["lluvia_total_mm"].corr(d["declaratorias"]) if len(d) >= 3 else float("nan")


corr = correlacion(filtrado)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Declaratorias", f"{filtrado['declaratorias'].sum():,}")
c2.metric("Prórrogas", f"{filtrado['prorrogas'].sum():,}")
c3.metric("Lluvia promedio (mm)", f"{filtrado['lluvia_total_mm'].mean():,.0f}")
c4.metric("Más declaratorias", lider["departamento"], f"{lider['declaratorias']} decretos", delta_color="off")
c5.metric("Correlación lluvia–declaratorias", "—" if pd.isna(corr) else f"{corr:.2f}",
          help="Pearson entre la lluvia de la capital y las declaratorias (fila = departamento y temporada). "
               "Menos de 0.3 en valor absoluto es una relación débil.")

# ---------------------------------------------------------------- Gráficos
st.subheader("1. ¿Dónde se declara más emergencia?")
top = por_depto.nlargest(10, "declaratorias").sort_values("declaratorias")
fig_barras = px.bar(
    top, x="declaratorias", y="departamento", orientation="h", text="declaratorias",
    hover_data=["lluvia_promedio_mm", "prorrogas"], labels=ETIQUETAS,
    title=f"{lider['departamento']} lidera las declaratorias con {lider['declaratorias']} decretos",
    color_discrete_sequence=["#2468a9"],
)
fig_barras.update_layout(template="plotly_white", height=460)
st.plotly_chart(fig_barras)

st.subheader("2. ¿Más lluvia, más declaratorias?")
if pd.isna(corr):
    titulo_disp = "Con estos filtros hay muy pocos puntos para medir la relación"
elif abs(corr) < 0.3:
    titulo_disp = f"Más lluvia no significa más declaratorias (correlación {corr:.2f}, débil)"
else:
    sentido = "más" if corr > 0 else "menos"
    titulo_disp = f"En esta selección, más lluvia se asocia a {sentido} declaratorias (correlación {corr:.2f})"
fig_disp = px.scatter(
    filtrado.astype({"temporada": str}), x="lluvia_total_mm", y="declaratorias", color="temporada",
    hover_name="departamento", hover_data=["capital", "dias_lluvia_fuerte", "prorrogas"],
    category_orders={"temporada": [str(t) for t in temporadas]},
    color_discrete_sequence=["#7fb6dc", "#4c94c8", "#2468a9", "#083b72"],
    labels=ETIQUETAS, title=titulo_disp,
)
fig_disp.update_traces(marker=dict(size=10, line=dict(width=1, color="white")))
fig_disp.update_layout(template="plotly_white", height=500)
st.plotly_chart(fig_disp)

st.subheader("3. ¿Cambió la relación entre temporadas?")
por_temporada = (filtrado.groupby("temporada", as_index=False)
                 .agg(declaratorias=("declaratorias", "sum"), lluvia_promedio_mm=("lluvia_total_mm", "mean")))
por_temporada["correlacion"] = [correlacion(g) for _, g in filtrado.groupby("temporada")]
por_temporada = por_temporada.round({"lluvia_promedio_mm": 1, "correlacion": 2}).astype({"temporada": str})
primera, ultima = por_temporada.iloc[0], por_temporada.iloc[-1]
if len(por_temporada) == 1:
    titulo_temp = (f"{primera['temporada']}: {primera['declaratorias']} declaratorias con "
                   f"{primera['lluvia_promedio_mm']:.0f} mm de lluvia promedio. Elige más temporadas para comparar")
else:
    titulo_temp = (f"Las declaratorias pasaron de {primera['declaratorias']} en {primera['temporada']} a "
                   f"{ultima['declaratorias']} en {ultima['temporada']}; la lluvia promedio, de "
                   f"{primera['lluvia_promedio_mm']:.0f} a {ultima['lluvia_promedio_mm']:.0f} mm")
fig_temp = px.bar(
    por_temporada, x="temporada", y="declaratorias", text="declaratorias",
    hover_data=["lluvia_promedio_mm", "correlacion"], labels=ETIQUETAS,
    title=titulo_temp, color_discrete_sequence=["#2468a9"],
)
fig_temp.update_layout(template="plotly_white", height=420)
st.plotly_chart(fig_temp)
st.caption("Al pasar el mouse por cada barra se ve la lluvia promedio y la correlación de esa temporada.")

st.subheader("4. Mapa del Perú por departamento")
fig_mapa = px.choropleth_map(
    por_depto, geojson=geo, locations="ubigeo", featureidkey="properties.ubigeo",
    color=col_metrica, color_continuous_scale="Blues" if col_metrica == "lluvia_promedio_mm" else "Reds",
    hover_name="departamento",
    hover_data={"ubigeo": False, "declaratorias": True, "prorrogas": True, "lluvia_promedio_mm": True,
                "dias_lluvia_fuerte": True},
    labels={**ETIQUETAS, col_metrica: nombre_metrica},
    map_style="carto-positron", center={"lat": -9.2, "lon": -75.0}, zoom=3.6, opacity=0.8,
    title=f"{nombre_metrica} por departamento ({', '.join(map(str, sorted(sel_temporadas)))})",
)
fig_mapa.update_layout(height=640, margin=dict(l=0, r=0, t=50, b=0))
st.plotly_chart(fig_mapa)

# Reporte de cruce con el GeoJSON (lo que no cruzó se dice, no se oculta)
sin_dato_en_mapa = sorted(set(df["departamento"]) - set(por_depto["departamento"]))
st.caption(
    f"Cruce tabla–GeoJSON por ubigeo (texto): {por_depto['ubigeo'].nunique()} de {len(geo['features'])} "
    f"polígonos con datos con los filtros actuales. "
    f"Polígonos sin ubigeo en la tabla: {', '.join(poligonos_sin_dato) or 'ninguno'}. "
    + (f"Sin datos por los filtros: {len(sin_dato_en_mapa)} departamentos." if sin_dato_en_mapa else "")
)

# ---------------------------------------------------------------- Tabla
st.subheader("5. Datos filtrados")
tabla = (filtrado[["temporada", "ubigeo", "departamento", "capital", "lluvia_total_mm",
                   "dias_lluvia_fuerte", "declaratorias", "prorrogas"]]
         .sort_values(["temporada", "declaratorias"], ascending=[True, False]))
st.dataframe(tabla, hide_index=True)
st.download_button("Descargar la tabla filtrada (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                   file_name="datos_filtrados.csv", mime="text/csv")

st.caption(FUENTE)
