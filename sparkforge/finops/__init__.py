"""Leitura financeira: custo, a troca recurso-tempo, e onde a alavanca esta.

Pacote proprio, e nao `sparkforge/economy/`: aquele e sobre economia de
chamadas e tokens de LLM, com perfis ECO/QUALITY/STRICT, e o nome colidiria
com o assunto errado. A separacao esta na seccao 22 do documento de origem.
"""
from sparkforge.finops.report import build_finops_report

__all__ = ["build_finops_report"]
