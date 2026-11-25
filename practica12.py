# Practica 12 - Tu API
# Herramientas de Visualizacion - Unidad II
# Alumna: Amayrani Guadalupe Perusquia Gutierrez
#
# API: NASA NeoWs (Near Earth Object Web Service)
# Datos: asteroides que pasaron cerca de la Tierra de julio a septiembre 2026
#
# El token NO esta en este archivo. Se lee de token.txt o de la
# variable de entorno NASA_TOKEN.

import os
import json
import time
from datetime import date, timedelta

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------- configuracion ----------------
URL_BASE = "https://api.nasa.gov/neo/rest/v1/feed"
ARCHIVO_TOKEN = "token.txt"
ARCHIVO_JSON = "respuesta.json"
CARPETA_GRAFICAS = "graficas"

# 13 semanas (la API solo deja pedir 7 dias por peticion)
# con 4 semanas solo salian 145 registros, por eso pido mas
FECHA_INICIO = date(2026, 7, 1)
SEMANAS = 13

# paleta del curso
GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
CUALI = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]


# =============== 1. leer y validar el token ===============
def leer_token():
    token = os.environ.get("NASA_TOKEN", "").strip()
    origen = "variable de entorno NASA_TOKEN"

    if token == "":
        if not os.path.exists(ARCHIVO_TOKEN):
            print("ERROR: no encontre el token.")
            print("Crea el archivo", ARCHIVO_TOKEN, "con tu llave de la NASA")
            print("o define la variable de entorno NASA_TOKEN.")
            raise SystemExit(1)
        with open(ARCHIVO_TOKEN, "r", encoding="utf-8") as f:
            token = f.read().strip()
        origen = ARCHIVO_TOKEN

    if token == "":
        print("ERROR: el token esta vacio (" + origen + ").")
        raise SystemExit(1)

    if token == "DEMO_KEY":
        print("ERROR: estas usando DEMO_KEY, usa tu propia llave.")
        raise SystemExit(1)

    # las llaves de api.nasa.gov tienen 40 caracteres, solo letras y numeros
    if len(token) != 40:
        print("ERROR: el token tiene", len(token), "caracteres y deberia tener 40.")
        print("Seguramente se copio incompleto, revisalo en", origen)
        raise SystemExit(1)
    if not token.isalnum():
        print("ERROR: el token tiene caracteres raros (espacios, comillas, etc).")
        raise SystemExit(1)

    # nunca se imprime el token completo
    print("Token leido de", origen, "-> ok (" + token[:4] + "...)")
    return token


# =============== 2 y 3. pedir a la API y revisar ===============
def quitar_links(obj):
    """La NASA regresa ligas que traen el api_key pegado.
    Las quito para que el token no quede guardado en respuesta.json"""
    if isinstance(obj, dict):
        return {k: quitar_links(v) for k, v in obj.items() if k != "links"}
    if isinstance(obj, list):
        return [quitar_links(x) for x in obj]
    return obj


def buscar_token(obj, token, ruta="datos"):
    """Regresa las rutas del JSON donde aparece el token (sin imprimir el token)"""
    encontrados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            encontrados += buscar_token(v, token, ruta + "[" + repr(k) + "]")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            encontrados += buscar_token(v, token, ruta + "[" + str(i) + "]")
    elif isinstance(obj, str) and token in obj:
        encontrados.append(ruta)
    return encontrados


