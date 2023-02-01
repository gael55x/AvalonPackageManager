import keepachangelog # type: ignore
import semver         # type: ignore
import os
import sys
import subprocess
import re
import path

from case.case import getCaseInsensitivePath
from typing    import Optional, Generator, Dict, List, Any, Tuple
from color     import debug


Changelog = Dict[str, str | List[str] | Dict[str, Optional[int]]]


def get_changelog_path(package_dir: str) -> Optional[str]:
    "Get case insensitive path to `CHANGELOG.MD` in `package_dir`"
    
    changelog_path = getCaseInsensitivePath(package_dir + "/" + "CHANGELOG.MD")
    if not os.path.exists(changelog_path):
        return None

    return changelog_path


def get_parsed_changelog(package_dir: str) -> Optional[Dict[str, Any]]:
    "Parse changelog at `package_dir/CHANGELOG.MD`"
    
    changelog_path = get_changelog_path(package_dir)

    if not changelog_path:
        debug(f"[Changelog] CHANGELOG.MD does not exist in {package_dir}.")
        return None

    return keepachangelog.to_dict(changelog_path)


def current_version(package_dir: str) -> Optional[semver.VersionInfo]:
    "Get latest version from `package_dir/CHANGELOG.MD`"
    
    chlog = get_parsed_changelog(package_dir)

    if not chlog:
        return None
    
    versions = chlog.keys()

    if not len(versions):
        debug(f"[Changelog] CHANGELOG.MD has no versions.")
        return None
    
    return semver.VersionInfo.parse(list(versions)[0])
    

def get_changes_after(package_dir: str, compare_version: semver.VersionInfo) -> Generator[Changelog, None, None]:
    "Get versions from `package_dir/CHANGELOG.MD` that are later than `compare_version`"
    
    chlog = get_parsed_changelog(package_dir)

    if not chlog:
        return

    for version in reversed(chlog.keys()):
        if semver.VersionInfo.parse(version) > compare_version:
            yield chlog[version]


def inline_code(match):
    return "\033[35;7m" + match[1] + "\033[27;39m"
            

def prettify_changelogs(logs: List[Tuple[str, List[Changelog]]]) -> bytes:
    buf = ""

    for program in logs:
        if program[1]:
            if program[0]:
                buf += "\033[1;4m"
                buf += program[0]
                buf += "\033[0m\n\n"
            
            for version in program[1]:
                buf += "\033[1;4m"
                buf += str(version["version"])
                buf += " \033[2m"
                buf += str(version["release_date"]).replace("[yanked]", "\033[31m[YANKED]\033[37m")
                buf += "\033[0m\n\n"

                for changes in ["deprecated", "added", "changed", "removed", "fixed", "security"]:
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

            
def display_changelogs(logs: List[Tuple[str, List[Changelog]]]) -> None:
    
    i = prettify_changelogs(logs)
    if len(i) > 0:
        p = subprocess.Popen(["less", "-r"],
                             stdin=subprocess.PIPE)

        p.communicate(input = i)

        p.wait()


def get_package_versions(packages: List[str]) -> List[Tuple[str, semver.VersionInfo]]:
    out = []
    
    for package in packages:
        ver = current_version(path.srcpath + "/" + package.lower())
        out.append((package, ver if ver else semver.VersionInfo.parse("0.0.0")))

    return out
    
    
def display_changelogs_packages(packages: List[Tuple[str, Optional[semver.VersionInfo]]]) -> None:
    display_changelogs([(
        package,
        list(get_changes_after(path.srcpath + "/" + package.lower(),
                               startver))
    ) for package, startver in packages])


# display_changelogs_packages(get_package_versions(["r2boyo25/avalonpackagemanager", "r2boyo25/cliparse"]))