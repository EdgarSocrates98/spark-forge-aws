"""Projecoes de findings ja julgados para superficies externas.

Nada aqui le artefato, grava arquivo ou abre rede: as funcoes recebem findings,
facts e uma funcao `existe` construida por quem chama, e devolvem o que cada
superficie espera. `sparkforge/adapters/_core.py::report_github` e a borda que
le JSON, confina os caminhos ao repositorio e grava.
"""
