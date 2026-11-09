# -*- coding: utf-8 -*-
"""
Created on Sun Nov  8 19:59:47 2026

@author: Jose
"""

import os
import pandas as pd
import numpy as np

# ==========================================
# 0. CARGA DE ARCHIVOS PARQUET
# ==========================================
# Cambia la ruta a donde tengas guardados tus archivos .parquet
DATA_DIR = "D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/"
print("Cargando archivos parquet...")
# Carga optimizada seleccionando solo las columnas requeridas
oinv = pd.read_parquet(os.path.join(DATA_DIR, "oinv.parquet"))[['DocEntry', 'DocNum', 'DocDate', 'DocCur', 'DocRate', 'Canceled']]
inv1 = pd.read_parquet(os.path.join(DATA_DIR, "inv1.parquet"))[['DocEntry', 'ItemCode', 'WhsCode', 'LineTotal', 'StockValue', 'Quantity', 'U_Ubicacion']]

orin = pd.read_parquet(os.path.join(DATA_DIR, "orin.parquet"))[['DocEntry', 'DocNum', 'DocDate', 'DocCur', 'DocRate', 'Canceled']]
rin1 = pd.read_parquet(os.path.join(DATA_DIR, "rin1.parquet"))[['DocEntry', 'ItemCode', 'WhsCode', 'LineTotal', 'StockValue', 'Quantity', 'U_Ubicacion', 'BaseEntry']]

oitm = pd.read_parquet(os.path.join(DATA_DIR, "oitm.parquet"))[['ItemCode', 'InvntryUom', 'ItmsGrpCod']]
oitb = pd.read_parquet(os.path.join(DATA_DIR, "oitb.parquet"))[['ItmsGrpCod', 'ItmsGrpNam']]
owhs = pd.read_parquet(os.path.join(DATA_DIR, "owhs.parquet"))[['WhsCode', 'WhsName']]
obin = pd.read_parquet(os.path.join(DATA_DIR, "obin.parquet"))[['AbsEntry', 'Canal', 'Ubicacion']]
inventario = pd.read_parquet(os.path.join(DATA_DIR, "inventario_regional.parquet"))

# ==========================================
# 1. CONSTRUCCIÓN DE LA TABLA DE VENTAS (A.1)
# ==========================================

# A. Facturas (OINV + INV1)
facturas = inv1.merge(oinv, on="DocEntry", how="inner")
facturas["TipoDocumento"] = "Factura"
facturas["FactorSigno"] = 1

# B. Notas de Crédito (ORIN + RIN1)
notas = rin1.merge(orin, on="DocEntry", how="inner")
notas["TipoDocumento"] = "NotaCredito"
notas["FactorSigno"] = -1

# C. Concatenación de Facturas y Notas de Crédito
df_ventas = pd.concat([facturas, notas], ignore_index=True)

# D. Cruce de catálogos (OITM, OITB, OWHS, OBIN)
df_ventas = df_ventas.merge(
    oitm[["ItemCode", "InvntryUom", "ItmsGrpCod"]], on="ItemCode", how="left"
)
df_ventas = df_ventas.merge(
    oitb[["ItmsGrpCod", "ItmsGrpNam"]], on="ItmsGrpCod", how="left"
)
df_ventas = df_ventas.merge(
    owhs[["WhsCode", "WhsName"]], on="WhsCode", how="left"
)

# Mapeo de ubicación y canal por U_Ubicacion = AbsEntry
if "U_Ubicacion" in df_ventas.columns and "AbsEntry" in obin.columns:
    df_ventas = df_ventas.merge(
        obin[["AbsEntry", "Canal", "Ubicacion"]],
        left_on="U_Ubicacion",
        right_on="AbsEntry",
        how="left",
    )

# Renombrar columnas clave según especificaciones
df_ventas.rename(
    columns={
        "InvntryUom": "SKU",
        "ItmsGrpNam": "GrupoArticulo",
        "WhsName": "Bodega",
    },
    inplace=True,
)

