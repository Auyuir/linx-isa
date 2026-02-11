#include <pto/linx/AutoModeKernels.hpp>

extern "C" void pto_gemm_auto_i32(const int *lhs, const int *rhs, int *dst) {
  pto::linx::auto_mode::gemm_kernel_i32(lhs, rhs, dst);
}
