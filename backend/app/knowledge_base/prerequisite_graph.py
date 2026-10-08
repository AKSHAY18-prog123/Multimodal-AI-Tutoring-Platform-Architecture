import networkx as nx
from typing import List, Dict, Any, Optional
from backend.app.core.logging import logger

class PrerequisiteGraphService:
    """Manages the pedagogical concept prerequisite Directed Acyclic Graph (DAG) using NetworkX."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def load_graph(self, concepts: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        """Build or refresh graph from database concepts and relationships."""
        self.graph.clear()

        for c in concepts:
            self.graph.add_node(
                c["id"],
                id=c["id"],
                name=c.get("name", "Concept"),
                label=c.get("name", "Concept"),
                topic_id=c.get("topic_id"),
                topic_title=c.get("topic_title", "Core Curriculum"),
                difficulty=c.get("difficulty_level", "medium"),
                difficulty_level=c.get("difficulty_level", "medium"),
                summary=c.get("summary") or c.get("definition") or "",
                definition=c.get("definition") or c.get("summary") or ""
            )

        edge_added = False
        for r in relationships:
            src = r["source_concept_id"]
            dst = r["target_concept_id"]
            # Prerequisite: src -> dst means src must be learned before dst
            if src in self.graph and dst in self.graph:
                self.graph.add_edge(
                    src,
                    dst,
                    relationship_type=r.get("relationship_type", "prerequisite"),
                    strength=r.get("strength", 1.0)
                )
                edge_added = True

        # If no explicit edges were provided but multiple concepts exist,
        # synthesize sequential prerequisite edges following curriculum order
        if not edge_added and len(concepts) > 1:
            for i in range(len(concepts) - 1):
                src = concepts[i]["id"]
                dst = concepts[i + 1]["id"]
                if src in self.graph and dst in self.graph:
                    self.graph.add_edge(
                        src,
                        dst,
                        relationship_type="prerequisite",
                        strength=0.9
                    )

        logger.info(f"Loaded concept graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def get_prerequisites(self, concept_id: str) -> List[Dict[str, Any]]:
        """Returns all direct and indirect prerequisites for a concept in pedagogical order."""
        if concept_id not in self.graph:
            return []

        # Ancestors are prerequisites
        ancestors = nx.ancestors(self.graph, concept_id)
        subgraph = self.graph.subgraph(list(ancestors) + [concept_id])

        try:
            topo_order = list(nx.topological_sort(subgraph))
        except nx.NetworkXUnfeasible:
            topo_order = list(ancestors)

        prereqs = []
        for node_id in topo_order:
            if node_id != concept_id:
                data = self.graph.nodes[node_id]
                prereqs.append({
                    "id": node_id,
                    "name": data.get("name"),
                    "difficulty": data.get("difficulty")
                })
        return prereqs

    def get_downstream_concepts(self, concept_id: str) -> List[Dict[str, Any]]:
        """Returns concepts that unlock after mastering this concept."""
        if concept_id not in self.graph:
            return []

        descendants = nx.descendants(self.graph, concept_id)
        return [
            {"id": nid, "name": self.graph.nodes[nid].get("name")}
            for nid in descendants
        ]

    def get_learning_path(self) -> List[Dict[str, Any]]:
        """Computes optimal topological learning progression through the course."""
        try:
            order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            logger.warning("Graph contains cycles; sorting by in-degree fallback.")
            order = sorted(self.graph.nodes(), key=lambda n: self.graph.in_degree(n))

        path = []
        for nid in order:
            data = self.graph.nodes[nid]
            path.append({
                "id": nid,
                "name": data.get("name"),
                "difficulty": data.get("difficulty"),
                "direct_prereqs": [self.graph.nodes[p].get("name") for p in self.graph.predecessors(nid)]
            })
        return path

    def export_graph_visualization(self) -> Dict[str, Any]:
        """Exports nodes and edges in D3/Vis.js compatible structure for frontend graph rendering."""
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            nodes.append({
                "id": nid,
                "name": data.get("name", nid),
                "label": data.get("label", data.get("name", nid)),
                "difficulty": data.get("difficulty", "medium"),
                "difficulty_level": data.get("difficulty_level", data.get("difficulty", "medium")),
                "topic_id": data.get("topic_id"),
                "topic_title": data.get("topic_title", "Foundations"),
                "summary": data.get("summary", ""),
                "definition": data.get("definition", data.get("summary", ""))
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "type": data.get("relationship_type", "prerequisite"),
                "strength": data.get("strength", 1.0)
            })

        return {"nodes": nodes, "edges": edges}

prerequisite_engine = PrerequisiteGraphService()