def pedir_semana(token, inicio, fin):
    parametros = {
        "start_date": inicio.isoformat(),
        "end_date": fin.isoformat(),
        "api_key": token,
    }
    try:
        respuesta = requests.get(URL_BASE, params=parametros, timeout=30)
    except requests.exceptions.RequestException as e:
        print("ERROR de conexion:", type(e).__name__)
        print("Revisa tu internet. Si ya tienes respuesta.json no hace falta red.")
        raise SystemExit(1)

    codigo = respuesta.status_code
    print("  ", inicio, "a", fin, "-> codigo", codigo)

    # revisar el codigo de estado ANTES de leer nada
    if codigo in (401, 403):
        print("ERROR", codigo, ": el token no sirve (invalido o no activado).")
        print("Revisa que copiaste bien la llave que te llego al correo.")
        raise SystemExit(1)
    if codigo == 400:
        print("ERROR 400: la peticion esta mal hecha (fechas o parametros).")
        print("La API solo acepta rangos de maximo 7 dias.")
        print(respuesta.text[:300].replace(token, "****"))
        raise SystemExit(1)
    if codigo == 429:
        print("ERROR 429: te pasaste del limite de peticiones (1000 por hora).")
        print("Espera una hora antes de volver a correr el programa.")
        raise SystemExit(1)
    if codigo != 200:
        print("ERROR: codigo inesperado", codigo)
        print(respuesta.text[:300].replace(token, "****"))
        raise SystemExit(1)

    # un 200 no garantiza que sea JSON
    if "json" not in (respuesta.headers.get("Content-Type") or ""):
        print("ERROR: la respuesta no es JSON. Esto llego:")
        print(respuesta.text[:300])
        raise SystemExit(1)

    restantes = respuesta.headers.get("X-RateLimit-Remaining")
    if restantes is not None:
        print("     peticiones restantes esta hora:", restantes)

    return respuesta.json()


# =============== 4. guardar o reutilizar la respuesta ===============
def obtener_datos():
    if os.path.exists(ARCHIVO_JSON):
        print("Ya existe", ARCHIVO_JSON, "-> lo leo y NO consulto la API")
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)

    print("No existe", ARCHIVO_JSON, "-> consulto la API de la NASA")
    token = leer_token()

    todo = {"element_count": 0, "near_earth_objects": {}}
    for i in range(SEMANAS):
        inicio = FECHA_INICIO + timedelta(days=7 * i)
        fin = inicio + timedelta(days=6)
        datos = pedir_semana(token, inicio, fin)
        todo["element_count"] += datos.get("element_count", 0)
        todo["near_earth_objects"].update(datos["near_earth_objects"])
        time.sleep(1)  # para no saturar la API

    todo = quitar_links(todo)

    # revision extra: que el token no se haya colado en otra parte
    texto = json.dumps(todo)
    if token in texto:
        lugares = buscar_token(todo, token)
        print("AVISO: el token venia en", len(lugares), "lugares de la respuesta, por ejemplo:")
        for lugar in lugares[:5]:
            print("   ", lugar)
        texto = texto.replace(token, "TOKEN_OCULTO")
        todo = json.loads(texto)
        print("Lo reemplace por TOKEN_OCULTO antes de guardar.")

    if token in json.dumps(todo):
        print("ERROR: el token sigue en la respuesta, no la guardo.")
        raise SystemExit(1)
    print("Revision de seguridad: el token NO esta en respuesta.json")

    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(todo, f, indent=2)
    print("Respuesta guardada en", ARCHIVO_JSON)
    return todo


# =============== armar la tabla ===============
def json_a_tabla(datos):
    # la tabla vive en datos["near_earth_objects"]["AAAA-MM-DD"] -> lista
    renglones = []
    for dia, lista in datos["near_earth_objects"].items():
        for ast in lista:
            acercamiento = ast["close_approach_data"][0]
            metros = ast["estimated_diameter"]["meters"]
            renglones.append({
                "nombre": ast.get("name"),
                "fecha": acercamiento.get("close_approach_date"),
                "magnitud_h": ast.get("absolute_magnitude_h"),
                "diam_min_m": metros.get("estimated_diameter_min"),
                "diam_max_m": metros.get("estimated_diameter_max"),
                "peligroso": ast.get("is_potentially_hazardous_asteroid"),
                # estas dos llegan como TEXTO desde la API
                "velocidad_kms": acercamiento["relative_velocity"].get("kilometers_per_second"),
                "distancia_lunar": acercamiento["miss_distance"].get("lunar"),
            })
    return pd.DataFrame(renglones)