# E. Conversión de moneda a GTQ y ajuste de signos
# Si DocCur == 'GTQ', se toma LineTotal/StockValue; si no, se multiplica por DocRate.
# Se multiplica por FactorSigno (+1 para Factura, -1 para NC).
df_ventas["DocDate"] = pd.to_datetime(df_ventas["DocDate"])

df_ventas["LineTotal_GTQ"] = np.where(
    df_ventas["DocCur"] == "GTQ",
    df_ventas["LineTotal"],
    df_ventas["LineTotal"] * df_ventas["DocRate"],
) * df_ventas["FactorSigno"]

df_ventas["StockValue_GTQ"] = np.where(
    df_ventas["DocCur"] == "GTQ",
    df_ventas["StockValue"],
    df_ventas["StockValue"] * df_ventas["DocRate"],
) * df_ventas["FactorSigno"]

df_ventas["Cantidad_Ajustada"] = df_ventas["Quantity"] * df_ventas["FactorSigno"]

# Guardar o preparar el dataframe base
print("Tabla de ventas unificada procesada exitosamente.")

# ==========================================
# 2. RESOLUCIÓN DE INCISOS A.2 A A.8
# ==========================================
respuestas = []

# --- A2: Venta Neta Total (1-21 de Agosto en GTQ) ---
filtro_agosto_valido = (
    (df_ventas["DocDate"] >= "2026-08-01")
    & (df_ventas["DocDate"] <= "2026-08-21")
    & (df_ventas["Canceled"] == "N")
)

venta_neta_total = df_ventas.loc[filtro_agosto_valido, "LineTotal_GTQ"].sum()
respuestas.append({
    "Inciso": "A2",
    "Pregunta": "Venta Neta Total (1-21 Ago en GTQ)",
    "Valor_Numerico": round(venta_neta_total, 2),
    "Detalle_Observaciones": "Suma de LineTotal en GTQ excluyendo documentos cancelados (Canceled='Y')."
})

# --- A3: Documentos No Contables (Cancelados) ---
docs_cancelados = df_ventas[df_ventas["Canceled"] == "Y"]
cant_docs_cancelados = docs_cancelados["DocEntry"].nunique()
monto_docs_cancelados = docs_cancelados["LineTotal_GTQ"].sum()

respuestas.append({
    "Inciso": "A3",
    "Pregunta": "Documentos No Contables (Cancelados)",
    "Valor_Numerico": cant_docs_cancelados,
    "Detalle_Observaciones": f"Total de DocEntry cancelados. Monto bruto afectado: Q{abs(monto_docs_cancelados):,.2f} GTQ."
})

# --- A4: Líneas con Ajuste / Anomalías (LineTotal <= 0 o Costo <= 0) ---
lineas_anomalas = df_ventas[
    filtro_agosto_valido & ((df_ventas["LineTotal_GTQ"] <= 0) | (df_ventas["StockValue_GTQ"] <= 0))
]

respuestas.append({
    "Inciso": "A4",
    "Pregunta": "Líneas con Ajuste/Anomalías",
    "Valor_Numerico": len(lineas_anomalas),
    "Detalle_Observaciones": f"Líneas válidas de agosto con monto o costo <= 0. Suma en GTQ: Q{lineas_anomalas['LineTotal_GTQ'].sum():,.2f}."
})

# --- A5: Duplicados en inventario_regional.parquet ---
columnas_clave_inv = ["DataMartDate", "CodigoAlmacen", "SKU", "Ubicacion"]
duplicados_mask = inventario.duplicated(subset=columnas_clave_inv, keep=False)
total_filas_duplicadas = duplicados_mask.sum()

respuestas.append({
    "Inciso": "A5",
    "Pregunta": "Registros Duplicados en Inventario",
    "Valor_Numerico": total_filas_duplicadas,
    "Detalle_Observaciones": "Número de registros que comparten la misma llave (DataMartDate, CodigoAlmacen, SKU, Ubicacion)."
})

