#include <array>
#include <iostream>
#include <stdexcept>
#include "kickcat/EmulatedNetwork.h"
#include "pdo_target.h"

using namespace kickcat;
static void require(bool condition, char const* message) {
    if(!condition)throw std::runtime_error(message);
}

int main() {
    std::array<EmulatedESC,4> slaves;
    EmulatedNetwork network({&slaves[0],&slaves[1],&slaves[2],&slaves[3]});
    // Exercise actual frame routing: a broadcast must traverse all four ESCs once.
    Frame frame;
    uint16_t value=0;
    frame.addDatagram(0,Command::BRD,static_cast<uint32_t>(reg::AL_STATUS)<<16,&value,sizeof(value));
    frame.finalize();
    require(network.route(frame),"Network rejected frame");
    frame.resetContext();
    auto [header,data,wkc]=frame.peekDatagram();
    (void)header; (void)data;
    require(wkc && *wkc==4,"Four ESC broadcast WKC mismatch");

    for(size_t i=0;i<slaves.size();++i) {
        fmmu::Register mapping{};
        mapping.logical_address=0x1000+i*24;
        mapping.length=24;
        mapping.logical_stop_bit=7;
        mapping.physical_address=0x1800;
        mapping.type=2; mapping.activate=1;
        DatagramHeader write{};
        write.command=Command::BWR;
        write.address=static_cast<uint32_t>(reg::FMMU)<<16;
        write.len=sizeof(mapping);
        uint16_t count=0;
        slaves[i].processDatagram(&write,&mapping,&count);
        require(count==1,"FMMU configuration failed");
    }
    for(size_t target=0;target<slaves.size();++target) {
        DatagramHeader output{};
        output.command=Command::LWR; output.address=0x1000+target*24; output.len=24;
        for(size_t i=0;i<slaves.size();++i)
            require(cmmt::targetsOutput(slaves[i],output,24)==(i==target),"Output targeted wrong model");
        output.len=23;
        require(!cmmt::targetsOutput(slaves[target],output,24),"Partial PDO advanced model");
    }
    DatagramHeader all{}; all.command=Command::LRW; all.address=0x1000; all.len=96;
    for(auto& slave:slaves) require(cmmt::targetsOutput(slave,all,24),"Combined PDO omitted slave");
    std::cout<<"Four ESC routing and per-axis PDO targeting passed\n";
}
