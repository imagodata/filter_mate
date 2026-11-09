# -*- coding: utf-8 -*-
"""The free quota through the deployed relay, the way the plugin reaches it: one real request, paid by the relay.

    docker run --rm -e FM_FREE_QUOTA_URL=https://... -v "$PWD:/src:ro" qgis/qgis:ltr python3 /src/tests/qgis_headless/check_free_quota_live.py
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HOME = tempfile.mkdtemp()
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = HOME
os.environ["QGIS_AUTH_DB_DIR_PATH"] = HOME

from qgis.core import QgsApplication  # noqa: E402
from qgis.PyQt.QtCore import QCoreApplication, QObject  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def main():
    from filter_mate.adapters.agent import free_quota
    from filter_mate.adapters.agent.qt_transport import QtTransport
    from filter_mate.adapters.agent.settings import AgentSettings, provider_config
    from filter_mate.config import config
    from filter_mate.core.agent.messages import StreamFailure, TextDelta, TurnComplete
    from filter_mate.core.agent.providers import FREE_MODEL, FREE_PRESET, create_provider
    from filter_mate.core.agent.session import AgentSession
    from filter_mate.core.agent.system_prompt import SYSTEM_PROMPT
    from filter_mate.core.agent.tool_catalog import chat_tools

    url = os.environ["FM_FREE_QUOTA_URL"].rstrip("/")
    agent = config.ENV_VARS.setdefault("CONFIG_DATA", {}).setdefault("APP", {}).setdefault("OPTIONS", {}).setdefault("AGENT", {})
    agent["free_quota_url"] = {"value": url}
    # A token given by the caller spares one of the few registrations an address gets each day.
    token = os.environ.get("FM_FREE_TOKEN", "")
    if not token:
        free_quota.forget_token()
        token = free_quota.token_for(url)
    check("a token from the relay", token.startswith("fmq1."))
    provider = create_provider(provider_config(AgentSettings(preset=FREE_PRESET, model=FREE_MODEL), token))
    session = AgentSession(provider, chat_tools(), SYSTEM_PROMPT)
    session.add_user_text("Dis bonjour en une phrase, sans utiliser d'outil.")
    events = []
    owner = QObject()
    QtTransport(owner).start(session.next_request(), session.new_parser(), events.append)
    deadline = time.time() + 90
    while time.time() < deadline and not any(isinstance(e, (TurnComplete, StreamFailure)) for e in events):
        QCoreApplication.processEvents()
        time.sleep(0.01)
    failure = next((e for e in events if isinstance(e, StreamFailure)), None)
    done = next((e for e in events if isinstance(e, TurnComplete)), None)
    text = "".join(e.text for e in events if isinstance(e, TextDelta))
    check("the model answers through the relay", done is not None and text.strip(),
          failure.error.message[:300] if failure else "no answer")
    if done is not None:
        print("answer:", text.strip()[:200], flush=True)
        print("usage:", getattr(done, "usage", None), flush=True)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(0 if RESULTS and all(RESULTS) else 1)
