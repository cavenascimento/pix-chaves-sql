"""Testes rápidos: pytest -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_pix as b


def chaves_ok():
    return pd.DataFrame({"data": ["2025-01-31"] * 2 + ["2025-02-28"] * 2, "ispb": ["1", "2"] * 2, "nome": ["A", "B"] * 2,
                         "natureza": ["PF"] * 4, "tipo_chave": ["CPF"] * 4, "qtd": [10, 5, 12, 6], "segmento": ["X"] * 4})


def dict_ok():
    return pd.DataFrame({"data": ["2025-01-31", "2025-02-28"], "pf": [8, 9], "pj": [2, 3], "total": [10, 12]})


def test_validacao_aceita_dados_corretos():
    b.validar_entrada(chaves_ok(), dict_ok())


def test_validacao_barra_duplicidade():
    c = pd.concat([chaves_ok(), chaves_ok().head(1)])
    with pytest.raises(b.ErroDeDados):
        b.validar_entrada(c, dict_ok())


def test_validacao_barra_total_errado():
    d = dict_ok(); d.loc[0, "total"] = 99
    with pytest.raises(b.ErroDeDados):
        b.validar_entrada(chaves_ok(), d)


def test_validacao_barra_mes_faltando():
    d = pd.DataFrame({"data": ["2025-01-31", "2025-03-31"], "pf": [1, 1], "pj": [1, 1], "total": [2, 2]})
    with pytest.raises(b.ErroDeDados):
        b.validar_entrada(chaves_ok(), d)


def test_sql_fecha_com_origem():
    c, d = chaves_ok(), dict_ok()
    con = b.carregar_banco(c, d)
    m = b.consulta(con, "01_total_mensal.sql")
    assert m.chaves.tolist() == [15, 18] and round(m.var_pct.iloc[1], 1) == 20.0


def test_formatacao():
    assert b.num(1234.5) == "1.234,5" and b.abrev(1_020_000_000) == "1,02 bi" and b.abrev(-43_716) == "-44 mil"
    assert b.bonito("NU PAGAMENTOS - IP") == "Nu Pagamentos - IP" and b.mes_ano("2026-10-31") == "out/26"


def test_movimento_de_instituicoes_fecha():
    c = pd.DataFrame({"data": ["2025-01-31", "2025-01-31", "2025-02-28", "2025-02-28"], "ispb": ["1", "2", "1", "3"],
                      "nome": ["A", "B", "A", "C"], "natureza": ["PF"] * 4, "tipo_chave": ["CPF"] * 4,
                      "qtd": [10, 4, 12, 7], "segmento": ["X"] * 4})
    d = pd.DataFrame({"data": ["2025-01-31", "2025-02-28"], "pf": [1, 1], "pj": [1, 1], "total": [2, 2]})
    m = b.consulta(b.carregar_banco(c, d), "07_movimento_participantes.sql").iloc[0]
    assert (m.novas, m.saidas, m.permanecem, m.chaves_das_saidas) == (1, 1, 1, 4)
