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
        raw_name = node.get("name", {}).get("value", "").strip()
        
        # 2. Extract Agent ID from Name (if present)
        # Pattern: "... --agent-id:123--"
        import re
        agent_id = None
        match = re.search(r'--agent-id:(\d+)--', raw_name)
        if match:
            agent_id = match.group(1)
            # Remove the ID tag from the display name to keep it clean
            name = raw_name.replace(match.group(0), "").strip()
        else:
            name = raw_name

        # 3. Advanced Filtering & Collapsing:
        # A. Ignore redundant text leaf nodes if their parent already has the name
        # BUT keep them if they have an ID (unlikely for static text, but safety first)
        if not agent_id and role in ["StaticText", "InlineTextBox"] and depth > 0:
            return "" # These are usually redundant in a clean tree

        # B. Ignore extremely common verbose containers without semantic value
        # UNLESS they have an ID (which means we marked them as interactive)
        if not agent_id and role in ["generic", "none", "WebArea", "RootWebArea"] and not name and depth > 0:
            return self._process_children(node, node_map, depth)

        # C. Prune internal components of atomic inputs (Date, Time, etc.)
        if role in ["date", "time", "datetime-local", "combobox"]:
            # Format the parent but don't process children
            states = []
            if node.get("disabled"): states.append("disabled")
            if node.get("focused"): states.append("focused")
            state_str = f" [{', '.join(states)}]" if states else ""
            
            id_prefix = f"[{agent_id}] " if agent_id else ""
            indent = "  " * depth
            return f"{indent}{id_prefix}[{role}] '{name}'{state_str}\n"

        # 4. Extract states
        states = []
        if node.get("disabled"): states.append("disabled")
        if node.get("focused"): states.append("focused")
        if node.get("expanded"): states.append("expanded")
        # Add clickable state if we found an ID (implies interactivity)
        if agent_id: states.append("clickable")
        
        state_str = f" [{', '.join(states)}]" if states else ""
        
        # 5. Format current node line
        indent = "  " * depth
        id_prefix = f"[{agent_id}] " if agent_id else ""
        line = f"{indent}{id_prefix}[{role}] '{name}'{state_str}\n"
        
        # 6. Process children
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
