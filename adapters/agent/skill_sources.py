# -*- coding: utf-8 -*-
"""Skills from elsewhere: the folder ``FilterMate/skills`` of the QGIS profile (trust ``user``) and the folder
``filtermate_skills`` next to the open project (trust ``project``).

They follow the standard of ``skills/README.md`` (a skill that does not is left out and logged). They are data, not
instructions of FilterMate: the user reads one and allows it before it is loaded the first time (``approved`` /
``approve``, by the fingerprint of its text and of where it comes from), it guides the chat only, and it gives no
tool (``core/agent/skills.set_extra``).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from ...core.agent import skills

logger = logging.getLogger("FilterMate")
USER_FOLDER = "skills"
PROJECT_FOLDER = "filtermate_skills"
APPROVED_KEY = "FilterMate/agent/approved_skills"
MAX_APPROVED = 200


def user_folder() -> Optional[Path]:
    """``FilterMate/skills`` of the QGIS profile (next to the configuration of FilterMate)."""
    try:
        from ...config.config import ENV_VARS
        base = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY")
    except ImportError:
        base = None
    if not base:
        try:
            from qgis.core import QgsApplication
            base = os.path.join(QgsApplication.qgisSettingsDirPath(), "FilterMate")
        except Exception:
            return None
    return Path(base) / USER_FOLDER


def project_folder() -> Optional[Path]:
    """``filtermate_skills`` next to the open project file; None for a project never saved or kept in a database.

    The folder of the file itself, not a home path the project sets: it can be any place (the share of another
    computer too), which was then read at each request, on the main thread (2026-11-13). A project kept in a
    GeoPackage has no file path of its own: without a home path set, its home path is the folder of the GeoPackage.
    """
    try:
        from qgis.core import QgsProject
        project = QgsProject.instance()
        path = project.absoluteFilePath()
        if path:
            return Path(path).parent / PROJECT_FOLDER
        home = "" if project.presetHomePath() else project.homePath()
    except Exception:
        return None
    return Path(home) / PROJECT_FOLDER if home else None


def refresh() -> List[str]:
    """Read both folders again (the project may have changed); the reasons of the skills left out."""
    errors: List[str] = []
    found = {}
    for folder, trust in ((user_folder(), "user"), (project_folder(), "project")):
        if folder is None:
            continue
        try:
            # A link is told before it is followed: one to a share would be reached at each request (2026-11-13).
            if folder.is_symlink() or skills._is_junction(str(folder)):
                errors.append(f"{folder.name}: a link, the skills are in a folder of their own")
                continue
            for name, skill in skills.read_folder(folder, trust=trust, errors=errors, limit=skills.MAX_EXTRA,
                                                  reserved=skills.RESERVED).items():
                if name in found:  # the profile first: a project cannot replace a skill the user keeps
                    errors.append(f"{name}: a skill of the profile has that name")
                    continue
                found[name] = skill
        except Exception as exc:  # whatever happens, the skills of a folder read before are not kept by mistake
            errors.append(f"{folder.name}: not read ({type(exc).__name__})")
    errors += skills.set_extra(found)
    for error in errors:
        logger.info("Agent skill left out: %s", error)
    return errors


def _approved() -> List[str]:
    try:
        from qgis.core import QgsSettings
        value = json.loads(str(QgsSettings().value(APPROVED_KEY, "[]") or "[]"))
    except Exception:
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def approved(skill: "skills.Skill") -> bool:
    return skill.trust == "builtin" or skills.fingerprint(skill) in _approved()


# Skills the user said no to, until QGIS restarts or the text changes: a model must not ask again at each request
# until the user, tired of it, says yes (2026-11-13).
_declined: set = set()


def declined(skill: "skills.Skill") -> bool:
    return skills.fingerprint(skill) in _declined


def decline(skill: "skills.Skill") -> None:
    _declined.add(skills.fingerprint(skill))


def remember(skill: "skills.Skill") -> None:
    """The user allowed this text from this place: not asked again until it changes."""
    try:
        from qgis.core import QgsSettings
        kept = [item for item in _approved() if item != skills.fingerprint(skill)][-(MAX_APPROVED - 1):]
        QgsSettings().setValue(APPROVED_KEY, json.dumps(kept + [skills.fingerprint(skill)]))
    except Exception:
        logger.debug("Agent skill approval not kept", exc_info=True)
