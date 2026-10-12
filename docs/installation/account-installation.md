# Account-scoped installation

Run `install.sh` (POSIX) or `install.ps1` (Windows) from this checkout. Installer performs `pip install -e .` into `~/.forge/installs/spark-forge-aws/.venv`, outside project workspaces.

Published variables use prefix `SPARK_FORGE_AWS`: `HOME`, `INSTALL_ROOT`, `VENV`, `PYTHON`, `CLI`, and `LAUNCHER`. Underscores are canonical because POSIX shells reject hyphens. Windows also receives aliases such as `SPARK-FORGE-AWS-HOME`, without administrator permission.

POSIX installer writes `~/.config/forjas/env.sh`; open a new shell or run `source ~/.config/forjas/env.sh`. Windows processes opened after installation receive HKCU variables.

`setup.sh`/`setup.ps1` remains compatibility mode. The Forge doctor and Portal validate runtime paths while never reading credentials.
