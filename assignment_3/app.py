"""Dashboard – ¿El Estado declara emergencia donde más llueve? (Perú, temporadas ene–may 2022-2025)

Assignment 3 – Parte 3. Se ejecuta desde la carpeta assignment_3/ con:
    uv run streamlit run app.py        (o)        streamlit run app.py
"""
import json
import unicodedata
from itertools import count
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

# Paleta (apta para daltonismo): azul = lluvia, naranja = emergencia, navy = texto
LLUVIA = "#0072B2"
EMERGENCIA = "#D55E00"
NAVY = "#0B2540"
ESCALA_LLUVIA = ["#E6F1F8", "#A9D0E8", "#5BA3D0", LLUVIA, "#004A75"]
ESCALA_EMERGENCIA = ["#FDF0E3", "#F9CFA3", "#F0A25F", EMERGENCIA, "#8A3B00"]

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

st.set_page_config(page_title="Perú: emergencias por lluvias 2022–2025", layout="wide")


def normalizar(texto):
    """MAYÚSCULAS y sin tildes, para enlazar el nombre del GeoJSON con la tabla."""
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip()


def correlacion(d):
    """Pearson lluvia–declaratorias; NaN con menos de 3 filas (con 2 puntos siempre da ±1) o valores constantes."""
    return d["lluvia_total_mm"].corr(d["declaratorias"]) if len(d) >= 3 else float("nan")


def rango(d):
    """Texto con las temporadas presentes en d: "2024" o "2022–2025"."""
    ini, fin = d["temporada"].min(), d["temporada"].max()
    return str(ini) if ini == fin else f"{ini}–{fin}"


numero_figura = count(1)


def mostrar_figura(titulo, fig, descripcion, alto, nota=None, lectura=None):
    """Título-conclusión arriba, figura sin título interno, "Figura N." y fuente debajo, y la lectura al final."""
    st.markdown(f"### {titulo}")
    fig.update_layout(title=None, template="plotly_white", height=alto, font_color=NAVY)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Figura {next(numero_figura)}. {descripcion}")
    st.caption(FUENTE + (f" {nota}" if nota else ""))
    if lectura:
        st.info(f"Lo que significa: {lectura}")


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
sel_lluvia = st.sidebar.slider(
    "Mostrar registros con lluvia entre (mm)", lluvia_min, lluvia_max, (lluvia_min, lluvia_max),
    help="Filtra registros de departamento y temporada, no departamentos completos: un departamento puede "
         "quedar solo con las temporadas cuya lluvia en la capital cae dentro del rango.")

sel_depto = st.sidebar.multiselect("Departamentos (vacío = todos)", sorted(df["departamento"].unique()))

nombre_metrica = st.sidebar.selectbox("Variable que se pinta en el mapa", list(METRICAS_MAPA))
col_metrica = METRICAS_MAPA[nombre_metrica]

# ---------------------------------------------------------------- Filtrado
# La pestaña Evolución compara temporadas, así que usa todos los filtros menos el de temporada
sin_filtro_temporada = df[df["lluvia_total_mm"].between(*sel_lluvia)]
if sel_depto:
    sin_filtro_temporada = sin_filtro_temporada[sin_filtro_temporada["departamento"].isin(sel_depto)]
filtrado = sin_filtro_temporada[sin_filtro_temporada["temporada"].isin(sel_temporadas)]

# ---------------------------------------------------------------- Encabezado
st.title("Perú: emergencias por lluvias, temporadas enero–mayo 2022–2025")
st.markdown("#### ¿El Estado declara emergencia donde más llueve?")
st.caption("Cruzamos las declaratorias de emergencia por lluvias (PCM) con la lluvia acumulada en la capital "
           "de cada uno de los 25 departamentos.")

if filtrado.empty:
    st.warning("Ningún departamento cumple los filtros elegidos. Amplía las temporadas o el rango de lluvia.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Declaratorias", f"{filtrado['declaratorias'].sum():,}", border=True)
