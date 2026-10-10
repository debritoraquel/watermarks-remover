# Guia de organização do Relatório Ambiental — Fitoplâncton (Lajeado São José / CASAN)

Este guia acompanha o `mapear_figuras.py`. O script diz **onde** está cada problema e **de qual script** veio cada figura. Este guia diz **como** cada figura, tabela e seção deve ficar para o relatório ser cientificamente completo e reprodutível.

---

## 1. Fluxo de trabalho recomendado

1. Rodar o auditor na pasta do relatório (ver `README.md`) e abrir `_auditoria_relatorio/04_diagnostico_relatorio.md`.
2. Para cada figura do `03_figuras_no_relatorio.csv`:
   - confirmar o script e a linha que a gera;
   - abrir o script e anotar o **N**, o **teste/modelo**, as **permutações/bootstraps**, a **semente** e a **transformação/distância**. O CSV já traz o que foi detectado automaticamente;
   - reescrever a legenda pelo modelo da seção 3 abaixo.
3. Resolver as figuras **órfãs** (sem script): ou o script está fora da pasta, ou a imagem foi exportada à mão pelo RStudio. Nesse caso, acrescente `ggsave("nome.png", ...)` ao script para que ela possa ser regenerada.
4. Renumerar figuras e tabelas com **Referências > Inserir Legenda** e as citações com **Referência Cruzada**. Assim a numeração não volta a quebrar ao mover blocos de texto.
5. Reorganizar as seções segundo a estrutura da seção 5 e eliminar os parágrafos duplicados apontados pelo auditor.
6. Fechar as citações: cada citação deve estar na lista de referências e vice-versa (ABNT NBR 10520:2023 e NBR 6023:2018).

---

## 2. Regras gerais de figura em relatório técnico-científico

| Elemento | Regra |
|---|---|
| Posição da legenda | **Acima** da figura pela ABNT NBR 14724 (título + "Fonte:" abaixo). Escolha um padrão e use-o no documento inteiro. |
| Numeração | Arábica, sequencial, na ordem da **primeira citação** no texto. Sem duplicatas. Painéis identificados como (A), (B), (C)... |
| Autossuficiência | A legenda deve permitir entender a figura **sem ler o texto**: o que é, onde, quando, quantas amostras, qual teste, o que significam os símbolos. |
| Fonte | "Fonte: elaborado pelos autores (2026), script `XX.R`" ou a base de dados externa (MapBiomas, IBGE...). |
| Citação no texto | Toda figura precisa ser citada **antes** de aparecer ("(Figura 7)"). |
| Unidades | No eixo e na legenda: ind/mL, cél/mL, mg/L, µS/cm, %. Usar vírgula decimal. Avisar quando o eixo estiver em log₁₀. |
| Nomes de táxons | Em itálico; autoridade na primeira menção no texto ou na tabela de espécies. |
| Fatores | Trechos sempre com os mesmos nomes e na mesma ordem: Montante → Intermediário → Jusante → Reservatório. Campanhas: C1 (out/2022) e C2 (abr/2023). |

---

## 3. Modelos de legenda por tipo de análise

Preencha os colchetes com o que está no script. O auditor já sugere um esqueleto com os parâmetros que encontrou.

### 3.1 Boxplot / densidade / riqueza (descritivo + teste)
> **Figura X.** Densidade fitoplanctônica total (ind/mL, escala log₁₀) por trecho do Lajeado São José (Montante, Intermediário, Jusante e Reservatório) nas campanhas de outubro/2022 (C1) e abril/2023 (C2); N = [n] amostras ([n] por trecho e campanha). A caixa representa o intervalo interquartil, a linha central a mediana, as hastes 1,5 × IIQ e os pontos os valores extremos. Letras diferentes indicam diferença significativa (Kruskal-Wallis, H = [ ], p = [ ]; pós-teste de Dunn com ajuste de [Holm]).

### 3.2 Barras empilhadas de composição
> **Figura X.** Contribuição relativa (%) dos grupos taxonômicos ([Bacillariophyceae, Cyanobacteria, Chlorophyceae...]) para a densidade total (A) e para a riqueza (B) por trecho e campanha. Proporções calculadas sobre a soma das densidades de cada trecho; N = [n] amostras; [n] táxons no total.

### 3.3 Heatmap dos táxons dominantes
> **Figura X.** Densidade média (ind/mL, log₁₀(x+1)) dos 20 táxons mais abundantes por trecho e campanha. Táxons ordenados por [densidade total decrescente / agrupamento hierárquico]; escala de cor de [mín.] a [máx.].

### 3.4 Curvas de rarefação (iNEXT)
> **Figura X.** Curvas de rarefação (linha contínua) e extrapolação (linha tracejada) da riqueza de táxons (q = 0) baseadas em [incidência/abundância] por trecho, com intervalo de confiança de 95% (sombreado; [nboot] bootstraps). Os símbolos marcam a riqueza observada. Cobertura amostral: [Montante x%, ...].

