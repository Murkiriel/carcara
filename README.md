# Carcará — mapa base do Brasil por estado, para uso offline

> **Projeto novo.** A primeira release saiu em 2026-10-02, com o repositório ainda privado. O que já foi
> conferido e o que ainda é suposição está separado em [`gerador/FONTES.md`](gerador/FONTES.md) e
> [`gerador/PENDENCIAS.md`](gerador/PENDENCIAS.md).

## O que vai ser

O Carcará vai publicar o **mapa base vetorial do Brasil em arquivos prontos para uso offline**: um pacote base
(o país inteiro em zoom baixo), um pacote por estado (até o zoom 15, e uma versão leve até o zoom 13) e um pacote
de recursos (ícones e fontes).
Os arquivos são [PMTiles](https://docs.protomaps.com/pmtiles/), no esquema de camadas do
[basemap da Protomaps](https://docs.protomaps.com/basemaps/layers), recortados de novo a cada 29 dias do build
diário que a Protomaps gera do OpenStreetMap, e publicados como arquivos de release, com um `catalogo.json` na
raiz.

É o terceiro projeto do mesmo molde: o **Pardal** publica radares e limites de velocidade, o **Andorinha**
publica os tiles de roteamento do Valhalla, e o Carcará publica o mapa que se desenha por baixo dos dois.

## Por que existe

Quem quer o mapa do Brasil offline tem hoje duas saídas, e as duas são ruins:

- **Baixar tile a tile do build público da Protomaps.** O arquivo mundial tem 138 GB e é lido por faixas de
  bytes, um pedido por tile. O retângulo de Goiás tem 602.806 tiles do zoom 8 ao 15; na prática, um estado inteiro
  só é viável até o zoom 13 (37.996 tiles), e o detalhe de rua fica restrito ao corredor de uma rota. A própria
  Protomaps pede para não usar esse endereço como infraestrutura: "copie o tileset para o seu armazenamento".
- **Gerar por conta própria.** Exige montar a geração, ter máquina e repetir a cada atualização.

Com um arquivo por estado, baixar Goiás vira **um download**, com o detalhe completo no estado inteiro, que pode
ser conferido por sha256, retomado, atualizado e apagado como um arquivo só.

## Baixar

<!-- downloads:start -->
Geração **2026-10-02-0c6171ea**: build da Protomaps de 2026-10-02, com dados do OpenStreetMap de 2026-10-02, no esquema 4.15.2. Confira o sha256 de cada arquivo pelo [`catalogo.json`](catalogo.json).

Ícones e fontes: [carcara-recursos.tar.gz](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-recursos.tar.gz) (6,2 MB).

| Pacote | Completo (até o zoom 15) | Tamanho | Leve (até o zoom 13) | Tamanho |
|---|---|---:|---|---:|
| **Base** (o país até o zoom 9) | [carcara-base.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-base.pmtiles) | 44,3 MB |  |  |
| Acre (AC) | [carcara-AC.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AC.pmtiles) | 62,2 MB | [carcara-AC-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AC-leve.pmtiles) | 20,0 MB |
| Alagoas (AL) | [carcara-AL.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AL.pmtiles) | 35,5 MB | [carcara-AL-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AL-leve.pmtiles) | 10,1 MB |
| Amapá (AP) | [carcara-AP.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AP.pmtiles) | 23,7 MB | [carcara-AP-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AP-leve.pmtiles) | 7,7 MB |
| Amazonas (AM) | [carcara-AM.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AM.pmtiles) | 215,0 MB | [carcara-AM-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-AM-leve.pmtiles) | 64,5 MB |
| Bahia (BA) | [carcara-BA.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-BA.pmtiles) | 295,8 MB | [carcara-BA-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-BA-leve.pmtiles) | 77,1 MB |
| Ceará (CE) | [carcara-CE.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-CE.pmtiles) | 159,1 MB | [carcara-CE-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-CE-leve.pmtiles) | 31,6 MB |
| Distrito Federal (DF) | [carcara-DF.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-DF.pmtiles) | 48,0 MB | [carcara-DF-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-DF-leve.pmtiles) | 7,1 MB |
| Espírito Santo (ES) | [carcara-ES.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-ES.pmtiles) | 364,4 MB | [carcara-ES-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-ES-leve.pmtiles) | 124,9 MB |
| Goiás (GO) | [carcara-GO.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-GO.pmtiles) | 182,5 MB | [carcara-GO-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-GO-leve.pmtiles) | 50,3 MB |
| Maranhão (MA) | [carcara-MA.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MA.pmtiles) | 112,7 MB | [carcara-MA-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MA-leve.pmtiles) | 28,1 MB |
| Mato Grosso (MT) | [carcara-MT.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MT.pmtiles) | 230,7 MB | [carcara-MT-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MT-leve.pmtiles) | 59,0 MB |
| Mato Grosso do Sul (MS) | [carcara-MS.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MS.pmtiles) | 111,2 MB | [carcara-MS-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MS-leve.pmtiles) | 29,5 MB |
| Minas Gerais (MG) | [carcara-MG.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MG.pmtiles) | 593,7 MB | [carcara-MG-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-MG-leve.pmtiles) | 182,9 MB |
| Pará (PA) | [carcara-PA.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PA.pmtiles) | 206,3 MB | [carcara-PA-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PA-leve.pmtiles) | 56,1 MB |
| Paraíba (PB) | [carcara-PB.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PB.pmtiles) | 75,6 MB | [carcara-PB-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PB-leve.pmtiles) | 21,1 MB |
| Paraná (PR) | [carcara-PR.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PR.pmtiles) | 327,5 MB | [carcara-PR-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PR-leve.pmtiles) | 99,4 MB |
| Pernambuco (PE) | [carcara-PE.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PE.pmtiles) | 104,9 MB | [carcara-PE-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PE-leve.pmtiles) | 26,2 MB |
| Piauí (PI) | [carcara-PI.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PI.pmtiles) | 115,3 MB | [carcara-PI-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-PI-leve.pmtiles) | 25,2 MB |
| Rio Grande do Norte (RN) | [carcara-RN.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RN.pmtiles) | 43,7 MB | [carcara-RN-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RN-leve.pmtiles) | 12,3 MB |
| Rio Grande do Sul (RS) | [carcara-RS.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RS.pmtiles) | 280,3 MB | [carcara-RS-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RS-leve.pmtiles) | 67,5 MB |
| Rio de Janeiro (RJ) | [carcara-RJ.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RJ.pmtiles) | 115,7 MB | [carcara-RJ-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RJ-leve.pmtiles) | 31,8 MB |
| Rondônia (RO) | [carcara-RO.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RO.pmtiles) | 53,6 MB | [carcara-RO-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RO-leve.pmtiles) | 15,3 MB |
| Roraima (RR) | [carcara-RR.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RR.pmtiles) | 38,9 MB | [carcara-RR-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-RR-leve.pmtiles) | 11,7 MB |
| Santa Catarina (SC) | [carcara-SC.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SC.pmtiles) | 228,4 MB | [carcara-SC-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SC-leve.pmtiles) | 57,8 MB |
| São Paulo (SP) | [carcara-SP.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SP.pmtiles) | 495,6 MB | [carcara-SP-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SP-leve.pmtiles) | 126,2 MB |
| Sergipe (SE) | [carcara-SE.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SE.pmtiles) | 29,5 MB | [carcara-SE-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-SE-leve.pmtiles) | 7,9 MB |
| Tocantins (TO) | [carcara-TO.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-TO.pmtiles) | 67,9 MB | [carcara-TO-leve.pmtiles](https://github.com/Murkiriel/carcara/releases/download/2026-10-02-0c6171ea/carcara-TO-leve.pmtiles) | 17,0 MB |
<!-- downloads:end -->

## O que muda para quem usa

| Hoje (tile a tile) | Com os pacotes |
|---|---|
| Centenas de milhares de pedidos por estado | Um arquivo por estado |
| Estado inteiro só até o zoom 13 | Zoom 15 no estado inteiro |
| Depende de um endereço público sem garantia | Arquivo de release, com sha256 |
| Ícones e fontes vêm de outro servidor, no primeiro uso | Pacote de recursos da mesma geração |
| Centenas de milhares de arquivos pequenos no aparelho | Um arquivo, lido no lugar |

## Documentos

| Documento | O que tem |
|---|---|
| [`docs/DECISOES.md`](docs/DECISOES.md) | O que foi decidido, o que é só proposta, e as alternativas descartadas |
| [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) | Pacotes, zooms, recorte por estado, `catalogo.json`, releases, estrutura do repositório, licenças |
| [`docs/GERACAO.md`](docs/GERACAO.md) | Como os pacotes serão gerados (o recorte do build da Protomaps), validação, agendamento e publicação |
| [`docs/CONSUMO.md`](docs/CONSUMO.md) | Como um aplicativo ou site lê os pacotes |
| [`gerador/FONTES.md`](gerador/FONTES.md) | Fontes externas: o que foi conferido, quando e onde |
| [`gerador/PENDENCIAS.md`](gerador/PENDENCIAS.md) | Medições que faltam, decisões em aberto e riscos |

## Situação

| Item | Situação em 2026-10-02 |
|---|---|
| Nome | `carcara`, definitivo desde 2026-10-02 ([`docs/DECISOES.md`](docs/DECISOES.md)) |
| Repositório no GitHub | Criado em 2026-10-02, privado |
| Gerador | Pronto: recorta o build por estado, passa a geração pelas nove travas de validação, monta o catálogo e publica ([`gerador/`](gerador/README.md)). Rodou inteiro em casa e no GitHub Actions. O agendamento (a cada 29 dias) está escrito e ainda não teve um disparo que gerasse |
| Pacotes | Publicados em 2026-10-02, pelo GitHub Actions: 56 arquivos, 5,9 GB com os leves; 4,6 GB os 27 completos, o maior com 594 MB (tabela acima e [`gerador/PENDENCIAS.md`](gerador/PENDENCIAS.md)) |
| Origem dos tiles | Decidida em 2026-10-01: só o recorte do build da Protomaps (etapa A) |
| Medições | M1 a M5 feitas ([`gerador/PENDENCIAS.md`](gerador/PENDENCIAS.md)) |
| Decisões com os números | Base até o zoom 9, pacote de estado desde o zoom 0, pacote leve até o zoom 13, 3 gerações ([`gerador/PENDENCIAS.md`](gerador/PENDENCIAS.md), X2 a X6) |
| Próximo passo | Abrir o repositório; conferir o primeiro disparo agendado (ele só gera de novo com 29 dias) |

## Convenções

A regra em uma frase: **arquivos e pastas de dados em português; código e formato de dados em inglês; tudo o que
é texto para pessoas em português.**

| O quê | Idioma | Exemplos |
|---|---|---|
| Arquivos e pastas de dados e documentos | português, sem acento nem espaço | `catalogo.json`, `carcara-GO.pmtiles`, `carcara-recursos.tar.gz`, `PENDENCIAS.md`, `gerar.yml` |
| Código: variáveis, funções, classes, módulos, arquivos de código | inglês | `regions.py`, `measure.py`, `latest_build` |
| Opções de linha de comando | inglês | `--areas`, `--zooms`, `--dest` |
| Formato dos dados: chaves e valores do catálogo | inglês | `build_id`, `tileset_version`, `bbox` |
| Identificadores de automação (variáveis e jobs de workflow) | inglês | `CARCARA_PMTILES`, job `tests` |
| Comentários, docstrings, documentação, logs, erros | português | |
| Commits, releases, nomes dos passos de workflow | português | |
| Siglas e nomes próprios | como são | `ibge`, `osm`, `pmtiles` |

Nomes que o ecossistema espera ficam como são: `README.md`, `LICENSE`, `requirements.txt`, e, dentro do pacote de
recursos, as pastas `fonts/` e `sprites/` no formato que o MapLibre procura.

Todo formato publicado tem um campo de versão (`"schema": 1`), que só sobe quando um leitor antigo quebraria.

## Regras do repositório

- O repositório é independente e anônimo: **não cita nenhum aplicativo específico que use os pacotes**, não tem
  dados pessoais, e-mail pessoal nem caminhos de máquina local. Commits usam o e-mail anônimo do GitHub
  (`…@users.noreply.github.com`).
- Os arquivos gerados (`gerador/data/`) ficam fora do git: os pacotes vão para as releases.
- Código e dados em commits separados.
- Nasce privado e só fica público depois da revisão do dono.

## Licenças

- **Pacotes:** base derivada do OpenStreetMap, Open Database License (ODbL) 1.0. Crédito obrigatório:
  "© colaboradores do OpenStreetMap". Os tiles vêm do build da Protomaps, que também é ODbL.
- **Cobertura do solo** (a camada `landcover`, nos zooms 0 a 7): derivada do ESA WorldCover, sob CC BY 4.0.
  Crédito obrigatório: "© ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium".
- **Código do gerador:** MIT, como nos projetos irmãos.
- **Recursos:** fontes Noto Sans sob SIL Open Font License; ícones derivados de um conjunto MIT.
- **Recorte por estado:** malha das UFs do IBGE.

Os detalhes estão em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md), seção "Licenças e crédito".
