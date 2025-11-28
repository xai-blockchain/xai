"""API contract regression test that exercises docs/api/openapi.yaml against a live node."""

import os

import pytest
import schemathesis

API_BASE_URL = os.environ.get("API_BASE_URL")
pytestmark = pytest.mark.skipif(
    API_BASE_URL is None,
    reason="Set API_BASE_URL to point at a running node before enabling contract regression tests.",
)

schema = schemathesis.from_path("docs/api/openapi.yaml")


@schema.parametrize()
def test_openapi_contract(case):
    """Each schema-defined endpoint must accept the generated request without schema drift."""
    response = case.call(base_url=API_BASE_URL)
    case.validate_response(response)
