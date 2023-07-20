import keepachangelog  # type: ignore
import semver  # type: ignore
import os
import sys
import subprocess
import re
import datetime
from typing import Optional, Generator, Dict, List, Any, Tuple, Union, Iterable
from pathlib import Path

import apm.path as path
from .case.case import getCaseInsensitivePath
from .log import debug, error

# Define a custom type for the changelog data
Changelog = Dict[str, Union[str, List[str], Dict[str, Optional[int]]]]

# Function to get the case insensitive path to 'CHANGELOG.MD' in 'package_dir'
def get_changelog_path(package_dir: Path) -> Optional[Path]:
    "Get case insensitive path to `CHANGELOG.MD` in `package_dir`"

    changelog_path = Path(
        getCaseInsensitivePath(str((package_dir / "CHANGELOG.MD").absolute()))
    )

    dname = changelog_path.parent

    chlog = Path(getCaseInsensitivePath(str(dname / "CHANGELOG.MD")))
    while not chlog.exists() and str(dname.parent) != "/":
        dname = dname.parent
        chlog = Path(getCaseInsensitivePath(str(dname / "CHANGELOG.MD")))
        if not chlog.exists():
            chlog = Path("/238ghdfg9832hnbjwhgfdsi783rkjf/uwjfgehfsguydsdf")

    if not chlog.exists():
        return None

    return chlog

# Function to parse the changelog at 'package_dir/CHANGELOG.MD'
def get_parsed_changelog(package_dir: Path) -> Optional[Dict[str, Any]]:
    "Parse changelog at `package_dir/CHANGELOG.MD`"

    changelog_path = get_changelog_path(package_dir)

    if not changelog_path:
        debug(f"[Changelog] CHANGELOG.MD does not exist in {package_dir}.")
        return None

    return keepachangelog.to_dict(changelog_path, show_unreleased=True)  # type: ignore

# Function to get the latest version from 'package_dir/CHANGELOG.MD'
def current_version(package_dir: Path) -> Optional[semver.VersionInfo]:
    "Get latest version from `package_dir/CHANGELOG.MD`"

    chlog = get_parsed_changelog(package_dir)

    if not chlog:
        return None

    versions = list(chlog.keys())

    if not len(versions):
        debug(f"[Changelog] CHANGELOG.MD has no versions.")
        return None

    if versions[0] == "unreleased":
        del versions[0]

    return semver.VersionInfo.parse(versions[0])

# Function to get changes in 'package_dir/CHANGELOG.MD' that are later than 'compare_version'
def get_changes_after(
    package_dir: Path, compare_version: semver.VersionInfo
) -> Generator[Changelog, None, None]:
    "Get versions from `package_dir/CHANGELOG.MD` that are later than `compare_version`"

    chlog = get_parsed_changelog(package_dir)

    if not chlog:
        return

    for version in chlog.keys():
        if version == "unreleased":
            continue
        if semver.VersionInfo.parse(version) > compare_version:
            yield chlog[version]

# Helper function to format inline code in changelog entries
def inline_code(match: re.Match[str]) -> str:
    return "\033[35;7m" + match[1] + "\033[27;39m"

# Function to prettify changelogs for display
def prettify_changelogs(logs: Iterable[Tuple[str, Iterable[Changelog]]]) -> bytes:
    buf = ""
    END_SECTION = "\033[0m\n\n"

    for program in logs:
        if program[1]:
            if program[0]:
                buf += "\033[1;4m"
                buf += program[0]
                buf += END_SECTION

            for version in program[1]:
                buf += "\033[1;4m"
                buf += str(version["version"])
                buf += " \033[2m"
                buf += str(version["release_date"]).replace(
                    "[yanked]", "\033[31m[YANKED]\033[37m"
                )
                buf += END_SECTION

                for changes in [
                    "deprecated",
                    "added",
                    "changed",
                    "removed",
                    "fixed",
                    "security",
                ]:
                    if changes in version:
                        buf += "\033[4m"
                        buf += changes.title()
                        buf += "\033[0m\n"

                        for change in version[changes]:
                            buf += " - "
                            buf += re.sub("\`(.*?)\`", inline_code, change)
                            buf += "\n"

                        buf += "\n"

    return bytes(buf, "utf-8")

# Function to display changelogs in a paginated view using 'less'
def display_changelogs(logs: Iterable[Tuple[str, Iterable[Changelog]]]) -> None:

    i = prettify_changelogs(logs)
    if len(i) > 0:
        p = subprocess.Popen(["less", "-r"], stdin=subprocess.PIPE)

        p.communicate(input=i)

        p.wait()

# Function to retrieve the latest version for a list of packages
def get_package_versions(packages: List[str]) -> List[Tuple[str, semver.VersionInfo]]:
    out = []

    for package in packages:
        ver = current_version(path.paths["src"] / package.lower())
        out.append((package, ver if ver else semver.VersionInfo.parse("0.0.0")))

    return out

# Function to display changelogs for specific packages and versions
def display_changelogs_packages(
    packages: Iterable[Tuple[str, Optional[semver.VersionInfo]]]
) -> None:
    display_changelogs(
        [
            (
                package,
                list(get_changes_after(path.paths["src"] / package.lower(), startver)),
            )
            for package, startver in packages
        ]
    )

# Function to bump the version in the 'CHANGELOG.MD' file based on the 'Unreleased' section
def bump_version(part: Optional[str] = None) -> None:
    if not part:
        try:
            keepachangelog.release(get_changelog_path(Path(".")))

        except Exception:
            # FIXME: only catch Exceptions for Unreleased section:
            #        "Release content must be provided within changelog Unreleased section."

            error("No changes provided in `Unreleased` section of `CHANGELOG.MD`")
            exit(1)
        return

    error("`release bump` does not support `part` yet (`keepachangelog` issue).")
    exit(1)

    if part not in ["major", "minor", "patch"]:
        error(f"{part} must be `major`, `minor`, or `patch`")
        exit(1)

    chl = get_parsed_changelog(".")

    if not chl:
        error("There exists no parseable `CHANGELOG.MD` in the current project.")
        exit(1)

    v = current_version(".").next_version(part=part)

    chl[str(v)] = {
        "version": str(v),
        "release_date": datetime.datetime.utcnow().isoformat(" ").split(" ")[0],
    }

# Function to display all changelogs for a list of packages
def display_all_changelogs(packages: List[str]) -> None:
    display_changelogs(
        [
            (
                package,
                list(
                    get_changes_after(
                        path.paths["src"] / package.lower(),
                        semver.VersionInfo.parse("0.0.0"),
                    )
                ),
            )
            for package in packages
        ]
    )
