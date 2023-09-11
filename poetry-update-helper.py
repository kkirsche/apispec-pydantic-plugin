#!/usr/bin/env python3

""" Poetry Update Helper

This file is a temporary solution to assist with updating packages outside of their
pinned dependency range. This is important as it allows us to lock our build versions
to a predictable range of bug fix releases while still giving us the opportunity to
update them to their latest versions when we would like to.

This file is planned to be replaced by a Poetry plugin once Poetry 2.x is released for
public usage. This feature does not exist in Poetry 1.x.

# https://python-poetry.org/docs/master/plugins/
"""

from argparse import ArgumentParser
from collections.abc import Mapping, Sequence
from functools import reduce
from itertools import chain
from operator import getitem
from os import environ
from pathlib import Path
from shlex import split
from subprocess import run  # nosec
from tomllib import loads
from typing import Any, TypeVar

_T = TypeVar("_T")
InnermostDictValues = list[str] | set[str] | str
InnerValues = dict[str, InnermostDictValues] | str
ExpectedShape = dict[str, InnerValues]


def normalize_value(_obj: _T) -> _T | str:
    match _obj:
        case str():
            return _obj.strip().lower()
        case _:
            return _obj


def load_pyproject(path: Path) -> dict[str, Any]:
    """Load the pyproject.toml file as a dictionary, if it exists.

    Args:
        path: The path of the pyproject.toml file.

    Raises:
        FileNotFoundError: If the path of the pyproject.toml doesn't exist.

    Returns:
        The parsed content of the pyproject.toml file.
    """
    return loads(path.resolve(strict=True).read_text(encoding="utf-8"))


def retrieve_key_from_pyproject(
    contents: Mapping[str, Any], key: str
) -> Mapping[str, Any]:
    """Recursively walks a pyproject.toml mapping to retrieve the desired key.

    A key such as tool.poetry.dependencies is equivalent
    to contents["tool"]["poetry"]["dependencies"]

    Args:
        contents: The mapping representation of the pyproject.toml
        key: The key to retrieve from the contents variable.

    Raises:
        ValueError: Raised if the pyproject.toml structure does not match expectations.

    Returns:
        The key's value.
    """
    key_path = key.split(".")
    return reduce(getitem, key_path, contents)


def get_group_dependencies(contents: Mapping[str, Any], group: str) -> dict[str, Any]:
    if group == "main":
        group_dependencies = contents["tool"]["poetry"]["dependencies"]
    else:
        group_dependencies = contents["tool"]["poetry"]["group"][group]["dependencies"]
    if not isinstance(group_dependencies, dict):
        raise TypeError(
            f"Group dependencies was not a dict, was {type(group_dependencies)}"
        )
    return group_dependencies


def get_group_packages(
    contents: Mapping[str, Any],
    groups: Sequence[str] | None = None,
    except_groups: Sequence[str] = (),
) -> Mapping[str, Any]:
    dependencies: dict[str, dict[str, str]] = {}
    # if no groups, update everything
    if groups is None:
        # we want to begin with the main dependencies before including groups to align
        # with most users expectations of order of events.
        for group in chain(("main",), contents["tool"]["poetry"]["group"]):
            if not isinstance(group, str):
                raise TypeError(f"Group {group=} was not a string, was {type(group)}")
            if group in except_groups:
                continue
            group_dependencies = get_group_dependencies(contents, group)
            dependencies[group] = group_dependencies
    else:
        # for efficiency, when the user filters the groups, just iterate over these, so
        # that we're not wasting compute cycles iterating over stuff we don't need
        for group in groups:
            if group in except_groups:
                continue
            group_dependencies = get_group_dependencies(contents, group)
            dependencies[group] = group_dependencies

    return dependencies


def as_latest(
    contents: ExpectedShape,
    except_packages: set[str],
) -> list[str]:
    """Create a list of version specification strings at the latest version for the
    packages in contents.

    Args:
        contents: The packages dictionary to build the dependency specification from.

    Returns:
        The sorted list of packages.

    Yields:
        The packages used to build the list.
    """
    packages: set[str] = set()
    for package_name, package in contents.items():
        # python isn't actually a dependency
        if normalize_value(package_name) in except_packages:
            continue
        if isinstance(package, dict) and "extras" in package:
            p = f"'{package_name}@latest[{', '.join(package['extras'])}]'"
        else:
            p = f"'{package_name}@latest'"
        packages.add(p)
    return sorted(packages)


if __name__ == "__main__":
    parser = ArgumentParser(description="Update packages using Poetry.")
    parser.add_argument(
        "--group",
        "-g",
        action="extend",
        default=None,
        dest="groups",
        help="Only update this/these group(s).",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--except-group",
        "-e",
        action="extend",
        default=[],
        dest="except_groups",
        help="Don't update this/these group(s) (overrides group).",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--except-package",
        "-x",
        action="extend",
        dest="except_packages",
        help="Exclude these packages from being updated in any group.",
        nargs="+",
        type=str,
    )
    args = parser.parse_args()
    normalized_except_packages = {
        normalize_value(pkg) for pkg in args.except_packages or []
    }
    normalized_except_packages.add("python")

    current_dir = Path(__file__).parent.resolve()
    path = current_dir / "pyproject.toml"
    contents = load_pyproject(path)
    normalized_groups = (
        tuple(normalize_value(group) for group in args.groups)
        if args.groups is not None
        else None
    )
    normalized_except_groups = tuple(
        normalize_value(group) for group in args.except_groups
    )
    group_packages = get_group_packages(
        contents=contents,
        groups=normalized_groups,
        except_groups=normalized_except_groups,
    )
    for group, packages in group_packages.items():
        if group in normalized_except_groups:
            continue
        latest_packages = as_latest(packages, normalized_except_packages)
        packages_str = " ".join(latest_packages)
        if normalize_value(group) == normalize_value("main"):
            cmd = f"poetry add {packages_str}"
        else:
            cmd = f"poetry add --group {group!r} {packages_str}"
        environ["PYTHONWARNINGS"] = "ignore"
        print(f"Upgrading {group=} with command:\n{cmd}")
        run(
            args=split(cmd),
            check=True,
            cwd=current_dir,
            shell=False,  # nosec
            env=environ,
        )
    print("Ensuring all dependencies are at their latest allowed version")
    run(
        args=split("poetry update"),
        check=True,
        cwd=current_dir,
        shell=False,  # nosec
        env=environ,
    )

    try:
        run(
            args=split("taplo format -o indent_string='    ' pyproject.toml"),
            check=True,
            cwd=current_dir,
            shell=False,  # nosec
            env=environ,
        )
    except FileNotFoundError:
        print("taplo is not installed. Skipping formatting.")
        print("to install taplo, view instructions at:")
        print("https://taplo.tamasfe.dev/cli/#installation")
