# -*- coding: utf-8 -*-
"""
Configuration dialog for the git binary used by favorites_sharing.

Lets the user:
- See where the current git binary is resolved from (system / portable /
  configured / missing)
- Type or browse an explicit path
- Download Portable Git on demand (Windows only — admin-free install)
- Remove an existing portable install

The actual download runs on a worker thread so the dialog stays
responsive (50 MB transfer can take 30+ seconds on slow links).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

try:
    from qgis.PyQt.QtCore import QThread, pyqtSignal
    from qgis.PyQt.QtWidgets import (
        QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
        QLineEdit, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
        QWidget,
    )
    HAS_QT = True
except ImportError:  # pragma: no cover - headless test env
    HAS_QT = False

from ..git_resolver import (
    GitResolution,
    GitSource,
    get_portable_git_install_dir,
    is_portable_git_installed,
    resolve_for_extension,
)
from .. import portable_git_installer as installer

logger = logging.getLogger("FilterMate.FavoritesSharing.UI.GitBinary")


def _tr(message: str) -> str:
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("FilterMateGitBinary", message)
    except Exception:
        return message


def _profile_tools_dir() -> str:
    """Resolve ``[QGIS profile]/FilterMate/tools`` from FilterMate env."""
    try:
        from filter_mate.config.config import ENV_VARS  # type: ignore
        base = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY") or ""
        if not base:
            return ""
        return os.path.join(base, "tools")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Worker for the download — lives on its own QThread
# ---------------------------------------------------------------------------


if HAS_QT:

    class PortableGitDownloadWorker(QThread):
        """Run the installer in a worker thread.

        Emits :pyattr:`progress` for each chunk and :pyattr:`finished_ok`
        / :pyattr:`failed` once the install completes.
        """

        progress = pyqtSignal(int, int)  # bytes_so_far, total_bytes_or_-1
        finished_ok = pyqtSignal(str)    # git_executable path
        failed = pyqtSignal(str)         # error message

        def __init__(self, profile_tools_dir: str, force: bool = False):
            super().__init__()
            self._tools_dir = profile_tools_dir
            self._force = force
            self._cancelled = False

        def request_cancel(self) -> None:
            """Cooperative cancel — checked between progress callbacks."""
            self._cancelled = True

        def run(self) -> None:  # noqa: D401 — Qt convention
            def _progress(bytes_so_far: int, total: Optional[int]) -> None:
                if self._cancelled:
                    raise installer.PortableGitError("cancelled by user")
                self.progress.emit(bytes_so_far, total if total is not None else -1)

            try:
                result = installer.download_and_install(
                    profile_tools_dir=self._tools_dir,
                    progress_callback=_progress,
                    force=self._force,
                )
            except installer.PortableGitError as exc:
                self.failed.emit(str(exc))
                return
            except Exception as exc:  # pragma: no cover — last-line safety
                logger.exception("Unexpected installer failure")
                self.failed.emit(f"unexpected error: {exc}")
                return

            if result.success:
                self.finished_ok.emit(result.git_executable)
            else:
                self.failed.emit(
                    result.error_message
                    or result.skipped_reason
                    or "unknown installer failure"
                )


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class GitBinaryConfigDialog(QDialog if HAS_QT else object):
    """Configure the git binary used by favorites_sharing.

    Bound to a live extension instance so it can read/write
    ``git_binary_path`` and resolve the current binary on entry.
    """

    def __init__(self, extension, parent=None):
        if HAS_QT:
            super().__init__(parent)
        self._extension = extension
        self._worker: Optional["PortableGitDownloadWorker"] = None
        if HAS_QT:
            self._setup_ui()
            self._refresh_status()

    # ─── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(_tr("FilterMate — Git Binary"))
        self.setMinimumWidth(620)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        intro = QLabel(_tr(
            "FilterMate uses <b>git</b> to publish favorites to a remote "
            "repository. If git is not on your system PATH, configure an "
            "explicit path below or download a portable copy."
        ))
        intro.setWordWrap(True)
        root.addWidget(intro)

        # Current resolution
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("padding: 6px; background: #f4f4f4;")
        root.addWidget(self._status_label)

        # Explicit path row
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(_tr(
            "Empty = auto-detect (portable → system PATH)"
        ))
        self._path_edit.setText(self._extension.get_git_binary_path() or "")
        path_row.addWidget(self._path_edit, 1)

        browse = QPushButton("…")
        browse.setFixedWidth(32)
        browse.setToolTip(_tr("Browse for git executable"))
        browse.clicked.connect(self._on_browse)
        path_row.addWidget(browse)

        clear = QPushButton(_tr("Clear"))
        clear.clicked.connect(lambda: self._path_edit.setText(""))
        path_row.addWidget(clear)
        root.addLayout(path_row)

        # Apply / Test row
        apply_row = QHBoxLayout()
        self._apply_btn = QPushButton(_tr("Apply path"))
        self._apply_btn.clicked.connect(self._on_apply_path)
        apply_row.addWidget(self._apply_btn)

        self._test_btn = QPushButton("🔌 " + _tr("Test"))
        self._test_btn.setToolTip(_tr("Run 'git --version' against the resolved binary"))
        self._test_btn.clicked.connect(self._on_test)
        apply_row.addWidget(self._test_btn)

        apply_row.addStretch()
        root.addLayout(apply_row)

        # Portable Git section — Windows-only block
        portable_box = QWidget()
        pbox = QVBoxLayout(portable_box)
        pbox.setContentsMargins(0, 8, 0, 0)
        pbox.setSpacing(6)

        meta = installer.get_default_release_metadata()
        portable_header = QLabel(
            "<b>" + _tr("Portable Git") + "</b> — "
            + _tr("download a self-contained git ({0}, no admin rights "
                  "needed) into the QGIS profile.").format(meta["version"])
        )
        portable_header.setWordWrap(True)
        pbox.addWidget(portable_header)

        self._portable_status_label = QLabel("")
        self._portable_status_label.setWordWrap(True)
        pbox.addWidget(self._portable_status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        pbox.addWidget(self._progress_bar)

        portable_btn_row = QHBoxLayout()
        self._dl_btn = QPushButton("⬇ " + _tr("Download Portable Git"))
        self._dl_btn.clicked.connect(self._on_download)
        portable_btn_row.addWidget(self._dl_btn)

        self._reinstall_btn = QPushButton(_tr("Reinstall"))
        self._reinstall_btn.clicked.connect(lambda: self._on_download(force=True))
        portable_btn_row.addWidget(self._reinstall_btn)

        self._remove_btn = QPushButton("🗑 " + _tr("Remove"))
        self._remove_btn.clicked.connect(self._on_remove_portable)
        portable_btn_row.addWidget(self._remove_btn)

        portable_btn_row.addStretch()
        pbox.addLayout(portable_btn_row)

        # Hide the whole portable group on non-Windows hosts
        if not installer.is_supported_platform():
            portable_box.setVisible(False)

        root.addWidget(portable_box)

        # Close
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

    # ─── State refresh ─────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        res: GitResolution = resolve_for_extension(self._extension)
        if res.found:
            color = "#2a7a2a"
            label = {
                GitSource.CONFIGURED: _tr("Configured path"),
                GitSource.PORTABLE: _tr("Portable (downloaded)"),
                GitSource.SYSTEM: _tr("System PATH"),
            }.get(res.source, res.source.value)
            self._status_label.setText(
                f"<span style='color:{color};'>✔ {label}</span> — "
                f"<code>{res.binary_path}</code>"
            )
        else:
            self._status_label.setText(
                "<span style='color:#c33;'>✗ "
                + _tr("git not found")
                + "</span> — "
                + _tr("set a path below or download Portable Git.")
            )

        # Portable subsection state
        tools_dir = _profile_tools_dir()
        installed = bool(tools_dir) and is_portable_git_installed(
            get_portable_git_install_dir(tools_dir)
        )
        if installed:
            self._portable_status_label.setText(
                "<span style='color:#2a7a2a;'>✔ " + _tr("installed") + "</span> — "
                + f"<code>{get_portable_git_install_dir(tools_dir)}</code>"
            )
            self._dl_btn.setVisible(False)
            self._reinstall_btn.setVisible(True)
            self._remove_btn.setVisible(True)
        else:
            self._portable_status_label.setText(
                _tr("not installed")
            )
            self._dl_btn.setVisible(True)
            self._reinstall_btn.setVisible(False)
            self._remove_btn.setVisible(False)

    # ─── Actions ───────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        if not HAS_QT:
            return
        start = self._path_edit.text().strip() or os.path.expanduser("~")
        if os.name == "nt":
            filters = _tr("Git executable (git.exe);;All files (*.*)")
        else:
            filters = _tr("All files (*)")
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("Locate git executable"), start, filters,
        )
        if path:
            self._path_edit.setText(path)

    def _on_apply_path(self) -> None:
        path = self._path_edit.text().strip()
        if path and not os.path.isfile(path):
            QMessageBox.warning(
                self, _tr("Invalid path"),
                _tr("File does not exist:\n{0}").format(path),
            )
            return
        ok = self._extension.set_git_binary_path(path)
        if not ok:
            QMessageBox.warning(
                self, _tr("Save failed"),
                _tr("Could not persist git_binary_path to the extension config."),
            )
            return
        self._refresh_status()

    def _on_test(self) -> None:
        # Apply current field first so the resolver sees the latest value
        self._on_apply_path()
        res = resolve_for_extension(self._extension)
        if not res.found or not res.binary_path:
            QMessageBox.warning(
                self, _tr("git not found"),
                _tr("Cannot find a git binary. Configure a path or "
                    "download Portable Git."),
            )
            return
        import subprocess
        try:
            proc = subprocess.run(
                [res.binary_path, "--version"],
                capture_output=True, text=True, timeout=10, check=False,
            )
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self, _tr("Test failed"),
                _tr("Could not execute {0}:\n{1}").format(res.binary_path, exc),
            )
            return
        except subprocess.TimeoutExpired:
            QMessageBox.warning(
                self, _tr("Test failed"),
                _tr("git --version timed out after 10 s."),
            )
            return

        if proc.returncode == 0:
            QMessageBox.information(
                self, _tr("Test OK"),
                _tr("{0}\n\nResolved from: {1}").format(
                    (proc.stdout or "").strip(), res.detail,
                ),
            )
        else:
            QMessageBox.warning(
                self, _tr("Test failed"),
                _tr("Exit {0}: {1}").format(
                    proc.returncode, (proc.stderr or "").strip(),
                ),
            )

    def _on_download(self, force: bool = False) -> None:
        if not HAS_QT:
            return
        if not installer.is_supported_platform():
            QMessageBox.information(
                self, _tr("Unsupported platform"),
                _tr("Portable Git is Windows-only. Install git via your "
                    "package manager."),
            )
            return
        tools_dir = _profile_tools_dir()
        if not tools_dir:
            QMessageBox.warning(
                self, _tr("Profile not initialized"),
                _tr("Cannot resolve QGIS profile dir — try restarting QGIS."),
            )
            return

        meta = installer.get_default_release_metadata()
        confirm = QMessageBox.question(
            self, _tr("Download Portable Git"),
            _tr("Download {0} (~50 MB) into:\n{1}\n\nContinue?").format(
                meta["filename"],
                get_portable_git_install_dir(tools_dir),
            ),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._set_download_busy(True)
        self._progress_bar.setRange(0, 0)  # indeterminate until first chunk
        self._progress_bar.setVisible(True)
        self._portable_status_label.setText(_tr("Downloading…"))

        worker = PortableGitDownloadWorker(tools_dir, force=force)
        worker.progress.connect(self._on_progress)
        worker.finished_ok.connect(self._on_download_ok)
        worker.failed.connect(self._on_download_failed)
        # Ensure cleanup
        worker.finished_ok.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_progress(self, bytes_so_far: int, total: int) -> None:
        if total > 0:
            if self._progress_bar.maximum() != total:
                self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(bytes_so_far)
            mb_done = bytes_so_far / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._portable_status_label.setText(
                _tr("Downloading… {0:.1f} / {1:.1f} MB").format(mb_done, mb_total)
            )
        else:
            mb_done = bytes_so_far / (1024 * 1024)
            self._portable_status_label.setText(
                _tr("Downloading… {0:.1f} MB").format(mb_done)
            )

    def _on_download_ok(self, git_exe: str) -> None:
        self._set_download_busy(False)
        self._progress_bar.setVisible(False)
        QMessageBox.information(
            self, _tr("Portable Git installed"),
            _tr("Installation complete:\n{0}").format(git_exe),
        )
        self._refresh_status()

    def _on_download_failed(self, message: str) -> None:
        self._set_download_busy(False)
        self._progress_bar.setVisible(False)
        QMessageBox.warning(
            self, _tr("Download failed"),
            _tr("Portable Git could not be installed:\n\n{0}").format(message),
        )
        self._refresh_status()

    def _on_remove_portable(self) -> None:
        confirm = QMessageBox.question(
            self, _tr("Remove Portable Git"),
            _tr("Delete the bundled Portable Git directory?"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        tools_dir = _profile_tools_dir()
        ok = installer.remove_install(tools_dir)
        if not ok:
            QMessageBox.warning(
                self, _tr("Removal failed"),
                _tr("Could not delete the Portable Git directory. "
                    "Check that no QGIS process is using it and retry."),
            )
        self._refresh_status()

    def _set_download_busy(self, busy: bool) -> None:
        self._dl_btn.setEnabled(not busy)
        self._reinstall_btn.setEnabled(not busy)
        self._remove_btn.setEnabled(not busy)
        self._apply_btn.setEnabled(not busy)
        self._test_btn.setEnabled(not busy)

    # ─── Lifecycle ─────────────────────────────────────────────────────

    def closeEvent(self, event):  # type: ignore[override]
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.request_cancel()
            try:
                worker.progress.disconnect()
                worker.finished_ok.disconnect()
                worker.failed.disconnect()
            except (TypeError, RuntimeError):
                pass
            worker.wait(20_000)
        super().closeEvent(event)
