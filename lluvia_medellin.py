"""
Lluvia y temperatura en Medellín: climatología, tendencia y anomalías anuales.

Datos: reanálisis ERA5 servido por Open-Meteo (Historical Weather API), un punto en Medellín.
Fuente: Open-Meteo.com (licencia CC BY 4.0). Su API es gratuita solo para uso no comercial.

Uso:
    python lluvia_medellin.py --inicio 1991 --fin 2025 --salida resultados

Salidas (en la carpeta indicada): datos_mensuales.csv, datos_anuales.csv, climatologia.png,
serie_anual.png, anomalias.png y un resumen impreso en pantalla.

Los criterios son los mismos que usa la página web, para que ambos den los mismos números:
  * un mes es válido si tiene al menos el 90 % de sus días con dato;
  * un año es válido si sus 12 meses son válidos;
  * la precipitación anual es la suma de los meses; la temperatura anual, el promedio de los meses;
  * la tendencia es una regresión lineal por mínimos cuadrados, con intervalo de confianza del 95 %.
"""
import argparse
import math
import os

import numpy as np
import pandas as pd

LAT, LON = 6.2442, -75.5812
URL = "https://archive-api.open-meteo.com/v1/archive"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def descargar(inicio, fin):
    """Descarga los datos diarios (precipitación y temperatura media) de Open-Meteo."""
    import requests
    params = {
        "latitude": LAT, "longitude": LON,
        "start_date": f"{inicio}-01-01", "end_date": f"{fin}-12-31",
        "daily": "precipitation_sum,temperature_2m_mean", "timezone": "America/Bogota",
    }
    r = requests.get(URL, params=params, timeout=120)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({"fecha": pd.to_datetime(d["time"]),
                         "precip_mm": d["precipitation_sum"], "temp_c": d["temperature_2m_mean"]})


def mensual(df):
    """Agrega a mensual. Un mes con menos del 90 % de sus días queda como NaN."""
    g = df.assign(anio=df.fecha.dt.year, mes=df.fecha.dt.month).groupby(["anio", "mes"])
    out = g.agg(precip=("precip_mm", "sum"), temp=("temp_c", "mean"),
                n_p=("precip_mm", "count"), n_t=("temp_c", "count")).reset_index()
    out["dias"] = [pd.Period(year=int(a), month=int(m), freq="M").days_in_month
                   for a, m in zip(out.anio, out.mes)]
    out.loc[out.n_p < 0.9 * out.dias, "precip"] = np.nan
    out.loc[out.n_t < 0.9 * out.dias, "temp"] = np.nan
    return out[["anio", "mes", "precip", "temp", "dias"]]


def anual(m):
    """Agrega a anual: solo años con los 12 meses válidos."""
    a = m.groupby("anio").agg(
        precip=("precip", lambda s: s.sum() if s.notna().sum() == 12 else np.nan),
        temp=("temp", lambda s: s.mean() if s.notna().sum() == 12 else np.nan),
    ).reset_index()
    return a


def t_critico(gl):
    """Valor t de dos colas al 95 % (aproximación de Cornish-Fisher; la usa también la página)."""
    z = 1.96
    return z + (z**3 + z) / (4 * gl) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * gl**2)


