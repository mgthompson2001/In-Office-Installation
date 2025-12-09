#!/usr/bin/env python3
"""
Dependency Mapper - Understands HOW actions relate to each other
Part of the Context Understanding Engine
"""

import json
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import logging


class DependencyMapper:
    """
    Dependency Mapper - Understands relationships between actions
    
    Maps:
    - Sequential dependencies: Actions that must happen in order
    - Causal dependencies: Actions that cause other actions
    - Contextual dependencies: Actions that share context
    - Temporal dependencies: Actions that occur close in time
    """
    
    def __init__(self):
        """Initialize Dependency Mapper"""
        self.logger = logging.getLogger(__name__)
        
        # Dependency types
        self.dependency_types = {
            "sequential": "Actions that must happen in order",
            "causal": "Actions that cause other actions",
            "contextual": "Actions that share context",
            "temporal": "Actions that occur close in time",
            "conditional": "Actions that depend on conditions",
            "parallel": "Actions that can happen simultaneously"
        }
        
        # Common dependency patterns
        self.dependency_patterns = {
            "login_before_action": {
                "source_intent": "login",
                "target_intent": ["navigate", "search", "view"],
                "type": "sequential"
            },
            "search_before_view": {
                "source_intent": "search",
                "target_intent": ["view", "edit"],
                "type": "sequential"
            },
            "view_before_edit": {
                "source_intent": "view",
                "target_intent": ["edit", "delete"],
                "type": "sequential"
            },
            "edit_before_submit": {
                "source_intent": "edit",
                "target_intent": ["submit", "save"],
                "type": "sequential"
            },
            "upload_before_process": {
                "source_intent": "upload",
                "target_intent": ["process", "submit"],
                "type": "sequential"
            }
        }
    
    def map_dependencies(self, actions: List[Dict], contexts: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Map dependencies between actions
        
        Args:
            actions: List of actions in sequence
            contexts: Optional list of contexts for each action
            
        Returns:
            List of dependency dictionaries
        """
        dependencies = []
        
        if len(actions) < 2:
            return dependencies
        
        # Map dependencies between consecutive actions
        for i in range(len(actions) - 1):
            source_action = actions[i]
            target_action = actions[i + 1]
            
            source_context = contexts[i] if contexts and i < len(contexts) else None
            target_context = contexts[i + 1] if contexts and i + 1 < len(contexts) else None
            
            # Determine dependency
            dependency = self._determine_dependency(
                source_action, target_action,
                source_context, target_context
            )
            
            if dependency:
                dependencies.append(dependency)
        
        # Map dependencies between non-consecutive actions (causal chains)
        causal_dependencies = self._map_causal_dependencies(actions, contexts)
        dependencies.extend(causal_dependencies)
        
        return dependencies
    
    def _determine_dependency(self, source: Dict, target: Dict,
                             source_context: Optional[Dict] = None,
                             target_context: Optional[Dict] = None) -> Optional[Dict]:
        """Determine dependency between two actions"""
        # Time-based dependency
        time_dependency = self._check_temporal_dependency(source, target)
        
        # Intent-based dependency
        intent_dependency = self._check_intent_dependency(source, target)
        
        # Context-based dependency
        context_dependency = self._check_context_dependency(
            source, target, source_context, target_context
        )
        
        # Combine dependencies
        dependency_type = None
        strength = 0.0
        
        if intent_dependency:
            dependency_type = intent_dependency["type"]
            strength = intent_dependency["strength"]
        elif time_dependency:
            dependency_type = "temporal"
            strength = time_dependency["strength"]
        elif context_dependency:
            dependency_type = "contextual"
            strength = context_dependency["strength"]
        
        if dependency_type:
            return {
                "source_action_id": source.get("id", ""),
                "target_action_id": target.get("id", ""),
                "dependency_type": dependency_type,
                "dependency_strength": strength,
                "dependency_metadata": json.dumps({
                    "source": source,
                    "target": target,
                    "source_context": source_context,
                    "target_context": target_context
                })
            }
        
        return None
    
    def _check_temporal_dependency(self, source: Dict, target: Dict) -> Optional[Dict]:
        """Check temporal dependency (actions close in time)"""
        source_time = source.get("timestamp", "")
        target_time = target.get("timestamp", "")
        
        try:
            source_dt = datetime.fromisoformat(source_time)
            target_dt = datetime.fromisoformat(target_time)
            time_diff = (target_dt - source_dt).total_seconds()
            
            # If actions are close in time, they're likely related
            if 0 < time_diff < 10.0:  # Within 10 seconds
                strength = 1.0 - (time_diff / 10.0)
                return {
                    "type": "temporal",
                    "strength": strength,
                    "time_diff": time_diff
                }
        except:
            pass
        
        return None
    
    def _check_intent_dependency(self, source: Dict, target: Dict) -> Optional[Dict]:
        """Check intent-based dependency"""
        source_intent = source.get("intent_category", "")
        target_intent = target.get("intent_category", "")
        
        # Check against dependency patterns
        for pattern_name, pattern in self.dependency_patterns.items():
            if (source_intent == pattern["source_intent"] and
                target_intent in pattern["target_intent"]):
                return {
                    "type": pattern["type"],
                    "strength": 0.9,  # High confidence for known patterns
                    "pattern": pattern_name
                }
        
        # Check for general sequential dependency
        if source_intent and target_intent:
            # If intents are different, they might be sequential
            if source_intent != target_intent:
                return {
                    "type": "sequential",
                    "strength": 0.6,  # Medium confidence
                    "pattern": "general_sequential"
                }
        
        return None
    
    def _check_context_dependency(self, source: Dict, target: Dict,
                                  source_context: Optional[Dict] = None,
                                  target_context: Optional[Dict] = None) -> Optional[Dict]:
        """Check context-based dependency"""
        if not source_context or not target_context:
            return None
        
        # Check if actions share context
        source_app = source_context.get("application", {}).get("application", "")
        target_app = target_context.get("application", {}).get("application", "")
        
        source_page = source_context.get("page", {}).get("page", "")
        target_page = target_context.get("page", {}).get("page", "")
        
        # Same application/page suggests dependency
        if source_app and target_app and source_app == target_app:
            return {
                "type": "contextual",
                "strength": 0.7,
                "shared_context": "application"
            }
        
        if source_page and target_page and source_page == target_page:
            return {
                "type": "contextual",
                "strength": 0.8,
                "shared_context": "page"
            }
        
        return None
    
    def _map_causal_dependencies(self, actions: List[Dict],
                                 contexts: Optional[List[Dict]] = None) -> List[Dict]:
        """Map causal dependencies (non-consecutive actions that are related)"""
        causal_dependencies = []
        
        # Look for causal chains (e.g., login → navigate → search → view)
        for i in range(len(actions) - 1):
            source_action = actions[i]
            source_intent = source_action.get("intent_category", "")
            
            # Look ahead for related actions
            for j in range(i + 2, min(i + 10, len(actions))):  # Look up to 10 actions ahead
                target_action = actions[j]
                target_intent = target_action.get("intent_category", "")
                
                # Check if target intent is a common follow-up to source intent
                if source_intent in self.dependency_patterns:
                    pattern = self.dependency_patterns.get(source_intent, {})
                    if target_intent in pattern.get("target_intent", []):
                        # Check temporal proximity
                        source_time = source_action.get("timestamp", "")
                        target_time = target_action.get("timestamp", "")
                        
                        try:
                            source_dt = datetime.fromisoformat(source_time)
                            target_dt = datetime.fromisoformat(target_time)
                            time_diff = (target_dt - source_dt).total_seconds()
                            
                            # If within reasonable time window (e.g., 60 seconds)
                            if 0 < time_diff < 60.0:
                                causal_dependencies.append({
                                    "source_action_id": source_action.get("id", ""),
                                    "target_action_id": target_action.get("id", ""),
                                    "dependency_type": "causal",
                                    "dependency_strength": 0.7,
                                    "dependency_metadata": json.dumps({
                                        "source": source_action,
                                        "target": target_action,
                                        "time_diff": time_diff,
                                        "pattern": f"{source_intent}_to_{target_intent}"
                                    })
                                })
                        except:
                            pass
        
        return causal_dependencies
    
    def build_dependency_graph(self, actions: List[Dict],
                              contexts: Optional[List[Dict]] = None) -> Dict:
        """
        Build dependency graph from actions
        
        Args:
            actions: List of actions
            contexts: Optional list of contexts
            
        Returns:
            Dictionary with:
                - nodes: List of action nodes
                - edges: List of dependency edges
                - graph_structure: Graph structure information
        """
        dependencies = self.map_dependencies(actions, contexts)
        
        # Build graph structure
        nodes = []
        edges = []
        
        for i, action in enumerate(actions):
            nodes.append({
                "id": action.get("id", f"action_{i}"),
                "type": action.get("type", ""),
                "intent": action.get("intent_category", ""),
                "timestamp": action.get("timestamp", "")
            })
        
        for dependency in dependencies:
            edges.append({
                "source": dependency["source_action_id"],
                "target": dependency["target_action_id"],
                "type": dependency["dependency_type"],
                "strength": dependency["dependency_strength"]
            })
        
        # Analyze graph structure
        graph_structure = self._analyze_graph_structure(nodes, edges)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "graph_structure": graph_structure,
            "total_dependencies": len(dependencies)
        }
    
    def _analyze_graph_structure(self, nodes: List[Dict], edges: List[Dict]) -> Dict:
        """Analyze dependency graph structure"""
        # Count dependencies by type
        dependency_counts = defaultdict(int)
        for edge in edges:
            dependency_counts[edge["type"]] += 1
        
        # Find critical paths (chains of dependencies)
        critical_paths = self._find_critical_paths(nodes, edges)
        
        # Find dependency clusters
        clusters = self._find_dependency_clusters(nodes, edges)
        
        return {
            "dependency_counts": dict(dependency_counts),
            "critical_paths": critical_paths,
            "clusters": clusters,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    
    def _find_critical_paths(self, nodes: List[Dict], edges: List[Dict]) -> List[List[str]]:
        """Find critical paths (long chains of dependencies)"""
        # Build adjacency list
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge["source"]].append(edge["target"])
        
        # Find longest paths
        paths = []
        visited = set()
        
        def dfs(node, path):
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            if node in adjacency:
                for neighbor in adjacency[node]:
                    dfs(neighbor, path.copy())
            else:
                # End of path
                if len(path) > 2:  # Only paths with 3+ nodes
                    paths.append(path)
            
            visited.remove(node)
        
        for node in nodes:
            if node["id"] not in visited:
                dfs(node["id"], [])
        
        # Return longest paths
        if paths:
            paths.sort(key=len, reverse=True)
            return paths[:5]  # Top 5 longest paths
        
        return []
    
    def _find_dependency_clusters(self, nodes: List[Dict], edges: List[Dict]) -> List[List[str]]:
        """Find dependency clusters (groups of related actions)"""
        # Simple clustering by shared dependencies
        clusters = []
        node_clusters = {}
        
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            # If both nodes are in same cluster, continue
            if source in node_clusters and target in node_clusters:
                if node_clusters[source] == node_clusters[target]:
                    continue
            
            # Merge clusters
            if source in node_clusters:
                cluster_id = node_clusters[source]
                node_clusters[target] = cluster_id
            elif target in node_clusters:
                cluster_id = node_clusters[target]
                node_clusters[source] = cluster_id
            else:
                # New cluster
                cluster_id = len(clusters)
                clusters.append([])
                node_clusters[source] = cluster_id
                node_clusters[target] = cluster_id
            
            # Add nodes to cluster
            cluster = clusters[cluster_id]
            if source not in cluster:
                cluster.append(source)
            if target not in cluster:
                cluster.append(target)
        
        return clusters

