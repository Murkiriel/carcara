# Arquitetura

Desenho proposto em 2026-10-01. Nada disto existe ainda. Os números marcados como "a medir" dependem das
medições de [`PENDENCIAS.md`](../gerador/PENDENCIAS.md).

O projeto usa só a **etapa A** (recorte do build da Protomaps). Onde este documento fala da etapa B, é registro
de uma possibilidade sem data ([`DECISOES.md`](DECISOES.md), D6): o formato do catálogo já reserva os campos
dela para não precisar mudar depois.

## Visão geral

```
build diário da Protomaps (etapa A)          malha das UFs (IBGE)
   ou extrato do Brasil + Planetiler (B)              │
                    │                                 │
                    └────────────► gerador ◄──────────┘
                                      │
              recorta por estado, valida, calcula sha256, monta o catálogo
                                      │
            ┌─────────────────────────┴─────────────────────────┐
     release <build_id>                                   catalogo.json (raiz)
     carcara-base.pmtiles                                 aponta para a release
     carcara-<UF>.pmtiles (27)                            mais recente
     carcara-<UF>-leve.pmtiles (27)
     carcara-recursos.tar.gz
```

## Pacotes

| Arquivo | Conteúdo | Zoom |
|---|---|---|
| `carcara-base.pmtiles` | O Brasil inteiro em zoom baixo: visão geral do país para onde não há estado instalado | 0 a 9 (44 MB na medição M2, contra 15 MB até o zoom 8 e 106 MB até o 10) |
| `carcara-<UF>.pmtiles` | Um por estado e o DF (27): todos os tiles que tocam o polígono da UF, com margem. De 24 MB (AP) a 594 MB (MG); 4,6 GB os 27 | 0 a 15 |
| `carcara-<UF>-leve.pmtiles` | O mesmo estado, só até o zoom 13, para quem tem pouco espaço: cerca de 27% do tamanho do completo. De 7 MB (DF) a 183 MB (MG); 1,27 GB os 27 | 0 a 13 |
| `carcara-recursos.tar.gz` | Ícones (`sprites/v4/`) e fontes dos rótulos (`fonts/`) da mesma versão do esquema, com as licenças e um `LEIAME.md`. 6,2 MB | não se aplica |

### Por que o pacote de estado começa no zoom 0

Dois motivos:

- **O pacote funciona sozinho.** Quem baixa só Goiás tem um mapa utilizável de Goiás, do zoom mais aberto ao
  mais fechado, sem depender da base.
- **É o recorte barato.** O `pmtiles extract` copia uma pirâmide do zoom 0 ao máximo com poucos pedidos; pedir um
  zoom mínimo maior que zero "pode exigir muito mais pedidos" (documentação do comando).

O custo é pequeno. Na medição M2, os zooms 0 a 9 de Goiás são 135 tiles e 3,2 MB num pacote de 182 MB; nos seis
estados medidos ficam entre 1% e 2% do pacote, e em 5% no menor de todos (Amapá). A alternativa, o pacote de
estado só com os zooms acima da base, obrigaria a ter sempre a base instalada para economizar isso.

### Zoom máximo

O esquema da Protomaps vai até o zoom 15. Acima disso não existe dado: quem desenha amplia o tile do zoom 15.
Nenhum pacote de estado é publicado com menos que o zoom 15. Se um estado não couber no limite de 2 GiB por
arquivo, ele é **dividido** em mais de um arquivo; reduzir o zoom em silêncio não é opção. Hoje nenhum chega
perto: o maior tem 592 MB.

### Pacote leve

Além do completo, cada estado tem um pacote **leve**, até o zoom 13. É o mesmo recorte com menos zooms: sem o
detalhe de rua dos zooms 14 e 15. Serve para quem tem pouco espaço ou quer o estado inteiro só como visão geral.

- O leve é recortado do arquivo completo já baixado; não custa nada a mais ao build da Protomaps.
- Completo e leve do mesmo estado não se somam: o completo contém tudo o que o leve tem. Quem instala o completo
  pode apagar o leve.
- A regra que decidiu (2026-10-01): publicar o leve se algum estado completo passasse de 500 MB na medição M1.
  Minas Gerais passou (592 MB). É padrão de trabalho, ainda sem confirmação do dono; desligar é uma opção do
  gerador.

### Recorte por estado

- Polígono da UF pela malha oficial do IBGE (API de malhas, versão 3), com margem de 0,05° (cerca de 5 km): a
  mesma malha e a mesma margem dos tiles de roteamento.
- Entram no pacote os tiles que tocam o polígono com a margem. O tile entra **inteiro**, sem cortar o conteúdo na
  linha da divisa (conferido na medição M4).
