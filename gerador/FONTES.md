# Fontes

De onde vem cada afirmação dos outros documentos. A primeira tabela é o que foi **conferido em 2026-10-01**, com
o endereço consultado. A segunda é o que foi escrito **de memória ou por raciocínio** e ainda precisa de
conferência. Ao conferir um item da segunda tabela, movê-lo para a primeira com a data.

## Conferido em 2026-10-01

### Build diário da Protomaps

Lido de `https://build-metadata.protomaps.dev/builds.json`.

| Item | Valor |
|---|---|
| Entradas no índice | 62 (a mais antiga é `20230918.pmtiles`); não vêm em ordem de data |
| Build mais recente | `20261001.pmtiles`, enviado em 2026-10-01 08:53 UTC |
| Tamanho | 138.507.309.367 bytes (138,5 GB) |
| Versão do esquema | 4.15.2 |
| Campos de cada entrada | `key`, `size`, `md5sum` (base64), `b3sum` (hexadecimal), `uploaded`, `version` |
| Os dois builds anteriores | `20260930` e `20260929`, também 4.15.2, com tamanhos crescendo ~30 MB por dia |

Lido de `https://docs.protomaps.com/basemaps/downloads`.

| Item | O que a página diz |
|---|---|
| Conteúdo | "A full planet file is roughly 120 gigabytes, including zoom levels from 0 to 15." (o índice mostra 138,5 GB hoje) |
| Retenção | "All builds for the past week. The latest build for each patch version" |
| Uso do endereço | "URLs may change and hotlinking to these downloads are discouraged. Instead, you should copy the tileset to your own Cloud Storage." |
| Recorte | "To download a cutout of a specific region […] see the CLI's extract command." |
| Licença | "distributed as an Open Database License Produced Work (OpenStreetMap attribution required)" |
| Estilos | "compatible with @protomaps/basemaps style v4.0.0 and newer" |

### Ferramenta `pmtiles`

Lido de `https://docs.protomaps.com/pmtiles/cli` e do código-fonte
(`https://github.com/protomaps/go-pmtiles`, arquivo `main.go`).

| Item | Valor |
|---|---|
| Recorte de arquivo remoto | Sim: `pmtiles extract https://…/INPUT.pmtiles OUTPUT.pmtiles …` |
| `--region` | GeoJSON Polygon, MultiPolygon, Feature ou FeatureCollection, em arquivo local |
| `--bbox` | `MIN_LON,MIN_LAT,MAX_LON,MAX_LAT` |
| `--maxzoom` | "Extracting a full sub-pyramid from 0 to maxzoom is always an efficient operation that makes minimal I/O or network requests." |
| `--minzoom` | "Extract only a partial sub-pyramid. This may require many more requests than leaving the default --minzoom=0." |
| `--download-threads` | Padrão 4 |
| `--overfetch` | Padrão 0,05 |
| `--dry-run` | Existe no código ("Calculate tiles to extract, but don't download them"); não aparece na página de documentação |
| Requisito | O arquivo de origem precisa estar "clustered" |
| Outros comandos | `show` (cabeçalho e metadados), `verify`, `serve`, `convert`, `tile` |

Conferido também no binário da versão 1.31.2 (release `v1.31.2`, com o sha256 do arquivo igual ao publicado na
release), pela ajuda dos comandos:

| Item | Valor |
|---|---|
| `extract --help` | Lista `--region`, `--bbox`, `--minzoom`, `--maxzoom`, `--download-threads` (4), `--dry-run` e `--overfetch` (0,05) |
| `show --help` | Tem `--header-json` (parte do cabeçalho em JSON), `--metadata` e `--tilejson` |
| Comandos além dos listados acima | `cluster`, `edit`, `merge` (junta arquivos sem sobreposição em um só), `upload` |

### Perfil de geração da Protomaps

Lido de `https://github.com/protomaps/basemaps`.

| Item | Valor |
|---|---|
| O que é | "A Planetiler build profile that generates planet.pmtiles from OpenStreetMap and Natural Earth in 2-3 hours" |
| Requisito | Java 21 ou mais novo |
| Exemplo de comando | `java -jar target/*-with-deps.jar --download --force --area=monaco` |
| Licenças | Código BSD-3; "Tilesets are ODbL, attribute OSM"; "Map design is CC0" |
| Recursos | Fontes e ícones no repositório `basemaps-assets` |

### Esquema de camadas

Lido de `https://docs.protomaps.com/basemaps/layers`.

