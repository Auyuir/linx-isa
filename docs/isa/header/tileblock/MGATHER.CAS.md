# MGATHER.CAS

## Overview

**Atomic Compare-and-Swap Gather from Memory to Tile**

`MGATHER.CAS` extends `MGATHER` with a per-element atomic compare-and-swap
operation. For each active element, the instruction atomically compares the
value in memory against an expected value from `SrcTile1`; if they match,
the memory location is updated with a desired value from `SrcTile2`. The
old value at the memory location is always written to the destination Tile.

Only the `[0, validRow) x [0, validCol)` region participates in the CAS
operation. The rest of the destination Tile is filled with `PadValue`.

Compare and swap element types must match `DataType`. The offset Tile element
type is independent and may be `u16`, `u32`, or `u64`.

## Assembly syntax

```asm
MGATHER.CAS <LB0:validCol, LB1:validRow, LB2:Col, DataType, PadValue>,
           SrcTile0<.reuse>, SrcTile1<.reuse>, SrcTile2<.reuse>,
           [RegSrc], ->DstTile<Size>
```

## Parameters

| Parameter | Description | Optional |
|-----------|-------------|----------|
| **validCol** | Number of valid columns in all source Tiles and the output Tile. Written to `LB0`. | No |
| **validRow** | Number of valid rows in all source Tiles and the output Tile. Written to `LB1`. | Yes, defaults to 1 |
| **Col** | Physical column count of the destination Tile, including padded columns. Written to `LB2`. | Yes, defaults to `validCol` |
| **Row** | Physical row count of the destination Tile. Hardware derives this as `Size / (Col * sizeof(DataType))`. | Hardware-derived |
| **DataType** | Element type in memory, also the element type of `SrcTile1` (expected) and `SrcTile2` (desired). | No |
| **PadValue** | Fill value for destination elements outside the valid region. Supported values are `Null`, `Zero`, `Max`, and `Min`. | Yes, defaults to `Null` |
| **RegSrc** | Base address register. | No |
| **SrcTile0** | Offset Tile. Each element is a byte offset from `RegSrc`. | No |
| **SrcTile1** | Expected value Tile (compare operand). Element type must match `DataType`. | No |
| **SrcTile2** | Desired value Tile (swap operand). Element type must match `DataType`. | No |
| **DstTile** | Output Tile that receives the old (pre-CAS) memory value at each position. | No |
| **Size** | Destination Tile size in bytes. Must equal `Row * Col * sizeof(DataType)`. | No |

The offset width is resolved from the element width used when `SrcTile0` was
written. Canonical forms allow `u16`, `u32`, or `u64` offsets.

## Encoding

`MGATHER.CAS` expands to:

- [BSTART.TMA](../../blockIntro/tma_block/header.md) `MGATHER.CAS, DataType`
- [B.DATR](../../header/B.DATR.md) `PadValue` (optional)
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB0` (`validCol`)
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB1` (`validRow`)
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB2` (`Col`, optional)
- [B.IOT](../../header/B.IOT.md) `SrcTile0<.reuse>, SrcTile1<.reuse>`
- [B.IOT](../../header/B.IOT.md) `SrcTile2<.reuse>, last, ->DstTile<Size>`
- [B.IOR](../../header/B.IOR.md) `RegSrc`

## Execution model

```c
void MGATHER.CAS(Tile dst, Scalar base, Tile offset, Tile expected, Tile desired) {
    for (int i = 0; i < Row; ++i) {
        for (int j = 0; j < Col; ++j) {
            if (i < validRow && j < validCol) {
                offset_t off = offset[i][j];
                // Atomic compare-and-swap on memory[base + off]
                T old = MemoryAtomicCAS(base + off, expected[i][j], desired[i][j]);
                dst[i][j] = old;
            } else {
                dst[i][j] = PadValue;
            }
        }
    }
}
```

## Notes

- `validCol <= Col` and `validRow <= Row` must hold.
- `Size` must be a whole multiple of `Col * sizeof(DataType)`.
- Elements outside the valid region do not issue memory accesses.
- The compare-and-swap is **atomic per element**: concurrent writes from other
  agents to the same address are ordered by the hardware atomic unit.
- A failed CAS (memory value does not match `expected`) writes the current
  memory value to `DstTile` so the caller can decide whether to retry.
- `SrcTile1` (expected) and `SrcTile2` (desired) must have the same element
  type as `DataType`. Their tile shapes must match the offset Tile's valid
  shape `[validRow, validCol]`.
