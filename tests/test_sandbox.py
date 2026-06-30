"""Tests for LocalSandbox."""
import os
import pytest

from finders.sandbox import LocalSandbox, GrepMatch, PathMapping


@pytest.fixture
def sandbox(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return LocalSandbox(ws)


@pytest.fixture
def sandbox_with_readonly(tmp_path):
    """Sandbox with a read-only mapping."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    (readonly_dir / "reference.txt").write_text("do not modify", encoding="utf-8")
    mappings = [PathMapping("/readonly", str(readonly_dir), read_only=True)]
    return LocalSandbox(ws, path_mappings=mappings)


@pytest.fixture
def sandbox_with_skills(tmp_path):
    """Sandbox with /user_skill (user skills, read-write) and /proj_skill (project skills, read-write) mappings."""
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


def test_read_file_outside_workspace(sandbox):
    with pytest.raises(PermissionError):
        sandbox.read_file("../outside.txt")


def test_write_file_creates_file(sandbox):
    sandbox.write_file("sub/dir/file.txt", "content")
    target = sandbox.workspace / "sub" / "dir" / "file.txt"
    assert target.read_text(encoding="utf-8") == "content"


def test_write_file_outside_workspace(sandbox):
    with pytest.raises(PermissionError):
        sandbox.write_file("../outside.txt", "bad")


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


def test_security_traversal(sandbox):
    with pytest.raises(PermissionError):
        sandbox.read_file("/../../etc/passwd")


# --- PathMapping tests ---

def test_path_mapping_created(sandbox):
    """Default mapping should be /workspace -> workspace path."""
    assert len(sandbox.path_mappings) >= 1
    default = sandbox.path_mappings[0]
    assert default.container_path == "/workspace"
    assert default.local_path == str(sandbox.workspace)
    assert default.read_only is False


def test_path_mapping_read_only(sandbox_with_readonly):
    """Read-only mapping should prevent writes."""
    sb = sandbox_with_readonly
    with pytest.raises(OSError):
        sb.write_file("../readonly/new.txt", "bad")


# --- Path resolution tests ---

def test_resolve_path_container_to_local(sandbox):
    """Container path /workspace/file.txt should resolve to local workspace path."""
    resolved = sandbox._resolve_path("/workspace/test.txt")
    expected = str(sandbox.workspace / "test.txt")
    assert resolved == expected


def test_resolve_path_plain_path(sandbox):
    """Plain paths (container-style) should be handled via workspace fallback."""
    resolved = sandbox._resolve_path("test.txt")
    assert resolved == "test.txt"


def test_reverse_resolve_path_local_to_container(sandbox):
    """Local workspace path should reverse-resolve to /workspace/..."""
    local_path = str(sandbox.workspace / "test.txt")
    reversed_path = sandbox._reverse_resolve_path(local_path)
    assert reversed_path == "/workspace/test.txt"


def test_reverse_resolve_paths_in_output(sandbox):
    """Output containing local paths should be converted to container paths."""
    local_path = str(sandbox.workspace / "project" / "file.txt")
    output = f"Error in {local_path} at line 5"
    result = sandbox._reverse_resolve_paths_in_output(output)
    assert "/workspace/project/file.txt" in result
    assert str(sandbox.workspace) not in result


# --- Agent written path tracking ---

def test_agent_written_path_tracking(sandbox):
    """write_file should track the resolved path for reverse resolution."""
    sandbox.write_file("tracked.txt", "some content")
    resolved = str(sandbox.workspace / "tracked.txt")
    assert resolved in sandbox._agent_written_paths


def test_read_file_reverse_resolves_agent_content(sandbox):
    """Content written by agent with container paths should be reverse-resolved on read."""
    sandbox.write_file("ref.txt", "see /workspace/other.txt for details")
    content = sandbox.read_file("ref.txt")
    assert "/workspace/other.txt" in content
    assert str(sandbox.workspace) not in content


# --- Content path resolution ---

def test_resolve_paths_in_content(sandbox):
    """Container paths in file content should be resolved to local paths."""
    content = "Import from /workspace/utils.py"
    result = sandbox._resolve_paths_in_content(content)
    # Should start with the local workspace path, not the container path
    assert result.startswith("Import from " + str(sandbox.workspace).replace("\\", "/"))
    # The content "Import from" should be followed by a local path
    assert "C:/" in result or result.startswith("/")


# --- Command path resolution ---

def test_resolve_paths_in_command(sandbox):
    """Container paths in commands should be resolved to local paths."""
    cmd = "cat /workspace/file.txt"
    result = sandbox._resolve_paths_in_command(cmd)
    assert "/workspace" not in result
    assert str(sandbox.workspace) in result


# --- Execute with path resolution ---

def test_execute_with_container_path(sandbox):
    """Execute should resolve container paths in commands."""
    (sandbox.workspace / "exec_test.txt").write_text("exec content", encoding="utf-8")
    # Use cat for reading file content
    output = sandbox.execute("cat /workspace/exec_test.txt")
    assert "exec content" in output


# --- Glob with path resolution ---

def test_glob_reverse_resolves_paths(sandbox):
    """Glob results should use container paths."""
    (sandbox.workspace / "test_glob.py").write_text("x", encoding="utf-8")
    matches, _ = sandbox.glob(".", "*.py")
    assert len(matches) == 1
    # Should contain container path, not local path
    assert "/workspace/test_glob.py" in matches[0]


# --- Grep with path resolution ---

def test_grep_reverse_resolves_paths(sandbox):
    """Grep results should use container paths."""
    (sandbox.workspace / "test_grep.py").write_text("grep test line\n", encoding="utf-8")
    matches, _ = sandbox.grep(".", "grep test")
    assert len(matches) == 1
    assert "/workspace/test_grep.py" in matches[0].path


# --- List dir with path resolution ---

def test_list_dir_reverse_resolves_paths(sandbox):
    """List dir results should use container paths."""
    (sandbox.workspace / "listed.txt").write_text("x", encoding="utf-8")
    entries = sandbox.list_dir(".", max_depth=1)
    assert any("/workspace/listed.txt" in e for e in entries)


# --- Read-only file system ---

def test_read_only_write_file(sandbox_with_readonly):
    """Write to read-only path should raise OSError."""
    sb = sandbox_with_readonly
    with pytest.raises(OSError):
        sb.write_file("../readonly/new.txt", "should fail")


def test_read_only_edit_file(sandbox_with_readonly):
    """Edit read-only path should raise OSError."""
    sb = sandbox_with_readonly
    (sb.workspace / ".." / "readonly" / "ref.txt").parent.resolve()
    # Since readonly is a separate path, use path mapping directly
    readonly_path = sb.path_mappings[1].local_path + "/reference.txt"
    with open(readonly_path, "w") as f:
        f.write("original content")
    with pytest.raises(OSError):
        # The path resolves through the readonly mapping
        sb.edit_file("../readonly/reference.txt", "original", "modified")


# --- /user_skill and /proj_skill virtual path tests ---

def test_skill_mappings_created(sandbox_with_skills):
    """Sandbox should have /workspace, /user_skill, and /proj_skill mappings."""
    containers = [m.container_path for m in sandbox_with_skills.path_mappings]
    assert "/workspace" in containers
    assert "/user_skill" in containers
    assert "/proj_skill" in containers
    user_mapping = next(m for m in sandbox_with_skills.path_mappings if m.container_path == "/user_skill")
    proj_mapping = next(m for m in sandbox_with_skills.path_mappings if m.container_path == "/proj_skill")
    assert user_mapping.read_only is False
    assert proj_mapping.read_only is False


def test_read_project_skill_via_virtual_path(sandbox_with_skills):
    """read_file should resolve /proj_skill/<skill>/SKILL.md to the project skills dir."""
    content = sandbox_with_skills.read_file("/proj_skill/web-research/SKILL.md")
    assert "# web-research" in content


def test_read_user_skill_via_virtual_path(sandbox_with_skills):
    """read_file should resolve /user_skill/<skill>/SKILL.md to the user skills dir."""
    content = sandbox_with_skills.read_file("/user_skill/code-review/SKILL.md")
    assert "# code-review" in content


def test_read_workspace_via_virtual_path(sandbox_with_skills):
    """read_file should resolve /workspace/... to the workspace dir."""
    (sandbox_with_skills.workspace / "note.txt").write_text("hello", encoding="utf-8")
    assert sandbox_with_skills.read_file("/workspace/note.txt") == "hello"


def test_write_to_proj_skill_succeeds(sandbox_with_skills):
    """Writing to /proj_skill (read-write) should succeed."""
    sandbox_with_skills.write_file("/proj_skill/new.txt", "ok")
    assert sandbox_with_skills.read_file("/proj_skill/new.txt") == "ok"


def test_write_to_user_skill_succeeds(sandbox_with_skills):
    """Writing to /user_skill (read-write) should succeed."""
    sandbox_with_skills.write_file("/user_skill/new.txt", "ok")
    assert sandbox_with_skills.read_file("/user_skill/new.txt") == "ok"


def test_proj_skill_traversal_blocked(sandbox_with_skills):
    """Traversal via /proj_skill/../.. should be blocked."""
    with pytest.raises(PermissionError):
        sandbox_with_skills.read_file("/proj_skill/../../etc/passwd")


def test_user_skill_traversal_blocked(sandbox_with_skills):
    """Traversal via /user_skill/../.. should be blocked."""
    with pytest.raises(PermissionError):
        sandbox_with_skills.read_file("/user_skill/../../etc/passwd")


def test_workspace_virtual_path_still_secured(sandbox_with_skills):
    """Traversal via /workspace/.. should be blocked."""
    with pytest.raises(PermissionError):
        sandbox_with_skills.read_file("/workspace/../outside.txt")


def test_finders_workspace_env_var(monkeypatch, tmp_path):
    """Sandbox should read FINDERS_WORKSPACE from env when workspace is None."""
    ws = tmp_path / "env_workspace"
    monkeypatch.setenv("FINDERS_WORKSPACE", str(ws))
    sb = LocalSandbox()
    assert sb.workspace == ws.resolve()
    assert sb.workspace.exists()
