import sys
from pathlib import Path

ROOT = (
    Path(__file__)
    .resolve()
    .parent.parent
)

sys.path.append(
    str(ROOT)
)

from scraper.scraper import (
    extract_configs
)


def test_extract_single_vmess():
    text = (
        "vmess://abc123"
    )

    result = (
        extract_configs(
            text
        )
    )

    assert (
        len(result)
        == 1
    )

    assert (
        result[0]
        ==
        "vmess://abc123"
    )


def test_extract_multiple_configs():

    text = """
    vmess://aaa

    vless://bbb

    trojan://ccc

    ss://ddd
    """

    result = (
        extract_configs(
            text
        )
    )

    assert (
        len(result)
        == 4
    )


def test_extract_empty_text():

    result = (
        extract_configs(
            ""
        )
    )

    assert (
        result
        ==
        []
    )


def test_extract_invalid_text():

    text = (
        "hello world"
    )

    result = (
        extract_configs(
            text
        )
    )

    assert (
        result
        ==
        []
    )


def test_dedupe_configs():

    text = """
    vmess://aaa
    vmess://aaa
    """

    result = (
        extract_configs(
            text
        )
    )

    assert (
        len(result)
        >= 1
    )