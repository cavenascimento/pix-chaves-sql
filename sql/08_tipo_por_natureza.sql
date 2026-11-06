-- Estoque do último mês por tipo de chave e natureza do usuário (pessoa física ou jurídica).
SELECT tipo_chave, natureza, SUM(qtd) AS chaves
FROM chaves
WHERE data = (SELECT MAX(data) FROM chaves)
GROUP BY tipo_chave, natureza
ORDER BY tipo_chave, natureza;