# =============== 5. limpieza documentada ===============
def limpiar(df):
    print("\n========== LIMPIEZA ==========")
    print("Registros recibidos:", len(df))
    print("\nTipos de dato al cargar:")
    print(df.dtypes.to_string())
    print("\nFaltantes por columna (antes de convertir):")
    print(df.isna().sum().to_string())

    # columnas que llegan como texto y deben ser numero
    for col in ["velocidad_kms", "distancia_lunar", "magnitud_h", "diam_min_m", "diam_max_m"]:
        antes = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        perdidos = antes - df[col].notna().sum()
        print(f"Converti {col} a numero -> se perdieron {perdidos} valores")

    antes = df["fecha"].notna().sum()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    print("Converti fecha a datetime -> se perdieron", antes - df["fecha"].notna().sum(), "valores")

    df["peligroso"] = df["peligroso"].astype("boolean")

    # columna nueva: diametro promedio y grupo de tamano
    df["diametro_m"] = (df["diam_min_m"] + df["diam_max_m"]) / 2
    df["tamano"] = pd.cut(df["diametro_m"],
                          bins=[0, 50, 150, 500, np.inf],
                          labels=["< 50 m", "50 - 150 m", "150 - 500 m", "> 500 m"])

    print("\nTipos de dato despues de limpiar:")
    print(df.dtypes.to_string())
    print("\nFaltantes por columna (despues de convertir):")
    print(df.isna().sum().to_string())

    duplicados = df.duplicated(subset=["nombre", "fecha"]).sum()
    df = df.drop_duplicates(subset=["nombre", "fecha"])
    print("\nDuplicados quitados:", duplicados)

    df = df.dropna(subset=["fecha", "diametro_m", "velocidad_kms", "distancia_lunar"])
    print("Registros utilizables:", len(df))
    if len(df) < 200:
        print("AVISO: quedaron menos de 200 registros")
    print("==============================\n")
    return df


# =============== 6. graficas ===============
def estilo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def grafica_distribucion(df):
    # Pregunta: como se reparten los tamanos de los asteroides?
    mediana = df["diametro_m"].median()
    grandes = (df["diametro_m"] > 1000).sum()

    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.logspace(np.log10(df["diametro_m"].min()), np.log10(df["diametro_m"].max()), 30)
    ax.hist(df["diametro_m"], bins=bins, color=GRIS, edgecolor="white")
    ax.axvline(mediana, color=AZUL, linewidth=2)
    ax.text(mediana * 1.1, ax.get_ylim()[1] * 0.9, f"mediana: {mediana:.0f} m", color=AZUL)
    ax.set_xscale("log")
    ax.set_title(f"La mitad de los asteroides mide menos de {mediana:.0f} m; "
                 f"solo {grandes} superan 1 km", loc="left")
    ax.set_xlabel("Diametro estimado (metros, escala logaritmica)")
    ax.set_ylabel("Numero de asteroides")
    estilo(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETA_GRAFICAS, "1_distribucion.png"), dpi=150)
    plt.show()


def grafica_comparacion(df):
    # Pregunta: que tan rapido pasan segun su tamano?
    vel = df.groupby("tamano", observed=False)["velocidad_kms"].median()
    conteo = df["tamano"].value_counts().reindex(vel.index)
    mas_rapido = vel.idxmax()
    mas_lento = vel.idxmin()

    colores = [AZUL if g == mas_rapido else GRIS for g in vel.index]
    fig, ax = plt.subplots(figsize=(9, 5))
    barras = ax.bar(vel.index.astype(str), vel.values, color=colores)
    for b, v, n in zip(barras, vel.values, conteo.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}\n(n={n})",
                ha="center", va="bottom", fontsize=9)
    ax.set_title(f"Los asteroides de {mas_rapido} pasan mas rapido "
                 f"({vel.max():.1f} km/s) que los de {mas_lento} ({vel.min():.1f} km/s)",
                 loc="left")
    ax.set_xlabel("Tamano del asteroide (diametro estimado)")
    ax.set_ylabel("Velocidad mediana (km/s)")
    ax.set_ylim(0, vel.max() * 1.25)
    estilo(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETA_GRAFICAS, "2_comparacion.png"), dpi=150)
    plt.show()


