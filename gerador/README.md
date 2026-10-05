# Gerador

O programa que recorta o build da Protomaps por estado, valida os pacotes e os publica.
**Já recorta, valida, monta o catálogo, sabe publicar e tem o agendamento escrito. Uma geração completa das 27
UFs já foi feita em casa e passou em todas as travas; nenhuma foi publicada, e o workflow da geração nunca
rodou no GitHub.** Hoje ele baixa a malha do IBGE, monta os polígonos
de recorte, escolhe o build, recorta os pacotes (o de cada estado, o leve e a base), monta o pacote de recursos
(ícones e fontes), passa tudo pelas travas de validação e escreve o `catalogo.json` da geração. O desenho completo está em [`../docs/ARQUITETURA.md`](../docs/ARQUITETURA.md) e
[`../docs/GERACAO.md`](../docs/GERACAO.md); o que falta, em [`PENDENCIAS.md`](PENDENCIAS.md).

## O que é preciso

- Python 3.9 ou mais novo (testado no 3.12).
- As dependências de [`requirements.txt`](requirements.txt): `pip install -r requirements.txt`.
- O binário `pmtiles` na versão fixada em [`carcara/config.py`](carcara/config.py). O script abaixo baixa o
  arquivo da release da ferramenta, confere o sha256 e deixa o binário em `data/ferramentas/`:

  ```
  python scripts/install_pmtiles.py
  ```

  Depois, aponte a variável `CARCARA_PMTILES` para o caminho que ele imprime (ou ponha o binário no `PATH`). Outra
  versão do `pmtiles` é recusada: o gerador lê o que a ferramenta escreve, e isso foi conferido nesta versão.

## Testes

Da pasta `gerador/`:

```
python -m unittest discover -s tests -t .
```

Nenhum teste usa a internet nem o build da Protomaps: os downloads são exercitados contra um servidor local que
os próprios testes sobem. A ferramenta `pmtiles` é simulada na maior parte dos testes; os de
`tests/test_extraction_real.py` usam o binário de verdade sobre um arquivo pequeno do repositório
(`tests/fixtures/bairro.pmtiles`) e são pulados, com o motivo, se o binário da versão fixada não for encontrado.

## Gerar os pacotes

```
python generate.py --states DF,GO      # só estas UFs e a base: cerca de 290 MB baixados, 2 a 3 minutos
python generate.py                     # as 27 UFs: cerca de 4,9 GB baixados, perto de meia hora
python generate.py --no-light          # sem os pacotes leves
python generate.py --accept-drop       # passa por cima da trava de queda
```

Os arquivos saem em `data/dist/`: `carcara-<UF>.pmtiles` (zoom 0 a 15), `carcara-<UF>-leve.pmtiles` (zoom 0 a 13,
recortado do completo, sem baixar nada a mais), `carcara-base.pmtiles` (o país, zoom 0 a 9) e
`carcara-recursos.tar.gz`. Cada arquivo é conferido com `pmtiles verify` e pelo cabeçalho.

- `pacotes.json` anota cada pacote assim que ele fica pronto. Se a geração cair no meio, rodar de novo **continua
  de onde parou**, desde que o build seja o mesmo. Com um build mais novo, tudo começa de novo.
- `geracao.json` guarda o tempo de cada etapa, o pico de disco e os bytes baixados.
- `GERACAO_EM_ANDAMENTO` existe enquanto a geração roda. Se ficou lá, a geração caiu.

O mesmo build dá sempre os mesmos arquivos, byte a byte.

Uma geração completa, medida em 2026-10-01 numa conexão doméstica (build `20261001.pmtiles`):

| Item | Valor |
|---|---|
| Arquivos | 56: 27 completos (4,62 GB), 27 leves (1,27 GB), a base (44 MB) e os recursos (6 MB) |
| Total | 5,94 GB |
| Baixado do build | 4,88 GB, em 5.372 pedidos, com 4 em paralelo |
| Tempo | 26 minutos medidos, com 3 dos 28 recortes reaproveitados de antes; somando o tempo deles, cerca de 28,5. Os recortes somam 25 minutos e as travas, 1,6 |
| Pico de disco em `data/` | 6,3 GB |
| Maior arquivo | Minas Gerais, 594 MB |

