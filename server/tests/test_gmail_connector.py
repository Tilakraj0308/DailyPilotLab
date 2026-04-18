from connectors.providers import PROVIDER_MAP


def test_gmail_provider_registered():
    assert "gmail" in PROVIDER_MAP
    connector_cls = PROVIDER_MAP["gmail"]
    inst = connector_cls()
    assert getattr(inst, "provider_key", None) == "gmail"
