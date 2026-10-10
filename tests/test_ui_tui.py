"""TUI/menu contract tests — vendored ui.* surface."""

import pytest


def test_menu_well_formed():
    """Every _MENU item is a (label, argv|None) pair — no bare strings."""
    from sparkforge_aws.ui import home
    for item in home._MENU:
        assert isinstance(item, tuple) and len(item) == 2, item
        label, argv = item
        assert isinstance(label, str) and label
        assert argv is None or argv == "__wizard__" or isinstance(argv, list)


def test_tui_entries_real():
    from sparkforge_aws.ui import tui
    entries = tui.entries()
    assert len(entries) >= 3
    assert any("wizard" in e.label for e in entries)


def test_tui_renders_non_tty_ctx():
    from sparkforge_aws.ui import tui
    from sparkforge_aws.ui.app import ForgeApp
    from sparkforge_aws.ui.kit import UIContext
    from sparkforge_aws.ui.screen import Buffer
    ctx = UIContext(interactive=False, color=False, unicode=False,
                    width=80, height=24, ansi=False)
    app = ForgeApp(ctx, forge_id="x", title="cc", entries=tui.entries())
    buf = Buffer(ctx, 80, 24)
    app.render(buf)
    assert "menu" in chr(10).join(buf.render())


def test_home_requires_tty():
    from sparkforge_aws.ui import home
    from sparkforge_aws.ui.kit import NonInteractive, UIContext
    ctx = UIContext(interactive=False, color=False, unicode=False, width=80)
    with pytest.raises(NonInteractive):
        home.run_home(ctx=ctx)
