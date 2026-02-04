import pytest
from app.parser.hc_parser import parse_hc, HCProgram
from app.services.metrics_registry import metrics


def test_parse_hc_mission_block():
    code = 'mission alpha {\n  set retries = 3;\n  agent orchestrator do queue("alpha");\n  call memory.store("alpha","ready");\n  remember note "initialized";\n}'
    before = metrics.snapshot()["counters"].get("parser_calls", 0)
    prog = parse_hc(code)
    after = metrics.snapshot()["counters"].get("parser_calls", 0)
    assert isinstance(prog, HCProgram)
    assert len(prog.body) == 1
    m = prog.body[0]
    assert m.kind == "mission"
    assert m.value["id"] == "alpha"
    assert len(m.children) == 4
    kinds = [c.kind for c in m.children]
    assert kinds == ["set", "agent_action", "call", "remember"]
    assert after == before + 1
