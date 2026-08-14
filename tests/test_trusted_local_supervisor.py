from __future__ import annotations

from pathlib import Path

import pytest

from fossil_core.trusted_local_supervisor import (
    REPOSITORY,
    Release,
    SupervisorConfig,
    SupervisorError,
    apply_release,
    parse_release_directives,
    runtime_argv,
)


SHA = "a" * 40
OLD_ID = "sha256:old"
NEW_ID = "sha256:new"
REPOSITORY_PATH = Path.cwd() / "supervisor-test-repo"
BROKER_CONFIG_PATH = Path.cwd() / "local" / "broker.json"


class Evidence:
    def __init__(self, value: bool = True):
        self.value = value

    def checks_successful(self, sha: str) -> bool:
        return self.value


class Host:
    def __init__(
        self,
        *,
        smoke_fails: bool = False,
        start_fails: bool = False,
        health_fails: bool = False,
        live_main: str = SHA,
    ):
        self.calls: list[tuple[str, ...]] = []
        self.smoke_fails = smoke_fails
        self.start_fails = start_fails
        self.health_fails = health_fails
        self.live_main = live_main
        self.running = True
        self.health = "healthy"
        self.image = OLD_ID
        self.revision = "b" * 40

    def run(self, argv, *, cwd=None):
        command = tuple(argv)
        self.calls.append(command)
        if command[:4] == ("git", "-C", str(REPOSITORY_PATH), "config"):
            return "https://github.com/Pukujan/fossil-core.git"
        if command[:4] == ("git", "-C", str(REPOSITORY_PATH), "ls-remote"):
            return f"{self.live_main}\trefs/heads/main"
        if command[:2] == ("git", "-C") and command[-2:] == ("rev-parse", "HEAD"):
            return SHA
        if command[:2] == ("git", "-C") and command[-3:] == ("config", "--get", "remote.origin.url"):
            return "https://github.com/Pukujan/fossil-core.git"
        if command[:4] == ("docker", "image", "inspect", "--format"):
            return NEW_ID
        if command[:3] == ("docker", "run", "--rm"):
            if self.smoke_fails:
                raise SupervisorError("smoke failure")
            return ""
        if command[:3] == ("docker", "container", "inspect"):
            template = command[-2]
            if "State.Running" in template:
                return "true" if self.running else "false"
            if "State.Health" in template:
                return self.health if self.running else "none"
            if ".Image" in template:
                if not self.running:
                    raise SupervisorError("container absent")
                return self.image
            if "Labels" in template:
                return self.revision if self.running else ""
        if command[:2] == ("docker", "stop"):
            self.running = False
            return ""
        if command[:3] == ("docker", "rm", "-f"):
            self.running = False
            return ""
        if command[:3] == ("docker", "run", "-d"):
            image = command[-1]
            self.image = NEW_ID if "reviewed-" in image else OLD_ID
            self.revision = SHA if "reviewed-" in image else "b" * 40
            self.running = not (self.start_fails and "reviewed-" in image)
            self.health = "unhealthy" if self.health_fails and "reviewed-" in image else "healthy"
            return "container-id"
        return ""


def config() -> SupervisorConfig:
    return SupervisorConfig(repository_path=REPOSITORY_PATH, broker_config_file=BROKER_CONFIG_PATH)


def comment(*, login="Pukujan", sha=SHA, suffix=""):
    return {"user": {"login": login}, "body": f"BROKER_RELEASE repo={REPOSITORY} reviewed_sha={sha}{suffix}"}


def test_release_directive_requires_trusted_author_and_exact_sha_and_ignores_extra_fields():
    assert parse_release_directives([comment(login="attacker")]) == []
    assert parse_release_directives([comment(sha="main")]) == []
    parsed = parse_release_directives([comment(suffix=" image=evil command='sh' mount=/var/run/docker.sock port=80")])
    assert parsed == [Release(SHA)]


def test_non_main_or_missing_or_failing_ci_fails_closed_before_docker():
    for host, evidence in ((Host(live_main="c" * 40), Evidence()), (Host(), Evidence(False))):
        with pytest.raises(SupervisorError):
            apply_release(Release(SHA), config=config(), host=host, evidence=evidence)
        assert not any(call[:2] == ("docker", "build") for call in host.calls)


def test_candidate_smoke_failure_leaves_old_broker_running():
    host = Host(smoke_fails=True)
    with pytest.raises(SupervisorError):
        apply_release(Release(SHA), config=config(), host=host, evidence=Evidence())
    assert host.running is True and host.image == OLD_ID
    assert not any(call[:2] == ("docker", "stop") for call in host.calls)


def test_replacement_health_failure_removes_candidate_and_rolls_back_old_image():
    host = Host(start_fails=True)
    with pytest.raises(SupervisorError):
        apply_release(Release(SHA), config=config(), host=host, evidence=Evidence())
    assert host.running is True and host.image == OLD_ID
    assert any(call[:3] == ("docker", "rm", "-f") for call in host.calls)
    assert not any(call[:3] == ("docker", "image", "rm") for call in host.calls)


def test_replacement_unhealthy_but_running_rolls_back_old_image():
    host = Host(health_fails=True)
    with pytest.raises(SupervisorError, match="healthy image revision"):
        apply_release(Release(SHA), config=config(), host=host, evidence=Evidence())
    assert host.running is True and host.image == OLD_ID
    assert any("State.Health" in " ".join(call) for call in host.calls)


def test_success_has_no_ports_socket_or_owner_profile_and_duplicate_is_noop():
    host = Host()
    assert apply_release(Release(SHA), config=config(), host=host, evidence=Evidence()) == "APPLIED"
    runtime = next(call for call in host.calls if call[:3] == ("docker", "run", "-d"))
    joined = " ".join(runtime)
    assert "--restart unless-stopped" in joined
    assert "--publish" not in runtime and "-p" not in runtime
    assert "docker.sock" not in joined
    assert f"type=bind,src={BROKER_CONFIG_PATH},dst=/etc/fossil/broker.json,readonly" in runtime
    before = len(host.calls)
    assert apply_release(Release(SHA), config=config(), host=host, evidence=Evidence()) == "NOOP"
    assert len(host.calls) > before
    assert not any(call[:2] == ("docker", "build") for call in host.calls[before:])


def test_mount_config_rejects_socket_owner_profile_or_provider_secret_names():
    for value in ("/var/run/docker.sock", "owner-profile", "provider-secret"):
        bad = SupervisorConfig(REPOSITORY_PATH, BROKER_CONFIG_PATH, worker_codex_volume=value)
        with pytest.raises(SupervisorError):
            runtime_argv(bad, "image")


def test_module_has_no_shell_eval_or_exec_surface():
    source = Path("src/fossil_core/trusted_local_supervisor.py").read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "eval(" not in source
    assert "exec(" not in source
