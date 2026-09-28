from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from phyloom.core._sequence_record import SequenceRecord
    from phyloom.types import PathLike


class MSA:
    """Multiple sequence alignment.

    Args:
        sequences: Sequence records in alignment order.

    Examples:
        Maintain a multiple sequence alignment of three sequences.

        >>> from phyloom.core import MSA, SequenceRecord
        >>> sequences = [
        ...     SequenceRecord("human", "ACGT"),
        ...     SequenceRecord("mouse", "A-GT"),
        ...     SequenceRecord("avian", "AC-T"),
        ... ]
        >>> msa = MSA(sequences)
        >>> [sequence.name for sequence in msa]
        ['human', 'mouse', 'avian']
        >>> msa.n_sequences, msa.n_sites, msa.shape, msa.n_unique_sequences
        (3, 4, (3, 4), 3)
        >>> len(msa)
        3

        Empty and ragged alignments are rejected.

        >>> MSA([])
        Traceback (most recent call last):
        ...
        ValueError: MSA must contain at least one sequence.
        >>> MSA([SequenceRecord("a", "AC"), SequenceRecord("b", "A")])
        Traceback (most recent call last):
        ...
        ValueError: All sequences in the alignment must have the same length (got lengths: {1, 2}).
    """

    def __init__(self, sequences: Iterable[SequenceRecord]):
        if not sequences:
            raise ValueError("MSA must contain at least one sequence.")

        self._sequences = list(sequences)
        lengths = {seq.n_chars for seq in sequences}
        if len(lengths) > 1:
            raise ValueError(
                f"All sequences in the alignment must have the same length (got lengths: {lengths})."
            )
        (self._n_sites,) = lengths

    @property
    def sequences(self) -> tuple[SequenceRecord, ...]:
        """Sequence records in alignment order."""
        return tuple(self._sequences)

    @property
    def n_sequences(self) -> int:
        """Number of sequences in the alignment."""
        return len(self.sequences)

    @property
    def n_sites(self) -> int:
        """Number of aligned sites in each sequence."""
        return self._n_sites

    @property
    def shape(self) -> tuple[int, int]:
        """Alignment shape as ``(n_sequences, n_sites)``."""
        return self.n_sequences, self.n_sites

    @property
    def n_unique_sequences(self) -> int:
        """Number of distinct character rows in the alignment."""
        return len(np.unique([list(seq.chars) for seq in self], axis=0))

    def dump(
        self,
        filepath: PathLike,
        header_from_sequence: Callable[[SequenceRecord], str] | None,
    ):
        """Write the alignment to a FASTA file.

        Args:
            filepath: Path to the output FASTA file.
            header_from_sequence: Optional function to generate a header from a sequence.
                If not provided, the sequence name is used as the header.
        """
        from phyloom.io import dump_fasta

        dump_fasta(self, filepath, header_from_sequence=header_from_sequence)

    def __len__(self) -> int:
        """Return the number of sequences in the alignment."""
        return self.n_sequences

    def __iter__(self) -> Iterator[SequenceRecord]:
        """Iterate over sequence records in alignment order."""
        return iter(self.sequences)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(n_sequences={self.n_sequences}, n_sites={self.n_sites})"
