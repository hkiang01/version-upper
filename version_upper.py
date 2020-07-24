import json
import logging
import re
import subprocess
from enum import Enum
from typing import List, Union

import click
from pydantic import BaseModel, DirectoryPath, Field, FilePath

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "version_upper.json"


class Config(BaseModel):
    """The configuration file schema"""

    current_version: str = Field(
        "0.0.0",
        description=("The current version"),
        regex=r"(\d+\.\d+\.\d+(rc\d+)?)|[a-f\d]{40}",
        examples=[
            "0.0.0",
            "0.0.0rc1",
            "57fabefae989244d87b562cc4fd576fb5e4e6933",
        ],
    )
    current_semantic_version: str = Field(
        "0.0.0",
        description=("The current semantic version"),
        regex=r"\d+\.\d+\.\d+",
    )
    files: List[Union[FilePath, DirectoryPath]] = Field(
        [],
        description=(
            "Files and directories wherein version strings will be updated. "
            "Directories will be searched recursively."
        ),
        examples=["app/main.py", "app/module/"],
    )


class BumpPart(str, Enum):
    major = "major"
    minor = "minor"
    patch = "patch"
    rc = "rc"
    commit_hash = "commit_hash"


class VersionUpper(object):
    def __init__(self, config_path: str = DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        try:
            with open(config_path) as f:
                self.config: Config = Config(**json.load(f))
        except FileNotFoundError:
            logger.error(
                f"ERROR: Unable to find config file {config_path}.\n"
                "See below for a sample config:\n"
                f"{Config().json(indent=2)}"
            )
            exit(1)


@click.group(
    help="""A tool to update version strings in files
    using semantic versioning and commit hashes.

    Examples:

    \b
    # bump commit sha version
    version-upper bump commit_sha

    \b
    # bump patch version
    version-upper bump patch

    \b
    # bump patch version as release candidate
    version-upper bump patch --release-candidate

    \b
    # bump minor version
    version-upper bump minor

    \b
    # bump major version
    version-upper bump major


    The config file adheres to the Config Pydantic schema,
    and is named version_conifg.json by default.

    \b
    Here is a sample config:
    {
        "current_version": "0.0.0",
        "current_semantic_version": "0.0.0",
        "files": []
    }
    """,
)
@click.option("--config", default=DEFAULT_CONFIG_FILE, show_default=True)
@click.pass_context
def cli(ctx, config: str):
    ctx.obj = VersionUpper(config_path=config)


@cli.command(help="Prints the config schema in JSON")
def config_schema() -> None:
    print(Config().schema_json(indent=2))


@cli.command(help="Prints a sample config")
def sample_config() -> None:
    print(Config().json(indent=2))


@cli.command(help="Prints the current version")
@click.pass_obj
def current_version(version_upper: VersionUpper) -> None:
    print(version_upper.config.current_version)


@cli.command(help="Prints the current semantic version")
@click.pass_obj
def current_semantic_version(version_upper: VersionUpper) -> None:
    print(version_upper.config.current_semantic_version)


@cli.command(help="Removes rc from the version strings")
@click.pass_obj
def release(version_upper: VersionUpper) -> None:
    config = version_upper.config
    current_version = config.current_version
    commit_hash_pattern = re.compile(r"[\da-f]{40}")
    if commit_hash_pattern.search(current_version):
        logger.error("Canont release if current verison is a commit hash")
        exit(1)

    rc_pattern = re.compile(r"\d+\.\d+\.\d+rc(\d+)")
    if rc_pattern.search(current_version) is None:
        logger.error(
            "Unable to release if current version does not contain rc"
        )
        exit(1)

    new_version_pattern = re.compile(r"(\d+\.\d+\.\d+)rc1")
    new_version = new_version_pattern.search(current_version).group(1)
    __replace_version_strings(version_upper, new_version, new_version)


def __replace_version_strings(
    version_upper: VersionUpper,
    new_version: str,
    new_semantic_version: str = None,
) -> None:
    """Replace version strings in files specified in the config with new_version

    Parameters
    ----------
    version_upper : VersionUpper,
        The click context
    new_version : str
        The new version
    new_semantic_version : str, optional
        The new semantic version,
        by default None
    """
    old_version = version_upper.config.current_version
    for f in version_upper.config.files:
        with open(f, "r") as fp:
            old_content = fp.read()
        if old_version not in old_content:
            logger.error(f"Unable to find {old_version} in {f}")
            exit(1)
        new_content = old_content.replace(old_version, new_version)
        with open(f, "w") as fp:
            fp.write(new_content)
    version_upper.config.current_version = new_version
    if new_semantic_version:
        version_upper.config.current_semantic_version = new_semantic_version
    with open(DEFAULT_CONFIG_FILE, "w") as f:
        f.write(version_upper.config.json(indent=2))


def __bump_commit_hash(version_upper: VersionUpper) -> None:
    """Bump version strings in files to the latest commit hash
    and changes current_version in the config to new version accordingly

    Parameters
    ----------
    version_upper : VersionUpper,
        The click context
    """
    new_version = subprocess.check_output(
        ["git", "log", "-n1", "--format=format:%H"]
    ).decode()
    __replace_version_strings(version_upper, new_version)


def __bump_semantic(
    version_upper: VersionUpper,
    part: BumpPart,
    release_candidate: bool = False,
) -> None:
    """Bumps semantic version or rc in files to the next release candidate.

    If part is major, minor, or patch:
        Corresponding semantic version part is bumped.

    Parameters
    ----------
    version_upper : VersionUpper,
        The click context
    part : BumpPart
        The part to bump
    release_candidate : bool, optional
        If specified, will designate the bumped version as a release candidate.
    """
    config = version_upper.config
    current_semantic_version = config.current_semantic_version
    major_pattern = re.compile(r"(\d+)\.\d+\.\d+")
    minor_pattern = re.compile(r"\d+\.(\d+)\.\d+")
    patch_pattern = re.compile(r"\d+\.\d+\.(\d+)")
    major = int(major_pattern.search(current_semantic_version).group(1))
    minor = int(minor_pattern.search(current_semantic_version).group(1))
    patch = int(patch_pattern.search(current_semantic_version).group(1))

    if part == BumpPart.major:
        new_semantic_version = f"{major+1}.0.0"
        new_version = new_semantic_version
    elif part == BumpPart.minor:
        new_semantic_version = f"{major}.{minor+1}.0"
        new_version = new_semantic_version
    elif part == BumpPart.patch:
        new_semantic_version = f"{major}.{minor}.{patch+1}"
        new_version = new_semantic_version
    elif part == BumpPart.rc:
        current_version = config.current_version
        if "rc" not in current_version:
            new_version = current_version + "rc1"
        else:
            rc_pattern = re.compile(r"\d+\.\d+\.\d+rc(\d+)")
            rc = int(rc_pattern.search(current_version).group(1))
            new_version = current_semantic_version + f"rc{rc+1}"
        new_semantic_version = f"{major}.{minor}.{patch}"
    else:
        logger.error(f"Invalid part {part}")
        exit(1)
    if release_candidate and not part == BumpPart.rc:
        new_version = new_version + "rc1"
    __replace_version_strings(version_upper, new_version, new_semantic_version)


@cli.command(help=("Bumps version strings, updates config."))
@click.option(
    "--release-candidate",
    help="If semantic version being bumped is to be a release candidate.",
    is_flag=True,
)
@click.argument("part", required=True, type=click.Choice(list(BumpPart)))
@click.pass_obj
def bump(
    version_upper: VersionUpper, part: BumpPart, release_candidate: bool,
) -> None:
    if part == BumpPart.commit_hash:
        if release_candidate:
            logger.error(
                "Cannot make a release candidate out of a commit_hash bump"
            )
            exit(1)
        __bump_commit_hash(version_upper)

    elif part in [BumpPart.major, BumpPart.minor, BumpPart.patch, BumpPart.rc]:
        __bump_semantic(version_upper, part, release_candidate)
    else:
        raise RuntimeError(f"Invalid part {part}")


if __name__ == "__main__":
    cli()
