# -*- coding: utf-8 -*-
"""The links to the feedback page and the one invitation to give a review."""
import pytest

from infrastructure import feedback_forms as ff


class FakeSettings:
    """QgsSettings stores strings once read back from disk: keep that in mind with values."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):  # noqa: N802 - QgsSettings API
        self.values[key] = value


def test_url_points_to_the_section_with_its_ref():
    assert ff.feedback_url("review", "plugin-invite", "en") == (
        "https://imagodata.github.io/filter_mate/feedback.html?ref=plugin-invite#review")


def test_french_plugin_opens_the_french_page_others_the_english_one():
    assert "/feedback.fr.html?" in ff.feedback_url("usage", "plugin-menu", "fr")
    assert "/feedback.html?" in ff.feedback_url("usage", "plugin-menu", "de")


def test_set_locale_drives_the_default_language():
    try:
        ff.set_locale("fr_FR")
        assert "/feedback.fr.html?" in ff.feedback_url("feature", "plugin-menu")
        ff.set_locale(None)
        assert "/feedback.html?" in ff.feedback_url("feature", "plugin-menu")
    finally:
        ff.set_locale("en")


def test_unknown_form_is_refused():
    with pytest.raises(ValueError):
        ff.feedback_url("waitlist", "plugin-menu", "en")


def test_invitation_comes_once_after_the_threshold():
    settings = FakeSettings()
    due = [ff.note_successful_filter(settings, environ={}) for _ in range(ff.INVITE_AFTER + 5)]
    assert due.index(True) == ff.INVITE_AFTER - 1
    assert due.count(True) == 1


def test_invitation_never_comes_back_once_shown():
    # Read back from disk, the flag is the string "true".
    settings = FakeSettings({ff.SHOWN_KEY: "true", ff.COUNT_KEY: "3"})
    assert not any(ff.note_successful_filter(settings, environ={}) for _ in range(50))
    assert settings.values[ff.COUNT_KEY] == "3"  # nothing counted any more


def test_count_read_back_as_a_string_keeps_counting():
    settings = FakeSettings({ff.COUNT_KEY: str(ff.INVITE_AFTER - 1)})
    assert ff.note_successful_filter(settings, environ={}) is True


def test_benches_and_captures_never_get_the_invitation():
    settings = FakeSettings({ff.COUNT_KEY: ff.INVITE_AFTER * 2})
    assert ff.note_successful_filter(settings, environ={ff.NO_INVITE_ENV: "1"}) is False
    assert ff.SHOWN_KEY not in settings.values
