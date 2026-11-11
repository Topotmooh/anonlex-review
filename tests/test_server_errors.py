"""Тесты кодов ошибок API (ТЗ UC-4)."""

import xml.etree.ElementTree as ET
import zipfile

from anonlex.doc_converter import DocConversionError
from server.errors import (
    CONVERSION_FAILED,
    INTERNAL_ERROR,
    INVALID_FORMAT,
    classify,
    message_for,
)


def test_classify_conversion() -> None:
    assert classify(DocConversionError("x")) == CONVERSION_FAILED


def test_classify_bad_zip() -> None:
    assert classify(zipfile.BadZipFile("x")) == INVALID_FORMAT


def test_classify_parse_error() -> None:
    assert classify(ET.ParseError("x")) == INVALID_FORMAT


def test_classify_unknown_is_internal() -> None:
    assert classify(RuntimeError("x")) == INTERNAL_ERROR


def test_message_is_human_russian() -> None:
    assert "повреждён" in message_for(INVALID_FORMAT)