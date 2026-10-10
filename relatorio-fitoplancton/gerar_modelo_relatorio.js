// Gera o modelo Word do Relatório Ambiental do Fitoplâncton (LJS/CASAN).
// Uso: node gerar_modelo_relatorio.js [saida.docx]
// Estrutura em 5 partes / 13 capítulos, legendas com numeração automática
// (campos SEQ Figura / SEQ Tabela), sumário e listas atualizáveis no Word (F9).
"use strict";
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, TableOfContents,
  SequentialIdentifier, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, Footer, PageNumber, LevelFormat,
} = require("docx");

const saida = process.argv[2] || "Modelo_Relatorio_Fitoplancton.docx";
const FONTE = "Arial";
const LARG = 9071; // A4 com margens ABNT 3/2 cm: 11906 - 1701 - 1134 (DXA)

// ---------------------------------------------------------------------------
// blocos utilitários
// ---------------------------------------------------------------------------
const p = (texto, opt = {}) =>
  new Paragraph({ spacing: { after: 120, line: 360 }, alignment: AlignmentType.JUSTIFIED, ...opt,
    children: [].concat(texto).map((t) => (typeof t === "string" ? new TextRun(t) : t)) });
const instr = (texto) => // orientação para quem preenche (vermelho, itálico): apagar depois
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: `[${texto}]`, italics: true, color: "C00000" })] });
const h = (texto, nivel) => new Paragraph({ heading: nivel, children: [new TextRun(texto)] });
const quebra = () => new Paragraph({ children: [new PageBreak()] });

// Legenda ABNT: título acima ("Figura N – ..."), fonte abaixo.
function figura(legenda, script, resultado) {
  return [
    new Paragraph({ style: "Legenda", keepNext: true, children: [
      new TextRun({ text: "Figura ", bold: true }), new SequentialIdentifier("Figura"),
      new TextRun({ text: " – ", bold: true }), new TextRun(legenda)] }),
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" },
      spacing: { before: 120, after: 120, line: 1800 }, children: [
        new TextRun({ text: "INSERIR FIGURA", bold: true, color: "808080" }),
        new TextRun({ text: `  ·  script: ${script}${resultado ? "  ·  resultados: " + resultado : ""}`, color: "808080", size: 18 })] }),
    new Paragraph({ style: "Fonte", children: [new TextRun(`Fonte: elaborado pelos autores (2026), a partir de ${script}.`)] }),
  ];
}

function tabela(titulo, cabecalho, linhas, larguras) {
  const borda = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
  const sem = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const total = larguras.reduce((a, b) => a + b, 0);
  const mk = (vals, cab) => new TableRow({ tableHeader: cab, children: vals.map((v, i) => new TableCell({
    width: { size: larguras[i], type: WidthType.DXA },
    shading: cab ? { type: ShadingType.CLEAR, fill: "E7EEF5", color: "auto" } : undefined,
    borders: { top: cab ? borda : sem, left: sem, bottom: cab ? borda : sem, right: sem },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({ children: [new TextRun({ text: v, bold: cab, size: 18 })] })] })) });
  const ultima = linhas.length ? linhas : [cabecalho.map(() => "")];
  const rows = [mk(cabecalho, true), ...ultima.map((l) => mk(l, false))];
  return [
    new Paragraph({ style: "Legenda", keepNext: true, children: [
      new TextRun({ text: "Tabela ", bold: true }), new SequentialIdentifier("Tabela"),
      new TextRun({ text: " – ", bold: true }), new TextRun(titulo)] }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: larguras, rows,
      borders: { top: borda, left: sem, bottom: borda, right: sem, insideHorizontal: sem, insideVertical: sem } }),
    new Paragraph({ style: "Fonte", children: [new TextRun("Fonte: elaborado pelos autores (2026).")] }),
  ];
}

const W = (...fr) => { const s = fr.reduce((a, b) => a + b, 0); const r = fr.map((f) => Math.floor((LARG * f) / s)); r[r.length - 1] += LARG - r.reduce((a, b) => a + b, 0); return r; };
const TRECHOS = ["Montante", "Intermediário", "Jusante", "Reservatório"];

// ---------------------------------------------------------------------------
// conteúdo
// ---------------------------------------------------------------------------
const corpo = [];
const add = (...xs) => xs.flat().forEach((x) => corpo.push(x));

