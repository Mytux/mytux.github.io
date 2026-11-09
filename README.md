# Lluvia y temperatura en Medellín (1991–2025)

Proyecto de datos reproducible de Mytux. Responde a la pregunta: **¿cómo se reparte la lluvia a lo largo del año en Medellín y ha cambiado en las últimas décadas?**

La misma lógica corre en la página web (en el navegador del visitante) y en este script de Python, y ambos usan los mismos criterios, así que deben dar los mismos números.

## Datos
- **Fuente:** reanálisis ERA5 servido por la API Historical Weather de [Open-Meteo](https://open-meteo.com/).
- **Punto:** latitud 6.2442, longitud -75.5812 (Medellín). Un solo punto de la malla del modelo.
- **Variables diarias:** precipitación total (`precipitation_sum`) y temperatura media del aire (`temperature_2m_mean`).
- **Licencia:** CC BY 4.0 (hay que citar a Open-Meteo.com). Su API es gratuita solo para uso no comercial.

## Método
1. Descargar los datos diarios del periodo.
2. Agregar por mes (un mes es válido si tiene al menos el 90 % de sus días con dato).
3. Agregar por año (un año es válido si sus 12 meses son válidos): precipitación = suma; temperatura = promedio de los meses.
4. Climatología: promedio de cada mes sobre todos los años.
5. Tendencia: regresión lineal por mínimos cuadrados, con intervalo de confianza del 95 % de la pendiente (valor t aproximado por Cornish-Fisher).
6. Anomalías: diferencia de cada año respecto al promedio del periodo.

## Cómo reproducirlo
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python lluvia_medellin.py --inicio 1991 --fin 2025 --salida resultados
```
Genera `datos_mensuales.csv`, `datos_anuales.csv`, tres gráficas en PNG y un resumen en la terminal.

## Limitaciones
- Es un **reanálisis** (modelo que asimila observaciones), no mediciones de estaciones. En un valle de montaña como el de Aburrá, una celda del modelo no captura las diferencias locales.
- Un punto y un periodo corto no bastan para atribuir causas: la tendencia describe lo que muestran estos datos, no explica por qué.
- Con unos 35 años, el intervalo de confianza de la tendencia suele ser amplio.
