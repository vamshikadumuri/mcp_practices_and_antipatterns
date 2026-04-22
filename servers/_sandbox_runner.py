"""Sandbox runner. Reads user code from stdin, runs it with a curated
__builtins__ and only `mlops` pre-imported, emits JSON result on stdout.
Never import this module into the parent process."""
import builtins, contextlib, io, json, sys, traceback
from mlops_backend import api as mlops

_SAFE_NAMES = [
    "abs","all","any","ascii","bin","bool","bytes","callable","chr",
    "dict","divmod","enumerate","filter","float","format","frozenset",
    "hash","hex","id","int","isinstance","issubclass","iter","len","list",
    "map","max","min","next","oct","ord","pow","print","range","repr",
    "reversed","round","set","slice","sorted","str","sum","tuple","zip",
    "True","False","None","Exception","ValueError","KeyError","TypeError",
    "IndexError","StopIteration","ArithmeticError","ZeroDivisionError",
]
SAFE_BUILTINS = {name: getattr(builtins, name) for name in _SAFE_NAMES}

def main() -> None:
    code = sys.stdin.read()
    buf = io.StringIO()
    env = {"mlops": mlops, "__builtins__": SAFE_BUILTINS}
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<codemode>", "exec"), env)
        payload = {"ok": True, "stdout": buf.getvalue(),
                   "result": repr(env["result"]) if "result" in env else None}
    except BaseException as e:
        payload = {"ok": False,
                   "error": f"{type(e).__name__}: {e}",
                   "traceback": traceback.format_exc(limit=3),
                   "stdout": buf.getvalue()}
    sys.stdout.write(json.dumps(payload))

if __name__ == "__main__":
    main()
