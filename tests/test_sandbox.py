"""Tests for LocalSandbox."""
import os
import pytest

from finders.sandbox import LocalSandbox, GrepMatch


@pytest.fixture
def sandbox(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return LocalSandbox(ws)


@pytest.fixture
def sandbox_with_skills(tmp_path):
    """Sandbox with user_skill_dir and project_skill_dir."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    user_skill_dir = tmp_path / "user" / ".finders" / "skills"
    user_skill_dir.mkdir(parents=True)
    (user_skill_dir / "code-review" / "SKILL.md").parent.mkdir(parents=True)
    (user_skill_dir / "code-review" / "SKILL.md").write_text("# code-review", encoding="utf-8")
    project_skill_dir = tmp_path / "project" / ".finders" / "skills"
    project_skill_dir.mkdir(parents=True)
    (project_skill_dir / "web-research" / "SKILL.md").parent.mkdir(parents=True)
    (project_skill_dir / "web-research" / "SKILL.md").write_text("# web-research", encoding="utf-8")
    return LocalSandbox(ws, user_skill_dir=user_skill_dir, project_skill_dir=project_skill_dir)


def test_read_file_success(sandbox):
    target = sandbox.workspace / "test.txt"
    target.write_text("hello world", encoding="utf-8")
    assert sandbox.read_file("test.txt") == "hello world"


def test_read_file_not_found(sandbox):
    with pytest.raises(FileNotFoundError):
        sandbox.read_file("missing.txt")


def test_read_file_absolute_path(sandbox):
    target = sandbox.workspace / "test.txt"
    target.write_text("hello world", encoding="utf-8")
    assert sandbox.read_file(str(target)) == "hello world"


def test_write_file_creates_file(sandbox):
    sandbox.write_file("sub/dir/file.txt", "content")
    target = sandbox.workspace / "sub" / "dir" / "file.txt"
    assert target.read_text(encoding="utf-8") == "content"


def test_write_file_outside_workspace(sandbox):
    with pytest.raises(PermissionError):
        sandbox.write_file("/etc/passwd", "bad")


def test_edit_file_success(sandbox):
    target = sandbox.workspace / "edit.txt"
    target.write_text("old content", encoding="utf-8")
    sandbox.edit_file("edit.txt", "old", "new")
    assert target.read_text(encoding="utf-8") == "new content"


def test_edit_file_old_string_not_found(sandbox):
    target = sandbox.workspace / "edit.txt"
    target.write_text("content", encoding="utf-8")
    with pytest.raises(ValueError):
        sandbox.edit_file("edit.txt", "missing", "new")


def test_edit_file_readonly_path(sandbox):
    target = sandbox.workspace / "edit.txt"
    target.write_text("old content", encoding="utf-8")
    with pytest.raises(PermissionError):
        sandbox.edit_file("/etc/some_file.txt", "old", "new")


def test_list_dir(sandbox):
    (sandbox.workspace / "a.txt").write_text("a", encoding="utf-8")
    (sandbox.workspace / "b").mkdir()
    (sandbox.workspace / "b" / "c.txt").write_text("c", encoding="utf-8")
    entries = sandbox.list_dir(".", max_depth=2)
    assert any("a.txt" in e for e in entries)
    assert any("b/" in e for e in entries)
    assert any("c.txt" in e for e in entries)


def test_glob(sandbox):
    (sandbox.workspace / "foo.py").write_text("x", encoding="utf-8")
    (sandbox.workspace / "bar.txt").write_text("y", encoding="utf-8")
    matches, truncated = sandbox.glob(".", "*.py")
    assert len(matches) == 1
    assert "foo.py" in matches[0]
    assert truncated is False


def test_grep(sandbox):
    (sandbox.workspace / "sample.py").write_text("hello world\nfoo bar\n", encoding="utf-8")
    matches, truncated = sandbox.grep(".", "foo")
    assert len(matches) == 1
    assert matches[0].line_number == 2
    assert "foo" in matches[0].line


def test_execute_echo(sandbox):
    output = sandbox.execute("echo hello")
    assert "hello" in output


def test_write_outside_workspace_blocked(sandbox):
    with pytest.raises(PermissionError):
        sandbox.write_file("/tmp/outside.txt", "bad")


def test_write_to_skill_dir_succeeds(sandbox_with_skills):
    """Writing to user_skill_dir and project_skill_dir should succeed."""
    sandbox_with_skills.write_file(str(sandbox_with_skills.user_skill_dir / "new.txt"), "ok")
    assert sandbox_with_skills.read_file(str(sandbox_with_skills.user_skill_dir / "new.txt")) == "ok"

    sandbox_with_skills.write_file(str(sandbox_with_skills.project_skill_dir / "new.txt"), "ok")
    assert sandbox_with_skills.read_file(str(sandbox_with_skills.project_skill_dir / "new.txt")) == "ok"


def test_read_outside_workspace_allowed(sandbox):
    """Reading files outside workspace should be allowed (read-only)."""
    # Create a file outside workspace
    outside = sandbox.workspace.parent / "outside.txt"
    outside.write_text("outside content", encoding="utf-8")
    assert sandbox.read_file(str(outside)) == "outside content"


def test_finders_workspace_env_var(monkeypatch, tmp_path):
    """Sandbox should read FINDERS_WORKSPACE from env when workspace is None."""
    ws = tmp_path / "env_workspace"
    monkeypatch.setenv("FINDERS_WORKSPACE", str(ws))
    sb = LocalSandbox()
    assert sb.workspace == ws.resolve()
    assert sb.workspace.exists()
