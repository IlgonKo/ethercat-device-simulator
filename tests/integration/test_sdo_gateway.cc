#include <fstream>
#include <thread>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include "kickcat/simulation/SimulatedSlave.h"
#include "ipc/model_client.h"
#include "ipc/sdo_gateway.h"
using namespace kickcat;
void require(bool condition,char const* message){if(!condition)throw std::runtime_error(message);}
int main(int argc,char** argv) {
    try {
        require(argc==4,"fixture manifest, contract and socket required");
        json manifest,spec; std::ifstream(argv[1])>>manifest; std::ifstream(argv[2])>>spec;
        ModelClient client(argv[3]);
        require(client.request({{"op","describe"}})==spec,"contract mismatch");
        size_t axis=0;
        for(;axis<spec["devices"].size();++axis)
            if(spec["devices"][axis]["device"]["model"]["type"]=="copley_drive_sim")break;
        require(axis<spec["devices"].size(),"Copley axis required");
        auto sim=sim::buildSlave(manifest["slaves"][axis]);
        auto& gateway=cmmt::sdoGateways[sim.mailbox.get()];
        for(auto const& e:spec["devices"][axis]["contract"]["entries"])
            gateway.entries.emplace(e["index"],e["subindex"]);
        gateway.request=[&](json r){r["slave_index"]=axis;return client.request(r);};
        unsigned calls=0;
        auto exchange=[&](uint16_t index,uint8_t sub,uint8_t command,uint32_t value=0) {
            std::vector<uint8_t> raw(128,0);
            auto h=reinterpret_cast<mailbox::Header*>(raw.data());
            h->len=10;h->type=mailbox::Type::CoE;h->count=1+(calls++%7);
            auto coe=reinterpret_cast<CoE::Header*>(raw.data()+6);coe->service=CoE::Service::SDO_REQUEST;
            raw[8]=command;raw[9]=index&255;raw[10]=index>>8;raw[11]=sub;
            for(int i=0;i<4;++i)raw[12+i]=value>>(8*i);
            auto response=sim.mailbox->processRequest(std::move(raw));
            require(response.size()==128,"mailbox buffer truncated: ESC would never signal ready");
            require(response[9]==(index&255)&&response[10]==(index>>8)&&response[11]==sub,"wrong echoed index");
            require(sim.mailbox->popReply().empty(),"more than one reply");
            // Real ESC mailbox readiness depends on writing its final byte.
            EmulatedESC esc;
            SyncManager::Register sm{};
            sm.start_address=0x1400;sm.length=128;sm.control=0x22;sm.activate=1;
            DatagramHeader setup{};setup.command=Command::BWR;
            setup.address=static_cast<uint32_t>(reg::SYNC_MANAGER)<<16;
            setup.len=sizeof(sm);uint16_t wkc=0;
            esc.processDatagram(&setup,&sm,&wkc);
            require(wkc==1,"SM setup failed");
            uint16_t state=1;
            setup.address=static_cast<uint32_t>(reg::AL_CONTROL)<<16;setup.len=2;
            esc.processDatagram(&setup,&state,&wkc);
            state=2;esc.processDatagram(&setup,&state,&wkc);
            esc.write(0x1400,response.data(),response.size());
            esc.read(reg::SYNC_MANAGER,&sm,sizeof(sm));
            require(sm.status & SM_STATUS_MAILBOX,"response did not publish ESC mailbox");

            return response;
        };
        auto aborted=[&](uint16_t index,uint8_t sub,uint8_t command,uint32_t value,uint32_t code) {
            auto r=exchange(index,sub,command,value);
            uint32_t actual=0;for(int i=0;i<4;++i)actual|=uint32_t(r[12+i])<<(8*i);
            require(r[8]==0x80,"Abort command must be exactly 0x80");
            require(reinterpret_cast<CoE::Header*>(r.data()+6)->service==CoE::Service::SDO_REQUEST,"Abort CoE service");
            require(reinterpret_cast<mailbox::Header*>(r.data())->len==10,"Abort length");
            require(actual==code,"wrong abort code");
        };
        require(exchange(0x2000,1,0x2f,0)[8]==0x60,"restart clear failed");
        aborted(0x2000,1,0x2f,1,0x06010000);
        require(exchange(0x2000,1,0x40)[12]==0,"rejected write mutated OD");
        aborted(0x6041,0,0x2b,0,0x06010002);
        aborted(0xffff,0,0x23,0,0x06020000); // upstream Abort also normalized
        aborted(0x2000,9,0x40,0,0x06090011);
        aborted(0x2000,1,0x2b,0,0x06070010);
        aborted(0x6060,0,0x2f,8,0x06010000);
        require(exchange(0x6060,0,0x2f,1)[8]==0x60,"PP mode after Abort failed");
        require(exchange(0x216e,1,0x40)[8]==0x4b,"unit read after Abort failed");
        for(auto key:std::vector<std::pair<uint16_t,uint8_t>>{{0x2194,1},{0x2194,2},{0x2194,3},{0x2194,4},
                {0x607d,1},{0x607d,2},{0x6081,0},{0x6083,0},{0x6084,0},{0x60a4,1},
                {0x607f,0},{0x2183,12},{0x60c5,0},{0x60c6,0}}) {
            auto response=exchange(key.first,key.second,0x40);
            require((response[8]&0xe0)==0x40,"startup OD read failed");
        }
        // PDO cycles on the same IPC stream still reach operation enabled.
        for(uint16_t cw:{0x106,0x107,0x10f}) {
            std::this_thread::sleep_for(std::chrono::milliseconds(8));
            auto v=gateway.request({{"op","read"},{"index",0x6081},{"subindex",0}})["data"].get<std::string>();
            char buf[5];snprintf(buf,sizeof(buf),"%02x%02x",cw&255,cw>>8);
            auto r=gateway.request({{"op","cycle"},{"data",std::string(buf)+"01"+"00000000"+v+"00000000000000000000000000"}});
            require(r.contains("data"),"PDO cycle after SDO Abort failed");
        }
        auto r=exchange(0x6041,0,0x40);
        require(((r[12]|(r[13]<<8))&0x6f)==0x27,"operation enabled after Abort failed");
        std::cout<<"SDO Abort wire format, recovery, unchanged OD and PDO continuation passed\n";
        return 0;
    }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}
}
