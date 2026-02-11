#include <pto/linx/AutoModeKernels.hpp>

extern "C" void pto_flash_attention_auto_i32(const int *query, const int *key,
                                             const int *value, int *dst) {
  pto::linx::auto_mode::flash_attention_kernel_i32(query, key, value, dst);
}
