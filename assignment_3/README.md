# Assignment 3 – Lluvias y declaratorias de emergencia en el Perú (2022-2025)

**Dashboard público:** PENDIENTE – pegar aquí el enlace `https://....streamlit.app` una vez desplegado.

## 1. ¿De qué trata la aplicación? (pregunta)

¿El Estado declara emergencia donde más llueve? ¿Cambió esa relación entre las temporadas de lluvias
(enero–mayo) de 2022, 2023, 2024 y 2025? La app cruza la lluvia acumulada en la capital de cada
departamento con el número de decretos supremos que declaran emergencia por lluvias, y permite
filtrar por temporada, rango de lluvia y departamento.

## 2. ¿De dónde provienen los datos?

- `datos/tabla_final_2022_2025.csv`: 25 departamentos × 4 temporadas = 100 filas. Es la tabla del
  Assignment 2 (temporada 2024) unida con las tablas de las temporadas 2022, 2023 y 2025 que
  trabajaron otros grupos con el mismo método.
  - **Declaratorias y prórrogas:** decretos supremos de la PCM publicados en gob.pe.
  - **Lluvia:** precipitación diaria en la capital de cada departamento, de Open-Meteo.
  - **Ubigeo:** código INEI de 2 dígitos, leído siempre como texto.
- `datos/departamentos_peru.geojson`: polígonos departamentales (solo traen el nombre; el ubigeo se
  agrega por nombre normalizado y el cruce con la tabla se reporta al pie del mapa).

## 3. Dos hallazgos

1. **La lluvia no explica dónde se declara emergencia.** La correlación entre lluvia y declaratorias
   está entre -0.22 y 0.20 en las cuatro temporadas. Loreto es el departamento más lluvioso
   (1,642 mm promedio por temporada) y acumula 12 declaratorias; Lima, con unos 42 mm, acumula 20.
2. **Las declaratorias se concentran en la sierra y en Lima, y crecieron cada año.** Ayacucho (21),
   Lima (20), Arequipa y Áncash (19) lideran el total. A nivel nacional se pasó de 3 declaratorias en
   2022 a 72 en 2023, 99 en 2024 y 157 en 2025, mientras la lluvia promedio subió y bajó.

## 4. Limitaciones

- **2022 tiene solo 3 declaratorias** (un único decreto de lluvias, el D.S. 032-2022-PCM), verificado
  por los cuatro grupos que trabajaron esa temporada. Aporta poco a la comparación.
- **La lluvia se mide en un solo punto** (la capital). En departamentos grandes o con costa, sierra y
  selva, como Lima, no representa lo que llovió en los distritos afectados.
- **Se cuenta por departamento, no por distrito:** un decreto con 2 distritos pesa igual que uno con 200.
- **Los datos dependen del buscador de gob.pe** y de decisiones de cada grupo (por ejemplo, Lima 2023
  tiene 6 declaratorias en nuestra tabla y 7 en la de otros grupos).

## Cómo correrla en local

Desde la carpeta `assignment_3/`:

```
uv run streamlit run app.py
```

(o `pip install -r requirements.txt` y luego `streamlit run app.py`).

## Archivos

| Archivo | Contenido |
|---|---|
| `visualizacion.ipynb` | Parte 1: gráficos con Plotly Express |
| `mapas.ipynb` | Parte 2: mapas con Geopandas y Folium |
| `app.py` | Parte 3: dashboard en Streamlit |
| `datos/` | Tabla y GeoJSON que usa todo lo anterior |
