# Pendências

Situação em 2026-10-01: o projeto só tem documentação, e o dono decidiu ficar na etapa A (o recorte do build da
Protomaps; ver [`DECISOES.md`](../docs/DECISOES.md), D6). O que falta medir, o que falta decidir e o que pode dar errado.

## Medições antes de escrever o gerador

Nenhuma delas publica nada. M1 a M4 só precisam do `pmtiles` instalado e da malha do IBGE; M5 precisa de um
aparelho ou emulador.

| ID | Medição | Como | O que ela decide |
|---|---|---|---|
| M1 | **Tamanho de cada pacote de estado** no zoom 15 e no 13. **Feita**: resultado abaixo | `pmtiles extract <build> saida.pmtiles --region=<UF>.geojson --maxzoom=15 --dry-run`, para as 27 UFs | Se algum estado passa de 2 GiB (dividir em partes muda o catálogo); o total por geração; se vale publicar também um pacote "leve" |
| M2 | **Tamanho da base** nos zooms 7, 8, 9 e 10, e o peso dos zooms 0 a 9 dentro de um pacote de estado. **Feita**: resultado abaixo | Mesmo comando, com o polígono do Brasil e `--maxzoom` variando | O zoom máximo da base; se o pacote de estado começa no zoom 0 ou acima da base |
| M3 | **Tempo e tráfego do recorte de verdade**. **Feita**: resultado abaixo | Recortar de fato dois estados vizinhos (um pequeno e um maior) e a base, em casa | Quanto demora e quanto baixa a geração inteira. A medida na máquina gratuita do GitHub Actions sai da primeira geração feita lá |
| M4 | **Tile de divisa**. **Feita**: resultado abaixo | Comparar tiles de divisa nos dois recortes da M3 e no build | Confirma que o tile vem inteiro e idêntico (a decisão D10 e a trava "Divisa" dependem disso) |
| M5 | **Leitura no aparelho**. **Feita no emulador**: resultado abaixo | Abrir um pacote real no MapLibre por `pmtiles://file://` e pelo leitor Java, com um estilo da versão 4 | Confirma o guia de consumo; mostra a compressão real dos tiles |

### M1: tamanho dos pacotes de estado (feita em 2026-10-01)

Simulação com `pmtiles extract --dry-run` (versão 1.31.2) sobre o build `20261001.pmtiles` (esquema 4.15.2), com
o polígono de cada UF e a margem de 0,05°. A simulação lê só os diretórios do build e **não baixa nenhum tile**;
o tamanho é o que a ferramenta calcula para o arquivo de saída, arredondado para o MB. O recorte de verdade, que
confirma esses números, é a medição M3. Para repetir: `python scripts/measure.py`, na pasta do gerador.

