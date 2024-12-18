"""Repo utils."""

from __future__ import annotations

import os
import threading
import time
from os import PathLike
from pathlib import Path, PurePosixPath

import git
import git.exc
import pathspec
from git import Blob, Commit, Remote
from pathspec import PathSpec
from rich.console import Console

from .. import __env_var_prefix__
from ..lib.llm_config import LlmConfig, llm_run_manager
from ..lib.llm_utils import llm_config_from_env
from ..utils import safe_abs_path

commit_system = """
You are an expert software engineer that generates concise, one-line Git commit messages based on the provided diffs.
Review the provided context and diffs which are about to be committed to a git repo.
Review the diffs carefully.
Generate a one-line commit message for those changes.
The commit message should be structured as follows: <type>: <description>
Use these for <type>: fix, feat, build, chore, ci, docs, style, refactor, perf, test

Ensure the commit message:
- Starts with the appropriate prefix.
- Is in the imperative mood (e.g., "Add feature" not "Added feature" or "Adding feature").
- Does not exceed 72 characters.

Reply only with the one-line commit message, without any additional text, explanations, or line breaks.
""".strip()


ANY_GIT_ERROR = (
    git.exc.ODBError,
    git.exc.GitError,
    OSError,
    IndexError,
    BufferError,
    TypeError,
    ValueError,
)


