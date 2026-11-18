# -*- coding: utf-8 -*-
"""Links to the feedback forms of the site, and the one invitation to give a review.

The forms live on the feedback page of the site (``feedback.html``), which holds
their Tally ids: the plugin only opens that page in the browser, with a ``ref``
naming where the click came from. Nothing is sent by the plugin itself.

After ``INVITE_AFTER`` successful filters, a message of the QGIS message bar offers
the short review form once, and never again: the invitation is marked as shown the
moment it is shown, whatever the user does with it.
"""

import logging
import os

from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices


logger = logging.getLogger(__name__)


def _tr(text):
    return QCoreApplication.translate('FilterMate', text)


SITE = "https://imagodata.github.io/filter_mate/"
FORMS = ("usage", "review", "feature", "testers", "services")
INVITE_AFTER = 20
INVITE_SECONDS = 60
COUNT_KEY = "FilterMate/feedback/successful_filters"
SHOWN_KEY = "FilterMate/feedback/invite_shown"
# Set in benches and scripted captures: no invitation in their screenshots.
NO_INVITE_ENV = "FILTERMATE_NO_FEEDBACK_INVITE"

_locale = "en"


def set_locale(locale):
    """The language of the plugin's translator ('fr', 'en'...), for the page to open."""
    global _locale
    _locale = (locale or "en")[:2].lower()


def feedback_url(form, ref, locale=None):
    """The feedback page at the section of ``form``, French for a French plugin, English otherwise."""
    if form not in FORMS:
        raise ValueError(f"unknown form: {form}")
    page = "feedback.fr.html" if (locale or _locale) == "fr" else "feedback.html"
    return f"{SITE}{page}?ref={ref}#{form}"


def open_form(form, ref):
    """Open the page of a form in the browser."""
    QDesktopServices.openUrl(QUrl(feedback_url(form, ref)))


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def note_successful_filter(settings, environ=None):
    """Count a successful filter; True when the invitation is due now (once, ever).

    ``settings`` has ``value(key, default)`` and ``setValue(key, value)`` (a QgsSettings).
    """
    environ = os.environ if environ is None else environ
    if environ.get(NO_INVITE_ENV):
        return False
    if _as_bool(settings.value(SHOWN_KEY, False)):
        return False
    count = _as_int(settings.value(COUNT_KEY, 0)) + 1
    settings.setValue(COUNT_KEY, count)
    if count < INVITE_AFTER:
        return False
    settings.setValue(SHOWN_KEY, True)
    return True


def show_invite(iface):
    """The one message of the message bar that offers the review form."""
    from qgis.core import Qgis
    from qgis.PyQt.QtWidgets import QPushButton

    bar = iface.messageBar()
    text = _tr("FilterMate has run {} filters for you. Thirty seconds to rate it?").format(INVITE_AFTER)
    item = bar.createMessage("FilterMate", text)
    button = QPushButton(_tr("Give my opinion"))

    def clicked():
        open_form("review", "plugin-invite")
        try:
            bar.popWidget(item)
        except RuntimeError:  # already closed
            pass

    button.clicked.connect(clicked)
    item.layout().addWidget(button)
    bar.pushWidget(item, Qgis.MessageLevel.Info, INVITE_SECONDS)


def maybe_invite(iface):
    """After a successful filter: count it, and show the invitation when it is due."""
    try:
        from qgis.core import QgsSettings
        if note_successful_filter(QgsSettings()) and iface is not None:
            show_invite(iface)
    except Exception as error:  # an invitation must never break the end of a filter
        logger.debug(f"FilterMate: feedback invitation skipped: {error}")
