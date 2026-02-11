#include <pto/pto-inst.hpp>

#include <cstdint>
#include <cstdio>

namespace {

constexpr unsigned kTileElemsI32 = 1024u;

using GlobalTile = pto::GlobalTensor<int32_t, pto::Shape<1, 1, 1, 8, 8>, pto::Stride<64, 64, 64, 8, 1>>;
using TileMat = pto::Tile<pto::TileType::Mat, int32_t, 16, 16, pto::BLayout::ColMajor, 8, 8, pto::SLayout::RowMajor,
                          512>;
using TileLeft = pto::TileLeft<int32_t, 16, 16, 8, 8>;
using TileRight = pto::TileRight<int32_t, 16, 16, 8, 8>;
using TileAcc = pto::TileAcc<int32_t, 16, 16, 8, 8>;

inline int32_t *tile_ptr(int32_t *buffer, unsigned tile_idx)
{
    return buffer + tile_idx * kTileElemsI32;
}

inline const int32_t *tile_ptr(const int32_t *buffer, unsigned tile_idx)
{
    return buffer + tile_idx * kTileElemsI32;
}

void init_tile_pattern(int32_t *tile, int32_t seed)
{
    for (unsigned i = 0; i < kTileElemsI32; i++) {
        tile[i] = 0;
    }
    for (unsigned i = 0; i < 64; i++) {
        int32_t lane = (int32_t)(i % 13u) - 6;
        int32_t col = (int32_t)(i & 7u) - 3;
        tile[i] = lane * seed + col;
    }
}

void matmul_tile_i32(const int32_t *lhs, const int32_t *rhs, int32_t *dst)
{
    GlobalTile lhsGlobal(const_cast<int32_t *>(lhs));
    GlobalTile rhsGlobal(const_cast<int32_t *>(rhs));
    GlobalTile dstGlobal(dst);

    TileMat lhsMat;
    TileMat rhsMat;
    TileLeft lhsTile;
    TileRight rhsTile;
    TileAcc accTile;

    pto::TASSIGN(lhsMat, 0x0000);
    pto::TASSIGN(rhsMat, 0x2000);
    pto::TASSIGN(lhsTile, 0x4000);
    pto::TASSIGN(rhsTile, 0x6000);
    pto::TASSIGN(accTile, 0x8000);

    pto::TLOAD(lhsMat, lhsGlobal);
    pto::TLOAD(rhsMat, rhsGlobal);
    pto::TMOV(lhsTile, lhsMat);
    pto::TMOV(rhsTile, rhsMat);
    pto::TMATMUL(accTile, lhsTile, rhsTile);
    pto::TSTORE(dstGlobal, accTile);
}

int64_t checksum_tiles_i32(const int32_t *tiles, unsigned tile_count)
{
    int64_t checksum = 0;
    for (unsigned tile = 0; tile < tile_count; tile++) {
        const int32_t *base = tile_ptr(tiles, tile);
        for (unsigned i = 0; i < 64; i++) {
            checksum += (int64_t)base[i];
        }
    }
    return checksum;
}

int64_t run_gemm_kernel()
{
    alignas(64) int32_t gemmA[9 * kTileElemsI32];
    alignas(64) int32_t gemmB[8 * kTileElemsI32];
    alignas(64) int32_t gemmOut[11 * kTileElemsI32];

    for (unsigned tile = 0; tile < 9; tile++) {
        init_tile_pattern(tile_ptr(gemmA, tile), (int32_t)(3 + tile));
    }
    for (unsigned tile = 0; tile < 8; tile++) {
        init_tile_pattern(tile_ptr(gemmB, tile), (int32_t)(11 + tile));
    }
    for (unsigned i = 0; i < 11 * kTileElemsI32; i++) {
        gemmOut[i] = 0;
    }

    const unsigned lhsMap[11] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 0, 1};
    const unsigned rhsMap[11] = {0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 7};
    for (unsigned tile = 0; tile < 11; tile++) {
        matmul_tile_i32(tile_ptr(gemmA, lhsMap[tile]), tile_ptr(gemmB, rhsMap[tile]), tile_ptr(gemmOut, tile));
    }

    return checksum_tiles_i32(gemmOut, 11);
}

int64_t run_flash_kernel()
{
    alignas(64) int32_t flashQ[5 * kTileElemsI32];
    alignas(64) int32_t flashK[5 * kTileElemsI32];
    alignas(64) int32_t flashV[4 * kTileElemsI32];
    alignas(64) int32_t flashOut[9 * kTileElemsI32];
    alignas(64) int32_t score[9 * kTileElemsI32];

    for (unsigned tile = 0; tile < 5; tile++) {
        init_tile_pattern(tile_ptr(flashQ, tile), (int32_t)(17 + tile));
        init_tile_pattern(tile_ptr(flashK, tile), (int32_t)(29 + tile));
    }
    for (unsigned tile = 0; tile < 4; tile++) {
        init_tile_pattern(tile_ptr(flashV, tile), (int32_t)(41 + tile));
    }
    for (unsigned i = 0; i < 9 * kTileElemsI32; i++) {
        flashOut[i] = 0;
        score[i] = 0;
    }

    const unsigned scoreQMap[9] = {0, 1, 2, 3, 4, 0, 1, 2, 3};
    const unsigned scoreKMap[9] = {0, 1, 2, 3, 4, 1, 2, 3, 4};
    const unsigned scoreVMap[9] = {0, 1, 2, 3, 0, 1, 2, 3, 0};

    for (unsigned tile = 0; tile < 9; tile++) {
        matmul_tile_i32(tile_ptr(flashQ, scoreQMap[tile]), tile_ptr(flashK, scoreKMap[tile]), tile_ptr(score, tile));
        matmul_tile_i32(tile_ptr(score, tile), tile_ptr(flashV, scoreVMap[tile]), tile_ptr(flashOut, tile));
    }

    return checksum_tiles_i32(flashOut, 9);
}

} // namespace

int main()
{
    const int64_t gemmChecksum = run_gemm_kernel();
    const int64_t flashChecksum = run_flash_kernel();

    std::printf("PTO_SIM_GEMM_CHECKSUM=0x%016llx\n", (unsigned long long)(uint64_t)gemmChecksum);
    std::printf("PTO_SIM_FLASH_CHECKSUM=0x%016llx\n", (unsigned long long)(uint64_t)flashChecksum);
    return 0;
}
