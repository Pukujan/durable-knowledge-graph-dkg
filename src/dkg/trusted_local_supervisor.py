"""Small host-side root of trust for reviewed trusted-local broker releases.

This module intentionally has no queue/model-controlled Docker surface.  The
only accepted release input is a trusted-author ``BROKER_RELEASE`` directive
for fossil-core and its exact reviewed SHA.  Docker authority is confined here,
outside the broker container.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPOSITORY = "Pukujan/fossil-core"
ORIGINS = frozenset({"https://github.com/Pukujan/fossil-core", "https://github.com/Pukujan/fossil-core.git"})
TRUSTED_AUTHORS = frozenset({"Pukujan"})
SHA = re.compile(r"^[0-9a-f]{40}$")
VOLUME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
FORBIDDEN_MOUNT_NAME = re.compile(r"(?i)(docker|socket|owner|profile|provider|secret|railway|credential|home|drive)")


class SupervisorError(RuntimeError):
    """A fail-closed supervisor policy or host-operation failure."""


@dataclass(frozen=True)
class Release:
    sha: str
    task: str = "BROKER_RELEASE"


@dataclass(frozen=True)
class SupervisorConfig:
    repository_path: Path
    broker_config_file: Path
    broker_name: str = "fossil-trusted-local-broker"
    runtime_network: str = "bridge"
    broker_parent_github_volume: str = "fossil-broker-github-auth"
    worker_codex_volume: str = "fossil-codex-auth"
    worktree_volume: str = "fossil-broker-worktrees"

    def validate(self) -> None:
        if self.runtime_network not in {"bridge"}:
            raise SupervisorError("only the fixed bridge runtime network is allowed")
        if not self.broker_name or "/" in self.broker_name or self.broker_name.startswith("."):
            raise SupervisorError("invalid broker container name")
        for volume in (self.broker_parent_github_volume, self.worker_codex_volume, self.worktree_volume):
            if not VOLUME.fullmatch(volume) or FORBIDDEN_MOUNT_NAME.search(volume):
                raise SupervisorError("mount configuration must contain only named Docker volumes")
        if not self.broker_config_file.is_absolute():
            raise SupervisorError("broker config file must be an absolute owner-local path")


def parse_release_directives(
    comments: Iterable[Mapping[str, Any]], *, trusted_authors: frozenset[str] = TRUSTED_AUTHORS
) -> list[Release]:
    """Return trusted exact releases; all other directive fields are inert."""
    releases: list[Release] = []
    for comment in comments:
        user = comment.get("user")
        if not isinstance(user, Mapping) or user.get("login") not in trusted_authors:
            continue
        for line in str(comment.get("body", "")).splitlines():
            tokens = line.split()
            if not tokens or tokens[0] != "BROKER_RELEASE":
                continue
            fields = dict(token.split("=", 1) for token in tokens[1:] if "=" in token)
            if fields.get("repo") != REPOSITORY:
                continue
            sha = fields.get("reviewed_sha", "")
            if SHA.fullmatch(sha):
                releases.append(Release(sha=sha))
    return releases


class GitHubEvidence(Protocol):
    def checks_successful(self, sha: str) -> bool: ...


class DockerHost(Protocol):
    def run(self, argv: Sequence[str], *, cwd: Path | None = None) -> str: ...


class SubprocessHost:
    """Literal argv runner. No shell, eval, or string command parsing is used."""

    def run(self, argv: Sequence[str], *, cwd: Path | None = None) -> str:
        completed = subprocess.run(list(argv), cwd=cwd, check=False, capture_output=True, text=True)
        if completed.returncode:
            raise SupervisorError("host command failed")
        return completed.stdout.strip()


class GitHubChecks:
    """Read-only GitHub checks reader; token is supervisor-only and never Docker input."""

    def __init__(self, token: str) -> None:
        if not token:
            raise SupervisorError("supervisor GitHub credential is required")
        self._token = token

    def _get(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "fossil-trusted-local-supervisor",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(request, timeout=15) as response:  # fixed GitHub API origin
            return json.loads(response.read().decode("utf-8"))

    def comments(self) -> list[Mapping[str, Any]]:
        """Read the fixed coordination issue; nothing else schedules Docker work."""
        comments: list[Mapping[str, Any]] = []
        try:
            for page in range(1, 101):
                page_data = self._get(
                    f"https://api.github.com/repos/{REPOSITORY}/issues/94/comments?per_page=100&page={page}"
                )
                if not isinstance(page_data, list):
                    raise SupervisorError("GitHub queue response was not a list")
                comments.extend(item for item in page_data if isinstance(item, Mapping))
                if len(page_data) < 100:
                    return comments
        except (HTTPError, OSError, ValueError) as exc:
            raise SupervisorError("trusted release queue is unreadable") from exc
        raise SupervisorError("trusted release queue pagination limit reached")

    def checks_successful(self, sha: str) -> bool:
        if not SHA.fullmatch(sha):
            return False
        try:
            payload = self._get(f"https://api.github.com/repos/{REPOSITORY}/commits/{sha}/check-runs?per_page=100")
        except (HTTPError, OSError, ValueError):
            return False
        checks = payload.get("check_runs") if isinstance(payload, Mapping) else None
        return bool(checks) and all(
            isinstance(check, Mapping)
            and check.get("status") == "completed"
            and check.get("conclusion") == "success"
            for check in checks
        )


def candidate_tag(sha: str) -> str:
    if not SHA.fullmatch(sha):
        raise SupervisorError("reviewed_sha must be exactly 40 lowercase hex characters")
    return f"fossil-trusted-local-broker:reviewed-{sha}"


def _git(host: DockerHost, repository: Path, *arguments: str) -> str:
    return host.run(["git", "-C", str(repository), *arguments])


def verify_origin_and_main(host: DockerHost, config: SupervisorConfig, sha: str) -> None:
    origin = _git(host, config.repository_path, "config", "--get", "remote.origin.url")
    if origin.rstrip("/") not in ORIGINS:
        raise SupervisorError("repository origin is not the fixed fossil-core origin")
    main = _git(host, config.repository_path, "ls-remote", "origin", "refs/heads/main").split()
    if len(main) < 1 or main[0] != sha:
        raise SupervisorError("reviewed_sha is not live origin/main")


def _mount(source: str, target: str, *, readonly: bool = False, bind: bool = False) -> list[str]:
    spec = f"type={'bind' if bind else 'volume'},src={source},dst={target}"
    if readonly:
        spec += ",readonly"
    return ["--mount", spec]


def runtime_argv(config: SupervisorConfig, image: str, *, name: str | None = None) -> list[str]:
    """The only runtime shape: no ports/socket/profile/secrets mounts are expressible."""
    config.validate()
    return [
        "docker", "run", "-d", "--name", name or config.broker_name,
        "--restart", "unless-stopped", "--network", config.runtime_network,
        *_mount(config.broker_parent_github_volume, "/run/fossil/broker-github", readonly=True),
        *_mount(config.worker_codex_volume, "/worker/codex-home", readonly=False),
        *_mount(config.worktree_volume, "/worker/worktrees", readonly=False),
        *_mount(str(config.broker_config_file), "/etc/fossil/broker.json", readonly=True, bind=True),
        image,
    ]


def _image_id(host: DockerHost, image: str) -> str:
    value = host.run(["docker", "image", "inspect", "--format", "{{.Id}}", image])
    if not value:
        raise SupervisorError("could not resolve image identity")
    return value


def _container_image(host: DockerHost, name: str) -> str | None:
    try:
        return host.run(["docker", "container", "inspect", "--format", "{{.Image}}", name]) or None
    except SupervisorError:
        return None


def _container_revision(host: DockerHost, name: str) -> str | None:
    try:
        return host.run(["docker", "container", "inspect", "--format", "{{index .Config.Labels \"org.opencontainers.image.revision\"}}", name]) or None
    except SupervisorError:
        return None


def _running(host: DockerHost, name: str) -> bool:
    try:
        return host.run(["docker", "container", "inspect", "--format", "{{.State.Running}}", name]) == "true"
    except SupervisorError:
        return False


def _remove(host: DockerHost, name: str) -> None:
    try:
        host.run(["docker", "rm", "-f", name])
    except SupervisorError:
        pass


def apply_release(
    release: Release, *, config: SupervisorConfig, host: DockerHost, evidence: GitHubEvidence
) -> str:
    """Build/smoke first, then replace and roll back to a known-good image on failure."""
    config.validate()
    sha = release.sha
    if not SHA.fullmatch(sha):
        raise SupervisorError("malformed reviewed_sha")
    verify_origin_and_main(host, config, sha)
    if not evidence.checks_successful(sha):
        raise SupervisorError("GitHub CI/check evidence absent, unreadable, or non-success")
    if _running(host, config.broker_name) and _container_revision(host, config.broker_name) == sha:
        return "NOOP"

    image = candidate_tag(sha)
    with tempfile.TemporaryDirectory(prefix="fossil-broker-release-") as temporary:
        worktree = Path(temporary) / "source"
        host.run(["git", "-C", str(config.repository_path), "worktree", "add", "--detach", str(worktree), sha])
        try:
            if _git(host, worktree, "rev-parse", "HEAD") != sha:
                raise SupervisorError("detached build worktree revision mismatch")
            if _git(host, worktree, "config", "--get", "remote.origin.url").rstrip("/") not in ORIGINS:
                raise SupervisorError("detached build worktree origin mismatch")
            host.run(["docker", "build", "--label", f"org.opencontainers.image.revision={sha}", "-t", image, "-f", "docker/trusted-local-broker/Dockerfile", "."], cwd=worktree)
            candidate_id = _image_id(host, image)
            host.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python3", image, "-c", "import dkg"])
        finally:
            host.run(["git", "-C", str(config.repository_path), "worktree", "remove", "--force", str(worktree)])

    previous = _container_image(host, config.broker_name)
    if previous is not None:
        host.run(["docker", "stop", config.broker_name])
        _remove(host, config.broker_name)
    try:
        host.run(runtime_argv(config, image))
        if not _running(host, config.broker_name) or _container_image(host, config.broker_name) != candidate_id or _container_revision(host, config.broker_name) != sha:
            raise SupervisorError("candidate did not reach requested running image revision")
    except SupervisorError:
        _remove(host, config.broker_name)
        if previous is not None:
            host.run(runtime_argv(config, previous))
        raise
    return "APPLIED"


def load_config(path: Path) -> SupervisorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise SupervisorError("supervisor config must be an object")
    config = SupervisorConfig(
        repository_path=Path(str(raw.get("repository_path", ""))).resolve(),
        broker_config_file=Path(str(raw.get("broker_config_file", ""))).resolve(),
        broker_name=str(raw.get("broker_name", "fossil-trusted-local-broker")),
        runtime_network=str(raw.get("runtime_network", "bridge")),
        broker_parent_github_volume=str(raw.get("broker_parent_github_volume", "fossil-broker-github-auth")),
        worker_codex_volume=str(raw.get("worker_codex_volume", "fossil-codex-auth")),
        worktree_volume=str(raw.get("worktree_volume", "fossil-broker-worktrees")),
    )
    config.validate()
    return config
