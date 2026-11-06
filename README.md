# Pix em números: chaves e usuários

Painel interativo que mostra como o estoque de chaves Pix cresceu entre jan/2025 e out/2026, quais instituições concentram esse crescimento e como o cadastro de usuários do DICT evoluiu desde o lançamento do Pix. A análise foi feita com **SQL** (SQLite) e o painel foi gerado inteiramente em **Python** (pandas e Plotly), a partir de dados abertos do Banco Central do Brasil.

**Painel online:** https://cavenascimento.github.io/pix-chaves-sql/

> Se o nome do seu repositório for outro, ajuste o final do endereço acima.

## Pergunta central

> Como as chaves Pix cresceram desde 2025 e quem concentra esse crescimento?

O painel usa o ranking de instituições, o perfil das chaves (tipo, segmento e natureza do usuário) e a série do DICT como contexto.

## O que o painel mostra

- Indicadores no topo: estoque de chaves, ganho no período, número de instituições, concentração das 5 maiores, usuários no DICT e chaves por usuário
- Textos de destaque calculados automaticamente a partir dos dados (nenhum número é escrito à mão)
- Estoque de chaves por mês, com variação mensal
- Ranking das 15 maiores instituições e gráfico de quem mais ganhou e quem mais perdeu chaves
- Evolução das 10 maiores instituições, com menu para ver uma de cada vez
- Tabela pesquisável com todas as instituições, com filtro por segmento e ordenação por coluna
- Perfil das chaves: tipo de chave, segmento, pessoa física x jurídica e número de instituições com chaves por mês
- Usuários do DICT: total por natureza, novos usuários por mês com média móvel de 12 meses, crescimento em 12 meses e chaves por usuário
- Tema claro e escuro, e gráficos interativos

## Principais achados

Valores calculados pelas consultas SQL deste projeto (dados até out/2026):

| Tema | Resultado |
|---|---|
| Estoque de chaves | de cerca de 828 milhões (jan/2025) para 1,02 bilhão (out/2026), alta de 23,3% |
| Concentração | as 5 maiores instituições têm 55,5% das chaves |
| Quem mais ganhou chaves | Mercado Pago (+33,7 milhões) |
| Maior queda | Banco Itaucard (−9,2 milhões) |
| Posições no ranking | entre as 10 maiores, o Banco Inter subiu do 8º para o 5º lugar, e o Bradesco desceu do 4º para o 6º, em chaves cadastradas |
| Tipo de chave | a chave aleatória representa 52,6% do estoque |
| Natureza | pessoas jurídicas têm 5,1% das chaves; pessoas físicas são 89,9% dos usuários do DICT |
| Instituições | 88 passaram a ter chaves e 158 deixaram de aparecer; as que saíram somavam cerca de 1,8 milhão de chaves em jan/2025 |
| DICT | de cerca de 41 milhões de usuários (nov/2020) para cerca de 188 milhões (out/2026); o crescimento em 12 meses caiu de 179,5% (nov/2021) para 5,4% (out/2026) |

Os resultados descrevem o que aconteceu, não o motivo. O projeto não atribui causas.

## Fonte dos dados

Banco Central do Brasil, conjunto **Estatísticas do Pix** (dados abertos): https://dadosabertos.bcb.gov.br/dataset/pix

| Recurso usado | Arquivo no projeto | Período |
|---|---|---|
| Estoque de chaves Pix por participante | `dados/chaves.csv` | jan/2025 a out/2026 (22 meses, 137.072 linhas) |
| Usuários cadastrados no DICT | `dados/usuarios_dict.csv` | nov/2020 a out/2026 (72 meses) |

São estatísticas agregadas por instituição e por mês, sem dados pessoais. Consulte a fonte para os termos de uso dos dados.

## Como funciona

```
CSVs  →  validação  →  SQLite em memória  →  consultas em sql/  →  conferência  →  painel (Plotly) em HTML
```

