import json
import logging
import re
import subprocess
import sys
from enum import Enum
from typing import List, Union

import click
from pydantic import BaseModel, DirectoryPath, Field, FilePath, validator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "version-upper.json"
CURRENT_VERSION_PATTERN = (
    r"(?P<current_version>(\d+\.\d+\.\d+(rc\d+)?)|[a-f\d]{40})"
)


class SearchPattern(BaseModel):
    path: str
    # TODO: change SearchPattern.search_pattern type to typing.Pattern
    # See test_pydantic_bug_1269() in tests/test_version_upper.py
    search_pattern: str

    @validator("search_pattern", pre=True)
    def must_contain_current_pattern(cls, v):
        f"""Replaces search_pattern with regex used to bump versions,
        specifically a named capture group defined by the Config schema

        This makes it easy for the user to define a search pattern.
        For example, the following search_pattern:
        ```
        appVersion: {{current_version}}
        ```
        Will become this:
        ```
        appVersion: {CURRENT_VERSION_PATTERN}
        ```

        Parameters
        ----------
        v : Pattern
            The new pattern with the named capture group
        """
        assert (
            v.count("{current_version}") == 1
        ), "search_pattern must have exactly 1 instance of '{current_version}'"
        return v


class Config(BaseModel):
    """The configuration file schema"""

    current_version: str = Field(
        "0.0.0",
        description=("The current version"),
        regex=CURRENT_VERSION_PATTERN,
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
    files: List[Union[FilePath, DirectoryPath, SearchPattern]] = Field(
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
            raise click.FileError(
                config_path,
                "\nSee below for a sample config:\n"
                f"{Config().json(indent=2)}",
            )


@click.group(
    help="""A tool to update version strings in files
    using semantic versioning and commit hashes.

    Examples:

    \b
    # bump commit hash version
    version-upper bump commit_hash

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
    and is named version-upper.json by default.

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
def version_upper(ctx, config: str):
    if ctx.invoked_subcommand not in ["config-schema", "sample-config"]:
        ctx.obj = VersionUpper(config_path=config)


@version_upper.command(help="Prints the config schema in JSON")
def config_schema() -> None:
    click.echo(Config.schema_json())


@version_upper.command(help="Prints a sample config")
def sample_config() -> None:
    click.echo(Config().json(indent=2))


@version_upper.command(help="Prints the current version")
@click.pass_obj
def current_version(version_upper: VersionUpper) -> None:
    click.echo(version_upper.config.current_version)


@version_upper.command(help="Prints the current semantic version")
@click.pass_obj
def current_semantic_version(version_upper: VersionUpper) -> None:
    click.echo(version_upper.config.current_semantic_version)


@version_upper.command(help="Removes rc from the version strings")
@click.pass_obj
def release(version_upper: VersionUpper) -> None:
    config = version_upper.config
    current_version = config.current_version
    rc_pattern = re.compile(r"\d+\.\d+\.\d+rc(\d+)")
    if rc_pattern.search(current_version) is None:
        raise click.ClickException(
            "Unable to release if current version does not contain rc"
        )

    new_version_pattern = re.compile(r"(\d+\.\d+\.\d+)rc.*")
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
        if isinstance(f, SearchPattern):
            curr_file = f.path
            with open(curr_file, "r") as fp:
                content = fp.read()

            # prepare to search for the current version
            # by prepping the pattern used to search for it
            curr_search_pattern = f.search_pattern
            curr_search_pattern = curr_search_pattern.replace(
                "{current_version}", CURRENT_VERSION_PATTERN
            )
            curr_pattern = re.compile(curr_search_pattern)

            # for every match against the `search_pattern` in `path`,
            # replace the current_version named capture group
            # with `new_version`
            match = curr_pattern.search(content)
            while (
                match and match.groupdict()["current_version"] != new_version
            ):
                # get group index of the current_version named capture group
                current_version_grp_idx = list(
                    curr_pattern.groupindex.values()
                )[0]

                # get the positions of the substring to replace
                # with `new_version`
                (start, end) = match.span(current_version_grp_idx)
                content = content[0:start] + new_version + content[end:]

                match = curr_pattern.search(content)
            with open(curr_file, "w") as fp:
                fp.write(content)
        else:
            with open(f, "r") as fp:
                content = fp.read()
            if old_version not in content:
                raise click.ClickException(
                    f"Unable to find {old_version} in {f}"
                )
            new_content = content.replace(old_version, new_version)
            with open(f, "w") as fp:
                fp.write(new_content)
    version_upper.config.current_version = new_version
    if new_semantic_version:
        version_upper.config.current_semantic_version = new_semantic_version
    with open(version_upper.config_path, "w") as f:
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

    if part == BumpPart.rc and release_candidate:
        raise click.BadOptionUsage(
            "release-candidate",
            "Cannot use --release-candidate when bumping rc",
        )

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
    else:
        current_version = config.current_version
        if "rc" not in current_version:
            new_version = current_version + "rc1"
        else:
            rc_pattern = re.compile(r"\d+\.\d+\.\d+rc(\d+)")
            rc = int(rc_pattern.search(current_version).group(1))
            new_version = current_semantic_version + f"rc{rc+1}"
        new_semantic_version = f"{major}.{minor}.{patch}"
    if release_candidate:
        new_version = new_version + "rc1"
    __replace_version_strings(version_upper, new_version, new_semantic_version)


@version_upper.command(help=("Bumps version strings, updates config."))
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
            raise click.BadOptionUsage(
                "release-candidate",
                "Cannot use --release-candidate when bumping commit_hash",
            )
        __bump_commit_hash(version_upper)

    else:
        __bump_semantic(version_upper, part, release_candidate)


def init():
    if __name__ == "__main__":
        sys.exit(version_upper())


init()
