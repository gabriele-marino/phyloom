r"""Read and write networks in Newick format.

Newick is a compact, text-based format for representing evolutionary trees
and networks. Nested parentheses describe the branching structure, commas
separate sibling nodes, labels name nodes, and values following ``:``
specify edge lengths. Each tree or network ends with a semicolon, and a
Newick file stores one per line. Labels and edge lengths may be omitted.

Metadata are encoded as bracketed comments of the form ``[&key=value,...]``.
Metadata immediately following a node label are stored on that node, while
metadata immediately following an edge length, or a bare ``:``, are stored
on the corresponding edge.

Nodes with more than one parent are represented by labels prefixed with
``#``: every occurrence of the same ``#`` label refers to the same network
node rather than to a new one. When reading, metadata attached to any
occurrence are merged into that node, and conflicting values raise errors.
When writing, the node's subtree and metadata are written at its first
occurrence only.

:func:`from_newick` and :func:`to_newick` convert between a single Newick
string and a :class:`~phyloom.core.Net` or :class:`~phyloom.core.Tree`,
while :func:`load_newick` and :func:`dump_newick` read and write Newick
files.

The supported Newick grammar is:

.. code-block:: text

   newick_file   ::= newick_line+
   newick_line   ::= newick "\n"
   newick        ::= node ";"
   node          ::= children? reference? label metadata? edge?
   children      ::= "(" node ("," node)* ")"
   reference     ::= "#"
   label         ::= <possibly empty string without ":", "[", ",", ")" or ";">
   edge          ::= ":" edge_length? metadata?
   edge_length   ::= <float>
   metadata      ::= "[&" feature ("," feature)* "]"
   feature       ::= key "=" value
   key           ::= <string without ",", "=" or "]">
   value         ::= <string without "=" or "]">
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING, overload

from phyloom.core import Edge, Net, Node, Tree
from phyloom.io._utils import iter_stripped_lines

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Literal

    from phyloom.types import Metadata, NodeID, PathLike


@overload
def from_newick(newick: str, *, parse_as: Literal["tree"]) -> Tree[float | None]: ...
@overload
def from_newick(
    newick: str, *, parse_as: Literal["net"] = "net"
) -> Net[float | None]: ...
def from_newick(
    newick: str, *, parse_as: Literal["tree", "net"] = "net"
) -> Net[float | None]:
    """Parse a Newick string into a network or tree.

    Args:
        newick: Newick string to parse.
        parse_as: Whether to parse the Newick string as a tree or a network.

    Examples:
        Parse a network with node metadata, edge metadata, and a repeated
        node reference.

        >>> from phyloom.io import from_newick
        >>> newick = (
        ...     '((A[&host="human",date=2020.1]:0.1,'
        ...     '#H1[&host="avian",date=2020.2]:0.2)'
        ...     'AB[&kind="clade"]:0.3[&support=0.95],'
        ...     '(#H1[&status="resampled"]:[&route="reference"],'
        ...     'C[&host="swine",date=2020.3]:0.5)'
        ...     'BC[&kind="reticulate"]:[&support=0.85])'
        ...     'Root[&location="Zurich"]:0.0[&clock="days"];'
        ... )
        >>> from_newick(newick).pretty_print()
        Root (location=Zurich) [0.0, clock=days]
        |-- AB (kind=clade) [0.3, support=0.95]
        |   |-- A (host=human, date=2020.1) [0.1]
        |   `-- H1 (host=avian, date=2020.2, status=resampled) [0.2]
        `-- BC (kind=reticulate) [support=0.85]
            |-- ref H1 [route=reference]
            `-- C (host=swine, date=2020.3) [0.5]
    """

    newick = newick.strip()
    if not newick.endswith(";"):
        raise ValueError("Newick string must end with a semicolon ';'.")

    nodes: dict[NodeID, Node] = {}
    edges: dict[tuple[NodeID, NodeID], Edge[float | None]] = {}
    stack: list[list[tuple[NodeID, Edge[float | None]]]] = []
    current_children: list[tuple[NodeID, Edge[float | None]]] = []
    current_nodes: list[tuple[NodeID, Edge[float | None]]] = []
    references: dict[str, NodeID] = {}
    i = 0
    while True:

        def read_chars(stoppers: list[str]) -> str:
            nonlocal i
            chars = ""
            while i < len(newick) and newick[i] not in stoppers:
                chars += newick[i]
                i += 1
            if i == len(newick):
                raise ValueError(f"Expected one of {stoppers}, got end of string.")
            return chars

        def read_metadata() -> dict[str, object]:
            nonlocal i
            metadata: dict[str, object] = {}
            if newick[i] == "[":
                i += 1
                if newick[i] != "&":
                    raise ValueError("'[' must be followed by '&' for a feature block.")
                i += 1
                features = re.split(r",(?=[^,]+=)", read_chars(["]"]))
                i += 1
                for feature in features:
                    key, value = feature.split("=")
                    try:
                        metadata[key] = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        metadata[key] = value
            return metadata

        if newick[i] == "(":
            stack.append(current_nodes)
            current_nodes = []
            i += 1
            continue

        node_label = read_chars([":", "[", ",", ")", ";"])
        is_reference = node_label.startswith("#")
        node_name = node_label[1:] if is_reference else node_label
        node_metadata = read_metadata()
        if is_reference:
            if node_name in references:
                current_node_id = references[node_name]
                current_node = nodes[current_node_id]
                for key, value in node_metadata.items():
                    if (
                        key in current_node.metadata
                        and value != current_node.metadata[key]
                    ):
                        raise ValueError(
                            f"Conflicting metadata value for node #{node_name}: "
                            f"`{key}` is already `{current_node.metadata[key]}`, but "
                            f"attempted to set it to `{value}`."
                        )
                nodes[current_node_id].update(node_metadata)
            else:
                current_node = Node(node_name, **node_metadata)
                current_node_id = len(nodes)
                nodes[current_node_id] = current_node
                references[node_name] = current_node_id
        else:
            current_node = Node(node_name, **node_metadata)
            current_node_id = len(nodes)
            nodes[current_node_id] = current_node

        edge_length = None
        edge_metadata: dict[str, object] = {}
        if newick[i] == ":":
            i += 1
            edge_length_str = read_chars(["[", ",", ")", ";"])
            if edge_length_str:
                try:
                    edge_length = float(edge_length_str)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid edge length: {edge_length_str}."
                    ) from exc
            edge_metadata = read_metadata()
        current_edge = Edge(length=edge_length, **edge_metadata)

        for child, edge in current_children:
            edges[(current_node_id, child)] = edge
        current_children = []
        current_nodes.append((current_node_id, current_edge))

        if newick[i] == ")":
            current_children = current_nodes
            if not stack:
                raise ValueError("Unexpected ')' in Newick string.")
            current_nodes = stack.pop()
        elif newick[i] == ";":
            if i != len(newick) - 1:
                raise ValueError("Unexpected characters after ';' in Newick string.")
            if stack:
                raise ValueError("Unclosed '(' in Newick string.")
            if len(current_nodes) != 1:
                raise ValueError(
                    "Newick string must have exactly one root node, but found "
                    f"{len(current_nodes)} root nodes."
                )
            ((root, stem),) = current_nodes
            if parse_as == "tree":
                return Tree(nodes, edges, root, stem)
            return Net(nodes, edges, root, stem)

        i += 1


@overload
def load_newick(
    filepath: PathLike, *, load_as: Literal["tree"]
) -> Iterator[Tree[float | None]]: ...
@overload
def load_newick(
    filepath: PathLike, *, load_as: Literal["net"] = "net"
) -> Iterator[Net[float | None]]: ...
def load_newick(
    filepath: PathLike, load_as: Literal["tree", "net"] = "net"
) -> Iterator[Net[float | None]]:
    """Load networks or trees from a Newick file.

    Args:
        filepath: Path to the Newick file.
        load_as: Whether to load the Newick file as trees or networks.
    """
    for newick in iter_stripped_lines(filepath):
        yield from_newick(newick, parse_as=load_as)


def to_newick(net: Net[float | None]) -> str:
    """Serialize a network into a Newick string.

    Args:
        net: Network to serialize.

    Examples:
        Serialize a network with two inner nodes and a shared leaf.

        >>> from phyloom.core import Edge, Net, Node
        >>> from phyloom.io import to_newick
        >>> nodes = {
        ...     0: Node("root"),
        ...     1: Node("left"),
        ...     2: Node("right"),
        ...     3: Node("H1", host="human"),
        ... }
        >>> edges = {
        ...     (0, 1): Edge(length=0.1),
        ...     (0, 2): Edge(length=0.2),
        ...     (1, 3): Edge(),
        ...     (2, 3): Edge(length=0.4, route="reference"),
        ... }
        >>> net = Net(nodes, edges, root=0, stem=Edge(length=0.0))
        >>> to_newick(net)
        '((#H1[&host="human"])left:0.1,(#H1:0.4[&route="reference"])right:0.2)root:0.0;'
    """

    def label_metadata(metadata: Metadata) -> str:
        if not metadata:
            return ""
        reprs = {k: repr(v).replace("'", '"') for k, v in metadata.items()}
        for k, r in reprs.items():
            if "," in k or "=" in k or "]" in k:
                raise ValueError(
                    f"Invalid feature key `{k}`: keys must not contain ',', '=', or ']'."
                )
            if "=" in r or "]" in r:
                raise ValueError(
                    f"Invalid value `{r}` for feature `{k}`: values must not contain '=' or ']'."
                )
        features = [f"{k}={r}" for k, r in reprs.items()]
        return f"[&{','.join(features)}]"

    def label_edge(edge: Edge[float | None]) -> str:
        metadata_label = label_metadata(edge.metadata)
        if edge.length is None:
            return f":{metadata_label}" if metadata_label else ""
        return f":{edge.length}{metadata_label}"

    def label_node(node_id: NodeID) -> str:
        node = net.nodes[node_id]
        name_label = node.name
        if len(net.parents_of(node_id)) > 1:
            name_label = f"#{name_label}"
        if node_id in labeled:
            return name_label
        return f"{name_label}{label_metadata(node.metadata)}"

    newick: str = ""
    stem = Edge() if net.stem is None else net.stem
    stack: list[tuple[NodeID, Edge[float | None]] | str] = [";", (net.root, stem)]

    labeled: set[NodeID] = set()
    while stack:
        value = stack.pop()

        if isinstance(value, str):
            newick += value
            continue

        node_id, edge = value
        children = net.children_of(node_id)
        stack.extend([label_edge(edge), label_node(node_id)])
        if node_id not in labeled and children:
            stack.append(")")
            for child in reversed(children):
                stack.append((child, net.edges[(node_id, child)]))
                if child is not children[0]:
                    stack.append(",")
            stack.append("(")
        labeled.add(node_id)

    return newick


def dump_newick(nets: Iterable[Net[float | None]], filepath: PathLike):
    """Write networks to a Newick file.

    Args:
        nets: Networks to write.
        filepath: Path to the output Newick file.
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.writelines(to_newick(net) + "\n" for net in nets)
