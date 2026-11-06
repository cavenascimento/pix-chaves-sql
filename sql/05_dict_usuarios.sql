-- Usuários cadastrados no DICT: novos por mês, média móvel de 12 meses, crescimento em 12 meses e peso de PF.
WITH d AS (
    SELECT data, pf, pj, total, total - LAG(total) OVER (ORDER BY data) AS novos
    FROM dict_usuarios
)
SELECT data, pf, pj, total, novos,
       AVG(novos) OVER (ORDER BY data ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS novos_media12,
       COUNT(novos) OVER (ORDER BY data ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS n_janela,
       100.0 * (total - LAG(total, 12) OVER (ORDER BY data)) / LAG(total, 12) OVER (ORDER BY data) AS cresc_12m,
       100.0 * pf / total AS pct_pf
FROM d
ORDER BY data;
