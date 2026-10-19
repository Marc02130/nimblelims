"""Naive-clock scan: qualified datetime calls and import aliases."""
from checks.naive_instants import find_python_source


def test_flags_imported_datetime_class() -> None:
    findings = find_python_source(
        "from datetime import datetime\n"
        "value = datetime.now()\n"
        "other = datetime.utcnow()\n",
        "clock.py",
    )
    assert findings == [
        ("clock.py", 2, "datetime.now() has no timezone"),
        ("clock.py", 3, "datetime.utcnow is naive"),
    ]


def test_flags_datetime_datetime_now() -> None:
    findings = find_python_source(
        "import datetime\nvalue = datetime.datetime.now()\n",
        "clock.py",
    )
    assert findings == [("clock.py", 2, "datetime.now() has no timezone")]


def test_flags_datetime_datetime_utcnow() -> None:
    findings = find_python_source(
        "import datetime\nvalue = datetime.datetime.utcnow()\n",
        "clock.py",
    )
    assert findings == [("clock.py", 2, "datetime.utcnow is naive")]


def test_flags_datetime_class_alias() -> None:
    findings = find_python_source(
        "from datetime import datetime as dt\n"
        "value = dt.now()\n"
        "other = dt.utcnow()\n",
        "clock.py",
    )
    assert findings == [
        ("clock.py", 2, "datetime.now() has no timezone"),
        ("clock.py", 3, "datetime.utcnow is naive"),
    ]


def test_flags_datetime_module_alias() -> None:
    findings = find_python_source(
        "import datetime as d\n"
        "value = d.datetime.now()\n"
        "other = d.datetime.utcnow()\n",
        "clock.py",
    )
    assert findings == [
        ("clock.py", 2, "datetime.now() has no timezone"),
        ("clock.py", 3, "datetime.utcnow is naive"),
    ]


def test_allows_aware_qualified_and_aliased_clocks() -> None:
    samples = [
        "import datetime\nvalue = datetime.datetime.now(datetime.timezone.utc)\n",
        "from datetime import datetime as dt, timezone\nvalue = dt.now(timezone.utc)\n",
        "from datetime import datetime as dt, timezone\nvalue = dt.now(tz=timezone.utc)\n",
        "import datetime as d\nvalue = d.datetime.now(d.timezone.utc)\n",
        "from datetime import datetime\nvalue = datetime.now(timezone.utc)\n",
    ]
    for source in samples:
        assert find_python_source(source, "clock.py") == [], source
