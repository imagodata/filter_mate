# -*- coding: utf-8 -*-
"""Rule that keeps one project copy of a global favorite.

Applying a global favorite (or copying it to the project) imports it into the
project first. Doing it twice must not pile up copies: a project favorite with
the same name and expression is reused. Pure, standard library only.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# ``FavoritesManager.copy_to_global`` appends it, ``import_global_to_project`` strips it.
GLOBAL_NAME_SUFFIX = " (Global)"


def project_copy_of_global(global_favorite: Any, project_favorites: Iterable[Any]) -> Optional[Any]:
    """The project favorite that already is a copy of ``global_favorite``, or None.

    Same expression and same name, the name being compared as stored in the
    global list and as ``import_global_to_project`` writes it (without the
    ``" (Global)"`` suffix).
    """
    names = {global_favorite.name, (global_favorite.name or "").replace(GLOBAL_NAME_SUFFIX, "")}
    for favorite in project_favorites:
        if favorite.expression == global_favorite.expression and favorite.name in names:
            return favorite
    return None
