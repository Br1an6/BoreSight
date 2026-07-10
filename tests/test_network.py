import pytest
from boresight.core.network import ProxyRotator

def test_proxy_rotator():
    proxies = ["http://proxy1", "http://proxy2"]
    rotator = ProxyRotator(proxies)
    
    assert rotator.get_proxy() == "http://proxy1"
    assert rotator.get_proxy() == "http://proxy2"
    assert rotator.get_proxy() == "http://proxy1"

def test_empty_proxy_rotator():
    rotator = ProxyRotator([])
    assert rotator.get_proxy() is None
