# Geração

Como os pacotes são gerados e como serão validados e publicados. Proposta de 2026-10-01. O recorte (passos 1
a 6 da etapa A) já existe no gerador e foi executado para o Distrito Federal e Goiás; a validação, o catálogo e a
publicação ainda não. O projeto usa só a etapa A. As opções do `pmtiles` foram conferidas na documentação e no código-fonte da
ferramenta (ver [`FONTES.md`](../gerador/FONTES.md)).

## Etapa A: recorte do build da Protomaps

A Protomaps publica todo dia um arquivo PMTiles do mundo inteiro, do zoom 0 ao 15. O `pmtiles extract` lê esse
arquivo pela internet e copia para um arquivo local só os tiles de uma região, baixando apenas as faixas de
bytes necessárias.

### Passo a passo

1. **Escolher o build.** Ler `https://build-metadata.protomaps.dev/builds.json` e pegar a entrada mais recente.
   Cada entrada tem `key` (nome do arquivo), `size`, `md5sum`, `b3sum`, `uploaded` e `version`. Recusar se a versão
   maior não for a esperada (4).
2. **Baixar a malha das UFs** do IBGE e conferir que tem as 27 unidades.
3. **Montar os polígonos:** cada UF com a margem de 0,05°, gravada como GeoJSON; o Brasil para a base.
4. **Recortar cada estado:**

   ```
   pmtiles extract https://build.protomaps.com/<key> carcara-GO.pmtiles \
       --region=GO.geojson --maxzoom=15 --download-threads=4
   ```

   O arquivo é gravado com um nome provisório e só recebe o nome final quando está inteiro. O **pacote leve** do
   estado sai do arquivo completo já no disco, sem nenhum pedido ao build:

   ```
   pmtiles extract carcara-GO.pmtiles carcara-GO-leve.pmtiles --maxzoom=13
   ```

5. **Recortar a base:**

   ```
   pmtiles extract https://build.protomaps.com/<key> carcara-base.pmtiles \
       --region=brasil.geojson --maxzoom=9
   ```

6. **Montar o pacote de recursos:** ícones e fontes da versão do esquema usada, em `carcara-recursos.tar.gz`.
7. **Validar** (seção "Travas antes de publicar").
8. **Calcular** tamanho e sha256 de cada arquivo, ler o número de tiles e os zooms do cabeçalho
   (`pmtiles show`) e montar o `catalogo.json`.
9. **Publicar** (seção "Publicação").

### Opções do `pmtiles extract`

| Opção | O que faz | Padrão |
|---|---|---|
| `--region` | Arquivo GeoJSON local (Polygon ou MultiPolygon) com a área de interesse | |
| `--bbox` | Retângulo: `lon mín, lat mín, lon máx, lat máx` | |
| `--maxzoom` | Zoom máximo, inclusive | o do arquivo |
| `--minzoom` | Zoom mínimo, inclusive. Maior que zero "pode exigir muito mais pedidos" | 0 |
| `--download-threads` | Pedidos em paralelo | 4 |
| `--overfetch` | Quanto baixar a mais para juntar pedidos pequenos (0,05 = 5%) | 0,05 |
| `--dry-run` | Calcula os tiles do recorte sem baixar. Está no código-fonte, não na página de documentação | desligado |

O arquivo de origem precisa estar "clustered" (tiles ordenados no arquivo); os builds da Protomaps estão.

### O que a etapa A exige da máquina

Pouca memória e pouco processamento: é cópia de bytes. O gargalo é a rede e o disco para os arquivos de saída.
O total baixado da Protomaps por geração é, mais ou menos, a soma dos tamanhos dos pacotes. Tempo e tamanho
reais são a medição M3.

### Convivência com a Protomaps

A página de downloads desaconselha apontar aplicativos para o endereço dos builds e recomenda copiar o tileset
para armazenamento próprio. Um recorte a cada 29 dias é exatamente essa cópia. Cuidados:

- manter os 4 pedidos em paralelo do padrão, sem acelerar;
- ler sempre o `builds.json` em vez de montar o endereço na mão ("os endereços podem mudar");
- a Protomaps guarda todos os builds da última semana e o mais recente de cada versão: um build escolhido hoje
  pode não existir daqui a um mês, então a geração nunca depende de um build antigo.

## Etapa B: geração própria

> **Não planejada.** Em 2026-10-01 o dono decidiu ficar na etapa A ([`DECISOES.md`](DECISOES.md), D6). Esta
> seção fica como registro do que a etapa B seria; nada dela entra no gerador.

O basemap da Protomaps é gerado por um perfil aberto do Planetiler (Java 21 ou mais novo). O mesmo perfil,
aplicado ao extrato do Brasil, produz tiles no mesmo esquema.

### Passo a passo previsto

1. **Baixar o extrato do Brasil** e o md5 publicado ao lado. O endereço usado pelos tiles de roteamento é
   `https://download.openstreetmap.fr/extracts/south-america/brazil-latest.osm.pbf`.
