#!/usr/bin/env python3
import os
import sys
import urllib.parse

from github import Auth, Github, GithubException
from github.Environment import Environment

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _ensure_environment(repo, name):
    if name is None:
        return None
    try:
        return repo.get_environment(name)
    except GithubException as e:
        if e.status == 404:
            try:
                env_name = urllib.parse.quote(name, safe="")
                headers, data = repo._requester.requestJsonAndCheck(
                    "PUT", f"{repo.url}/environments/{env_name}"
                )
                if "url" not in data:
                    data["url"] = f"{repo.url}/environments/{env_name}"
                return Environment(repo._requester, headers, data, completed=True)
            except GithubException as ce:
                if ce.status == 403:
                    return None
                raise
        if e.status == 403:
            return None
        raise


def _set_secret(repo, environment, name, value):
    if environment is not None:
        env = repo.get_environment(environment)
        env.create_secret(name, value)
    else:
        repo.create_secret(name, value)


def _set_variable(repo, environment, name, value):
    source = repo.get_environment(environment) if environment is not None else repo
    try:
        source.create_variable(name, value)
    except GithubException as e:
        if e.status != 409:
            raise
        source.get_variable(name).edit(value)


def _delete_all_secrets(source):
    deleted = []
    for secret in list(source.get_secrets()):
        name = secret.name
        source.delete_secret(name)
        deleted.append(f"secret:{name}")
    return deleted


def _delete_all_variables(source):
    deleted = []
    for var in list(source.get_variables()):
        name = var.name
        source.delete_variable(name)
        deleted.append(f"var:{name}")
    return deleted


def clean_repo_secrets(repo, environment=None):
    deleted = []
    for name in _delete_all_secrets(repo) + _delete_all_variables(repo):
        deleted.append(f"repo:{name}")

    envs = []
    try:
        envs = list(repo.get_environments())
    except GithubException as e:
        if e.status not in (403, 404):
            raise
        if environment:
            try:
                envs = [repo.get_environment(environment)]
            except GithubException as ge:
                if ge.status not in (403, 404):
                    raise

    for env in envs:
        env_name = getattr(env, "name", None) or environment or "?"
        try:
            target = repo.get_environment(env_name)
            for name in _delete_all_secrets(target) + _delete_all_variables(target):
                deleted.append(f"{env_name}:{name}")
            repo.delete_environment(env_name)
            deleted.append(f"env:{env_name}")
        except GithubException as e:
            if e.status in (403, 404):
                continue
            raise
    return deleted


def _sync_repo(repo, environment, deploy_user, deploy_host, ssh_key):
    env_name = None
    if environment:
        env = _ensure_environment(repo, environment)
        env_name = environment if env is not None else None
    _set_variable(repo, env_name, "DEPLOY_USER", deploy_user)
    _set_variable(repo, env_name, "DEPLOY_HOST", deploy_host)
    _set_secret(repo, env_name, "DEPLOY_SSH_KEY", ssh_key)
    scope = env_name or "repo"
    print(f"ok: {repo.full_name} ({scope})")


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def _repo_names(gh_cfg):
    raw = gh_cfg.get("repos", gh_cfg.get("repo"))
    if raw is None:
        return None
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    return [str(x).strip() for x in raw if str(x).strip()]


def _full_name(login, name):
    return name if "/" in name else f"{login}/{name}"


def _iter_repos(g, names):
    login = g.get_user().login
    for name in names:
        yield g.get_repo(_full_name(login, name))


def clean_all_repo_secrets_and_variables(g, environment, names):
    failed = 0
    for repo in _iter_repos(g, names):
        try:
            deleted = clean_repo_secrets(repo, environment)
            print(f"ok: {repo.full_name} deleted={deleted or []}")
        except GithubException as e:
            failed += 1
            print(f"fail: {repo.full_name}: {e}", file=sys.stderr)
    if failed:
        sys.exit(1)


def sync_all_repo_secrets_and_variables(g, environment, deploy_user, deploy_host, ssh_key, names):
    failed = 0
    for repo in _iter_repos(g, names):
        try:
            _sync_repo(repo, environment, deploy_user, deploy_host, ssh_key)
        except GithubException as e:
            failed += 1
            print(f"fail: {repo.full_name}: {e}", file=sys.stderr)
    if failed:
        sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if a != "--clean-vars"]
    clean_vars = "--clean-vars" in sys.argv[1:]
    path = (
        args[0]
        if args
        else os.environ.get("DEPLOY_GITHUB_CONFIG", "deploy-github.toml")
    )
    cfg = load_config(path)
    gh = cfg.get("github") or {}
    dep = cfg.get("deploy") or {}
    token = gh.get("token")
    environment = dep.get("environment")
    if not token:
        print("配置 github.token", file=sys.stderr)
        sys.exit(1)

    g = Github(auth=Auth.Token(token))
    names = _repo_names(dep)
    if not names:
        print("配置 deploy.repos", file=sys.stderr)
        sys.exit(1)

    deploy_user = dep.get("user")
    deploy_host = dep.get("host")
    ssh_key_file = dep.get("ssh_key_file")
    ssh_key = dep.get("ssh_key")
    if not deploy_user or not deploy_host:
        print("配置 deploy.user 与 deploy.host", file=sys.stderr)
        sys.exit(1)
    if bool(ssh_key_file) == bool(ssh_key):
        print("deploy.ssh_key_file 与 deploy.ssh_key 必须且只能配置一个", file=sys.stderr)
        sys.exit(1)
    if ssh_key_file:
        kpath = ssh_key_file
        if not os.path.isabs(kpath):
            base = os.path.dirname(os.path.abspath(path))
            kpath = os.path.normpath(os.path.join(base, kpath))
        with open(kpath, encoding="utf-8") as f:
            ssh_key = f.read()

    clean_all_repo_secrets_and_variables(g, environment, names)
    sync_all_repo_secrets_and_variables(
        g, environment, deploy_user, deploy_host, ssh_key, names
    )


if __name__ == "__main__":
    main()
