#include "dynamic_mapping.h"
#include <cassert>
#include <functional>
using namespace cmmt;
static void reject(std::function<void()> fn) {bool caught=false;try{fn();}catch(MappingError const&){caught=true;}assert(caught);}
int main(){
 DynamicMapping m({{{0x6040,0},{16,true,false}},{{0x6041,0},{16,false,true}},{{0x607a,0},{32,true,false}}});
 auto w=[&](int i,int s,uint32_t v){m.write(i,s,v,true);};
 reject([&]{m.prepare();});assert(!m.active());
 w(0x1600,1,0x607a0020);w(0x1600,2,0x60400010);w(0x1600,3,8);w(0x1600,0,3);
 w(0x1c12,1,0x1600);w(0x1c12,0,1);
 w(0x1a00,1,0x60410010);w(0x1a00,0,1);w(0x1c13,1,0x1a00);w(0x1c13,0,1);
 m.activate(m.prepare());assert(DynamicMapping::bytes(m.configuration().rx)==7);
 reject([&]{m.write(0x1c12,0,0,false);});assert(m.read(0x1c12,0)==1);
 w(0x1c12,0,0);w(0x1600,0,0);w(0x1600,2,0x607a0020);
 reject([&]{w(0x1600,0,2);});assert(m.read(0x1600,0)==0);
 assert(DynamicMapping::bytes(m.configuration().rx)==7);
 reject([&]{w(0x1600,2,0x60410010);});reject([&]{w(0x1600,2,0x60400008);});
 w(0x1600,1,0x60400010);w(0x1600,2,248);w(0x1600,3,248);
 w(0x1600,0,3);assert(m.read(0x1600,0)==3); // 64 bytes incl. repeated padding
 w(0x1600,0,0);w(0x1600,4,8);reject([&]{w(0x1600,0,4);});
 reject([&]{w(0x1600,0,17);});reject([&]{w(0x1600,17,8);});
}
