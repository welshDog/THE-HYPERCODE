import argparse
import sys
import time

def _eval_source(src: str) -> str:
    s = src.strip()
    if s.lower().startswith("print "):
        return s[6:].strip().strip('"').strip("'")
    return s

def main():
    parser = argparse.ArgumentParser(prog="hypercode")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("file")
    p_eval = sub.add_parser("eval")
    p_eval.add_argument("-e", "--expr", required=True)
    args = parser.parse_args()
    t0 = time.time()
    try:
        if args.cmd == "run":
            with open(args.file, "r", encoding="utf-8") as f:
                out = _eval_source(f.read())
        else:
            out = _eval_source(args.expr)
        sys.stdout.write(out)
        sys.stdout.flush()
        return 0
    except Exception as e:
        sys.stderr.write(str(e))
        sys.stderr.flush()
        return 1
    finally:
        _ = time.time() - t0

if __name__ == "__main__":
    code = main()
    sys.exit(code)

