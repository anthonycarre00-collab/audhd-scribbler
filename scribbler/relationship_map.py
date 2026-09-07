#!/usr/bin/env python3
"""Relationship map builder.

Aggregates characters and relationships across all tagged files into a graph
structure suitable for visualization:
  {
    "nodes": [{ id, name, type, mention_count, first_appearance, files }],
    "edges": [{ source, target, relation, files }],
  }

Type inference:
- Characters from the `characters` column on each file
- Relationships from the `relationships` column (LLM-extracted, may be empty)
- Fallback: if no LLM relationships exist, infer co-occurrence edges
  (characters that appear in the same file are likely related)
"""
from typing import Dict, List, Any
from collections import Counter, defaultdict
from . import db


def build_map() -> Dict[str, Any]:
    """Build the relationship map from all tagged files in the DB."""
    all_files = db.get_all_files()
    nodes_by_name = {}  # lowercased name -> node dict
    edges_by_pair = {}  # "a|b" -> edge dict
    co_occurrence = defaultdict(lambda: defaultdict(int))  # name -> Counter of co-occurring names

    for f in all_files:
        filename = f.get("filename", "")
        path = f.get("path", "")
        characters = f.get("characters") or []
        relationships = f.get("relationships") or []

        # Build / update nodes
        for char in characters:
            if not char or not isinstance(char, str):
                continue
            key = char.lower()
            if key not in nodes_by_name:
                nodes_by_name[key] = {
                    "id": char,
                    "name": char,
                    "type": "person",
                    "mention_count": 0,
                    "first_appearance": filename,
                    "files": [],
                }
            node = nodes_by_name[key]
            node["mention_count"] += 1
            if filename and filename not in node["files"]:
                node["files"].append(filename)

        # Track co-occurrence for fallback edge inference
        for i, a in enumerate(characters):
            if not isinstance(a, str):
                continue
            for b in characters[i + 1:]:
                if not isinstance(b, str):
                    continue
                if a.lower() == b.lower():
                    continue
                co_occurrence[a.lower()][b.lower()] += 1

        # Build / update edges from LLM-extracted relationships
        for rel in relationships:
            if not isinstance(rel, dict):
                continue
            a = rel.get("a", "").strip()
            b = rel.get("b", "").strip()
            relation = rel.get("relation", "related").strip() or "related"
            if not a or not b:
                continue
            # Ensure both nodes exist
            for name in (a, b):
                key = name.lower()
                if key not in nodes_by_name:
                    nodes_by_name[key] = {
                        "id": name,
                        "name": name,
                        "type": "person",
                        "mention_count": 0,
                        "first_appearance": filename,
                        "files": [],
                    }
            # Build edge key (sorted so a-b and b-a are the same edge)
            pair_key = "|".join(sorted([a.lower(), b.lower()]))
            if pair_key not in edges_by_pair:
                edges_by_pair[pair_key] = {
                    "source": a,
                    "target": b,
                    "relation": relation,
                    "files": [],
                    "weight": 0,
                    "inferred": False,
                }
            edge = edges_by_pair[pair_key]
            edge["weight"] += 1
            # If we have multiple relation labels, keep the first non-generic one
            if relation != "related" and edge["relation"] == "related":
                edge["relation"] = relation
            if filename and filename not in edge["files"]:
                edge["files"].append(filename)

    # Fallback: infer edges from co-occurrence when no LLM relationships exist
    if not edges_by_pair:
        for a_lower, counts in co_occurrence.items():
            for b_lower, count in counts.items():
                if count < 1:
                    continue
                a = nodes_by_name.get(a_lower, {}).get("name", a_lower)
                b = nodes_by_name.get(b_lower, {}).get("name", b_lower)
                pair_key = "|".join(sorted([a_lower, b_lower]))
                if pair_key not in edges_by_pair:
                    edges_by_pair[pair_key] = {
                        "source": a,
                        "target": b,
                        "relation": "co-occurs",
                        "files": [],
                        "weight": count,
                        "inferred": True,
                    }

    nodes = list(nodes_by_name.values())
    edges = list(edges_by_pair.values())

    # Sort nodes by mention_count (most mentioned first)
    nodes.sort(key=lambda n: n["mention_count"], reverse=True)

    return {
        "nodes": nodes,
        "edges": edges,
        "file_count": len(all_files),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "has_inferred_edges": any(e.get("inferred") for e in edges),
    }
