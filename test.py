#!/usr/bin/env python3
import os
import sys

from github import Auth, Github, GithubException

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _set_variable(repo, environment, name, value):
    def apply_on(create_fn, get_fn):
        try:
            create_fn(name, value)
        except GithubException as e:
            if e.status not in (409, 422):
                raise
            get_fn(name).edit(value)

    if environment is not None:
        env = repo.get_environment(environment)
        apply_on(env.create_variable, env.get_variable)
    else:
        apply_on(repo.create_variable, repo.get_variable)


def _set_secret(repo, environment, name, value):
    if environment is not None:
        env = repo.get_environment(environment)
        env.create_secret(name, value)
    else:
        repo.create_secret(name, value)


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def main():
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("DEPLOY_GITHUB_CONFIG", "deploy-github.toml")
    )
    cfg = load_config(path)
    gh = cfg.get("github") or {}
    dep = cfg.get("deploy") or {}
    repo = gh.get("repo")
    token = gh.get("token")
    deploy_user = dep.get("user")
    deploy_host = dep.get("host")
    ssh_key_file = dep.get("ssh_key_file")
    ssh_key = dep.get("ssh_key")
    environment = dep.get("environment")
    if not repo:
        print("配置 github.repo 或环境变量 GITHUB_REPOSITORY", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("未找到 token：配置 github.token 或对应 token_env 环境变量", file=sys.stderr)
        sys.exit(1)
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
    g = Github(auth=Auth.Token(token))
    # Then play with your Github objects:
    for repo_obj in g.get_user().get_repos():
        print(repo_obj.name)


    env = environment
    try:
        repo_obj = g.get_repo(str(repo))

        try:
            env11 = repo_obj.get_environment(environment)
        except GithubException as e:
            if e.status != 404:
                raise
            env11 = repo.create_environment(environment)
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        _set_variable(repo_obj, env, "DEPLOY_USER", deploy_user)
        _set_variable(repo_obj, env, "DEPLOY_HOST", deploy_host)
        _set_secret(repo_obj, env, "DEPLOY_SSH_KEY", ssh_key)
    except GithubException as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