Tabela associada: riqueza observada, Chao2, Jackknife 1 e 2, ± EP e % do estimado já amostrado.

### 3.5 Modelos de contagem (binomial negativa, hurdle)
> **Figura X.** Densidade predita (± IC 95%) de [fitoplâncton total (A), diatomáceas (B) e cianobactérias (C)] por trecho e campanha, estimada por [GLM binomial negativo (MASS::glm.nb) / glmmTMB nbinom2 com dispersão variando por campanha / modelo hurdle (parte binária logit + contagem binomial negativa truncada)]. Pontos: valores observados; N = [n]. Letras: contrastes de Tukey (emmeans) na escala da resposta.

Nos métodos, informe a família e o link, o offset (volume analisado), o diagnóstico de resíduos (DHARMa: uniformidade, dispersão, zeros) e a seleção por AIC.

### 3.6 Mapas (grupos de risco, bioindicadores)
> **Figura X.** Distribuição espacial da densidade de [cianobactérias] (cél/mL) nos 30 pontos amostrais do Lajeado São José em C1 (A) e C2 (B). O tamanho do símbolo é proporcional à densidade; as cores indicam as faixas da Portaria GM/MS nº 888/2021 (< 10.000; 10.000–20.000; > 20.000 cél/mL). Sistema de referência SIRGAS 2000 / UTM 22S; base hidrográfica: [ANA/SDE-SC]; uso do solo: MapBiomas Coleção [x], [ano]. Escala gráfica e norte no mapa.

Para os bioindicadores, liste na legenda os táxons somados.

### 3.7 PCA (físico-química, uso do solo, médias por táxon)
> **Figura X.** Biplot da Análise de Componentes Principais das variáveis [físico-químicas: pH, OD, condutividade, turbidez, NH₄⁺, PT...] padronizadas (média 0, DP 1), com os pontos amostrais coloridos por trecho e os símbolos por campanha. PC1 explica [x]% e PC2 [y]% da variância; vetores indicam as cargas das variáveis. N = [n].

Escreva uma frase que diga **por que** existem PCAs separadas: a físico-química descreve a qualidade da água; o uso do solo descreve a paisagem (buffer de 2 km, dados composicionais com transformação clr/arco-seno); a PCA das médias por táxon descreve o nicho ambiental das espécies.

### 3.8 Diversidade funcional (dendrograma, PCoA, índices, SES, CWM)
- **Dendrograma:** "Agrupamento UPGMA da matriz de distância de Gower entre [n] táxons com base em [10] atributos ([lista]); correlação cofenética = [ ]."
- **PCoA:** "Espaço funcional (PCoA da distância de Gower com correção de Cailliez); polígonos = envoltória convexa de cada trecho; PCoA1 [x]%, PCoA2 [y]%. PERMANOVA: pseudo-F = [ ], R² = [ ], p = [ ] ([999] permutações)."
- **Índices alfa (FRic, FEve, FDiv, FDis, RaoQ):** informe o **N de amostras com índice calculável**, porque o FRic exige mais espécies do que atributos (FD::dbFD, `corr = "cailliez"`, `m = [ ]`).
- **SES:** "Tamanho de efeito padronizado, SES = (obs − média nula)/DP nula, com [999] aleatorizações ([independentswap/richness]); linhas tracejadas em ±1,96."
- **CWM:** "Média ponderada pela comunidade (densidade relativa) para os atributos [lista]; PERMANOVA sobre a CWM transformada por Hellinger: R² = 10,1%, p = [ ]."

### 3.9 Diversidade beta (betapart)
> **Figura X.** Partição da diversidade beta multi-sítio (Sørensen, Baselga 2010) em substituição (βSIM) e aninhamento (βSNE), taxonômica (A) e funcional (B), por campanha. (C) Relação par a par entre βSIM e βSNE para pares dentro do mesmo trecho e entre trechos diferentes.

### 3.10 TITAN2
> **Figura X.** Limiares de mudança (change points) de táxons ao longo do gradiente de [variável], estimados por TITAN2 com [500] bootstraps e [250] permutações. Apenas táxons com pureza e confiabilidade ≥ 0,95 são mostrados; z− (decrescentes) em azul e z+ (crescentes) em vermelho; linhas = IC 5–95%.

### 3.11 k-prototypes + Sankey
> **Figura X.** Grupos de táxons definidos por k-prototypes (k = 6, escolhido por [silhueta/elbow]; λ = [ ]) sobre atributos mistos (quantitativos e categóricos). (A) Diagrama de Sankey: correspondência entre grupos e trechos. (B) Distribuição dos atributos quantitativos por grupo.

### 3.12 IndVal
> **Figura X.** Táxons indicadores (IndVal.g, indicspecies::multipatt) dos trechos e das combinações trecho × campanha; barras = valor IndVal; apenas p < 0,05 após [999] permutações. A (especificidade) e B (fidelidade) na Tabela [Y].

