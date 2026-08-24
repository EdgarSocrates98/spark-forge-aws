"""Secao 40 e 76: classe de tool DERIVADA, e autorizacao com cadeia.

A classificacao nao e uma segunda lista mantida a mao. As anotacoes MCP de cada
tool ja carregam as tres dimensoes que a definem -- `readOnlyHint`,
`openWorldHint`, `destructiveHint` --, e derivar delas e a mesma disciplina de
`coordinators_by_skill()`: a relacao vem do que ja esta declarado, e nao de uma
tabela paralela que cresce em desacordo com a primeira.
"""
from __future__ import annotations

import pytest

from sparkforge.adapters.tools import TOOLS
from sparkforge.agents.autonomy import (
    AuthorizationDecision,
    ToolClass,
    authorize,
    tool_class,
)
from sparkforge.registry.models import ExecutionProfile

UMA_LEITURA_LOCAL = "sparkforge_analyze_pyspark"
UMA_DE_REDE = "sparkforge_collect_glue_job"
UMA_MUTACAO_LOCAL = "sparkforge_case_open"


def catalogo_falso(monkeypatch, **anotacoes_por_tool):
    """Substitui `TOOLS` por um catalogo sintetico.

    Existe porque duas das cinco classes nao tem tool nenhuma no catalogo real
    (medido: `CLOUD_READ` e `DESTRUCTIVE` estao vazias), e o codigo que
    classifica uma tool destrutiva e justamente o que vai rodar primeiro no dia
    em que a primeira entrar. Cobrir so o que existe hoje deixaria esse ramo
    sem teste ate o dia em que ele importar.

    Funciona porque `tool_class()` importa `TOOLS` em tempo de CHAMADA, e nao
    no topo do modulo -- ver a docstring dela.
    """
    falso = {
        nome: {"annotations": dict(anotacoes)}
        for nome, anotacoes in anotacoes_por_tool.items()
    }
    monkeypatch.setattr("sparkforge.adapters.tools.TOOLS", falso)
    return falso


class TestClasseDerivadaDaAnotacao:
    @pytest.mark.parametrize("nome", sorted(TOOLS))
    def test_toda_tool_tem_classe(self, nome):
        assert isinstance(tool_class(nome), ToolClass)

    def test_a_classe_vem_da_anotacao_e_nao_de_uma_lista(self):
        """Se alguem trocar a anotacao de uma tool, a classe TEM que mudar
        junto. Uma lista paralela nao mudaria, e o desacordo seria mudo."""
        leitura_local = [
            n
            for n, t in TOOLS.items()
            if t["annotations"]["readOnlyHint"] and not t["annotations"]["openWorldHint"]
        ]
        assert leitura_local, "o corpus precisa ter ao menos uma tool de leitura local"
        assert {tool_class(n) for n in leitura_local} == {ToolClass.READ_ONLY}

    def test_trocar_a_anotacao_troca_a_classe(self, monkeypatch):
        """A afirmacao acima, exercitada em vez de so declarada.

        O teste irmao observa o corpus e confirma que a relacao VALE hoje; ele
        nao consegue distinguir uma derivacao de uma tabela paralela que por
        acaso concorda. Este troca a anotacao da MESMA tool quatro vezes e
        cobra que a classe acompanhe -- e o unico jeito de a docstring virar
        verdade."""
        esperado = {
            (True, False): ToolClass.READ_ONLY,
            (True, True): ToolClass.CLOUD_READ,
            (False, False): ToolClass.LOCAL_MUTATION,
            (False, True): ToolClass.CLOUD_MUTATION,
        }
        for (somente_leitura, de_nuvem), classe in esperado.items():
            catalogo_falso(
                monkeypatch,
                tool_sintetica={
                    "readOnlyHint": somente_leitura,
                    "openWorldHint": de_nuvem,
                    "destructiveHint": False,
                },
            )
            assert tool_class("tool_sintetica") is classe, (somente_leitura, de_nuvem)

    def test_destructive_vence_as_outras_duas_dimensoes(self, monkeypatch):
        """`DESTRUCTIVE` nao tem membro no catalogo de hoje, e por isso mesmo
        precisa de teste: o ramo so roda de verdade no dia em que a primeira
        tool destrutiva entrar, e ai nao ha ninguem olhando."""
        catalogo_falso(
            monkeypatch,
            tool_sintetica={
                "readOnlyHint": True,
                "openWorldHint": False,
                "destructiveHint": True,
            },
        )
        assert tool_class("tool_sintetica") is ToolClass.DESTRUCTIVE

    def test_tool_de_rede_nao_e_classificada_como_leitura_local(self):
        """Afirma o que o nome promete, e nada alem.

        A versao anterior cobrava igualdade exata com `{CLOUD_READ}`, o que
        quebraria sozinho na primeira tool de escrita na nuvem legitima --
        transformar adicao correta em teste vermelho e como um teste ensina a
        equipe a ignora-lo. O invariante real e mais fraco e mais duravel: sair
        para a rede tira a tool de `READ_ONLY`."""
        de_nuvem = [n for n, t in TOOLS.items() if t["annotations"]["openWorldHint"]]
        assert de_nuvem, "o corpus precisa ter ao menos uma tool de nuvem"
        classes = {tool_class(n) for n in de_nuvem}
        assert ToolClass.READ_ONLY not in classes
        assert ToolClass.LOCAL_MUTATION not in classes

    def test_tool_desconhecida_falha_fechada(self):
        """Nome que nao esta no catalogo de tools nao vira READ_ONLY por
        default. Default permissivo para o desconhecido e como uma tool nova
        entra sem classe."""
        with pytest.raises(KeyError):
            tool_class("sparkforge_tool_que_nao_existe")


