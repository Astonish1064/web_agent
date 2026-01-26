from typing import Dict, Any, List, Set

class A11yProcessor:
    """
    Processes CDP AXTree snapshots (flat list of nodes) and converts them 
    into a cleaned, indented text format for LLM consumption.
    """
    
    def process(self, cdp_snapshot: Dict[str, Any]) -> str:
        """Main entry point for processing a CDP AXTree snapshot."""
        nodes = cdp_snapshot.get("nodes", [])
        if not nodes:
            return ""
        
        # Build node map for quick lookup - handle both string and int IDs
        node_map = {}
        for node in nodes:
            nid = str(node["nodeId"])
            node_map[nid] = node
        
        # Start recursion from the first node (root)
        root_node = nodes[0]
        return self._node_to_text(root_node, node_map, depth=0)

    def _node_to_text(self, node: Dict[str, Any], node_map: Dict[str, Any], depth: int) -> str:
        """Recursively converts a node and its children to text."""
        # 0. Skip ignored nodes
        if node.get("ignored", False):
            return self._process_children(node, node_map, depth)

        # 1. Extract basic info
        role = node.get("role", {}).get("value", "unknown")
        name = node.get("name", {}).get("value", "").strip()
        
        # 2. Advanced Filtering & Collapsing:
        # A. Ignore redundant text leaf nodes if their parent already has the name
        if role in ["StaticText", "InlineTextBox"] and depth > 0:
            return "" # These are usually redundant in a clean tree

        # B. Ignore extremely common verbose containers without semantic value
        if role in ["generic", "none", "WebArea", "RootWebArea"] and not name and depth > 0:
            return self._process_children(node, node_map, depth)

        # C. Prune internal components of atomic inputs (Date, Time, etc.)
        # These are often browser internals like spinbuttons that are not reachable via locators.
        # We want the agent to interact with the parent element instead.
        if role in ["date", "time", "datetime-local", "combobox"]:
            # Format the parent but don't process children
            states = []
            if node.get("disabled"): states.append("disabled")
            if node.get("focused"): states.append("focused")
            state_str = f" [{', '.join(states)}]" if states else ""
            indent = "  " * depth
            return f"{indent}[{role}] '{name}'{state_str}\n"

        # 3. Extract states
        states = []
        if node.get("disabled"): states.append("disabled")
        if node.get("focused"): states.append("focused")
        if node.get("expanded"): states.append("expanded")
        state_str = f" [{', '.join(states)}]" if states else ""
        
        # 4. Format current node line
        indent = "  " * depth
        line = f"{indent}[{role}] '{name}'{state_str}\n"
        
        # 5. Process children
        line += self._process_children(node, node_map, depth + 1)
        return line

    def _process_children(self, node: Dict[str, Any], node_map: Dict[str, Any], depth: int) -> str:
        """Helper to process all children of a node."""
        text = ""
        for child_id in node.get("childIds", []):
            cid = str(child_id)
            if cid in node_map:
                text += self._node_to_text(node_map[cid], node_map, depth)
        return text