| UF | Estado | Tiles até o zoom 15 | Tamanho até o zoom 15 | Tiles até o zoom 13 | Tamanho até o zoom 13 |
|---|---|---:|---:|---:|---:|
| AC | Acre | 165.980 | 62 MB | 10.841 | 20 MB |
| AL | Alagoas | 31.765 | 36 MB | 2.187 | 10 MB |
| AM | Amazonas | 1.455.690 | 213 MB | 92.351 | 64 MB |
| AP | Amapá | 141.635 | 24 MB | 9.280 | 8 MB |
| BA | Bahia | 562.894 | 295 MB | 36.071 | 77 MB |
| CE | Ceará | 146.423 | 159 MB | 9.524 | 32 MB |
| DF | Distrito Federal | 7.868 | 48 MB | 576 | 7 MB |
| ES | Espírito Santo | 54.797 | 364 MB | 3.670 | 125 MB |
| GO | Goiás | 355.106 | 182 MB | 22.896 | 50 MB |
| MA | Maranhão | 324.222 | 112 MB | 20.930 | 28 MB |
| MG | Minas Gerais | 616.660 | 592 MB | 39.438 | 183 MB |
| MS | Mato Grosso do Sul | 385.183 | 111 MB | 24.691 | 29 MB |
| MT | Mato Grosso | 886.897 | 229 MB | 56.413 | 59 MB |
| PA | Pará | 1.165.728 | 205 MB | 73.981 | 56 MB |
| PB | Paraíba | 62.521 | 76 MB | 4.231 | 21 MB |
| PE | Pernambuco | 105.303 | 105 MB | 7.037 | 26 MB |
| PI | Piauí | 248.897 | 115 MB | 16.134 | 25 MB |
| PR | Paraná | 231.867 | 327 MB | 14.914 | 99 MB |
| RJ | Rio de Janeiro | 57.532 | 116 MB | 3.875 | 32 MB |
| RN | Rio Grande do Norte | 56.411 | 44 MB | 3.795 | 12 MB |
| RO | Rondônia | 239.663 | 53 MB | 15.524 | 15 MB |
| RR | Roraima | 220.303 | 39 MB | 14.360 | 12 MB |
| RS | Rio Grande do Sul | 347.690 | 280 MB | 22.475 | 68 MB |
| SC | Santa Catarina | 123.775 | 228 MB | 8.141 | 58 MB |
| SE | Sergipe | 25.376 | 30 MB | 1.759 | 8 MB |
| SP | São Paulo | 283.071 | 495 MB | 18.346 | 126 MB |
| TO | Tocantins | 279.025 | 67 MB | 18.074 | 17 MB |
| | **Total** | **8.582.282** | **4.607 MB** | **551.514** | **1.267 MB** |

"Tiles" são os endereçados dentro da área, do zoom 0 ao máximo. Os totais contam duas vezes o tile de divisa,
que entra nos dois pacotes vizinhos.

O que os números dizem:

- **Nenhum estado chega perto de 2 GiB.** O maior é Minas Gerais, com 592 MB; depois São Paulo (495 MB) e
  Espírito Santo (364 MB). O menor é o Amapá, com 24 MB.
- **Uma geração inteira dos 27 estados soma 4,6 GB**; três gerações guardadas, cerca de 14 GB. A simulação
  estima 4,8 GB baixados da Protomaps por geração, em cerca de 5.300 pedidos.
- **O pacote até o zoom 13 pesa, no total, 27% do completo** (de 15% no DF a 34% no ES), e não os 6% que a
  contagem de tiles sugere: os tiles dos zooms baixos são poucos, mas muito mais pesados. Os 27 somam 1,27 GB.
- **O tamanho não acompanha a área.** O Amazonas tem 1,46 milhão de tiles e 213 MB; o Espírito Santo tem 55 mil
  tiles e 364 MB. O que pesa é o quanto o estado está mapeado. No ES, uma amostra de quatro tiles mostrou a
  camada `landuse` com 60 a 69 KB num tile rural do zoom 12, contra 4 a 5 KB em tiles vizinhos de MG e do RJ:
  o uso do solo do estado está desenhado em muito detalhe no OpenStreetMap.
- A estimativa anterior a esta medição (conta de 4 a 8 GB para o país, "perto de 1 GB" para SP e MG) acertou o
  total e errou os maiores para mais.

A simulação das 54 combinações levou 5 minutos e 8.359 pedidos ao build.

### M2: tamanho da base e peso dos zooms baixos (feita em 2026-10-01)

Mesma simulação, mesmo build. A base é o polígono do Brasil (a união das UFs) com a margem de 0,05°.

| Base até o zoom | Tiles | Tamanho |
|---:|---:|---:|
| 5 | 32 | 1,2 MB |
| 6 | 74 | 2,2 MB |
| 7 | 200 | 6,1 MB |
| 8 | 647 | 15 MB |
| 9 | 2.295 | 44 MB |
| 10 | 8.604 | 106 MB |
| 11 | 33.230 | 225 MB |

Cada zoom a mais multiplica o tamanho por cerca de 2 a 3. Para comparar: a base até o zoom 9 pesa quase o mesmo
que o pacote completo do Distrito Federal (48 MB), e até o zoom 10 pesa mais que 11 dos 27 estados.

Quanto pesam os zooms baixos **dentro** de um pacote de estado (o que ele repete da base):