class TestCadeiaDeAutorizacao:
    def test_leitura_local_e_autorizada_sem_aprovacao(self):
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(),
        )
        assert isinstance(decisao, AuthorizationDecision)
        assert decisao.authorized is True
        assert decisao.tool_class is ToolClass.READ_ONLY
        assert decisao.required_approval is None

    def test_a_decisao_nomeia_quem_autorizou_e_sob_qual_perfil(self):
        """E isto que separa cadeia de checagem de um nivel: a decisao carrega
        o perfil e a aprovacao que a sustentou, entao um trace consegue
        responder 'quem permitiu isso, e com base em que'."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(),
        )
        assert decisao.agent == "sf-runtime-specialist"
        assert decisao.profile is ExecutionProfile.ECO

    def test_tool_fora_da_allowlist_do_agente_e_recusada(self):
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(),
        )
        assert decisao.authorized is False
        assert "allowlist" in decisao.reason

    def test_mutacao_local_exige_aprovacao_nomeada(self):
        decisao = authorize(
            agent="sf-orchestrator",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_MUTACAO_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(),
        )
        assert decisao.authorized is False
        assert decisao.required_approval is ToolClass.LOCAL_MUTATION

    def test_a_aprovacao_e_por_classe_e_nao_um_booleano_global(self):
        """Aprovar mutacao local NAO aprova escrita na nuvem. Um booleano
        `approval=True` aprovava as duas de uma vez, e era essa a lacuna."""
        decisao = authorize(
            agent="sf-orchestrator",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_MUTACAO_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(ToolClass.LOCAL_MUTATION,),
        )
        assert decisao.authorized is True
        assert decisao.granted_by is ToolClass.LOCAL_MUTATION

    def test_aprovar_mutacao_local_nao_libera_a_tool_de_nuvem(self):
        """O par negativo do teste acima: a MESMA aprovacao, na tool da outra
        classe, nao vale."""
        decisao = authorize(
            agent="sf-orchestrator",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=ExecutionProfile.BALANCED,
            approvals=(ToolClass.LOCAL_MUTATION,),
        )
        assert decisao.authorized is False
        assert decisao.required_approval is tool_class(UMA_DE_REDE)


class TestPerfilEhTeto:
    """O perfil e um teto, nao uma preferencia -- e o teto tem que valer para o
    tipo canonico do repositorio, nao so para uma grafia.

    A versao anterior destes testes passava `"OFFLINE"` em maiuscula, que era a
    UNICA grafia que funcionava: `ExecutionProfile.OFFLINE` vale `"offline"`,
    minusculo, e por ser `str, Enum` atravessava a anotacao `profile: str` sem
    erro de tipo e comparava `False`. O teto sumia em silencio e a decisao saia
    gravada como `"autorizado"`. O teste trancava o literal, nao o conceito.
    """

    @pytest.mark.parametrize(
        "perfil", [ExecutionProfile.OFFLINE, "offline", "OFFLINE", "Offline"]
    )
    def test_OFFLINE_recusa_tool_de_rede_em_qualquer_grafia(self, perfil):
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=perfil,
            approvals=(),
        )
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason

    @pytest.mark.parametrize(
        "perfil", [ExecutionProfile.OFFLINE, "offline", "OFFLINE", "Offline"]
    )
    def test_aprovacao_nao_fura_o_teto_OFFLINE(self, perfil):
        """Aprovacao nao fura teto -- senao OFFLINE deixaria de significar
        'zero rede' na primeira aprovacao distraida."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=perfil,
            approvals=(ToolClass.CLOUD_READ, ToolClass.CLOUD_MUTATION),
        )
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason

    def test_OFFLINE_nao_barra_leitura_local(self):
        """O par positivo: o teto e sobre REDE, nao sobre parar tudo. Sem este
        teste, `authorize()` poderia recusar tudo sob OFFLINE e os testes acima
        continuariam verdes."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.OFFLINE,
            approvals=(),
        )
        assert decisao.authorized is True

    @pytest.mark.parametrize("perfil", ["", "NAO_EXISTE", "ofline", None, 3])
    def test_perfil_nao_reconhecido_recusa(self, perfil):
        """Mesma disciplina de `tool_class()`: sem perfil nao ha teto, e "sem
        teto" nao pode ser o default de quem escreveu o nome errado."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=perfil,
            approvals=(ToolClass.CLOUD_MUTATION,),
        )
        assert decisao.authorized is False
        assert "perfil nao reconhecido" in decisao.reason

    @pytest.mark.parametrize("perfil", list(ExecutionProfile))
    def test_todo_perfil_do_enum_e_reconhecido(self, perfil):
        """O par positivo do teste acima, derivado do enum em vez de listado a
        mao: nenhum perfil canonico pode cair na recusa de "nao reconhecido"."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=perfil,
            approvals=(),
        )
        assert "perfil nao reconhecido" not in decisao.reason


class TestClassesSemMembroHoje:
    """`CLOUD_READ` e `DESTRUCTIVE` nao tem tool nenhuma no catalogo de hoje.

    O codigo que decide sobre elas so roda de verdade no dia em que a primeira
    entrar -- e ai a decisao ja vale. Catalogo sintetico para exercitar agora.
    """

    def test_destructive_exige_aprovacao_propria(self, monkeypatch):
        catalogo_falso(
            monkeypatch,
            tool_destrutiva={
                "readOnlyHint": False,
                "openWorldHint": False,
                "destructiveHint": True,
            },
        )
        sem = authorize(
            agent="a",
            tool="tool_destrutiva",
            allowed_tools=["tool_destrutiva"],
            profile=ExecutionProfile.ECO,
            approvals=(ToolClass.LOCAL_MUTATION,),
        )
        assert sem.authorized is False
        assert sem.required_approval is ToolClass.DESTRUCTIVE

        com = authorize(
            agent="a",
            tool="tool_destrutiva",
            allowed_tools=["tool_destrutiva"],
            profile=ExecutionProfile.ECO,
            approvals=(ToolClass.DESTRUCTIVE,),
        )
        assert com.authorized is True
        assert com.granted_by is ToolClass.DESTRUCTIVE

    def test_cloud_read_sintetica_bate_no_teto_OFFLINE(self, monkeypatch):
        catalogo_falso(
            monkeypatch,
            tool_leitura_nuvem={
                "readOnlyHint": True,
                "openWorldHint": True,
                "destructiveHint": False,
            },
        )
        decisao = authorize(
            agent="a",
            tool="tool_leitura_nuvem",
            allowed_tools=["tool_leitura_nuvem"],
            profile=ExecutionProfile.OFFLINE,
            approvals=(ToolClass.CLOUD_READ,),
        )
        assert decisao.tool_class is ToolClass.CLOUD_READ
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason

    def test_cloud_read_exige_aprovacao_propria_sob_perfil_sem_teto(self, monkeypatch):
        """O teste do teto acima NAO cobre a aprovacao de `CLOUD_READ`, e a
        diferenca e estrutural, nao de gosto.

        Sob `OFFLINE` o teto dispara ANTES da checagem de aprovacao, entao o
        `approvals=(CLOUD_READ,)` daquele teste e decorativo por construcao --
        ele existe para provar que aprovacao nao fura teto. O efeito colateral
        e que a linha de `_EXIGEM_APROVACAO` nunca via `CLOUD_READ`: remover a
        classe daquele frozenset deixava a suite inteira verde.

        Isso importa mais para `CLOUD_READ` do que para as outras: ela e a
        classe que esta fase ESVAZIOU, e a mais provavel de voltar a ter
        membro na primeira tool que leia da nuvem sem persistir nada."""
        catalogo_falso(
            monkeypatch,
            tool_leitura_nuvem={
                "readOnlyHint": True,
                "openWorldHint": True,
                "destructiveHint": False,
            },
        )
        comum = {
            "agent": "a",
            "tool": "tool_leitura_nuvem",
            "allowed_tools": ["tool_leitura_nuvem"],
            "profile": ExecutionProfile.ECO,
        }
        sem = authorize(**comum, approvals=())
        assert sem.authorized is False
        assert sem.required_approval is ToolClass.CLOUD_READ

        com = authorize(**comum, approvals=(ToolClass.CLOUD_READ,))
        assert com.authorized is True
        assert com.granted_by is ToolClass.CLOUD_READ

        outra = authorize(**comum, approvals=(ToolClass.LOCAL_MUTATION,))
        assert outra.authorized is False, "aprovacao de outra classe nao vale"

    def test_cloud_mutation_bate_no_teto_OFFLINE(self):
        """`CLOUD_MUTATION` deixou de ser vazia na Fase I3 -- os sete coletores
        caem nela desde que a anotacao passou a dizer que eles escrevem. Usa o
        catalogo real, entao."""
        assert tool_class(UMA_DE_REDE) is ToolClass.CLOUD_MUTATION
        decisao = authorize(
            agent="a",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=ExecutionProfile.OFFLINE,
            approvals=(ToolClass.CLOUD_MUTATION,),
        )
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason


class TestToolForaDoCatalogo:
    """`authorize()` e a fronteira de auditoria: ela DECIDE, nunca estoura.

    `tool_class()` levanta `KeyError` de proposito e continua assim. Mas o caso
    mais provavel de todos -- agente alucina um nome de tool, ou um rename
    perde um call site -- era o unico que nao produzia registro nenhum.
    """

    def test_tool_desconhecida_fora_da_allowlist_recusa_pela_allowlist(self):
        decisao = authorize(
            agent="a",
            tool="ferramenta_inexistente",
            allowed_tools=[],
            profile=ExecutionProfile.ECO,
        )
        assert decisao.authorized is False
        assert decisao.tool_class is None
        assert "allowlist" in decisao.reason

    def test_tool_desconhecida_dentro_da_allowlist_recusa_por_falta_de_classe(self):
        decisao = authorize(
            agent="a",
            tool="ferramenta_inexistente",
            allowed_tools=["ferramenta_inexistente"],
            profile=ExecutionProfile.ECO,
        )
        assert decisao.authorized is False
        assert decisao.tool_class is None
        assert "catalogo" in decisao.reason


class TestDenylist:
    """`AgentManifest` declara `denied_tools` ao lado de `allowed_tools`, e as
    duas sao validadas por schema. Denylist que a cadeia ignorasse em silencio
    seria pior que denylist nenhuma."""

    def test_tool_na_denylist_e_recusada(self):
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            denied_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
        )
        assert decisao.authorized is False
        assert "denylist" in decisao.reason

    def test_denylist_vazia_nao_muda_nada(self):
        """O par positivo: a denylist so morde quem esta nela."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            denied_tools=[],
            profile=ExecutionProfile.ECO,
        )
        assert decisao.authorized is True

    def test_deny_vence_allow_mesmo_com_aprovacao(self):
        """Precedencia declarada: uma tool nos dois campos e recusada. E a
        unica ordem em que um engano na allowlist nao abre o que a denylist
        fechou de proposito."""
        decisao = authorize(
            agent="a",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_MUTACAO_LOCAL],
            denied_tools=[UMA_MUTACAO_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(ToolClass.LOCAL_MUTATION,),
        )
        assert decisao.authorized is False
        assert "denylist" in decisao.reason


