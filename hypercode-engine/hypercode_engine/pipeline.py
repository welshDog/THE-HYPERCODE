import os
import shutil
import subprocess
import tempfile

class Pipeline:
    def __init__(self, target: str, mode: str):
        self.target = target
        self.mode = mode

    def generate(self, ir: dict) -> str:
        v = ir.get("value", "")
        t = self.target
        if t == "python":
            return f"print(\"{v}\")"
        if t in ("javascript", "js"):
            return f"console.log(\"{v}\");"
        if t in ("c++", "cpp"):
            return (
                "#include <iostream>\n"
                "int main(){\n"
                f"  std::cout << \"{v}\" << std::endl;\n"
                "  return 0;\n"
                "}"
            )
        if t == "java":
            return (
                "public class Main {\n"
                "  public static void main(String[] args){\n"
                f"    System.out.println(\"{v}\");\n"
                "  }\n"
                "}"
            )
        return f"print(\"{v}\")"

    def compile_and_run(self, code: str) -> str:
        if self.mode != "compile":
            return code
        t = self.target
        if t == "python":
            p = subprocess.run(["python", "-c", code], capture_output=True, text=True)
            return p.stdout.strip()
        if t in ("javascript", "js"):
            node = shutil.which("node")
            if not node:
                return code
            p = subprocess.run([node, "-e", code], capture_output=True, text=True)
            return p.stdout.strip()
        if t in ("c++", "cpp"):
            gxx = shutil.which("g++")
            if not gxx:
                return code
            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, "main.cpp")
                exe = os.path.join(td, "a.exe" if os.name == "nt" else "a.out")
                with open(src, "w", encoding="utf-8"):
                    pass
                with open(src, "w", encoding="utf-8") as f:
                    f.write(code)
                subprocess.check_call([gxx, src, "-o", exe])
                p = subprocess.run([exe], capture_output=True, text=True)
                return p.stdout.strip()
        if t == "java":
            javac = shutil.which("javac")
            java = shutil.which("java")
            if not javac or not java:
                return code
            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, "Main.java")
                with open(src, "w", encoding="utf-8") as f:
                    f.write(code)
                subprocess.check_call([javac, src])
                p = subprocess.run([java, "-cp", td, "Main"], capture_output=True, text=True)
                return p.stdout.strip()
        return code

