# Dashboard Streamlit - Practica 12 (NASA NeoWs)
# Herramientas de Visualizacion - Unidad II - Grupo IDIA222
#
# Reutiliza las funciones de practica12.py (token, peticiones, limpieza).
# Correr con:  streamlit run app.py

import os
import json

import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

import practica12 as p12

AZUL = p12.AZUL
GRIS = p12.GRIS
ORDEN_TAMANO = ["< 50 m", "50 - 150 m", "150 - 500 m", "> 500 m"]

st.set_page_config(page_title="Asteroides cerca de la Tierra", page_icon="☄️", layout="wide")


# ---------------- datos ----------------
@st.cache_data(show_spinner="Consultando la API de la NASA (13 semanas)...")
def cargar_datos():
    # si existe respuesta.json se usa sin gastar peticiones; si no, consulta la API
    try:
        datos = p12.obtener_datos()
    except SystemExit:
        return None
    df = p12.json_a_tabla(datos)
    df = p12.limpiar(df)
    df["tamano"] = df["tamano"].astype(str)
    df["peligroso_txt"] = df["peligroso"].map({True: "Potencialmente peligroso", False: "No peligroso"})
    return df


# Si el token esta en .streamlit/secrets.toml lo pasamos como variable de entorno
try:
    if "NASA_TOKEN" in st.secrets and not os.environ.get("NASA_TOKEN"):
        os.environ["NASA_TOKEN"] = st.secrets["NASA_TOKEN"]
except Exception:
    pass  # no hay secrets.toml, se usa token.txt o la variable de entorno

df_total = cargar_datos()

st.title("☄️ Asteroides que pasan cerca de la Tierra")
st.caption("Fuente: NASA NeoWs (api.nasa.gov) · julio a septiembre 2026 · "
           "Herramientas de Visualizacion, Unidad II, IDIA222")

if df_total is None or df_total.empty:
    st.error("No pude obtener los datos. Revisa la terminal: falta el token "
             "(token.txt, NASA_TOKEN o .streamlit/secrets.toml) o hubo un error de la API.")
    st.stop()

# ---------------- filtros ----------------
with st.sidebar:
    st.header("Filtros")
    fmin, fmax = df_total["fecha"].min().date(), df_total["fecha"].max().date()
    rango = st.date_input("Rango de fechas", (fmin, fmax), min_value=fmin, max_value=fmax)
    tamanos = st.multiselect("Grupo de tamano", ORDEN_TAMANO, default=ORDEN_TAMANO)
    solo_peligrosos = st.toggle("Solo potencialmente peligrosos", value=False)
    if st.button("Recargar datos"):
        st.cache_data.clear()
        st.rerun()

df = df_total[df_total["tamano"].isin(tamanos)]
if isinstance(rango, tuple) and len(rango) == 2:
    df = df[(df["fecha"].dt.date >= rango[0]) & (df["fecha"].dt.date <= rango[1])]
if solo_peligrosos:
    df = df[df["peligroso"] == True]

if df.empty:
    st.warning("Ningun asteroide cumple con los filtros.")
    st.stop()

# ---------------- KPIs ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Asteroides", f"{len(df):,}")
c2.metric("Potencialmente peligrosos", int(df["peligroso"].sum()),
          f"{df['peligroso'].mean() * 100:.1f}% del total", delta_color="off")
c3.metric("Diametro mediano", f"{df['diametro_m'].median():.0f} m")
c4.metric("Paso mas cercano", f"{df['distancia_lunar'].min():.2f} dist. lunares")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1 · Distribucion", "2 · Comparacion", "3 · Relacion", "4 · Evolucion", "Datos"])

# G1 - Distribucion
with tab1:
    mediana = df["diametro_m"].median()
    st.subheader(f"La mitad de los asteroides mide menos de {mediana:.0f} m")
    base = df.assign(log_d=df["diametro_m"].apply(lambda x: np.log10(x)))
    hist = alt.Chart(base).mark_bar(color=GRIS).encode(
        x=alt.X("log_d:Q", bin=alt.Bin(maxbins=30), title="Diametro estimado (log10 de metros)"),
        y=alt.Y("count()", title="Numero de asteroides"),
        tooltip=[alt.Tooltip("count()", title="Asteroides")])
    regla = alt.Chart(pd.DataFrame({"m": [np.log10(mediana)]})).mark_rule(
        color=AZUL, size=2).encode(x="m:Q")
    st.altair_chart(hist + regla, use_container_width=True)
    st.caption(f"Linea azul = mediana ({mediana:.0f} m). "
               f"{(df['diametro_m'] > 1000).sum()} asteroides superan 1 km. "
               "Eje en log10: 1 = 10 m, 2 = 100 m, 3 = 1 km.")

