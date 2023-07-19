import os
import sys
import semver  # type: ignore

from typing import Any

from .pmUtil import (
    installPackage,
    uninstallPackage,
    installLocalPackage,
    redoBin,
    updatePackage,
    installed,
    dlSrc,
    updateCache,
    getInstalledRepos,
)
from .path import binpath, srcpath, cachepath, configpath, tmppath, filepath
from CLIParse import Parse  # type: ignore
import CLIParse
from .version import version, cyear
from .changelog import (
    get_package_versions,
    display_changelogs_packages,
    bump_version,
    get_changelog_path,
    get_changes_after,
    display_changelogs,
    display_all_changelogs,
)
from .case.case import getCaseInsensitivePath

before = f"Avalon Package Manager V{version} Copyright (C) {cyear} R2Boyo25"

p = Parse(
    "apm",
    before=before,
    after="NOTE: flags MUST be before command!",
    flagsAsArgumentsAfterCommand=True,
)

p.flag("update", short="U", long="update", help="Reinstall APM dependencies")
p.flag("fresh", short="F", long="fresh", help="Reinstall instead of updating")
p.flag("force", short="f", long="force", help="Force install package.")
p.flag(
    "debug",
    short="d",
    long="debug",
    help="Print debug output (VERY large amount of text)",
)
p.flag(
    "noinstall",
    long="noinstall",
    help="Only download, skip compilation and installation (Debug)",
)
p.flag(
    "machine",
    short="m",
    long="machine",
    help="Disable user-facing features. Use in scripts and wrappers or things might break.",
)


freeze_changelogs = get_package_versions(getInstalledRepos([srcpath]))


def display_changes(machine: bool = False) -> None:
    if not machine:
        display_changelogs_packages(freeze_changelogs)


def create_changelog(path: str) -> None:
    path = getCaseInsensitivePath(path)
    path += "/CHANGELOG.MD"

    dname = os.path.dirname(path)

    chlog = getCaseInsensitivePath(dname + "/CHANGELOG.MD")
    while not os.path.exists(chlog) and os.path.dirname(dname) != "/":
        dname = os.path.dirname(dname)
        chlog = getCaseInsensitivePath(dname + "/CHANGELOG.MD")
        if os.path.exists(chlog):
            return

    if os.path.exists(path):
        return

    with open(path, "w") as f:
        f.write(
            """
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
""".strip()
            + "\n"
        )


@p.command("release")
def releaseSubmenu(_: Any, __: Any, *args: str) -> None:
    "Submenu for interacting with changelogs"

    rp = Parse("apm release", before=before)

    @rp.command("bump")
    def releaseBump(flags: CLIParse.flags.Flags, *args: str) -> None:
        "Bump `CHANGELOG.MD`'s version: major, minor, or patch\nIf `part` not specified, guess based off of `[Unreleased]`"

        create_changelog(os.getcwd())

        bump_version(*args)

    @rp.command("change")
    def releaseChange(flags: CLIParse.flags.Flags, *args: str) -> None:
        "Edit `CHANGELOG.MD` w/ `$VISUAL_EDITOR`"

        create_changelog(os.getcwd())

        visual_editor = os.environ.get(
            "VISUAL_EDITOR", os.environ.get("EDITOR", "nano")
        )

        exit(os.system(f"{visual_editor} {get_changelog_path('.')}"))

    rp.run(args=args)


@p.command("changes")
def packageChanges(flags: CLIParse.flags.Flags, paths: list[str], *args: str) -> None:
    "View changes in `package` since `version`\nchanges [version]\nchanges [package]\nchanges <package> [version]"
    if not len(args):
        changes = get_changes_after(".", semver.VersionInfo.parse("0.0.0"))

        display_changelogs([("", changes)])
        return

    if len(args) == 2:
        version = semver.VersionInfo.parse(args[1])

        display_changelogs_packages([(args[0], version)])
        return

    if args[0] == "all":
        display_all_changelogs(getInstalledRepos([srcpath]))
        return

    if not "/" in args[0]:
        version = semver.VersionInfo.parse(args[0])
        changes = get_changes_after(".", version)

        display_changelogs([("", changes)])
        return

    pkgpath = srcpath + args[0]
    changes = get_changes_after(pkgpath, semver.VersionInfo.parse("0.0.0"))

    display_changelogs([(args[0], changes)])


@p.command("gen")
def genPackage(flags: CLIParse.flags.Flags, paths: list[str], *args: str) -> None:
    "Generate a package using AvalonGen"
    os.system(binpath + "/avalongen " + " ".join([f'"{i}"' for i in sys.argv[2:]]))


@p.command("install")
def installFunction(flags: CLIParse.flags.Flags, paths: list[str], *args: str) -> None:
    "Installs a package"

    installPackage(flags, paths, list(args))

    display_changes(flags.machine)


@p.command("uninstall")
def uninstallFunction(
    flags: CLIParse.flags.Flags, paths: list[str], *args: str
) -> None:
    "Uninstalls a package"
    uninstallPackage(flags, paths, list(args))


@p.command("update", hidden=True)
def updatePackageCLI(*args: Any) -> None:
    "Update to newest version of a repo, then recompile + reinstall program"
    updatePackage(*args)

    display_changes(args[0].machine)


@p.command("refresh")
def refreshCacheFolder(*args: Any) -> None:
    "Refresh main repo cache"

    updateCache(*args)


@p.command("pack")
def genAPM(*args: Any) -> None:
    "Generate .apm file with AvalonGen"
    os.system(
        binpath
        + "/avalongen "
        + "package "
        + " ".join([f'"{i}"' for i in sys.argv[2:]])
    )


@p.command("unpack")
def unpackAPM(*args: Any) -> None:
    "Unpack .apm file with AvalonGen"
    raise NotImplementedError
    # os.system(binpath + '/avalongen ' + "unpack " + " ".join([f"\"{i}\"" for i in sys.argv[2:]]))


@p.command("redobin", hidden=True)
def redoBinCopy(*args: Any) -> None:
    redoBin(*args)


@p.command("installed")
def listInstalled(*args: Any) -> None:
    "List installed packages"

    installed(*args)


@p.command("src")
def dlSrcCli(*args: Any) -> None:
    "Download repo into folder"

    dlSrc(*args)


def main() -> None:

    p.run(extras=[srcpath, binpath, cachepath, configpath, filepath, tmppath])