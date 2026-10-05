# Como usar os pacotes

Guia para quem vai ler os pacotes em um aplicativo ou site. Proposta de 2026-10-01: descreve como os pacotes
foram pensados para ser usados. A leitura no Android foi conferida com um pacote real do Distrito Federal, num
emulador (medição M5, em [`FONTES.md`](../gerador/FONTES.md)); o resto ainda não foi exercitado, porque nenhum pacote foi
publicado.

## Em resumo

1. Ler o `catalogo.json` e escolher os pacotes pelo `bbox`: os estados por onde vai passar, a base para o resto
   do país, e os recursos.
2. Conferir que a versão maior de `tileset.version` é uma que os seus estilos conhecem.
3. Baixar cada arquivo de `release_url` + `file` e conferir o `sha256`.
4. Usar o arquivo `.pmtiles` como veio. Não há o que extrair.
5. Mostrar o crédito do campo `attribution`.

## Escolher os pacotes

- O `bbox` de cada pacote é `[lat mín, lon mín, lat máx, lon máx]` da área que ele atende; o `bbox_tiles`, na
  mesma ordem, é a área que os tiles do zoom mais fundo dele cobrem, um pouco maior. Um ponto pode cair no
  `bbox` de mais de um estado (retângulos se sobrepõem): baixar todos os que contêm o ponto, ou conferir contra o
  polígono se o aplicativo tiver a malha.
- Para uma rota, juntar os estados cujo `bbox` toca o retângulo da rota.
- A base cobre o Brasil inteiro em zoom baixo. Sem ela, fora dos estados instalados não há mapa.

## Ler os tiles

### No MapLibre para Android e iOS

O MapLibre lê PMTiles sozinho: no Android, desde a versão 11.7.0. Basta prefixar o endereço da fonte com
`pmtiles://`:

```json
{
  "sources": {
    "mapa": { "type": "vector", "url": "pmtiles://file:///caminho/para/carcara-GO.pmtiles" }
  }
}
```

Formas aceitas: `pmtiles://file://` (arquivo no aparelho), `pmtiles://asset://` (arquivo dentro do aplicativo) e
`pmtiles://https://` (arquivo remoto, lido por faixas). A forma `pmtiles://file://` foi conferida com um pacote
real no MapLibre 13.4.1 para Android: o mapa leu as vias direto do arquivo, e o crédito veio dos metadados do
pacote. As outras duas formas não foram testadas.

### Com mais de um estado instalado

Cada arquivo é uma fonte separada, e uma camada de estilo lê de uma fonte só. Com vários estados, há três
caminhos:

| Caminho | Como | Quando usar |
|---|---|---|
| **Servidor local** | Um pequeno servidor HTTP em `127.0.0.1` que recebe `/{z}/{x}/{y}` e procura o tile nos pacotes instalados; o estilo aponta para ele como uma fonte só | Recomendado para aplicativos: uma fonte, qualquer número de estados, e o mesmo servidor entrega ícones e fontes |
| Uma fonte por arquivo | Repetir as camadas do estilo para cada fonte | Só com um ou dois estados; o estilo cresce a cada pacote |
| Juntar em um arquivo | Combinar os pacotes em um PMTiles só, no aparelho | Não recomendado: reescreve arquivos grandes a cada mudança |

No servidor local, a ordem de busca sugerida é: pacotes de estado, depois a base, depois o que o aplicativo já
tinha (cache próprio ou rede). Um tile de divisa existe em dois pacotes; qualquer um serve.

Dois cuidados no Android, para quem usa o servidor local com o MapLibre:

- o Android bloqueia HTTP sem criptografia por padrão: é preciso liberar `127.0.0.1` na configuração de
  segurança de rede do aplicativo;
- o MapLibre deixa de fazer pedidos quando o sistema informa que não há rede, inclusive para `127.0.0.1`. Quem
  serve tiles locais precisa avisar o MapLibre de que está conectado (`MapLibre.setConnected(true)`).

### Fora do MapLibre

Qualquer leitor de PMTiles serve. Em Java e Kotlin, a biblioteca `ch.poole.geo.pmtiles-reader` (conferida na
versão 0.3.6) abre um arquivo local com `Reader(File)` ou `Reader(FileChannel)` e entrega os bytes com
`getTile(z, x, y)`.

- Os bytes vêm **como estão no arquivo**. O cabeçalho informa a compressão (`getTileCompression()`); nos pacotes
  é gzip (conferido no cabeçalho de três recortes), então descompactar antes de decodificar o MVT. Um
  decodificador que receba os bytes ainda compactados pode devolver "nenhuma camada" em vez de um erro. Um
  servidor local pode entregar os bytes compactados com o cabeçalho `Content-Encoding: gzip`.
- Um tile que não está no pacote volta como `null`, sem exceção: é assim que se descobre que é hora de procurar
  em outro pacote.
- Ler é rápido: 100 tiles do zoom 15, lidos e descompactados em sequência, levaram cerca de 0,16 s num emulador.
- `getBounds()` devolve oeste, sul, leste, norte (longitude primeiro), como o cabeçalho do arquivo.
- Não compartilhar o mesmo leitor entre threads sem conferir que a biblioteca permite: um leitor por thread, ou
  um conjunto de leitores, é o caminho seguro.