c2.metric("Prórrogas", f"{filtrado['prorrogas'].sum():,}", border=True)
c3.metric("Lluvia promedio por registro (mm)", f"{filtrado['lluvia_total_mm'].mean():,.0f}", border=True,
          help="Promedio de la lluvia acumulada ene–may en la capital, entre los registros (departamento y "
               "temporada) que cumplen los filtros.")
c4.metric("Días de lluvia fuerte", f"{filtrado['dias_lluvia_fuerte'].sum():,}", border=True,
          help="Suma de los días con 20 mm o más en la capital, en los registros filtrados.")

corr = correlacion(filtrado)
if pd.isna(corr):
    lectura_rapida = (f"con {len(filtrado)} registro{'' if len(filtrado) == 1 else 's'} no se calcula la correlación lluvia–declaratorias "
                      "(hacen falta al menos 3 con valores distintos).")
else:
    grado = "poco" if abs(corr) < 0.3 else "moderadamente" if abs(corr) < 0.6 else "bastante"
    sentido = "" if abs(corr) < 0.3 else (" (más lluvia va con más declaratorias)" if corr > 0
                                          else " (más lluvia va con menos declaratorias)")
    lectura_rapida = f"con estos filtros, la lluvia y las declaratorias se relacionan {grado}{sentido}: r = {corr:.2f}."
st.info(f"**Lectura rápida:** {lectura_rapida} La lluvia se mide en la capital de cada departamento, "
        "no en todo su territorio.")

# Una fila por departamento (suma de declaratorias; promedio de lluvia por temporada)
por_depto = (filtrado.groupby(["ubigeo", "departamento"], as_index=False)
             .agg(lluvia_promedio_mm=("lluvia_total_mm", "mean"),
                  dias_lluvia_fuerte=("dias_lluvia_fuerte", "sum"),
                  declaratorias=("declaratorias", "sum"),
                  prorrogas=("prorrogas", "sum"))
             .round({"lluvia_promedio_mm": 1}))

tab_evol, tab_disp, tab_mapa, tab_prorr, tab_datos = st.tabs(
    ["Evolución", "Lluvia vs emergencias", "Mapa", "Prórrogas", "Datos"])

# ---------------------------------------------------------------- Evolución
with tab_evol:
    por_temporada = (sin_filtro_temporada.groupby("temporada", as_index=False)
                     .agg(declaratorias=("declaratorias", "sum"), lluvia_promedio_mm=("lluvia_total_mm", "mean")))
    por_temporada["correlacion"] = [correlacion(g) for _, g in sin_filtro_temporada.groupby("temporada")]
    por_temporada = por_temporada.round({"lluvia_promedio_mm": 1, "correlacion": 2}).astype({"temporada": str})
    primera, ultima = por_temporada.iloc[0], por_temporada.iloc[-1]
    mas_lluvia = por_temporada.loc[por_temporada["lluvia_promedio_mm"].idxmax()]
    menos_lluvia = por_temporada.loc[por_temporada["lluvia_promedio_mm"].idxmin()]
    nota_evol = "Este gráfico ignora el filtro de temporada."

    if len(por_temporada) == 1:
        titulo_decl = f"En {primera['temporada']} hubo {primera['declaratorias']} declaratorias"
        titulo_lluvia = f"En {primera['temporada']} la lluvia promedio fue {primera['lluvia_promedio_mm']:.0f} mm"
    else:
        titulo_decl = (f"Las declaratorias pasaron de {primera['declaratorias']} en {primera['temporada']} "
                       f"a {ultima['declaratorias']} en {ultima['temporada']}")
        titulo_lluvia = (f"La temporada más lluviosa fue {mas_lluvia['temporada']} "
                         f"({mas_lluvia['lluvia_promedio_mm']:.0f} mm) y la más seca {menos_lluvia['temporada']} "
                         f"({menos_lluvia['lluvia_promedio_mm']:.0f} mm)")

    fig_decl = px.bar(por_temporada, x="temporada", y="declaratorias", text="declaratorias",
                      hover_data=["lluvia_promedio_mm", "correlacion"], labels=ETIQUETAS,
                      color_discrete_sequence=[EMERGENCIA])
    mostrar_figura(titulo_decl, fig_decl,
                   f"Declaratorias de emergencia por lluvias en cada temporada, temporadas {rango(sin_filtro_temporada)}",
                   400, nota_evol,
                   "compara la altura de cada barra con la lluvia promedio del gráfico siguiente. Si las "
                   "declaratorias cambian mucho más que la lluvia entre temporadas, influyen otros factores "
                   "además de la lluvia.")

    fig_lluvia = px.bar(por_temporada, x="temporada", y="lluvia_promedio_mm", text="lluvia_promedio_mm",
                        labels=ETIQUETAS, color_discrete_sequence=[LLUVIA])
    fig_lluvia.update_traces(texttemplate="%{y:.0f} mm")
    mostrar_figura(titulo_lluvia, fig_lluvia,
                   f"Lluvia promedio acumulada ene–may en las capitales, temporadas {rango(sin_filtro_temporada)}",
                   400, nota_evol)

