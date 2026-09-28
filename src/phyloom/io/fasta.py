r"""Read and write multiple sequence alignments (MSA) in FASTA format.

FASTA is a text-based format for storing biological sequences. Each sequence
record begins with a header line starting with ``>``, followed by one or more
lines containing the sequence characters. When reading, the character lines
of a record are concatenated into a single sequence, leading and trailing
whitespace is stripped, and blank lines are ignored. When writing, each
sequence is written on a single line. Since the records form an alignment,
every sequence must contain at least one character and all sequences must
have the same length.

Headers often encode sequence metadata alongside the name, separated by
delimiters such as ``|``; for example, ``name|date|country``. By default,
the full header is used as the sequence name and no metadata are extracted.
:func:`load_fasta` accepts functions that extract the name and the metadata
of a :class:`~phyloom.core.SequenceRecord` from its header, and
:func:`dump_fasta` accepts a function that builds the header from a record,
so that metadata can be preserved in both directions.

The supported FASTA grammar is:

.. code-block:: text

   fasta_file      ::= sequence_record+
   sequence_record ::= header_line chars_line+
   header_line     ::= ">" header "\n"
   header          ::= <string>
   chars_line      ::= chars "\n"
   chars           ::= <non-empty string not starting with ">">
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.core import MSA, SequenceRecord
from phyloom.io._utils import iter_stripped_lines

if TYPE_CHECKING:
    from collections.abc import Callable

    from phyloom.types import Metadata, PathLike


def load_fasta(
    filepath: PathLike,
    *,
    sequence_name_from_header: Callable[[str], str] | None = None,
    sequence_metadata_from_header: Callable[[str], Metadata] | None = None,
) -> MSA:
    """Load a multiple sequence alignment from a FASTA file.

    Args:
        filepath: Path to the FASTA file.
        sequence_name_from_header: Optional function that extracts a sequence name from a header.
            If not provided, the full header is used as the sequence name.
        sequence_metadata_from_header: Optional function that extracts sequence metadata from a header.
            If not provided, no metadata is extracted.
    """

    def emit_sequence(header_line: str, chars: str) -> SequenceRecord:
        header = header_line[1:]
        name = (
            header
            if sequence_name_from_header is None
            else sequence_name_from_header(header)
        )
        seq = SequenceRecord(name=name, chars=chars)
        if sequence_metadata_from_header is not None:
            seq.update(sequence_metadata_from_header(header))
        return seq

    sequences: list[SequenceRecord] = []
    lines = iter_stripped_lines(filepath)
    current_header_line = next(lines)
    if not current_header_line.startswith(">"):
        raise ValueError(
            "FASTA file must start with a header line (starting with '>')."
        )

    current_chars = ""
    for line in lines:
        if line.startswith(">"):
            if not current_chars:
                raise ValueError(
                    "FASTA records must have at least one sequence character."
                )
            sequences.append(emit_sequence(current_header_line, current_chars))
            current_header_line = line
            current_chars = ""
        else:
            current_chars += line
    sequences.append(emit_sequence(current_header_line, current_chars))

    return MSA(sequences)


def dump_fasta(
    msa: MSA,
    filepath: PathLike,
    *,
    header_from_sequence: Callable[[SequenceRecord], str] | None = None,
):
    """Write a multiple sequence alignment to a FASTA file.

    Args:
        msa: Multiple sequence alignment to write.
        filepath: Path to the output FASTA file.
        header_from_sequence: Optional function to generate a header from a sequence.
            If not provided, the sequence name is used as the header.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        for sequence in msa:
            sequence_name = (
                sequence.name
                if header_from_sequence is None
                else header_from_sequence(sequence)
            )
            f.write(f">{sequence_name}\n")
            f.write(f"{sequence.chars}\n")