| Item | Valor |
|---|---|
| Camadas listadas | `boundaries`, `buildings`, `earth`, `landcover`, `landuse`, `places`, `pois`, `roads`, `transit` (vazia hoje), `water` |
| Atributos de `roads` | `kind`, `kind_detail`, `ref`, `shield_text`, `network`, `oneway`, `service`, `is_link`, `is_tunnel`, `is_bridge` |
| Superfície da via | Nenhum atributo de pavimento documentado em nenhuma camada |
| Atributos de `pois` | `kind`, `cuisine`, `religion`, `sport`, `iata`, `wikidata`; os mais conhecidos sobem para zooms mais baixos |

A lista de camadas veio de um resumo da página. Há estilos em uso que leem uma camada `physical_point` (picos),
que não aparece nesse resumo; na versão 4.15.2 ela também não aparece nos metadados nem nos tiles lidos (seção
"Recorte de verdade"), e a `transit`, listada na página como vazia, tampouco.

### Estilos de referência

Lido de `https://github.com/protomaps/basemaps`, `styles/src/base_layers.ts` e `styles/src/language.ts`, na
revisão `42ffaaa4a85a41bfcb23e43cc0f5b492a5eca123` (2026-09-11).

| Item | Valor |
|---|---|
| Camadas que o estilo lê | `earth`, `landcover`, `landuse`, `water`, `buildings`, `boundaries`, `roads`, `places`, `pois` |
| Fontes pedidas | `Noto Sans Regular`, `Noto Sans Medium` e `Noto Sans Italic` |
| Fonte para outra escrita | Uma feição cujo nome só existe em devanágari pede `Noto Sans Devanagari Regular v1`, em qualquer idioma do estilo. O pacote de recursos não a traz |
| Ícones fixos | `arrow` (mão única), `townspot` e `capital` (lugares) |
| Escudos de rodovia | `generic_shield-<n>char`, e `US:I-<n>char` e `NL:S-road-<n>char` para essas duas redes, com `n` igual ao número de caracteres do `shield_text`. A folha tem de 1 a 5 |
| Ícones de pontos de interesse | O `kind` do ponto, para 36 tipos (`station` vira `train_station`). Só as variações com pontos de interesse os desenham |
| Falha da origem | O estilo pede o ícone `townhall`, e a folha de ícones não o tem |

### Recursos (ícones e fontes)

Lido de `https://github.com/protomaps/basemaps-assets`.

| Item | Valor |
|---|---|
| Fontes | Noto Sans Regular, Medium e Italic, em PBF por faixa |
| Endereço das fontes | `https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf` |
| Ícones | Folhas de ícones por versão maior, em variações clara e escura, em 1x e 2x |
| Licenças | Fontes: SIL Open Font License. Ícones: derivados de um conjunto MIT |

Conferido de novo ao montar o pacote, na revisão `028c18f713baecad011301ff7a69acc39bcc2ae7` (2025-10-31), lendo
o arquivo do repositório inteiro:

| Item | Valor |
|---|---|
| `fonts/` | Quatro pastas, 256 faixas cada: `Noto Sans Regular` (6,2 MB), `Noto Sans Medium` (3,6 MB), `Noto Sans Italic` (1,2 MB) e `Noto Sans Devanagari Regular v1`; mais `fonts/OFL.txt` |
| `Noto Sans Devanagari Regular v1` | Só quatro faixas são arquivos de verdade; as outras 252 são links para a mesma faixa da `Noto Sans Regular` |
| `sprites/v4/` | Cinco variações (`light`, `dark`, `white`, `grayscale`, `black`), cada uma com `.json` e `.png`, em 1x e 2x: 20 arquivos, 147 KB |
| `sprites/v3/` | Os mesmos 20 nomes, mas com 64 a 300 bytes cada: sobras, sem ícones. O README do repositório ainda cita esta pasta |
| Ícones nas folhas `white`, `grayscale` e `black` | 18: só a seta, o ponto de cidade, o de capital e os escudos |
| Ícones na folha `light` da versão 4 | 53, entre eles os escudos de rodovia por número de caracteres (`generic_shield-1char` a `-5char`), `peak`, `townspot`, `capital`, `aerodrome`, `bus_stop`, `train_station` e pontos de interesse como `restaurant`, `school`, `supermarket`. Não há ícone de posto de combustível |
| Licença dos scripts do repositório | BSD-3 (`scripts/LICENSE.md`); os scripts não entram no pacote |
| Texto da licença MIT do conjunto de ícones de origem | Não está no repositório de recursos; foi buscado no repositório do conjunto (`tangrams/icons`, "Copyright (c) 2017 Mapzen") e vai dentro do pacote |