def grafica_relacion(df):
    # Pregunta: los asteroides mas grandes pasan mas lejos o mas cerca?
    # Spearman = correlacion de los rangos (asi no se necesita scipy)
    r = df["diametro_m"].rank().corr(df["distancia_lunar"].rank())
    if r > 0.2:
        titulo = "Los asteroides mas grandes tienden a pasar mas lejos de la Tierra"
    elif r < -0.2:
        titulo = "Los asteroides mas grandes tienden a pasar mas cerca de la Tierra"
    else:
        titulo = "El tamano de un asteroide no dice que tan cerca va a pasar"

    normal = df[df["peligroso"] == False]
    peligro = df[df["peligroso"] == True]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(normal["diametro_m"], normal["distancia_lunar"], s=15, color=GRIS,
               alpha=0.8, label="No peligroso")
    ax.scatter(peligro["diametro_m"], peligro["distancia_lunar"], s=25, color=AZUL,
               label="Potencialmente peligroso (NASA)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(titulo + f"  (Spearman r = {r:.2f})", loc="left")
    ax.set_xlabel("Diametro estimado (metros, escala log)")
    ax.set_ylabel("Distancia minima a la Tierra\n(distancias lunares, escala log)")
    ax.legend(frameon=False)
    estilo(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETA_GRAFICAS, "3_relacion.png"), dpi=150)
    plt.show()
    return r


def grafica_evolucion(df):
    # Pregunta: cuantos asteroides pasan cada dia y cambia con el tiempo?
    por_dia = df.groupby("fecha").size()
    promedio = por_dia.mean()
    dia_max = por_dia.idxmax()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(por_dia.index, por_dia.values, color=GRIS, marker="o", markersize=4)
    ax.axhline(promedio, color=AZUL, linestyle="--", linewidth=1.5)
    ax.text(por_dia.index[0], promedio + 0.5, f"promedio: {promedio:.1f} por dia", color=AZUL)
    ax.scatter([dia_max], [por_dia.max()], color=AZUL, s=50, zorder=3)
    ax.annotate(f"maximo: {por_dia.max()} ({dia_max:%d/%m})", (dia_max, por_dia.max()),
                textcoords="offset points", xytext=(5, 5), color=AZUL)
    ax.set_title(f"Cada dia pasan en promedio {promedio:.0f} asteroides cerca de la Tierra, "
                 f"entre {por_dia.min()} y {por_dia.max()}", loc="left")
    ax.set_xlabel("Fecha de acercamiento (julio a septiembre 2026)")
    ax.set_ylabel("Asteroides por dia")
    ax.set_ylim(0, por_dia.max() * 1.2)
    estilo(ax)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETA_GRAFICAS, "4_evolucion.png"), dpi=150)
    plt.show()


# =============== programa principal ===============
if __name__ == "__main__":
    os.makedirs(CARPETA_GRAFICAS, exist_ok=True)

    datos = obtener_datos()
    print("element_count reportado por la API:", datos.get("element_count"))

    df = json_a_tabla(datos)
    df = limpiar(df)

    print("Resumen numerico:")
    print(df[["diametro_m", "velocidad_kms", "distancia_lunar", "magnitud_h"]].describe().round(2))
    print("\nAsteroides por grupo de tamano:")
    print(df["tamano"].value_counts().sort_index().to_string())
    print("\nPotencialmente peligrosos:", int(df["peligroso"].sum()), "de", len(df))

    grafica_distribucion(df)
    grafica_comparacion(df)
    r = grafica_relacion(df)
    grafica_evolucion(df)

    print("\nCorrelacion de Spearman diametro vs distancia:", round(r, 2))
    print("Listo. Graficas guardadas en la carpeta", CARPETA_GRAFICAS)
