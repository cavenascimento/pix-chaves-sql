-- Evolução mensal das 10 maiores instituições (pelo estoque do último mês).
WITH top AS (
    SELECT ispb
    FROM chaves
    WHERE data = (SELECT MAX(data) FROM chaves)
    GROUP BY ispb
    ORDER BY SUM(qtd) DESC
    LIMIT 10
)
SELECT c.data, MAX(c.nome) AS nome, SUM(c.qtd) AS chaves
FROM chaves AS c
JOIN top USING (ispb)
GROUP BY c.ispb, c.data
ORDER BY nome, c.data;
