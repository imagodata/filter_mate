# -*- coding: utf-8 -*-
"""The ``filtermate`` command (standard library only).

    filtermate [options] [project or layers...]   start the application
    filtermate doctor                              say which QGIS runtimes this machine has
    filtermate setup [--yes] [--remove]            install (or remove) a runtime of FilterMate's own
    filtermate version

Everything after the command name goes to the host (``filtermate --help`` lists its options).
"""

import argparse
import json
import sys
from typing import List, Optional

from . import paths, provision, runtime, version

COMMANDS = ("run", "doctor", "setup", "version")

def no_runtime_message() -> str:
    return f"""FilterMate runs on the QGIS libraries (PyQGIS {runtime.MIN_QGIS} or later) and found none on this machine.

  * Install QGIS (https://qgis.org/download), then start FilterMate again; or
  * let FilterMate install a runtime of its own, without administrator rights:
        filtermate setup
  * or name a Python that has PyQGIS:
        {runtime.ENV_OVERRIDE}=/path/to/python filtermate

`filtermate doctor` lists what was tried."""


def _say(text: str = "") -> None:
    print(text, flush=True)


def _confirm(question: str) -> bool:
    if not sys.stdin or not sys.stdin.isatty():
        return False
    try:
        return input(question + " [y/N] ").strip().lower() in ("y", "yes", "o", "oui")
    except (EOFError, KeyboardInterrupt):
        return False


def cmd_version(_args: List[str]) -> int:
    _say(f"FilterMate {version() or '(unknown version)'}")
    return 0


def cmd_doctor(args: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="filtermate doctor", description=cmd_doctor.__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    options = parser.parse_args(args)
    tried = runtime.survey()
    chosen = runtime.choose(tried)
    if options.json:
        _say(json.dumps({
            "filtermate": version(), "home": paths.user_data_dir(),
            "chosen": chosen.command if chosen else None,
            "runtimes": [{"kind": r.kind, "label": r.label, "command": r.command, "usable": r.usable, **r.info}
                         for r in tried]}, indent=1))
        return 0 if chosen else 1
    _say(f"FilterMate {version()}")
    _say(f"Application folder: {paths.user_data_dir()}")
    _say()
    _say("QGIS runtimes:")
    for candidate in tried:
        mark = "->" if candidate is chosen else "  "
        state = "ok " if candidate.usable else "no "
        _say(f" {mark} {state} {candidate.label}")
        _say(f"         {candidate.describe()}")
    _say()
    if chosen is None:
        _say(no_runtime_message())
        return 1
    _say(f"FilterMate starts with: {chosen.label}")
    return 0


cmd_doctor.__doc__ = "Try every QGIS runtime of this machine and say which one FilterMate uses."


def cmd_setup(args: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="filtermate setup",
        description="Install a QGIS runtime of FilterMate's own (conda-forge, through micromamba), "
                    "in the application folder, without administrator rights.")
    parser.add_argument("--yes", "-y", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--remove", action="store_true", help="delete the runtime installed by a previous setup")
    options = parser.parse_args(args)
    folder = paths.runtime_dir()
    if options.remove:
        if provision.installed_runtime() is None and not _exists(folder):
            _say("No runtime of FilterMate's own is installed.")
            return 0
        if not options.yes and not _confirm(f"Delete {folder}?"):
            _say("Nothing deleted.")
            return 1
        try:
            provision.remove()
        except provision.ProvisionError as error:
            print(f"FilterMate: {error}", file=sys.stderr)
            return 1
        _say(f"Deleted {folder}.")
        return 0
    existing = provision.installed_runtime()
    if existing is not None and runtime.probe(existing).usable:
        _say(f"Already installed: {existing.describe()}")
        _say(f"  {folder}")
        return 0
    _say(f"This downloads QGIS from conda-forge into {folder}")
    _say(f"(about 0.8 GB to download, 4.5 GB once installed; {provision.NEEDED_BYTES // 1024 ** 3} GB of free space asked). Nothing else is changed.")
    if not options.yes and not _confirm("Continue?"):
        _say("Nothing installed. Run `filtermate setup --yes` to install without the question.")
        return 1
    try:
        installed = provision.install(log=_say)
    except provision.ProvisionError as error:
        print(f"FilterMate: {error}", file=sys.stderr)
        return 1
    _say(f"Installed: {installed.describe()}")
    _say("Start the application with: filtermate")
    return 0


def _exists(folder: str) -> bool:
    import os
    return os.path.isdir(folder)


def cmd_run(args: List[str]) -> int:
    """Start the host in a QGIS runtime; ``--runtime`` and ``--refresh`` are the launcher's own options."""
    import os
    host_args, refresh, index = [], False, 0
    while index < len(args):
        argument = args[index]
        if argument == "--refresh":
            refresh = True
        elif argument == "--runtime" and index + 1 < len(args):
            index += 1
            os.environ[runtime.ENV_OVERRIDE] = args[index]
        elif argument.startswith("--runtime="):
            os.environ[runtime.ENV_OVERRIDE] = argument.split("=", 1)[1]
        else:
            host_args.append(argument)
        index += 1
    if any(a in ("-h", "--help") for a in host_args):
        # Answered here: the options of the host need no QGIS to be listed, and a machine without one must not be
        # offered an install for a --help.
        from .host.options import build_parser
        build_parser().print_help()
        _say("\nLauncher options:\n  --runtime PYTHON   start in this Python (same as {0})\n"
             "  --refresh          search for a runtime again instead of reusing the last one\n\n"
             "Other commands: filtermate doctor | setup [--remove] | version".format(runtime.ENV_OVERRIDE))
        return 0
    runtime.last_override_failure = None
    chosen = runtime.resolve(refresh=refresh)
    if chosen is None and runtime.last_override_failure is not None:
        failed = runtime.last_override_failure
        print(f"FilterMate: {failed.label} does not start: {failed.describe()}", file=sys.stderr)
        return 1
    if chosen is None:
        print(no_runtime_message(), file=sys.stderr)
        if not _confirm("\nInstall the runtime now?"):
            return 1
        try:
            chosen = provision.install(log=_say)
        except provision.ProvisionError as error:
            print(f"FilterMate: {error}", file=sys.stderr)
            return 1
    code = runtime.launch(chosen, host_args)
    if code == runtime.EXIT_NO_QGIS and not refresh:
        # The QGIS chosen at an earlier launch is gone (uninstalled, its environment deleted): search again, once.
        print(f"FilterMate: {chosen.label} has no PyQGIS any more; searching again.", file=sys.stderr)
        return cmd_run(["--refresh"] + list(args))
    return code


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args and args[0] in COMMANDS else "run"
    if args and args[0] in COMMANDS:
        args = args[1:]
    if command == "run" and args[:1] in (["--version"], ["-V"]):
        command, args = "version", []
    handler = {"run": cmd_run, "doctor": cmd_doctor, "setup": cmd_setup, "version": cmd_version}[command]
    try:
        return int(handler(args) or 0)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
