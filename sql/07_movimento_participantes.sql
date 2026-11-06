-- Instituições que passaram a ter chaves, que deixaram de aparecer e que permaneceram entre o primeiro e o último mês.
WITH lim AS (SELECT MIN(data) AS ini, MAX(data) AS fim FROM chaves),
a AS (SELECT ispb, SUM(qtd) AS chaves FROM chaves WHERE data = (SELECT ini FROM lim) GROUP BY ispb),
b AS (SELECT ispb FROM chaves WHERE data = (SELECT fim FROM lim) GROUP BY ispb)
SELECT
    (SELECT COUNT(*) FROM b WHERE ispb NOT IN (SELECT ispb FROM a)) AS novas,
    (SELECT COUNT(*) FROM a WHERE ispb NOT IN (SELECT ispb FROM b)) AS saidas,
    (SELECT COUNT(*) FROM a WHERE ispb IN (SELECT ispb FROM b)) AS permanecem,
    (SELECT COALESCE(SUM(chaves), 0) FROM a WHERE ispb NOT IN (SELECT ispb FROM b)) AS chaves_das_saidas;