| UF | Zooms 0 a 5 | Zooms 0 a 7 | Zooms 0 a 9 | Pacote completo | Zooms 0 a 9 no pacote |
|---|---:|---:|---:|---:|---:|
| AP | 0,561 MB | 0,757 MB | 1,3 MB | 24 MB | 5,4% |
| DF | 0,334 MB | 0,445 MB | 0,963 MB | 48 MB | 2,0% |
| GO | 0,334 MB | 0,734 MB | 3,2 MB | 182 MB | 1,8% |
| ES | 0,210 MB | 0,418 MB | 3,3 MB | 364 MB | 0,9% |
| SP | 0,464 MB | 1,2 MB | 6,3 MB | 495 MB | 1,3% |
| MG | 0,516 MB | 1,5 MB | 8,7 MB | 592 MB | 1,5% |

O que os números dizem:

- **Começar o pacote de estado no zoom 0 custa de 1% a 2% do pacote** nos estados médios e grandes, e 5% no
  menor de todos (Amapá). Em troca, o pacote funciona sozinho e o recorte é o barato. Tirar os zooms baixos
  economizaria 9 MB no maior estado (MG) e menos nos outros cinco medidos.
- **A base até o zoom 9 tem 44 MB**: é o que se baixa uma vez para ter o país inteiro em visão geral.

### M3: recorte de verdade (feita em 2026-10-01)

Distrito Federal e Goiás até o zoom 15 e a base até o zoom 9, recortados de fato do build `20261001.pmtiles`, com
4 pedidos em paralelo, numa conexão doméstica. Os detalhes estão em [`FONTES.md`](FONTES.md).

| Recorte | Tempo | Baixado | Arquivo final | Simulado na M1 e na M2 |
|---|---:|---:|---:|---:|
| Distrito Federal | 15 s | 50 MB | 48,0 MB | 48 MB |
| Goiás | 71 s | 191 MB | 182,4 MB | 182 MB |
| Base | 12 s | 46 MB | 44,3 MB | 44 MB |

- **A simulação acerta.** Nos três, o arquivo real ficou dentro do arredondamento do simulado. Os números da M1
  valem como tamanho dos pacotes.
- **Os arquivos saem prontos:** passam no `pmtiles verify`, são "clustered", com tiles MVT em gzip, do zoom 0 ao
  15 (9 na base).
- **O recorte é reprodutível:** o DF recortado duas vezes do mesmo build deu o mesmo arquivo, byte a byte.
- **Tempo da geração inteira, por conta:** Goiás baixou a cerca de 3 MB/s. Nesse ritmo, os 4,8 GB dos 27 estados
  levam perto de 30 minutos nesta conexão. Era estimativa; a geração completa mediu 26 minutos, mais 2,4 dos
  três recortes reaproveitados (seção "Geração completa em casa").

### M4: tile de divisa (feita em 2026-10-01)

Com os recortes do DF e de Goiás da M3: dos 7.868 tiles do pacote do DF, 4.177 também estão no de Goiás, e
**todos os 4.177 são idênticos byte a byte** nos dois. Uma amostra de 7 deles, do zoom 0 ao 15, é idêntica também
ao tile do build remoto.

- **O recorte não corta o tile na borda da região**: copia o tile inteiro, como está no build.
- **O tile de divisa é o mesmo nos dois pacotes vizinhos** da mesma geração. A decisão D10 e a trava "Divisa"
  ficam de pé.
- Foi conferido um par de vizinhos (DF e GO), de um build. A trava "Divisa" confere outros pares a cada geração.

### M5: leitura em um aparelho (feita em 2026-10-01)

O pacote do DF copiado para um emulador Android, lido de duas formas. Os detalhes estão em
[`FONTES.md`](FONTES.md).

- **Leitor Java (`pmtiles-reader` 0.3.6):** abre o arquivo local, o cabeçalho confere, um tile do zoom 15 do
  centro de Brasília descompacta e decodifica com as camadas `roads` e `places`. Cem tiles em sequência levam
  cerca de 0,16 s. Tile fora do pacote volta `null`.
