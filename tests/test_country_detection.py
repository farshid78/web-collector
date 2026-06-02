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
    extract_host,
    resolve_host
)


def test_extract_host_vless():

    config = (
        "vless://id@google.com:443"
    )

    host = (
        extract_host(
            config
        )
    )

    assert (
        host
        ==
        "google.com"
    )


def test_extract_host_trojan():

    config = (
        "trojan://pass@1.1.1.1:443"
    )

    host = (
        extract_host(
            config
        )
    )

    assert (
        host
        ==
        "1.1.1.1"
    )


def test_resolve_ip():

    result = (
        resolve_host(
            "1.1.1.1"
        )
    )

    assert (
        result
        ==
        "1.1.1.1"
    )


def test_resolve_domain():

    result = (
        resolve_host(
            "google.com"
        )
    )

    assert result is not None