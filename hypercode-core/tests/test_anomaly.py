import math
from hypercode.server import z_scores

def test_z_scores_empty():
    assert z_scores([]) == []

def test_z_scores_single():
    zs = z_scores([10.0])
    assert zs == [0.0]

def test_z_scores_basic():
    zs = z_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert len(zs) == 5
    assert abs(sum(zs)) < 1e-6

def test_z_scores_outlier():
    zs = z_scores([1.0, 1.0, 1.0, 100.0])
    assert max(zs) > 2.5