// Capa
add(
  new Paragraph({ spacing: { before: 2400 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "RELATÓRIO AMBIENTAL", bold: true, size: 36 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Comunidade fitoplanctônica da microbacia do Lajeado São José e riscos à captação de água para abastecimento de Chapecó (SC)", size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Campanhas de outubro/2022 (C1) e abril/2023 (C2)", size: 24 })] }),
  new Paragraph({ spacing: { before: 2400 }, alignment: AlignmentType.CENTER, children: [new TextRun("[Equipe técnica · Instituição · Contrato/edital CASAN nº ___]")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun("Chapecó, 2026")] }),
  quebra(),
  h("Sumário", HeadingLevel.TITLE),
  instr("Clique com o botão direito no sumário > Atualizar campo > Atualizar o índice inteiro. Faça o mesmo em Referências > Inserir Índice de Ilustrações para as listas de figuras e tabelas"),
  new TableOfContents("Sumário", { hyperlink: true, headingStyleRange: "1-3" }),
  quebra(),
  h("Como usar este modelo", HeadingLevel.TITLE),
  instr("Apague esta página antes de entregar"),
  p("Cada figura tem uma legenda-modelo acima (padrão ABNT), um quadro tracejado no lugar da imagem com o nome do script R que a gera e uma linha de Fonte abaixo. Substitua os colchetes pelos valores dos scripts e dos arquivos saidas/*.txt e cole a imagem no quadro. O auditor mapear_figuras.py (03_figuras_no_relatorio.csv) indica o script e a linha de cada figura."),
  p("A numeração de figuras e tabelas é automática (campos SEQ). Para citá-las no texto use Inserir > Referência Cruzada > Figura/Tabela; nunca digite o número. Depois de mover blocos, selecione tudo (Ctrl+A) e pressione F9."),
  p("Os nomes dos trechos são sempre Montante, Intermediário, Jusante e Reservatório, nessa ordem; as campanhas são C1 (outubro/2022) e C2 (abril/2023). Use vírgula decimal e unidades ind/mL, cél/mL, mg/L e µS/cm."),
  quebra(),
);

