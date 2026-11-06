-- Relação entre chaves cadastradas (por instituição) e usuários do DICT, nos meses em comum.
SELECT c.data, c.chaves, d.total AS usuarios, 1.0 * c.chaves / d.total AS chaves_por_usuario
FROM (SELECT data, SUM(qtd) AS chaves FROM chaves GROUP BY data) AS c
JOIN dict_usuarios AS d USING (data)
ORDER BY c.data;