- **MapLibre 13.4.1:** com a fonte `pmtiles://file://`, o mapa leu as vias direto do arquivo (76 numa execução,
  304 em outra; zero com o endereço de um arquivo que não existe).
- **Só o emulador provou.** Falta um aparelho de verdade (ARM). Os pixels, que ficaram de fora em 2026-10-01 (no
  emulador sem tela a foto do mapa saía transparente), foram conferidos em 2026-10-05: ver "Pixels conferidos".

### Pixels conferidos (2026-10-05)

O pacote de Goiás publicado (`carcara-GO.pmtiles`, geração `2026-10-02-0c6171ea`, o SHA-256 do catálogo) contra o
build de onde ele saiu (`https://build.protomaps.com/20261002.pmtiles`), no centro de Goiânia (-16,6869,
-49,2648), nos zooms 13 e 15.

- **Bytes:** os 9 tiles em volta do centro, em cada zoom (18 no total), lidos com `pmtiles tile` dos dois lados,
  são idênticos byte a byte.
- **Pixels:** no Chrome de um emulador Android 16 com tela, uma página com o MapLibre GL JS 5.24.0, o `pmtiles`
  4.5.0 e o estilo `light` do `@protomaps/basemaps` 5.7.2 (com as fontes e os ícones do `carcara-recursos.tar.gz`)
  desenhou o mesmo lugar do pacote e do build, os dois entregues por um mesmo programa local (o build não manda cabeçalho de
  CORS, então foi repassado por ele). A página só avisava "pronto" com todos os tiles carregados. Captura de tela
  inteira: **zero pixels diferentes** em 1.814.400 da área do mapa, nos dois zooms; as imagens têm 7.320 (zoom 13) e
  10.660 (zoom 15) cores, com ruas, nomes, parques e ícones. O mesmo comparador acusa a troca do zoom 13 pelo 15
  na tela inteira, então ele vê diferença quando há.
- **Por que basta:** com os tiles idênticos, qualquer leitor desenha os dois iguais; a captura mostra que o pacote
  desenha de verdade, com fontes e ícones do pacote de recursos, e não sai em branco.
- **O que segue sem conferência:** um aparelho de verdade (ARM) e o desenho nativo do MapLibre no Android (o desta
  conferência é o do navegador). As capturas ficam em `gerador/data/medicoes/pixels_20261005/` (fora do git).

### Geração completa em casa (feita em 2026-10-01)

Uma geração inteira pelo `generate.py`, do build `20261001.pmtiles`, numa conexão doméstica, com 4 pedidos em
paralelo. **Nada foi publicado.** Passou nas nove travas de primeira, e depois nas travas da publicação
(`scripts/publish.py` sem opções, que só confere).

| Item | Valor |
|---|---|
| Arquivos | 56: 27 completos, 27 leves, a base e os recursos |
| Completos (zoom 0 a 15) | 4,62 GB |
| Leves (zoom 0 a 13) | 1,27 GB |
| Base e recursos | 44,3 MB e 6,2 MB |
| Total da geração | 5,94 GB |
| Baixado do build | 4,88 GB, em 5.372 pedidos |
| Tempo | 26 minutos para 25 estados e os leves; o DF, Goiás e a base, recortados horas antes do mesmo build, foram reaproveitados (tinham levado 2,4 minutos) |
| Tempo só dos recortes | 25 minutos (1.500 s) somando os 27 estados e a base: 3,3 MB/s em média |
| Tempo das travas | 1,6 minuto |
| Pico de disco na pasta de dados | 6,3 GB |

