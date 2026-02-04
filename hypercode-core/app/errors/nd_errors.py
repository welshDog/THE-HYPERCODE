from dataclasses import dataclass
from typing import Optional, List


@dataclass
class NDError:
    error_type: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    explanation: Optional[str] = None

    def format(self) -> str:
        parts = []
        emoji = {
            "SyntaxError": "🤔",
            "NameError": "❓",
            "TypeError": "🔧",
            "ValueError": "⚠️",
            "RuntimeError": "💥",
            "UnsupportedError": "🚧",
        }.get(self.error_type, "⚡")
        location = f" at line {self.line}" if self.line else ""
        parts.append(f"\n{emoji} {self.error_type}{location}, BRO!\n")
        parts.append(f"💬 {self.message}\n")
        if self.code_snippet:
            parts.append(f"\n📝 You wrote:\n{self._indent(self.code_snippet)}\n")
            if self.column:
                pointer = " " * (self.column - 1) + "^"
                parts.append(f"{self._indent(pointer)}\n")
        if self.suggestion:
            parts.append(f"\n💡 Quick fix:\n{self._indent(self.suggestion)}\n")
        if self.explanation:
            parts.append(f"\n🧠 Why this matters:\n{self._indent(self.explanation)}\n")
        parts.append("\n✅ Ready to try again? (Press Enter)\n")
        return "".join(parts)

    def _indent(self, text: str, spaces: int = 4) -> str:
        indent = " " * spaces
        return "\n".join(indent + line for line in text.split("\n"))


def _find_similar_names(target: str, candidates: List[str], max_distance: int = 2) -> List[str]:
    def d(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return d(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
    similar = []
    for cand in candidates:
        dist = d(target.lower(), cand.lower())
        if dist <= max_distance:
            similar.append((dist, cand))
    similar.sort(key=lambda x: x[0])
    return [name for _, name in similar]


def create_undefined_name_error(name: str, line: int, available_names: List[str]) -> NDError:
    suggestions = _find_similar_names(name, available_names)
    suggestion_text = None
    if suggestions:
        suggestion_text = f"Did you mean: {', '.join(suggestions[:3])}?"
    explanation = (
        f"The name '{name}' hasn't been defined yet. This usually means:\n"
        f"  • Typo in the variable name\n"
        f"  • Variable defined after it's used\n"
        f"  • Variable defined in a different scope"
    )
    return NDError(
        error_type="NameError",
        message=f"I can't find '{name}' anywhere!",
        line=line,
        suggestion=suggestion_text,
        explanation=explanation,
    )


def create_syntax_error(message: str, line: int, column: int, code_snippet: str) -> NDError:
    explanations = {
        "unexpected eof": (
            "The code ended before I expected it to. Usually this means:\n"
            "  • Missing closing bracket/parenthesis\n"
            "  • Incomplete function definition"
        ),
        "invalid syntax": (
            "Something about this line doesn't follow HyperCode rules.\n"
            "  • Check for missing colons (:) after if/while/for/def\n"
            "  • Check for mismatched quotes\n"
            "  • Check indentation (should be 4 spaces)"
        ),
    }
    explanation = next((exp for pattern, exp in explanations.items() if pattern in message.lower()), "The syntax doesn't match what HyperCode expects.")
    return NDError(
        error_type="SyntaxError",
        message=message,
        line=line,
        column=column,
        code_snippet=code_snippet,
        explanation=explanation,
    )


def create_type_error(operation: str, expected: str, got: str, line: int) -> NDError:
    return NDError(
        error_type="TypeError",
        message=f"Can't do '{operation}' with these types!",
        line=line,
        suggestion=f"Expected {expected}, but got {got}",
        explanation=(
            "Type mismatches happen! Common causes:\n"
            "  • Trying to do math with strings\n"
            "  • Forgetting to convert types (int(), str(), float())\n"
            "  • Using wrong operator for the data type"
        ),
    )


def create_unsupported_error(feature: str, line: int) -> NDError:
    return NDError(
        error_type="UnsupportedError",
        message=f"'{feature}' isn't supported in HyperCode v0.1 yet!",
        line=line,
        explanation=(
            f"HyperCode is growing! '{feature}' is on the roadmap.\n"
            f"  • Check the docs for supported features\n"
            f"  • v0.2 will add more functionality\n"
            f"  • Want to contribute? Join the community!"
        ),
    )


def wrap_interpreter_error(error: Exception, code: str, env_names: List[str]) -> NDError:
    error_type = type(error).__name__
    if isinstance(error, NameError):
        import re
        m = re.search(r"'(.+?)'", str(error))
        if m:
            name = m.group(1)
            return create_undefined_name_error(name, 0, env_names)
    if isinstance(error, SyntaxError):
        return create_syntax_error(str(error), getattr(error, "lineno", 0), getattr(error, "offset", 0), code)
    if isinstance(error, TypeError):
        return create_type_error("operation", "compatible types", "incompatible types", 0)
    return NDError(error_type=error_type, message=str(error), explanation="Something unexpected happened. Check the code and try again!")

