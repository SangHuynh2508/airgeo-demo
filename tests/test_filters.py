import random
import statistics

from airgeo.filters import MovingAverage, NoFilter, OneEuro


def _noisy_still(n=300, sigma=3.0):
    # Tay "đứng yên" ở (100, 100), nhiễu ±3 px, 30 Hz
    random.seed(0)
    return [(100 + random.gauss(0, sigma), 100 + random.gauss(0, sigma), i / 30) for i in range(n)]


def _std_x(f, samples):
    return statistics.pstdev([f.filter(*s)[0] for s in samples][30:])


def test_one_euro_halves_jitter_when_still():
    s = _noisy_still()
    assert _std_x(OneEuro(), s) < _std_x(NoFilter(), s) / 2


def test_moving_average_is_mean_of_window():
    f = MovingAverage(3)
    for x in (0, 3, 6):
        out = f.filter(x, 0, 0)
    assert out == (3.0, 0.0)
    assert f.filter(9, 0, 0) == (6.0, 0.0)


def test_moving_average_set_n_keeps_recent_points():
    f = MovingAverage(5)
    for x in range(5):
        f.filter(x, 0, 0)
    f.set_n(2)
    assert f.filter(10, 0, 0) == (7.0, 0.0)
    f.set_n(0)
    assert f.n == 1


def test_reset_forgets_history():
    for f in (MovingAverage(5), OneEuro()):
        f.filter(0, 0, 0.0)
        f.filter(0, 0, 0.033)
        f.reset()
        assert f.filter(500, 500, 1.0) == (500, 500)


def test_one_euro_set_params_updates_describe():
    f = OneEuro()
    f.set_params(mincutoff=0.5, beta=0.01)
    assert f.describe() == "mincutoff=0.500 beta=0.0100"


def test_names_used_in_csv():
    assert [f.name for f in (NoFilter(), MovingAverage(), OneEuro())] == ["none", "moving_avg", "one_euro"]
