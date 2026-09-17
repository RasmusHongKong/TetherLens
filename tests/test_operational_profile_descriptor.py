import pytest
from pydantic import ValidationError

from tetherlens_ingest.operational_profile import OperationalProfileDescriptor


def test_operational_profile_descriptor_requires_configuration_product_identity():
    with pytest.raises(ValidationError, match="configuration_product_refs"):
        OperationalProfileDescriptor(
            profile_ref="profile:unbound",
            display_name="Unbound profile",
            configuration_product_refs=[],
        )
