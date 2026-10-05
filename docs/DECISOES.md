# Decisões

Registro do que foi decidido até 2026-10-01 e por quê. A coluna "Situação" separa o que o dono **confirmou** do
que é **proposta** ainda sem confirmação. Uma proposta vale como padrão de trabalho, mas pode mudar antes de o
gerador ser escrito. As decisões que ainda dependem de medição estão em [`PENDENCIAS.md`](../gerador/PENDENCIAS.md).

## Resumo

| ID | Decisão | Situação |
|---|---|---|
| D1 | Projeto independente, em repositório próprio | Confirmada (2026-10-01: o dono pediu a pasta própria) |
| D2 | Nome `carcara` | Definitivo (2026-10-02: o dono manteve o nome) |
| D3 | Por enquanto, só documentação | Confirmada (2026-10-01) |
| D4 | Formato dos pacotes: PMTiles | Confirmada com a etapa A (2026-10-01) |
| D5 | Esquema de camadas: o do basemap da Protomaps, versão 4 | Confirmada com a etapa A (2026-10-01) |
| D6 | Origem dos tiles: recorte do build da Protomaps (etapa A). A geração própria (etapa B) não está planejada | Confirmada (2026-10-01): só a etapa A |
| D7 | Na etapa B, gerar o Brasil inteiro e só então recortar por estado | Vale só para a etapa B, que não tem data |
| D8 | Um arquivo por estado, lido no lugar, sem desempacotar | Confirmada com a etapa A (2026-10-01) |
| D9 | Mesmo molde dos projetos irmãos: `catalogo.json`, releases, 29 dias, 3 gerações | Confirmada com a etapa A (2026-10-01) |
| D10 | Gerações diferentes podem conviver; versões maiores do esquema, não | Confirmada com a etapa A (2026-10-01) |
| D11 | Recorte pela malha das UFs do IBGE, com margem | Confirmada com a etapa A (2026-10-01) |

"Confirmada com a etapa A" quer dizer: em 2026-10-01 o dono escolheu a etapa A e mandou executar o desenho
como está. Os detalhes que ainda dependem de número (zoom da base, pacote leve, gerações mantidas) continuam
em aberto em [`PENDENCIAS.md`](../gerador/PENDENCIAS.md).

## D1: projeto independente

O mapa base não entra no repositório dos tiles de roteamento, embora os dois partam do OpenStreetMap.

- **Ciclos de compatibilidade diferentes.** Os tiles de roteamento são presos à versão do motor que os lê: uma
  troca de versão obriga a gerar tudo de novo. O mapa base é preso ao esquema de camadas. Juntos, a troca de um
  forçaria nova publicação do outro.
- **Ferramentas e peso diferentes.** Um usa o motor de roteamento; o outro, o `pmtiles` e depois o Planetiler
  (Java). Somar os dois num job só arrisca estourar disco e tempo da máquina do GitHub.
- **Falha isolada.** A publicação é recusada quando a geração registra falha. Juntos, um problema no mapa
  seguraria os pacotes de rota, e o contrário.
- **Público diferente.** Quem quer só o mapa para um site não precisa de roteamento, e quem quer rotas não
  precisa de 15 níveis de zoom.

O que os projetos compartilham é o desenho, não o repositório: o formato do `catalogo.json`, a malha do IBGE, a
divisão em pacote base mais pacotes por estado, a regra dos 29 dias e a limpeza de releases antigas.

## D2: nome

`carcara` é o nome definitivo desde 2026-10-02. O critério foi o mesmo dos irmãos, em que a ave tem a ver com a função (pardal é o
apelido do radar; andorinha é a ave que viaja): o carcará enxerga o terreno de cima e vive no Brasil inteiro.
É uma palavra só e funciona como nome de repositório e de arquivo.

Alternativas levantadas:

| Nome | Ligação com o mapa base | Ponto fraco |
|---|---|---|
| Sabiá | Ave nacional; "minha terra tem palmeiras onde canta o sabiá" | Sem acento, `sabia` lê como verbo |
| João-de-barro | Constrói a casa de terra: a base onde os outros se apoiam | Nome longo em arquivo e em código |
| Seriema | Ave que anda no chão do cerrado | Menos conhecida fora do Centro-Oeste |
| Bem-te-vi | O nome fala de ver | Combinaria também com radar; hífens |
| Arara | Colorida, como um mapa rico | Ligação mais fraca com a função |

Nomes guardados para projetos futuros, para não gastar aqui: **Coruja** (busca de endereço offline) e
**Quero-quero** (condição e risco da via).

Trocar o nome depois de publicar custa caro: ele vira endereço (repositório, nome dos arquivos, links). Se for
mudar, é antes da primeira release. O que carrega o nome: a pasta, o repositório, o prefixo dos arquivos
(`carcara-GO.pmtiles`), o pacote Python do gerador e as variáveis de ambiente (`CARCARA_*`).

## D4: formato PMTiles

Um arquivo PMTiles guarda a pirâmide inteira de tiles com um índice, e pode ser lido por faixas de bytes, tanto
por HTTP quanto do disco.

- **Um arquivo por estado**, em vez de centenas de milhares de arquivos pequenos.
- **Tiles repetidos são guardados uma vez só** (mar, áreas vazias).
- **Lido direto por quem desenha:** o MapLibre no Android lê `pmtiles://` desde a versão 11.7.0, e há leitores
  em Java, JavaScript, Python, Go e outras linguagens.
- **Serve também na web:** hospedado em qualquer lugar que aceite pedidos por faixa, um site lê o pacote sem
  servidor de tiles.
- **Recortar é barato:** o `pmtiles extract` copia os tiles de uma região de um arquivo para outro sem decodificar.

Alternativa descartada: `.tar.gz` com os tiles soltos (o formato dos tiles de roteamento). Obrigaria a
desempacotar centenas de milhares de arquivos no aparelho, que é o problema que o projeto quer resolver.

## D5: esquema da Protomaps

O esquema define os nomes das camadas (`earth`, `water`, `roads`, `places`, `pois`…) e dos atributos (`kind`). Todo
estilo é escrito contra um esquema; trocar de esquema obriga a reescrever os estilos de quem consome.

| Opção | A favor | Contra |
|---|---|---|
| **Protomaps basemap v4** (escolhida) | Vai até o zoom 15; build diário público de onde recortar; perfil de geração aberto (BSD-3); estilos prontos; quem já desenha esse esquema não muda nada | Menos estilos de terceiros que o OpenMapTiles |
| OpenMapTiles | Muitos estilos prontos; é o esquema de serviços públicos de tiles online | Zoom máximo 14 (de memória, não conferido); não há build público recortável, só geração própria; exige reescrever estilos feitos para a Protomaps |

A escolha pesa mais para quem já tem estilos escritos para a Protomaps. Um consumidor novo, sem estilo nenhum,
perde pouco com qualquer das duas; o zoom 15 e o caminho rápido da etapa A continuam a favor da Protomaps.

## D6: a origem dos tiles é o recorte do build da Protomaps (etapa A)

**Decisão de 2026-10-01: o projeto fica na etapa A.** A etapa B foi considerada custosa demais e não tem data
nem item de trabalho. O que segue registra as duas, para a escolha poder ser revista.

O formato e o esquema não dependem da etapa; o que muda de uma para a outra é **de onde os tiles vêm**.

| Etapa | Origem | O que entrega | Custo |
|---|---|---|---|
| **A** | Recorte do build diário da Protomaps, por estado | Pacotes logo, sem montar geração de mapa | O conteúdo é o que a Protomaps decide; a geração depende do servidor dela |
| **B** | Geração própria com o Planetiler e o perfil aberto da Protomaps, a partir do extrato do Brasil | Independência; conteúdo sob medida; mesmo extrato dos tiles de roteamento | Geração mais pesada, ainda não medida |