// PARTE I
add(h("PARTE I — CONTEXTO", HeadingLevel.TITLE));
add(h("1 Apresentação", HeadingLevel.HEADING_1),
  h("1.1 Identificação do estudo e da equipe", HeadingLevel.HEADING_2), instr("Contratante, executora, responsáveis técnicos e registro profissional"),
  h("1.2 Objetivos", HeadingLevel.HEADING_2), instr("Objetivo geral; objetivos específicos numerados, um para cada capítulo de resultados (6 a 12)"),
  h("1.3 Vínculo com a captação da CASAN", HeadingLevel.HEADING_2), instr("Perguntas do edital: risco de toxicidade (cianobactérias), risco de colmatação de filtros (Ceratium, diatomáceas filamentosas) e influência do uso do solo"),
  h("1.4 Marco legal", HeadingLevel.HEADING_2),
  p("Resolução CONAMA nº 357/2005 (classificação e enquadramento); Resolução CONAMA nº 430/2011 (efluentes); Portaria GM/MS nº 888/2021 (potabilidade e monitoramento de cianobactérias e cianotoxinas no manancial); Lei nº 9.433/1997 (Política Nacional de Recursos Hídricos)."),
  instr("Conferir na Portaria GM/MS 888/2021 vigente os limiares de cianobactérias (cél/mL) que disparam monitoramento semanal e análise de cianotoxinas antes de citá-los"),
);
add(h("2 Área de estudo", HeadingLevel.HEADING_1),
  h("2.1 Localização", HeadingLevel.HEADING_2),
  figura("Localização da microbacia do Lajeado São José (Chapecó e Cordilheira Alta, SC) no estado de Santa Catarina (A) e no município (B). Sistema de referência SIRGAS 2000 / UTM 22S. Base cartográfica: [IBGE, ANA/SDE-SC].", "fig01_M1_mapa_area_estudo.R ou QGIS"),
  h("2.2 Caracterização ambiental", HeadingLevel.HEADING_2), instr("Clima (Köppen), geologia e solos, vegetação, histórico do uso do solo"),
  h("2.3 Pontos amostrais e trechos", HeadingLevel.HEADING_2),
  figura("Distribuição dos 30 pontos amostrais nos quatro trechos do Lajeado São José (Montante, Intermediário, Jusante e Reservatório) sobre o uso e cobertura do solo (MapBiomas Coleção [x], [ano]). Escala gráfica e norte no mapa; SIRGAS 2000 / UTM 22S.", "fig01_mapas_M1_M2.R / plano guilherme\\mapas_espaciais_CORRIGIDO.py"),
  tabela("Pontos amostrais: código, trecho, coordenadas e altitude", ["Ponto", "Trecho", "Latitude", "Longitude", "Altitude (m)", "Distância da captação (km)"], [], W(1, 1.6, 1.4, 1.4, 1.1, 1.6)),
  h("2.4 Captação e sistema de tratamento", HeadingLevel.HEADING_2), instr("Localização da tomada d'água, vazão captada, tipo de tratamento da ETA"),
);
add(h("3 Material e métodos", HeadingLevel.HEADING_1),
  h("3.1 Delineamento amostral", HeadingLevel.HEADING_2),
  tabela("Cronograma das campanhas e condição hidrológica", ["Campanha", "Período", "Nº de pontos", "Precipitação acumulada 7 dias antes (mm)"], [["C1", "outubro/2022", "", ""], ["C2", "abril/2023", "", ""]], W(1, 1.5, 1.2, 2.5)),
  h("3.2 Coleta e análise do fitoplâncton", HeadingLevel.HEADING_2), instr("Volume coletado, fixação, câmara de Sedgwick-Rafter, critérios de contagem (SMWW 10200), laboratório responsável, unidade (ind/mL e cél/mL), biovolume"),
  h("3.3 Variáveis ambientais", HeadingLevel.HEADING_2),
  tabela("Variáveis físico-químicas: método analítico e limite de quantificação", ["Parâmetro", "Unidade", "Método", "Limite de quantificação", "Laboratório"], [["pH", "—", "", "", ""], ["Oxigênio dissolvido", "mg/L", "", "", ""], ["Condutividade elétrica", "µS/cm", "", "", ""], ["Turbidez", "NTU", "", "", ""], ["Nitrogênio amoniacal", "mg/L", "", "", ""], ["Fósforo total", "mg/L", "", "", ""]], W(2, 1, 2, 1.5, 1.5)),
  h("3.4 Uso e cobertura do solo", HeadingLevel.HEADING_2), instr("MapBiomas (coleção e ano), buffer (raio), classes agregadas, transformação dos dados composicionais"),
  h("3.5 Atributos funcionais", HeadingLevel.HEADING_2),
  tabela("Atributos funcionais e taxonômicos usados na diversidade funcional", ["Atributo", "Tipo", "Categorias / unidade", "Significado ecológico"], [["", "", "", ""]], W(1.5, 1, 2, 2.5)),
  h("3.6 Análise estatística", HeadingLevel.HEADING_2),
  instr("Uma subseção por grupo de análise, na mesma ordem dos capítulos de resultados. Defina aqui CWM, SES, βSIM/βSNE, IndVal e TITAN2"),
  tabela("Resumo das análises estatísticas, pacotes do R e scripts", ["Análise", "Pergunta", "Pacote R (versão)", "Parâmetros (permutações, semente)", "Script"], [["PCA", "", "stats / FactoMineR", "", "06_uso_solo.R"], ["PERMANOVA", "", "vegan::adonis2", "999 perm.; set.seed()", "09_CWM_PCoA_PERMANOVA.R"], ["Diversidade funcional", "", "FD::dbFD", "corr = \"cailliez\"", ""], ["Modelos nulos (SES)", "", "picante", "", "15_modelos_nulos_FD.R"], ["Beta", "", "betapart", "", ""], ["TITAN2", "", "TITAN2", "nBoot, numPerm", ""], ["IndVal", "", "indicspecies", "", ""], ["Modelos de contagem", "", "MASS / glmmTMB / pscl", "", ""]], W(1.6, 1.6, 1.5, 1.8, 1.9)),
  quebra(),
);

