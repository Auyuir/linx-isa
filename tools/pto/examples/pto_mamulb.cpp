#include <pto/linx/TileOps.hpp>

extern "C" void pto_mamulb_i32_8x8(const int *lhs, const int *rhs, int *dst) {
  // v0.3 bring-up size mapping: bytes = 2^(SizeCode+4). 4KiB => SizeCode=8.
  constexpr unsigned SizeCode = 8u;
  auto t_lhs = pto::linx::tload<SizeCode>(lhs);
  auto t_rhs = pto::linx::tload<SizeCode>(rhs);
  auto t_dst = pto::linx::mamulb<8, 8, 8>(t_lhs, t_rhs);
  pto::linx::tstore<SizeCode>(dst, t_dst);
}
