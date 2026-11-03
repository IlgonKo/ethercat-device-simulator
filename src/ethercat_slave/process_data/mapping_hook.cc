#include "mapping_hook.h"
extern "C" kickcat::StatusCode originalMapping(kickcat::PDO*,kickcat::CoE::Dictionary&)
 asm("__real__ZN7kickcat3PDO16configureMappingERSt6vectorINS_3CoE6ObjectESaIS3_EE");
extern "C" kickcat::StatusCode wrappedMapping(kickcat::PDO*,kickcat::CoE::Dictionary&)
 asm("__wrap__ZN7kickcat3PDO16configureMappingERSt6vectorINS_3CoE6ObjectESaIS3_EE");
extern "C" kickcat::StatusCode wrappedMapping(kickcat::PDO* p,kickcat::CoE::Dictionary& d) {
 auto it=cmmt::mappingHooks.find(p);
 return it==cmmt::mappingHooks.end()?originalMapping(p,d):it->second();
}
