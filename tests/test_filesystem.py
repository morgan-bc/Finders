"""Tests for filesystem tools backed by LocalSandbox."""
import pytest

from finders.tools.filesystem import read_file, write_file, edit_file, list_dir, glob, grep, execute


@pytest.fixture
def tools_sandbox(monkeypatch, tmp_path):
    """Patch the module-level sandbox to use a temp workspace."""
    from finders.tools import filesystem as fs_mod
    from finders.sandbox import LocalSandbox

    original = fs_mod._sandbox
    fs_mod._sandbox = LocalSandbox(tmp_path / "workspace")
    yield fs_mod._sandbox
    fs_mod._sandbox = original


@pytest.mark.asyncio
async def test_read_file_tool(tools_sandbox):
    (tools_sandbox.workspace / "test.txt").write_text("hello", encoding="utf-8")
    result = await read_file.ainvoke({"path": "test.txt"})
    assert result == "hello"


@pytest.mark.asyncio
async def test_write_file_tool(tools_sandbox):
    result = await write_file.ainvoke({"path": "new.txt", "content": "world"})
    assert "Successfully wrote" in result
    assert (tools_sandbox.workspace / "new.txt").read_text(encoding="utf-8") == "world"


@pytest.mark.asyncio
async def test_edit_file_tool(tools_sandbox):
    (tools_sandbox.workspace / "edit.txt").write_text("old", encoding="utf-8")
    result = await edit_file.ainvoke({"path": "edit.txt", "old_string": "old", "new_string": "new"})
    assert "Successfully edited" in result
    assert (tools_sandbox.workspace / "edit.txt").read_text(encoding="utf-8") == "new"


@pytest.mark.asyncio
async def test_list_dir_tool(tools_sandbox):
    (tools_sandbox.workspace / "a.txt").write_text("a", encoding="utf-8")
    result = await list_dir.ainvoke({"path": "."})
    assert "a.txt" in result


@pytest.mark.asyncio
async def test_glob_tool(tools_sandbox):
    (tools_sandbox.workspace / "foo.py").write_text("x", encoding="utf-8")
    result = await glob.ainvoke({"path": ".", "pattern": "*.py"})
    assert "foo.py" in result


@pytest.mark.asyncio
async def test_grep_tool(tools_sandbox):
    (tools_sandbox.workspace / "bar.py").write_text("hello world\n", encoding="utf-8")
    result = await grep.ainvoke({"path": ".", "pattern": "hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_execute_tool():
    result = await execute.ainvoke({"command": "echo test123"})
    assert "test123" in result
