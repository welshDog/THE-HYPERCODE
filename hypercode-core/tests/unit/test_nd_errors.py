from app.errors.nd_errors import (
    create_undefined_name_error,
    create_syntax_error,
    create_type_error,
    create_unsupported_error,
    _find_similar_names,
)


def test_undefined_name_error_with_suggestions():
    available = ["count", "counter", "total", "result"]
    error = create_undefined_name_error("cont", 5, available)
    assert error.error_type == "NameError"
    assert error.line == 5
    assert (error.suggestion and ("count" in error.suggestion or "counter" in error.suggestion))


def test_syntax_error_formatting():
    code_snippet = "if x = 5:"
    error = create_syntax_error("invalid syntax", 1, 6, code_snippet)
    formatted = error.format()
    assert "🤔" in formatted
    assert "📝 You wrote:" in formatted
    assert code_snippet in formatted


def test_type_error_explanation():
    error = create_type_error("addition", "int", "str", 10)
    assert "addition" in error.message
    assert "Type mismatches happen" in error.explanation
    assert error.line == 10


def test_unsupported_feature_helpful():
    error = create_unsupported_error("classes", 15)
    assert "isn't supported" in error.message
    assert "HyperCode is growing" in error.explanation


def test_similar_names_detection():
    candidates = ["variable", "value", "result", "count"]
    similar = _find_similar_names("variabel", candidates, max_distance=2)
    assert "variable" in similar