// PARTE II
add(h("PARTE II — CARACTERIZAÇÃO AMBIENTAL", HeadingLevel.TITLE));
add(h("4 Variáveis físico-químicas", HeadingLevel.HEADING_1),
  instr("Frase-ponte: o que este capítulo responde e por que vem antes da comunidade"),
  h("4.1 Caracterização geral", HeadingLevel.HEADING_2),
  tabela("Variáveis físico-químicas por trecho e campanha: mediana (mínimo–máximo)", ["Parâmetro", ...TRECHOS.map((t) => `${t} C1 / C2`)], [["", "", "", "", ""]], W(1.6, 1.6, 1.6, 1.6, 1.6)),
  h("4.2 Conformidade com a legislação", HeadingLevel.HEADING_2),
  tabela("Valores observados versus limites da Resolução CONAMA 357/2005 (classe [ ]) e da Portaria GM/MS 888/2021", ["Parâmetro", "Limite legal", "Norma", "Máximo observado (trecho, campanha)", "Nº de amostras acima do limite", "Situação"], [["Nitrogênio amoniacal", "", "CONAMA 357", "", "", ""], ["Fósforo total", "", "CONAMA 357", "", "", ""], ["Oxigênio dissolvido", "", "CONAMA 357", "", "", ""], ["Cianobactérias (cél/mL)", "", "GM/MS 888", "", "", ""]], W(1.6, 1.1, 1.1, 1.8, 1.4, 1)),
  h("4.3 Ordenação das variáveis físico-químicas", HeadingLevel.HEADING_2),
  figura("Biplot da Análise de Componentes Principais das variáveis físico-químicas [listar] padronizadas (média 0, DP 1). Pontos coloridos por trecho e símbolos por campanha; vetores = cargas. PC1 explica [x]% e PC2 [y]% da variância; N = [n] amostras.", "[script da PCA físico-química]", "resultados_PCAs.txt"),
  figura("Diagnóstico da PCA físico-química: (A) variância explicada por eixo (scree plot) e (B) contribuição (%) de cada variável para PC1 e PC2; a linha tracejada indica a contribuição esperada se todas fossem iguais.", "[mesmo script]"),
);
add(h("5 Uso e cobertura do solo", HeadingLevel.HEADING_1),
  h("5.1 Composição no entorno dos pontos", HeadingLevel.HEADING_2),
  tabela("Proporção (%) das classes de uso e cobertura do solo no buffer de [x] km por trecho", ["Classe", ...TRECHOS], [["Formação florestal", "", "", "", ""], ["Agricultura", "", "", "", ""], ["Pastagem", "", "", "", ""], ["Área urbanizada", "", "", "", ""], ["Silvicultura", "", "", "", ""]], W(2, 1, 1, 1, 1)),
  h("5.2 Ordenação do uso do solo", HeadingLevel.HEADING_2),
  p("A ordenação do uso do solo é separada da físico-química porque descreve a paisagem (dados composicionais, transformados por [clr/arco-seno]) e não a qualidade da água."),
  figura("Biplot da PCA da composição do uso do solo no buffer de [x] km ([transformação]) por ponto amostral, colorido por trecho; PC1 [x]%, PC2 [y]%; N = 30 pontos.", "06_uso_solo.R", "uso_solo_*.txt"),
  h("5.3 Gradiente longitudinal", HeadingLevel.HEADING_2), instr("Descrever a mudança Montante → Reservatório e conectar com o capítulo 6"),
  quebra(),
);