O pacote montado dessa revisão (`carcara-recursos.tar.gz`): 791 arquivos, 6.155.919 bytes. Montado duas vezes, sai
idêntico byte a byte.

### MapLibre

Lido de `https://maplibre.org/maplibre-native/android/examples/data/PMTiles/`.

| Item | Valor |
|---|---|
| Suporte | "Starting MapLibre Android 11.7.0, PMTiles archives are supported as tile sources." |
| Formas | `pmtiles://https://`, `pmtiles://file://`, `pmtiles://asset://` |

### Leitor em Java

Conferido no próprio arquivo `.jar` da biblioteca `ch.poole.geo.pmtiles-reader`, versão 0.3.6.

| Item | Valor |
|---|---|
| Abrir arquivo local | `Reader(java.io.File)` e `Reader(java.nio.channels.FileChannel)` |
| Ler | `getTile(int, int, int)` devolve `byte[]` |
| Cabeçalho | `getTileCompression()`, `getTileType()`, `getMinZoom()`, `getMaxZoom()`, `getBounds()`, `getMetadata()` |

### Releases do GitHub

Lido de `https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases`.

| Item | Valor |
|---|---|
| Tamanho por arquivo | "Each file included in a release must be under 2 GiB." |
| Arquivos por release | Até 1.000 |
| Tamanho total e tráfego | "There is no limit on the total size of a release, nor bandwidth usage." |
| O que o `gh release view --json assets` informa de cada arquivo (versão 2.100.0 do `gh`, numa release pública de outro projeto) | Entre outros campos, `name`, `size` e `digest` (`sha256:<64 hexadecimais>`). É com o `digest` que a publicação confere o que subiu |
| Release que não existe | O `gh release view` sai com código 1 e a mensagem "release not found" |

### Dos projetos irmãos

Lido do código do gerador dos tiles de roteamento.

| Item | Valor |
|---|---|
| Extrato do Brasil | `https://download.openstreetmap.fr/extracts/south-america/brazil-latest.osm.pbf`, com a data em `brazil.state.txt` e o md5 em `brazil.osm.pbf.md5` na mesma pasta |
| Malha das UFs | API de malhas do IBGE, versão 3 (`https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR…`), com o código da UF em `codarea` |
| Margem do recorte | 0,05° |
| Intervalo entre gerações | 29 dias |
| Gerações mantidas | 3 |

### Contas sobre tiles

| Item | Valor | De onde |
|---|---|---|
| Tiles no retângulo de Goiás, zoom 8 a 15 | 602.806 (451.580 só no zoom 15) | Conta sobre o retângulo do estado |
| Tiles no retângulo de Goiás, zoom 8 a 13 | 37.996 | Idem |

São contas sobre o **retângulo**. O recorte pelo polígono dá menos.

### Tamanho dos pacotes (simulado)

Simulação de 2026-10-01 com `pmtiles extract --dry-run` sobre o build `20261001.pmtiles`, pelo polígono de cada
UF com a margem. A tabela das 27 UFs está em [`PENDENCIAS.md`](PENDENCIAS.md), seção da medição M1.

| Item | Valor |
|---|---|
| O que a simulação informa | Tiles da área, entradas no arquivo de saída, pedidos, bytes a baixar e tamanho do arquivo de saída. Os tamanhos saem arredondados, em unidades decimais ("48 MB", "1.2 GB") |
| O que a simulação baixa | Só os diretórios do build: de 33 a 516 pedidos por simulação, nenhum tile |
| Goiás pelo polígono, zoom 0 a 15 | 355.106 tiles, 182 MB (o retângulo, do zoom 8 ao 15, tem 602.806) |
| Soma dos 27 estados, zoom 0 a 15 | 8.582.282 tiles, 4.607 MB |
| Soma dos 27 estados, zoom 0 a 13 | 551.514 tiles, 1.267 MB |
| Maior e menor estado, zoom 0 a 15 | Minas Gerais, 592 MB; Amapá, 24 MB |
| Base (polígono do Brasil), zoom 0 a 9 | 2.295 tiles, 44 MB. Até o zoom 8, 15 MB; até o 10, 106 MB |
| Zooms 0 a 9 dentro de um pacote de estado | De 0,963 MB (DF) a 8,7 MB (MG): 1% a 2% do pacote, 5,4% no Amapá. Medido em 6 estados |
| Compressão de um tile | Os tiles lidos um a um do build (`pmtiles tile`) vêm em gzip. Conferido em 8 tiles, e depois no cabeçalho dos recortes (seção seguinte) |

