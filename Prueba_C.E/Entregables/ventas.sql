--Facturas - encabezado
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\oinv.parquet');

--Facturas - detalle
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\inv1.parquet');

--Notas de credito - encabezado
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\orin.parquet');

--Notas de credito - detalle
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\rin1.parquet');

--Cataolgo de productos
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\oitm.parquet');

--Grupo de productos
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\oitb.parquet');

--Bodegas
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\owhs.parquet');

--Ubicaciones
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\obin.parquet');

--Inventario diario
SELECT * FROM read_parquet('D:\Proceso Trade\Prueba_C.E\Prueba_C.E\datos\inventario_regional.parquet');

--
CREATE OR REPLACE VIEW vista_ventas AS

-- Facturas de Venta
SELECT 
    T0.DocEntry,
    CAST(T0.DocDate AS DATE) AS DocDate,
    T0.Canceled,
    T1.LineNum,
    T1.ItemCode,
    T3.InvntryUom AS SKU,
    T4.GrupoArticulo AS GrupoArticulo,
    T5.WhsName AS Bodega,
    T6.Canal,
    T6.Ubicacion,
    
    (T1.Quantity * 1) AS Cantidad,
    (T1.LineTotal * 1) AS LineTotal_GTQ,
    (T1.StockValue * 1) AS CostoTotal_GTQ,
    
    'Factura' AS TipoDocumento

FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oinv.parquet') T0
INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inv1.parquet') T1 ON T0.DocEntry = T1.DocEntry
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oitm.parquet') T3 ON T1.ItemCode = T3.ItemCode
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oitb.parquet') T4 ON T3.ItmsGrpCod = T4.ItmsGrpCod
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/owhs.parquet') T5 ON T1.WhsCode = T5.WhsCode
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/obin.parquet') T6 ON T1.U_Ubicacion = T6.AbsEntry

UNION ALL

-- Notas de Crédito (Devoluciones)
SELECT 
    T0.DocEntry,
    CAST(T0.DocDate AS DATE) AS DocDate,
    T0.Canceled,
    T1.LineNum,
    T1.ItemCode,
    T3.InvntryUom AS SKU,
    T4.GrupoArticulo AS GrupoArticulo,
    T5.WhsName AS Bodega,
    T6.Canal,
    T6.Ubicacion,
    
    (T1.Quantity * -1) AS Cantidad,
    (T1.LineTotal * -1) AS LineTotal_GTQ,
    (T1.StockValue * -1) AS CostoTotal_GTQ,
    
    'NotaCredito' AS TipoDocumento

FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/orin.parquet') T0
INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/rin1.parquet') T1 ON T0.DocEntry = T1.DocEntry
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oitm.parquet') T3 ON T1.ItemCode = T3.ItemCode
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oitb.parquet') T4 ON T3.ItmsGrpCod = T4.ItmsGrpCod
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/owhs.parquet') T5 ON T1.WhsCode = T5.WhsCode
LEFT JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/obin.parquet') T6 ON T1.U_Ubicacion = T6.AbsEntry;

--A1
select * from vista_ventas;

--A2
SELECT 
    SUM(LineTotal_GTQ) AS VentaNetaTotal_GTQ
FROM vista_ventas
WHERE DocDate BETWEEN '2026-08-01' AND '2026-08-21'
  AND Canceled = 'N';

--A3
SELECT 
    TipoDocumento,
    COUNT(DISTINCT DocEntry) AS CantidadDocumentosNoContables,
    SUM(LineTotal_GTQ) AS MontoAfectado_GTQ
FROM vista_ventas
WHERE Canceled = 'Y'
GROUP BY TipoDocumento;

--A4
SELECT 
    COUNT(*) AS Cantidad_Lineas_Anomalas,
    ROUND(SUM(LineTotal_GTQ), 2) AS Monto_Total_Lineas_GTQ
FROM vista_ventas
WHERE DocDate BETWEEN '2026-08-01' AND '2026-08-21'
  AND Canceled = 'N'
  AND (LineTotal_GTQ <= 0 OR CostoTotal_GTQ <= 0);

