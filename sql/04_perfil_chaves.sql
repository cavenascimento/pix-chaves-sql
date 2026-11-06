-- Participação (%) de cada categoria no estoque, por mês, em três dimensões.
WITH base AS (
    SELECT 'Tipo de chave' AS dimensao, tipo_chave AS categoria, data, SUM(qtd) AS chaves FROM chaves GROUP BY tipo_chave, data
    UNION ALL
    SELECT 'Segmento', segmento, data, SUM(qtd) FROM chaves GROUP BY segmento, data
    UNION ALL
    SELECT 'Natureza', natureza, data, SUM(qtd) FROM chaves GROUP BY natureza, data
)
SELECT dimensao, categoria, data, chaves,
       100.0 * chaves / SUM(chaves) OVER (PARTITION BY dimensao, data) AS pct
FROM base
ORDER BY dimensao, data, chaves DESC;
