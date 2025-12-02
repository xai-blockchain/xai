"""API contract regression test that exercises docs/api/openapi.yaml against a live node."""

import os

import pytest
schemathesis = pytest.importorskip("schemathesis")
loaders = getattr(schemathesis, "loaders", None)

API_BASE_URL = os.environ.get("API_BASE_URL")
pytestmark = pytest.mark.skipif(
    API_BASE_URL is None,
    reason="Set API_BASE_URL to point at a running node before enabling contract regression tests.",
)

if loaders and hasattr(loaders, "from_path"):
    schema = loaders.from_path("docs/api/openapi.yaml")
elif hasattr(schemathesis, "from_path"):
    schema = schemathesis.from_path("docs/api/openapi.yaml")
else:
    pytest.skip("schemathesis loader not available", allow_module_level=True)


@schema.parametrize()
def test_openapi_contract(case):
    """Each schema-defined endpoint must accept the generated request without schema drift."""
    response = case.call(base_url=API_BASE_URL)
    case.validate_response(response)