### Recorte de verdade (medição M3)

Recortes feitos em 2026-10-01 do build `20261001.pmtiles`, com 4 pedidos em paralelo, numa conexão doméstica.

| Recorte | Tiles | Tempo | Pedidos | Baixado | Arquivo final | Simulado |
|---|---:|---:|---:|---:|---:|---:|
| Distrito Federal, zoom 0 a 15 | 7.868 | 15 s | 45 | 50 MB | 47.992.685 bytes | 48 MB |
| Goiás, zoom 0 a 15 | 355.106 | 71 s | 250 | 191 MB | 182.443.237 bytes | 182 MB |
| Base (Brasil), zoom 0 a 9 | 2.295 | 12 s | 45 | 46 MB | 44.282.829 bytes | 44 MB |

| Item | Valor |
|---|---|
| Simulação contra o arquivo real | Bateu nos três, dentro do arredondamento. "MB" na saída da ferramenta é 10⁶ bytes |
| `pmtiles verify` | Passou nos três |
| Cabeçalho dos recortes (`pmtiles show --header-json`) | `tile_type` `mvt`, `tile_compression` `gzip`, `minzoom` 0, `maxzoom` 15 (9 na base) |
| `bounds` do cabeçalho | É o retângulo do polígono de recorte, com a margem (no DF: −48,3357, −16,1000, −47,2585, −15,4518), em longitude e latitude. Não é a área coberta pelos tiles |
| "Clustered" | `clustered: true` nos três recortes e no build remoto |
| Tiles repetidos | Guardados uma vez: Goiás tem 355.106 tiles endereçados, 315.903 entradas e 286.121 conteúdos distintos |
| Dois recortes da mesma área do mesmo build | Idênticos byte a byte (o DF recortado duas vezes, mesmo sha256). Confirmado de novo pelo gerador: o DF, Goiás e a base saíram iguais aos da medição, horas depois |
| Pacote leve recortado do completo local (`--maxzoom=13`, sem região) | DF: 576 tiles, 7.082.704 bytes (simulado: 7 MB). Goiás: 22.896 tiles, 50.233.439 bytes (simulado: 50 MB). Nenhum pedido ao build |
| Código de saída da ferramenta | 1 quando o recorte, o `verify` ou o `show` falham (origem que não existe, arquivo truncado, arquivo que não é PMTiles); 0 quando dão certo |
| Metadados que o recorte herda do build | `version` (4.15.2), `name`, `attribution`, `description`, `vector_layers`, e os do Planetiler, entre eles `planetiler:osm:osmosisreplicationtime` (a data dos dados do OpenStreetMap: 2026-10-01T04:00:00Z) |
| Camadas declaradas em `vector_layers` | 9: `boundaries`, `buildings`, `earth`, `landcover`, `landuse`, `places`, `pois`, `roads`, `water`. Não aparecem `transit` nem `physical_point` |
| Camadas encontradas em 128 tiles de Goiás (zoom 0 a 15, quatro pontos, um deles um pico) | As mesmas 9, e nenhuma outra |
| Atributos de `roads` em `vector_layers` | Os da documentação, mais `access`, `route`, `min_zoom`, `sort_rank`, nomes por idioma (`name:pt` e outros) e as variações numeradas de `network` e `shield_text`. Nenhum de superfície |

O build remoto, por `pmtiles show`: versão 3 do formato, `mvt`, zoom 0 a 15, 1.431.655.765 tiles endereçados, gzip,
`clustered: true`, versão 4.15.2.

### Tile de divisa (medição M4)

Conferido em 2026-10-01 nos recortes do Distrito Federal e de Goiás da medição M3, lendo tile a tile com
`pmtiles tile`.

| Item | Valor |
|---|---|
| Tiles do pacote do DF | 7.868, do zoom 0 ao 15 (o mesmo número do cabeçalho) |
| Tiles do DF que também estão no pacote de Goiás | 4.177 (53%): a margem de Goiás entra 5 km no DF, e nos zooms baixos um tile cobre os dois |
| Comparação dos 4.177, byte a byte | Todos idênticos nos dois pacotes; nenhum diferente, em nenhum zoom |
| Amostra contra o build remoto | 7 tiles (três do zoom 15 e um de cada um dos zooms 12, 9, 5 e 0): idênticos ao build nos dois pacotes |

