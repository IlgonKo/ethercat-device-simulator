#pragma once
#include <stdexcept>
#include "kickcat/ESC/EmulatedESC.h"

namespace cmmt {
using namespace kickcat;
// Fixed byte-aligned RxPDO contract: only tick slaves whose output FMMU is
// completely covered. Another slave's logical write must not advance this one.
inline bool targetsOutput(EmulatedESC& esc, DatagramHeader const& header, size_t rx_size) {
    for(unsigned i=0;i<16;++i) {
        fmmu::Register map{};
        if(esc.read(reg::FMMU+i*sizeof(map), &map, sizeof(map))!=sizeof(map))
            throw std::runtime_error("Cannot inspect output FMMU");
        if(!map.activate || map.type!=2 || map.physical_address!=0x1800)continue;
        if(map.length!=rx_size || map.logical_start_bit!=0 || map.logical_stop_bit!=7 || map.physical_start_bit!=0)
            throw std::runtime_error("Unsupported output FMMU layout");
        auto begin=static_cast<uint64_t>(header.address);
        auto end=begin+header.len;
        if(begin<=map.logical_address && end>=static_cast<uint64_t>(map.logical_address)+map.length)return true;
    }
    return false;
}

}
