"""Tests for forge CLI doctor and inspection commands."""
import pytest
from sparkforge.cli.forge import main


def test_forge_doctor(capsys):
    rc = main(["doctor", "--repo", "."])
    assert rc == 0
    captured = capsys.readouterr()
    assert '"status": "PASS"' in captured.out
    assert '"registry_valid": true' in captured.out


def test_forge_inspect_agent(capsys):
    rc = main(["inspect", "agent", "spark-performance-architect"])
    assert rc == 0
    captured = capsys.readouterr()
    assert '"name": "spark-performance-architect"' in captured.out