Conclusão: o `pmtiles extract --region` copia o tile **inteiro**, como está no build, sem cortar o conteúdo na
borda da região. O tile de divisa é o mesmo nos pacotes vizinhos de uma mesma geração.

### Leitura em um aparelho (medição M5)

Conferido em 2026-10-01 com o pacote do Distrito Federal da medição M3, copiado para um emulador Android
(x86_64, Android 16), com o MapLibre 13.4.1 e o leitor Java `ch.poole.geo.pmtiles-reader` 0.3.6.

| Item | Valor |
|---|---|
| Leitor Java, `Reader(File)` no arquivo local | Abre. Cabeçalho: tiles MVT, compressão gzip, zoom 0 a 15 |
| `getBounds()` | Oeste, sul, leste, norte; contém o centro de Brasília |
| `getTile(15, 12025, 17840)` (o centro de Brasília) | Bytes em gzip. Descompactado, decodifica como MVT, com as camadas `roads` (cada via com `kind`, ruas com `name`) e `places` |
| O mesmo tile sem descompactar | O decodificador de MVT usado no teste não acusou erro: devolveu zero camadas |
| `getTile` de um tile fora do pacote | `null`, sem exceção |
| 100 tiles do zoom 15 em sequência, lidos e descompactados | 153 a 161 ms (3,8 MB descompactados) |
| MapLibre, fonte `pmtiles://file://<arquivo>` | O estilo carrega, e o mapa tem feições da camada `roads` em tela sobre Brasília, no zoom 14 (`queryRenderedFeatures`): 76 numa execução e 304 em outra, conforme quantos tiles já tinham chegado na hora da contagem. Com o endereço de um arquivo que não existe, zero |
| Crédito | O MapLibre mostra "© OSM", tirado do `attribution` dos metadados do pacote |

O que **não** foi conferido nessa data: os pixels desenhados (no emulador sem tela, a foto fora de tela do
MapLibre sai transparente com qualquer estilo, então a conferência foi pelas feições, não pela imagem); um aparelho
de verdade, com processador ARM; e as formas `pmtiles://asset://` e `pmtiles://https://`. Os pixels foram
conferidos em 2026-10-05, num navegador do emulador, contra o build de origem: idênticos (seção "Pixels conferidos"
de [`PENDENCIAS.md`](PENDENCIAS.md)).

### Geração completa (2026-10-01)

Uma geração das 27 UFs pelo gerador, do build `20261001.pmtiles`, numa conexão doméstica, sem publicar. A tabela
por estado está em [`PENDENCIAS.md`](PENDENCIAS.md), seção "Geração completa em casa".

| Item | Valor |
|---|---|
| Arquivos e tamanho | 56 arquivos, 5.935.601.816 bytes: completos 4.617.243.141, leves 1.267.919.927, base 44.282.829, recursos 6.155.919 |
| Maior e menor pacote completo | Minas Gerais, 593.547.730 bytes; Amapá, 23.675.580 bytes |
| Tiles | 8.582.282 nos completos e 551.514 nos leves: os mesmos números da simulação, estado por estado |
| Simulação contra o arquivo real, nos 54 pacotes | Diferença de até 1,9 MB (Amazonas, 214,9 MB contra 213 MB) e de até 2,3% (num arquivo de 12 MB). A simulação arredonda para o MB |
| Baixado do build | 4,88 GB em 5.372 pedidos, com 4 em paralelo |
| Tempo | 26,1 minutos para 25 estados, os 27 leves e as travas; o DF, Goiás e a base foram reaproveitados de um recorte anterior do mesmo build. Soma do tempo de todos os recortes: 1.500 s |
| Pico de disco | 6,3 GB na pasta de dados |
| Travas | As nove passaram, com os 51 pares de divisa nos zooms 15 e 12 |
| Leve contra completo | Sobre as 27 capitais, o tile dos zooms 13, 9 e 4 é idêntico byte a byte nos dois arquivos; o leve não tem tile no zoom 15 |
| Base contra estado | Sobre as 27 capitais, o tile dos zooms 9 e 6 é idêntico byte a byte na base e no pacote do estado |
| `pmtiles tile` de um tile que o arquivo não tem | Código de saída 0 e nenhum byte na saída. Quem lê tem de tratar a saída vazia como tile ausente |
| Data dos dados do OpenStreetMap, nos metadados | 2026-10-01T04:00:00Z |