Uma passagem de A para B **não mudaria nada para quem consome**: mesmo formato, mesmo esquema, mesmo catálogo.
Por isso ficar na etapa A não cria dívida: se um dia a B valer a pena, entra sem quebrar ninguém.

O que a etapa A entrega é o mapa que a Protomaps publica, completo até o zoom 15 em cada estado. O que fica de
fora, porque só a etapa B permitiria:

- **Independência:** nenhuma dependência do servidor de builds da Protomaps.
- **Mapa e rotas do mesmo extrato:** a rota nunca passa por uma via que o mapa não desenha. Não exige o mesmo
  repositório: basta os dois projetos gerarem no mesmo ciclo e cada catálogo registrar a data e o md5 do extrato.
- **Conteúdo sob medida:** por exemplo, a superfície da via (o esquema atual não tem atributo de pavimento),
  postos de combustível em zoom mais baixo. Sempre como acréscimo, sem remover nem renomear nada do esquema.

## D7: na etapa B, o Brasil inteiro antes do recorte

Vale só para a etapa B, que não está planejada (D6). Fica registrada para o caso de a escolha ser revista.

Gerar estado por estado, cada um do seu extrato, deixaria os tiles de divisa incompletos: cada lado teria só os
dados do seu estado. Gerando o Brasil inteiro e recortando depois, o tile de divisa é completo e idêntico nos
dois pacotes vizinhos, como acontece no recorte da etapa A (conferido na medição M4).

## D8: arquivo lido no lugar

O pacote é usado como veio: baixa, confere o sha256 e lê. Não há etapa de extração. Apagar ou atualizar um
estado é trocar um arquivo. Os detalhes para quem consome estão em [`CONSUMO.md`](CONSUMO.md).

## D9: mesmo molde dos projetos irmãos

- `catalogo.json` na raiz, chaves em inglês, campo `schema`.
- Pacotes como arquivos de release; a etiqueta da release é o `build_id`.
- Geração a cada 29 dias pelo GitHub Actions: cron diário mais um job que só deixa gerar com 29 dias ou mais.
- Ficam as 3 gerações mais recentes; as anteriores são apagadas depois de cada publicação.
- Publicação recusada se a geração registrou falha ou se um pacote encolheu além da tolerância.

## D10: gerações e versões

Diferente dos tiles de roteamento, um tile de mapa não aponta para os vizinhos. Dois estados de gerações
diferentes funcionam juntos; o pior caso é uma emenda visível na divisa, onde uma via nova aparece de um lado só.
Por isso **atualizar um estado de cada vez é permitido**.

O que não pode se misturar é a **versão maior do esquema**: um estilo escrito para a versão 4 pode não desenhar
nada de um tile da versão 5. O catálogo publica a versão do esquema, e quem consome deve recusar uma versão
maior que não conhece.

## D11: recorte pela malha do IBGE

Cada estado é recortado pelo polígono oficial da UF, com uma margem, e não por um retângulo. O retângulo de um
estado comprido ou diagonal inclui muito território vizinho, e o pacote cresceria sem necessidade. A malha e a
margem são as mesmas dos tiles de roteamento, para um aplicativo poder escolher os pacotes dos dois projetos com
a mesma conta.

## Alternativas descartadas para o projeto como um todo

| Alternativa | Por que não |
|---|---|
| Continuar baixando tile a tile do build público | Lento, limitado ao zoom 13 por estado, e contra o pedido da própria Protomaps |
| Servidor próprio espelhando o build | Custo mensal e manutenção; as releases do GitHub não cobram armazenamento nem tráfego |
| Entregar dentro do projeto de tiles de roteamento | Ver D1 |
| Trocar para o esquema OpenMapTiles | Ver D5 |
| Fabricar o mapa por conta própria (etapa B) | Custosa demais para o ganho; ver D6. Fica registrada, sem data |