def tendencia(x, y):
    """Regresión lineal y = a + b·x, con error estándar e intervalo de confianza del 95 % de b."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    sxx = ((x - x.mean()) ** 2).sum()
    sxy = ((x - x.mean()) * (y - y.mean())).sum()
    syy = ((y - y.mean()) ** 2).sum()
    b = sxy / sxx
    a = y.mean() - b * x.mean()
    sse = ((y - (a + b * x)) ** 2).sum()
    gl = n - 2
    se = math.sqrt(sse / gl / sxx)
    t = t_critico(gl)
    return {"n": n, "a": a, "b": b, "r2": 1 - sse / syy if syy else 0.0,
            "se": se, "ic_bajo": b - t * se, "ic_alto": b + t * se}


def climatologia(m, a0, a1):
    """Promedio de cada mes sobre los años del rango."""
    s = m[(m.anio >= a0) & (m.anio <= a1)]
    return s.groupby("mes").agg(precip=("precip", "mean"), temp=("temp", "mean")).reindex(range(1, 13))


def analizar(df, a0, a1):
    """Devuelve las tablas y las estadísticas del análisis completo."""
    m = mensual(df)
    a = anual(m)
    a = a[(a.anio >= a0) & (a.anio <= a1)]
    res = {"mensual": m, "anual": a, "clim": climatologia(m, a0, a1), "stats": {}}
    for var in ("precip", "temp"):
        v = a.dropna(subset=[var])
        if len(v) >= 6:
            res["stats"][var] = {"media": v[var].mean(), **tendencia(v.anio, v[var])}
    return res


def graficar(res, salida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c, a = res["clim"], res["anual"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(range(1, 13), c.precip, color="#2f7d4f")
    ax.set_xticks(range(1, 13), [x[:3] for x in MESES])
    ax.set_ylabel("Precipitación mensual media (mm)")
    ax2 = ax.twinx()
    ax2.plot(range(1, 13), c.temp, color="#1d6fa5", marker="o")
    ax2.set_ylabel("Temperatura media (°C)")
    ax.set_title("Climatología mensual de Medellín")
    fig.tight_layout(); fig.savefig(os.path.join(salida, "climatologia.png"), dpi=150); plt.close(fig)
    for var, nombre, unidad, color in (("precip", "precipitación anual", "mm", "#2f7d4f"), ("temp", "temperatura media anual", "°C", "#1d6fa5")):
        if var not in res["stats"]:
            continue
        v, st = a.dropna(subset=[var]), res["stats"][var]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.plot(v.anio, v[var], marker="o", color=color)
        ax.plot(v.anio, st["a"] + st["b"] * v.anio, "--", color="gray", label=f"Tendencia: {st['b'] * 10:+.2f} {unidad}/década")
        ax.set_ylabel(f"{nombre.capitalize()} ({unidad})"); ax.legend(); ax.set_title(f"Serie de {nombre}")
        fig.tight_layout(); fig.savefig(os.path.join(salida, f"serie_anual_{var}.png"), dpi=150); plt.close(fig)
        fig, ax = plt.subplots(figsize=(8, 4.2))
        anom = v[var] - st["media"]
        ax.bar(v.anio, anom, color=np.where(anom >= 0, color, "#b8bfba"))
        ax.axhline(0, color="black", lw=.8); ax.set_ylabel(f"Anomalía ({unidad})"); ax.set_title(f"Anomalías de {nombre} respecto al promedio")
        fig.tight_layout(); fig.savefig(os.path.join(salida, f"anomalias_{var}.png"), dpi=150); plt.close(fig)


def resumen(res, a0, a1):
    lineas = []
    c = res["clim"].precip.dropna()
    if len(c) == 12:
        top = c.sort_values(ascending=False).index[:2]
        lineas.append(f"Los dos meses más lluviosos son {MESES[top[0] - 1]} y {MESES[top[1] - 1]}.")
    nombres = {"precip": ("precipitación anual", "mm"), "temp": ("temperatura media anual", "°C")}
    for var, (nombre, u) in nombres.items():
        st = res["stats"].get(var)
        if not st:
            continue
        d = 1 if var == "precip" else 2
        b10, lo, hi = st["b"] * 10, st["ic_bajo"] * 10, st["ic_alto"] * 10
        veredicto = ("El intervalo incluye el cero: con estos datos no se puede afirmar que haya una tendencia."
                     if lo <= 0 <= hi else "El intervalo no incluye el cero (ver limitaciones del reanálisis).")
        lineas.append(f"{a0}-{a1} ({st['n']} años): {nombre} media = {st['media']:.{d}f} {u}; tendencia = {b10:+.{d}f} {u} por década "
                      f"(IC 95 %: {lo:+.{d}f} a {hi:+.{d}f}; R² = {st['r2']:.2f}). {veredicto}")
    return "\n".join(lineas)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inicio", type=int, default=1991)
    p.add_argument("--fin", type=int, default=2025)
    p.add_argument("--salida", default="resultados")
    args = p.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    df = descargar(args.inicio, args.fin)
    res = analizar(df, args.inicio, args.fin)
    res["mensual"].to_csv(os.path.join(args.salida, "datos_mensuales.csv"), index=False)
    res["anual"].to_csv(os.path.join(args.salida, "datos_anuales.csv"), index=False)
    graficar(res, args.salida)
    print(resumen(res, args.inicio, args.fin))
    print(f"\nArchivos guardados en: {os.path.abspath(args.salida)}")


if __name__ == "__main__":
    main()