Os tamanhos de cada estado estão em [`PENDENCIAS.md`](PENDENCIAS.md).

Na máquina do GitHub Actions (`ubuntu-24.04`, 2 processadores, 7,8 GB de memória, 14 GB livres em disco), a
primeira geração completa, em 2026-10-02: 8,8 minutos para gerar e 4,7 para publicar; 4,88 GB baixados do build; pico de 5,95 GB em disco; pico de 1,1 GB de memória em uso (amostras a cada 30 s). É uma medição só; a rede de lá é bem mais rápida que a
de casa.

No fim, a geração passa pelas **travas** descritas em [`../docs/GERACAO.md`](../docs/GERACAO.md): estrutura,
cabeçalho, conteúdo, divisa, tamanho, queda, versão, completude e recursos. Se alguma barra, o comando termina com
código 1 e lista os problemas. Uma geração de só algumas UFs passa pelas travas, mas sai marcada como parcial.

Com as travas passando, sai `data/dist/catalogo.json`, no formato descrito em
[`../docs/ARQUITETURA.md`](../docs/ARQUITETURA.md): o índice que quem usa os pacotes lê. Ele só vai para a raiz
do repositório, junto com a tabela de downloads do README, na publicação.

## Publicar

```
python scripts/publish.py                             # só confere; nada é publicado
python scripts/publish.py --release --commit --push   # sobe a release, grava o catálogo e a tabela, envia
python scripts/publish.py --prune --dry-run           # lista as releases antigas que a limpeza apagaria
```

Usa o `gh` (GitHub CLI) já logado. A ordem é esta, e cada passo só acontece se o anterior deu certo:

1. as travas da publicação: geração completa (as 27 UFs), sem a marca `GERACAO_EM_ANDAMENTO`, cada arquivo no
   disco com o tamanho e o sha256 do catálogo, nenhuma queda além da tolerância, build não mais antigo que o da
   geração publicada;
2. a release sobe como **rascunho**; cada arquivo que falta, ou que está com outro tamanho ou outro sha256, é
   enviado; a release só é publicada quando o GitHub informa o tamanho e o sha256 certos de todos;
3. o `catalogo.json` e a tabela de downloads do README são gravados na raiz e vão num commit só deles;
4. depois do push, as releases antigas são apagadas: ficam a do catálogo e as anteriores mais recentes, 3 no
   total. Só etiquetas no formato do `build_id` entram; a do catálogo publicado nunca; falha aqui vira aviso.

Se a subida cair no meio, fica um rascunho que ninguém vê, e rodar de novo retoma do que falta.

## Agendamento

O workflow [`gerar.yml`](../.github/workflows/gerar.yml) roda todo dia e pergunta ao `scripts/due.py` se está na
hora:

```
python scripts/due.py            # lê o catalogo.json da raiz; gera se a geração publicada tem 29 dias ou mais
python scripts/due.py --manual   # disparo à mão: sempre gera
```

- **Sem `catalogo.json` na raiz, o agendamento não gera.** A primeira geração é disparada à mão (Actions, `gerar`,
  "Run workflow"), e só publica com a opção `publish` marcada.
- Com um catálogo que não dá para ler, não gera e o job fica vermelho.
- No agendamento, a geração que passa pelas travas é publicada. À mão, sem `publish`, só gera e valida; o
  relatório (`geracao.json`, `catalogo.json`, `pacotes.json` e o uso de memória e disco) fica nos artefatos do run.

## Medir o tamanho dos pacotes

```
python scripts/measure.py                               # as 27 UFs, nos zooms 15 e 13
python scripts/measure.py --areas DF,GO --zooms 15
python scripts/measure.py --areas brasil --zooms 7,8,9,10
```

Usa `pmtiles extract --dry-run`: lê só os diretórios do build, **não baixa nenhum tile**, e diz quantos tiles e
quantos bytes cada recorte teria. O resultado vai para `data/medicoes/tamanhos_<build>.json`.