class TestCompatibilidade:
    def test_authorize_tool_continua_existindo_e_respondendo_igual(self):
        """`AutonomyController.authorize_tool` e API publica exportada em
        `sparkforge.agents.__all__`, e a cadeia entra AO LADO, nao no lugar:
        quebrar a assinatura antiga transformaria uma adicao de seguranca numa
        migracao.

        O que esta afirmacao NAO diz, porque seria falso: que ha chamador em
        producao. Busca exaustiva na Fase I3 achou zero -- os unicos chamadores
        sao `tests/test_agent_autonomy.py` e este teste. A razao de manter e
        ser superficie publica, nao ter consumidor interno."""
        from sparkforge.agents.autonomy import AutonomyController

        controlador = AutonomyController()
        ok, razao = controlador.authorize_tool(
            agent="a", tool="t", allowed_tools=["t"], mutating=False, approval=False
        )
        assert ok is True and razao == "authorized"


class TestArgumentoEntraNaDecisao:
    """A cadeia autorizava um NOME; agora ela ve a CHAMADA.

    O limite estava declarado em `docs/harness/AUTHORIZATION-CHAIN.md` com
    medicao: uma tool `READ_ONLY` com `path` arbitrario leu um segredo de fora
    do repositorio sob perfil `OFFLINE`, com a cadeia funcionando exatamente
    como especificada. A classe da tool nao muda -- ler continua sendo
    `READ_ONLY`. O que muda e que o argumento entra na decisao.

    Medido no catalogo de hoje: 43 das 44 tools declaram algum parametro de
    caminho de sistema de arquivos. Nao e caso de borda; e a forma da chamada.
    """

    def test_recusa_caminho_fora_da_raiz(self, tmp_path):
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": "../../../etc/passwd"},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "fora da raiz" in decisao.reason
        assert decisao.checked_arguments is True

    def test_recusa_caminho_absoluto_de_fora_da_raiz(self, tmp_path):
        """Traversal por `..` e a forma obvia; caminho absoluto e a barata.

        `Path.__truediv__` descarta o lado esquerdo quando o direito e
        absoluto, entao um confinamento escrito como concatenacao de texto
        aprovaria isto sem piscar.
        """
        fora = tmp_path.parent / "segredo.txt"
        fora.write_text("x\n", encoding="utf-8")
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": str(fora)},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "fora da raiz" in decisao.reason

    def test_recusa_til_porque_a_cadeia_nao_expande_home(self, tmp_path):
        """`~/.aws/credentials` nao e expandido pelo confinamento.

        Sem expansao, `raiz / "~/.aws/credentials"` cai DENTRO da raiz e
        passaria. Hoje nenhum adapter deste repositorio chama `expanduser()`
        num argumento de tool (conferido por busca), entao a leitura falharia
        de todo jeito -- mas a recusa nao depende de isso continuar verdade, e
        e barata.
        """
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": "~/.aws/credentials"},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "fora da raiz" in decisao.reason

    def test_aceita_caminho_dentro_da_raiz(self, tmp_path):
        (tmp_path / "job.py").write_text("x = 1\n", encoding="utf-8")
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": str(tmp_path / "job.py")},
            root=tmp_path,
        )
        assert decisao.authorized is True
        assert decisao.checked_arguments is True

    def test_aceita_caminho_relativo_dentro_da_raiz(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "job.py").write_text("x = 1\n", encoding="utf-8")
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": "src/job.py"},
            root=tmp_path,
        )
        assert decisao.authorized is True

    @pytest.mark.parametrize(
        "chave", ["path", "repo", "file", "before", "after", "facts_path", "report_path"]
    )
    def test_a_verificacao_nao_e_so_do_parametro_chamado_path(self, tmp_path, chave):
        """As 43 tools nomeiam o caminho de sete jeitos diferentes.

        Verificar so `path` deixaria `sparkforge_report_verify` (`report_path`,
        `findings_path`) e `sparkforge_analyze_terraform_diff` (`before`,
        `after`) inteiramente de fora -- e as duas leem arquivo.
        """
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={chave: "../fora.json"},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "fora da raiz" in decisao.reason
        assert chave in decisao.reason

    def test_lista_de_caminhos_e_verificada_item_a_item(self, tmp_path):
        """`facts_paths` de `sparkforge_fuse` e lista, nao string.

        Verificar so `isinstance(valor, str)` deixaria a lista inteira passar
        sem checagem nenhuma -- e ela e o argumento principal daquela tool.
        """
        (tmp_path / "a.json").write_text("{}\n", encoding="utf-8")
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"facts_paths": [str(tmp_path / "a.json"), "../../fora.json"]},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "facts_paths" in decisao.reason

    def test_argumento_que_nao_e_caminho_nao_vira_caminho(self, tmp_path):
        """`case_id` e `limit` nao sao caminho, e tratar tudo como caminho
        transformaria a cadeia num gerador de falso negativo de
        disponibilidade."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"case_id": "../../nao-e-caminho", "limit": 10},
            root=tmp_path,
        )
        assert decisao.authorized is True
        assert decisao.checked_arguments is True

    def test_arguments_vazio_conta_como_verificado(self, tmp_path):
        """Dicionario vazio e uma chamada SEM argumento de caminho, e isso foi
        examinado. Nao passar `arguments` e nao ter olhado. Os dois nao podem
        colapsar no mesmo valor."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={},
            root=tmp_path,
        )
        assert decisao.authorized is True
        assert decisao.checked_arguments is True

    def test_arguments_sem_raiz_recusa(self, tmp_path):
        """Mesma disciplina de `tool_class()` e do perfil: sem raiz nao ha
        confinamento, e "sem confinamento" nao pode ser o default de quem
        passou o argumento e esqueceu a raiz."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": "job.py"},
        )
        assert decisao.authorized is False
        assert "raiz" in decisao.reason
        assert decisao.checked_arguments is False

    def test_o_argumento_nao_fura_a_classe_nem_o_teto(self, tmp_path):
        """Caminho legitimo nao promove nada: a tool de rede continua batendo
        no teto `OFFLINE` com argumento perfeito."""
        decisao = authorize(
            agent="a",
            tool=UMA_DE_REDE,
            allowed_tools=[UMA_DE_REDE],
            profile=ExecutionProfile.OFFLINE,
            arguments={"repo": str(tmp_path)},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason
        assert decisao.checked_arguments is False

    def test_caminho_fora_da_raiz_nao_e_salvo_por_aprovacao(self, tmp_path):
        """Aprovacao e por CLASSE, e classe nao diz nada sobre argumento.

        Se aprovar `LOCAL_MUTATION` liberasse qualquer caminho, a fase teria
        trocado um buraco por outro.
        """
        decisao = authorize(
            agent="a",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_MUTACAO_LOCAL],
            profile=ExecutionProfile.ECO,
            approvals=(ToolClass.LOCAL_MUTATION,),
            arguments={"repo": "../../outro-repo"},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "fora da raiz" in decisao.reason


class TestCompatibilidadeDoArgumento:
    def test_sem_arguments_a_decisao_continua_como_antes(self):
        """Quem nao passa `arguments` nao muda de comportamento.

        `checked_arguments` e o que torna isso AUDITAVEL em vez de so
        compativel: sem o campo, uma decisao tomada sem olhar argumento nenhum
        seria indistinguivel de uma que olhou e aprovou.
        """
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
        )
        assert decisao.authorized is True
        assert decisao.checked_arguments is False

    def test_root_sozinho_nao_liga_a_verificacao(self, tmp_path):
        """Passar `root` sem `arguments` nao inventa uma verificacao que nao
        aconteceu -- nao ha argumento para verificar."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            root=tmp_path,
        )
        assert decisao.authorized is True
        assert decisao.checked_arguments is False

    def test_recusa_por_falta_de_aprovacao_declara_que_nao_olhou(self, tmp_path):
        """O ramo da aprovacao e o UNICO que constroi `AuthorizationDecision`
        direto, sem passar por `recusa()` -- ele herda o default do campo.

        Sem este teste o default e codigo morto do ponto de vista da suite:
        teste de mutacao trocando `checked_arguments: bool = False` por `True`
        sobreviveu, e a decisao passava a afirmar que examinou um argumento que
        nunca chegou a ver.
        """
        decisao = authorize(
            agent="a",
            tool=UMA_MUTACAO_LOCAL,
            allowed_tools=[UMA_MUTACAO_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"repo": str(tmp_path)},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert decisao.required_approval is ToolClass.LOCAL_MUTATION
        assert decisao.checked_arguments is False

    def test_recusa_anterior_ao_argumento_declara_que_nao_olhou(self, tmp_path):
        """A allowlist decide ANTES, e a decisao nao pode dizer que examinou o
        argumento quando nao chegou la."""
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=["outra_tool"],
            profile=ExecutionProfile.ECO,
            arguments={"path": "../../../etc/passwd"},
            root=tmp_path,
        )
        assert decisao.authorized is False
        assert "allowlist" in decisao.reason
        assert decisao.checked_arguments is False


