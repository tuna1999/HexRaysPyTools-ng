"""Ground-truth fields of the negative-offset fixture structs (byte offsets/sizes)."""

NEGATIVE_FIELDS: dict[str, list[list[int]]] = {
    "NegOuter": [[0, 4], [4, 4]],
    "Neg16Outer": [[0, 2], [2, 2], [4, 2]],
}
