"""The numeric-truthiness check treats 0 as a value and ignores string ||."""
from checks.numeric_truthiness import find_python_source, find_typescript_source


def test_python_flags_truthiness_and_allows_none_checks():
    flagged = find_python_source(
        "def f(sample):\n    if sample.temperature:\n        return sample.amount or 0\n",
        "sample.py",
    )
    assert len(flagged) == 2
    clean = find_python_source(
        "def f(sample):\n"
        "    if sample.temperature is not None:\n"
        "        return sample.amount if sample.amount is not None else 0\n",
        "sample.py",
    )
    assert clean == []


def test_typescript_flags_or_and_allows_nullish():
    flagged = find_typescript_source(
        "const temperature = sample?.temperature || null;\n"
        "if (formData.concentration) {\n"
        "  send(formData.concentration);\n"
        "}\n",
        "Form.tsx",
    )
    assert len(flagged) == 2
    clean = find_typescript_source(
        "const temperature = sample?.temperature ?? null;\n"
        "if (formData.concentration !== '' && !Number.isNaN(formData.concentration)) {\n"
        "  send(formData.concentration);\n"
        "}\n"
        "const label = unit.type_name === 'mass' || unit.type_name === 'volume';\n"
        "const row = formData.row ?? '';\n"
        "const column = formData.column || 1;\n"
        "const figures = rule.significant_figures ?? null;\n",
        "Form.tsx",
    )
    assert clean == []