- O tile de divisa vem nos dois pacotes vizinhos. Na mesma geração, é o mesmo conteúdo nos dois, byte a byte
  (conferido na M4, entre o DF e Goiás).
- A base usa o polígono do Brasil.

## Geração e `build_id`

Cada geração tem um `build_id`, que também é a etiqueta da release:

```
AAAA-MM-DD-xxxxxxxx
```

- **Etapa A:** a data é a do build da Protomaps usado, e os 8 caracteres são os primeiros do `b3sum` desse build.
- **Etapa B:** a data é a do extrato do OpenStreetMap, e os 8 caracteres são os primeiros do md5 do extrato, como
  nos tiles de roteamento. Com o mesmo extrato, os dois projetos terão o mesmo `build_id`.

O formato é o mesmo dos projetos irmãos, e a limpeza de releases antigas só toca etiquetas nesse formato.

Gerações diferentes podem conviver no mesmo aparelho (decisão D10). O que identifica compatibilidade é a
versão do esquema, não o `build_id`.

## `catalogo.json`

O formato, com `"schema": 1`. Chaves em inglês. É o que `gerador/carcara/catalog.py` escreve; um teste confere
que toda chave do catálogo está descrita aqui.

```
schema             versão deste formato (1)
build_id           a geração: AAAA-MM-DD-xxxxxxxx, também o nome da release
built_at           quando foi gerada (UTC)
generator_commit   commit do gerador que produziu a geração
tileset            o esquema dos tiles
  name             "protomaps-basemap"
  version          versão do esquema que gerou os tiles (ex.: "4.15.2"); quem consome confere a versão maior
  extensions       acréscimos próprios ao esquema, se houver (etapa B); lista vazia na etapa A
source             de onde os tiles vieram
  kind             "protomaps-build" (etapa A) ou "osm-extract" (etapa B)
  timestamp        data do build ou do extrato
  url              endereço do build ou do extrato
  checksum         b3sum do build (A) ou md5 do extrato (B)
  osm_timestamp    data dos dados do OpenStreetMap que o build usou (lida dos metadados dos pacotes)
tile_format        "mvt"
tile_compression   "gzip"
release_url        onde baixar os arquivos desta geração
attribution        crédito obrigatório dos dados
resources          o pacote de ícones e fontes: file, bytes, sha256
base               o pacote base (campos abaixo)
states             {UF: pacote}, um por estado
  name             nome do estado (só em states)
  file             nome do arquivo na release
  bytes            tamanho do arquivo
  sha256           para conferir o download
  tiles            quantos tiles endereçados o pacote tem
  minzoom, maxzoom zooms do pacote
  bbox             área que o pacote atende: o polígono da UF no IBGE (na base, o Brasil),
                   [lat mín, lon mín, lat máx, lon máx], arredondado para fora; use para escolher o que baixar
  bbox_tiles       área coberta pelos tiles do zoom mais fundo do pacote, na mesma ordem do bbox
                   (maior que o bbox: o recorte leva a margem e os tiles passam da divisa)
  light            o pacote leve do estado (só em states, opcional): file, bytes, sha256, tiles, minzoom, maxzoom
```

Pontos do contrato:

- **`tileset.version`** faz o papel que a versão do motor faz nos tiles de roteamento. Quem consome deve recusar
  uma versão **maior** (o primeiro número) que não conhece. Versões menores só acrescentam.
- **`bbox` na ordem latitude, longitude**, igual ao catálogo dos tiles de roteamento, para a mesma conta servir
  aos dois. O cabeçalho do PMTiles usa longitude primeiro; não confundir os dois.
- **Estado dividido em mais de um arquivo:** não é preciso hoje (o maior estado tem 592 MB, medição M1) e não
  entra no formato. Se um dia for, `file`, `bytes` e `sha256` passariam a ser uma lista em `parts`, e isso sobe
  o `schema`. Até lá, a trava de tamanho barra a publicação de um arquivo perto de 2 GiB.
- **`light` é opcional.** Um leitor que não conhece a chave a ignora e continua vendo o pacote completo em
  `file`. Por isso o pacote leve pode entrar ou sair de uma geração sem subir o `schema`.
- **`schema` só sobe** quando um leitor antigo quebraria (chave renomeada ou removida, nome de arquivo que muda).
  Chave nova que um leitor antigo pode ignorar não sobe.

## Releases

- Uma release por geração, com a etiqueta `build_id`. São 56 arquivos: a base, os 27 estados completos, os 27
  leves e os recursos. Cerca de 5,9 GB por geração.
- O `catalogo.json` da raiz aponta sempre para a geração mais recente. Quem consome usa o `release_url` do
  catálogo, nunca um link fixo.
- Ficam no ar as 3 gerações mais recentes (cerca de 18 GB); as anteriores são apagadas depois de cada
  publicação.
