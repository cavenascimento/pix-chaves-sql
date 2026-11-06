-- Estoque total de chaves Pix por mês, com variação mensal e acumulada desde o primeiro mês.
WITH mensal AS (
    SELECT data, SUM(qtd) AS chaves, COUNT(DISTINCT ispb) AS participantes
    FROM chaves
    GROUP BY data
)
SELECT data, chaves, participantes,
       chaves - LAG(chaves) OVER (ORDER BY data) AS var_abs,
       100.0 * (chaves - LAG(chaves) OVER (ORDER BY data)) / LAG(chaves) OVER (ORDER BY data) AS var_pct,
       100.0 * (chaves - FIRST_VALUE(chaves) OVER (ORDER BY data)) / FIRST_VALUE(chaves) OVER (ORDER BY data) AS acum_pct
FROM mensal
ORDER BY data;
