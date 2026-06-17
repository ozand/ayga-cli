import pytest
from ayga_cli.utils.fields import filter_fields

def test_filter_basic():
    data = {"a": 1, "b": 2, "c": 3}
    assert filter_fields(data, "a,b") == {"a": 1, "b": 2}

def test_filter_dot_notation():
    data = {"meta": {"url": "x", "ts": "y"}, "title": "t"}
    assert filter_fields(data, "title,meta.url") == {"title": "t", "meta": {"url": "x"}}

def test_filter_missing_field():
    data = {"a": 1}
    assert filter_fields(data, "a,nonexistent") == {"a": 1}

def test_filter_list():
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert filter_fields(data, "a") == [{"a": 1}, {"a": 3}]

def test_filter_none_fields():
    data = {"a": 1}
    assert filter_fields(data, None) == {"a": 1}
