#include <pto/linx/TileOps.hpp>

extern "C" void pto_tload_store_i32(const int *src, int *dst) {
  // v0.3 bring-up size mapping: bytes = 2^(SizeCode+4). 4KiB => SizeCode=8.
  constexpr unsigned SizeCode = 8u;
  auto tile = pto::linx::tload<SizeCode>(src);
  pto::linx::tstore<SizeCode>(dst, tile);
}
