from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phyloom.core._edge import Edge
    from phyloom.core._net import Net
    from phyloom.types import NodeID


def _label_node(net: Net[float | None], id_: NodeID) -> str:
    node = net.nodes[id_]
    metadata = ", ".join(f"{k}={v}" for k, v in node.metadata.items())
    label = f"{node.name}"
    if metadata:
        label += f" ({metadata})"
    return label


def _label_edge(edge: Edge[float | None]) -> str:
    metadata = ", ".join(f"{k}={v}" for k, v in edge.metadata.items())
    if edge.length is None and metadata:
        return f" [{metadata}]"
    if edge.length is None:
        return ""
    if metadata:
        return f" [{edge.length}, {metadata}]"
    return f" [{edge.length}]"


def _label_root(net: Net[float | None]) -> str:
    root_label = _label_node(net, net.root)
    if net.stem is not None:
        root_label += _label_edge(net.stem)
    return root_label


def pprint_net(net: Net[float | None]):
    lines: list[str] = [_label_root(net)]
    stack: list[tuple[NodeID, NodeID, str, bool]] = []
    children = net.children_of(net.root)
    for child in reversed(children):
        stack.append((child, net.root, "", child == children[-1]))

    visited: set[NodeID] = {net.root}
    while stack:
        node, parent, prefix, is_last = stack.pop()
        edge = net.edges[(parent, node)]
        connector = "`-- " if is_last else "|-- "
        label = (
            f"ref {net.nodes[node].name}" if node in visited else _label_node(net, node)
        )
        lines.append(f"{prefix}{connector}{label}{_label_edge(edge)}")
        if node not in visited:
            visited.add(node)
            prefix += "    " if is_last else "|   "
            children = net.children_of(node)
            for child in reversed(children):
                stack.append((child, node, prefix, child == children[-1]))

    rendered = "\n".join(lines)
    print(rendered)
