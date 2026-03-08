"""
Exercise 3: REST API Versioning
=================================

Implement a version negotiation system that supports multiple
API versioning strategies simultaneously.

Strategies:
- URL path: /api/v1/users, /api/v2/users
- Header: Accept: application/vnd.mobility.v2+json
- Query param: /api/users?version=2
"""


class VersionNegotiator:
    """
    API version negotiator supporting multiple strategies.

    The negotiator checks (in order):
    1. URL path version (/api/v2/...)
    2. Accept header version (application/vnd.mobility.v2+json)
    3. Query parameter (?version=2)
    4. Default version (v1)
    """

    def __init__(self, supported_versions: list[str] | None = None) -> None:
        self.supported = supported_versions or ["v1", "v2"]
        self.default_version = "v1"

    def resolve(self, path: str, headers: dict[str, str] | None = None,
                query_params: dict[str, str] | None = None) -> str:
        """
        Determine the API version from the request.

        Returns the resolved version string (e.g., "v1", "v2").
        Returns default_version if no version indicator found.
        Returns "unsupported" if requested version isn't in supported list.
        """
        # TODO: Implement version resolution (~15 lines)
        raise NotImplementedError("Implement version negotiation")


# ── Tests ──


def test_url_path_version():
    neg = VersionNegotiator(["v1", "v2"])
    assert neg.resolve("/api/v2/users") == "v2"


def test_header_version():
    neg = VersionNegotiator(["v1", "v2"])
    headers = {"Accept": "application/vnd.mobility.v2+json"}
    assert neg.resolve("/api/users", headers=headers) == "v2"


def test_query_param_version():
    neg = VersionNegotiator(["v1", "v2"])
    assert neg.resolve("/api/users", query_params={"version": "2"}) == "v2"


def test_default_version():
    neg = VersionNegotiator(["v1", "v2"])
    assert neg.resolve("/api/users") == "v1"


def test_unsupported_version():
    neg = VersionNegotiator(["v1", "v2"])
    assert neg.resolve("/api/v99/users") == "unsupported"