// PARTE III
add(h("PARTE III — COMUNIDADE FITOPLANCTÔNICA", HeadingLevel.TITLE));
add(h("6 Composição e densidade", HeadingLevel.HEADING_1),
  h("6.1 Composição taxonômica", HeadingLevel.HEADING_2),
  tabela("Táxons registrados, com ocorrência, densidade média e potencial de risco", ["Classe", "Táxon", "Frequência de ocorrência (%)", "Densidade média (ind/mL)", "Potencialmente tóxico", "Potencial colmatador"], [["", "", "", "", "", ""]], W(1.3, 2.2, 1.3, 1.3, 1.1, 1.1)),
  h("6.2 Densidade total", HeadingLevel.HEADING_2),
  figura("Densidade fitoplanctônica total (ind/mL, escala log₁₀) por trecho em C1 (outubro/2022) e C2 (abril/2023); N = [n] amostras ([n] por trecho e campanha). Caixa = intervalo interquartil; linha = mediana; hastes = 1,5 × IIQ; pontos = valores extremos. Letras diferentes indicam diferença significativa (Kruskal-Wallis, H = [ ], p = [ ]; pós-teste de Dunn com ajuste de [Holm]).", "[script]", "dados_por_amostra_AED.csv"),
  figura("Contribuição relativa (%) dos grupos taxonômicos para a densidade total (A) e para a riqueza (B) por trecho e campanha; proporções calculadas sobre a soma de cada trecho; [n] táxons no total.", "[script]"),
  h("6.3 Táxons dominantes", HeadingLevel.HEADING_2),
  figura("Densidade média (ind/mL, log₁₀(x+1)) dos 20 táxons mais abundantes por trecho e campanha. Táxons ordenados por [densidade total decrescente / agrupamento hierárquico]; escala de cor de [mín.] a [máx.].", "[script]"),
);
add(h("7 Riqueza e diversidade alfa", HeadingLevel.HEADING_1),
  figura("Riqueza de táxons (A), índice de Shannon-Wiener (B, ln) e equitabilidade de Pielou (C) por trecho e campanha; N = [n]. [Teste], p = [ ].", "[script]"),
  figura("Curvas de rarefação (linha contínua) e extrapolação (linha tracejada) da riqueza (q = 0) baseadas em [incidência/abundância] por trecho, com intervalo de confiança de 95% ([nboot] bootstraps). Os símbolos marcam a riqueza observada; cobertura amostral: [Montante x%, ...].", "[script iNEXT]"),
  tabela("Riqueza observada e estimada por trecho", ["Trecho", "S observado", "Chao2 ± EP", "Jackknife 1 ± EP", "Jackknife 2", "% do estimado amostrado"], TRECHOS.map((t) => [t, "", "", "", "", ""]), W(1.5, 1, 1.3, 1.3, 1.1, 1.4)),
);
add(h("8 Modelos de densidade", HeadingLevel.HEADING_1),
  instr("Informar nos Métodos: família e link, offset (volume analisado), diagnóstico de resíduos (DHARMa) e seleção por AIC"),
  figura("Densidade predita (± IC 95%) de fitoplâncton total (A), diatomáceas (B) e cianobactérias (C) por trecho e campanha. (A, B) [GLM binomial negativo / glmmTMB nbinom2 com dispersão variando por campanha]; (C) modelo hurdle (parte binária logit + contagem binomial negativa truncada). Pontos = observados; N = [n]; letras = contrastes de Tukey (emmeans) na escala da resposta.", "fig04_M1_glm_predictions.R / [script]", "GLM_*.txt"),
  tabela("Coeficientes dos modelos de densidade", ["Resposta", "Termo", "Estimativa", "EP", "z", "p"], [["", "", "", "", "", ""]], W(1.6, 1.8, 1.1, 0.9, 0.9, 0.9)),
  quebra(),
);