- O `y` segue a convenção XYZ (origem no canto superior esquerdo), a mesma dos endereços `/{z}/{x}/{y}`.

### Na web

Hospedado em qualquer servidor que aceite pedidos por faixa, o pacote é lido direto pelo MapLibre GL JS com a
biblioteca `pmtiles`, sem servidor de tiles. Os arquivos de release do GitHub servem para **baixar**; para ler
direto do navegador, copie o pacote para o seu armazenamento (o GitHub redireciona os downloads e não é feito
para isso).

## Zoom

- Os pacotes de estado vão do zoom 0 ao 15; o pacote leve de cada estado, do 0 ao 13; a base, do 0 ao 9.
- Com o pacote leve, declarar `maxzoom: 13` na fonte: do zoom 14 em diante o mapa amplia o tile do 13, sem o
  detalhe de rua.
- **Não existe dado acima do zoom 15.** Declarar `maxzoom: 15` na fonte: o MapLibre amplia o tile do zoom 15
  para os zooms maiores. Um desenhador próprio precisa fazer o mesmo.
- Onde só a base está instalada, o mapa tem detalhe até o zoom dela e é ampliado dali em diante.

## Estilo

Os tiles seguem o esquema do basemap da Protomaps, versão 4. Servem:

- os estilos prontos da Protomaps (pacote de estilos `@protomaps/basemaps`, da versão 4.0.0 em diante), em mais
  de uma variação de cores;
- um estilo próprio, escrito contra as camadas do esquema, usando o atributo `kind`. Na versão 4.15.2 os pacotes
  têm nove camadas: `earth`, `landcover`, `landuse`, `water`, `buildings`, `boundaries`, `roads`, `places` e
  `pois`. A lista de cada pacote está nos metadados dele (`vector_layers`). A documentação cita também `transit`
  (vazia), e há estilos que leem `physical_point`: nenhuma das duas aparece nos metadados nem nos tiles
  conferidos desta versão, e uma camada de estilo apontada para uma camada que não existe não desenha nada.

Atributos da camada `roads`: `kind`, `kind_detail`, `ref`, `shield_text`, `network`, `oneway`, `service`, `is_link`,
`is_tunnel`, `is_bridge`. **Não há atributo de superfície** (pavimentada ou não) no esquema atual, e os pacotes
não acrescentam nada ao que a Protomaps publica.

Um estilo escrito para outro esquema (OpenMapTiles, por exemplo) **não desenha nada** destes tiles e não acusa
erro: os nomes das camadas não batem.

## Ícones e fontes

O pacote `carcara-recursos.tar.gz` traz as pastas no formato que o MapLibre espera:

```
fonts/<nome da fonte>/<faixa>.pbf      ex.: fonts/Noto Sans Regular/0-255.pbf
sprites/<versão>/<variação>.json|png   e as versões @2x
```

No estilo:

```json
{
  "glyphs": "http://127.0.0.1:<porta>/fonts/{fontstack}/{range}.pbf",
  "sprite": "http://127.0.0.1:<porta>/sprites/v4/light"
}
```

As fontes disponíveis são Noto Sans Regular, Medium e Italic, com as 256 faixas de cada uma. Um estilo que
peça outra fonte fica sem rótulos; é o caso de um estilo gerado para hindi, marata ou nepalês, que pede uma fonte
para a escrita devanágari que o pacote não traz.

As folhas de ícones ficam em `sprites/v4/`, em cinco variações de cor: `light`, `dark`, `white`, `grayscale` e
`black`, cada uma em 1x e 2x. As folhas `light` e `dark` têm 53 ícones; as outras três, só os 18 que não são de
pontos de interesse. Não há ícone de posto de combustível nem de prefeitura (`townhall`), embora o estilo de
referência peça este último. Os escudos de rodovia vão até 5 caracteres.

O pacote traz ainda `LEIAME.md` (origem e revisão), `fonts/OFL.txt` e `sprites/LICENCA.md` (as licenças).

## Atualizar e apagar

- **Atualizar:** baixar o arquivo novo para um nome temporário, conferir o sha256 e só então trocar pelo antigo.
  Uma queda no meio não estraga o que já funcionava.
- **Um estado de cada vez é permitido.** Pacotes de gerações diferentes convivem; o pior caso é uma emenda
  visível na divisa.
- **Versão maior diferente não convive.** Se o catálogo publicar uma versão maior nova, os estilos precisam ser
  atualizados junto, e os pacotes antigos e novos não devem ser desenhados com o mesmo estilo.
- **Apagar:** remover o arquivo. Nenhum outro pacote depende dele.
- As releases guardam as 3 gerações mais recentes. Usar sempre o `release_url` do catálogo.

## Crédito

Mostrar no mapa o texto do campo `attribution` do catálogo. No mínimo: "© colaboradores do OpenStreetMap", à
vista (por exemplo, no canto do mapa). Quem desenha a camada `landcover` (zooms 0 a 7) também precisa mostrar,
em algum lugar do produto, a frase do ESA WorldCover: "© ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium".
