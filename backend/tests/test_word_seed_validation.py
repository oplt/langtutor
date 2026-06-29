from __future__ import annotations

from backend.app.modules.learning.engine import _is_valid_seed_lemma


def test_valid_single_word_lemma():
    assert _is_valid_seed_lemma("schouder") is True


def test_rejects_overlong_lemma():
    assert _is_valid_seed_lemma("a" * 129) is False


def test_rejects_pdf_garbage_blob():
    blob = "emotions gelukkig happy blij " * 40
    assert _is_valid_seed_lemma(blob) is False


def test_rejects_xodo_artifact():
    assert _is_valid_seed_lemma("made with xodo pdf reader") is False