2. **Gerar o Brasil inteiro** com o perfil da Protomaps, numa versão fixada. O README do perfil dá o exemplo
   `java -jar target/*-with-deps.jar --download --force --area=monaco`. Para o Brasil, a forma provável é:

   ```
   java -jar protomaps-basemap-<versão>-with-deps.jar --download --osm_path=brazil-latest.osm.pbf \
       --output=brasil.pmtiles
   ```

   As opções `--osm_path` e `--output` são do Planetiler e foram escritas de memória. O perfil baixa também as
   fontes auxiliares que usa (Natural Earth e outras). O comando exato e a lista das fontes precisam ser
   conferidos na versão escolhida (medição M6).
3. **Recortar por estado**, agora de um arquivo local, com os mesmos comandos da etapa A.
4. **Validar e publicar** como na etapa A.

### Regras da etapa B

- **Versão do perfil fixada** no gerador, como a versão do motor é fixada nos tiles de roteamento. Subir a versão
  é mudança deliberada, com nota na release.
- **Brasil inteiro antes do recorte** (decisão D7), para o tile de divisa sair completo.
- **Acréscimos próprios só como acréscimo.** Atributo ou camada nova pode entrar; nada do esquema original é
  removido nem renomeado, para os estilos prontos continuarem funcionando. Cada acréscimo entra em
  `tileset.extensions` no catálogo e na documentação.
- **Mesmo extrato dos tiles de roteamento, quando possível.** O catálogo registra a data e o md5 do extrato; se
  os dois projetos gerarem no mesmo dia, ficam com o mesmo `build_id`.

### O que a etapa B exige da máquina

Não medido. O README do perfil diz que ele gera o planeta em 2 a 3 horas, sem dizer em que máquina; o Brasil é
uma fração disso. Falta saber se cabe na máquina gratuita do GitHub Actions em memória, disco e tempo, contando as
fontes auxiliares que o perfil baixa. Seria a medição M6, que não será feita enquanto a etapa B não tiver data.

## Travas antes de publicar

Rodam no fim de toda geração (`carcara/validation.py`). Se qualquer uma falhar, o `generate.py` termina com
código 1, lista os problemas e deixa a marca `GERACAO_EM_ANDAMENTO`; nada é publicado. A única trava que pode ser
passada por cima é a de queda, com `--accept-drop`, e isso fica escrito no log.

| Trava | O que confere |
|---|---|
| Estrutura | `pmtiles verify` em cada arquivo: os completos, os leves e a base |
| Cabeçalho | Tiles MVT, compressão gzip, "clustered", zoom mínimo 0 e zoom máximo do tipo do pacote (15, 13 no leve, 9 na base); a área do arquivo cobre o retângulo da UF (na base, o de todas as UFs) |
| Conteúdo | Sobre a capital de cada UF: o tile do zoom mais fundo do pacote existe, descompacta, decodifica e tem feições em `roads`; o tile do zoom 12 tem feições em `places`. Na base, o tile do zoom 9 sobre Brasília tem as duas |
| Divisa | Para cada par de UFs vizinhas (51 pares no país), o tile sobre um ponto da divisa, nos zooms 15 e 12, existe nos dois pacotes e é idêntico byte a byte |
| Tamanho | Nenhum arquivo chega a 1,9 GB (o limite de um arquivo de release é 2 GiB) |
| Queda | Nenhum pacote, completo ou leve, perde mais de 5% dos tiles ou dos bytes em relação ao catálogo publicado (um build truncado ou uma malha errada passariam despercebidos sem isso). Na primeira geração não há com o que comparar, e o log diz |
| Versão | Os metadados de cada pacote trazem a versão do esquema do build desta geração, e a versão maior é a 4 |
| Completude | Cada UF pedida, o leve de cada uma, a base e os recursos existem no disco, do tamanho anotado. Uma geração de só algumas UFs passa nas travas, mas é marcada como parcial e não é publicável |
| Recursos | O pacote de recursos abre; tem as 256 faixas das três fontes, as 20 folhas de ícones, as licenças e o `LEIAME.md`; cada folha tem os ícones que o estilo de referência pede, e nenhum ícone do índice fica fora da imagem |

Os ícones exigidos saem da fonte dos estilos de referência (`protomaps/basemaps`, `styles/src/base_layers.ts`, na
revisão `42ffaaa` de 2026-09-11): a seta de mão única, o ponto de cidade e o de capital, os escudos de rodovia de 1
a 5 caracteres e, nas variações `light` e `dark`, 35 ícones de pontos de interesse. O estilo de referência pede
ainda `townhall`, que a folha de origem não tem; isso é uma falha de lá, e a trava não o exige.

## Agendamento

O workflow `gerar.yml` roda todo dia às 06:17 e às 12:17 UTC (03:17 e 09:17 em Brasília, fora do minuto zero), como
nos projetos irmãos, e pode ser disparado à mão. São dois por dia porque um disparo pulado não avisa ninguém: o segundo
cobre o primeiro e, se o primeiro já publicou, só confere a data e para. A regra fica em `carcara/schedule.py`, e o
workflow a consulta por `scripts/due.py`.

