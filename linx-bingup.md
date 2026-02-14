# Linx ISA bring up plan

Please follow my following word and make adjustmend to the ISA documents, compiler, qemu, linux, core designs. And then update the skills and related information.

Check 1:
Linx ISA is a block structured instruction set architecture. A block structure is also called hierachical structure.
Linx CPU based on this block structure, has two hierachical set of architectural states.

Check 2:
Global States, GSTATE, 1st layer, shared by all processing units PEs
    - 24 GPRs (R0-R23)
    - 32 Tile Registers
    - SSR (system status registers)
Check 3:
Local Block State called BSTATE, 2nd layer, different type of blocks have different states
    - Scalar Block States (life cycles only within one basic block)
        - T hand (4 depth)
        - U hand (4 depth)
        - BCARG
            - block type
            - current bpc
            - next bpc
            - setc conditional flags
    - Vector Block States 
        - T hand (4 depth, 64bit)
        - U hand (4 depth, 64bit)
        - VT hand (4 depth, each lane is 32bit, variable lane count)
        - VU hand (4 depth, each lane is 32bit, variable lane count)
        - VM hand (4 depth, each lane is 32bit, variable lane count)
        - VN hand (4 depth, each lane is 32bit, variable lane count)
    - Template Block States
        - Internal states for local FSMs so it can be restarted at the state

Check 4:
ESAVE, and ERET are template blocks that save different 2nd layer to the 1st layer. 2nd layer is a union structure.

Check 5:
The whole LinxCPU is naturally designed as hierachical architectural states in the first day.

So the machine model is a scheduler called BCC (block control core) + many heterogenious PEs.
All the PEs and BCC share the common first layer state (global state), including GPR, tile register, and SSRs
But different PEs has its own local state based on its block type.

Check 6:
For linxisa, all the computations are organized into blocks. There is no instructions between blocks. You could have empty blocks.

The program order sequentially executes the blocks with different types.

BlockA -> BlockB -> BlockC 

Check 7:
Control flow is performed after the commit of the current block. Inside each block, it computes or predict the next block address and put it in BARG.NextBPC. During the commit of the block, the next bpc will become visible and set to the global PC.

Check 8:
All control flows MUST jump to a block boundary instruction (BSTART, BSTOP with different kind). 
If the control flow jump in the middle of the block. And exception is generated (Illegal control flow). 
Note that this feature is for safety purposes. LinxISA design this feature for *control flow integrety*. 
A block assumes fall through if there is no branch target set internally.

Check 9:
Block Boundary Instructions
    - BSTART.xxx terminates the previous block and start the next block
    - C.BSTART
    - BSTOP serve as nop if jump directly
    - C.BSTOP, L.BSTOP
    - BWE (bus wait event), BWI (bus wait interrupt) are special BSTOPs
    - ACRE, ACRC, EBREAK are all block boundaries that terminates the blocks and switch to another ACR level

