import json
import shutil
import types
from pathlib import Path

import pytest

from scripts import check_vnext_claims as gate

ROOT = Path(__file__).resolve().parents[1]


class TestDocumentosAuditados:
    def test_cobre_os_dois_diretorios_sem_repetir(self):
        docs = gate.audited_docs()
        nomes = {p.name for p in docs}
        assert "FINAL-REPORT.md" in nomes
        assert "ADR-001-canonical-registry.md" in nomes
        assert len(nomes) == len(docs), "documento contado duas vezes"
        assert any(p.parent.name == "adrs" for p in docs)
        assert any(p.parent.name == "vnext" for p in docs)

    def test_inclui_todo_adr_do_diretorio(self):
        no_disco = {p.name for p in (gate.VNEXT / "adrs").glob("*.md")}
        auditados = {p.name for p in gate.audited_docs()}
        assert no_disco <= auditados

    def test_o_caminho_e_relativo_a_raiz(self):
        doc = gate.audited_docs()[0]
        assert gate.rel(doc).startswith("docs/vnext/")
        assert "\\" not in gate.rel(doc)


DOC_SINTETICO = """# Titulo

Este relatorio declara uma economia de 81,8% no custo por mil tarefas
e 5.485 testes na suite, em 2026-08-21, versao 0.5.0, conforme ADR-003.
Sao 38 agentes no catalogo.

Fonte: https://docs.aws.amazon.com/glue/latest/dg/release-notes-5-1.html

```python
BATCH = 1000
```
"""


