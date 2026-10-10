# Auditoria do Relatório Ambiental — Fitoplâncton

Ferramentas para organizar o relatório do fitoplâncton do Lajeado São José (CASAN): ligar cada gráfico ao script R que o gerou e apontar legendas incompletas, numeração quebrada, seções e parágrafos duplicados e referências faltantes.

| Arquivo | Para que serve |
|---|---|
| `mapear_figuras.py` | Auditor automático (somente leitura). Varre scripts, imagens e o `.docx`. |
| `GUIA_legendas_e_estrutura.md` | Padrão científico de legenda por tipo de análise, tabelas obrigatórias e estrutura do relatório. |
| `Modelo_Relatorio_Fitoplancton.docx` | Modelo Word do relatório (5 partes, 13 capítulos) com 28 figuras e 16 tabelas já posicionadas, legendas-modelo, numeração automática (Inserir Legenda/SEQ), sumário e apêndice de rastreabilidade. Ao abrir, aceite "atualizar campos". |
| `gerar_modelo_relatorio.js` | Gera o modelo de novo (`node gerar_modelo_relatorio.js`), se você quiser mudar a estrutura. |

## Como rodar no seu computador (Windows)

1. Instale o Python 3.8 ou superior (python.org) se ainda não tiver. Nenhuma biblioteca extra é necessária.
2. Feche o relatório no Word. Ele precisa estar salvo como **.docx**, não .doc.
3. No PowerShell:

```powershell
python mapear_figuras.py "E:\Fitoplancton\Relatório completo Fitoplancton"
```

Se o relatório estiver fora da pasta, ou houver mais de um .docx:

```powershell
python mapear_figuras.py "E:\Fitoplancton\Relatório completo Fitoplancton" --relatorio "E:\Fitoplancton\Relatório completo Fitoplancton\Relatorio_final.docx"
```

**Recomendado: rodar na pasta-mãe inteira.** Os scripts que geram as figuras ficam espalhados entre `fitoplancton_consolidado\` (pipeline `00`–`15`, `99_figures_english.R`, `run_all_figures.R`, `fig0X_*.R`), `SM_dados_totais\Scripts\` (espelho) e `plano guilherme\` (variantes, inclusive `.R.txt`, e os mapas em Python). Rodar na pasta-mãe cobre tudo:

```powershell
python mapear_figuras.py "E:\Fitoplancton" --relatorio "E:\Fitoplancton\Relatório completo Fitoplancton\<nome do relatório>.docx" --saida "E:\Fitoplancton\Relatório completo Fitoplancton\_auditoria_relatorio"
```

4. Abra `E:\Fitoplancton\Relatório completo Fitoplancton\_auditoria_relatorio\04_diagnostico_relatorio.md` (no VS Code, no Typora ou em qualquer editor de texto). Os CSVs abrem no Excel (separador `;`).

## O que sai

| Arquivo | Conteúdo |
|---|---|
| `01_inventario_scripts.csv` | Cada script: análises detectadas (PCA, PERMANOVA, dbFD, TITAN2, IndVal, iNEXT, glm.nb, hurdle...) com o nº da linha, tipo de gráfico, figuras e tabelas que gera, dados de entrada, `set.seed`, permutações e bootstraps. |
| `02_inventario_imagens.csv` | Cada imagem da pasta → script e linha que a gera, grau de confiança e se ela está no relatório (como "Figura N"). |
| `03_figuras_no_relatorio.csv` | Cada imagem do Word, na ordem: seção, legenda atual, **o que falta**, arquivo de origem, script, parâmetros e **legenda sugerida**. |
| `04_diagnostico_relatorio.md` | Relatório completo: figuras uma a uma, legendas sem imagem, numeração, tabelas (inclusive as digitadas como texto), seções, parágrafos duplicados, citações × referências, pendências de texto (inclusive marcadores `[please ...]`), scripts com cópias divergentes entre pastas e encadeamento por `source()`. |
| `05_resultados_texto.csv` | Cada arquivo de resultado (`saidas\*.txt`, `.csv`) → script e linha que o escreve (`sink`, `capture.output`, `write.csv`...). Serve para rastrear de onde vem cada número citado no texto. |

## Como a figura do Word é ligada ao script

1. A imagem dentro do .docx é comparada **byte a byte** com as imagens da pasta. O Word costuma guardar o PNG original.
2. Se o Word recomprimiu a imagem, a comparação é feita pelas **dimensões em pixels**.
3. O arquivo encontrado é procurado nos scripts: `ggsave()`, `png()`, `pdf()`, `tiff()`, `savefig()`, inclusive com nomes montados por `paste0()`/`file.path()` e nomes guardados em variáveis.

Os casos que não fecham aparecem como "órfã" ou "não localizado". Normalmente é uma imagem exportada à mão pelo RStudio, um print, ou um script guardado fora da pasta. Também dá para rodar o auditor na pasta-mãe (`E:\Fitoplancton`) para incluir os scripts de outras subpastas.

## Limitações

- A detecção é por padrões de texto. Confira as análises listadas antes de copiá-las para os Métodos.
- O cruzamento citação × referência é aproximado (sobrenome + ano).
- Gráficos colados como objeto do Excel não são imagens. Eles aparecem em "Legendas sem imagem ao lado".