| UF | Estado | Tiles | Completo | Leve | Tempo do recorte |
|---|---|---:|---:|---:|---:|
| AC | Acre | 165.980 | 62,2 MB | 20,0 MB | 40 s |
| AL | Alagoas | 31.765 | 35,5 MB | 10,1 MB | 20 s |
| AM | Amazonas | 1.455.690 | 214,9 MB | 64,4 MB | 95 s |
| AP | Amapá | 141.635 | 23,7 MB | 7,7 MB | 34 s |
| BA | Bahia | 562.894 | 295,8 MB | 77,1 MB | 54 s |
| CE | Ceará | 146.423 | 159,1 MB | 31,6 MB | 62 s |
| DF | Distrito Federal | 7.868 | 48,0 MB | 7,1 MB | 18 s |
| ES | Espírito Santo | 54.797 | 364,4 MB | 124,9 MB | 48 s |
| GO | Goiás | 355.106 | 182,4 MB | 50,2 MB | 70 s |
| MA | Maranhão | 324.222 | 112,7 MB | 28,1 MB | 47 s |
| MG | Minas Gerais | 616.660 | 593,5 MB | 182,9 MB | 100 s |
| MS | Mato Grosso do Sul | 385.183 | 111,2 MB | 29,5 MB | 65 s |
| MT | Mato Grosso | 886.897 | 230,7 MB | 59,0 MB | 72 s |
| PA | Pará | 1.165.728 | 206,3 MB | 56,1 MB | 74 s |
| PB | Paraíba | 62.521 | 75,6 MB | 21,1 MB | 30 s |
| PE | Pernambuco | 105.303 | 104,8 MB | 26,2 MB | 45 s |
| PI | Piauí | 248.897 | 115,3 MB | 25,2 MB | 42 s |
| PR | Paraná | 231.867 | 327,5 MB | 99,4 MB | 101 s |
| RJ | Rio de Janeiro | 57.532 | 115,7 MB | 31,8 MB | 25 s |
| RN | Rio Grande do Norte | 56.411 | 43,7 MB | 12,3 MB | 27 s |
| RO | Rondônia | 239.663 | 53,6 MB | 15,3 MB | 38 s |
| RR | Roraima | 220.303 | 38,9 MB | 11,7 MB | 51 s |
| RS | Rio Grande do Sul | 347.690 | 280,3 MB | 67,5 MB | 49 s |
| SC | Santa Catarina | 123.775 | 228,4 MB | 57,8 MB | 47 s |
| SE | Sergipe | 25.376 | 29,5 MB | 7,9 MB | 20 s |
| SP | São Paulo | 283.071 | 495,5 MB | 126,2 MB | 79 s |
| TO | Tocantins | 279.025 | 67,9 MB | 17,0 MB | 92 s |

- **A simulação da M1 acertou.** A contagem de tiles é a mesma, estado por estado, no completo e no leve. No
  tamanho, a maior diferença é de 1,9 MB (Amazonas: 214,9 MB contra 213 MB simulados); em proporção, 2,3%
  num arquivo de 12 MB, onde o que pesa é o arredondamento da simulação para o MB.
- **O maior arquivo tem 593,5 MB**, menos de um terço do limite de 2 GiB.
- **O tempo não acompanha o tamanho.** O Tocantins (68 MB) levou 92 s e São Paulo (496 MB) levou 79 s: o que
  demora é o número de pedidos, que cresce com a área, não com os bytes.
- **Conferido por fora das travas**, sobre a capital de cada UF: o tile dos zooms 13, 9 e 4 é idêntico byte a
  byte no completo e no leve (81 tiles); o leve não tem tile no zoom 15; o tile dos zooms 9 e 6 é idêntico na
  base e no pacote do estado (54 tiles).
- **Medido em 2026-10-02 na máquina do GitHub Actions** (2 processadores, 7,8 GB de memória, 14 GB livres):
  8,8 minutos para gerar e 4,7 para publicar; 4,88 GB baixados do build; pico de 5,95 GB em disco; pico de 1,1 GB de memória em uso (amostras a cada 30 s). Sobram cerca de 8 GB de disco no pico: o mínimo que o gerador exige para começar (12 GB
  livres) passa por 2 GB.

## Decisões em aberto

