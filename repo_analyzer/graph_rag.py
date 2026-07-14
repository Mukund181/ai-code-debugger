import os
import json
from repo_analyzer.ast_parser import parse_any_file, ALL_SOURCE_EXTENSIONS, should_skip_dir

class CodeGraph:
    def __init__(self):
        # Nodes: maps node_id to properties
        # Node properties: {"type": "file"|"class"|"function"|"method", "name": str, "file": str, "code": str, "doc": str, "bases": list}
        self.nodes = {}
        # Edges: list of {"from": node_id, "to": node_id, "rel": "calls"|"defines"|"inherits"|"imports"}
        self.edges = []
        # Adjacency lists for fast traversal
        self.adj_out = {} # node_id -> set of (to_node, rel)
        self.adj_in = {}  # node_id -> set of (from_node, rel)

    def add_node(self, node_id: str, node_type: str, name: str, file_path: str, code: str = "", doc: str = "", extra: dict = None):
        properties = {
            "type": node_type,
            "name": name,
            "file": file_path,
            "code": code,
            "doc": doc
        }
        if extra:
            properties.update(extra)
        self.nodes[node_id] = properties
        if node_id not in self.adj_out:
            self.adj_out[node_id] = set()
        if node_id not in self.adj_in:
            self.adj_in[node_id] = set()

    def add_edge(self, from_node: str, to_node: str, relation: str):
        if from_node not in self.nodes or to_node not in self.nodes:
            return  # Nodes must exist
        
        edge = {"from": from_node, "to": to_node, "rel": relation}
        # Avoid duplicate edges
        if edge not in self.edges:
            self.edges.append(edge)
            self.adj_out[from_node].add((to_node, relation))
            self.adj_in[to_node].add((from_node, relation))

    def build_from_directory(self, root_dir: str):
        """Recursively scans a directory for source files and maps their graph structure."""
        self.nodes.clear()
        self.edges.clear()
        self.adj_out.clear()
        self.adj_in.clear()

        # Step 1: Parse structure of each source file
        parsed_files = {}
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune directories we never want to enter
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ALL_SOURCE_EXTENSIONS:
                    abs_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(abs_path, root_dir).replace("\\", "/")
                    parsed = parse_any_file(abs_path)
                    parsed_files[rel_path] = parsed

        # Step 2: Add nodes for files, classes, methods, functions
        for rel_path, structure in parsed_files.items():
            file_node_id = f"file:{rel_path}"
            raw_code = structure.get("raw_code", "")
            
            # If there was a parsing error, read the raw code directly as fallback
            if "error" in structure and not raw_code:
                try:
                    with open(os.path.join(root_dir, rel_path), "r", encoding="utf-8", errors="replace") as f:
                        raw_code = f.read()
                except Exception:
                    raw_code = ""

            self.add_node(file_node_id, "file", rel_path, rel_path, code=raw_code)

            if "error" in structure:
                # File is mapped, but skip class/method extraction since it has syntax errors
                continue

            # Classes
            for class_name, class_info in structure.get("classes", {}).items():
                class_node_id = f"class:{rel_path}:{class_name}"
                self.add_node(
                    class_node_id, "class", class_name, rel_path,
                    doc=class_info.get("docstring", ""),
                    extra={"bases": class_info.get("bases", [])}
                )
                self.add_edge(file_node_id, class_node_id, "defines")

                # Methods inside class
                for method_name, method_info in class_info.get("methods", {}).items():
                    method_node_id = f"method:{rel_path}:{class_name}.{method_name}"
                    self.add_node(
                        method_node_id, "method", f"{class_name}.{method_name}", rel_path,
                        doc=method_info.get("docstring", "")
                    )
                    self.add_edge(class_node_id, method_node_id, "defines")

            # Top-level Functions
            for func_name, func_info in structure.get("functions", {}).items():
                func_node_id = f"func:{rel_path}:{func_name}"
                self.add_node(
                    func_node_id, "function", func_name, rel_path,
                    doc=func_info.get("docstring", "")
                )
                self.add_edge(file_node_id, func_node_id, "defines")

        # Step 3: Add edges for function calls, base-class inheritance, and imports
        # Create helper lookup dicts for name resolution
        defined_functions = {}  # name -> list of node_ids
        defined_classes = {}    # name -> list of node_ids

        for node_id, props in self.nodes.items():
            if props["type"] == "function":
                defined_functions.setdefault(props["name"], []).append(node_id)
            elif props["type"] == "method":
                short_name = props["name"].split(".")[-1]
                defined_functions.setdefault(short_name, []).append(node_id)
            elif props["type"] == "class":
                defined_classes.setdefault(props["name"], []).append(node_id)

        # Build connection edges
        for rel_path, structure in parsed_files.items():
            file_node_id = f"file:{rel_path}"

            # Base class inheritances
            for class_name, class_info in structure.get("classes", {}).items():
                class_node_id = f"class:{rel_path}:{class_name}"
                for base in class_info.get("bases", []):
                    # Check if base class is defined locally
                    if base in defined_classes:
                        for target_node_id in defined_classes[base]:
                            self.add_edge(class_node_id, target_node_id, "inherits")

            # Method calls
            for class_name, class_info in structure.get("classes", {}).items():
                for method_name, method_info in class_info.get("methods", {}).items():
                    method_node_id = f"method:{rel_path}:{class_name}.{method_name}"
                    for call in method_info.get("calls", []):
                        # Attempt to resolve call targets
                        if call in defined_functions:
                            for target_node_id in defined_functions[call]:
                                self.add_edge(method_node_id, target_node_id, "calls")

            # Top-level function calls
            for func_name, func_info in structure.get("functions", {}).items():
                func_node_id = f"func:{rel_path}:{func_name}"
                for call in func_info.get("calls", []):
                    if call in defined_functions:
                        for target_node_id in defined_functions[call]:
                            self.add_edge(func_node_id, target_node_id, "calls")

    def query_impact(self, modified_file: str, max_depth: int = 3) -> dict:
        """Finds all code entities that depend on the files or modules inside modified_file."""
        # Find all nodes defined in the modified file
        affected_nodes = [
            node_id for node_id, props in self.nodes.items()
            if props["file"] == modified_file
        ]

        if not affected_nodes:
            # Maybe the file was matched without prefix
            affected_nodes = [
                node_id for node_id, props in self.nodes.items()
                if modified_file in props["file"]
            ]

        # Traversal: Breadth-First Search (BFS) going backwards (inwards) along edges to find dependers
        visited = set()
        queue = []
        for node in affected_nodes:
            visited.add(node)
            queue.append((node, 0))

        impact_chain = []
        while queue:
            curr, depth = queue.pop(0)
            if depth > max_depth:
                continue

            # Skip the starting nodes in the impact logs, except as root references
            if depth > 0:
                impact_chain.append({
                    "node_id": curr,
                    "type": self.nodes[curr]["type"],
                    "name": self.nodes[curr]["name"],
                    "file": self.nodes[curr]["file"],
                    "depth": depth
                })

            # Traverse incoming edges (what links into this node)
            for from_node, rel in self.adj_in.get(curr, set()):
                if from_node not in visited:
                    visited.add(from_node)
                    queue.append((from_node, depth + 1))

        return {
            "root_file": modified_file,
            "root_nodes": [self.nodes[n]["name"] for n in affected_nodes],
            "impact_chain": impact_chain
        }

    def save_index(self, output_path: str):
        """Saves the graph structure as a local JSON file."""
        # Convert sets to lists for JSON serialization
        serializable_adj_out = {k: list(v) for k, v in self.adj_out.items()}
        serializable_adj_in = {k: list(v) for k, v in self.adj_in.items()}
        data = {
            "nodes": self.nodes,
            "edges": self.edges,
            "adj_out": serializable_adj_out,
            "adj_in": serializable_adj_in
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_index(self, input_path: str):
        """Loads the graph structure from a local JSON file."""
        if not os.path.exists(input_path):
            return False
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
        self.nodes = data.get("nodes", {})
        self.edges = data.get("edges", [])
        # Re-construct adjacency sets
        self.adj_out = {k: set(tuple(x) for x in v) for k, v in data.get("adj_out", {}).items()}
        self.adj_in = {k: set(tuple(x) for x in v) for k, v in data.get("adj_in", {}).items()}
        return True
