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
    extract_sub_links
)


def test_extract_txt_link():

    text = (
        "https://abc.com/sub.txt"
    )

    result = (
        extract_sub_links(
            text
        )
    )

    assert (
        len(result)
        == 1
    )


def test_extract_subscription_url():

    text = (
        "https://site.com/subscription"
    )

    result = (
        extract_sub_links(
            text
        )
    )

    assert (
        len(result)
        == 1
    )


def test_extract_multiple_links():

    text = """
    https://a.com/sub.txt
    https://b.com/subscription
    """

    result = (
        extract_sub_links(
            text
        )
    )

    assert (
        len(result)
        == 2
    )


def test_empty_links():

    result = (
        extract_sub_links(
            ""
        )
    )

    assert (
        result
        ==
        []
    )


def test_invalid_links():

    result = (
        extract_sub_links(
            "hello"
        )
    )

    assert (
        result
        ==
        []
    )