| ID | Decisão | Padrão proposto | Alternativa | Depende de |
|---|---|---|---|---|
| X1 | Nome definitivo | **`carcara`, decidido pelo dono em 2026-10-02** | Sabiá, João-de-barro, Seriema, Bem-te-vi, Arara | Fechada |
| X2 | Zoom máximo da base | **9, aplicado em 2026-10-01**: 44 MB | 7, 8 ou 10 | M2, feita: 6,1 MB no zoom 7, 15 MB no 8, 44 MB no 9, 106 MB no 10. O dono ainda pode mudar |
| X3 | Pacote de estado começa no zoom 0 (funciona sozinho) | **Sim, aplicado em 2026-10-01** | Só os zooms acima da base (base obrigatória) | M2, feita: os zooms 0 a 9 são de 1% a 2% do pacote (5% no Amapá) |
| X4 | Pacote "leve" por estado (até o zoom 13), além do completo | **Sim, aplicado em 2026-10-01** pela regra "publicar o leve se algum estado completo passar de 500 MB": Minas Gerais tem 592 MB. Os 27 leves somam 1,27 GB | Não publicar o leve | M1, feita. **Confirmado pelo dono em 2026-10-02**: o leve é o pacote que basta para o uso comum, e os completos continuam sendo gerados para quem quer o detalhe dos zooms 14 e 15 |
| X5 | Estado acima de 2 GiB | **Não se aplica hoje**: o maior estado tem 592 MB. Se um dia algum passar de 1,8 GiB, a geração para e o dono decide | Dividir em partes; hospedar esse estado em outro lugar | M1, feita |
| X6 | Quantas gerações manter nas releases | **3, aplicado em 2026-10-01**: cerca de 18 GB (5,9 GB por geração, com os leves) | 2 | M1, feita |
| X9 | Fontes do pacote de recursos | **As três (Regular, Medium, Italic), todas as faixas, aplicado em 2026-10-01**: o pacote inteiro tem 6,2 MB | Só Regular, só as faixas usadas em português | Medido na montagem: as fontes são 11,1 MB soltas e os ícones 0,15 MB. A fonte para a escrita devanágari, que a origem também tem, fica de fora |
| X10 | Onde ficam os documentos quando o gerador existir | **Aplicado em 2026-10-05**: `FONTES.md` e `PENDENCIAS.md` em `gerador/`; os outros em `docs/` | Tudo em `gerador/` | Fechada |
| X11 | Visibilidade | **Público desde 2026-10-05**, recriado com um commit só. Nasceu privado; a revisão de abertura foi feita em 2026-10-05: arquivos, histórico inteiro, mensagens, logs das execuções, artefatos, notas e anexos da release e metadados dos pacotes sem dado pessoal, caminho de máquina ou segredo; licenças conferidas | | Dono (a abertura) |

X7, X8 e X12 tratavam da etapa B e estão na seção "Etapa B (sem data)", no fim.

## Riscos