## Não conferido

| Afirmação | Onde aparece | Como conferir |
|---|---|---|
| O disparo agendado do workflow `gerar` (o job `interval` parando antes dos 29 dias, e gerando depois) | GERACAO, PENDENCIAS | Olhar os runs agendados depois de 2026-10-02 |
| O OpenMapTiles vai só até o zoom 14 | DECISOES (D5) | Documentação do OpenMapTiles |
| A Protomaps publica estilos prontos em mais de uma variação de cores | CONSUMO | Repositório `protomaps/basemaps`, pasta de estilos |
| Opções `--osm_path` e `--output` do Planetiler | GERACAO | Documentação do Planetiler, na versão do perfil escolhida |
| Fontes auxiliares que o perfil baixa (quais e quanto pesam) | GERACAO | Não será conferido: é da etapa B, que não está planejada |
| A etapa B cabe na máquina gratuita do GitHub Actions | GERACAO | Não será conferido: é da etapa B, que não está planejada |
| O MapLibre desenha um pacote real num aparelho de verdade (no emulador, a leitura por `pmtiles://file://` já foi conferida) | CONSUMO | Teste em um aparelho ARM |
| O GitHub não serve bem leitura por faixas direto do navegador | CONSUMO | Teste com um arquivo de release |

## Crédito pedido pelas fontes (conferido em 2026-10-02)

Lido no `README.md` e no `LICENSE_DATA.md` do repositório `protomaps/basemaps`, na página de downloads da
Protomaps, na página de acesso aos dados do ESA WorldCover e na página de crédito da Overture Maps.

| Fato | Valor |
|---|---|
| Licença dos tiles | "Tilesets are ODbL, attribute OSM": são um Produced Work do OpenStreetMap |
| O que é obrigatório | "Web maps and native apps that use this Produced Work must visibly attribute © OpenStreetMap - for example, in the corner of the map display" |
| Crédito à Protomaps | Pedido, não exigido: "We kindly request that you attribute the Protomaps project [...] but you are not required to do so" |
| Nome | Quem distribui tiles ou estilos modificados "must name your product or service something different from Protomaps". Redistribuição gratuita e sem modificação pode usar o nome |
| Natural Earth (zooms baixos) | Domínio público; "Crediting the authors is unnecessary" |
| Polígonos de terra e água (osmdata.openstreetmap.de) | ODbL, como o OpenStreetMap; o mesmo crédito cobre |
| Camada `landcover` | Derivada do ESA WorldCover, sob CC BY 4.0. Frase pedida: "© ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium" |
| Ícones dos estilos | Derivados do conjunto `tangrams/icons`, MIT: "Copyright (c) 2017 Mapzen, Linux Foundation" |
| O que mudou aqui | O crédito do catálogo (`config.ATTRIBUTION`) passou a citar o ESA WorldCover; antes só citava o OpenStreetMap |

A Protomaps avisa que essas regras "are subject to change with the addition of other open datasets": vale reler
quando a versão maior do esquema subir.

## Primeira geração no GitHub Actions (medido em 2026-10-02)

| Fato | Valor |
|---|---|
| Máquina | `ubuntu-24.04`, 2 processadores, 7,8 GB de memória, 14 GB livres em disco (72 GB no total, 82% usados) |
| Workflow `testes` | 352 testes, 1 pulado, em 26 s |
| Geração de dois estados, sem publicar | 39 s o job inteiro; 0,29 GB baixados; passo "Publicar" pulado; nenhuma release criada |
| Geração completa | 8,8 minutos para gerar e 4,7 para publicar; 4,88 GB baixados do build; pico de 5,95 GB em disco; pico de 1,1 GB de memória em uso (amostras a cada 30 s) |
| Build recortado | `20261002.pmtiles` |
| Release | 56 arquivos, 5,94 GB, publicada (não é rascunho); `catalogo.json` e a tabela do README commitados pelo robô |
| Conferência por fora | sha256 de dois pacotes baixados da release (um completo e um leve) igual ao do catálogo |
| Repositório privado | O `catalogo.json` por endereço de arquivo bruto responde 404 para quem não está autenticado: enquanto o repositório for privado, ninguém de fora lê o catálogo nem baixa os pacotes |