Check 10:
Block Attribute Instructions
There are instructions that give additional information for the block structure, but not directly serve as computations.
    - B.ARG conveys the immediate value to the block argument during the block initialization. Different types of blocks might have different interpretations of the B.ARG.
    - B.ATTR attributes normally control the barriers between the block
    - B.IOR (block input and output registers) acts like a sensitivity list that specifies the live-in and live-out for the block. Only takes effect for decoupled blocks and template blocks. The input and output are absolute GPR ids.
    - B.IOT (block input and output tile registers) specifies the tile register input and output for the block. It is different because it uses relative register encoding in SSA form. B.IOT [T#k, M#j] -> U. Tile output register for each block never overides its input tile register.
    - B.IOD (currently absolete) used for dummy dependence between block instructions. 

Check 11:

Scalar blocks, Termplate blocks, Tile blocks orgnize in a sequential way.

LinxCPU will execute blocks out-of-order or in-order depending on the implementation. But the block commit must commit in order. LinxCPU will use *block reorder buffer* to control the retirement of the block despite different type of blocks.
The scheduling of the blocks should not look at the type of the blocks. It is purely depending on the dependence between the blocks.

A block instruction is issued for PE execution whenever its inputs are ready. Scalar blocks normally contains a few instructions. This will harm performance, so for scalar blocks, there is no need to wait for the input to be ready. All the block instructions are waited in the scalar issue queue.

Check 12:
Another way of interpreting block instructions

A block instruction is a variable length CISC instruction that is encoded into several 16bit,32bit,48bit and 64bit instructions.

For example, a scalar block instruction:

BSTART
add a0, a1 -> t
sub t#1, a2 -> u
sw zero, [u#1, 100]
BSTOP

The global inputs are [a0, a1, a2], the private inputs are forward within T, U relative registers. There is a store instruciton also serve as the output of the block.

You can think it as a fused instruction 
```
sw zero, [(a0+a1)-a2,100]
```
Note that all register T, U, queues must have one producer and one consumer (to serve as a internal forward behaviour)

LinxISA add this restrictions to make the hardware much easier for maintaining the speculative states. We are telling the LinxCPU those are temporary results that are definately giving forward behaviour. So that the microarch can free the ptag resource earlier. 

Guide for compilers, all block internal states should use T/U hand as mush as possible.

Check 13:
Coupled and decoupled blocks

Coupled blocks embed microinstructions into BSTART and BSTOP form. Those micro-instructions are executed in the first layer. 
Decoupled blocks split the header and block in different PCs. The header is executed in the first layer, the body is executed in the second layer.

- B.TEXT is only visible in decoupled blocks. B.TEXT is assigned with an offset to its body.

BSTART
...
B.TEXT <body_lable>
BSTOP/BSTART

body_label:
    inst0
    inst1
    inst2
    bstop

Check 14:
B.TEXT decides whether the block has a separate body. Template blocks do have a block body but the micro-architecture might generate the body for it. 

Template blocks are implementation defined.

- Implementation A: it stores the body into the ROM inside the LinxCPU
- Implementation B: it dynamically generates uops in CT (code template FSM)
- Implementation C: it packs input data and pack into commands, send to an internal engine and do the execution.

Check 15:
LinxISA provides a generic TEPL block type, so that it can be extended different acceration PEs in the second layer.

For example
```
BSTART.TEPL opcode
B.ATTR attributes
B.ARG arguments
B.IOR [input_regs], [output_regs]
...
B.IOR [input_regs], [output_regs]
B.IOT [input_tile_regs], -> output_tile_type
...
B.IOT [input_tile_regs], -> output_tile_type
BSTOP
```
The above only specifies a block instruction, its input, output relative to other block instructions.

The compiler is advised to provide intrinsic like
```
__linx_block(opc, ins(%r0, ..., %rn, %tile0, ..., %tilen), outs(%r0, ..., %rm, %tile0, ..., %tilem))
```
to provide generic interface with in-core accelerator PEs. Note that this PE Must not touch memory access.

In the future, we will provide a list of accelerated blocks.

Check 15:

Floating point instructions. LinxISA do not have dedicated FP architectural state for FP. All the integer and fp use the same layer 1 arch state. Change block type to BSTART.FP if there exist FP instructions. BSTART.FP allow normal scalar instructions interleave with FP. BSTART.FP only serve as a hint.

Check 16:

Vector instructions. LinxISA choses to use different vector instruction design compared to AVX, SVE. It is a SIMT-style instruction set with hardware loop design.

For loops like this
```
for (int i=0; i<n; i++) {
    for (int j=0; j<m; j++) {
        a[i][j] = i + j;
    }
}
```
The assembly code should be like this:
```
BSTART.MSEQ     ; sequential vector execution of block body
B.TEXT <.body>
B.IOR [s0], []  ; s0 contains array a base
B.DIM a0 -> lb0 ; a0 contains value m
B.DIM a1 -> lb1 ; a1 contains value n
BSTOP

.body:
v.add lc0.sw, lc1.sw -> vt
v.st vt#1, [ri0, lc0<<2, lc1<<10] ; assumes higher dim stride is 1024
bstop
```

- Vector blocks use the same B.IOR, B.IOT to specify input, output
- Vector block body only specify one lane of compute, repeated by Block DIM
- Vector blocks unroll the loop and commit loop iterations in order


# Check 17

BSTART.MPAR : parallel execution of block in parallel

The semantics like this
```
parallel_for (int i=0; i<n; i++) {
    parallel_for (int j=0; j<m; j++) {
        a[i][j] = i + j;
    }
}
```
The difference of PAR and VEC is the execution model
PAR: execute block body in parallel (parallel commits for all lanes)
SEQ: execute block body in vector mode (parallel in VLEN, but sequential between VLEN)

# Check 18

BSTART.VPAR : parallel execution of vector without touching memory, it only accesses tile register
BSTART.VSEQ : sequential execution of vector without touching meory, it only accesses tile register 

Please note that we suggest the usage of VPAR and VSEQ. 

Tile registers are not memory accesses. Different vector blocks can be executed out of order. 
This is a significant source of performance improvement.

VPAR and VSEQ can be executed speculatively.

# Check 19

Tile registers are special concept defined in Linx ISA.

- 32 tile registers as architectural state
- Tile registers are variable in sizes. But they have a minimum size of 512B, and maximum size of 4KB.
- Architectural states are 32x4KB = 128KB 
- Architectural states all record tile size for tile registers as architectural states
- LinxCPU implementation will squeeze the bubbles and allocate tile registers in different places.
- Tile registers can be renamed. There are more physical tile registers than architectural tile registers.
- Tile registers are referenced relatively.

# Check 20

For compiler writers, tile register allocation and vector register is a very difficult task because it uses Clockhands. Scalar block do not have the problem because there is no internal control flow for scalar blocks. So T que and U que do not need to consider control flow. But for tile and vector use and def are obfusecated with control flow. We need to make sure at each dynamic path, the relative distance of two tile registers are in the same distance. You need to check the clockhand paper online.

# Check 21
You need to understand the general structure of the LinxCPU. The interface between the first layer and second layer is called block command. Normally LinxCPU preposes the following:
- BSTART.XXX pack the opcode, bid, and info into block command
- B.IOR: read the input register data when the input are ready, pack them into block command. Reserve a ptag for output registers.
- B.IOT: perform tile rename, work out the input and output tile register address and pack them into block command.
- B.ARG/B.ATTR: pack the immediate value to the block command.
- B.IOD: wait for the block comnand to resolve dependence
- B.DIM: pack the block dimension into the block command
- B.TEXT: calculate the pc and pack the pc into block command
- BSTOP: check all field are ready and then kick off the block command to the second layer (PE execution)

# Check 22:
You need to understand the general structure of the LinxCPU. The second layer PE is only active whenever it receives a valid block command. The PE first receives  and buffer the block command. Parse the command into detailed operations.

- Vector PE: retrive the input data, block dim repeat value, execution mode, get the pc and jump to the pc.
- Cube PE: retrieve the input tile address for left and right, the M, N, K value, and split the uops for systolic arrarys
- TAU PE: retireve the input tile address, the opcode. Start loading from tiles and pipe into accelerators.
- TMA PE: retrieve the arguemnt, layout, stride, range of global tenor. Performs a range load/store.
- More PE: B.IOR, B.IOT, are interpreted based on its own defination.

But whenever a block command finishes execution, the PE need to send block command back to first layer scheduler.
Before resolve, it need to:
1. pack the liveout value into block command
2. update status (success, fail, exceptions) to the block rob.

The first layer has a BROB that keep tracks of all block command status and retire the command in order.
Some command might be flushed due to mispredication and speculations.

Note: a PE might execute multiple block command at a time.

# Check 23:
The Vector PE do not have direct access to main memory. Only scalar pipe and TMA has access. (scalar load, scalar store, TLOAD, TSTORE). They are issued out of order but the memory access is in order.

Note that, LinxISA memory model is **TSO**. Store values should not be reordered despite their address might differ.

# Check 24:

Scalar load/store, Tile load/store must always go to the same TLB and MMU. Tile load/store are ranged access so they might need multiple lookup. Page fault might happen at tile load/store. We should treat tile load/store as restartable. OS kernels must prepare all TLOAD, TSTORE pages before resuming back to execution.

# Check 25:

BSTART.MSEQ, BSTART.MPAR rely on the vector core to perform memory access. But the vector core do not have direct access to memory. So whenever the vector core locates the global memory. It has to do the following:
1. Write the global DDR address to tile register and notify TMA
2. TMA read from the tile register, get the DDR address, and perform load
3. Load data return back to tile register, and notify vector core
4. Vector core read from the tile resgiter and get the value.      

There are memory barriers between MSEQ, MPAR to avoid potential memory conflicts.

# Check 26:
For vector blocks:
1. You must encode load/store for tile direction as `load.local` and `store.local` for example `lw.local [ri0, vt#1] -> vt` There is 1 bit in the encoding.
2. You must label global load/store as `load.brg` and `store.brg` to do the bridged access.
3. Vector core could not directly access first layer registers. They need to use `ri0, ri1, ..., rin` to map B.IOR ordered arguments. And same for output.
4. Vector core need to reference tile input base as `TA`, `TB` ..., output base as `TO`, scratch base as `TS`.
5. Vector block can have scalar instructions and vector instructions mixed together. Scalar instructions are similar to uniform instructions that only access (t, u, p). Vector instructions access (vt, vu, vm, vn and predicate p)
6. Vector groups are similar to SIMT warps. You have group level instructions and inter-group instructions.