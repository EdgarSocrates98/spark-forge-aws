"""As recusas do L1 e do L2, com o que destrava cada uma (regra 20).

Um modulo so para os nomes porque tres modulos os levantam (`plan`, `apply`,
`sandbox`) e a tool os declara no `outputSchema`: nome escrito em dois lugares
e o que diverge calado no dia em que alguem renomeia um so.
"""
from __future__ import annotations

from typing import Any

SEM_PROCEDENCIA = "sem_procedencia_em_arquivo"
LINHA_NAO_CONFERE = "linha_nao_confere"
PROCEDENCIA_AMBIGUA = "procedencia_ambigua"
VALOR_NAO_LITERAL = "valor_nao_literal"
VALOR_REDIGIDO = "valor_redigido"
VALOR_INVALIDO = "valor_invalido"
VALOR_JA_IGUAL = "valor_ja_igual"
CAMINHO_FORA_DA_RAIZ = "caminho_fora_da_raiz"

DIFF_VAZIO = "diff_vazio"
DIFF_GRANDE_DEMAIS = "diff_grande_demais"
DIFF_NAO_SUPORTADO = "diff_nao_suportado"
DIFF_MALFORMADO = "diff_malformado"
DIFF_NAO_APLICA = "diff_nao_aplica"
ARQUIVO_FORA_DA_COPIA = "arquivo_fora_da_copia"

SANDBOX_INEXISTENTE = "sandbox_inexistente"
SANDBOX_NAO_APLICADO = "sandbox_nao_aplicado"
SANDBOX_DESATUALIZADO = "sandbox_desatualizado"
ACHADO_NOVO_BLOQUEANTE = "achado_novo_bloqueante"

DESTRAVA: dict[str, str] = {
    SEM_PROCEDENCIA: (
        "declare a chave em arquivo (Terraform `--conf` ou `spark.conf.set`) e extraia de "
        "novo com `sparkforge analyze terraform|pyspark --out`; valor que so o runtime ou o "
        "cluster define nao tem linha para mudar"
    ),
    LINHA_NAO_CONFERE: (
        "extraia os facts de novo sobre a arvore atual (`sparkforge analyze terraform|pyspark "
        "--out`) e passe `--repo` na mesma raiz usada na extracao"
    ),
    PROCEDENCIA_AMBIGUA: (
        "deixe a chave num lugar so (o codigo vence o Terraform em runtime) e extraia de novo"
    ),
    VALOR_NAO_LITERAL: "escreva o valor como literal simples na chamada, ou mude a mao",
    VALOR_REDIGIDO: "o valor parece segredo e foi redigido na extracao; mude a mao",
    VALOR_INVALIDO: "passe um valor do mesmo tipo do atual, sem espaco, aspas ou barra invertida",
    VALOR_JA_IGUAL: "nada a mudar: o arquivo ja pede esse valor",
    CAMINHO_FORA_DA_RAIZ: "use caminho relativo a raiz do repositorio, sem `..` nem absoluto",
    DIFF_VAZIO: (
        "gere o diff com `sparkforge change plan --out <arquivo>` ou `git diff > <arquivo>`"
    ),
    DIFF_GRANDE_DEMAIS: "divida o diff em partes menores; o teto e 2 MB",
    DIFF_NAO_SUPORTADO: (
        "o sandbox so aplica mudanca de conteudo em arquivo de texto que ja existe; criacao, "
        "remocao, renome e binario ficam de fora"
    ),
    DIFF_MALFORMADO: "gere o diff de novo com `git diff` ou `sparkforge change plan --out`",
    DIFF_NAO_APLICA: (
        "o diff foi feito sobre outra versao do arquivo; gere-o de novo sobre a arvore atual"
    ),
    ARQUIVO_FORA_DA_COPIA: (
        "o arquivo e sensivel, fica em diretorio ignorado (vendor, build, .venv...) ou passa do "
        "teto de tamanho da varredura; mude-o a mao"
    ),
    SANDBOX_INEXISTENTE: (
        "rode `sparkforge change sandbox --repo <raiz> --diff <arquivo>` e passe o `id` que ele "
        "devolver"
    ),
    SANDBOX_NAO_APLICADO: (
        "o sandbox recusou o diff; resolva a recusa dele e rode `sparkforge change sandbox` de novo"
    ),
    SANDBOX_DESATUALIZADO: (
        "a arvore mudou depois do sandbox; rode `sparkforge change sandbox` de novo sobre a "
        "arvore atual e proponha o `id` novo"
    ),
    ACHADO_NOVO_BLOQUEANTE: (
        "o diff faz aparecer achado P0 ou P1; corrija a mudanca, rode o sandbox de novo e so "
        "entao proponha"
    ),
}

RECUSAS_DO_PLANO: tuple[str, ...] = (
    SEM_PROCEDENCIA, LINHA_NAO_CONFERE, PROCEDENCIA_AMBIGUA, VALOR_NAO_LITERAL,
    VALOR_REDIGIDO, VALOR_INVALIDO, VALOR_JA_IGUAL, CAMINHO_FORA_DA_RAIZ,
)
RECUSAS_DO_SANDBOX: tuple[str, ...] = (
    DIFF_VAZIO, DIFF_GRANDE_DEMAIS, DIFF_NAO_SUPORTADO, DIFF_MALFORMADO, DIFF_NAO_APLICA,
    CAMINHO_FORA_DA_RAIZ, ARQUIVO_FORA_DA_COPIA,
)
RECUSAS_DA_PROPOSTA: tuple[str, ...] = (
    SANDBOX_INEXISTENTE, SANDBOX_NAO_APLICADO, SANDBOX_DESATUALIZADO, ACHADO_NOVO_BLOQUEANTE,
    CAMINHO_FORA_DA_RAIZ,
)


class ChangeError(ValueError):
    """Recusa nomeada: `reason` e um dos nomes acima, `detail` diz onde."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{detail} [{reason}]")
        self.reason = reason
        self.detail = detail

    def to_dict(self, key: str | None = None) -> dict[str, Any]:
        recusa: dict[str, Any] = {
            "reason": self.reason,
            "detail": self.detail,
            "unlock": DESTRAVA[self.reason],
        }
        if key is not None:
            recusa["key"] = key
        return recusa