| Risco | Efeito | O que reduz |
|---|---|---|
| A Protomaps muda o endereço ou o formato do índice de builds, ou deixa de publicar o build | A geração para | Ler sempre o índice; a geração falha com mensagem clara e os pacotes publicados continuam valendo. Só a etapa B eliminaria a dependência, e ela não tem data: é o risco que a decisão D6 aceita |
| A Protomaps sobe a versão maior do esquema (4 para 5) | Estilos escritos para a 4 podem deixar de desenhar | O gerador recusa versão maior inesperada; o catálogo publica a versão; a troca vira decisão deliberada, com aviso |
| Um estado passa de 2 GiB | O arquivo não entra na release | Hoje o maior tem 592 MB (medição M1): falta um fator de três. A trava de tamanho antes de publicar continua; decisão X5 |
| O recorte corta o conteúdo do tile na borda da região | Divisas com falhas no mapa | Afastado pela medição M4 com o `pmtiles` 1.31.2: o tile vem inteiro. A trava "Divisa" pega se outra versão da ferramenta mudar isso |
| Pacotes grandes demais para o aparelho | Pouca gente baixa o estado inteiro | Medido na M1: 21 dos 27 estados ficam abaixo de 250 MB; os maiores são MG (592 MB) e SP (495 MB). Decisão X4 |
| A geração baixa vários GB da Protomaps a cada 29 dias | Uso pesado de um serviço gratuito | É o uso que a própria Protomaps recomenda (copiar para armazenamento próprio); manter os pedidos em paralelo no padrão; gerações completas só no ciclo de 29 dias, nunca em teste repetido |
| O agendamento do GitHub atrasa ou pula disparos | Geração atrasada | A regra "29 dias ou mais" tolera, e o cron fica fora do minuto zero; ver "Lições herdadas" em [`GERACAO.md`](../docs/GERACAO.md) |
| A geração pelo agendamento ainda não foi vista | Um erro que só exista nesse caminho aparece no primeiro disparo agendado que gerar | Em 2026-10-02 o workflow rodou duas vezes à mão: dois estados sem publicar, e a geração completa publicando (release, catálogo e README commitados pelo robô). O disparo agendado roda: em 2026-10-03 e 2026-10-04 ele parou no job `interval` como deve ("geração publicada em 2026-10-02 (2 dias): ainda não, gera ao completar 29 dias"). Desde 2026-10-05 há uma geração extra marcada para 2026-10-06 (`GENERATE_FROM`): é ela o primeiro disparo agendado que gera |
| A máquina do GitHub Actions fica sem disco para a geração inteira | A geração para antes de baixar qualquer coisa (exige 12 GB livres; em 2026-10-02 havia 14) | Decisão do dono em 2026-10-02: se o disco virar problema, **dividir a geração em tarefas** (por exemplo, um job por grupo de estados, cada um enviando os seus arquivos, e um job final que valida, monta o catálogo e publica). Não feito: hoje cabe numa execução só |
| Crédito ou licença da etapa A mal redigidos | Problema ao abrir o repositório | Conferido em 2026-10-02 ([`FONTES.md`](FONTES.md), "Crédito pedido pelas fontes"): faltava citar o ESA WorldCover, e o catálogo passou a citar. Visto em 2026-10-05: o crédito **dentro** de cada `.pmtiles` (o campo `attribution` dos metadados, que o MapLibre mostra sozinho) é o da origem, só "© OpenStreetMap"; o do ESA WorldCover está no catálogo, nas notas da release e no README. **Decidido pelo dono no mesmo dia:** a geração passa a escrever o crédito inteiro, com o do ESA, dentro de cada arquivo (`config.EMBEDDED_ATTRIBUTION`, por `pmtiles edit` antes do sha256), a partir da próxima geração |
| Tiles mais ricos pesam mais para desenhar em aparelhos fracos | Mapa mais lento no zoom 15 real do que no zoom 13 ampliado | Medir em quem consome; a saída é otimizar o desenho, não empobrecer o pacote |

## O que não é objetivo

- **Fabricar o mapa.** O projeto recorta o build da Protomaps (etapa A); a geração própria não está planejada.
- **Roteamento.** É outro projeto.
- **Relevo e imagens de satélite.** Só o mapa vetorial.
- **Outros países.** O recorte é pelo polígono do Brasil e das UFs.
- **Servir tiles online.** O projeto publica arquivos; quem quiser servir hospeda uma cópia.
- **Dados acima do zoom 15.** O esquema não tem.

## Ordem sugerida do trabalho

1. Medições M1 a M5.
2. Decisões X1 a X6, com os números na mão.
3. Repositório privado, gerador da etapa A com testes, primeira geração à mão.
4. Workflow agendado e limpeza de releases, no molde dos irmãos.
5. Revisão do dono e abertura.

## Etapa B (sem data)

A geração própria com o Planetiler não está planejada (decisão D6, 2026-10-01). O que dependia dela fica aqui
como registro, fora da ordem de trabalho.

| ID | O que era | Situação |
|---|---|---|
| M6 | Medição: rodar o perfil da Protomaps sobre o extrato de um estado pequeno e depois do Brasil, medindo memória, disco, tempo e as fontes auxiliares baixadas | Não será feita |
| X7 | Quando passar para a etapa B | Sem data. Reabrir só se o conteúdo ou a disponibilidade do build da Protomaps virar problema |
| X8 | Acréscimos ao esquema (superfície da via; postos em zoom mais baixo) | Só existiriam com a etapa B |
| X12 | Gerar no mesmo dia dos tiles de roteamento, para os dois terem o mesmo extrato | Só faria sentido com a etapa B; na etapa A a data dos dados é a do build da Protomaps |
