# -*- coding: utf-8 -*-
"""Every module that translates strings is a source of i18n/FilterMate.pro.

pylupdate5 marks obsolete every message of a file it is not given: the translations of the AGENT section
were lost that way once, in every language. A module that calls ``translate`` or ``tr`` has to be listed.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIPPED_DIRS = {'tests', 'scripts', 'website', 'docs', '_bmad', 'i18n', '.git', '.claude',
                'node_modules', '__pycache__'}
TRANSLATES = re.compile(r"QCoreApplication\.translate\(|\.tr\(|\b_tr\(")
# Modules not in the project file yet, their strings not translated (empty since the backlog was translated).
NOT_YET = set()


def _pro_sources():
    with open(os.path.join(ROOT, 'i18n', 'FilterMate.pro'), encoding='utf-8') as handle:
        return {path for path in re.findall(r"\.\./(\S+\.py)", handle.read())}


def _translating_modules():
    found = set()
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIPPED_DIRS]
        for name in files:
            if name.endswith('.py'):
                path = os.path.join(folder, name)
                with open(path, encoding='utf-8') as handle:
                    if TRANSLATES.search(handle.read()):
                        found.add(os.path.relpath(path, ROOT).replace(os.sep, '/'))
    return found


def test_every_translating_module_is_in_the_project_file():
    missing = sorted(_translating_modules() - _pro_sources() - NOT_YET)
    assert not missing, f"add these to i18n/FilterMate.pro, or pylupdate5 drops their translations: {missing}"


def test_the_agent_modules_are_listed():
    sources = _pro_sources()
    for path in ('ui/widgets/agent_panel.py', 'ui/widgets/agent_thread.py', 'ui/controllers/agent_chat_controller.py',
                 'ui/layout/dock_chrome.py'):
        assert path in sources, path


def test_the_backlog_list_holds_only_modules_still_missing():
    assert not (NOT_YET & _pro_sources()), "listed in the project file now: take it out of NOT_YET"