---

## 4. Tabelas que um relatório ambiental para a CASAN precisa ter

| Tabela | Conteúdo |
|---|---|
| Pontos amostrais | código, trecho, coordenadas (SIRGAS 2000), altitude, distância da captação |
| Cronograma | datas das campanhas, condição hidrológica (precipitação dos 7 dias anteriores) |
| Métodos analíticos | parâmetro, método (SMWW 10200; câmara Sedgwick-Rafter), limite de quantificação, laboratório |
| Físico-química por trecho | mediana (mín.–máx.) por trecho e campanha |
| **Conformidade legal** | valores observados × CONAMA 357/2005 (classe de enquadramento) e Portaria GM/MS 888/2021 (cianobactérias: ≥ 10.000 cél/mL → monitoramento semanal; ≥ 20.000 cél/mL → análise de cianotoxinas no ponto de captação; **conferir os limites no texto vigente**) |
| Lista de táxons | classe, táxon (itálico + autoridade), frequência de ocorrência, densidade média, potencial tóxico/colmatador |
| Estimadores de riqueza | S observado, Chao2, Jackknife 1 e 2, cobertura |
| Resultados dos modelos | coeficientes, EP, z, p, R² (pseudo), contrastes |
| PERMANOVA / RDA | termo, gl, SQ, pseudo-F, R², p |
| IndVal e TITAN2 | táxon, grupo, IndVal/limiar, A, B, p / pureza, confiabilidade |
| Limitações | limitação, efeito no resultado, como mitigar no monitoramento |

Tabelas digitadas como texto corrido (o auditor as detecta) devem virar tabelas do Word com título acima e fonte abaixo.

---

## 5. Estrutura recomendada (sem limite de páginas)

**Parte I — Contexto**
1. Apresentação: objetivo geral e específicos, vínculo com a CASAN e marco legal (CONAMA 357/2005, CONAMA 430/2011, Portaria GM/MS 888/2021, Lei 9.433/1997)
2. Área de estudo: localização (mapa), caracterização, pontos e trechos (mapa + tabela), captação
3. Material e métodos: 3.1 delineamento · 3.2 fitoplâncton · 3.3 variáveis ambientais · 3.4 uso do solo · 3.5 atributos funcionais · 3.6 análise estatística (subseções na mesma ordem dos resultados + tabela-resumo análise → pacote R → script)

**Parte II — Caracterização ambiental**
4. Físico-química (descrição, conformidade legal, PCA)
5. Uso e cobertura do solo (composição no buffer, PCA, gradiente longitudinal)

**Parte III — Comunidade fitoplanctônica**
6. Composição e densidade (grupos, dominantes)
7. Riqueza e diversidade alfa (descritores, rarefação, estimadores)
8. Modelos de densidade (total, diatomáceas, cianobactérias)

**Parte IV — Risco à captação e organização funcional**
9. Grupos de risco: cianobactérias, potencialmente tóxicos, flagelados (*Ceratium*), diatomáceas filamentosas (*Aulacoseira*, *Melosira*) e síntese espacial
10. Diversidade funcional (espaço funcional, índices, SES, CWM, PERMANOVA)
11. Diversidade beta (multi-sítio, par a par)
12. Limiares e bioindicadores (TITAN2, k-prototypes, IndVal, mapa de bioindicadores)

**Parte V — Síntese**
13. Síntese, limitações e recomendações (respostas às perguntas do edital, métricas para monitoramento contínuo, recomendações para a captação/ETA, próximas campanhas)

Referências · Apêndices (lista completa de táxons, saídas completas dos modelos, **tabela figura → script → arquivo de dados**, versões do R e dos pacotes via `sessionInfo()`)

### Regras de fluxo entre seções
- Cada capítulo de resultados abre com **uma frase-ponte** dizendo que pergunta ele responde e como se liga ao anterior.
- Defina cada métrica (CWM, SES, βSIM, IndVal) **nos Métodos** e relembre em meia frase quando aparecer nos Resultados.
- Interprete o tamanho de efeito para leigos: "o trecho explica 10,1% da variação da composição funcional (R² da PERMANOVA)".
- Voz impessoal e tempo passado nos Métodos e Resultados ("foram coletadas", "observou-se").

---

## 6. Checklist final de cada figura

- [ ] Citada no texto antes de aparecer
- [ ] Número único e sequencial, inserido com **Inserir Legenda**
- [ ] Diz o que é mostrado, onde e quando
- [ ] Traz o N amostral
- [ ] Traz unidade e escala (log?)
- [ ] Traz o teste/modelo com estatística e p, ou permutações/bootstraps
- [ ] Explica símbolos, cores, barras, letras e painéis (A, B...)
- [ ] Mapa: SRC, escala, norte, fonte da base
- [ ] Fonte e script de origem
- [ ] Gerada por script (reprodutível), não exportada à mão
