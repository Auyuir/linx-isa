# MGATHER.CAS

## 说明

**原子比较-交换内存聚集（Atomic Compare-and-Swap Gather from Memory to Tile）**

`MGATHER.CAS` 在 `MGATHER` 的基础上扩展了逐元素的原子比较-交换（CAS）操作。
对每个有效元素，指令原子地比较目标内存地址的值与 `SrcTile1` 中存放的期望值
（expected）；如果相等，则将 `SrcTile2` 中的新值（desired）写入同一内存地址。
无论比较是否成功，**内存中的旧值**始终被写入输出 Tile（`DstTile`）。

只有 `[0, validRow) × [0, validCol)` 的有效区域参与 CAS 操作；超出有效区域的
输出位置写入 `PadValue`。

比较值和交换值的元素类型必须与 `DataType` 一致。偏移量 Tile 的元素类型独立，
可为 `u16`、`u32` 或 `u64`。

## 汇编语法

```asm
MGATHER.CAS <LB0:validCol, LB1:validRow, LB2:Col, DataType, PadValue>,
           SrcTile0<.reuse>, SrcTile1<.reuse>, SrcTile2<.reuse>,
           [RegSrc], ->DstTile<Size>
```

## 汇编符号

| 参数 | 说明 | 是否可选 |
|------|------|---------|
| **validCol** | 三个源 Tile 和输出 Tile 的有效列数。通过 `LB0` 传入。 | 否 |
| **validRow** | 三个源 Tile 和输出 Tile 的有效行数。通过 `LB1` 传入。 | 是，默认为 1 |
| **Col** | 输出 Tile 每行的物理列数（包含填充列）。通过 `LB2` 传入。 | 是，默认等于 `validCol` |
| **Row** | 输出 Tile 的物理行数（包含填充行）。硬件通过 `Size / (Col * sizeof(DataType))` 自动推导。 | 否（硬件推导） |
| **DataType** | 内存中元素的类型，也是 `SrcTile1`（期望值）和 `SrcTile2`（新值）的元素类型。 | 否 |
| **PadValue** | DstTile 中位于有效区域之外的填充值。可选值为 `Null`、`Zero`、`Max`、`Min`。 | 是，默认 `Null` |
| **RegSrc** | 输入全局寄存器 GGPR，用于存放 CAS 操作的内存基地址 `baseAddress`。 | 否 |
| **SrcTile0** | 偏移量 Tile，每个元素是一个相对于 `baseAddress` 的字节偏移量。 | 否 |
| **SrcTile1** | 期望值 Tile（比较操作数），元素类型必须与 `DataType` 一致。 | 否 |
| **SrcTile2** | 新值 Tile（交换操作数），元素类型必须与 `DataType` 一致。 | 否 |
| **DstTile** | 输出 Tile，用于存放 CAS 操作前内存中的旧值。 | 否 |
| **Size** | 输出 Tile 的大小，必须等于 `Row * Col * sizeof(DataType)`。 | 否 |

`SrcTile0` 中 offset 的位宽由写入该 Tile 时使用的元素位宽决定，规范形式
支持 `u16`、`u32` 和 `u64`。

## 编码格式

`MGATHER.CAS` 编码为以下指令：

- [BSTART.TMA](../../blockIntro/tma_block/header.md) `MGATHER.CAS, DataType`
- [B.DATR](../../header/B.DATR.md) `PadValue` *（可选）*
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB0` *（`validCol`）*
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB1` *（`validRow`）*
- [B.DIM](../../header/B.DIM.md) `reg, imm, ->LB2` *（`Col`，可选）*
- [B.IOT](../../header/B.IOT.md) `SrcTile0<.reuse>, SrcTile1<.reuse>`
- [B.IOT](../../header/B.IOT.md) `SrcTile2<.reuse>, last, ->DstTile<Size>`
- [B.IOR](../../header/B.IOR.md) `RegSrc`

## 执行模型

```c
void MGATHER.CAS(Tile dst, Scalar base, Tile offset, Tile expected, Tile desired) {
    for (int i = 0; i < Row; ++i) {
        for (int j = 0; j < Col; ++j) {
            if (i < validRow && j < validCol) {
                offset_t off = offset[i][j];
                // 对 memory[base + off] 执行原子 CAS
                T old = MemoryAtomicCAS(base + off, expected[i][j], desired[i][j]);
                dst[i][j] = old;
            } else {
                dst[i][j] = PadValue;
            }
        }
    }
}
```

## 注意事项

- `validCol <= Col`, `validRow <= Row`。
- `Size` 必须是 `Col * sizeof(DataType)` 的整数倍。
- 超出有效区域的位置不产生访存，直接写入 `PadValue`。
- **比较-交换是逐元素原子的**：来自其他代理对同一地址的并发写入由硬件原子单元排序。
- CAS 失败时（内存值不匹配期望值），仍将当前内存值写入 `DstTile`，调用方
  可据此决定是否需要重试。
- `SrcTile1`（期望值）和 `SrcTile2`（新值）的元素类型必须与 `DataType` 一致。
  两者的有效形状必须与偏移量 Tile 对齐，即 `[validRow, validCol]`。