class GitRepo:
    repo: git.Repo
    ignore_file: Path | None = None
    ignore_spec: PathSpec | None = None
    ignore_ts: float = 0
    ignore_last_check: float = 0
    subtree_only: bool = False
    ignore_file_cache: dict = {}
    git_repo_error: Exception | None = None
    DEFAULT_EXCLUDE: list[str] = ["*.lock"]

    def __init__(
        self,
        console: Console | None = None,
        fnames: list[str] | None = None,
        git_dname: str | None = None,
        attribute_author=False,
        attribute_committer=False,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt: str | None = None,
        subtree_only: bool = False,
        llm_config: LlmConfig | None = None,
    ):
        self.console = console or Console(stderr=True)

        self.normalized_path = {}
        self.tree_files = {}
        self.llm_config = llm_config or llm_config_from_env(prefix=__env_var_prefix__)

        self.attribute_author = attribute_author
        self.attribute_committer = attribute_committer
        self.attribute_commit_message_author = attribute_commit_message_author
        self.attribute_commit_message_committer = attribute_commit_message_committer
        self.commit_prompt = commit_prompt
        self.subtree_only = subtree_only
        self.ignore_file_cache = {}
        self.ignore_lock = threading.Lock()

        if git_dname:
            check_fnames = [git_dname]
        elif fnames:
            check_fnames = fnames
        else:
            check_fnames = ["."]

        repo_paths = []
        for fname in check_fnames:
            fname = Path(fname)
            fname = fname.resolve()

            if not fname.exists() and fname.parent.exists():
                fname = fname.parent

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except ANY_GIT_ERROR:
                pass

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.console.print("[bold red]Files are in different git repos.")
            raise FileNotFoundError

        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitCmdObjectDB)
        self.root = safe_abs_path(self.repo.working_tree_dir)

    def commit(
        self,
        fnames: list[str] | None = None,
        context: str | None = None,
        message: str | None = None,
        gpt_edits: bool = False,
    ) -> tuple[str | None, str] | None:
        if not fnames and not self.repo.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "(no commit message provided)"

        if gpt_edits and self.attribute_commit_message_author:
            commit_message = "gpt: " + commit_message
        elif self.attribute_commit_message_committer:
            commit_message = "gpt: " + commit_message

        full_commit_message = commit_message

        cmd = ["-m", full_commit_message, "--no-verify"]
        if fnames:
            fnames = [str(self.abs_root_path(fn)) for fn in fnames]
            for fname in fnames:
                try:
                    self.repo.git.add(fname)
                except ANY_GIT_ERROR as err:
                    self.console.print(f"[bold red]Unable to add {fname}: {err}")
            cmd += ["--"] + fnames
        else:
            cmd += ["-a"]

        original_user_name = self.repo.config_reader().get_value("user", "name")
        original_committer_name_env = os.environ.get("GIT_COMMITTER_NAME")
        committer_name = f"{original_user_name} (gpt)"

        if self.attribute_committer:
            os.environ["GIT_COMMITTER_NAME"] = committer_name

        if gpt_edits and self.attribute_author:
            original_auther_name_env = os.environ.get("GIT_AUTHOR_NAME")
            os.environ["GIT_AUTHOR_NAME"] = committer_name
        else:
            original_auther_name_env = None

        try:
            self.repo.git.commit(cmd)
            commit_hash = self.get_head_commit_sha(short=True)
            self.console.print(f"[bold]Commit {commit_hash} {commit_message}")
            return commit_hash, commit_message
        except ANY_GIT_ERROR as err:
            self.console.print(f"[bold red]Unable to commit: {err}")
        finally:
            # Restore the env

            if self.attribute_committer:
                if original_committer_name_env is not None:
                    os.environ["GIT_COMMITTER_NAME"] = original_committer_name_env
                else:
                    del os.environ["GIT_COMMITTER_NAME"]

            if gpt_edits and self.attribute_author:
                if original_auther_name_env is not None:
                    os.environ["GIT_AUTHOR_NAME"] = original_auther_name_env
                else:
                    del os.environ["GIT_AUTHOR_NAME"]

    def get_rel_repo_dir(self) -> str | PathLike:
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except ValueError:
            return self.repo.git_dir

    def get_commit_message(self, diffs: str | None, context: str | None = None) -> str:
        if not diffs:
            self.console.print("[bold yellow]Nothing to commit!")
            return ""

        diffs = "# Diffs:\n" + diffs

        content = ""
        if context:
            content += context + "\n"
        content += diffs

        system_content = self.commit_prompt or commit_system
        messages = [
            dict(role="system", content=system_content),
            dict(role="user", content=content),
        ]

        try:
            chat_model = self.llm_config.build_chat_model()
            commit_message = str(
                chat_model.invoke(messages, config=llm_run_manager.get_runnable_config(chat_model.name)).content
            )
        except Exception as e:
            self.console.print(f"[bold red]Failed to generate commit message: {e}")
            commit_message = ""

        if not commit_message:
            self.console.print("[bold red]Failed to generate commit message!")
            return commit_message

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, fnames: list[str] | None = None, exclude: list[str] | None = None):
        # We always want diffs of index and working dir

        if fnames is None:
            fnames = []

        if exclude is None:
            exclude = []

        if not exclude:
            exclude = self.DEFAULT_EXCLUDE

        current_branch_has_commits = False
        try:
            active_branch = self.repo.active_branch
            try:
                commits = self.repo.iter_commits(active_branch)
                current_branch_has_commits = any(commits)
            except ANY_GIT_ERROR:
                pass
        except ANY_GIT_ERROR:
            pass

        if exclude:
            exclude_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.gitwildmatch.GitWildMatchPattern,
                exclude,
            )
        else:
            exclude_spec = None

        diffs: str = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        try:
            if current_branch_has_commits:
                if fnames:
                    args = ["HEAD", "--"] + [
                        fname for fname in fnames if not (exclude_spec and exclude_spec.match_file(fname))
                    ]
                else:
                    args = ["HEAD"]
                    if exclude_spec:
                        args += ["--"] + [":(exclude)" + pattern for pattern in exclude]
                diffs += self.repo.git.diff(*args)
                return diffs

            if fnames:
                wd_args = ["--"] + [fname for fname in fnames if not (exclude_spec and exclude_spec.match_file(fname))]
                index_args = ["--cached"] + wd_args
            else:
                wd_args = []
                index_args = ["--cached"]
                if exclude_spec:
                    wd_args += ["--"] + [":(exclude)" + pattern for pattern in exclude]
                    index_args += ["--"] + [":(exclude)" + pattern for pattern in exclude]

            diffs += self.repo.git.diff(*index_args)
            diffs += self.repo.git.diff(*wd_args)

            return diffs
        except ANY_GIT_ERROR as err:
            self.console.print(f"[bold red]Unable to diff: {err}")

    def diff_commits(self, pretty: bool, from_commit: str, to_commit: str) -> list[str]:
        args = []
        if pretty:
            args += ["--color"]
        else:
            args += ["--color=never"]

        args += [from_commit, to_commit]
        diffs: list[str] = self.repo.git.diff(*args)

        return diffs

    def get_tracked_files(self) -> list[str]:
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None
        except ANY_GIT_ERROR as err:
            self.git_repo_error = err
            self.console.print(f"[bold red]Unable to list files in git repo: {err}")
            self.console.print("Is your git repo corrupted?")
            return []

        files = set()
        if commit:
            if commit in self.tree_files:
                files = self.tree_files[commit]
            else:
                try:
                    for blob in commit.tree.traverse():
                        if isinstance(blob, Blob) and blob.type == "blob":  # blob is a file
                            files.add(blob.path)
                except ANY_GIT_ERROR as err:
                    self.git_repo_error = err
                    self.console.print(f"[bold red]Unable to list files in git repo: {err}")
                    self.console.print("Is your git repo corrupted?")
                    return []
                files = set(self.normalize_path(path) for path in files)
                self.tree_files[commit] = set(files)

        # Add staged files
        index = self.repo.index
        staged_files = [path for path, _ in index.entries.keys()]
        files.update(self.normalize_path(path) for path in staged_files)

        res = [fname for fname in files if not self.ignored_file(fname)]

        return res

    def normalize_path(self, path: str | Path | PathLike) -> str:
        orig_path = path
        res = self.normalized_path.get(orig_path)
        if res:
            return res

        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
        self.normalized_path[orig_path] = path
        return path

    def refresh_ignore(self) -> None:
        if not self.ignore_file or not self.ignore_file.is_file():
            return

        with self.ignore_lock:
            current_time = time.perf_counter()
            if current_time - self.ignore_last_check < 1:
                return
            self.ignore_last_check = current_time

            mtime = self.ignore_file.stat().st_mtime
            if mtime != self.ignore_ts:
                self.ignore_ts = mtime
                self.ignore_file_cache = {}
                lines = self.ignore_file.read_text().splitlines()
                self.ignore_spec = pathspec.PathSpec.from_lines(
                    pathspec.patterns.gitwildmatch.GitWildMatchPattern,
                    lines,
                )

    def ignored_file(self, fname: str) -> bool:
        self.refresh_ignore()

        if fname in self.ignore_file_cache:
            return self.ignore_file_cache[fname]

        result = self.ignored_file_raw(fname)
        self.ignore_file_cache[fname] = result
        return result

    def ignored_file_raw(self, fname: str) -> bool:
        if self.subtree_only:
            fname_path = Path(self.normalize_path(fname))
            try:
                cwd_path = Path.cwd().resolve().relative_to(Path(self.root).resolve())
            except ValueError:
                # Issue #1524
                # ValueError: 'C:\\dev\\squid-certbot' is not in the subpath of
                # 'C:\\dev\\squid-certbot'
                # Clearly, fname is not under cwd... so ignore it
                return True

            if cwd_path not in fname_path.parents and fname_path != cwd_path:
                return True

        if not self.ignore_file or not self.ignore_file.is_file():
            return False

        try:
            fname = self.normalize_path(fname)
        except ValueError:
            return True
        if not self.ignore_spec:
            return False
        return self.ignore_spec.match_file(fname)

    def path_in_repo(self, path: str | Path | PathLike) -> bool:
        if not self.repo:
            return False
        if not path:
            return False

        tracked_files = set(self.get_tracked_files())
        return self.normalize_path(path) in tracked_files

    def abs_root_path(self, path: str | Path | PathLike) -> str:
        res = Path(self.root) / path
        return safe_abs_path(res)

    def get_dirty_files(self) -> list[str]:
        """
        Returns a list of all files which are dirty (not committed), either staged or in the working
        directory.
        """
        dirty_files = set()

        # Get staged files
        staged_files = self.repo.git.diff("--name-only", "--cached").splitlines()
        dirty_files.update(staged_files)

        # Get unstaged files
        unstaged_files = self.repo.git.diff("--name-only").splitlines()
        dirty_files.update(unstaged_files)

        return list(dirty_files)

    def is_dirty(self, path: str | Path | PathLike | None = None) -> bool:
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)

    def get_head_commit(self) -> Commit | None:
        try:
            return self.repo.head.commit
        except ANY_GIT_ERROR:
            return None

    def get_head_commit_sha(self, short: bool = False) -> str | None:
        commit = self.get_head_commit()
        if not commit:
            return
        if short:
            return commit.hexsha[:7]
        return commit.hexsha

    def get_head_commit_message(self, default: str | None = None) -> str | bytes | None:
        commit = self.get_head_commit()
        if not commit:
            return default
        return commit.message

    def create_remote(self, name: str, url: str) -> Remote | ANY_GIT_ERROR:
        try:
            return self.repo.create_remote(name, url)
        except ANY_GIT_ERROR as e:
            return e