class TestExtracaoNumerica:
    def _extrai(self, tmp_path):
        doc = tmp_path / "SINTETICO.md"
        doc.write_text(DOC_SINTETICO, encoding="utf-8")
        return [item["text"] for item in gate.extract_numbers(doc)]

    def test_captura_percentual_e_contagem(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "81,8%" in textos
        assert "5.485" in textos
        # Contagem de um ou dois digitos e a forma dominante de alegacao
        # nestes documentos -- perde-la e um buraco permanente na auditoria.
        assert "38" in textos

    def test_lookaround_descarta_data_e_identificador(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert not any("2026-08-21" in t for t in textos)
        assert not any(t == "003" for t in textos)

    def test_allowlist_descarta_versao_semantica_mesmo_com_pontuacao(self, tmp_path):
        doc = tmp_path / "VERSAO.md"
        doc.write_text("Pacote na versao 0.5.0, publicado.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_allowlist_descarta_ano_isolado_mesmo_com_pontuacao(self, tmp_path):
        doc = tmp_path / "ANO.md"
        doc.write_text("Fechado em 2026, sem pendencia.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_token_nao_carrega_pontuacao_final(self, tmp_path):
        doc = tmp_path / "PONTUACAO.md"
        doc.write_text("Sao 17, e depois 3.5, no total.\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["17", "3.5"]

    def test_ignora_bloco_de_codigo_e_linha_de_fonte(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "1000" not in textos
        assert not any("5-1" in t for t in textos)

    def test_percentual_negativo_solto_vira_alegacao_com_o_sinal(self, tmp_path):
        # Achado ao ler a semente inteira (Task 8): FINAL-REPORT.md alega
        # "**-81.8%** de economia" -- exatamente o exemplo motivador desta
        # tarefa -- e o NUMBER_RE antigo nunca produzia candidato nenhum pra
        # esse token porque o lookbehind bloqueava incondicionalmente
        # qualquer numero colado a `-`. O sinal precisa entrar no texto da
        # alegacao: "-81.8%" e "81.8%" sao afirmacoes opostas.
        doc = tmp_path / "NEGATIVO.md"
        doc.write_text(
            "| Custo | Antes | Depois |\n|---|---|---|\n"
            "| Estimativa | $45.00 | **-81.8%** de economia |\n",
            encoding="utf-8",
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert "-81.8%" in textos
        assert "45.00" in textos

    def test_hifen_de_identificador_continua_bloqueado_com_sinal_negativo_no_regex(
        self, tmp_path
    ):
        # Guarda de nao-regressao: o novo ramo que aceita `-` de negativo nao
        # pode reabrir a porta que o lookbehind original fechava para
        # identificador (`ADR-003`) e data ISO (`2026-08-21`) -- nos dois
        # casos o hifen esta colado a letra/digito, entao nao e sinal de
        # negativo solto.
        doc = tmp_path / "IDENTIFICADOR.md"
        doc.write_text(
            "Registrado em 2026-08-21 conforme ADR-003.\n", encoding="utf-8"
        )
        assert gate.extract_numbers(doc) == []

    def test_numero_negativo_precedido_de_espaco_tambem_vira_alegacao(self, tmp_path):
        doc = tmp_path / "NEGATIVO.md"
        doc.write_text("Variacao de -5 unidades no periodo.\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["-5"]

    def test_marcador_de_lista_com_hifen_seguido_de_espaco_nao_vira_negativo(
        self, tmp_path
    ):
        # Marcador de lista Markdown ("- item") usa hifen seguido de ESPACO,
        # nunca colado direto no digito -- o novo ramo exige `-\d` sem espaco
        # entre os dois, entao um item de lista comecando com numero
        # continua capturando so o numero, sem o hifen do marcador.
        doc = tmp_path / "LISTA.md"
        doc.write_text("- 5% de melhoria observada.\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["5%"]

    def test_cada_padrao_da_allowlist_declara_a_razao(self):
        for _, razao in gate.IGNORED_TOKENS:
            assert razao and len(razao) > 10

    def test_cada_padrao_de_ignored_lines_declara_a_razao(self):
        for _, razao in gate.IGNORED_LINES:
            assert razao and len(razao) > 10

    def test_marcador_de_lista_ordenada_nao_vira_alegacao(self, tmp_path):
        doc = tmp_path / "LISTA.md"
        doc.write_text(
            "1. Primeiro item da lista.\n2. Segundo item da lista.\n"
            "10. Decimo item, dois digitos no marcador.\n",
            encoding="utf-8",
        )
        assert gate.extract_numbers(doc) == []

    def test_marcador_de_lista_indentada_tambem_nao_vira_alegacao(self, tmp_path):
        # Lista aninhada ("  1. sub-item") usa a mesma forma de marcador com
        # indentacao antes do numero -- `IGNORED_LINES` aceita espaco opcional
        # no inicio da linha por isso.
        doc = tmp_path / "LISTA.md"
        doc.write_text("  1. Sub-item indentado.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_marcador_de_lista_nao_apaga_numero_real_na_mesma_linha(self, tmp_path):
        # Caso real do corpus (ARCHITECTURE.md, FINAL-REPORT.md): o marcador
        # "1." e ruido estrutural, mas "2.0" logo depois e uma alegacao de
        # versao de verdade -- mascarar so o prefixo, nao a linha inteira,
        # preserva ela.
        doc = tmp_path / "LISTA.md"
        doc.write_text(
            "1. **Antigravity 2.0**: plataforma com progressive disclosure.\n",
            encoding="utf-8",
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["2.0"]

    def test_numero_de_titulo_markdown_nao_vira_alegacao(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text("## 3. Lacunas Identificadas\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_numero_de_titulo_com_ate_seis_cerquilhas_nao_vira_alegacao(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text("###### 12. Subsecao profunda\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_numero_de_titulo_nao_apaga_numero_real_no_resto_da_linha(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text("## 4. Suporte a 12 plataformas\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["12"]

    def test_titulo_sem_numero_continua_capturando_numero_no_texto(self, tmp_path):
        # Guarda contra um regex de titulo tao amplo que apague qualquer
        # cerquilha -- so titulo cujo primeiro token e um numero seguido de
        # ponto deve mascarar.
        doc = tmp_path / "TITULO.md"
        doc.write_text("## Suporte a 12 plataformas\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["12"]

    def test_numero_de_fase_do_roadmap_no_titulo_h1_nao_vira_alegacao(self, tmp_path):
        # Achado ao ler a semente inteira: os 9 documentos vNext abrem com um
        # titulo H1 terminado em "(Phase N)" -- marca de roadmap interno, nao
        # resultado medido. O padrao mora no FIM da linha, nao no comeco
        # (diferente de marcador de lista e numero de secao), entao precisa
        # de `search`, nao `match`, no mecanismo de mascaramento.
        doc = tmp_path / "TITULO.md"
        doc.write_text(
            "# SparkForge AWS — Canonical Agent & Skill Catalog vNext (Phase 4)\n",
            encoding="utf-8",
        )
        assert gate.extract_numbers(doc) == []

    def test_numero_de_fase_em_portugues_tambem_nao_vira_alegacao(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text("# Relatorio de Progresso (Fase 7)\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_numero_de_fase_nao_apaga_numero_real_no_resto_do_titulo(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text(
            "# Catalogo com 38 agentes permanentes (Phase 4)\n", encoding="utf-8"
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["38"]

    def test_fase_fora_do_titulo_h1_continua_sendo_alegacao(self, tmp_path):
        # Revisao de codigo: mutation test do reviewer provou que a versao
        # anterior do padrao (sem ancora de linha) mascarava "(Phase N)" em
        # QUALQUER posicao, nao so no titulo H1 que a razao do padrao alega.
        # "(Phase 3)" solto em prosa, fora de um titulo H1, nao e a mesma
        # coisa que a marca de roadmap do titulo -- pode ser uma referencia
        # real a algo que precisa provar -- entao precisa sobreviver.
        doc = tmp_path / "PROSA.md"
        doc.write_text(
            "Prosa comum mencionando (Phase 3) no meio do paragrafo.\n",
            encoding="utf-8",
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["3"]

    def test_fase_em_titulo_h2_nao_e_mascarada(self, tmp_path):
        # A razao do padrao fala especificamente de titulo H1 (uma
        # cerquilha) -- os 9 documentos reais so usam essa forma. Um titulo
        # H2 com o mesmo sufixo nao e o caso que o padrao foi desenhado para
        # cobrir, entao fica de fora da ancora deliberadamente.
        doc = tmp_path / "TITULO.md"
        doc.write_text("## Subsecao qualquer (Phase 3)\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["3"]

    def test_fase_no_meio_do_titulo_h1_nao_e_mascarada(self, tmp_path):
        # O padrao exige "(Phase N)" no FIM da linha (`\s*$`) -- a razao diz
        # "titulo H1 terminado em (Phase N)". Fase no meio do titulo, com
        # texto depois, nao bate o formato real do corpus e fica de fora.
        doc = tmp_path / "TITULO.md"
        doc.write_text(
            "# Relatorio (Phase 3) com revisao adicional\n", encoding="utf-8"
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["3"]

    def test_titulo_pontuado_em_subsecao_nao_vaza_digito(self, tmp_path):
        # Achado pelo reviewer: "## 4.5 Subsecao" so tinha "4." mascarado
        # pelo padrao antigo, deixando ".5" para tras e vazando "5" como
        # alegacao. Nenhum titulo assim existe no corpus hoje, mas o padrao
        # precisa aguentar o dia em que alguem adicionar numeracao "N.M".
        doc = tmp_path / "TITULO.md"
        doc.write_text("## 4.5 Subsecao com 12 itens\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["12"]

    def test_titulo_pontuado_com_tres_niveis_nao_vaza_digito(self, tmp_path):
        doc = tmp_path / "TITULO.md"
        doc.write_text("### 4.5.2 Sub-subsecao\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_titulo_pontuado_com_ponto_final_continua_mascarado_por_inteiro(
        self, tmp_path
    ):
        # Forma equivalente com ponto final apos o ultimo segmento -- o
        # `\.?` opcional no fim do padrao cobre esse caso sem duplicar regra.
        doc = tmp_path / "TITULO.md"
        doc.write_text("## 4.5. Subsecao pontuada\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_rotulo_tier_e_pruned(self, tmp_path):
        # Achado pelo reviewer: rotulo de indice de taxonomia (substantivo
        # ANTES do digito) indica qual item, nao quantidade.
        doc = tmp_path / "ROTULO.md"
        doc.write_text("`Tier 3` (Cheap / Local Model): descricao.\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_rotulo_layer_em_titulo_e_pruned(self, tmp_path):
        doc = tmp_path / "ROTULO.md"
        doc.write_text("### Layer 0: Deterministic Core\n", encoding="utf-8")
        assert gate.extract_numbers(doc) == []

    def test_rotulo_wave_e_demo_sao_pruned(self, tmp_path):
        doc = tmp_path / "ROTULO.md"
        doc.write_text(
            "- `Wave 0`: Discovery.\n## Demo 2: Pipeline CDC\n", encoding="utf-8"
        )
        assert gate.extract_numbers(doc) == []

    def test_quantidade_digito_antes_do_substantivo_continua_alegacao(self, tmp_path):
        # O eixo que decide: substantivo-entao-digito e rotulo (prune);
        # digito-entao-substantivo-plural e alegacao de quantidade (keep).
        # Caso real do corpus: "Cascata de 7 Tiers".
        doc = tmp_path / "QUANTIDADE.md"
        doc.write_text(
            "Motor de economia em 7 tiers, organizado em 3 waves e 12 layers.\n",
            encoding="utf-8",
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert set(textos) == {"7", "3", "12"}

    def test_rotulo_nao_apaga_numero_real_na_mesma_linha(self, tmp_path):
        doc = tmp_path / "ROTULO.md"
        doc.write_text("`Tier 3`: usa ate 40 mil tokens.\n", encoding="utf-8")
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        assert textos == ["40"]

    def test_todas_as_ocorrencias_de_rotulo_na_mesma_linha_sao_mascaradas(
        self, tmp_path
    ):
        # Regressao: caso real de COURSE-KNOWLEDGE-MAP.md:30 encadeia "Tier
        # 0 ... Tier 1 ... Tier 6" sete vezes na MESMA linha. Um mecanismo
        # de mascaramento que so trata a primeira ocorrencia por padrao
        # deixaria "Tier 1" a "Tier 6" vazando como alegacao -- a mesma
        # classe de falso negativo que toda esta suite existe para evitar.
        doc = tmp_path / "CASCATA.md"
        doc.write_text(
            "Execucao em 7 tiers: Tier 0 Deterministico (0 tokens) "
            "-> Tier 1 Cache -> Tier 2 Retrieval -> Tier 3 Cheap "
            "-> Tier 4 Specialist -> Tier 5 Premium -> Tier 6 Multi-Agent.\n",
            encoding="utf-8",
        )
        textos = [i["text"] for i in gate.extract_numbers(doc)]
        # Sobrevive so o que NAO e rotulo "Tier N": o "7" de "7 tiers" (
        # quantidade) e o "0" de "(0 tokens)" (quantidade). Os sete "Tier N"
        # (0 a 6) somem todos, nao so o primeiro.
        assert sorted(textos) == ["0", "7"]

    def test_fence_nao_fechado_estoura_com_nome_do_arquivo(self, tmp_path):
        doc = tmp_path / "FENCE_ABERTO.md"
        doc.write_text("Antes da cerca\n```python\nresto sem fechar\n", encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            gate.extract_numbers(doc)
        assert doc.name in str(exc_info.value)

    def test_doc_fora_da_raiz_usa_caminho_absoluto_posix(self, tmp_path):
        doc = tmp_path / "SINTETICO.md"
        doc.write_text(DOC_SINTETICO, encoding="utf-8")
        itens = gate.extract_numbers(doc)
        assert itens[0]["doc"] == doc.resolve().as_posix()
        assert "\\" not in itens[0]["doc"]


MATRIZ_SINTETICA = """# Matriz

| Capacidade | Estado |
|---|---|
| Compilador multi-plataforma | entregue |
| Motor de economia em 7 tiers | entregue |

Prosa solta afirmando coisas que nao sao linha de tabela.
"""


class TestExtracaoDeCapacidade:
    def test_le_a_primeira_celula_de_cada_linha_de_tabela(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert "Compilador multi-plataforma" in textos
        assert "Motor de economia em 7 tiers" in textos

    def test_ignora_cabecalho_separador_e_prosa(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert "Capacidade" not in textos
        assert not any(set(t) <= {"-", " ", ":"} for t in textos)
        assert not any(t.startswith("Prosa") for t in textos)

    def test_o_tipo_e_capability(self, tmp_path):
        (tmp_path / "AGENT-CATALOG.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        for claim in gate.extract_capabilities(tmp_path):
            assert claim["type"] == "capability"


# Fixture sintetico que reproduz a forma real de docs/vnext/FINAL-REPORT.md:
# secao "## 3." com lista solta (nao deve contar), secao "## 4." com
# subcabecalho "###" e itens de inventario (deve contar), e secao "## 5."
# com outro item de lista (nao deve contar por estar fora da secao 4).
RELATORIO_SINTETICO = """# Relatorio

## 3. KPIs e Resultados

- Nao e alegacao de capacidade, e so um item de metrica solta.

## 4. Inventario de Arquivos Criados e Estrutura

### Novos Pacotes e Modulos:
- [`sparkforge/registry/`](file:///e:/projetos/spark-forge-aws/sparkforge/registry/): registro
- [`sparkforge/economy/`](file:///e:/projetos/spark-forge-aws/sparkforge/economy/): economia

## 5. Suporte a Plataformas

- Nao deveria ser capturado, esta fora da secao 4.
"""


class TestExtracaoDeCapacidadeInventarioFinalReport:
    def test_item_dentro_da_secao_4_vira_alegacao_de_capacidade(self, tmp_path):
        (tmp_path / "FINAL-REPORT.md").write_text(RELATORIO_SINTETICO, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert any("sparkforge/registry" in t for t in textos)
        assert any("sparkforge/economy" in t for t in textos)
        for claim in gate.extract_capabilities(tmp_path):
            assert claim["type"] == "capability"

    def test_item_fora_da_secao_4_nao_vira_alegacao(self, tmp_path):
        (tmp_path / "FINAL-REPORT.md").write_text(RELATORIO_SINTETICO, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert not any("metrica solta" in t for t in textos)
        assert not any("fora da secao 4" in t for t in textos)


class TestExtracaoDeCapacidadeProsaNaoConta:
    def test_documento_fora_das_tres_fontes_estruturais_nao_contribui(self, tmp_path):
        # Nem CAPABILITY-MATRIX.md, nem AGENT-CATALOG.md, nem FINAL-REPORT.md --
        # mesmo com tabela e lista dentro, nao e fonte estrutural reconhecida.
        (tmp_path / "ALGUM-OUTRO.md").write_text(
            "- Isto parece item de lista mas nao esta em nenhuma das tres fontes.\n\n"
            "| Capacidade | Estado |\n|---|---|\n| Coisa | ok |\n",
            encoding="utf-8",
        )
        assert gate.extract_capabilities(tmp_path) == []


TABELA_CABECALHO_INCOMUM = """# Matriz

| Servico AWS | Estado |
|---|---|
| Glue | entregue |
"""


class TestCabecalhoDetectadoPorPosicao:
    def test_cabecalho_com_palavra_fora_de_qualquer_lista_e_ignorado(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(TABELA_CABECALHO_INCOMUM, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert textos == ["Glue"]

    def test_tabela_sem_linha_separadora_trata_toda_linha_como_dado(self, tmp_path):
        # Markdown malformado: sem a linha "|---|---|" nao ha ancora para
        # distinguir cabecalho de dado por posicao. Decisao deliberada:
        # tratar toda linha como dado (falso positivo eventual) em vez de
        # reintroduzir uma heuristica de vocabulario para adivinhar o
        # cabecalho -- essa heuristica e exatamente o que a Task 3 provou
        # ser fragil.
        tabela_sem_separador = (
            "# Tabela malformada\n\n| Servico AWS | Estado |\n| Glue | entregue |\n"
        )
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(tabela_sem_separador, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert textos == ["Servico AWS", "Glue"]


RELATORIO_ANCORA_RENUMERADA = RELATORIO_SINTETICO.replace(
    "## 4. Inventario de Arquivos Criados e Estrutura",
    "## 5. Inventario de Arquivos Criados e Estrutura",
).replace("## 5. Suporte a Plataformas", "## 6. Suporte a Plataformas")


class TestAncoraDeInventarioPerdidaEstouraAlto:
    def test_ancora_renumerada_estoura_value_error_nomeando_o_arquivo(self, tmp_path):
        doc = tmp_path / "FINAL-REPORT.md"
        doc.write_text(RELATORIO_ANCORA_RENUMERADA, encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            gate.extract_capabilities(tmp_path)
        assert doc.name in str(exc_info.value)

    def test_arquivo_ausente_nao_estoura_e_nao_contribui(self, tmp_path):
        # Documento inteiro ausente nao e a mesma falha que ancora perdida
        # dentro de um documento presente -- fixture sintetica sem
        # FINAL-REPORT.md e o caso normal de qualquer teste desta suite.
        assert gate.extract_capabilities(tmp_path) == []


MATRIZ_COM_TABELA_CERCADA = """# Matriz

Exemplo ilustrativo dentro de bloco cercado -- nao e alegacao real:
```
| Capacidade | Estado |
|---|---|
| Fantasma dentro da cerca | fake |
```

| Capacidade | Estado |
|---|---|
| Compilador real | entregue |
"""

RELATORIO_COM_LISTA_CERCADA = """# Relatorio

## 4. Inventario de Arquivos Criados e Estrutura

Exemplo ilustrativo dentro de bloco cercado -- nao e alegacao real:
```
- fantasma/dentro/da/cerca: nao deveria contar
```

- sparkforge/registry/: entrega real

## 5. Suporte a Plataformas
"""


class TestExtracaoDeCapacidadeRespeitaBlocoCercado:
    # `extract_numbers` ja passa por `_strip_code_blocks` antes de iterar;
    # `extract_capabilities` e `_final_report_inventory` faziam a leitura de
    # linha direto do texto cru, entao uma tabela ou item de lista dentro de
    # um bloco cercado (AGENT-CATALOG.md e FINAL-REPORT.md ja tem blocos
    # cercados hoje) virava alegacao real por acidente. Reusa a mesma cerca
    # em vez de reimplementar a varredura de linha pela terceira vez.
    def test_linha_de_tabela_dentro_de_cerca_nao_vira_capacidade(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(
            MATRIZ_COM_TABELA_CERCADA, encoding="utf-8"
        )
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert textos == ["Compilador real"]

    def test_item_de_lista_dentro_de_cerca_na_secao_4_nao_vira_capacidade(self, tmp_path):
        (tmp_path / "FINAL-REPORT.md").write_text(RELATORIO_COM_LISTA_CERCADA, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert textos == ["sparkforge/registry/: entrega real"]


RELATORIO_SECAO_4_COM_LISTA_NUMERADA = """# Relatorio

## 4. Inventario de Arquivos Criados e Estrutura

1. sparkforge/registry/: entrega do registro canonico
2. sparkforge/economy/: motor de economia em 7 tiers

## 5. Suporte a Plataformas
"""


class TestSecao4ComAncoraMasSemItemEstouraAlto:
    def test_lista_numerada_nao_reconhecida_estoura_value_error_nomeando_arquivo(
        self, tmp_path
    ):
        # Ancora "## 4." e encontrada, mas o extrator so reconhece marcador
        # "- ". Lista reescrita como "1. "/"2. " passa pela deteccao de
        # ancora sem erro e devolveria lista vazia -- o mesmo miss silencioso
        # que a guarda de ancora perdida existe para impedir, so que um
        # degrau adiante.
        doc = tmp_path / "FINAL-REPORT.md"
        doc.write_text(RELATORIO_SECAO_4_COM_LISTA_NUMERADA, encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            gate.extract_capabilities(tmp_path)
        assert doc.name in str(exc_info.value)


class TestLimiteUltimaLinhaSemQuebraFinal:
    def test_tabela_cuja_ultima_linha_e_dado_sem_newline_final(self, tmp_path):
        # Nada na suite exercitava lineno == len(lines) (ultima linha do
        # arquivo, sem "\n" final) -- o ponto exato onde o lookahead
        # `lines[lineno]` precisaria virar IndexError se a guarda
        # `lineno < len(lines)` estivesse errada.
        conteudo = "# Matriz\n\n| Capacidade | Estado |\n|---|---|\n| Ultima linha | ok |"
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(conteudo, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert textos == ["Ultima linha"]


def manifesto(claims):
    return {"schema_version": 1, "extracted_from": "0" * 40, "claims": claims}


def entrada(**kwargs):
    base = {
        "id": "VNX-001",
        "doc": "docs/vnext/FINAL-REPORT.md",
        "line": 31,
        "text": "81,8%",
        "context": "economia de 81,8%",
        "type": "number",
        "state": "REMOVIDA",
        "note": "sem artefato de medicao no repositorio",
    }
    base.update(kwargs)
    return base


class TestValidacaoDoManifesto:
    def test_aceita_manifesto_bem_formado(self):
        assert gate.validate_manifest(manifesto([entrada()]), {}) == []

    def test_exige_note_quando_nao_e_provada(self):
        erros = gate.validate_manifest(manifesto([entrada(note="")]), {})
        assert any("exige note" in e for e in erros)

    def test_rejeita_id_repetido(self):
        erros = gate.validate_manifest(manifesto([entrada(), entrada(text="94,5%")]), {})
        assert any("id repetido" in e for e in erros)

    def test_rejeita_estado_desconhecido(self):
        erros = gate.validate_manifest(manifesto([entrada(state="TALVEZ")]), {})
        assert any("state" in e for e in erros)

    def test_rejeita_proof_fora_de_provada(self):
        prova = {"kind": "source", "source_id": "x"}
        erros = gate.validate_manifest(manifesto([entrada(proof=prova)]), {})
        assert any("proof so e aceita em PROVADA" in e for e in erros)

    def test_rejeita_schema_version_diferente(self):
        m = manifesto([entrada()])
        m["schema_version"] = 2
        erros = gate.validate_manifest(m, {})
        assert any("schema_version" in e for e in erros)


class TestValidacaoDaProva:
    def test_artifact_nao_prova_numero(self):
        prova = {"kind": "artifact", "path": "scripts/check_vnext_claims.py",
                 "test": "tests/test_vnext_claims.py"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("artifact nao prova alegacao numerica" in e for e in erros)

    def test_artifact_prova_capacidade_quando_path_e_test_existem(self):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "symbol": "audited_docs",
            "test": "tests/test_vnext_claims.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert erros == []

    def test_artifact_com_path_inexistente_falha(self):
        prova = {"kind": "artifact", "path": "nao/existe.py",
                 "test": "tests/test_vnext_claims.py"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert any("proof.path inexistente" in e for e in erros)

    def test_artifact_cujo_teste_nao_cita_o_simbolo_falha(self):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "symbol": "funcao_que_ninguem_testa",
            "test": "tests/test_vnext_claims.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert any("nao referencia" in e for e in erros)

    def test_source_exige_id_presente_no_sources_lock(self):
        prova = {"kind": "source", "source_id": "https://exemplo/invalido"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="external_fact")]),
            {"https://exemplo/valido": {}},
        )
        assert any("fora de knowledge/sources.lock.json" in e for e in erros)

    def test_external_fact_so_aceita_source(self):
        prova = {"kind": "command", "cmd": 'python -c "print(1)"', "tier": "fast",
                 "expect": {"kind": "contains", "value": "1"}}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="external_fact")]), {}
        )
        assert any("external_fact exige proof source" in e for e in erros)

    def test_command_exige_tier_valido(self):
        prova = {"kind": "command", "cmd": 'python -c "print(1)"', "tier": "medio",
                 "expect": {"kind": "contains", "value": "1"}}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("tier" in e for e in erros)

    def test_artifact_path_absoluto_fora_do_repositorio_e_rejeitado(self):
        # `ROOT / valor` descarta ROOT quando `valor` ja e absoluto -- sem
        # esta checagem um path absoluto validaria com zero erros, mesmo
        # apontando para fora do repositorio inteiro.
        prova = {
            "kind": "artifact",
            "path": "C:/Windows/System32/drivers/etc/hosts",
            "test": "tests/test_vnext_claims.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert any("proof.path fora do repositorio" in e for e in erros)

    def test_artifact_test_com_travessia_de_diretorio_e_rejeitado(self):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "test": "../../elsewhere",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert any("proof.test fora do repositorio" in e for e in erros)

    def test_symbol_referenciado_por_qualificador_diferente_de_gate_e_aceito(self):
        # A checagem de referencia nao pode travar no alias `gate.` que este
        # proprio arquivo de teste usa -- a Task 9 vai anexar prova artifact
        # contra modulos importados sob qualquer alias. `tests/test_agents_
        # parity.py` importa `scripts/sync_skills.py` como `sync_skills` (sem
        # alias `gate`) e chama `sync_skills.platform_for(...)` de verdade --
        # caso real do repositorio, nao fixture sintetica.
        prova = {
            "kind": "artifact",
            "path": "scripts/sync_skills.py",
            "symbol": "platform_for",
            "test": "tests/test_agents_parity.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="capability")]), {}
        )
        assert erros == []

    def test_expect_number_sem_grupo_de_captura_e_rejeitado(self):
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(1)"',
            "tier": "fast",
            "expect": {"kind": "number", "pattern": r"\d+"},
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("grupo de captura" in e for e in erros)

    def test_expect_number_com_pattern_incompilavel_e_rejeitado(self):
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(1)"',
            "tier": "fast",
            "expect": {"kind": "number", "pattern": r"(\d+"},
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("expect.pattern invalido" in e for e in erros)

    def test_expect_contains_sem_value_e_rejeitado(self):
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(1)"',
            "tier": "fast",
            "expect": {"kind": "contains"},
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("expect contains exige value" in e for e in erros)

    def test_cmd_com_barra_invertida_e_rejeitado(self):
        # `shlex.split` trata `\` como escape POSIX em qualquer sistema --
        # inclusive nesta workstation Windows, onde a Task 9 digita `cmd` a
        # mao. `shlex.split(r"python scripts\check.py")` corrompe o caminho
        # em silencio (sem lancar excecao), entao a rejeicao precisa
        # acontecer aqui, na validacao do manifesto.
        prova = {
            "kind": "command",
            "cmd": r"python scripts\check_thing.py",
            "tier": "fast",
            "expect": {"kind": "contains", "value": "ok"},
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("barra normal" in e for e in erros)

    def test_expect_stream_invalido_e_rejeitado(self):
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(1)"',
            "tier": "fast",
            "expect": {"kind": "contains", "value": "1", "stream": "stdin"},
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", proof=prova, type="number")]), {}
        )
        assert any("expect.stream" in e for e in erros)


class TestOrfaos:
    def _achado(self, text="81,8%", doc="docs/vnext/FINAL-REPORT.md", line=1):
        return {"doc": doc, "line": line, "text": text, "context": "", "type": "number"}

    def test_alegacao_sem_entrada_no_manifesto_falha(self):
        erros = gate.check_orphans([self._achado()], manifesto([]))
        assert any("sem entrada no manifesto" in e for e in erros)

    def test_entrada_sem_alegacao_no_documento_falha(self):
        erros = gate.check_orphans([], manifesto([entrada(state="SEM_LASTRO", note="pendente")]))
        assert any("orfa no manifesto" in e for e in erros)

    def test_removida_nao_conta_como_orfa(self):
        erros = gate.check_orphans([], manifesto([entrada()]))
        assert erros == []

    def test_removida_que_reaparece_no_documento_falha(self):
        erros = gate.check_orphans([self._achado()], manifesto([entrada()]))
        assert any("REMOVIDA ainda aparece" in e for e in erros)

    def test_removida_que_reaparece_multiplas_vezes_reporta_contagem(self):
        # A ramificacao irma ("sem entrada no manifesto") ja reporta
        # ({count}x); esta ramificacao (REMOVIDA reaparecendo) precisa da
        # mesma contagem, senao reaparecer 1 vez ou 5 vezes le identico.
        achados = [self._achado(), self._achado(), self._achado()]
        erros = gate.check_orphans(achados, manifesto([entrada()]))
        msg = next(e for e in erros if "REMOVIDA ainda aparece" in e)
        assert "(3x)" in msg

    def test_mensagem_de_orfao_no_documento_lista_as_linhas_das_ocorrencias(self):
        achados = [self._achado(text="7", line=10), self._achado(text="7", line=45)]
        erros = gate.check_orphans(achados, manifesto([]))
        msg = next(e for e in erros if "sem entrada no manifesto" in e)
        assert "10" in msg
        assert "45" in msg

    def test_mensagem_de_entrada_orfa_usa_a_linha_do_manifesto(self):
        m = manifesto([entrada(state="SEM_LASTRO", note="pendente", line=77)])
        erros = gate.check_orphans([], m)
        msg = next(e for e in erros if "orfa no manifesto" in e)
        assert "77" in msg

    def test_alegacao_repetida_duas_vezes_no_documento_exige_duas_entradas(self):
        # Multiset: a mesma alegacao aparecendo duas vezes no mesmo documento
        # com apenas uma entrada no manifesto continua sendo alegacao sem
        # lastro -- comparar por conjunto (em vez de Counter) deixaria a
        # segunda ocorrencia passar batida.
        achados = [self._achado(), self._achado()]
        erros = gate.check_orphans(achados, manifesto([entrada(state="SEM_LASTRO", note="x")]))
        assert any("sem entrada no manifesto (1x)" in e for e in erros)

    def test_nada_orfao_quando_contagens_batem_dos_dois_lados(self):
        achados = [self._achado(), self._achado()]
        m = manifesto(
            [
                entrada(state="SEM_LASTRO", note="x"),
                entrada(state="SEM_LASTRO", note="y"),
            ]
        )
        assert gate.check_orphans(achados, m) == []


class TestColetaDeAlegacoes:
    def test_junta_numeros_e_capacidades_de_documento_sintetico(self, tmp_path):
        (tmp_path / "SINTETICO.md").write_text(DOC_SINTETICO, encoding="utf-8")
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        achados = gate.collect_claims(tmp_path)
        tipos = {a["type"] for a in achados}
        assert "number" in tipos
        assert "capability" in tipos

    def test_chave_ignora_linha_mas_nao_documento_tipo_ou_texto(self):
        a = {"doc": "d.md", "line": 1, "text": "81,8%", "type": "number"}
        b = {"doc": "d.md", "line": 99, "text": "81,8%", "type": "number"}
        assert gate.claim_key(a) == gate.claim_key(b)


class TestProvasCommand:
    def _com_prova(self, cmd, expect, tier="fast"):
        prova = {"kind": "command", "cmd": cmd, "tier": tier, "expect": expect}
        return manifesto([entrada(state="PROVADA", proof=prova, type="number")])

    def test_prova_que_reproduz_passa(self):
        m = self._com_prova(
            'python -c "print(41, \'tools\')"',
            {"kind": "number", "pattern": r"(\d+) tools", "value": 41},
        )
        assert gate.run_command_proofs(m, include_slow=False) == []

    def test_prova_que_nao_reproduz_falha_com_os_dois_valores(self):
        m = self._com_prova(
            'python -c "print(5447, \'tests\')"',
            {"kind": "number", "pattern": r"(\d+) tests", "value": 5485},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("esperado 5485, obtido 5447" in e for e in erros)

    def test_streams_concatenados_nao_fabricam_casamento(self):
        # Caso do reviewer: stdout escreve "4" e stderr escreve "1 tools",
        # sem separador nenhum entre eles. Concatenar os dois formaria
        # "41 tools", que bateria com o padrao `(\d+) tools` valor 41 mesmo
        # sem nenhum stream, sozinho, ter escrito "41 tools". A alegacao so
        # pode contar como provada se UM stream, isolado, satisfaz `expect`.
        m = self._com_prova(
            "python -c \"import sys; print('4', end=''); "
            "sys.stderr.write('1 tools')\"",
            {"kind": "number", "pattern": r"(\d+) tools", "value": 41},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert erros != []
        assert not any("prova command nao reproduz — esperado 41, obtido 41" in e for e in erros)

    def test_stream_nao_declarado_nao_aceita_valor_que_so_o_stderr_produziu(self):
        # Imagem espelhada do caso acima: stdout imprime a contagem REAL
        # (errada), stderr imprime uma mensagem de erro que por acidente
        # contem o numero esperado. Sem `expect.stream`, o default e stdout
        # -- aceitar "qualquer um dos dois streams que bater" faria stderr
        # provar a alegacao, mesmo a mensagem de erro nao sendo a fonte da
        # verdade da prova.
        m = self._com_prova(
            'python -c "import sys; print(\'50 tests\'); '
            "sys.stderr.write('unexpected error, expected around 100 tests to run')\"",
            {"kind": "number", "pattern": r"(\d+) tests", "value": 100},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("esperado 100, obtido 50" in e for e in erros)

    def test_expect_stream_stderr_declarado_confere_so_o_stderr(self):
        # Mesmo comando do teste acima, mas agora `expect.stream: "stderr"`
        # aponta explicitamente para onde a prova deve olhar -- o gate
        # confere SO esse stream, e o valor que ele carrega e aceito.
        m = self._com_prova(
            'python -c "import sys; print(\'50 tests\'); '
            "sys.stderr.write('unexpected error, expected around 100 tests to run')\"",
            {"kind": "number", "pattern": r"(\d+) tests", "value": 100, "stream": "stderr"},
        )
        assert gate.run_command_proofs(m, include_slow=False) == []

    def test_tier_slow_nao_roda_por_padrao(self):
        m = self._com_prova(
            "comando-que-nao-existe-em-lugar-nenhum",
            {"kind": "contains", "value": "nada"},
            tier="slow",
        )
        assert gate.run_command_proofs(m, include_slow=False) == []
        assert gate.run_command_proofs(m, include_slow=True) != []

    def test_prova_contains_que_passa(self):
        m = self._com_prova(
            'python -c "print(\'ola mundo\')"',
            {"kind": "contains", "value": "ola mundo"},
        )
        assert gate.run_command_proofs(m, include_slow=False) == []

    def test_prova_contains_que_falha(self):
        m = self._com_prova(
            'python -c "print(\'ola mundo\')"',
            {"kind": "contains", "value": "nao esta aqui"},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("saida nao contem" in e for e in erros)

    def test_comando_inexistente_reporta_erro_sem_estourar(self):
        # OSError (FileNotFoundError) quando o executavel nao existe -- o
        # gate precisa reportar isso como erro de auditoria, nao deixar a
        # excecao subir crua.
        m = self._com_prova(
            "comando-que-definitivamente-nao-existe-no-path",
            {"kind": "contains", "value": "x"},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("nao executou" in e for e in erros)

    def test_grupo_capturado_nao_inteiro_nao_estoura(self):
        # `_validate_proof` so garante que o pattern compila e tem grupo de
        # captura, nao que o grupo sempre casa com digitos -- um pattern que
        # captura texto nao numerico precisa virar erro de auditoria legivel,
        # nao ValueError cru subindo do `int()`.
        m = self._com_prova(
            'python -c "print(\'quarenta e um tools\')"',
            {"kind": "number", "pattern": r"(\w+) tools", "value": 41},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("nao e inteiro" in e for e in erros)


def _sources_file(tmp_path, sources=None):
    caminho = tmp_path / "sources.lock.json"
    caminho.write_text(json.dumps({"sources": sources or {}}), encoding="utf-8")
    return caminho


class TestSuperficie:
    def test_seed_produz_uma_entrada_por_alegacao_em_sem_lastro(self, tmp_path, monkeypatch):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "UM.md").write_text("Economia de 81,8% e 5.485 testes.\n", encoding="utf-8")
        destino = tmp_path / "claims.lock.json"
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados["schema_version"] == 1
        assert {c["state"] for c in dados["claims"]} == {"SEM_LASTRO"}
        assert [c["id"] for c in dados["claims"]] == ["VNX-001", "VNX-002"]

    def test_report_emite_uma_linha_por_alegacao(self, tmp_path, monkeypatch, capsys):
        destino = tmp_path / "claims.lock.json"
        destino.write_text(json.dumps(manifesto([entrada()])), encoding="utf-8")
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "VNX-001" in saida
        assert "REMOVIDA" in saida


class TestSeedMerge:
    """Reviewer (revisao de b6753d1, Critical 1 e 2): `--seed` sem merge
    renumerava tudo posicionalmente (uma alegacao nova no topo do documento
    deslocava o id de todas as outras) e a unica saida da guarda de
    classificacao era `--force`, que apagava as 342 entradas classificadas a
    mao inteiras. `seed()` agora funde por `claim_key` -- ids sao sticky, e
    a guarda de classificacao foi removida porque deixou de ter trabalho: um
    `--seed` sem `--force` nao arrisca mais nada que valha proteger.
    """

    def _doc(self, tmp_path, monkeypatch, texto):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "UM.md").write_text(texto, encoding="utf-8")
        destino = tmp_path / "claims.lock.json"
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        monkeypatch.setattr(gate, "MANIFEST", destino)
        return destino

    def test_reseed_preserva_id_estado_nota_e_prova_e_novo_ganha_id_acima_do_maximo(
        self, tmp_path, monkeypatch
    ):
        destino = self._doc(
            tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\nEconomia de 81,8%.\n"
        )
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        por_texto = {c["text"]: c for c in dados["claims"]}
        assert por_texto["38"]["id"] == "VNX-001"
        assert por_texto["81,8%"]["id"] == "VNX-002"

        # classificacao a mao (Task 9), simulada diretamente no arquivo --
        # o proprio `seed()` nunca escreve `state: PROVADA`.
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(38)"',
            "tier": "fast",
            "expect": {"kind": "number", "pattern": r"(\d+)", "value": 38},
        }
        for claim in dados["claims"]:
            if claim["text"] == "38":
                claim["state"] = "PROVADA"
                claim["note"] = "conferido"
                claim["proof"] = prova
            elif claim["text"] == "81,8%":
                claim["state"] = "REMOVIDA"
                claim["note"] = "numero fantasioso, removido do documento"
        destino.write_text(json.dumps(dados), encoding="utf-8")

        # Uma alegacao nova aparece no TOPO do documento -- sob numeracao
        # posicional (comportamento antigo) isso deslocaria o id de tudo
        # abaixo dela; sob merge por chave, os ids antigos nao se movem.
        (tmp_path / "UM.md").write_text(
            "Novo dado: 7 tabelas.\nSao 38 agentes no catalogo.\nEconomia de 81,8%.\n",
            encoding="utf-8",
        )
        assert gate.seed() == 0
        refeito = json.loads(destino.read_text(encoding="utf-8"))
        por_texto2 = {c["text"]: c for c in refeito["claims"]}

        assert por_texto2["38"]["id"] == "VNX-001"
        assert por_texto2["38"]["state"] == "PROVADA"
        assert por_texto2["38"]["note"] == "conferido"
        assert por_texto2["38"]["proof"] == prova
        assert por_texto2["81,8%"]["id"] == "VNX-002"
        assert por_texto2["81,8%"]["state"] == "REMOVIDA"
        assert por_texto2["81,8%"]["note"] == "numero fantasioso, removido do documento"

        # nova alegacao ganha id acima do maximo ja emitido -- nunca reaproveita
        assert por_texto2["7"]["id"] == "VNX-003"
        assert por_texto2["7"]["state"] == "SEM_LASTRO"

    def test_alegacao_sumida_do_documento_e_retida_e_reportada(
        self, tmp_path, monkeypatch, capsys
    ):
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["claims"][0]["state"] = "PROVADA"
        dados["claims"][0]["note"] = "conferido"
        dados["claims"][0]["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(json.dumps(dados), encoding="utf-8")

        # a alegacao some do documento (reescrito sem numero nenhum)
        (tmp_path / "UM.md").write_text("Nada de numerico por aqui.\n", encoding="utf-8")
        assert gate.seed() == 0
        saida = capsys.readouterr().out
        assert "sumida" in saida

        refeito = json.loads(destino.read_text(encoding="utf-8"))
        assert len(refeito["claims"]) == 1
        retida = refeito["claims"][0]
        assert retida["text"] == "38"
        assert retida["id"] == "VNX-001"
        assert retida["state"] == "PROVADA"
        assert retida["proof"] == {"kind": "source", "source_id": "x"}

        # o proximo `audit` (via `check_orphans`, ja testado em TestOrfaos)
        # reporta essa entrada retida como orfa -- nada fica silenciosamente
        # perdido nem silenciosamente escondido.
        erros = gate.check_orphans(gate.collect_claims(gate.VNEXT), refeito)
        assert any("orfa no manifesto" in e for e in erros)

    def test_chaves_duplicadas_casam_por_ordem_e_contagem(self, tmp_path, monkeypatch):
        # "3" aparece tres vezes na mesma linha -- mesma claim_key, contagem 3.
        destino = self._doc(
            tmp_path, monkeypatch, "Sao 3 tabelas, 3 colunas e 3 indices no total.\n"
        )
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        tres = [c for c in dados["claims"] if c["text"] == "3"]
        assert len(tres) == 3
        ids_originais = sorted(c["id"] for c in tres)

        # reseed sem nenhuma mudanca no documento: casamento por ordem e
        # contagem (fila FIFO por chave) precisa devolver exatamente os
        # mesmos tres ids, nao uma permutacao nem uma renumeracao.
        assert gate.seed() == 0
        refeito = json.loads(destino.read_text(encoding="utf-8"))
        tres2 = [c for c in refeito["claims"] if c["text"] == "3"]
        assert sorted(c["id"] for c in tres2) == ids_originais
        assert len(refeito["claims"]) == len(dados["claims"])

    def test_force_descarta_e_renumera_do_zero(self, tmp_path, monkeypatch):
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["claims"][0]["state"] = "PROVADA"
        dados["claims"][0]["note"] = "conferido"
        dados["claims"][0]["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(json.dumps(dados), encoding="utf-8")

        assert gate.seed(force=True) == 0
        refeito = json.loads(destino.read_text(encoding="utf-8"))
        assert refeito["claims"][0]["id"] == "VNX-001"
        assert refeito["claims"][0]["state"] == "SEM_LASTRO"
        assert "proof" not in refeito["claims"][0]

    def test_sem_manifesto_previo_gera_semente_normal(self, tmp_path, monkeypatch):
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        assert not destino.exists()
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados["claims"][0]["id"] == "VNX-001"
        assert dados["claims"][0]["state"] == "SEM_LASTRO"

    def test_manifesto_corrompido_com_classificacao_recusa_e_preserva_o_arquivo(
        self, tmp_path, monkeypatch, capsys
    ):
        # Reviewer (Critical, revisao de 87cef4a): antes desta correcao, um
        # manifesto EXISTENTE mas ilegivel (JSON truncado) caia para geracao
        # fresca em silencio -- exatamente a mesma assinatura de "descarta
        # tudo" que `--force` tem, so que sem a confirmacao explicita nem o
        # aviso que tornam `--force` seguro. Reproduzido contra o codigo
        # anterior (commit 87cef4a): `seed()` sem `--force` devolvia 0 e
        # reescrevia a entrada PROVADA como "1 nova(s)" SEM_LASTRO -- pior
        # que silencio, porque reporta uma entrada destruida como se fosse
        # nova. Agora `seed()` recusa: retorna nao-zero, imprime as duas
        # saidas reais (restaurar via git, ou `--force` de proposito), e o
        # arquivo no disco fica byte-a-byte identico ao que a tentativa
        # encontrou.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["claims"][0]["state"] = "PROVADA"
        dados["claims"][0]["note"] = "conferido"
        dados["claims"][0]["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(json.dumps(dados), encoding="utf-8")
        antes = destino.read_bytes()

        # trunca o arquivo pela metade -- simula crash no meio da escrita,
        # arquivo travado, editor que salvou parcialmente, etc.
        destino.write_bytes(antes[: len(antes) // 2])
        truncado = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        # nada foi reescrito por cima do dano -- o arquivo continua
        # exatamente como a tentativa de seed o encontrou.
        assert destino.read_bytes() == truncado

    def test_manifesto_corrompido_com_force_descarta_e_renumera(self, tmp_path, monkeypatch):
        # Mesma configuracao do teste acima, mas com `--force`: essa e a
        # unica forma legitima de descartar um manifesto ilegivel -- ja
        # funcionava assim antes desta correcao (o caminho `force` nunca
        # tentava ler o arquivo existente) e continua funcionando depois.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["claims"][0]["state"] = "PROVADA"
        dados["claims"][0]["note"] = "conferido"
        dados["claims"][0]["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(json.dumps(dados), encoding="utf-8")
        antes = destino.read_bytes()
        destino.write_bytes(antes[: len(antes) // 2])

        assert gate.seed(force=True) == 0
        refeito = json.loads(destino.read_text(encoding="utf-8"))
        assert refeito["claims"][0]["id"] == "VNX-001"
        assert refeito["claims"][0]["state"] == "SEM_LASTRO"

    def _classificar(self, destino):
        """Semente + uma entrada classificada PROVADA a mao, devolvendo os
        bytes do arquivo classificado (o "antes" que a recusa precisa
        preservar byte a byte)."""
        gate.seed()
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["claims"][0]["state"] = "PROVADA"
        dados["claims"][0]["note"] = "conferido"
        dados["claims"][0]["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(json.dumps(dados), encoding="utf-8")
        return destino.read_bytes()

    def test_manifesto_com_chave_claims_ausente_recusa_e_preserva_o_arquivo(
        self, tmp_path, monkeypatch, capsys
    ):
        # Reviewer (Critical, round 4): JSON valido, objeto valido, so falta
        # a chave `claims` -- `load_manifest().get("claims", [])` nunca
        # levanta pra esse caso (chave ausente nao e erro de parse), entao a
        # recusa da correcao anterior nunca disparava aqui. Reproduzido
        # contra o codigo anterior (commit 06fa17c): `seed()` sem `--force`
        # devolvia 0 e reescrevia a entrada PROVADA como "1 nova(s)"
        # SEM_LASTRO -- a mesma perda de classificacao do bug anterior, um
        # passo ao lado do que a correcao anterior cobriu.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        self._classificar(destino)

        # sobrescreve com JSON valido, objeto valido, sem a chave `claims`
        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "abc"}), encoding="utf-8"
        )
        sem_claims = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == sem_claims

    def test_manifesto_com_claims_de_tipo_errado_recusa_sem_traceback(
        self, tmp_path, monkeypatch, capsys
    ):
        # Vizinho mapeado pelo reviewer: `claims` presente mas nao e lista
        # (aqui, uma string) crashava com `TypeError` cru antes de escrever
        # qualquer coisa -- seguro quanto a nao perder dado, mas uma
        # experiencia ruim pra quem roda o comando. A mesma checagem de
        # forma que fecha o buraco da chave ausente converte este caso na
        # mesma recusa amigavel, com a mesma mensagem de duas saidas.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        self._classificar(destino)

        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "abc", "claims": "oops"}),
            encoding="utf-8",
        )
        malformado = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == malformado

    def test_manifesto_top_level_lista_recusa_sem_traceback(
        self, tmp_path, monkeypatch, capsys
    ):
        # Outro vizinho mapeado pelo reviewer: JSON top-level e uma lista,
        # nao um objeto -- crashava com `AttributeError` cru (`'list' object
        # has no attribute 'get'`) antes desta correcao. Mesma recusa
        # amigavel agora.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        self._classificar(destino)

        destino.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        lista_top_level = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == lista_top_level

    def test_manifesto_com_claims_vazia_de_verdade_faz_reseed_normal_sem_force(
        self, tmp_path, monkeypatch
    ):
        # Correcao ao reviewer: `"claims": []` NAO e a mesma coisa que
        # `claims` ausente. Uma lista vazia e um manifesto legitimo sem nada
        # para perder -- e exatamente o que este `seed` escreve para um
        # conjunto de documentos sem nenhuma alegacao. Recusar aqui quebraria
        # reseed legitimo; este teste existe para que ninguem aperte demais
        # a checagem de forma mais tarde e transforme isso num falso
        # positivo.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "abc", "claims": []}),
            encoding="utf-8",
        )

        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert [c["id"] for c in dados["claims"]] == ["VNX-001"]
        assert dados["claims"][0]["state"] == "SEM_LASTRO"

    def test_null_dentro_de_claims_recusa_sem_traceback_e_preserva_o_arquivo(
        self, tmp_path, monkeypatch, capsys
    ):
        # Reviewer (round 5): entrada malformada DENTRO da lista `claims`
        # (nao a lista em si -- um item dela) crashava com `TypeError` cru
        # antes desta correcao, porque a checagem de forma so olha o nivel
        # de fora ("claims e uma lista?"), nao o que tem dentro. Reproduzido
        # contra o codigo anterior (commit 837849c): `claim_key(None)`
        # estoura `TypeError: 'NoneType' object is not subscriptable` no
        # meio do laco de merge, sem nada escrito (a escrita so acontece no
        # fim de `seed`) mas tambem sem a recusa amigavel. O `except
        # Exception` que envolve o laco inteiro converte isso na mesma
        # recusa de duas saidas.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        self._classificar(destino)
        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "x", "claims": [None]}),
            encoding="utf-8",
        )
        malformado = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == malformado

    def test_entrada_nao_dict_dentro_de_claims_recusa_sem_traceback(
        self, tmp_path, monkeypatch, capsys
    ):
        # Vizinho mapeado pelo reviewer: item de `claims` que e string em vez
        # de objeto. Contra o codigo anterior: `TypeError: string indices
        # must be integers, not 'str'` cru. Mesma recusa agora.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        self._classificar(destino)
        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "x", "claims": ["oops"]}),
            encoding="utf-8",
        )
        malformado = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == malformado

    def test_entrada_casada_sem_id_recusa_sem_traceback(self, tmp_path, monkeypatch, capsys):
        # Terceiro vizinho mapeado pelo reviewer: a entrada e um dict valido
        # e CASA por `claim_key` (tem doc/type/text) mas nao tem `id` --
        # `claim_key()` sozinho nao usa `id`, entao a entrada passa pela
        # indexacao por chave sem erro; o `KeyError: 'id'` cru so acontecia
        # depois, quando o merge tenta copiar `antiga["id"]` para a entrada
        # fresca que casou. Contra o codigo anterior isso tambem crashava
        # cru. Mesma recusa agora.
        destino = self._doc(tmp_path, monkeypatch, "Sao 38 agentes no catalogo.\n")
        gate.seed()
        dados = json.loads(destino.read_text(encoding="utf-8"))
        sem_id = dict(dados["claims"][0])
        sem_id.pop("id")
        sem_id["state"] = "PROVADA"
        sem_id["note"] = "conferido"
        sem_id["proof"] = {"kind": "source", "source_id": "x"}
        destino.write_text(
            json.dumps({"schema_version": 1, "extracted_from": "x", "claims": [sem_id]}),
            encoding="utf-8",
        )
        malformado = destino.read_bytes()

        assert gate.seed() != 0
        saida = capsys.readouterr().out
        assert "--force" in saida
        assert "git checkout" in saida
        assert destino.read_bytes() == malformado


class TestSeedIdEstouraFormato:
    """Judgment call 1: alem de 999 alegacoes o id `VNX-NNN` nao cabe mais
    em tres digitos -- a falha precisa ser um erro visivel na geracao, nao
    um id malformado escrito em silencio."""

    def test_mais_de_999_alegacoes_estoura_em_vez_de_gerar_id_malformado(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        destino = tmp_path / "claims.lock.json"
        monkeypatch.setattr(gate, "MANIFEST", destino)
        fabricadas = [
            {"doc": "d.md", "line": i, "text": str(i), "context": "", "type": "number"}
            for i in range(1000)
        ]
        monkeypatch.setattr(gate, "collect_claims", lambda root: fabricadas)
        with pytest.raises(ValueError) as exc_info:
            gate.seed()
        assert "999" in str(exc_info.value)
        assert not destino.exists()


class TestAuditoria:
    def _prep(self, tmp_path, monkeypatch, doc_text="Sao 38 agentes no catalogo.\n"):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "UM.md").write_text(doc_text, encoding="utf-8")
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        destino = tmp_path / "claims.lock.json"
        monkeypatch.setattr(gate, "MANIFEST", destino)
        monkeypatch.setattr(gate, "SOURCES_LOCK", _sources_file(tmp_path))
        return destino

    def test_manifesto_ausente_orienta_a_rodar_seed(self, tmp_path, monkeypatch, capsys):
        destino = self._prep(tmp_path, monkeypatch)
        assert not destino.exists()
        assert gate.audit(include_slow=False) == 1
        saida = capsys.readouterr().out
        assert "--seed" in saida

    def test_manifesto_com_json_invalido_reporta_erro_legivel(self, tmp_path, monkeypatch, capsys):
        destino = self._prep(tmp_path, monkeypatch)
        destino.write_text("{isso nao e json", encoding="utf-8")
        assert gate.audit(include_slow=False) == 1
        saida = capsys.readouterr().out
        assert "JSON" in saida

    def test_manifesto_consistente_retorna_0(self, tmp_path, monkeypatch):
        destino = self._prep(tmp_path, monkeypatch)
        achados = gate.collect_claims(gate.VNEXT)
        claims = [
            {**item, "id": f"VNX-{i:03d}", "state": "SEM_LASTRO", "note": "pendente"}
            for i, item in enumerate(achados, start=1)
        ]
        destino.write_text(json.dumps(manifesto(claims)), encoding="utf-8")
        assert gate.audit(include_slow=False) == 0

    def test_manifesto_inconsistente_retorna_1_e_imprime_divergencia(
        self, tmp_path, monkeypatch, capsys
    ):
        destino = self._prep(tmp_path, monkeypatch)
        destino.write_text(json.dumps(manifesto([])), encoding="utf-8")
        assert gate.audit(include_slow=False) == 1
        saida = capsys.readouterr().out
        assert "sem entrada no manifesto" in saida
        assert "divergencia" in saida

    def test_pula_provas_command_quando_ha_erro_estrutural(self, tmp_path, monkeypatch, capsys):
        # Reviewer (Important 4): id duplicado e um erro que `validate_
        # manifest` acusa instantaneamente -- nao deveria custar um
        # subprocesso para reportar.
        destino = self._prep(
            tmp_path, monkeypatch, doc_text="Sao 38 agentes no catalogo e 12 skills.\n"
        )
        achados = gate.collect_claims(gate.VNEXT)
        assert len(achados) >= 2
        claims = [
            {**item, "id": "VNX-001", "state": "SEM_LASTRO", "note": "pendente"}
            for item in achados
        ]  # todas com o mesmo id -> "id repetido"
        destino.write_text(json.dumps(manifesto(claims)), encoding="utf-8")

        chamadas = []
        monkeypatch.setattr(
            gate,
            "run_command_proofs",
            lambda *a, **k: (chamadas.append(1), ["prova nao deveria ter rodado"])[1],
        )
        assert gate.audit(include_slow=False) == 1
        assert chamadas == []
        saida = capsys.readouterr().out
        assert "id repetido" in saida
        assert "prova nao deveria ter rodado" not in saida
        assert "NAO executadas" in saida

    def test_executa_provas_command_quando_manifesto_e_estruturalmente_valido(
        self, tmp_path, monkeypatch, capsys
    ):
        destino = self._prep(tmp_path, monkeypatch)
        achados = gate.collect_claims(gate.VNEXT)
        claims = [
            {**item, "id": f"VNX-{i:03d}", "state": "SEM_LASTRO", "note": "pendente"}
            for i, item in enumerate(achados, start=1)
        ]
        claims[0]["state"] = "PROVADA"
        claims[0]["proof"] = {
            "kind": "command",
            "cmd": 'python -c "print(1)"',
            "tier": "fast",
            "expect": {"kind": "contains", "value": "nao esta na saida"},
        }
        destino.write_text(json.dumps(manifesto(claims)), encoding="utf-8")
        assert gate.audit(include_slow=False) == 1
        saida = capsys.readouterr().out
        assert "saida nao contem" in saida
        assert "NAO executadas" not in saida


class TestRelatorioComPipeNoTexto:
    """Judgment call 4 (Task 7) / Critical 3 (revisao): prova
    `command`/`artifact`/`source` embute texto do manifesto (cmd, path,
    source_id) que pode conter `|` e fragmentar a tabela Markdown gerada."""

    def test_pipe_na_prova_nao_fragmenta_a_linha_da_tabela(self, tmp_path, monkeypatch, capsys):
        destino = tmp_path / "claims.lock.json"
        prova = {
            "kind": "command",
            "cmd": "python -c \"print('a|b')\"",
            "tier": "fast",
            "expect": {"kind": "contains", "value": "a|b"},
        }
        destino.write_text(
            json.dumps(manifesto([entrada(state="PROVADA", proof=prova, type="number")])),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        linha = next(
            linha_candidata
            for linha_candidata in capsys.readouterr().out.splitlines()
            if linha_candidata.startswith("| VNX-001")
        )
        import re as _re

        delimitadores = _re.findall(r"(?<!\\)\|", linha)
        # 7 colunas de dado (id, documento, tipo, texto, estado, prova,
        # motivo) == 8 pipes delimitadores nao escapados (bordas + 6
        # separadores internos); um `|` cru vindo do cmd empurraria essa
        # contagem para cima.
        assert len(delimitadores) == 8
        assert "a\\|b" in linha


class TestRelatorioColunas:
    """Critical 3 (revisao): sem `texto` um leitor de LASTRO.md nao sabe o
    QUE esta sendo alegado; sem `motivo` nao sabe POR QUE algo e REMOVIDA.
    Cobre tambem os dois ramos de prova (`artifact`, `source`) que a
    revisao apontou sem teste nenhum."""

    def test_removida_mostra_texto_e_nota(self, tmp_path, monkeypatch, capsys):
        destino = tmp_path / "claims.lock.json"
        destino.write_text(json.dumps(manifesto([entrada()])), encoding="utf-8")
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "81,8%" in saida
        assert "sem artefato de medicao no repositorio" in saida

    def test_prova_artifact_renderiza(self, tmp_path, monkeypatch, capsys):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "test": "tests/test_vnext_claims.py",
        }
        destino = tmp_path / "claims.lock.json"
        destino.write_text(
            json.dumps(
                manifesto([entrada(state="PROVADA", proof=prova, type="capability")])
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "artifact" in saida
        assert "scripts/check_vnext_claims.py" in saida

    def test_prova_source_renderiza(self, tmp_path, monkeypatch, capsys):
        prova = {
            "kind": "source",
            "source_id": "https://docs.aws.amazon.com/glue/latest/dg/release-notes-5-1.html",
        }
        destino = tmp_path / "claims.lock.json"
        destino.write_text(
            json.dumps(
                manifesto([entrada(state="PROVADA", proof=prova, type="external_fact")])
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "source" in saida
        assert "release-notes-5-1" in saida

    def test_prova_command_sem_cmd_nao_imprime_none(self, tmp_path, monkeypatch, capsys):
        # Minor 7: campo de prova ausente nao pode virar a string literal
        # "None" na tabela.
        prova = {"kind": "command", "tier": "fast", "expect": {"kind": "contains", "value": "x"}}
        destino = tmp_path / "claims.lock.json"
        destino.write_text(
            json.dumps(manifesto([entrada(state="PROVADA", proof=prova, type="number")])),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "None" not in saida
        assert "sem cmd" in saida

    def test_cmd_com_crase_nao_quebra_o_code_span(self, tmp_path, monkeypatch, capsys):
        # Minor 6: `_md_cell` nao escapava crase, e `report()` envolve
        # cmd/path/source_id em crase -- um valor com crase quebrava o span.
        prova = {
            "kind": "command",
            "cmd": "python -c \"print('a`b')\"",
            "tier": "fast",
            "expect": {"kind": "contains", "value": "a`b"},
        }
        destino = tmp_path / "claims.lock.json"
        destino.write_text(
            json.dumps(manifesto([entrada(state="PROVADA", proof=prova, type="number")])),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        linha = next(
            linha_candidata
            for linha_candidata in saida.splitlines()
            if linha_candidata.startswith("| VNX-001")
        )
        # delimitador precisa ser mais longo que a maior corrida de crases
        # dentro do valor (uma crase == corrida de 1) -- crase dupla.
        assert "``" in linha


class TestHeadCommit:
    """Important 5 (revisao): `_head_commit()` caia para 'desconhecido' em
    silencio quando o git falha -- nenhum aviso, nenhum teste sequer no
    caminho feliz."""

    def test_caminho_feliz_devolve_o_sha_sem_aviso(self, monkeypatch, capsys):
        def fake_run(*args, **kwargs):
            return types.SimpleNamespace(stdout="abc123def\n", stderr="", returncode=0)

        monkeypatch.setattr(gate.subprocess, "run", fake_run)
        assert gate._head_commit() == "abc123def"
        assert capsys.readouterr().err == ""

    def test_git_indisponivel_cai_para_desconhecido_com_aviso_no_stderr(
        self, monkeypatch, capsys
    ):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError("git nao encontrado")

        monkeypatch.setattr(gate.subprocess, "run", fake_run)
        assert gate._head_commit() == "desconhecido"
        erro = capsys.readouterr().err
        assert "aviso" in erro
        assert "desconhecido" in erro

    def test_stdout_vazio_cai_para_desconhecido_com_aviso_no_stderr(self, monkeypatch, capsys):
        def fake_run(*args, **kwargs):
            return types.SimpleNamespace(
                stdout="", stderr="fatal: not a git repository", returncode=128
            )

        monkeypatch.setattr(gate.subprocess, "run", fake_run)
        assert gate._head_commit() == "desconhecido"
        erro = capsys.readouterr().err
        assert "aviso" in erro


class TestGateReal:
    def test_o_manifesto_do_repositorio_esta_consistente(self):
        manifest = gate.load_manifest()
        assert gate.validate_manifest(manifest, gate._load_sources()) == []
        assert gate.check_orphans(gate.collect_claims(), manifest) == []

    def test_nenhuma_alegacao_ficou_pendente(self):
        estados = {c["state"] for c in gate.load_manifest()["claims"]}
        assert "SEM_LASTRO" not in estados

    def test_alegacao_reintroduzida_no_documento_derruba_o_gate(self, tmp_path, monkeypatch):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "NOVO.md").write_text("Ganho de 99,9% em tudo.\n", encoding="utf-8")
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        erros = gate.check_orphans(gate.collect_claims(tmp_path), manifesto([]))
        assert any("sem entrada no manifesto" in e for e in erros)

    def test_o_gate_roda_no_ci(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "scripts/check_vnext_claims.py" in ci

    def test_alegacao_removida_reintroduzida_no_documento_real_derruba_o_gate(
        self, tmp_path, monkeypatch
    ):
        # Os quatro testes acima nao provam a garantia central deste gate:
        # que texto REMOVIDO pelo audit e reintroduzido no documento REAL
        # (nao numa fixture sintetica que nunca existiu) derruba o CI. Uma
        # fixture sintetica so prova que o mecanismo de deteccao funciona no
        # vacuo -- nao que ele enxerga o corpus real, com a mesma allowlist e
        # os mesmos padroes estruturais (Tier/Layer/Wave/Demo, titulo
        # numerado, marcador de lista) que ja escondem numero de verdade
        # hoje. A entrada REMOVIDA e escolhida por PROGRAMA, nao por id
        # fixo -- um id copiado para dentro do teste apodrece do mesmo jeito
        # que um numero copiado apodreceria: o corpus muda (Task 9 ainda
        # pode reclassificar), o teste nao pode travar num ponto congelado
        # dele. Restringe a `type: number`: reintroduzir uma alegacao de
        # capacidade exigiria reconstruir a estrutura de tabela ou item de
        # inventario que `extract_capabilities` exige -- fora do escopo
        # desta garantia, que ja fica provada reintroduzindo um numero.
        manifest = gate.load_manifest()
        removida = next(
            c
            for c in manifest["claims"]
            if c["state"] == "REMOVIDA" and c["type"] == "number"
        )

        copia = tmp_path / "vnext"
        shutil.copytree(ROOT / "docs" / "vnext", copia)

        # `_display_path` cai para caminho absoluto quando o documento nao
        # esta sob ROOT (o caso da copia em tmp_path) -- sem remapear o
        # campo `doc` do manifesto para o mesmo formato, `claim_key` nunca
        # bateria e o teste provaria a coisa errada (chave sempre
        # desencontrada dos dois lados, nao o mecanismo de REMOVIDA
        # reaparecendo).
        def remapeia(doc: str) -> str:
            rel_path = Path(doc).relative_to("docs/vnext")
            return (copia / rel_path).resolve().as_posix()

        manifesto_remapado = {
            **manifest,
            "claims": [dict(c, doc=remapeia(c["doc"])) for c in manifest["claims"]],
        }

        alvo = copia / Path(removida["doc"]).relative_to("docs/vnext")
        alvo.write_text(
            alvo.read_text(encoding="utf-8")
            + f"\nTexto reintroduzido de proposito: {removida['text']} de novo.\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(gate, "VNEXT", copia)
        achados = gate.collect_claims(copia)
        erros = gate.check_orphans(achados, manifesto_remapado)
        assert any("REMOVIDA ainda aparece" in e for e in erros)

    def test_prova_command_que_para_de_reproduzir_derruba_a_alegacao_provada(self):
        # Simetria com o teste acima: uma alegacao PROVADA nao e prova para
        # sempre -- o comando que a sustenta pode mudar de saida (codigo
        # editado, contagem que se moveu) sem que ninguem toque o manifesto.
        # `run_command_proofs` e o mecanismo que capta isso; testa-lo aqui,
        # dentro de TestGateReal, amarra a garantia ao caminho que o CI
        # realmente exercita (`audit()` chama esta mesma funcao), nao so ao
        # unitario isolado que `TestProvasCommand` ja cobre em separado.
        prova = {
            "kind": "command",
            "cmd": 'python -c "print(41)"',
            "tier": "fast",
            "expect": {"kind": "number", "pattern": r"(\d+)", "value": 999},
        }
        manifest = manifesto([entrada(state="PROVADA", proof=prova, type="number")])
        erros = gate.run_command_proofs(manifest, include_slow=False)
        assert any("esperado 999" in e and "obtido 41" in e for e in erros)