- Job `interval`: lê o `built_at` do `catalogo.json` da raiz e só deixa gerar com 29 dias ou mais. A conta é
  arredondada (12 horas), para o horário da geração não empurrar a seguinte para o dia depois.
- **Geração extra por data** (`GENERATE_FROM` no workflow, `--generate-from` no `due.py`), como nos projetos
  irmãos: a partir do dia marcado (UTC), gera se a publicada for de antes dele, e tenta de novo nos dias seguintes
  se falhar; depois de publicar, não tem mais efeito, e os 29 dias passam a contar dela. Marcada para 2026-10-06.
- **Sem `catalogo.json` na raiz, o agendamento não gera.** A primeira geração é sempre disparada à mão, para a
  primeira release nunca sair sozinha. Nisto o projeto difere dos irmãos, de propósito.
- Catálogo que não dá para ler, ou sem a data: o agendamento não gera, e o job termina com erro, para alguém ver.
- Disparo à mão sempre gera, com ou sem catálogo.
- O catálogo é lido do checkout, e no agendamento o checkout é o da ponta do `main`: um disparo que esperou na
  fila atrás de uma publicação vê o catálogo novo.
- Job `generate`: só roda se o `interval` liberou. Publica no agendamento; à mão, só com a opção `publish` marcada.
  Sem ela, gera e valida, e o relatório fica nos artefatos do run por 14 dias (também quando a geração falha).
- As outras opções do disparo à mão: `states` (só algumas UFs; geração parcial não é publicada) e `accept_drop`
  (passa por cima da trava de queda). O que é digitado chega aos comandos por variável de ambiente.
- Uma geração por vez: um disparo que chega com outra em curso espera, não cancela.
- Se a geração falhar, tenta de novo no dia seguinte: o `built_at` publicado continua velho.
- No agendamento, só roda no repositório oficial: um fork não gera sozinho.

O workflow ainda não rodou no GitHub: o repositório não foi criado.

## Publicação

`python scripts/publish.py --release --commit --push`, com a lógica em `carcara/publishing.py`. Antes de
qualquer coisa, as travas da publicação: a geração é completa (as 27 UFs), não tem a marca de geração caída, e
cada arquivo no disco tem o tamanho e o sha256 que o catálogo diz.

1. Criar a release em rascunho, com a etiqueta `build_id`. Uma release já publicada com essa etiqueta barra tudo;
   um rascunho é retomado.
2. Enviar os 56 arquivos. O que já está na release com o tamanho e o sha256 certos não sobe de novo.
3. Conferir na release o tamanho e o sha256 de cada arquivo, pelo que o GitHub informa (`digest`). Se o GitHub
   não informar o sha256 de algum, ou se algum não bater, a release continua rascunho.
4. Publicar a release.
5. Gravar o `catalogo.json` e a tabela de downloads do README, em um commit só desses dois arquivos.
6. Só depois do push, apagar as releases além das 3 mais recentes, e os rascunhos órfãos. A limpeza nunca apaga a release do
   catálogo publicado nem etiqueta fora do formato do `build_id`, e falha na limpeza vira aviso, não derruba a
   publicação.

## Lições herdadas dos projetos irmãos

Coisas que já deram problema e que o gerador deve nascer sabendo:

| Lição | O que fazer |
|---|---|
| O IBGE manda a malha compactada com gzip para os executores do GitHub, mesmo sem o pedido aceitar compressão | O download detecta e descompacta; a malha é sempre conferida depois de baixada |
| O `ubuntu-latest` muda de versão com o tempo | Fixar a imagem (`ubuntu-24.04`) e as versões das actions |
| O agendamento do GitHub atrasa horas e pode pular disparos, sobretudo em repositório novo e no minuto zero | A regra "29 dias ou mais" tolera atraso; o cron fica no minuto 17 |
| Um run agendado que espera na fila lê o catálogo de antes da publicação e tenta gerar de novo | O job `interval` lê o catálogo do `main` atual, não o do commit que disparou |
| `raw.githubusercontent.com` responde 404 em repositório privado | Enquanto o repositório for privado, a data vem do arquivo no checkout |
| O extrato do Brasil troca uma vez por dia, por volta de 01:00 UTC; um download nessa hora pode pegar meio arquivo | Conferir o md5 publicado ao lado, antes e depois do download |
| Downloads grandes caem | Download com retomada e novas tentativas |
| Apagar release é irreversível | As travas da limpeza descritas em "Publicação" |
| Nos tiles de roteamento, a mesma geração não sai idêntica byte a byte em outra máquina | Não presumir que sai idêntica aqui: comparar contagens e tamanhos com tolerância. Na etapa A, o recorte do mesmo build deve sair idêntico; conferir na medição M4 |
