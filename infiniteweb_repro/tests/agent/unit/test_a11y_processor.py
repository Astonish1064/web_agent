import pytest
from src.agent.environments.a11y_processor import A11yProcessor

def test_empty_snapshot():
    processor = A11yProcessor()
    assert processor.process({}) == ""

def test_simple_cdp_nodes():
    # CDP format is a flat list with nodeIds and childIds
    snapshot = {
        "nodes": [
            {
                "nodeId": "1",
                "role": {"value": "Root"},
                "name": {"value": "Home"},
                "childIds": ["2", "3"]
            },
            {
                "nodeId": "2",
                "role": {"value": "button"},
                "name": {"value": "Search"},
                "childIds": []
            },
            {
                "nodeId": "3",
                "role": {"value": "link"},
                "name": {"value": "Books"},
                "childIds": []
            }
        ]
    }
    processor = A11yProcessor()
    expected = (
        "[Root] 'Home'\n"
        "  [button] 'Search'\n"
        "  [link] 'Books'"
    )
    assert processor.process(snapshot).strip() == expected

def test_ignored_nodes():
    snapshot = {
        "nodes": [
            {
                "nodeId": "1",
                "role": {"value": "Root"},
                "name": {"value": "App"},
                "childIds": ["2"]
            },
            {
                "nodeId": "2",
                "role": {"value": "generic"},
                "ignored": True,
                "childIds": ["3"]
            },
            {
                "nodeId": "3",
                "role": {"value": "link"},
                "name": {"value": "Login"},
                "childIds": []
            }
        ]
    }
    processor = A11yProcessor()
    expected = (
        "[Root] 'App'\n"
        "  [link] 'Login'"
    )
    assert processor.process(snapshot).strip() == expected
