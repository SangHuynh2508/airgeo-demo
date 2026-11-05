import csv

from airgeo.recording.csv_logger import COLUMNS, CsvLogger


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_columns_are_the_11_required_ones():
    assert COLUMNS == ["t", "x8_raw", "y8_raw", "x4_raw", "y4_raw", "pinch",
                       "filter_name", "x_filt", "y_filt", "mode", "session_id"]


def test_writes_header_and_blank_for_missing(tmp_path):
    lg = CsvLogger(str(tmp_path / "data"))          # thư mục chưa có -> tự tạo
    path = lg.start()
    lg.log(t="1.000000", x8_raw="10.50", pinch=1, filter_name="one_euro", mode="smart")
    lg.log(t="1.033000", x8_raw=None, pinch=0, filter_name="none", mode="free")
    lg.stop()
    rows = _read(path)
    assert rows[0] == COLUMNS
    assert rows[1] == ["1.000000", "10.50", "", "", "", "1", "one_euro", "", "", "smart", lg.session_id]
    assert rows[2][1] == "" and rows[2][5] == "0"


def test_log_without_start_is_noop(tmp_path):
    lg = CsvLogger(str(tmp_path))
    lg.log(t="1")
    lg.stop()
    assert not lg.active and list(tmp_path.iterdir()) == []


def test_two_sessions_in_same_second_do_not_overwrite(tmp_path):
    lg = CsvLogger(str(tmp_path))
    p1 = lg.start(); lg.log(t="1"); lg.stop()
    p2 = lg.start(); lg.log(t="2"); lg.stop()
    assert p1 != p2
    assert _read(p1)[1][0] == "1" and _read(p2)[1][0] == "2"