class TestConfinamentoEhUmSoAlgoritmo:
    """A cadeia e o catalogo de regras precisam recusar as MESMAS coisas.

    Duas implementacoes de confinamento nao divergem alto: divergem no dia em
    que alguem corrige uma e nao a outra. Este teste amarra os dois consumidores
    ao mesmo comportamento observavel, entao extrair o algoritmo para
    `sparkforge/paths.py` e mante-lo la deixa de ser convencao e passa a ser
    coisa medida.
    """

    ESCAPAM = ("../fora.yaml", "a/../../fora.yaml", "../../etc/passwd")
    FICAM = ("dentro.yaml", "sub/dentro.yaml", "./dentro.yaml")

    @pytest.mark.parametrize("nome", ESCAPAM)
    def test_os_dois_recusam_o_mesmo(self, tmp_path, nome):
        from sparkforge.rules.loader import CatalogError, safe_catalog_file

        raiz = tmp_path / "raiz"
        raiz.mkdir()
        with pytest.raises(CatalogError):
            safe_catalog_file(raiz, nome)
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": nome},
            root=raiz,
        )
        assert decisao.authorized is False

    @pytest.mark.parametrize("nome", FICAM)
    def test_os_dois_aceitam_o_mesmo(self, tmp_path, nome):
        from sparkforge.rules.loader import safe_catalog_file

        raiz = tmp_path / "raiz"
        raiz.mkdir()
        assert safe_catalog_file(raiz, nome)
        decisao = authorize(
            agent="a",
            tool=UMA_LEITURA_LOCAL,
            allowed_tools=[UMA_LEITURA_LOCAL],
            profile=ExecutionProfile.ECO,
            arguments={"path": nome},
            root=raiz,
        )
        assert decisao.authorized is True


class TestOCatalogoContinuaCabendoNaVerificacao:
    """O gate que impede a medicao do Passo 1 de envelhecer em silencio.

    Medido: 43 das 44 tools declaram parametro de caminho, e a unica sem
    nenhum e `sparkforge_rules_lookup` (`category`, `id`, `limit`, `cursor`).
    Se uma tool nova entrar com um caminho batizado de outro jeito
    (`caminho`, `origem`, `destino`), a contagem muda e este teste cai -- que e
    o ponto. O predicado nao adivinha; ele reconhece nomes, e nome novo tem de
    passar por decisao de alguem, nao por default silencioso.
    """

    SEM_CAMINHO = frozenset({"sparkforge_rules_lookup"})

    def test_toda_tool_menos_uma_declara_caminho(self):
        from sparkforge.agents.autonomy import _e_chave_de_caminho

        sem_caminho = {
            nome
            for nome in TOOLS
            if not any(
                _e_chave_de_caminho(p)
                for p in (TOOLS[nome].get("inputSchema") or {}).get("properties") or {}
            )
        }
        assert sem_caminho == self.SEM_CAMINHO
        assert len(TOOLS) - len(sem_caminho) == 43
