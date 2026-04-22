from servers.sandbox import run_sandboxed

def test_sandbox_runs_basic_code():
    out = run_sandboxed("print(2 + 2)")
    assert out.strip() == "4"

def test_sandbox_returns_result_variable():
    out = run_sandboxed("result = sum(range(10))")
    assert "45" in out

def test_sandbox_has_mlops_preimported():
    out = run_sandboxed("print(len(mlops.list_models()))")
    assert out.strip() == "5"

def test_sandbox_blocks_import_statement():
    out = run_sandboxed("import os\nprint(os.getcwd())")
    assert out.startswith("ERROR:")
    assert "__import__" in out or "ImportError" in out or "NameError" in out

def test_sandbox_blocks_open_builtin():
    out = run_sandboxed("open('/etc/passwd')")
    assert out.startswith("ERROR:") and "open" in out

def test_sandbox_blocks_eval_and_exec():
    assert run_sandboxed("eval('1+1')").startswith("ERROR:")
    assert run_sandboxed("exec('print(1)')").startswith("ERROR:")

def test_sandbox_enforces_timeout():
    out = run_sandboxed("while True: pass", timeout=1.0)
    assert "timeout" in out.lower()

def test_sandbox_isolates_state_between_calls():
    run_sandboxed("result = 42")
    out = run_sandboxed("print(result)")
    assert out.startswith("ERROR:") or "NameError" in out
