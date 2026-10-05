"""Tudo o que muda o resultado de uma geração, num lugar só."""
from __future__ import annotations

import os
from pathlib import Path

GENERATOR_DIR = Path(__file__).resolve().parent.parent
REPO = GENERATOR_DIR.parent
DATA = GENERATOR_DIR / "data"
RAW = DATA / "raw"                   # malha do IBGE, arquivo de recursos baixado
DIST = DATA / "dist"                 # os pacotes e o catalogo.json desta geração
REGIONS = DATA / "regioes"           # um GeoJSON por UF, com a margem, e o do Brasil
MEASUREMENTS = DATA / "medicoes"     # resultados das medições de tamanho

# Índice dos builds diários da Protomaps e a base dos endereços. O build é escolhido sempre pelo índice: a página de
# downloads avisa que os endereços podem mudar.
BUILDS_INDEX_URL = "https://build-metadata.protomaps.dev/builds.json"
BUILD_BASE_URL = "https://build.protomaps.com/"

# Versão maior do esquema de camadas (basemap da Protomaps) que os pacotes seguem. Um build de outra versão maior é
# recusado: estilos escritos para a 4 podem não desenhar nada de um tile da 5.
TILESET_MAJOR_VERSION = 4

# Zoom máximo dos pacotes de estado (o esquema não tem dado acima do 15), do pacote leve e do pacote base.
MAX_ZOOM = 15
LIGHT_MAX_ZOOM = 13
BASE_MAX_ZOOM = 9

# Pedidos em paralelo ao build da Protomaps. É o padrão do `pmtiles extract`; o build é um serviço gratuito e não é
# para ser apressado. De propósito, nenhuma variável de ambiente muda este número.
DOWNLOAD_THREADS = 4

# O binário `pmtiles` (go-pmtiles). CARCARA_PMTILES aponta para ele quando não está no PATH.
PMTILES = os.environ.get("CARCARA_PMTILES") or "pmtiles"

# A versão do `pmtiles` com que o gerador foi conferido. A leitura do que a ferramenta escreve (extraction.py)
# depende do texto desta versão; outra é recusada. Trocar aqui = conferir de novo a simulação e o recorte.
# O sha256 de cada arquivo é o publicado na release da ferramenta; `scripts/install_pmtiles.py` confere ao baixar.
PMTILES_VERSION = "1.31.2"
PMTILES_RELEASE_URL = f"https://github.com/protomaps/go-pmtiles/releases/download/v{PMTILES_VERSION}/"
PMTILES_ASSETS = {
    ("Linux", "x86_64"): (f"go-pmtiles_{PMTILES_VERSION}_Linux_x86_64.tar.gz",
                          "3ed7dbf4ec2e6dfe5e25b6f70d1ffc932729f93c86db353bf514dd71010a312f"),
    ("Windows", "x86_64"): (f"go-pmtiles_{PMTILES_VERSION}_Windows_x86_64.zip",
                            "a658baa4d7e55020aef6ca17bd9ff9faa1582671266b36f58c52db0ac8e785a1"),
}

# Ícones e fontes: o repositório de recursos do basemap da Protomaps, numa revisão fixa. O arquivo é baixado pelo
# commit, e o conteúdo que entra no pacote é conferido pelo sha256 abaixo (resources.content_digest): se o que
# veio não é o que foi conferido, a geração para. Trocar a revisão = conferir os estilos de referência de novo.
ASSETS_REVISION = "028c18f713baecad011301ff7a69acc39bcc2ae7"
ASSETS_ARCHIVE_URL = "https://github.com/protomaps/basemaps-assets/archive/{revision}.tar.gz"
ASSETS_CONTENT_SHA256 = "adc3f37d6993a52f1562eb89d7a0e7b1f279bd17ca4838c9225e7dfc372a4968"

# De quantos em quantos dias o agendamento gera de novo.
GENERATION_INTERVAL_DAYS = 29

# Quantas gerações ficam nas releases: a do catálogo publicado e as anteriores mais recentes. As demais são apagadas
# no fim de cada publicação. 0 = não apaga nenhuma. CARCARA_KEEP_GENERATIONS muda.
_keep = os.environ.get("CARCARA_KEEP_GENERATIONS")
KEEP_GENERATIONS = int(_keep) if _keep not in (None, "") else 3

