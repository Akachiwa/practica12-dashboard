# Practica 12 – Dashboard de asteroides (NASA NeoWs) en Streamlit

Herramientas de Visualizacion · Unidad II · Grupo IDIA222
Alumna: Amayrani Guadalupe Perusquia Gutierrez

Dashboard interactivo de los asteroides que pasaron cerca de la Tierra entre julio y septiembre de 2026,
con datos de la API **NASA NeoWs** (https://api.nasa.gov).

## Que responde
| Pestana | Pregunta |
|---|---|
| 1 · Distribucion | ¿Como se reparten los tamanos? ¿Hay casos extremos? |
| 2 · Comparacion | ¿Que grupo de tamano pasa mas rapido? |
| 3 · Relacion | ¿Los mas grandes pasan mas lejos o mas cerca? |
| 4 · Evolucion | ¿Cuantos pasan cada dia y como cambia? |

Filtros en la barra lateral: fechas, grupo de tamano y solo peligrosos. Tabla descargable en CSV.

## Como correrlo
```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "TU_LLAVE_DE_40_CARACTERES" > token.txt   # o export NASA_TOKEN=...
streamlit run app.py
```
La primera vez consulta la API (13 peticiones) y guarda `respuesta.json`; despues lo reutiliza sin gastar peticiones.

## Archivos
- `app.py` – dashboard de Streamlit
- `practica12.py` – lectura del token, peticiones, limpieza y graficas (Practica 12)
- `ficha_api.txt` – ficha de la API
- `evidencias/` – capturas del funcionamiento

**Seguridad:** el token no esta en el repositorio (`token.txt` y `.streamlit/secrets.toml` estan en `.gitignore`),
y `respuesta.json` se guarda sin las ligas que traen el `api_key`.

## Evidencias
![Inicio](evidencias/1_inicio.png)
![Distribucion](evidencias/2_distribucion.png)
![Comparacion](evidencias/3_comparacion.png)
![Relacion](evidencias/4_relacion.png)
![Evolucion](evidencias/5_evolucion.png)