--A5
WITH duplicados AS (
    SELECT 
        DataMartDate, CodigoAlmacen, SKU, Ubicacion,
        COUNT(*) AS repeticiones
    FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inventario_regional.parquet')
    GROUP BY DataMartDate, CodigoAlmacen, SKU, Ubicacion
    HAVING COUNT(*) > 1
)
SELECT 
    SUM(repeticiones - 1) AS Filas_Sobrantes
FROM duplicados;

--A6
SELECT 
    CodigoAlmacen,
    COUNT(DISTINCT CAST(DataMartDate AS DATE)) AS Dias_Con_Registro,
    COUNT(*) AS Total_Filas_Reportadas,
    MIN(CAST(DataMartDate AS DATE)) AS Fecha_Inicio,
    MAX(CAST(DataMartDate AS DATE)) AS Fecha_Fin
FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inventario_regional.parquet')
WHERE CAST(DataMartDate AS DATE) BETWEEN '2026-08-01' AND '2026-08-21'
GROUP BY CodigoAlmacen
ORDER BY Total_Filas_Reportadas ASC;

SELECT 
    CAST(DataMartDate AS DATE) AS Fecha,
    CodigoAlmacen,
    COUNT(*) AS Total_Registros_SKU,
    SUM(sum_Stock) AS Stock_Total_Dia
FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inventario_regional.parquet')
WHERE CodigoAlmacen IN ('GT1CEDI', 'GT1TRAN', 'GT2COMER')
  AND CAST(DataMartDate AS DATE) BETWEEN '2026-08-01' AND '2026-08-21'
GROUP BY CAST(DataMartDate AS DATE), CodigoAlmacen
ORDER BY CodigoAlmacen, Fecha;

--A7
SELECT 
    ROUND(SUM(
        CASE 
            WHEN nc.DocCur = 'GTQ' THEN det.LineTotal
            ELSE det.LineTotal * nc.DocRate 
        END
    ), 2) AS Monto_NC_Facturas_Julio_GTQ,
    COUNT(DISTINCT nc.DocEntry) AS Cantidad_Notas_Credito
FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/orin.parquet') nc
INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/rin1.parquet') det 
    ON nc.DocEntry = det.DocEntry
INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oinv.parquet') fact 
    ON det.BaseEntry = fact.DocEntry
WHERE CAST(nc.DocDate AS DATE) BETWEEN '2026-08-01' AND '2026-08-21'
  AND CAST(fact.DocDate AS DATE) < '2026-08-01'
  AND nc.Canceled = 'N';

--A8
SELECT 
    ROUND(SUM(T1.LineTotal), 2) AS Venta_Sin_Limpieza_GTQ
FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oinv.parquet') T0
INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inv1.parquet') T1 
    ON T0.DocEntry = T1.DocEntry
WHERE CAST(T0.DocDate AS DATE) BETWEEN '2026-08-01' AND '2026-08-21';

WITH venta_bruta AS (
    SELECT SUM(T1.LineTotal) AS monto
    FROM read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/oinv.parquet') T0
    INNER JOIN read_parquet('D:/Proceso Trade/Prueba_C.E/Prueba_C.E/datos/inv1.parquet') T1 
        ON T0.DocEntry = T1.DocEntry
    WHERE CAST(T0.DocDate AS DATE) BETWEEN '2026-08-01' AND '2026-08-21'
),
venta_neta AS (
    SELECT SUM(LineTotal_GTQ) AS monto
    FROM vista_ventas
    WHERE DocDate BETWEEN '2026-08-01' AND '2026-08-21'
      AND Canceled = 'N'
)
SELECT 
    ROUND(b.monto, 2) AS Venta_Sin_Limpieza_A8,
    ROUND(n.monto, 2) AS Venta_Neta_Real_A2,
    ROUND(b.monto - n.monto, 2) AS Diferencia_Difiere_GTQ
FROM venta_bruta b, venta_neta n;