1. **Leitura e validação:** o script confere colunas, valores ausentes, duplicidades, soma de PF + PJ e continuidade das séries mensais. Se o arquivo estiver vazio ou inconsistente, para com uma mensagem clara.
2. **Banco:** os dois CSVs são carregados em um SQLite em memória.
3. **Consultas:** a análise é feita em SQL, em arquivos separados na pasta `sql/`.
4. **Conferência:** o script verifica que os totais calculados no SQL fecham com os dados de origem.
5. **Painel:** os gráficos, indicadores e textos de destaque são gerados em Python e gravados em uma página HTML.

### Consultas SQL

| Arquivo | O que faz |
|---|---|
| `01_total_mensal.sql` | Estoque total por mês, variação mensal e acumulada (`LAG`, `FIRST_VALUE`) |
| `02_ranking.sql` | Ranking de instituições, ganho, posição inicial e final, participação e concentração acumulada (`RANK`, soma acumulada) |
| `03_serie_top10.sql` | Evolução mensal das 10 maiores instituições |
| `04_perfil_chaves.sql` | Participação por tipo de chave, segmento e natureza, mês a mês (`UNION ALL`, `PARTITION BY`) |
| `05_dict_usuarios.sql` | Novos usuários, média móvel de 12 meses, crescimento em 12 meses e peso de pessoas físicas |
| `06_chaves_por_usuario.sql` | Razão entre chaves e usuários do DICT nos meses em comum (`JOIN`) |
| `07_movimento_participantes.sql` | Instituições que entraram, saíram e permaneceram entre o primeiro e o último mês |
| `08_tipo_por_natureza.sql` | Estoque do último mês por tipo de chave e natureza do usuário |

## Como rodar

Requisitos: Python 3.10 ou superior.

```bash
pip install -r requirements.txt
python build_pix.py --chaves dados/chaves.csv --dict dados/usuarios_dict.csv --saida index.html
```

Opção para uma página mais leve (exige internet para carregar o Plotly):

```bash
python build_pix.py --chaves dados/chaves.csv --dict dados/usuarios_dict.csv --saida index.html --plotly cdn
```

Por padrão a página é autônoma e tem cerca de 5 MB, porque inclui a biblioteca do Plotly.

### Testes

```bash
python -m pytest -q tests
```

Os testes cobrem a validação dos dados, a consistência das consultas SQL e a formatação de números e nomes.

## Estrutura do repositório

```
.
├── index.html              # painel gerado
├── build_pix.py            # script principal (leitura, validação, SQL, gráficos)
├── template_pix.html       # layout da página
├── requirements.txt
├── sql/                    # consultas SQL (01 a 08)
├── tests/test_pix.py
└── dados/
    ├── chaves.csv
    └── usuarios_dict.csv
```

## Limitações e cuidados de leitura

- **Chave não é cliente.** Uma pessoa pode ter várias chaves, em várias instituições. O painel fala em chaves cadastradas na instituição, nunca em clientes.
- **Estoque de fim de mês.** Os dados de chaves são o estoque no último dia de cada mês. Valores de meses diferentes não devem ser somados.
- **Chaves por usuário é uma referência.** A razão compara duas séries com definições diferentes e não é uma medida exata.
- **Instituições que saíram.** O dado mostra que deixaram de aparecer, mas não explica o motivo (por exemplo, encerramento, fusão ou mudança de registro). Não foram feitas suposições.
- **Pequena queda no DICT.** O total de usuários cai levemente em jun/2025, o que é registrado no painel.
- **Sem valor de transações.** O projeto não mede o volume financeiro nem a quantidade de transações Pix. Usa apenas estoque de chaves e cadastro de usuários.
- **Recursos não utilizados.** O recurso por município veio vazio na fonte durante o desenvolvimento, e os recursos de transações e de fraude (MED) não foram usados.
- **Período curto de chaves.** A série de chaves cobre 22 meses, o que não permite falar em tendência de longo prazo.

## Tecnologias

SQL (SQLite), Python, pandas, Plotly, HTML/CSS/JavaScript, GitHub Pages e IA generativa (Claude) como apoio na construção.

## Autor

**Cauã Venseguerra Nascimento**: dados, BI e automação.
LinkedIn: [adicione aqui o link do seu perfil]