# ---------------------------------------------------------------- Lluvia vs emergencias
with tab_disp:
    if pd.isna(corr):
        titulo_disp = "Con estos filtros hay muy pocos puntos para medir la relación"
    elif abs(corr) < 0.3:
        titulo_disp = f"Más lluvia no significa más declaratorias (r = {corr:.2f}, relación débil)"
    else:
        titulo_disp = (f"En esta selección, más lluvia se asocia a {'más' if corr > 0 else 'menos'} "
                       f"declaratorias (r = {corr:.2f})")
    fig_disp = px.scatter(
        filtrado.astype({"temporada": str}), x="lluvia_total_mm", y="declaratorias", color="temporada",
        hover_name="departamento", hover_data=["capital", "dias_lluvia_fuerte", "prorrogas"],
        category_orders={"temporada": [str(t) for t in temporadas]},
        color_discrete_sequence=ESCALA_LLUVIA[1:], labels=ETIQUETAS,
    )
    fig_disp.update_traces(marker=dict(size=10, line=dict(width=0.8, color=NAVY)))
    mostrar_figura(titulo_disp, fig_disp,
                   f"Lluvia en la capital y declaratorias, un punto por departamento y temporada, "
                   f"temporadas {rango(filtrado)}",
                   500, lectura="si la lluvia explicara las declaratorias, los puntos subirían de izquierda a "
                                "derecha; mientras más dispersos estén, más débil es esa relación.")

# ---------------------------------------------------------------- Mapa
with tab_mapa:
    lider = por_depto.loc[por_depto[col_metrica].idxmax()]
    if lider[col_metrica] == 0:
        titulo_mapa = f"Ningún departamento registra {nombre_metrica.lower()} con estos filtros"
    else:
        titulo_mapa = (f"{lider['departamento']} tiene el valor más alto de {nombre_metrica.lower()} "
                       f"({lider[col_metrica]:,.0f})")
    fig_mapa = px.choropleth_map(
        por_depto, geojson=geo, locations="ubigeo", featureidkey="properties.ubigeo",
        color=col_metrica,
        color_continuous_scale=ESCALA_LLUVIA if col_metrica == "lluvia_promedio_mm" else ESCALA_EMERGENCIA,
        hover_name="departamento",
        hover_data={"ubigeo": False, "declaratorias": True, "prorrogas": True, "lluvia_promedio_mm": True,
                    "dias_lluvia_fuerte": True},
        labels={**ETIQUETAS, col_metrica: nombre_metrica},
        map_style="carto-positron", center={"lat": -9.2, "lon": -75.0}, zoom=3.6, opacity=0.8,
    )
    fig_mapa.update_layout(margin=dict(l=0, r=0, t=10, b=0))

    # Reporte de cruce con el GeoJSON (lo que no cruzó se dice, no se oculta)
    sin_dato_en_mapa = sorted(set(df["departamento"]) - set(por_depto["departamento"]))
    nota_cruce = (
        f"Cruce tabla–GeoJSON por ubigeo (texto): {por_depto['ubigeo'].nunique()} de {len(geo['features'])} "
        f"polígonos con datos con los filtros actuales. "
        f"Polígonos sin ubigeo en la tabla: {', '.join(poligonos_sin_dato) or 'ninguno'}."
        + (f" Sin datos por los filtros: {len(sin_dato_en_mapa)} departamentos." if sin_dato_en_mapa else "")
    )
    mostrar_figura(titulo_mapa, fig_mapa,
                   f"{nombre_metrica} por departamento, temporadas {rango(filtrado)}", 640, nota_cruce,
                   "los tonos más oscuros marcan los departamentos con el valor más alto de la variable elegida "
                   "en esta selección. Cambia la variable en la barra lateral para comparar dónde llueve más con "
                   "dónde se declara emergencia.")