- Limites do GitHub, conferidos em 2026-10-01: cada arquivo abaixo de 2 GiB, até 1.000 arquivos por release, sem
  limite para o tamanho total nem para o tráfego.
- A release é criada como rascunho e só é publicada com todos os arquivos enviados e conferidos. Um envio que
  cai deixa um rascunho, que a limpeza remove.

## Estrutura prevista do repositório

```
carcara/
├── README.md                 o que é, tabela de downloads, como usar, catálogo, licença
├── catalogo.json             índice da geração mais recente (escrito pelo robô)
├── LICENSE                   ODbL 1.0 (dados)
├── docs/                     estes documentos
├── gerador/
│   ├── README.md             como instalar, testar e medir                            (existe)
│   ├── LICENSE               MIT (código)                                             (existe)
│   ├── requirements.txt                                                               (existe)
│   ├── generate.py           ponto de entrada da geração                    (existe: recorta e valida)
│   ├── carcara/
│   │   ├── config.py         endereços, zooms, margem, ferramenta, intervalo, gerações (existe)
│   │   ├── net.py            download com retomada e novas tentativas                 (existe)
│   │   ├── sources.py        build da Protomaps pelo índice, malha do IBGE            (existe)
│   │   ├── regions.py        polígonos das UFs com margem, GeoJSON para o recorte     (existe)
│   │   ├── extraction.py     chama o pmtiles extract e lê o que ele informa           (existe)
│   │   ├── packs.py          os pacotes de uma geração: estado, leve e base           (existe)
│   │   ├── pmtiles_tool.py   instala o pmtiles fixado e recusa outra versão           (existe)
│   │   ├── resources.py      monta o pacote de ícones e fontes                        (existe)
│   │   ├── validation.py     as travas antes de publicar                              (existe)
│   │   ├── mvt.py            lê as camadas de um tile, para as travas                 (existe)
│   │   ├── catalog.py        monta o catalogo.json e a tabela do README               (existe)
│   │   ├── publishing.py     release em rascunho, envio, publicação, limpeza das antigas (existe)
│   │   ├── schedule.py       a regra dos 29 dias; sem geração publicada, não gera     (existe)
│   │   └── run_record.py     tempos e uso de máquina da geração                       (existe)
│   ├── scripts/
│   │   ├── install_pmtiles.py   instala a ferramenta, com o sha256 conferido          (existe)
│   │   ├── measure.py           simula os recortes e registra os tamanhos             (existe)
│   │   ├── publish.py           linha de comando da publicação                        (existe)
│   │   └── due.py               diz ao workflow se está na hora de gerar              (existe)
│   ├── licencas/             textos de licença que vão dentro do pacote de recursos   (existe)
│   ├── tests/                                                                         (existe)
│   └── data/                 fora do git: downloads, pacotes, medições, a ferramenta
└── .github/workflows/
    ├── gerar.yml             geração agendada e à mão                                 (existe)
    └── testes.yml            testes do gerador                                        (existe)
```

O que está marcado "(existe)" já está no repositório; o resto é previsto. Desde 2026-10-05 (decisão X10 de
[`PENDENCIAS.md`](../gerador/PENDENCIAS.md)), `FONTES.md` e `PENDENCIAS.md` ficam em `gerador/`, junto do código que
eles medem e explicam; os outros documentos ficam em `docs/`.

## Licenças e crédito

| Parte | Licença | Observação |
|---|---|---|
| Pacotes de mapa | ODbL 1.0 | Base derivada do OpenStreetMap. Crédito: "© colaboradores do OpenStreetMap" |
| Tiles da etapa A | ODbL (o README da Protomaps diz "Tilesets are ODbL"; a página de downloads diz "Produced Work") | As duas fontes pedem crédito ao OpenStreetMap. Redação conferida em 2026-10-02 ([`FONTES.md`](../gerador/FONTES.md)) |
| Camada `landcover` dos tiles (zooms 0 a 7) | CC BY 4.0 | Derivada do ESA WorldCover. Crédito: "© ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium" |
| Perfil de geração da Protomaps (etapa B) | BSD-3 | Manter o aviso de licença se o gerador embutir ou alterar o perfil |
| Desenho dos estilos da Protomaps | CC0 | |
| Fontes do pacote de recursos | SIL Open Font License | Noto Sans Regular, Medium e Italic |
| Ícones do pacote de recursos | derivados de um conjunto MIT | Manter o aviso |
| Malha das UFs | IBGE | Citar a fonte |
| Código do gerador | MIT | |

Texto de crédito do catálogo: `© colaboradores do OpenStreetMap (ODbL 1.0); cobertura do solo: © ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium
(CC BY 4.0); esquema e perfil: Protomaps; limites das UFs: IBGE`.
