# Arquivos de teste

## `bairro.pmtiles`

Um recorte pequeno e de verdade, para os testes que usam o binário `pmtiles`: dois tiles do centro de Brasília
(14/6012/8920 e 15/12025/17840), 86 KB. Foi recortado uma vez do pacote do Distrito Federal, que por sua vez veio
do build `20261001.pmtiles` do basemap da Protomaps (esquema 4.15.2):

```
pmtiles extract carcara-DF.pmtiles bairro.pmtiles --bbox=-47.886,-15.797,-47.882,-15.793 --minzoom=14 --maxzoom=15
```

Os dados são do OpenStreetMap, sob a Open Database License (ODbL) 1.0: © colaboradores do OpenStreetMap.

Os testes conferem o tamanho exato de um tile deste arquivo; se ele for recortado de novo de outro build, os
números dos testes mudam junto.