# ---------------------------------------------------------------- Prórrogas
with tab_prorr:
    con_prorrogas = por_depto[por_depto["prorrogas"] > 0]
    if con_prorrogas.empty:
        st.info("Ningún departamento tiene prórrogas con estos filtros.")
    else:
        # keep="all": si hay empate en el 10.º lugar se muestran todos, como en visualizacion.ipynb
        top_prorr = con_prorrogas.nlargest(10, "prorrogas", keep="all").sort_values("prorrogas")
        lider_prorr = top_prorr.iloc[-1]
        fig_prorr = px.bar(top_prorr, x="prorrogas", y="departamento", orientation="h", text="prorrogas",
                           hover_data=["declaratorias", "lluvia_promedio_mm"], labels=ETIQUETAS,
                           color_discrete_sequence=[EMERGENCIA])
        nota_empate = (f"Hay un empate en el 10.º lugar, por eso se muestran {len(top_prorr)} departamentos."
                       if len(top_prorr) > 10 else None)
        mostrar_figura(f"{lider_prorr['departamento']} acumula más prórrogas ({lider_prorr['prorrogas']})",
                       fig_prorr,
                       f"Departamentos con más prórrogas de emergencia (top 10), temporadas {rango(filtrado)}",
                       120 + 34 * len(top_prorr), nota_empate)

# ---------------------------------------------------------------- Datos
with tab_datos:
    tabla = (filtrado[["temporada", "ubigeo", "departamento", "capital", "lluvia_total_mm",
                       "dias_lluvia_fuerte", "declaratorias", "prorrogas"]]
             .sort_values(["temporada", "declaratorias"], ascending=[True, False]))
    st.dataframe(tabla, hide_index=True, width="stretch", column_config={
        "temporada": st.column_config.NumberColumn("Temporada", format="%d"),
        "ubigeo": st.column_config.TextColumn("Ubigeo"),
        "departamento": "Departamento", "capital": "Capital",
        "lluvia_total_mm": st.column_config.NumberColumn("Lluvia ene–may (mm)", format="%.1f"),
        "dias_lluvia_fuerte": st.column_config.NumberColumn("Días ≥ 20 mm"),
        "declaratorias": st.column_config.NumberColumn("Declaratorias"),
        "prorrogas": st.column_config.NumberColumn("Prórrogas"),
    })
    st.download_button("Descargar la tabla filtrada (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                       file_name="datos_filtrados.csv", mime="text/csv")
    with st.expander("Cómo leer estos datos"):
        st.markdown(
            "- La lluvia se mide en la **capital** de cada departamento, no en todo su territorio.\n"
            "- Muchas declaratorias son **preventivas**: no dependen solo de la lluvia observada.\n"
            "- Con **pocos registros** la correlación no es confiable."
        )
    st.caption(FUENTE)