# G2 - Comparacion
with tab2:
    vel = (df.groupby("tamano")["velocidad_kms"].agg(["median", "count"])
           .reindex([t for t in ORDEN_TAMANO if t in df["tamano"].unique()]).reset_index())
    rapido = vel.loc[vel["median"].idxmax(), "tamano"]
    st.subheader(f"Los asteroides de {rapido} pasan mas rapido")
    vel["destacado"] = vel["tamano"] == rapido
    barras = alt.Chart(vel).mark_bar().encode(
        x=alt.X("tamano:N", sort=ORDEN_TAMANO, title="Grupo de tamano"),
        y=alt.Y("median:Q", title="Velocidad mediana (km/s)"),
        color=alt.condition("datum.destacado", alt.value(AZUL), alt.value(GRIS)),
        tooltip=["tamano", alt.Tooltip("median:Q", format=".1f", title="km/s"),
                 alt.Tooltip("count:Q", title="n")])
    etiquetas = barras.mark_text(dy=-8).encode(text=alt.Text("median:Q", format=".1f"),
                                               color=alt.value("black"))
    st.altair_chart(barras + etiquetas, use_container_width=True)

# G3 - Relacion
with tab3:
    r = df["diametro_m"].rank().corr(df["distancia_lunar"].rank())
    if r > 0.2:
        titulo = "Los mas grandes tienden a pasar mas lejos"
    elif r < -0.2:
        titulo = "Los mas grandes tienden a pasar mas cerca"
    else:
        titulo = "El tamano no dice que tan cerca va a pasar"
    st.subheader(f"{titulo} (Spearman r = {r:.2f})")
    disp = alt.Chart(df).mark_circle(opacity=0.7).encode(
        x=alt.X("diametro_m:Q", scale=alt.Scale(type="log"), title="Diametro (m, log)"),
        y=alt.Y("distancia_lunar:Q", scale=alt.Scale(type="log"),
                title="Distancia minima (distancias lunares, log)"),
        color=alt.Color("peligroso_txt:N", title="",
                        scale=alt.Scale(domain=["No peligroso", "Potencialmente peligroso"],
                                        range=[GRIS, AZUL])),
        size=alt.condition("datum.peligroso", alt.value(45), alt.value(20)),
        tooltip=["nombre", alt.Tooltip("fecha:T", format="%d/%m/%Y"),
                 alt.Tooltip("diametro_m:Q", format=".0f"),
                 alt.Tooltip("distancia_lunar:Q", format=".2f"),
                 alt.Tooltip("velocidad_kms:Q", format=".1f")]).interactive()
    st.altair_chart(disp, use_container_width=True)

# G4 - Evolucion
with tab4:
    por_dia = df.groupby("fecha").size().reset_index(name="asteroides")
    prom = por_dia["asteroides"].mean()
    st.subheader(f"Cada dia pasan en promedio {prom:.0f} asteroides "
                 f"(entre {por_dia['asteroides'].min()} y {por_dia['asteroides'].max()})")
    linea = alt.Chart(por_dia).mark_line(color=GRIS, point=True).encode(
        x=alt.X("fecha:T", title="Fecha de acercamiento"),
        y=alt.Y("asteroides:Q", title="Asteroides por dia"),
        tooltip=[alt.Tooltip("fecha:T", format="%d/%m/%Y"), "asteroides"])
    prom_r = alt.Chart(pd.DataFrame({"p": [prom]})).mark_rule(
        color=AZUL, strokeDash=[6, 4]).encode(y="p:Q")
    st.altair_chart(linea + prom_r, use_container_width=True)
    st.caption("Linea punteada azul = promedio diario.")

# Tabla
with tab5:
    cols = ["nombre", "fecha", "tamano", "diametro_m", "velocidad_kms",
            "distancia_lunar", "magnitud_h", "peligroso"]
    st.dataframe(df[cols].sort_values("fecha"), use_container_width=True, hide_index=True)
    st.download_button("Descargar CSV", df[cols].to_csv(index=False).encode("utf-8"),
                       "asteroides.csv", "text/csv")
