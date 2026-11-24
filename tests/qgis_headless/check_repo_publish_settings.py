#!/usr/bin/env python3
"""Bundle name and commit e-mail of a remote repo entry, in a real QGIS.

The repo editor (fields filled from the entry, saved back, an invalid e-mail
refused), the publish dialog (the bundle name follows the selected repo, a name
typed by the user is kept, a local target goes back to the default) and the
quick publish (bundle name and commit author taken from the default repo entry,
pushed to a local bare remote with the git of the image).

    docker run --rm --init --network none -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_repo_publish_settings.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from qgis.core import QgsApplication

APP = QgsApplication([], True)
APP.initQgis()

from qgis.PyQt.QtWidgets import QDialog, QMessageBox  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("FM_REPO") or HERE.parents[1])

packages = Path(tempfile.mkdtemp(prefix="fm-repo-settings-"))
(packages / "filter_mate").symlink_to(ROOT, target_is_directory=True)
sys.path.insert(0, str(packages))

from filter_mate.extensions.favorites_sharing.remote_repo_manager import (  # noqa: E402
    DEFAULT_BUNDLE_NAME, DEFAULT_COMMIT_EMAIL, RemoteRepo, RemoteRepoManager,
)
from filter_mate.extensions.favorites_sharing.service import CollectionTarget  # noqa: E402
from filter_mate.extensions.favorites_sharing.ui.publish_dialog import PublishFavoritesDialog  # noqa: E402
from filter_mate.extensions.favorites_sharing.ui.repo_manager_dialog import RepoEditDialog  # noqa: E402
from filter_mate.ui.controllers.favorites_extension_bridge import FavoritesExtensionBridge  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    suffix = f" -- {detail}" if not condition and detail else ""
    print(("PASS " if condition else "FAIL ") + name + suffix, flush=True)
    if not condition:
        FAILURES.append(name)


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class FakeExtension:
    def __init__(self, repos, services=None):
        self._repos = list(repos)
        self._services = dict(services or {})

    def get_remote_repos(self):
        return list(self._repos)

    def get_config(self, key, default=None):
        return list(self._repos) if key == "remote_repos" else default

    def set_config(self, key, value, *, persist=True):
        if key == "remote_repos":
            self._repos = list(value)
        return True

    def get_git_binary_path(self):
        return ""

    def get_service(self, name):
        return self._services.get(name)


warnings = []
QMessageBox.warning = staticmethod(lambda *a, **k: warnings.append(a[1:3]) or QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

# ─── Repo editor ────────────────────────────────────────────────────────

repo = RemoteRepo(name="Team", git_url="http://git.example.internal:9082/sig/fav.git",
                  bundle_name="zones", commit_email="sig@team.example")
dlg = RepoEditDialog(repo=repo, existing_names=["Team"])
check("editor shows the bundle name of the entry", dlg._bundle_name_edit.text() == "zones")
check("editor shows the commit e-mail of the entry", dlg._commit_email_edit.text() == "sig@team.example")
check("editor placeholders name the defaults",
      DEFAULT_BUNDLE_NAME in dlg._bundle_name_edit.placeholderText()
      and DEFAULT_COMMIT_EMAIL in dlg._commit_email_edit.placeholderText())
dlg._bundle_name_edit.setText(" parcels ")
dlg._commit_email_edit.setText(" gis@team.example ")
edited = dlg.get_repo()
check("editor saves both fields", (edited.bundle_name, edited.commit_email) == ("parcels", "gis@team.example"),
      repr((edited.bundle_name, edited.commit_email)))

dlg._bundle_name_edit.setText("a/b")
warnings.clear()
dlg._on_accept()
check("editor refuses a bundle name with other characters",
      dlg.result() != QDialog.DialogCode.Accepted and len(warnings) == 1, repr(warnings))
dlg._bundle_name_edit.setText("parcels")
dlg._commit_email_edit.setText("not an e-mail")
warnings.clear()
dlg._on_accept()
check("editor refuses an invalid e-mail", dlg.result() != QDialog.DialogCode.Accepted and len(warnings) == 1,
      repr(warnings))
dlg._commit_email_edit.setText("")
dlg._on_accept()
check("editor accepts an empty e-mail (default)", dlg.result() == QDialog.DialogCode.Accepted)

mgr = RemoteRepoManager(FakeExtension([]))
mgr.save_repos([edited])
check("saved entry keeps both fields",
      (mgr.get_by_name("Team").bundle_name, mgr.get_by_name("Team").commit_email) == ("parcels", "gis@team.example"))

# ─── Publish dialog ─────────────────────────────────────────────────────

work = Path(tempfile.mkdtemp(prefix="fm-publish-"))
local_target = CollectionTarget(collection_dir=str(work / "local_coll"), display_name="Local", is_new=True)
entries = [
    {"name": "Zones", "git_url": "http://git.example.internal:9082/sig/zones.git",
     "local_clone": str(work / "zones"), "bundle_name": "zones", "is_default": True},
    {"name": "Plain", "local_clone": str(work / "plain")},
]
ext = FakeExtension(entries)
ext._services["remote_repos"] = RemoteRepoManager(ext)
sharing = SimpleNamespace(
    extension=ext,
    list_publish_targets=lambda: [local_target],
    has_configured_collections_root=lambda: False,
)
favorites = SimpleNamespace(get_all_favorites=lambda: [])
pub = PublishFavoritesDialog(sharing, favorites)
combo = pub._target_combo


def select(predicate):
    for i in range(combo.count()):
        if predicate(combo.itemData(i)):
            combo.setCurrentIndex(i)
            return True
    return False


check("default repo preselected with its bundle name", pub._bundle_name_edit.text() == "zones",
      pub._bundle_name_edit.text())
select(lambda d: d == "__REPO__:Plain")
check("repo without bundle_name shows the default", pub._bundle_name_edit.text() == DEFAULT_BUNDLE_NAME,
      pub._bundle_name_edit.text())
select(lambda d: d == "__REPO__:Zones")
check("back to the repo with bundle_name", pub._bundle_name_edit.text() == "zones")
select(lambda d: isinstance(d, CollectionTarget))
check("local target goes back to the default", pub._bundle_name_edit.text() == DEFAULT_BUNDLE_NAME,
      pub._bundle_name_edit.text())
pub._bundle_name_edit.setText("my_own")
select(lambda d: d == "__REPO__:Zones")
check("a name typed by the user is kept", pub._bundle_name_edit.text() == "my_own", pub._bundle_name_edit.text())
pub.close()

# ─── Quick publish (real git, local bare remote) ────────────────────────


def quick_publish_checks():
    bare = work / "remote.git"
    git("init", "-q", "--bare", "-b", "main", str(bare))
    seed = work / "seed"
    git("init", "-q", "-b", "main", str(seed))
    (seed / "README.md").write_text("seed\n")
    git("add", "README.md", cwd=seed)
    git("-c", "user.email=s@example.com", "-c", "user.name=S", "commit", "-q", "-m", "seed", cwd=seed)
    git("push", "-q", str(bare), "main", cwd=seed)

    written = {}

    def publish_bundle(**kw):
        written["bundle_filename"] = kw["bundle_filename"]
        os.makedirs(kw["target"].collection_dir, exist_ok=True)
        path = os.path.join(kw["target"].collection_dir, kw["bundle_filename"] + ".fmfav-pack.json")
        Path(path).write_text("{}\n")
        return SimpleNamespace(success=True, bundle_path=path, error_message="")

    qext = FakeExtension([{
        "name": "Quick", "git_url": str(bare), "branch": "main", "local_clone": str(work / "quick"),
        "target_collection": "sig", "bundle_name": "parcels", "commit_email": "sig@team.example", "is_default": True,
    }])
    qext._services["remote_repos"] = RemoteRepoManager(qext)
    qext._services["service"] = SimpleNamespace(publish_bundle=publish_bundle)
    qext.get_default_publish_metadata = lambda: {"author": "Ana <ana@home.example>"}
    messages = []
    ctrl = SimpleNamespace(
        _favorites_service=SimpleNamespace(get_all_favorites=lambda: [SimpleNamespace(id="f1")]),
        count=1, dockwidget=None, tr=lambda s: s,
        _show_warning=lambda m: messages.append(("warning", m)),
        _show_success=lambda m: messages.append(("success", m)),
    )
    bridge = FavoritesExtensionBridge.__new__(FavoritesExtensionBridge)
    bridge._controller = ctrl
    bridge.get_extension = lambda: qext
    bridge.quick_publish_to_default_repo()
    check("quick publish succeeded", messages and messages[-1][0] == "success", repr(messages))
    check("quick publish uses the bundle name of the entry", written.get("bundle_filename") == "parcels", repr(written))
    verify = work / "verify"
    git("clone", "-q", str(bare), str(verify))
    check("bundle pushed under the entry's name",
          (verify / "collections" / "sig" / "parcels.fmfav-pack.json").exists())
    check("commit author: name of the metadata, e-mail of the entry (not the one typed)",
          git("log", "-1", "--format=%an <%ae>", cwd=verify) == "Ana <sig@team.example>",
          git("log", "-1", "--format=%an <%ae>", cwd=verify))


if shutil.which("git"):
    quick_publish_checks()
else:
    print("SKIP quick publish -- no git in this image", flush=True)

print(f"\n{'OK' if not FAILURES else 'FAILED'}: {len(FAILURES)} failure(s)", flush=True)
APP.exitQgis()
sys.exit(1 if FAILURES else 0)