## O que há em cada arquivo

| Arquivo | O que faz |
|---|---|
| `carcara/config.py` | Tudo o que muda o resultado: endereços, zooms, margem, versão da ferramenta, intervalo, gerações mantidas |
| `carcara/net.py` | Download com retomada e novas tentativas |
| `carcara/sources.py` | O build mais recente do índice da Protomaps e a malha das UFs do IBGE, os dois conferidos |
| `carcara/regions.py` | O polígono de cada UF com a margem e o do Brasil, gravados como GeoJSON |
| `generate.py` | Ponto de entrada da geração |
| `carcara/extraction.py` | O `pmtiles extract` (simulação e recorte de verdade), o cabeçalho, os metadados e a conferência de um arquivo |
| `carcara/packs.py` | Os pacotes de uma geração: estado, leve e base; anota o que já foi feito e reaproveita |
| `carcara/run_record.py` | O registro da geração: tempos, pico de disco, bytes baixados |
| `carcara/validation.py` | As nove travas antes de publicar |
| `carcara/catalog.py` | O `catalogo.json` da geração e a tabela de downloads do README |
| `carcara/publishing.py` | As travas da publicação, a release em rascunho, a conferência e a limpeza das antigas |
| `scripts/publish.py` | Linha de comando da publicação |
| `carcara/schedule.py` | A regra dos 29 dias: quando o agendamento gera, e quando não |
| `scripts/due.py` | Linha de comando da regra, chamada pelo workflow `gerar` |
| `carcara/mvt.py` | O mínimo de leitura de um tile vetorial: camadas e número de feições |
| `carcara/pmtiles_tool.py` | Instala o `pmtiles` fixado e recusa outra versão |
| `carcara/resources.py` | Monta o pacote de ícones e fontes, de uma revisão fixa, com o conteúdo conferido |
| `licencas/` | Textos de licença que vão dentro do pacote de recursos |
| `scripts/install_pmtiles.py` | Linha de comando da instalação |
| `scripts/measure.py` | Linha de comando da medição |
| `tests/` | Os testes, um arquivo por módulo, mais os que conferem os workflows e o próprio repositório |

## Variáveis de ambiente

| Variável | Para quê | Padrão |
|---|---|---|
| `CARCARA_PMTILES` | Caminho do binário `pmtiles` | `pmtiles`, no `PATH` |
| `CARCARA_KEEP_GENERATIONS` | Quantas gerações ficam nas releases (0 = não apaga) | 3 |
| `CARCARA_LIGHT` | `0` desliga os pacotes leves | ligado |
| `CARCARA_MIN_FREE_DISK_GB` | Espaço livre exigido antes de recortar | 12 |
| `CARCARA_REPO` | O repositório das releases, para os links do catálogo (`dono/nome`) | o do GitHub Actions, senão o oficial |

O número de pedidos em paralelo ao build da Protomaps (4) **não** tem variável: o build é um serviço gratuito e
não é para ser apressado.

## Convivência com a Protomaps

- O endereço do build vem sempre do índice (`builds.json`), nunca montado com a data.
- Quatro pedidos em paralelo, o padrão da ferramenta.
- Uma geração completa baixa cerca de 4,9 GB. Para desenvolver e testar, use um ou dois estados pequenos.

## Onde ficam os dados

Tudo o que o gerador baixa ou produz vai para `data/`, que fica fora do git:

| Pasta | Conteúdo |
|---|---|
| `data/raw/` | Malha do IBGE; arquivo de recursos baixado |
| `data/dist/` | Os pacotes prontos, `catalogo.json`, `pacotes.json` e `geracao.json` |
| `data/regioes/` | Um GeoJSON por UF e o do Brasil |
| `data/medicoes/` | Resultados das medições |
| `data/ferramentas/` | O binário `pmtiles` instalado pelo script |

## Licença

O código do gerador é MIT ([`LICENSE`](LICENSE)). Os pacotes que ele vai produzir são ODbL 1.0
([`../LICENSE`](../LICENSE)).
