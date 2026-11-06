-- Ranking das instituições no último mês, comparado ao primeiro: ganho de chaves, posição e concentração.
WITH lim AS (SELECT MIN(data) AS ini, MAX(data) AS fim FROM chaves),
p AS (
    SELECT ispb, MAX(nome) AS nome, MAX(segmento) AS segmento,
           SUM(CASE WHEN data = (SELECT ini FROM lim) THEN qtd END) AS chaves_ini,
           SUM(CASE WHEN data = (SELECT fim FROM lim) THEN qtd END) AS chaves_fim
    FROM chaves
    GROUP BY ispb
),
r AS (
    SELECT *,
           COALESCE(chaves_fim, 0) - COALESCE(chaves_ini, 0) AS ganho,
           RANK() OVER (ORDER BY COALESCE(chaves_fim, 0) DESC) AS pos_fim,
           RANK() OVER (ORDER BY COALESCE(chaves_ini, 0) DESC) AS pos_ini,
           CASE WHEN chaves_ini > 0 THEN 100.0 * (chaves_fim - COALESCE(chaves_ini, 0)) / chaves_ini END AS var_pct,
           100.0 * chaves_fim / SUM(chaves_fim) OVER () AS part_fim
    FROM p
    WHERE chaves_fim IS NOT NULL
)
SELECT *, SUM(part_fim) OVER (ORDER BY pos_fim, ispb ROWS UNBOUNDED PRECEDING) AS part_acum
FROM r
ORDER BY pos_fim, ispb;
