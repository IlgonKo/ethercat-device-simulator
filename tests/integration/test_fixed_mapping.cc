#include "fixed_mapping.h"
#include <iostream>

static void require(bool value) { if (!value) throw std::runtime_error("test assertion failed"); }
int main() {
    FixedMapping guard({{{0x1600,0},1},{{0x1600,1},0x60400010},
                        {{0x1c12,0},1},{{0x1c12,1},0x1600}});
    require(guard.complete());
    guard.write(0x1c12,0,0,true);
    guard.write(0x1600,0,0,true);
    require(!guard.complete());
    guard.write(0x1600,1,0x60400010,true);
    guard.write(0x1600,0,1,true);
    require(!guard.complete());
    guard.write(0x1c12,1,0x1600,true);
    guard.write(0x1c12,0,1,true);
    require(guard.complete());
    for (int scenario=0; scenario<4; ++scenario) {
        bool rejected=false;
        try {
            if(scenario==0)guard.write(0x1600,1,0x607a0020,true);
            if(scenario==1)guard.write(0x1600,0,2,true);
            if(scenario==2)guard.write(0x1600,2,0,true);
            if(scenario==3)guard.write(0x1600,1,0x60400010,false);
        } catch(std::runtime_error const&) { rejected=true; }
        require(rejected && guard.complete());
    }
    std::cout << "Fixed mapping sequence and four rejection cases passed\n";
}
