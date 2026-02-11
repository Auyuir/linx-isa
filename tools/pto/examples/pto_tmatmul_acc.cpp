#include <pto/linx/TileOps.hpp>

extern "C" void pto_tmatmul_acc_i32_8x8(const int *lhs, const int *rhs, int *acc_dst) {
  // v0.3 bring-up size mapping: bytes = 2^(SizeCode+4). 4KiB => SizeCode=8.
  constexpr unsigned SizeCode = 8u;
  auto t_lhs = pto::linx::tload<SizeCode>(lhs);
  auto t_rhs = pto::linx::tload<SizeCode>(rhs);
  auto t_acc = pto::linx::mamulb<8, 8, 8>(t_lhs, t_rhs);
  auto t_out = pto::linx::tmatmul_acc<8, 8, 8>(t_acc, t_lhs, t_rhs);
  pto::linx::tstore<SizeCode>(acc_dst, t_out);
}
