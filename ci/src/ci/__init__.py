"""Dagger CI for medlab-insight.

Parallel to Jenkins: Jenkins still owns orchestration and ArgoCD keeps doing
CD. These functions only build/verify artefacts and bump the GitOps manifest.
"""

import re

from dagger import Directory, Secret, dag, function, object_type

_UV_IMAGE = "ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
_CI_IMAGE = "alpine:3.20"

_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_IMAGE_REF = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,253}$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")
_MANIFEST = re.compile(r"^[A-Za-z0-9._/-]{1,256}$")

_BUMP_SCRIPT = r"""#!/bin/sh
set -eu
: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
git config --global credential.helper \
  '!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f'
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" /repo
cd /repo
sed -i -E "s|^([[:space:]]*image:[[:space:]]*)${IMAGE_REF}:[^[:space:]]*|\1${IMAGE_REF}:${TAG}|" "$MANIFEST"
if ! grep -q "image: ${IMAGE_REF}:${TAG}" "$MANIFEST"; then
  echo "tag substitution failed in $MANIFEST" >&2
  exit 1
fi
if git diff --quiet -- "$MANIFEST"; then
  echo "manifest already points at ${IMAGE_REF}:${TAG}; nothing to commit"
  exit 0
fi
git -c user.name="dagger-ci" -c user.email="ci@medlab.local" \
  commit -am "[Dagger] Update image tag to ${TAG}"
git push origin "HEAD:${BRANCH}"
echo "pushed ${TAG} to ${REPO_URL} (${BRANCH})"
"""


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


# Local-only paths that must never enter the build context or the CI container.
_EXCLUDED_DIRS = (".venv", "mlruns", ".pytest_cache", ".ruff_cache", ".git")


async def _slim(source: Directory) -> Directory:
    present = set(await source.entries())
    for name in _EXCLUDED_DIRS:
        if name in present:
            source = source.without_directory(name)
    return source


async def _build_container(source: Directory):
    return (await _slim(source)).docker_build(dockerfile="Dockerfile")


@object_type
class Ci:
    @function
    async def check(self, source: Directory) -> str:
        """Lint + run the full test suite in a clean uv container."""
        source = await _slim(source)
        ctr = (
            dag.container()
            .from_(_UV_IMAGE)
            .with_mounted_cache("/root/.cache/uv", dag.cache_volume("medlab-uv"))
            .with_directory("/src", source)
            .with_workdir("/src")
            .with_env_variable("UV_LINK_MODE", "copy")
            .with_env_variable("UV_COMPILE_BYTECODE", "0")
            .with_exec(
                [
                    "sh",
                    "-c",
                    "rm -rf agents/gateway/.venv",
                ]
            )
            .with_exec(["uv", "sync", "--frozen", "--extra", "dev"])
            .with_exec(["uv", "run", "ruff", "check", "src", "app", "training", "tests"])
            .with_exec(
                ["uv", "run", "ruff", "format", "--check", "src", "app", "training", "tests"]
            )
            .with_exec(["uv", "run", "pytest", "--cov", "--cov-report=term-missing"])
        )
        return await ctr.stdout()

    @function
    async def build(self, source: Directory, tag: str = "dev") -> str:
        """Build the app image and return its container ID."""
        _require(_TAG.match(tag) is not None, f"invalid tag: {tag!r}")
        image = (await _build_container(source)).with_label(
            "org.opencontainers.image.version", tag
        )
        return await image.id()

    @function
    async def build_push(
        self,
        source: Directory,
        tag: str,
        username: Secret,
        password: Secret,
        image_ref: str = "nguyenphong8852/medlab-insight",
        registry: str = "docker.io",
    ) -> str:
        """Build and push the app image to a registry."""
        _require(_TAG.match(tag) is not None, f"invalid tag: {tag!r}")
        _require(_IMAGE_REF.match(image_ref) is not None, f"invalid image ref: {image_ref!r}")
        authed = (await _build_container(source)).with_registry_auth(
            registry, username, password
        )
        return await authed.publish(f"{image_ref}:{tag}")

    @function
    async def bump_manifest(
        self,
        tag: str,
        token: Secret,
        image_ref: str = "nguyenphong8852/medlab-insight",
        repository: str = "https://github.com/phongnt93/medlab-insight.git",
        branch: str = "main",
        manifest: str = "k8s/base/deployment.yaml",
    ) -> str:
        """Commit the new image tag so ArgoCD can roll it out."""
        _require(_TAG.match(tag) is not None, f"invalid tag: {tag!r}")
        _require(_IMAGE_REF.match(image_ref) is not None, f"invalid image ref: {image_ref!r}")
        _require(_BRANCH.match(branch) is not None, f"invalid branch: {branch!r}")
        _require(
            _MANIFEST.match(manifest) is not None and ".." not in manifest,
            f"invalid manifest path: {manifest!r}",
        )
        _require(
            repository.startswith("https://github.com/")
            or repository.startswith("https://gitlab.com/"),
            "repository must be an https github/gitlab URL",
        )
        return await (
            dag.container()
            .from_(_CI_IMAGE)
            .with_exec(["apk", "add", "--no-cache", "git"])
            .with_secret_variable("GITHUB_TOKEN", token)
            .with_env_variable("TAG", tag)
            .with_env_variable("IMAGE_REF", image_ref)
            .with_env_variable("REPO_URL", repository)
            .with_env_variable("BRANCH", branch)
            .with_env_variable("MANIFEST", manifest)
            .with_new_file("/bump-manifest.sh", _BUMP_SCRIPT, permissions=0o755)
            .with_exec(["sh", "/bump-manifest.sh"])
            .stdout()
        )