// PARTE IV
add(h("PARTE IV — RISCO À CAPTAÇÃO E ORGANIZAÇÃO FUNCIONAL", HeadingLevel.TITLE));
const mapa = (o, extra) => `Distribuição espacial da densidade de ${o} nos 30 pontos amostrais em C1 (A) e C2 (B). Tamanho do símbolo proporcional à densidade${extra || ""}. SIRGAS 2000 / UTM 22S; escala gráfica e norte no mapa; base: [ANA/SDE-SC].`;
add(h("9 Grupos de risco à captação", HeadingLevel.HEADING_1),
  h("9.1 Cianobactérias", HeadingLevel.HEADING_2),
  figura(mapa("cianobactérias (cél/mL)", "; cores = faixas da Portaria GM/MS 888/2021"), "[script de mapas]"),
  tabela("Densidade de cianobactérias versus limiares da Portaria GM/MS 888/2021", ["Trecho", "C1 (cél/mL)", "C2 (cél/mL)", "Faixa da Portaria", "Ação requerida"], TRECHOS.map((t) => [t, "", "", "", ""]), W(1.5, 1.2, 1.2, 1.5, 2.2)),
  h("9.2 Táxons potencialmente tóxicos", HeadingLevel.HEADING_2),
  figura(mapa("táxons potencialmente tóxicos ([listar gêneros]) (ind/mL)"), "[script de mapas]"),
  h("9.3 Flagelados (risco de colmatação)", HeadingLevel.HEADING_2),
  figura(mapa("flagelados, com destaque para Ceratium (ind/mL)"), "[script de mapas]"),
  h("9.4 Diatomáceas formadoras de cadeia", HeadingLevel.HEADING_2),
  figura(mapa("diatomáceas formadoras de cadeia (Aulacoseira, Melosira) (ind/mL)"), "[script de mapas]"),
  h("9.5 Síntese espacial", HeadingLevel.HEADING_2),
  figura("Painel-síntese dos grupos de risco por ponto e campanha: [média geométrica / soma] das densidades padronizadas; [critério de classes].", "[script]"),
);
add(h("10 Diversidade funcional", HeadingLevel.HEADING_1),
  h("10.1 Espaço funcional", HeadingLevel.HEADING_2),
  figura("Dendrograma funcional (UPGMA) da distância de Gower entre [n] táxons com base em [10] atributos ([listar]); correlação cofenética = [ ].", "09_CWM_PCoA_PERMANOVA.R"),
  figura("Espaço funcional (PCoA da distância de Gower com correção de Cailliez); polígonos = envoltória convexa de cada trecho; PCoA1 [x]%, PCoA2 [y]%. PERMANOVA: pseudo-F = [ ], R² = [ ], p = [ ] ([999] permutações).", "09_CWM_PCoA_PERMANOVA.R", "PERMANOVA_CWM.txt"),
  h("10.2 Índices de diversidade funcional", HeadingLevel.HEADING_2),
  figura("Riqueza (FRic), equitabilidade (FEve), divergência (FDiv), dispersão funcional (FDis) e entropia de Rao (RaoQ) por trecho (FD::dbFD, corr = \"cailliez\"); N de amostras com índice calculável: FRic = [n], demais = [n]. [Teste], p = [ ].", "[script]", "diversidade_funcional.txt"),
  figura("Índices de diversidade funcional por campanha (C1 × C2); N = [n] por campanha; teste de Wilcoxon, p = [ ].", "[script]"),
  h("10.3 Modelos nulos", HeadingLevel.HEADING_2),
  figura("Tamanho de efeito padronizado (SES = [obs − média nula]/DP nula) de RaoQ e FDis por trecho, com [999] aleatorizações ([algoritmo]); linhas tracejadas em ±1,96.", "15_modelos_nulos_FD.R", "SES_diversidade_funcional.txt"),
  h("10.4 Composição funcional ponderada (CWM)", HeadingLevel.HEADING_2),
  figura("Média ponderada pela comunidade (CWM, densidade relativa) dos atributos [listar] por trecho; PERMANOVA sobre a CWM transformada por Hellinger: R² = [ ], p = [ ] ([999] permutações).", "fig07_M2_CWM_profiles.R", "CWM_medias_regiao.txt"),
);
add(h("11 Diversidade beta", HeadingLevel.HEADING_1),
  figura("Partição da diversidade beta multi-sítio (Sørensen; Baselga, 2010) em substituição (βSIM) e aninhamento (βSNE), taxonômica (A) e funcional (B), por campanha.", "[script betapart]", "beta_*.txt"),
  figura("Relação par a par entre βSIM e βSNE para pares de pontos dentro do mesmo trecho e entre trechos diferentes.", "[script betapart]", "beta_taxonomica_pares.txt"),
);
add(h("12 Limiares ecológicos e bioindicadores", HeadingLevel.HEADING_1),
  h("12.1 TITAN2", HeadingLevel.HEADING_2),
  figura("Limiares de mudança de táxons ao longo do gradiente de [variável] (TITAN2; [500] bootstraps, [250] permutações). Apenas táxons com pureza e confiabilidade ≥ 0,95; z− (decrescentes) em azul, z+ (crescentes) em vermelho; linhas = IC 5–95%.", "[script TITAN2]", "TITAN_limiares_por_taxon.csv"),
  tabela("Táxons com limiar robusto (TITAN2)", ["Táxon", "Grupo (z− / z+)", "Limiar", "IC 5–95%", "Pureza", "Confiabilidade"], [["", "", "", "", "", ""]], W(2, 1.2, 1, 1.4, 1, 1.2)),
  h("12.2 Grupos funcionais (k-prototypes)", HeadingLevel.HEADING_2),
  figura("Grupos de táxons definidos por k-prototypes (k = 6, escolhido por [silhueta/elbow]; λ = [ ]): (A) diagrama de Sankey entre grupos e trechos; (B) distribuição dos atributos quantitativos por grupo.", "[script k-prototypes]", "grupos_TT_K_prototypes.csv"),
  h("12.3 Espécies indicadoras", HeadingLevel.HEADING_2),
  figura("Táxons indicadores (IndVal.g, indicspecies::multipatt) dos trechos e das combinações trecho × campanha; barras = IndVal; apenas p < 0,05 após [999] permutações.", "[script IndVal]", "especies_indicadoras.txt"),
  tabela("Táxons indicadores por trecho", ["Táxon", "Grupo", "A (especificidade)", "B (fidelidade)", "IndVal", "p"], [["", "", "", "", "", ""]], W(2.2, 1.4, 1.2, 1.2, 1, 0.8)),
  h("12.4 Distribuição dos bioindicadores", HeadingLevel.HEADING_2),
  figura(mapa("bioindicadores ([listar os 6 táxons somados]) (ind/mL)"), "[script de mapas]"),
  quebra(),
);