# --- A6: Confiabilidad del Inventario (Registros/Valores Atípicos) ---
# Ejemplo: Stock negativo o inconsistencias en inventario
stock_negativo = (inventario["sum_Stock"] < 0).sum() if "sum_Stock" in inventario.columns else 0

respuestas.append({
    "Inciso": "A6",
    "Pregunta": "Inconsistencias en Inventario (Stock Negativo)",
    "Valor_Numerico": stock_negativo,
    "Detalle_Observaciones": "Registros de inventario diario con valores de stock negativos."
})

# --- A7: Notas de Crédito de Meses Anteriores ---
# Cruce entre RIN1 (Notas) y OINV (Factura Original mediante BaseEntry)
notas_agosto = rin1.merge(orin, on="DocEntry", how="inner")
notas_agosto["DocDate_NC"] = pd.to_datetime(notas_agosto["DocDate_y"] if "DocDate_y" in notas_agosto.columns else notas_agosto["DocDate"])

# Filtrar NC emitidas del 1 al 21 de agosto
nc_1_21 = notas_agosto[
    (notas_agosto["DocDate_NC"] >= "2026-08-01") & (notas_agosto["DocDate_NC"] <= "2026-08-21")
]

# Unir con OINV original vía BaseEntry
nc_con_factura_origen = nc_1_21.merge(
    oinv[["DocEntry", "DocDate"]], left_on="BaseEntry", right_on="DocEntry", suffixes=("_NC", "_Fact")
)
nc_con_factura_origen["DocDate_Fact"] = pd.to_datetime(nc_con_factura_origen["DocDate_Fact"])

# Filtrar las facturas emitidas ANTES de agosto de 2026
nc_facturas_anteriores = nc_con_factura_origen[nc_facturas_anteriores_mask := nc_con_factura_origen["DocDate_Fact"] < "2026-08-01"]

monto_nc_anteriores = nc_facturas_anteriores["LineTotal"].sum() if "LineTotal" in nc_facturas_anteriores.columns else 0

respuestas.append({
    "Inciso": "A7",
    "Pregunta": "Monto NC de Facturas de Meses Anteriores (GTQ)",
    "Valor_Numerico": round(monto_nc_anteriores, 2),
    "Detalle_Observaciones": f"Notas de Crédito emitidas en agosto correspondientes a facturas anteriores al 01/08/2026. DocEntries afectados: {nc_facturas_anteriores['DocEntry_NC'].nunique()}."
})

# --- A8: Impacto de Joins Directos sin Auditoría ---
# Venta bruta acumulada uniendo directamente INV1 + OINV sin filtrar cancelados ni deduplicar
venta_bruta_sin_limpieza = (inv1.merge(oinv, on="DocEntry", how="inner")
    .query("DocDate >= '2026-08-01' and DocDate <= '2026-08-21'")["LineTotal"].sum())

diferencia_impacto = venta_bruta_sin_limpieza - venta_neta_total

respuestas.append({
    "Inciso": "A8",
    "Pregunta": "Diferencia Venta Sin Limpieza vs. Venta Neta Real (GTQ)",
    "Valor_Numerico": round(diferencia_impacto, 2),
    "Detalle_Observaciones": "Diferencia generada al omitir el filtro de cancelados, devoluciones y ajuste de moneda."
})

# ==========================================
# 3. EXPORTAR ENTREGABLE respuestas_A.csv
# ==========================================
df_respuestas = pd.DataFrame(respuestas)
df_respuestas.to_csv("respuestas_A.csv", index=False, encoding="utf-8")

print("\n¡Proceso completado exitosamente!")
print("Se ha generado el archivo 'respuestas_A.csv' en el directorio actual.")
print("\nResumen de resultados:")
print(df_respuestas[["Inciso", "Pregunta", "Valor_Numerico"]])