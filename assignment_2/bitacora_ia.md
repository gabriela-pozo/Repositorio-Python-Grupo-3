# Bitácora de IA

 **Grupo 3** · Temporada: 1 de enero al 31 de mayo de 2024.

En esta bitácora registramos momentos en que la IA nos dio algo **incorrecto, incompleto o que no funcionó**, cómo nos dimos cuenta y cómo lo corregimos.

**Herramienta usada:** Claude (Claude Code)

---

## Entrada 1 – Parte 1: el código no funcionó porque faltaba importar `time`

**1. ¿Qué le pedimos a la IA?**

Le pedimos continuar el scraping de los resultados correspondientes a abril de 2024, manteniendo una pausa entre consultas.

**2. ¿Qué nos respondió?**
La IA propuso el siguiente código:

```python
# Construye la URL de abril de 2024.
url_abril = url_base + "&desde=01-04-2024&hasta=30-04-2024"

# Espera dos segundos antes de realizar otra consulta.
time.sleep(2)

# Abre la búsqueda de abril.
navegador.get(url_abril)
```
**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

El código utilizaba `time.sleep(2)`, pero la biblioteca `time` no había sido importada previamente.
Al ejecutar la celda, Python devolvió:
`NameError: name 'time' is not defined`
Así comprobamos que el código proporcionado por la IA no podía ejecutarse tal como estaba escrito.

**4. ¿Cómo lo corregimos?**

Importamos primero la biblioteca `time`: `import time` 
Después volvimos a ejecutar la celda y `time.sleep(2)` funcionó correctamente.

---

## Entrada 2 – Parte 1: dos errores en los departamentos (paso 12)

**1. ¿Qué le pedimos a la IA?**

Que identificara qué departamentos menciona cada decreto, buscando por palabra completa como indica el enunciado.

**2. ¿Qué nos respondió?**
La IA propuso el siguiente código:

```python
def departamentos_en(titulo):
    # \b = límite de palabra: evita que "Ica" coincida dentro de "Huancavelica"
    return [d for d in departamentos if re.search(rf"\b{re.escape(d)}\b", titulo)]

```
**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

El `\b` evitaba el error de "Ica" dentro de "Huancavelica", pero dejaba pasar otros dos:
- El DS 049-2024-PCM dice *"provincia de Ucayali del departamento de Loreto"*, y el código lo contaba también para Ucayali.
- El DS 0012-2024-PCM escribe "Ancash" y "San Martin" sin tilde, y el código no los detectaba.

La celda de control de la IA solo buscaba algunos nombres sin tilde (no incluía "San Martin"), y su explicación decía que el DS 0012 menciona 5 departamentos, cuando son 7. Nos dimos cuenta al revisar los títulos de lluvias uno por uno contra la lista de departamentos de cada decreto.

**4. ¿Cómo lo corregimos?**

Quitamos las tildes del título y del nombre antes de comparar (`unicodedata`). Además, dejamos de contar un nombre cuando va justo después de "provincia de" o "distrito de". Agregamos una tabla que compara nuestro método con los métodos simples. El conteo cambió: Áncash pasó de 4 a 5 declaratorias, San Martín de 2 a 3 y Ucayali de 4 a 3.

---

## Entrada 3 – Parte 1: error al contar por departamento (paso 13)

**1. ¿Qué le pedimos a la IA?**

Que armara la tabla `decretos_por_departamento.csv`.

**2. ¿Qué nos respondió?**
La IA propuso el siguiente código:

```python
exp = lluvias.explode("departamentos")
conteo = pd.crosstab(exp["departamentos"], exp["tipo"])
```
**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

Al ejecutar la celda salió `ValueError: cannot reindex on an axis with duplicate labels`. Con `print(exp.index)` vimos la causa: `explode` repite el índice de cada decreto (0, 1, 1, 1…), y `crosstab` no acepta índices repetidos.

**4. ¿Cómo lo corregimos?**

Reiniciamos el índice después de `lluvias.explode("departamentos").reset_index(drop=True)`. Además, agregamos dos controles con `assert` para que la tabla tenga 25 departamentos y que el total coincida con las menciones de cada decreto.

---

## Entrada 4 – Parte 2: el código asumía que la carpeta `datos/` ya existía

**1. ¿Qué le pedimos a la IA?**

Le pedimos el código para el paso 8: guardar la tabla final en `datos/lluvias_por_departamento.csv` con las columnas `departamento`, `capital`, `latitud`, `longitud`, `lluvia_total_mm` y `dias_lluvia_fuerte`.

**2. ¿Qué nos respondió?**

```python
assert len(final) == 25
final.to_csv("datos/lluvias_por_departamento.csv", index=False, encoding="utf-8-sig")
pd.read_csv("datos/lluvias_por_departamento.csv")
```

**3. ¿Qué estaba mal y cómo nos dimos cuenta?**

El código guardaba el CSV dentro de `datos/` sin comprobar que esa carpeta existiera. En nuestro repositorio todavía no existía, porque los CSV de la Parte 1 estaban en un pull request que aún no se había aceptado. Al ejecutar la celda, Python mostró este error:

```text
OSError: Cannot save file into a non-existent directory: 'datos'
```

Nos dimos cuenta lo que estaba mal porque `to_csv` no crea carpetas: solo guarda archivos en carpetas que ya existen. La IA había probado el código en una carpeta donde `datos/` sí existía, por eso a ella le funcionó y a nosotros no.

**4. ¿Cómo lo corregimos?**

Creamos la carpeta `assignment_2/datos/` desde VS Code y volvimos a ejecutar la celda. Comprobamos que el archivo `datos/lluvias_por_departamento.csv` apareciera y tuviera 25 filas. Como Git guarda archivos y no carpetas, cuando se aceptó el pull request de la Parte 1 todos los CSV quedaron juntos en la misma carpeta `datos/`, sin conflictos.