# O GitHub Releases recusa arquivo a partir de 2 GiB; esta é a trava, com folga.
MAX_ASSET_BYTES = 1_900_000_000

# Quanto um pacote pode encolher, em tiles ou em bytes, de uma geração publicada para a seguinte sem barrar a
# publicação. Um build truncado ou uma malha errada passariam despercebidos sem isto.
MAX_DROP = 0.05

# O pacote leve de cada estado (até o LIGHT_MAX_ZOOM), além do completo. CARCARA_LIGHT=0 desliga.
LIGHT_PACKS = os.environ.get("CARCARA_LIGHT", "1") != "0"

# Espaço livre exigido na unidade de data/ antes de recortar. Uma geração inteira ocupa cerca de 6 GB (4,6 GB dos
# estados, 1,3 GB dos leves, a base e os recursos); o dobro, para os arquivos provisórios e a folga.
# CARCARA_MIN_FREE_DISK_GB muda.
MIN_FREE_DISK_BYTES = int(float(os.environ.get("CARCARA_MIN_FREE_DISK_GB") or 12) * 1_000_000_000)

# O repositório das releases: CARCARA_REPO, senão o do GitHub Actions (GITHUB_REPOSITORY, que ele define sozinho),
# senão o oficial. Assim um repositório de teste publica e aponta os links para ele mesmo.
GITHUB_REPO = os.environ.get("CARCARA_REPO") or os.environ.get("GITHUB_REPOSITORY") or "Murkiriel/carcara"
RELEASE_URL = "https://github.com/" + GITHUB_REPO + "/releases/download/{tag}/"

# O crédito que vai no catálogo e nas notas da release. A frase do ESA WorldCover é a que a licença dele (CC BY 4.0)
# pede, palavra por palavra: a camada landcover dos tiles (zooms 0 a 7) vem dele.
ATTRIBUTION = ("© colaboradores do OpenStreetMap (ODbL 1.0); cobertura do solo: © ESA WorldCover project 2020 / "
               "Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium (CC BY 4.0); "
               "esquema e perfil: Protomaps; limites das UFs: IBGE")

# O crédito escrito dentro de cada pacote, no metadado `attribution`, que o MapLibre mostra sozinho no canto do mapa
# (decisão do dono em 2026-10-05). O build da Protomaps traz só o do OpenStreetMap; a camada `landcover` (zooms 0 a 7)
# vem do ESA WorldCover, sob CC BY 4.0, que pede o crédito junto do mapa.
EMBEDDED_ATTRIBUTION = (
    '<a href="https://www.openstreetmap.org/copyright" target="_blank">&copy; colaboradores do OpenStreetMap</a> | '
    '<a href="https://esa-worldcover.org/" target="_blank">&copy; ESA WorldCover project 2020 / Contains modified '
    'Copernicus Sentinel data (2020) processed by ESA WorldCover consortium</a>'
)

# Marca que o gerador cria em DIST ao começar e apaga ao terminar: se ela existe, a geração caiu no meio.
IN_PROGRESS_MARKER = "GERACAO_EM_ANDAMENTO"

# Malha oficial das UFs (API de malhas do IBGE, v3, qualidade máxima): o polígono de cada pacote.
IBGE_MESH_URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
                 "?formato=application/vnd.geo%2Bjson&intrarregiao=UF&qualidade=maxima")

USER_AGENT = "carcara-gerador/1"

# Margem, em graus (~5 km), em volta do polígono da UF: o recorte pega os tiles que tocam o polígono com a margem.
# Tile na margem de duas UFs entra nas duas.
STATE_MARGIN_DEG = 0.05

STATES = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
          "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais",
          "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
          "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia",
          "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
          "TO": "Tocantins"}

# Código IBGE da UF (campo `codarea` da malha) -> sigla.
IBGE_STATE_CODES = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA",
                    "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
                    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
                    "51": "MT", "52": "GO", "53": "DF"}
