from mcmr.execution import backends


def test_tron_document_declares_shapes_and_safe_literal_blocks() -> None:
    """TRON declares repeated layouts once and cannot close a source block early."""
    source = "def example():\n    return ```\n" * 4
    document = backends.TronDocument(
        document={
            "e": {
                "e0": {"d": {"kind": "function", "source": source}, "s": "src/a.py"},
                "e1": {"d": {"kind": "function", "source": source}, "s": "src/b.py"},
            },
            "c": {"c0": {"e": ["e0"]}, "c1": {"e": ["e1"]}},
        }
    )

    rendered = document.render()

    assert rendered.startswith("Text blocks\n@0\n````\n")
    assert ": d,s" in rendered
    assert ": kind,source" in rendered
    assert rendered.count(source) == 1
    assert '("function","@0")' in rendered
    assert '"src/a.py"' in rendered


def test_tron_document_does_not_reuse_literal_reference_text() -> None:
    """A source string shaped like a reference cannot collide with a text block."""
    source = "line\n" * 20
    rendered = backends.TronDocument(
        document={
            "e": {
                "e0": {"d": "@0", "s": "src/a.py"},
                "e1": {"d": source, "s": "src/b.py"},
            }
        }
    ).render()

    assert "Text blocks\n@1\n" in rendered
    assert '("@0","src/a.py")' in rendered