// PARTE V
add(h("PARTE V — SÍNTESE", HeadingLevel.TITLE));
add(h("13 Síntese, limitações e recomendações", HeadingLevel.HEADING_1),
  h("13.1 Respostas às perguntas do edital", HeadingLevel.HEADING_2), instr("Toxicidade, colmatação e uso do solo: uma resposta direta para cada pergunta, com a figura ou tabela que a sustenta"),
  h("13.2 Limitações", HeadingLevel.HEADING_2),
  tabela("Limitações do estudo, efeito sobre os resultados e mitigação", ["Limitação", "Efeito no resultado", "Como mitigar no monitoramento"], [["Duas campanhas apenas", "", ""], ["Fração espacial (AEM) não incluída na partição de variância", "Variância não explicada atribuída a transporte passivo é interpretação, não medida", "Rodar AEM/dbMEM com coordenadas e rede de drenagem"], ["", "", ""]], W(2, 2.5, 2.5)),
  h("13.3 Métricas para monitoramento contínuo", HeadingLevel.HEADING_2),
  h("13.4 Recomendações operacionais para a captação e a ETA", HeadingLevel.HEADING_2),
  h("13.5 Prioridades para campanhas futuras", HeadingLevel.HEADING_2),
  quebra(),
  h("Referências", HeadingLevel.HEADING_1),
  instr("ABNT NBR 6023:2018; citações autor-data NBR 10520:2023. Cada citação do texto precisa estar aqui e vice-versa — confira com a seção 7 do diagnóstico"),
  h("Apêndice A — Rastreabilidade figura → script → dados", HeadingLevel.HEADING_1),
  tabela("Rastreabilidade das figuras e tabelas", ["Figura/Tabela", "Script (linha)", "Arquivo de dados de entrada", "Arquivo de resultado"], [["", "", "", ""]], W(1.3, 2.2, 2.2, 2.2)),
  h("Apêndice B — Ambiente computacional", HeadingLevel.HEADING_1),
  instr("Colar a saída de sessionInfo() do R (versão do R e dos pacotes)"),
);

// ---------------------------------------------------------------------------
const doc = new Document({
  creator: "", title: "Relatório Ambiental — Fitoplâncton LJS",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONTE, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { size: 30, bold: true, color: "1F3864", font: FONTE }, paragraph: { spacing: { before: 240, after: 240 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONTE }, paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, font: FONTE }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Legenda", name: "Legenda", basedOn: "Normal", next: "Normal", run: { size: 20, font: FONTE }, paragraph: { spacing: { before: 240, after: 60 }, alignment: AlignmentType.JUSTIFIED } },
      { id: "Fonte", name: "Fonte", basedOn: "Normal", next: "Normal", run: { size: 18, font: FONTE }, paragraph: { spacing: { before: 60, after: 240 } } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1701, bottom: 1134, left: 1701, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT] })] })] }) },
    children: corpo,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(saida, buf); console.log("Gerado:", saida); });
