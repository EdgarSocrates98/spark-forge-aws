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

    def test_cada_padrao_da_allowlist_declara_a_razao(self):
        for _, razao in gate.IGNORED_TOKENS:
            assert razao and len(razao) > 10

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
