#!/usr/bin/env python3
"""
mapear_figuras.py - Auditoria do Relatório Ambiental do Fitoplâncton (LJS/CASAN)

O que faz (somente leitura; nada na pasta é alterado):
  1. Varre todos os scripts (.R, .Rmd, .qmd, .py) da pasta e subpastas e registra,
     para cada um: pacotes, dados de entrada, arquivos gerados (figuras/tabelas),
     análises estatísticas detectadas, tipo de gráfico e parâmetros (set.seed,
     permutações, bootstraps).
  2. Lista todas as imagens da pasta e liga cada uma ao script que a gera.
  3. Abre o relatório .docx e, para cada imagem inserida no Word, descobre:
     - se tem legenda ("Figura N ...") e se a numeração é contínua/sem duplicatas;
     - qual arquivo de imagem da pasta ela é (comparação byte a byte e por
       dimensões em pixels) e, portanto, qual script a gerou;
     - o que falta na legenda (N amostral, teste, unidade, permutações...),
       com um esqueleto de legenda preenchido com os parâmetros achados no script.
  4. Audita a estrutura: numeração de seções, títulos com texto corrido,
     parágrafos duplicados, tabelas sem título, figuras citadas sem legenda,
     citações sem referência e referências não citadas, marcadores pendentes.

Uso (Windows, no Prompt de Comando ou PowerShell):
  python mapear_figuras.py "E:\\Fitoplancton\\Relatório completo Fitoplancton"
  python mapear_figuras.py "E:\\Fitoplancton\\Relatório completo Fitoplancton" --relatorio "E:\\...\\Relatorio.docx"

Saída (pasta _auditoria_relatorio dentro da pasta analisada, ou --saida):
  01_inventario_scripts.csv
  02_inventario_imagens.csv
  03_figuras_no_relatorio.csv
  04_diagnostico_relatorio.md   <- comece por aqui

Requer apenas Python 3.8+ (biblioteca padrão).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import hashlib
import os
import re
import struct
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_EXT = {".r", ".rmd", ".qmd", ".py"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".bmp", ".emf", ".wmf", ".pdf"}
TABLE_EXT = {".csv", ".txt", ".xlsx", ".xls", ".docx", ".rds", ".rdata", ".html", ".tsv"}
SKIP_DIRS = {".git", "_auditoria_relatorio", "renv", ".Rproj.user", "__pycache__", "node_modules"}

# ---------------------------------------------------------------------------
# Catálogo de análises: regex -> (nome da análise, pacote, o que a legenda/método
# precisa informar para ser reprodutível e cientificamente completa).
# ---------------------------------------------------------------------------
ANALISES = [
    (
        r"\bprcomp\s*\(|\bprincomp\s*\(|\bPCA\s*\(|\bdudi\.pca\s*\(",
        "PCA",
        "stats/FactoMineR/ade4",
        "variáveis incluídas e transformação (padronização/log); % de variância explicada nos eixos; critério de retenção dos eixos; vetores com maior carga; N de amostras",
    ),
    (
        r"\badonis2?\s*\(",
        "PERMANOVA",
        "vegan",
        "medida de distância; transformação; N de permutações; estratos (strata) se houver; pseudo-F, R² e p; termos do modelo",
    ),
    (
        r"\bbetadisper\s*\(",
        "PERMDISP (homogeneidade de dispersão)",
        "vegan",
        "distância; N de permutações; F e p (para interpretar a PERMANOVA)",
    ),
    (
        r"\bmetaMDS\s*\(",
        "NMDS",
        "vegan",
        "distância; k dimensões; stress final; N de inícios aleatórios",
    ),
    (
        r"\b(dbrda|capscale)\s*\(",
        "db-RDA",
        "vegan",
        "distância; variáveis explicativas; R² ajustado; teste por permutação (N); VIF",
    ),
    (
        r"\brda\s*\(",
        "RDA (ou PCA via rda)",
        "vegan",
        "se RDA: variáveis explicativas, transformação da resposta (ex.: Hellinger), R² ajustado, anova.cca com N permutações, VIF; se sem preditores é uma PCA",
    ),
    (
        r"\bcca\s*\(",
        "CCA",
        "vegan",
        "variáveis explicativas; inércia explicada; teste por permutação (N)",
    ),
    (
        r"\bvarpart\s*\(",
        "Partição de variância",
        "vegan",
        "frações [a], [b], [c], [d] com R² ajustado; conjuntos de variáveis",
    ),
    (
        r"\bvegdist\s*\(",
        "Matriz de dissimilaridade",
        "vegan",
        "índice (Bray-Curtis, Jaccard, Euclidiana...) e transformação prévia",
    ),
    (
        r"\bdecostand\s*\(",
        "Transformação de dados",
        "vegan",
        "método (hellinger, total, standardize, log...)",
    ),
    (
        r"\bgowdis\s*\(|daisy\s*\([^)]*gower",
        "Distância de Gower (atributos)",
        "FD/cluster",
        "atributos e tipos (quantitativo, categórico, ordinal); pesos",
    ),
    (
        r"\bhclust\s*\(",
        "Agrupamento hierárquico",
        "stats",
        "método de ligação (average = UPGMA); distância; correlação cofenética",
    ),
    (r"\bcophenetic\s*\(", "Correlação cofenética", "stats", "valor da correlação cofenética"),
    (
        r"\b(pcoa|cmdscale|wcmdscale)\s*\(",
        "PCoA",
        "ape/stats/vegan",
        "distância; correção de autovalores negativos (Cailliez/Lingoes); % explicada nos eixos",
    ),
    (
        r"\bdbFD\s*\(",
        "Diversidade funcional (FRic, FEve, FDiv, FDis, RaoQ)",
        "FD",
        "atributos usados; correção (corr=); m (eixos PCoA); N de amostras com índice calculável (FRic exige nº espécies > nº atributos)",
    ),
    (
        r"\bfunctcomp\s*\(|\bcwm\b|CWM",
        "CWM (média ponderada pela comunidade)",
        "FD",
        "atributos; ponderação (densidade/abundância relativa); categoria para atributos categóricos",
    ),
    (
        r"\bmelodic\s*\(|\brao\s*\(|RaoQ",
        "Entropia quadrática de Rao",
        "FD/custom",
        "distância funcional; ponderação",
    ),
    (
        r"\b(randomizeMatrix|permatswap|permatfull|nullmodel|oecosimu|ses\.\w+)\s*\(|\bSES\b",
        "Modelo nulo / SES",
        "picante/vegan",
        "algoritmo de aleatorização (ex.: independentswap, richness); N de iterações; fórmula do SES e interpretação (|SES|>1,96)",
    ),
    (
        r"\bbeta\.multi(\.abund)?\s*\(",
        "Diversidade beta multi-sítio",
        "betapart",
        "família (Sørensen/Jaccard, Baselga 2010); componentes βSOR, βSIM, βSNE; dado de presença/ausência ou abundância",
    ),
    (
        r"\bbeta\.pair(\.abund)?\s*\(",
        "Diversidade beta par a par",
        "betapart",
        "família; definição de pares dentro/entre trechos",
    ),
    (
        r"\bfunctional\.beta\.(multi|pair)\s*\(",
        "Diversidade beta funcional",
        "betapart",
        "eixos do espaço funcional usados; família",
    ),
    (
        r"\btitan\s*\(",
        "TITAN2 (limiares de táxons)",
        "TITAN2",
        "gradiente; nBoot; numPerm; critérios de pureza e confiabilidade (≥0,95); minSplt; nº mínimo de ocorrências por táxon",
    ),
    (
        r"\bkproto\s*\(|\bk_?prototypes?\b",
        "k-prototypes",
        "clustMixType",
        "variáveis; critério para escolher k (ex.: silhueta, elbow); lambda; semente",
    ),
    (
        r"\bkmeans\s*\(",
        "k-means",
        "stats",
        "variáveis padronizadas; critério de k; nstart; semente",
    ),
    (
        r"\b(multipatt|indval|strassoc)\s*\(",
        "Espécies indicadoras (IndVal)",
        "indicspecies/labdsv",
        "func (IndVal.g / r.g); grupos e combinações; N de permutações; correção para múltiplos testes; componentes A e B",
    ),
    (
        r"\biNEXT\s*\(|\bestimateD\s*\(",
        "Rarefação/extrapolação (iNEXT)",
        "iNEXT",
        "datatype (incidence_freq/abundance); q (0,1,2); endpoint; nboot; IC 95%; cobertura amostral",
    ),
    (
        r"\b(specpool|poolaccum|estimateR|estaccumR|specaccum|rarecurve|rarefy)\s*\(",
        "Estimadores de riqueza / rarefação",
        "vegan",
        "estimador (Chao2, Jackknife 1/2, ACE); N de permutações; unidade amostral",
    ),
    (
        r"\bglm\.nb\s*\(",
        "GLM binomial negativa",
        "MASS",
        "família e link; preditores; offset; teste de sobredispersão; diagnóstico de resíduos (DHARMa)",
    ),
    (
        r"\bglmmTMB\s*\(",
        "Modelo glmmTMB",
        "glmmTMB",
        "família (nbinom1/nbinom2, truncada); dispformula; ziformula; efeitos aleatórios; diagnóstico de resíduos",
    ),
    (
        r"\b(hurdle|zeroinfl)\s*\(",
        "Modelo hurdle / inflado de zeros",
        "pscl",
        "parte binária e parte de contagem; distribuição; preditores",
    ),
    (
        r"\b(glmer|lmer|lme|glmmPQL)\s*\(",
        "Modelo misto",
        "lme4/nlme",
        "efeitos fixos e aleatórios; família; diagnóstico",
    ),
    (r"\bgam\s*\(", "GAM", "mgcv", "suavizadores; k; família; edf; R² ajustado"),
    (r"\bglm\s*\(", "GLM", "stats", "família e link; preditores; deviance explicada"),
    (
        r"\blm\s*\(",
        "Regressão linear",
        "stats",
        "preditores; R²; pressupostos (normalidade, homocedasticidade)",
    ),
    (
        r"\b(emmeans|glht|TukeyHSD|pairs)\s*\(",
        "Comparações múltiplas / pós-teste",
        "emmeans/multcomp",
        "método de ajuste (Tukey, Holm, BH); escala (link/resposta); letras de significância",
    ),
    (r"\bkruskal\.test\s*\(", "Kruskal-Wallis", "stats", "H (χ²), gl, p; N por grupo"),
    (
        r"\b(dunn\.test|dunnTest|kwAllPairsDunnTest)\s*\(",
        "Pós-teste de Dunn",
        "dunn.test/FSA/PMCMRplus",
        "ajuste de p (Bonferroni/Holm/BH)",
    ),
    (
        r"\bwilcox\.test\s*\(|pairwise\.wilcox\.test\s*\(",
        "Wilcoxon / Mann-Whitney",
        "stats",
        "W ou V, p; pareado ou não; ajuste para múltiplos testes",
    ),
    (r"\b(aov|Anova)\s*\(", "ANOVA", "stats/car", "F, gl, p; pressupostos"),
    (r"\bt\.test\s*\(", "Teste t", "stats", "t, gl, p"),
    (
        r"\bcor\.test\s*\(|\bcor\s*\(|rcorr\s*\(",
        "Correlação",
        "stats/Hmisc",
        "método (Pearson/Spearman); r/ρ; p; N",
    ),
    (
        r"\bshapiro\.test\s*\(|\bleveneTest\s*\(",
        "Teste de pressupostos",
        "stats/car",
        "resultado do teste de normalidade/homocedasticidade",
    ),
    (
        r"\bmantel\s*\(|mantel\.partial\s*\(",
        "Teste de Mantel",
        "vegan",
        "matrizes comparadas; método; N permutações",
    ),
    (
        r"\bdiversity\s*\(|\bspecnumber\s*\(|\bshannon\b",
        "Diversidade alfa (riqueza, Shannon, Simpson)",
        "vegan",
        "índice e base do logaritmo; equitabilidade de Pielou",
    ),
    (
        r"\bsimulateResiduals\s*\(",
        "Diagnóstico de resíduos (DHARMa)",
        "DHARMa",
        "testes de uniformidade, dispersão e outliers",
    ),
    (
        r"\b(AIC|BIC|AICc|dredge|model\.sel)\s*\(",
        "Seleção de modelos",
        "stats/MuMIn",
        "critério e ΔAIC",
    ),
    (
        r"\bvif\s*\(|vif\.cca\s*\(",
        "VIF (colinearidade)",
        "car/vegan",
        "limiar de exclusão (ex.: VIF > 10)",
    ),
]

GRAFICOS = [
    (r"geom_boxplot|boxplot\s*\(", "boxplot"),
    (r"geom_violin", "violino"),
    (r"geom_(point|jitter)", "dispersão/pontos"),
    (r"geom_(bar|col)\b|barplot\s*\(", "barras"),
    (r"position\s*=\s*[\"']fill|position_fill", "barras empilhadas (proporção)"),
    (
        r"geom_tile|geom_raster|pheatmap\s*\(|heatmap\s*\(|ComplexHeatmap|corrplot\s*\(",
        "heatmap/matriz",
    ),
    (
        r"geom_sf|\btmap\b|tm_shape|leaflet\s*\(|ggspatial|annotation_scale|annotation_north_arrow|st_read\s*\(",
        "mapa",
    ),
    (r"ggalluvial|geom_alluvium|geom_sankey|ggsankey|sankeyNetwork", "Sankey/aluvial"),
    (
        r"fviz_pca|fviz_pca_biplot|autoplot\s*\(|biplot\s*\(|ordiplot|ordiellipse|ordihull|geom_segment\([^)]*arrow",
        "biplot/ordenação",
    ),
    (r"stat_ellipse|ordiellipse|chull\s*\(|geom_polygon", "envoltórias/elipses"),
    (r"ggdendro|dendextend|plot\s*\(\s*\w*(hc|hclust|dend)\w*|as\.dendrogram", "dendrograma"),
    (r"geom_line|geom_smooth|lines\s*\(", "linhas/curvas"),
    (r"ggiNEXT|plot\.iNEXT", "curva de rarefação iNEXT"),
    (r"geom_errorbar|geom_pointrange|geom_linerange", "barras de erro/IC"),
    (r"geom_histogram|hist\s*\(|geom_density", "histograma/densidade"),
    (r"facet_(wrap|grid)", "painéis (facetas)"),
    (r"plot_titan|plotSumz|plotTaxa", "gráfico TITAN2"),
    (r"patchwork|plot_grid|ggarrange|grid\.arrange", "figura composta (painéis A, B, C...)"),
]

PARAMS = [
    (r"set\.seed\s*\(\s*(\d+)", "set.seed"),
    (r"permutations\s*=\s*([\w\.]+)", "permutations"),
    (r"\bnperm\s*=\s*([\w\.]+)", "nperm"),
    (r"\bnBoot\s*=\s*([\w\.]+)", "nBoot"),
    (r"\bnboot\s*=\s*([\w\.]+)", "nboot"),
    (r"\bnumPerm\s*=\s*([\w\.]+)", "numPerm"),
    (r"\bminSplt\s*=\s*([\w\.]+)", "minSplt"),
    (r"\b(?:runs|iterations|nsim|nrep|n_?iter|reps)\s*=\s*([\w\.]+)", "iterações"),
    (r"\bmethod\s*=\s*[\"']([\w\.\-]+)[\"']", "method"),
    (r"\bfamily\s*=\s*([\w\.]+(?:\([^)]*\))?)", "family"),
    (r"\bcorr\s*=\s*[\"'](\w+)[\"']", "corr (dbFD)"),
    (r"\bdatatype\s*=\s*[\"'](\w+)[\"']", "datatype (iNEXT)"),
    (r"\bfunc\s*=\s*[\"']([\w\.]+)[\"']", "func (IndVal)"),
    (r"\bdistance\s*=\s*[\"'](\w+)[\"']", "distance"),
    (r"\bindex\.family\s*=\s*[\"'](\w+)[\"']", "index.family (betapart)"),
    (r"\bk\s*=\s*(\d+)", "k"),
    (r"\bconf\s*=\s*([\d\.]+)", "conf (IC)"),
    (
        r"\bp\.adjust(?:\.method(?:s)?)?\s*=\s*[\"'](\w+)[\"']|\badjust\s*=\s*[\"'](\w+)[\"']",
        "ajuste de p",
    ),
]

OUT_CALLS_R = r"\b(ggsave|png|jpeg|jpg|tiff|bmp|pdf|svg|cairo_pdf|CairoPNG|agg_png|svglite|tiff|write\.csv2?|write\.table|write_csv2?|write_tsv|write\.xlsx|write_xlsx|fwrite|saveRDS|save|sink|capture\.output|writeLines|save_as_docx|save_as_image|htmlwidgets::saveWidget|saveWidget|tmap_save|save_kable|kable_save|ggexport|export)\s*\("
OUT_CALLS_PY = r"\b(savefig|to_csv|to_excel|write_image|write_html|save)\s*\("
IN_CALLS = r"\b(read\.csv2?|read\.table|read\.delim|read_csv2?|read_tsv|read_excel|read_xlsx|read\.xlsx|readxl::read_excel|fread|readRDS|load|st_read|read_sf|raster|rast|pd\.read_csv|pd\.read_excel|read_csv|read_excel)\s*\("
FILE_LIT = re.compile(
    r"[\"']([^\"'\n]{1,240}?\.(?:png|jpe?g|tiff?|svg|bmp|pdf|emf|wmf|csv|txt|tsv|xlsx|xls|docx|rds|rdata|html|shp|gpkg|tif))[\"']",
    re.I,
)
STR_LIT = re.compile(r"[\"']([^\"'\n]{1,240})[\"']")


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def ler_texto(p: Path) -> str:
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def stem_norm(name: str) -> str:
    return norm(Path(name.replace("\\", "/")).stem)


def sem_comentario(linha: str, py: bool) -> str:
    """Remove comentário de linha (# ...) respeitando strings simples."""
    out, q = [], None
    for ch in linha:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def trecho_chamada(texto: str, inicio_paren: int, limite: int = 2000) -> str:
    """Retorna o conteúdo entre parênteses balanceados a partir de '('."""
    nivel, q, i = 0, None, inicio_paren
    fim = min(len(texto), inicio_paren + limite)
    while i < fim:
        ch = texto[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
            if nivel == 0:
                return texto[inicio_paren + 1 : i]
        i += 1
    return texto[inicio_paren + 1 : fim]


def linha_de(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def sha1(p: Path) -> str:
    h = hashlib.sha1(usedforsecurity=False)
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def dimensoes(dados: bytes):
    """(largura, altura) para PNG/JPEG/GIF/BMP; None caso contrário."""
    try:
        if dados[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", dados[16:24])
        if dados[:2] == b"\xff\xd8":
            i = 2
            while i < len(dados) - 9:
                if dados[i] != 0xFF:
                    i += 1
                    continue
                marca = dados[i + 1]
                if marca in (
                    0xC0,
                    0xC1,
                    0xC2,
                    0xC3,
                    0xC5,
                    0xC6,
                    0xC7,
                    0xC9,
                    0xCA,
                    0xCB,
                    0xCD,
                    0xCE,
                    0xCF,
                ):
                    h, w = struct.unpack(">HH", dados[i + 5 : i + 9])
                    return (w, h)
                seg = struct.unpack(">H", dados[i + 2 : i + 4])[0]
                i += 2 + seg
        if dados[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", dados[6:10])
        if dados[:2] == b"BM":
            w, h = struct.unpack("<ii", dados[18:26])
            return (w, abs(h))
    except struct.error:
        return None
    return None


def iter_arquivos(raiz: Path):
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith("~")]
        for fn in filenames:
            if fn.startswith("~$"):
                continue
            yield Path(dirpath) / fn


def rel(p: Path, raiz: Path) -> str:
    try:
        return str(p.relative_to(raiz))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# 1. scripts
# ---------------------------------------------------------------------------
def analisar_script(p: Path, raiz: Path) -> dict:
    texto_bruto = ler_texto(p)
    py = p.suffix.lower() == ".py"
    linhas = texto_bruto.splitlines()
    texto = "\n".join(sem_comentario(l, py) for l in linhas)

    pacotes = sorted(
        set(
            re.findall(
                r"\b(?:library|require|requireNamespace|p_load)\s*\(\s*[\"']?([\w\.]+)", texto
            )
        )
        | set(re.findall(r"\b([A-Za-z][\w\.]+)::", texto))
        | (set(re.findall(r"^\s*(?:import|from)\s+([\w\.]+)", texto, re.M)) if py else set())
    )

    saidas = []
    for m in re.finditer(OUT_CALLS_PY if py else OUT_CALLS_R, texto):
        dentro = trecho_chamada(texto, m.end() - 1)
        arqs = FILE_LIT.findall(dentro)
        literais = STR_LIT.findall(dentro)
        dinamico = bool(
            re.search(r"paste0?\s*\(|file\.path\s*\(|sprintf\s*\(|glue\s*\(|f[\"']", dentro)
        )
        if not arqs and not literais and m.group(1) in ("save", "export", "pairs"):
            continue
        saidas.append(
            {
                "funcao": m.group(1),
                "linha": linha_de(texto, m.start()),
                "arquivos": arqs,
                "pedacos": [l for l in literais if l not in arqs],
                "dinamico": dinamico,
                "trecho": re.sub(r"\s+", " ", dentro)[:160],
            }
        )
    # nomes de figura atribuídos a variáveis (ex.: arq <- "Fig3.png"; ggsave(arq))
    literais_fig = sorted(
        {
            m.group(1)
            for m in FILE_LIT.finditer(texto)
            if Path(m.group(1)).suffix.lower() in IMAGE_EXT
        }
    )
    for o in saidas:
        if o["dinamico"] and not o["arquivos"]:
            ext = next(
                (
                    x
                    for x in o["pedacos"]
                    if re.fullmatch(r"\.(png|jpe?g|tiff?|svg|pdf|bmp)", x, re.I)
                ),
                "",
            )
            fixos = [x for x in o["pedacos"] if x != ext]
            if ext and fixos:
                literais_fig.append("*".join(fixos) + "*" + ext)

    entradas = []
    for m in re.finditer(IN_CALLS, texto):
        dentro = trecho_chamada(texto, m.end() - 1)
        arqs = FILE_LIT.findall(dentro) or STR_LIT.findall(dentro)[:1]
        if arqs:
            entradas.append(arqs[0])
    entradas = sorted(set(entradas))

    analises = []
    for rx, nome, pacote, exige in ANALISES:
        linhas_hit = [linha_de(texto, m.start()) for m in re.finditer(rx, texto)]
        if linhas_hit:
            analises.append(
                {"analise": nome, "pacote": pacote, "linhas": linhas_hit[:8], "exige": exige}
            )
    # "rda" sem preditores e PCA se sobrepõem; "glm" casa com glm.nb: limpe redundâncias
    nomes = {a["analise"] for a in analises}
    if "GLM binomial negativa" in nomes:
        analises = [
            a
            for a in analises
            if not (
                a["analise"] == "GLM"
                and set(a["linhas"])
                <= set(
                    next(b["linhas"] for b in analises if b["analise"] == "GLM binomial negativa")
                )
            )
        ]

    graficos = sorted({nome for rx, nome in GRAFICOS if re.search(rx, texto)})

    params = defaultdict(set)
    for rx, nome in PARAMS:
        for m in re.finditer(rx, texto):
            val = next((g for g in m.groups() if g), None)
            if val:
                params[nome].add(val)

    titulos = re.findall(
        r"\b(?:labs|ggtitle|title|xlab|ylab|main)\s*\(\s*(?:title\s*=\s*)?[\"']([^\"']{3,120})[\"']",
        texto,
    )
    titulos += re.findall(
        r"\b(?:title|x|y|fill|colour|color|caption|subtitle)\s*=\s*[\"']([^\"']{3,120})[\"']", texto
    )

    st = p.stat()
    return {
        "caminho": rel(p, raiz),
        "nome": p.name,
        "linhas": len(linhas),
        "modificado": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "pacotes": pacotes,
        "entradas": entradas,
        "saidas": saidas,
        "literais_fig": literais_fig,
        "analises": analises,
        "graficos": graficos,
        "params": {k: sorted(v) for k, v in params.items()},
        "rotulos": sorted(set(titulos))[:30],
    }


# ---------------------------------------------------------------------------
# 2. imagens -> scripts
# ---------------------------------------------------------------------------
def ligar_imagens(imagens: list[Path], scripts: list[dict], raiz: Path) -> list[dict]:
    idx_exato = defaultdict(list)  # stem normalizado -> [(script, linha, funcao)]
    idx_pedacos = []  # (pedaços, script, linha, funcao)
    for s in scripts:
        for o in s["saidas"]:
            for a in o["arquivos"]:
                idx_exato[stem_norm(a)].append((s, o["linha"], o["funcao"]))
            if o["dinamico"] or not o["arquivos"]:
                peds = []
                for x in o["pedacos"] + o["arquivos"]:
                    x = norm(x.replace("\\", "/"))
                    if re.fullmatch(r"\.?[a-z]{2,4}", x):  # só a extensão (".png")
                        continue
                    x = x.rsplit("/", 1)[-1]  # só o nome, sem a pasta
                    x = re.sub(r"\.(png|jpe?g|tiff?|svg|pdf|bmp)$", "", x).strip("_-. ")
                    if len(x) >= 3:
                        peds.append(x)
                if peds:
                    idx_pedacos.append((peds, s, o["linha"], o["funcao"]))
        for a in [x for x in s["literais_fig"] if "*" not in x]:
            if not idx_exato.get(stem_norm(a)) or all(
                x[0] is not s for x in idx_exato[stem_norm(a)]
            ):
                idx_exato[stem_norm(a)].append((s, None, "nome atribuído a variável"))

    linhas = []
    for img in imagens:
        alvo = stem_norm(img.name)
        cand = list(idx_exato.get(alvo, []))
        confianca = "alta (nome idêntico no script)" if cand else ""
        if not cand:
            for peds, s, ln, fn in idx_pedacos:
                fixos = [p for p in peds if not re.fullmatch(r"[\w]{1,2}", p)]
                if fixos and all(p in alvo for p in fixos):
                    cand.append((s, ln, fn))
            if cand:
                confianca = "média (nome montado com paste0/file.path)"
        if not cand:
            # semelhança de nome como último recurso
            melhores = []
            for chave, lst in idx_exato.items():
                r = difflib.SequenceMatcher(None, alvo, chave).ratio()
                if r >= 0.8:
                    melhores.extend((s, ln, fn) for s, ln, fn in lst)
            if melhores:
                cand = melhores
                confianca = "baixa (nome parecido; conferir)"
        vistos, unicos = set(), []
        for s, ln, fn in cand:
            k = (s["caminho"], ln)
            if k not in vistos:
                vistos.add(k)
                unicos.append((s, ln, fn))
        st = img.stat()
        linhas.append(
            {
                "imagem": rel(img, raiz),
                "modificada": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "scripts": unicos,
                "confianca": confianca or "nenhum script encontrado (figura órfã)",
                "sha1": sha1(img),
                "dim": dimensoes(img.read_bytes()[:65536])
                if img.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
                else None,
            }
        )
    return linhas


# ---------------------------------------------------------------------------
# 3. relatório .docx
# ---------------------------------------------------------------------------
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
V = "{urn:schemas-microsoft-com:vml}"

RX_LEG_FIG = re.compile(r"^\s*(figura|figure|fig\.?)\s*(\d+)\s*[\.\-–—:]?\s*(.*)", re.I | re.S)
RX_LEG_TAB = re.compile(r"^\s*(tabela|quadro|table)\s*(\d+)\s*[\.\-–—:]?\s*(.*)", re.I | re.S)
RX_CIT_FIG = re.compile(
    r"\b(?:figuras?|figs?\.?)\s*(\d+(?:\s*(?:[a-d]|[A-D]))?(?:\s*(?:,|e|a|-|–)\s*\d+)*)", re.I
)
RX_TITULO = re.compile(r"(heading|t[ií]tulo|ttulo|title)\s*(\d)?", re.I)


def texto_par(p) -> str:
    partes = []
    for el in p.iter():
        if el.tag == W + "t" and el.text:
            partes.append(el.text)
        elif el.tag in (W + "tab",):
            partes.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            partes.append(" ")
    return "".join(partes).strip()


def ler_docx(caminho: Path) -> dict:
    with zipfile.ZipFile(caminho) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        rels = {}
        if "word/_rels/document.xml.rels" in z.namelist():
            for r in ET.fromstring(z.read("word/_rels/document.xml.rels")):
                rels[r.get("Id")] = r.get("Target")
        estilos = {}
        if "word/styles.xml" in z.namelist():
            for s in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
                nome = s.find(W + "name")
                estilos[s.get(W + "styleId")] = (
                    nome.get(W + "val") if nome is not None else s.get(W + "styleId")
                )
        midia = {}
        for n in z.namelist():
            if n.startswith("word/media/"):
                dados = z.read(n)
                midia[n] = {
                    "sha1": hashlib.sha1(dados, usedforsecurity=False).hexdigest(),
                    "dim": dimensoes(dados[:65536]),
                    "bytes": len(dados),
                }

    corpo = doc.find(W + "body")
    blocos = []  # ordem do documento: parágrafos e tabelas
    for el in corpo:
        if el.tag == W + "p":
            blocos.append(("p", el))
        elif el.tag == W + "tbl":
            blocos.append(("tbl", el))
        elif el.tag == W + "sdt":
            for p in el.iter(W + "p"):
                blocos.append(("p", p))

    pars = []
    for tipo, el in blocos:
        if tipo == "tbl":
            pars.append(
                {
                    "tipo": "tabela",
                    "texto": " | ".join(texto_par(p) for p in el.iter(W + "p"))[:300],
                    "estilo": "",
                    "imagens": [],
                }
            )
            continue
        ps = el.find(W + "pPr")
        sid = ""
        if ps is not None and ps.find(W + "pStyle") is not None:
            sid = ps.find(W + "pStyle").get(W + "val")
        estilo = estilos.get(sid, sid)
        imgs = []
        for d in el.iter(WP + "docPr"):
            imgs.append(
                {
                    "nome": d.get("name", ""),
                    "descr": d.get("descr", "") or d.get("title", ""),
                    "alvo": None,
                }
            )
        blips = [b.get(R_NS + "embed") for b in el.iter(A + "blip")]
        blips += [b.get(R_NS + "id") for b in el.iter(V + "imagedata")]
        for i, rid in enumerate(blips):
            alvo = rels.get(rid)
            alvo = (
                ("word/" + alvo) if alvo and not alvo.startswith("/") else (alvo or "").lstrip("/")
            )
            if i < len(imgs):
                imgs[i]["alvo"] = alvo
            else:
                imgs.append({"nome": "", "descr": "", "alvo": alvo})
        campos = " ".join(t.text or "" for t in el.iter(W + "instrText"))
        pars.append(
            {
                "tipo": "par",
                "texto": texto_par(el),
                "estilo": estilo,
                "imagens": imgs,
                "seq": bool(re.search(r"\bSEQ\b", campos)),
            }
        )
    return {"pars": pars, "midia": midia}


def nivel_titulo(par) -> int | None:
    m = RX_TITULO.search(par["estilo"] or "")
    if m and par["texto"]:
        return int(m.group(2)) if m.group(2) else 1
    return None


def checar_legenda(txt: str) -> list[str]:
    faltas = []
    palavras = len(txt.split())
    if palavras < 15:
        faltas.append(f"legenda curta ({palavras} palavras)")
    if not re.search(r"\b[nN]\s*=\s*\d|\bN\s*=|\d+\s*(amostras|pontos|unidades amostrais)", txt):
        faltas.append("sem N amostral")
    if not re.search(
        r"p\s*[<=>≤]|permuta|bootstrap|Kruskal|Wilcoxon|PERMANOVA|ANOVA|teste|IC\s*95|intervalo de confian|R²|R2|SES|modelo",
        txt,
        re.I,
    ):
        faltas.append("sem teste estatístico/medida de incerteza")
    if not re.search(
        r"ind\.?\s*/\s*mL|c[ée]l\.?\s*/\s*mL|mg\s*/\s*L|µS|uS|%|org\.?\s*/\s*mL|\bunidade|escala|log",
        txt,
        re.I,
    ):
        faltas.append("sem unidade/escala")
    if not re.search(
        r"Montante|Intermedi|Jusante|Reservat|trecho|campanha|outubro|abril|2022|2023", txt, re.I
    ):
        faltas.append("sem identificar trechos/campanhas")
    if (
        re.search(r"\b[A-D]\)|\([A-D]\)|painel", txt) is None
        and re.search(r"\b(e|and)\b.*\b(e|and)\b", txt) is None
    ):
        pass
    return faltas


def auditar_docx(caminho: Path, imagens_info: list[dict], scripts: list[dict]) -> dict:
    d = ler_docx(caminho)
    pars, midia = d["pars"], d["midia"]

    por_hash = defaultdict(list)
    por_dim = defaultdict(list)
    for info in imagens_info:
        por_hash[info["sha1"]].append(info)
        if info["dim"]:
            por_dim[tuple(info["dim"])].append(info)

    titulos, figuras, citacoes_fig = [], [], []
    secao_atual = "(antes do primeiro título)"
    for i, p in enumerate(pars):
        txt = p["texto"]
        nv = nivel_titulo(p)
        if nv:
            secao_atual = txt[:90]
            titulos.append({"i": i, "nivel": nv, "texto": txt})
        if p["tipo"] == "par" and txt:
            m = RX_LEG_FIG.match(txt)
            if m and (len(txt) < 1500):
                p["leg_fig"] = int(m.group(2))
            m2 = RX_LEG_TAB.match(txt)
            if m2 and len(txt) < 800:
                p["leg_tab"] = int(m2.group(2))
            if "leg_fig" not in p:
                for c in RX_CIT_FIG.finditer(txt):
                    for n in re.findall(r"\d+", c.group(1)):
                        citacoes_fig.append((int(n), i))
        p["secao"] = secao_atual

    reservadas = set()

    def legenda_proxima(i, chave, reservar=False):
        for j in (i + 1, i + 2, i - 1, i - 2, i + 3):
            if not (0 <= j < len(pars)) or chave not in pars[j] or j in reservadas:
                continue
            # não atravessa outra imagem/tabela para "roubar" a legenda dela
            entre = range(min(i, j) + 1, max(i, j))
            if any(pars[k]["imagens"] or pars[k]["tipo"] == "tabela" for k in entre):
                continue
            if reservar:
                reservadas.add(j)
            return j
        return None

    # cada imagem inserida
    ordem = 0
    for i, p in enumerate(pars):
        for img in p["imagens"]:
            ordem += 1
            j = (
                i
                if "leg_fig" in p and i not in reservadas
                else legenda_proxima(i, "leg_fig", reservar=True)
            )
            if j == i:
                reservadas.add(i)
            leg = pars[j]["texto"] if j is not None else ""
            num = pars[j]["leg_fig"] if j is not None else None
            m = midia.get(img["alvo"] or "", {})
            casam, como = [], ""
            if m:
                casam = por_hash.get(m["sha1"], [])
                como = "idêntica (bytes)" if casam else ""
                if not casam and m.get("dim"):
                    casam = por_dim.get(tuple(m["dim"]), [])
                    como = "provável (mesmas dimensões em pixels)" if casam else ""
            scripts_fig = []
            for c in casam:
                for s, ln, fn in c["scripts"]:
                    scripts_fig.append((s, ln, c["imagem"]))
            figuras.append(
                {
                    "ordem": ordem,
                    "par": i,
                    "secao": p["secao"],
                    "num": num,
                    "legenda": leg,
                    "alt": img["descr"] or img["nome"],
                    "midia": img["alvo"],
                    "dim": m.get("dim"),
                    "casam": casam,
                    "como": como,
                    "scripts": scripts_fig,
                    "faltas": checar_legenda(leg) if leg else ["SEM LEGENDA"],
                    "seq": pars[j].get("seq", False) if j is not None else False,
                }
            )

    # legendas de figura que não estão ao lado de nenhuma imagem (gráfico colado como objeto, ou figura faltando)
    legendas_sem_imagem = [
        (i, p["leg_fig"], p["texto"])
        for i, p in enumerate(pars)
        if "leg_fig" in p and i not in reservadas and not p["imagens"]
    ]

    # tabelas
    tabelas = []
    for i, p in enumerate(pars):
        if p["tipo"] == "tabela":
            j = legenda_proxima(i, "leg_tab", reservar=True)
            tabelas.append(
                {
                    "par": i,
                    "secao": p["secao"],
                    "num": pars[j]["leg_tab"] if j is not None else None,
                    "legenda": pars[j]["texto"] if j is not None else "",
                    "inicio": p["texto"][:120],
                }
            )

    # "tabelas" digitadas como texto: sequência de ≥5 parágrafos curtos com números
    tabelas_texto = []
    seq = []
    for i, p in enumerate(pars):
        t = p["texto"]
        if (
            p["tipo"] == "par"
            and t
            and len(t) < 60
            and (re.search(r"\d", t) or len(t.split()) <= 3)
            and not nivel_titulo(p)
        ):
            seq.append(i)
        else:
            if len(seq) >= 6:
                tabelas_texto.append(
                    (
                        seq[0],
                        seq[-1],
                        pars[seq[0]]["secao"],
                        " / ".join(pars[k]["texto"] for k in seq[:6]),
                    )
                )
            seq = []

    # numeração
    def problemas_numeracao(nums):
        c = Counter(n for n in nums if n is not None)
        dup = sorted(n for n, k in c.items() if k > 1)
        faltando = sorted(set(range(1, max(c) + 1)) - set(c)) if c else []
        fora = [b for a, b in zip(nums, nums[1:]) if a is not None and b is not None and b < a]
        return dup, faltando, fora

    num_figs = [p["leg_fig"] for p in pars if "leg_fig" in p]
    num_tabs = [p["leg_tab"] for p in pars if "leg_tab" in p]

    # seções numeradas
    secs = []
    for t in titulos:
        m = re.match(r"^\s*(\d+(?:\.\d+)*)[\.\s]", t["texto"])
        if m:
            secs.append(tuple(int(x) for x in m.group(1).split(".")))
    saltos = []
    ant = {}
    for s in secs:
        nivel = len(s)
        prev = ant.get(nivel)
        if nivel == 1 and prev and s[0] not in (prev[0], prev[0] + 1):
            saltos.append(f"{'.'.join(map(str, prev))} → {'.'.join(map(str, s))}")
        if nivel > 1 and prev and prev[:-1] == s[:-1] and s[-1] not in (prev[-1], prev[-1] + 1):
            saltos.append(f"{'.'.join(map(str, prev))} → {'.'.join(map(str, s))}")
        ant[nivel] = s
        for k in list(ant):
            if k > nivel:
                del ant[k]
    if secs and secs[0][0] != 1:
        saltos.insert(0, f"primeira seção numerada é {secs[0][0]}")
    dup_secs = [".".join(map(str, s)) for s, k in Counter(secs).items() if k > 1]

    titulos_longos = [t for t in titulos if len(t["texto"]) > 140]

    # parágrafos duplicados / quase duplicados
    longos = [
        (i, norm(p["texto"]))
        for i, p in enumerate(pars)
        if p["tipo"] == "par" and len(p["texto"]) > 180
    ]
    duplicados = []
    for a in range(len(longos)):
        for b in range(a + 1, len(longos)):
            sa, sb = longos[a][1], longos[b][1]
            sm = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
            if sm.real_quick_ratio() < 0.6 or sm.quick_ratio() < 0.6:
                continue
            r = sm.ratio()
            if r >= 0.6:
                duplicados.append((longos[a][0], longos[b][0], r))

    # citações x referências
    corpo_txt, refs_txt, em_refs = [], [], False
    for p in pars:
        if nivel_titulo(p) or re.fullmatch(
            r"\s*(refer[eê]ncias(\s+bibliogr[aá]ficas)?|bibliografia|references)\s*",
            p["texto"],
            re.I,
        ):
            em_refs = bool(re.search(r"refer[eê]ncias|bibliografia|references", p["texto"], re.I))
            continue
        (refs_txt if em_refs else corpo_txt).append(p["texto"])
    corpo = "\n".join(corpo_txt)
    cit = set()
    sobrenome = r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]+"
    for m in re.finditer(r"\(([^()]*?\b(?:19|20)\d\d[a-z]?[^()]*)\)", corpo):
        # (BAKER; KING, 2010; ANDERSON, 2006): o 1º sobrenome antes de cada ano é o 1º autor
        ini = 0
        for ano in re.finditer(r"\b((?:19|20)\d\d)[a-z]?\b", m.group(1)):
            seg = m.group(1)[ini : ano.start()]
            ini = ano.end()
            mm = re.search(sobrenome, seg)
            if mm:
                cit.add((norm(mm.group(0)), ano.group(1)))
    for mm in re.finditer(
        rf"\b({sobrenome})(?:\s+et\s+al\.?|\s+(?:e|&|and)\s+{sobrenome})?\s*\(((?:19|20)\d\d)[a-z]?\)",
        corpo,
    ):
        cit.add((norm(mm.group(1)), mm.group(2)))
    ignorar = {
        "figura",
        "tabela",
        "portaria",
        "resolucao",
        "lei",
        "conama",
        "decreto",
        "campanha",
        "outubro",
        "abril",
        "em",
        "de",
        "no",
    }
    cit = {c for c in cit if c[0] not in ignorar}
    refs = set()
    for r in refs_txt:
        mm = re.match(rf"\s*({sobrenome})", r)
        ano = re.search(r"\b((?:19|20)\d\d)[a-z]?\b", r)
        if mm and ano:
            refs.add((norm(mm.group(1)), ano.group(1)))
    cit_sem_ref = sorted(c for c in cit if c not in refs)
    ref_sem_cit = sorted(r for r in refs if r not in cit)

    # pendências textuais
    pend_rx = [
        (
            r"\[\s*autor\s*,?\s*ano\s*\]|\[\s*ref\w*\s*\]|\(autor,?\s*ano\)",
            "citação-marcador [autor, ano]",
        ),
        (
            r"Erro!\s*Fonte de refer[eê]ncia n[aã]o encontrada|Error!\s*Reference source not found",
            "referência cruzada quebrada",
        ),
        (r"\bXX+\b|\?\?+|TODO|COMPLETAR|inserir aqui", "trecho a completar"),
        (r"\bexeto\b", "exeto → exceto"),
        (r"\bapartir\b", "apartir → a partir"),
        (r"\bralação\b", "ralação → relação"),
        (r"\bAcomposição\b", "Acomposição → A composição"),
        (r"\bind\.\s*/?\s*mL", "padronizar unidade: ind/mL"),
        (r"\bcel\.\s*/?\s*mL|\bcels\s*/\s*mL", "padronizar unidade: cél/mL"),
        (
            r"(?<![\d\.,])\d+\.\d+(?![\d\.])",
            "decimal com ponto (usar vírgula no texto em português)",
        ),
    ]
    pendencias = []
    for i, p in enumerate(pars):
        for rx, desc in pend_rx:
            for m in re.finditer(rx, p["texto"]):
                ctx = p["texto"][max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")
                pendencias.append((i, p["secao"], desc, ctx))

    # citações a figuras
    nums_leg = set(num_figs)
    citadas = Counter(n for n, _ in citacoes_fig)
    citadas_sem_leg = sorted(n for n in citadas if n not in nums_leg)
    leg_nao_citadas = sorted(n for n in nums_leg if n not in citadas)

    return {
        "pars": pars,
        "titulos": titulos,
        "figuras": figuras,
        "tabelas": tabelas,
        "tabelas_texto": tabelas_texto,
        "legendas_sem_imagem": legendas_sem_imagem,
        "num_figs": problemas_numeracao(num_figs),
        "num_tabs": problemas_numeracao(num_tabs),
        "lista_figs": num_figs,
        "saltos_secoes": saltos,
        "dup_secoes": dup_secs,
        "titulos_longos": titulos_longos,
        "duplicados": duplicados,
        "cit_sem_ref": cit_sem_ref,
        "ref_sem_cit": ref_sem_cit,
        "n_cit": len(cit),
        "n_ref": len(refs),
        "pendencias": pendencias,
        "citadas_sem_leg": citadas_sem_leg,
        "leg_nao_citadas": leg_nao_citadas,
        "n_midia": len(midia),
    }


# ---------------------------------------------------------------------------
# esqueleto de legenda a partir do script
# ---------------------------------------------------------------------------
def esqueleto_legenda(scripts: list[dict], num) -> str:
    if not scripts:
        return (
            "Figura {n}. [Tipo de gráfico] de [variável, unidade] por [trecho: Montante, Intermediário, Jusante, "
            "Reservatório] e [campanha: out/2022, abr/2023]; N = [n] amostras. [Teste/modelo] ([parâmetros]). "
            "[Significado de símbolos, cores, barras de erro, letras]. Fonte: [script]."
        ).format(n=num or "X")
    s = scripts[0]
    graf = ", ".join(s["graficos"]) or "[tipo de gráfico]"
    an = "; ".join(a["analise"] for a in s["analises"][:4]) or "[análise]"
    p = s["params"]
    det = []
    for chave in ("permutations", "nperm", "numPerm", "nBoot", "nboot", "iterações"):
        if chave in p:
            det.append(f"{chave} = {', '.join(p[chave])}")
    if "set.seed" in p:
        det.append(f"semente = {', '.join(p['set.seed'])}")
    for chave in (
        "method",
        "distance",
        "family",
        "corr (dbFD)",
        "func (IndVal)",
        "index.family (betapart)",
        "datatype (iNEXT)",
        "ajuste de p",
    ):
        if chave in p:
            det.append(f"{chave}: {', '.join(p[chave][:3])}")
    mapa = ""
    if "mapa" in s["graficos"]:
        mapa = " Sistema de referência [SIRGAS 2000 / UTM 22S], escala gráfica, norte, fonte da base cartográfica [IBGE/MapBiomas/SDE-SC]."
    return (
        f"Figura {num or 'X'}. {graf.capitalize()} de [variável, unidade] por [trecho] e [campanha]; N = [n]. "
        f"{an} ({'; '.join(det) if det else 'informar permutações/bootstraps/semente'}). "
        f"[Explicar símbolos, cores, barras/IC, letras de significância].{mapa} Script: {s['nome']}."
    )


# ---------------------------------------------------------------------------
# saída
# ---------------------------------------------------------------------------
def escrever_csv(caminho: Path, cabecalho: list[str], linhas: list[list]):
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cabecalho)
        w.writerows(linhas)


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def gerar_saida(raiz: Path, saida: Path, scripts, imagens_info, aud, relatorio: Path | None):
    saida.mkdir(parents=True, exist_ok=True)

    escrever_csv(
        saida / "01_inventario_scripts.csv",
        [
            "script",
            "linhas",
            "modificado",
            "analises_detectadas",
            "graficos",
            "figuras_geradas",
            "tabelas_geradas",
            "nomes_dinamicos",
            "entradas",
            "parametros",
            "pacotes",
        ],
        [
            [
                s["caminho"],
                s["linhas"],
                s["modificado"],
                " | ".join(
                    f"{a['analise']} (l. {','.join(map(str, a['linhas'][:4]))})"
                    for a in s["analises"]
                ),
                ", ".join(s["graficos"]),
                ", ".join(
                    sorted(
                        {
                            a
                            for o in s["saidas"]
                            for a in o["arquivos"]
                            if Path(a).suffix.lower() in IMAGE_EXT
                        }
                        | set(s["literais_fig"])
                    )
                ),
                ", ".join(
                    sorted(
                        {
                            a
                            for o in s["saidas"]
                            for a in o["arquivos"]
                            if Path(a).suffix.lower() in TABLE_EXT
                        }
                    )
                ),
                " | ".join(
                    f"l.{o['linha']} {o['funcao']}({o['trecho'][:80]})"
                    for o in s["saidas"]
                    if o["dinamico"]
                ),
                ", ".join(s["entradas"]),
                " | ".join(f"{k}={','.join(v)}" for k, v in s["params"].items()),
                ", ".join(s["pacotes"]),
            ]
            for s in scripts
        ],
    )

    usadas_no_rel = defaultdict(list)
    if aud:
        for f in aud["figuras"]:
            for c in f["casam"]:
                usadas_no_rel[c["imagem"]].append(f["num"] or f"(sem nº, imagem {f['ordem']})")
    escrever_csv(
        saida / "02_inventario_imagens.csv",
        [
            "imagem",
            "modificada",
            "script(s)",
            "linha",
            "confianca",
            "analises_no_script",
            "no_relatorio_como",
        ],
        [
            [
                i["imagem"],
                i["modificada"],
                " | ".join(s["caminho"] for s, _, _ in i["scripts"]),
                " | ".join(str(ln or "?") for _, ln, _ in i["scripts"]),
                i["confianca"],
                " | ".join(
                    sorted({a["analise"] for s, _, _ in i["scripts"] for a in s["analises"]})
                ),
                ", ".join(
                    f"Figura {n}" if isinstance(n, int) else str(n)
                    for n in usadas_no_rel.get(i["imagem"], [])
                )
                or "não usada",
            ]
            for i in imagens_info
        ],
    )

    if aud:
        escrever_csv(
            saida / "03_figuras_no_relatorio.csv",
            [
                "ordem",
                "secao",
                "numero_legenda",
                "legenda_atual",
                "o_que_falta",
                "arquivo_correspondente",
                "correspondencia",
                "script",
                "analises",
                "parametros_no_script",
                "legenda_sugerida",
            ],
            [
                [
                    f["ordem"],
                    f["secao"],
                    f["num"] or "",
                    f["legenda"][:600],
                    "; ".join(f["faltas"]),
                    " | ".join(c["imagem"] for c in f["casam"]),
                    f["como"],
                    " | ".join(
                        f"{s['caminho']}{(' l.' + str(ln)) if ln else ''}"
                        for s, ln, _ in f["scripts"]
                    ),
                    " | ".join(
                        sorted({a["analise"] for s, _, _ in f["scripts"] for a in s["analises"]})
                    ),
                    " | ".join(
                        sorted(
                            {
                                f"{k}={','.join(v)}"
                                for s, _, _ in f["scripts"]
                                for k, v in s["params"].items()
                            }
                        )
                    ),
                    esqueleto_legenda([s for s, _, _ in f["scripts"]], f["num"]),
                ]
                for f in aud["figuras"]
            ],
        )

    L = []
    add = L.append
    add("# Diagnóstico do Relatório Ambiental — Fitoplâncton (LJS/CASAN)\n")
    add(f"Gerado em {dt.datetime.now():%d/%m/%Y %H:%M} por `mapear_figuras.py`.  ")
    add(f"Pasta analisada: `{raiz}`  ")
    add(
        f"Relatório: `{relatorio}`\n"
        if relatorio
        else "Relatório: (nenhum .docx informado/encontrado)\n"
    )

    add("## Resumo\n")
    add(f"- Scripts encontrados: **{len(scripts)}**")
    add(
        f"- Imagens na pasta: **{len(imagens_info)}**; sem script identificado (órfãs): "
        f"**{sum(1 for i in imagens_info if not i['scripts'])}**"
    )
    if aud:
        sem_leg = [f for f in aud["figuras"] if "SEM LEGENDA" in f["faltas"]]
        sem_scr = [f for f in aud["figuras"] if not f["scripts"]]
        dup, falt, fora = aud["num_figs"]
        add(
            f"- Imagens inseridas no relatório: **{len(aud['figuras'])}**; sem legenda: **{len(sem_leg)}**; "
            f"sem script identificado: **{len(sem_scr)}**"
        )
        add(
            f"- Numeração de figuras — duplicadas: **{dup or 'nenhuma'}**; faltando: **{falt or 'nenhuma'}**; "
            f"fora de ordem: **{fora or 'nenhuma'}**"
        )
        dup_t, falt_t, _ = aud["num_tabs"]
        add(
            f"- Tabelas do Word: **{len(aud['tabelas'])}** (sem título: {sum(1 for t in aud['tabelas'] if t['num'] is None)}); "
            f"tabelas digitadas como texto corrido: **{len(aud['tabelas_texto'])}**; nº de tabela duplicado: {dup_t or 'nenhum'}; faltando: {falt_t or 'nenhum'}"
        )
        add(
            f"- Saltos na numeração de seções: **{aud['saltos_secoes'] or 'nenhum'}**; títulos com texto corrido: **{len(aud['titulos_longos'])}**"
        )
        add(f"- Parágrafos duplicados/quase duplicados: **{len(aud['duplicados'])}**")
        add(
            f"- Citações sem referência: **{len(aud['cit_sem_ref'])}**; referências não citadas: **{len(aud['ref_sem_cit'])}**"
        )
        add(
            f"- Pendências textuais (marcadores, unidades, ortografia, decimais): **{len(aud['pendencias'])}**\n"
        )

        add("## 1. Figuras do relatório, uma a uma\n")
        add(
            "Para cada imagem inserida no Word: onde está, a legenda atual, o que falta e de qual script ela veio. "
            "A correspondência é feita comparando os bytes da imagem do Word com os arquivos da pasta "
            "(e, se o Word recomprimiu a imagem, pelas dimensões em pixels).\n"
        )
        for f in aud["figuras"]:
            add(
                f"### Imagem {f['ordem']} — {'Figura ' + str(f['num']) if f['num'] else 'SEM NÚMERO'}"
            )
            add(f"- **Seção:** {f['secao']}")
            add(f"- **Legenda atual:** {f['legenda'] or '— (não há legenda)'}")
            add(
                f"- **Falta:** {'; '.join(f['faltas']) or 'ok'}"
                + (
                    ""
                    if f["seq"] or not f["legenda"]
                    else " · numeração digitada à mão (usar Inserir Legenda para numerar automaticamente)"
                )
            )
            if f["casam"]:
                add(
                    f"- **Arquivo:** {', '.join('`' + c['imagem'] + '`' for c in f['casam'])} ({f['como']})"
                )
            else:
                add(
                    f"- **Arquivo:** não localizado na pasta (imagem colada de outro lugar, recortada ou recomprimida). Texto alternativo: `{f['alt']}`"
                )
            if f["scripts"]:
                for s, ln, img in f["scripts"]:
                    add(
                        f"- **Script:** `{s['caminho']}`{(' linha ' + str(ln)) if ln else ''} — análises: "
                        f"{', '.join(a['analise'] for a in s['analises']) or 'nenhuma detectada'}; gráfico: {', '.join(s['graficos']) or '?'}"
                    )
                    exige = {a["analise"]: a["exige"] for a in s["analises"]}
                    for k, v in list(exige.items())[:5]:
                        add(f"  - *{k}* → a legenda/métodos devem informar: {v}")
            else:
                add(
                    "- **Script:** não identificado — procure pelo nome do arquivo de imagem no `02_inventario_imagens.csv`."
                )
            add(
                f"- **Legenda sugerida (esqueleto):** {esqueleto_legenda([s for s, _, _ in f['scripts']], f['num'])}\n"
            )

        if aud["legendas_sem_imagem"]:
            add("## 2. Legendas sem imagem ao lado\n")
            add(
                "Podem ser gráficos colados como objeto do Excel/gráfico do Word, figuras removidas, ou legendas soltas.\n"
            )
            for i, n, t in aud["legendas_sem_imagem"]:
                add(f"- Parágrafo {i}: **Figura {n}** — {md_escape(t[:200])}")
            add("")

        add("## 3. Numeração e referências cruzadas de figuras\n")
        add(f"- Ordem das legendas no documento: {aud['lista_figs']}")
        add(
            f"- Figuras citadas no texto sem legenda correspondente: {aud['citadas_sem_leg'] or 'nenhuma'}"
        )
        add(
            f"- Figuras com legenda nunca citadas no texto: {aud['leg_nao_citadas'] or 'nenhuma'}\n"
        )

        add("## 4. Tabelas\n")
        for t in aud["tabelas"]:
            add(
                f"- Tabela do Word no parágrafo {t['par']} ({t['secao']}): "
                f"{'Tabela ' + str(t['num']) + ' — ' + md_escape(t['legenda'][:120]) if t['num'] else '**SEM TÍTULO**'} · início: {md_escape(t['inicio'])}"
            )
        for a, b, sec, amostra in aud["tabelas_texto"]:
            add(
                f"- **Tabela digitada como texto** (parágrafos {a}–{b}, seção {sec}): `{md_escape(amostra[:150])}` → converter em tabela do Word com título e fonte."
            )
        add("")

        add("## 5. Estrutura e seções\n")
        add("Títulos detectados (estilo Título/Heading):\n")
        for t in aud["titulos"]:
            add(
                f"{'  ' * (t['nivel'] - 1)}- [{t['nivel']}] {md_escape(t['texto'][:120])}{' …' if len(t['texto']) > 120 else ''}"
            )
        add("")
        add(f"- Saltos de numeração: {aud['saltos_secoes'] or 'nenhum'}")
        add(f"- Números de seção repetidos: {aud['dup_secoes'] or 'nenhum'}")
        for t in aud["titulos_longos"]:
            add(
                f'- **Título com texto corrido** (parágrafo {t["i"]}, {len(t["texto"])} caracteres): "{md_escape(t["texto"][:100])}…" → separar título e parágrafo (estilo Normal).'
            )
        add("")

        add("## 6. Parágrafos duplicados ou quase duplicados\n")
        pars = aud["pars"]
        for a, b, r in sorted(aud["duplicados"], key=lambda x: -x[2]):
            add(
                f'- Parágrafos {a} e {b} ({r:.0%} iguais) — seção "{pars[a]["secao"][:50]}" / "{pars[b]["secao"][:50]}"'
            )
            add(f"  - {a}: {md_escape(pars[a]['texto'][:160])}…")
            add(f"  - {b}: {md_escape(pars[b]['texto'][:160])}…")
        if not aud["duplicados"]:
            add("- nenhum")
        add("")

        add("## 7. Citações e referências (verificação automática — conferir)\n")
        add(
            f"- Citações distintas no texto: {aud['n_cit']}; entradas na lista de referências: {aud['n_ref']}"
        )
        add(
            f"- Citadas no texto e ausentes da lista: {', '.join(f'{a.title()} ({y})' for a, y in aud['cit_sem_ref']) or 'nenhuma'}"
        )
        add(
            f"- Na lista mas não citadas: {', '.join(f'{a.title()} ({y})' for a, y in aud['ref_sem_cit']) or 'nenhuma'}\n"
        )

        add("## 8. Pendências textuais\n")
        cont = Counter(d for _, _, d, _ in aud["pendencias"])
        for d, k in cont.most_common():
            add(f"- **{d}**: {k} ocorrência(s)")
        add("")
        for i, sec, d, ctx in aud["pendencias"][:200]:
            add(f'  - par. {i} ({sec[:40]}): {d} — "…{md_escape(ctx)}…"')
        add("")

    add("## 9. Inventário de scripts\n")
    add("| Script | Análises detectadas | Gráficos | Figuras que gera | Parâmetros |")
    add("|---|---|---|---|---|")
    for s in scripts:
        figs = sorted(
            {a for o in s["saidas"] for a in o["arquivos"] if Path(a).suffix.lower() in IMAGE_EXT}
            | set(s["literais_fig"])
        )
        add(
            f"| `{md_escape(s['caminho'])}` | {md_escape(', '.join(a['analise'] for a in s['analises']))} | "
            f"{md_escape(', '.join(s['graficos']))} | {md_escape(', '.join(figs)[:300])} | "
            f"{md_escape('; '.join(f'{k}={chr(44).join(v)}' for k, v in s['params'].items())[:200])} |"
        )
    add("")
    orfas = [i for i in imagens_info if not i["scripts"]]
    if orfas:
        add("## 10. Imagens sem script identificado\n")
        add(
            "Possíveis causas: nome gerado em laço (`for`), exportação manual pelo RStudio (Export > Save as Image), "
            "imagem editada depois, ou script fora desta pasta.\n"
        )
        for i in orfas:
            add(f"- `{i['imagem']}` ({i['modificada']})")
        add("")

    (saida / "04_diagnostico_relatorio.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
def escolher_relatorio(raiz: Path) -> Path | None:
    docs = [p for p in iter_arquivos(raiz) if p.suffix.lower() == ".docx"]
    if not docs:
        return None

    def peso(p: Path):
        n = norm(p.name)
        return (("relat" in n) + ("complet" in n) + ("final" in n), p.stat().st_mtime)

    return max(docs, key=peso)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("pasta", help="pasta com scripts, figuras e relatório")
    ap.add_argument(
        "--relatorio",
        help="caminho do relatório .docx (padrão: o .docx mais provável dentro da pasta)",
    )
    ap.add_argument("--saida", help="pasta de saída (padrão: <pasta>/_auditoria_relatorio)")
    a = ap.parse_args(argv)

    raiz = Path(a.pasta).expanduser().resolve()
    if not raiz.is_dir():
        sys.exit(f"Pasta não encontrada: {raiz}")
    saida = Path(a.saida).resolve() if a.saida else raiz / "_auditoria_relatorio"

    arquivos = list(iter_arquivos(raiz))
    scripts = [analisar_script(p, raiz) for p in arquivos if p.suffix.lower() in SCRIPT_EXT]
    imagens = [p for p in arquivos if p.suffix.lower() in IMAGE_EXT]
    relatorio = Path(a.relatorio).resolve() if a.relatorio else escolher_relatorio(raiz)
    if relatorio:
        imagens = [p for p in imagens if p.resolve() != relatorio.with_suffix(".pdf")]
    print(
        f"{len(scripts)} scripts, {len(imagens)} imagens. Relatório: {relatorio or 'não encontrado'}"
    )

    imagens_info = ligar_imagens(imagens, scripts, raiz)
    aud = None
    if relatorio and relatorio.exists():
        try:
            aud = auditar_docx(relatorio, imagens_info, scripts)
        except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
            print(
                f"Não foi possível ler o .docx ({e}). Salve-o como .docx (não .doc) e feche-o no Word."
            )
    gerar_saida(raiz, saida, scripts, imagens_info, aud, relatorio)
    print(f"Pronto. Abra: {saida / '04_diagnostico_relatorio.md'}")


if __name__ == "__main__":
    main()
