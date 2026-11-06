"""Pix: estoque de chaves e usuários do DICT (Banco Central do Brasil).

Fluxo: CSVs -> validação -> SQLite em memória -> consultas em sql/ -> conferência -> painel Plotly em HTML.
Uso:   python build_pix.py --chaves chaves.csv --dict usuarios_dict.csv --saida index.html
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

AQUI = Path(__file__).parent
SQL_DIR = AQUI / "sql"
log = logging.getLogger("pix")

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
COL_CHAVES = {"Data": "data", "ISPB": "ispb", "Nome": "nome", "NaturezaUsuario": "natureza",
              "TipoChave": "tipo_chave", "qtdChaves": "qtd", "Segmento": "segmento"}
COL_DICT = {"DataGraficosPix": "data", "qtdUsuariosPessoaFisica": "pf",
            "qtdUsuariosPessoaJuridica": "pj", "qtdUsuariosCadastradosDICTTotal": "total"}
AZUL, LARANJA, VERDE, CINZA = "#1F6FEB", "#E8702D", "#12A150", "#5A6B7B"
PALETA = ["#1F6FEB", "#E8702D", "#12A150", "#8E5CF7", "#D6336C", "#0CA5B0", "#B7791F", "#5A6B7B", "#2B8A3E", "#C92A2A"]


class ErroDeDados(Exception):
    """Dado de entrada inválido ou resultado que não fecha com a origem."""


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise ErroDeDados(mensagem)


# ---------------------------------------------------------------- leitura e validação
def ler(caminho: Path, colunas: dict[str, str], dtype: dict | None = None) -> pd.DataFrame:
    df = pd.read_csv(caminho, encoding="utf-8-sig", dtype=dtype)
    exigir(not df.empty, f"{caminho.name} está vazio (só cabeçalho). Baixe o arquivo novamente.")
    falta = set(colunas) - set(df.columns)
    exigir(not falta, f"{caminho.name}: faltam colunas {sorted(falta)}")
    return df[list(colunas)].rename(columns=colunas)


def validar_entrada(c: pd.DataFrame, d: pd.DataFrame) -> None:
    exigir(not c.isna().any().any(), "chaves: há valores ausentes")
    exigir(not d.isna().any().any(), "DICT: há valores ausentes")
    exigir(not c.duplicated(["data", "ispb", "natureza", "tipo_chave"]).any(), "chaves: linhas duplicadas")
    exigir((c.qtd >= 0).all(), "chaves: quantidade negativa")
    exigir((d.pf + d.pj == d.total).all(), "DICT: total diferente de PF + PJ")
    meses = pd.PeriodIndex(sorted(pd.to_datetime(d.data).dt.to_period("M").unique()))
    exigir(len(meses) == (meses[-1] - meses[0]).n + 1, "DICT: há meses faltando na série")
    meses_c = pd.PeriodIndex(sorted(pd.to_datetime(c.data).dt.to_period("M").unique()))
    exigir(len(meses_c) == (meses_c[-1] - meses_c[0]).n + 1, "chaves: há meses faltando na série")


# ---------------------------------------------------------------- banco e consultas
def carregar_banco(c: pd.DataFrame, d: pd.DataFrame) -> sqlite3.Connection:
    exigir(sqlite3.sqlite_version_info >= (3, 28), "SQLite antigo: é preciso 3.28+ (funções de janela)")
    con = sqlite3.connect(":memory:")
    c.to_sql("chaves", con, index=False)
    d.to_sql("dict_usuarios", con, index=False)
    con.execute("CREATE INDEX ix_chaves ON chaves (data, ispb)")
    return con


def consulta(con: sqlite3.Connection, arquivo: str) -> pd.DataFrame:
    return pd.read_sql_query((SQL_DIR / arquivo).read_text(encoding="utf-8"), con)


def conferir(c: pd.DataFrame, q: dict[str, pd.DataFrame]) -> None:
    """Garante que o resultado do SQL fecha com os dados de origem."""
    ultimo = c[c.data == c.data.max()].qtd.sum()
    exigir(int(q["mensal"].chaves.sum()) == int(c.qtd.sum()), "soma mensal do SQL difere da origem")
    exigir(int(q["ranking"].chaves_fim.sum()) == int(ultimo), "ranking não fecha com o estoque do último mês")
    exigir(abs(q["ranking"].part_acum.iloc[-1] - 100) < 1e-6, "participações não somam 100%")
    mv, ini_fim = q["mov"].iloc[0], q["mensal"].iloc[[0, -1]]
    exigir(int(mv.novas + mv.permanecem) == int(ini_fim.participantes.iloc[1]), "movimento de instituições não fecha com o último mês")
    exigir(int(mv.saidas + mv.permanecem) == int(ini_fim.participantes.iloc[0]), "movimento de instituições não fecha com o primeiro mês")
    exigir(int(q["tiponat"].chaves.sum()) == int(ultimo), "tipo x natureza não fecha com o último mês")
    for dim, g in q["perfil"].groupby("dimensao"):
        exigir((g.groupby("data").pct.sum().sub(100).abs() < 1e-6).all(), f"perfil ({dim}) não soma 100%")
    log.info("conferências ok: SQL fecha com os dados de origem")


# ---------------------------------------------------------------- formatação
def mes_ano(valor: str) -> str:
    t = pd.Timestamp(valor)
    return f"{MES[t.month - 1]}/{str(t.year)[2:]}"


def num(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def abrev(v: float) -> str:
    if abs(v) >= 1e9:
        return f"{num(v / 1e9, 2)} bi"
    return f"{num(v / 1e6, 1)} mi" if abs(v) >= 1e6 else f"{num(v / 1e3, 0)} mil"


def bonito(nome: str) -> str:
    """Nome de instituição em caixa alta -> caixa de título, preservando siglas comuns."""
    troca = {"IP": "IP", "S.A.": "S.A.", "S.A": "S.A.", "BCO": "Banco", "LTDA.": "Ltda.", "LTDA": "Ltda.",
             "DE": "de", "DO": "do", "DA": "da", "E": "e"}
    return " ".join(troca.get(w, w.capitalize()) for w in nome.split())


# ---------------------------------------------------------------- gráficos
def base(f: go.Figure, altura: int = 380) -> go.Figure:
    f.update_layout(height=altura, margin=dict(l=10, r=10, t=10, b=10), separators=",.",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Plus Jakarta Sans, system-ui, sans-serif", size=12),
                    legend=dict(orientation="h", y=-0.15), hovermode="x unified")
    f.update_xaxes(gridcolor="#DAE2E9", automargin=True)
    f.update_yaxes(gridcolor="#DAE2E9", automargin=True)
    return f


def fig_total(m: pd.DataFrame) -> go.Figure:
    x = [mes_ano(v) for v in m.data]
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.06)
    f.add_trace(go.Scatter(x=x, y=m.chaves / 1e6, mode="lines+markers", name="Chaves (milhões)",
                           line=dict(color=AZUL, width=3), hovertemplate="%{y:,.1f} mi"), 1, 1)
    f.add_trace(go.Bar(x=x, y=m.var_pct, name="Variação no mês (%)", marker_color=LARANJA,
                       hovertemplate="%{y:.2f}%"), 2, 1)
    f.update_yaxes(title_text="milhões de chaves", row=1, col=1)
    f.update_yaxes(title_text="% no mês", row=2, col=1)
    return base(f, 420)


def fig_ranking(r: pd.DataFrame) -> go.Figure:
    top = r.head(15).iloc[::-1]
    f = go.Figure()
    for i, (seg, g) in enumerate(top.groupby("segmento")):
        f.add_trace(go.Bar(y=g.nome, x=g.chaves_fim / 1e6, orientation="h", name=seg, marker_color=PALETA[i % 10],
                           text=[f"{num(v / 1e6, 1)} mi" for v in g.chaves_fim], textposition="outside",
                           hovertemplate="%{y}: %{x:,.1f} mi<extra></extra>"))
    f.update_layout(hovermode="closest", xaxis_title="milhões de chaves")
    return base(f, 520)


def fig_ganho(r: pd.DataFrame) -> go.Figure:
    g = pd.concat([r.nlargest(10, "ganho"), r.nsmallest(5, "ganho")]).drop_duplicates("ispb").sort_values("ganho")
    f = go.Figure(go.Bar(y=g.nome, x=g.ganho / 1e6, orientation="h",
                         marker_color=[VERDE if v >= 0 else LARANJA for v in g.ganho],
                         text=[f"{'+' if v >= 0 else ''}{num(v / 1e6, 1)} mi" for v in g.ganho], textposition="outside",
                         hovertemplate="%{y}: %{x:,.1f} mi<extra></extra>"))
    f.update_layout(hovermode="closest", xaxis_title="variação do estoque (milhões)")
    return base(f, 480)


def fig_series(s: pd.DataFrame) -> go.Figure:
    nomes = list(s.nome.unique())
    f = go.Figure()
    for i, n in enumerate(nomes):
        g = s[s.nome == n]
        f.add_trace(go.Scatter(x=[mes_ano(v) for v in g.data], y=g.chaves / 1e6, name=n, mode="lines",
                               line=dict(color=PALETA[i % 10], width=2.5), hovertemplate="%{y:,.1f} mi"))
    botoes = [dict(label="Todas", method="update", args=[{"visible": [True] * len(nomes)}])]
    botoes += [dict(label=n, method="update", args=[{"visible": [j == i for j in range(len(nomes))]}])
               for i, n in enumerate(nomes)]
    f.update_layout(updatemenus=[dict(buttons=botoes, direction="down", x=0, y=1.18, xanchor="left")],
                    yaxis_title="milhões de chaves", legend=dict(orientation="h", y=-0.2))
    return base(f, 440)


def fig_tipo(t: pd.DataFrame) -> go.Figure:
    g = t[t.dimensao == "Tipo de chave"]
    f = go.Figure()
    for i, cat in enumerate(g.groupby("categoria").pct.mean().sort_values(ascending=False).index):
        h = g[g.categoria == cat]
        f.add_trace(go.Scatter(x=[mes_ano(v) for v in h.data], y=h.pct, name=cat, stackgroup="u", mode="lines",
                               line=dict(width=0.5, color=PALETA[i]), hovertemplate="%{y:.1f}%"))
    f.update_layout(yaxis_title="% do estoque", yaxis_range=[0, 100])
    return base(f, 380)


def fig_segmento(t: pd.DataFrame) -> go.Figure:
    g = t[t.dimensao == "Segmento"]
    ini, fim = g.data.min(), g.data.max()
    cats = g[g.data == fim].nlargest(6, "pct").categoria.tolist()
    f = go.Figure()
    for d, cor in ((ini, "#9DB7E8"), (fim, AZUL)):
        h = g[(g.data == d) & g.categoria.isin(cats)].set_index("categoria").reindex(cats)
        f.add_trace(go.Bar(x=cats, y=h.pct, name=mes_ano(d), marker_color=cor,
                           text=[f"{num(v, 1)}%" for v in h.pct], textposition="outside",
                           hovertemplate="%{y:.1f}%"))
    f.update_layout(barmode="group", yaxis_title="% do estoque")
    return base(f, 380)


def fig_dict(d: pd.DataFrame) -> go.Figure:
    x = [mes_ano(v) for v in d.data]
    f = go.Figure()
    for col, nome, cor in (("pf", "Pessoas físicas", AZUL), ("pj", "Pessoas jurídicas", LARANJA)):
        f.add_trace(go.Scatter(x=x, y=d[col] / 1e6, name=nome, stackgroup="u", mode="lines",
                               line=dict(width=0.5, color=cor), hovertemplate="%{y:,.1f} mi"))
    f.update_layout(yaxis_title="milhões de usuários")
    return base(f, 380)


def fig_novos(d: pd.DataFrame) -> go.Figure:
    x = [mes_ano(v) for v in d.data]
    media = d.novos_media12.where(d.n_janela == 12)        # só mostra a média com 12 meses completos
    f = go.Figure()
    f.add_trace(go.Bar(x=x, y=d.novos / 1e6, name="Novos usuários no mês", marker_color="#9DB7E8",
                       hovertemplate="%{y:,.2f} mi"))
    f.add_trace(go.Scatter(x=x, y=media / 1e6, name="Média móvel de 12 meses", mode="lines",
                           line=dict(color=LARANJA, width=3), hovertemplate="%{y:,.2f} mi"))
    f.update_layout(yaxis_title="milhões por mês")
    return base(f, 380)


def fig_natureza(tn: pd.DataFrame) -> go.Figure:
    ordem = list(tn.groupby("tipo_chave").chaves.sum().sort_values(ascending=False).index)
    f = go.Figure()
    for nat, nome, cor in (("PF", "Pessoas físicas", AZUL), ("PJ", "Pessoas jurídicas", LARANJA)):
        g = tn[tn.natureza == nat].set_index("tipo_chave").reindex(ordem).chaves.fillna(0)
        f.add_trace(go.Bar(x=ordem, y=g / 1e6, name=nome, marker_color=cor, text=[f"{num(v / 1e6, 1)} mi" for v in g],
                           textposition="outside", hovertemplate="%{y:,.1f} mi"))
    f.update_layout(barmode="group", yaxis_title="milhões de chaves")
    return base(f, 380)


def fig_linha(x: list[str], y, nome: str, titulo_y: str, cor: str = AZUL, fmt: str = "%{y:,.2f}") -> go.Figure:
    f = go.Figure(go.Scatter(x=x, y=y, name=nome, mode="lines+markers", line=dict(color=cor, width=3), hovertemplate=fmt))
    f.update_layout(yaxis_title=titulo_y, showlegend=False)
    return base(f, 340)


def tabela(r: pd.DataFrame) -> list[dict]:
    """Todas as instituições do último mês, em formato enxuto para a tabela da página."""
    nulo = lambda v: None if pd.isna(v) else float(v)
    return [dict(pos=int(x.pos_fim), nome=bonito(x.nome), seg=x.segmento, ch=int(x.chaves_fim), pt=float(x.part_fim),
                 gn=int(x.ganho), vp=nulo(x.var_pct), nova=bool(pd.isna(x.chaves_ini))) for x in r.itertuples()]


# ---------------------------------------------------------------- textos calculados
def destaques(q: dict[str, pd.DataFrame]) -> tuple[list[tuple[str, str, str]], list[str]]:
    m, r, p, t, d, u = q["mensal"], q["ranking"], q["serie"], q["perfil"], q["dict"], q["usuario"]
    ini, fim = m.iloc[0], m.iloc[-1]
    top5 = r.iloc[4].part_acum
    tipo = t[t.dimensao == "Tipo de chave"]
    alea = tipo[tipo.categoria == "Aleatória"].sort_values("data")
    maior = r.nlargest(1, "ganho").iloc[0]
    queda = r.nsmallest(1, "ganho").iloc[0]
    dm = d.where(d.n_janela == 12).dropna(subset=["novos_media12"])
    pico = dm.loc[dm.novos_media12.idxmax()]
    neg = d[d.novos < 0]
    t10 = r[r.pos_fim <= 10].assign(delta=lambda x: x.pos_ini - x.pos_fim)
    subiu, caiu = t10.nlargest(1, "delta").iloc[0], t10.nsmallest(1, "delta").iloc[0]
    kpis = [
        (f"Chaves Pix em {mes_ano(fim.data)}", abrev(fim.chaves), f"{num(fim.acum_pct)}% acima de {mes_ano(ini.data)}"),
        ("Ganho no período", "+" + abrev(fim.chaves - ini.chaves), f"{mes_ano(ini.data)} a {mes_ano(fim.data)}"),
        ("Instituições com chaves", num(fim.participantes, 0), f"eram {num(ini.participantes, 0)} em {mes_ano(ini.data)}"),
        ("Concentração das 5 maiores", f"{num(top5)}%", "do estoque de chaves"),
        ("Usuários no DICT", abrev(d.total.iloc[-1]), f"em {mes_ano(d.data.iloc[-1])}"),
        ("Chaves por usuário", num(u.chaves_por_usuario.iloc[-1], 2), "razão entre as duas séries"),
    ]
    achados = [
        f"O estoque passou de {abrev(ini.chaves)} para {abrev(fim.chaves)} entre {mes_ano(ini.data)} e {mes_ano(fim.data)}, "
        f"uma alta de {num(fim.acum_pct)}%.",
        f"As 5 maiores instituições concentram {num(top5)}% das chaves; a maior é {bonito(r.iloc[0].nome)}, "
        f"com {abrev(r.iloc[0].chaves_fim)}.",
        f"Quem mais ganhou chaves no período foi {bonito(maior.nome)} (+{abrev(maior.ganho)}). "
        f"A maior queda foi de {bonito(queda.nome)} ({abrev(queda.ganho)}).",
        f"Entre as 10 maiores, {bonito(subiu.nome)} foi a que mais subiu no ranking ({int(subiu.pos_ini)}º para {int(subiu.pos_fim)}º) "
        f"e {bonito(caiu.nome)} a que mais desceu ({int(caiu.pos_ini)}º para {int(caiu.pos_fim)}º), em chaves cadastradas.",
        f"A chave aleatória representa {num(alea.pct.iloc[-1])}% do estoque em {mes_ano(alea.data.iloc[-1])} "
        f"({num(alea.pct.iloc[-1] - alea.pct.iloc[0])} p.p. desde {mes_ano(alea.data.iloc[0])}).",
        f"No DICT, a média de novos usuários por mês (janela de 12 meses) teve pico de {abrev(pico.novos_media12)} "
        f"em {mes_ano(pico.data)} e está em {abrev(dm.novos_media12.iloc[-1])} em {mes_ano(dm.data.iloc[-1])}.",
    ]
    if len(neg):
        achados.append("Houve queda no total de usuários em " + ", ".join(mes_ano(v) for v in neg.data) +
                       f" ({abrev(neg.novos.min())} no pior mês).")
    nat = t[(t.dimensao == "Natureza") & (t.data == t.data.max())].set_index("categoria").pct
    mv = q["mov"].iloc[0]
    cr = d.dropna(subset=["cresc_12m"])
    achados += [
        f"Pessoas jurídicas têm {num(nat.get('PJ', 0))}% das chaves, enquanto pessoas físicas são {num(d.pct_pf.iloc[-1])}% dos usuários do DICT.",
        f"Entre {mes_ano(ini.data)} e {mes_ano(fim.data)}, {num(mv.novas, 0)} instituições passaram a ter chaves e {num(mv.saidas, 0)} deixaram de aparecer "
        f"(elas somavam {abrev(mv.chaves_das_saidas)} de chaves em {mes_ano(ini.data)}, o que o dado não explica).",
        f"As chaves por usuário foram de {num(u.chaves_por_usuario.iloc[0], 2)} em {mes_ano(u.data.iloc[0])} para "
        f"{num(u.chaves_por_usuario.iloc[-1], 2)} em {mes_ano(u.data.iloc[-1])}. O total de usuários do DICT cresce "
        f"{num(cr.cresc_12m.iloc[-1])}% em 12 meses, ante {num(cr.cresc_12m.iloc[0])}% em {mes_ano(cr.data.iloc[0])}.",
    ]
    return kpis, achados


# ---------------------------------------------------------------- página
def renderizar(figs: dict[str, go.Figure], kpis, achados, linhas: list[dict], caminho: Path, modelo: str, plotly: str = "inline") -> None:
    div = lambda k: figs[k].to_html(full_html=False, include_plotlyjs=False, div_id=f"g_{k}",
                                    config={"displaylogo": False, "responsive": True})
    html = modelo
    for k in figs:
        html = html.replace(f"__{k.upper()}__", div(k))
    html = html.replace("__KPIS__", "".join(f'<div class="k"><small>{a}</small><b>{b}</b><span>{c}</span></div>' for a, b, c in kpis))
    html = html.replace("__TABELA__", json.dumps(linhas, ensure_ascii=False, separators=(",", ":"))).replace("__NINST__", str(len(linhas)))
    html = html.replace("__ACHADOS__", "".join(f"<li>{a}</li>" for a in achados))
    # a biblioteca é inserida por último: a versão do plotly.js precisa ser a mesma do pacote Python
    if plotly == "cdn":
        js = f'<script src="https://cdn.plot.ly/plotly-{pyo.get_plotlyjs_version()}.min.js"></script>'
    else:
        # o caractere U+FFFD aparece literal numa regex do plotly.js; o escape \ufffd é equivalente e evita problemas de codificação
        js = "<script>" + pyo.get_plotlyjs().replace("\ufffd", "\\ufffd") + "</script>"
    caminho.write_text(html.replace("__PLOTLYJS__", js), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chaves", type=Path, required=True)
    ap.add_argument("--dict", dest="dic", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=Path("index.html"))
    ap.add_argument("--plotly", choices=["inline", "cdn"], default="inline",
                    help="inline: página autônoma (~5 MB); cdn: página leve, exige internet")
    ap.add_argument("--modelo", type=Path, default=AQUI / "template_pix.html")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        c = ler(a.chaves, COL_CHAVES, {"ISPB": str})
        d = ler(a.dic, COL_DICT)
        c["qtd"] = c.qtd.astype("int64")
        validar_entrada(c, d)
        con = carregar_banco(c, d)
        q = {k: consulta(con, f) for k, f in (("mensal", "01_total_mensal.sql"), ("ranking", "02_ranking.sql"),
             ("serie", "03_serie_top10.sql"), ("perfil", "04_perfil_chaves.sql"),
             ("dict", "05_dict_usuarios.sql"), ("usuario", "06_chaves_por_usuario.sql"),
             ("mov", "07_movimento_participantes.sql"), ("tiponat", "08_tipo_por_natureza.sql"))}
        conferir(c, q)
    except ErroDeDados as e:
        sys.exit(f"Erro nos dados: {e}")
    figs = {"total": fig_total(q["mensal"]), "ranking": fig_ranking(q["ranking"]), "ganho": fig_ganho(q["ranking"]),
            "series": fig_series(q["serie"]), "tipo": fig_tipo(q["perfil"]), "segmento": fig_segmento(q["perfil"]),
            "dict": fig_dict(q["dict"]), "novos": fig_novos(q["dict"]),
            "natureza": fig_natureza(q["tiponat"]),
            "part": fig_linha([mes_ano(v) for v in q["mensal"].data], q["mensal"].participantes, "Instituições", "instituições com chaves", LARANJA, "%{y:,.0f}"),
            "usuario": fig_linha([mes_ano(v) for v in q["usuario"].data], q["usuario"].chaves_por_usuario, "Chaves por usuário", "chaves por usuário"),
            "cresc": fig_linha([mes_ano(v) for v in q["dict"].dropna(subset=["cresc_12m"]).data], q["dict"].dropna(subset=["cresc_12m"]).cresc_12m, "Crescimento em 12 meses", "% em 12 meses", VERDE, "%{y:.1f}%")}
    kpis, achados = destaques(q)
    renderizar(figs, kpis, achados, tabela(q["ranking"]), a.saida, a.modelo.read_text(encoding="utf-8"), a.plotly)
    log.info("painel gerado em %s", a.saida)


if __name__ == "__main__":
    main()
