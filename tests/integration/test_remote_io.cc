#include <fstream>
#include <iostream>
#include <memory>
#include <vector>
#include "process_data/fixed_io.h"
#include "ipc/model_client.h"
#include <thread>
#include "kickcat/EmulatedNetwork.h"
#include "kickcat/Frame.h"
using namespace kickcat;
using json=nlohmann::json;
void require(bool ok,char const* message){if(!ok)throw std::runtime_error(message);}
int main(int argc,char** argv) {
 try {
  require(argc==3 || argc==4,"manifest, contract, optional model socket required");json manifest,spec;
  std::ifstream(argv[1])>>manifest;std::ifstream(argv[2])>>spec;
  std::vector<std::unique_ptr<sim::SimulatedSlave>> slaves;
  std::vector<std::unique_ptr<softesc::FixedIO>> ios;std::vector<EmulatedESC*> escs;
  size_t n=0;
  for(auto const& path:manifest.at("slaves")) {
   slaves.push_back(std::make_unique<sim::SimulatedSlave>(sim::buildSlave(path)));
   auto& sim=*slaves.back();auto contract=spec["devices"][n++]["contract"];
   ios.push_back(std::make_unique<softesc::FixedIO>(sim,contract));auto& io=*ios.back();escs.push_back(sim.esc.get());
   std::fill(sim.input.begin(),sim.input.end(),0);std::fill(sim.output.begin(),sim.output.end(),0);
   auto write=[&](uint16_t address,void* data,uint16_t length) {
    DatagramHeader d{};d.command=Command::BWR;d.address=uint32_t(address)<<16;d.len=length;
    uint16_t wkc=0;sim.esc->processDatagram(&d,data,&wkc);require(wkc==1,"Register write failed");
   };
   auto sm=[&](unsigned index,uint16_t address,uint16_t length,uint8_t control) {
    SyncManager::Register r{};r.start_address=address;r.length=length;r.control=control;r.activate=1;
    write(reg::SYNC_MANAGER+index*sizeof(r),&r,sizeof(r));
   };
   auto state=[&](uint16_t requested) {write(reg::AL_CONTROL,&requested,2);sim.slave->routine();};
   sm(0,0x1000,128,0x26);sm(1,0x1400,128,0x22);
   sm(2,0x1800,io.bytes(true),0x64);sm(3,0x1c00,io.bytes(false),0x20);
   auto fmmu=[&](unsigned i,uint32_t logical,uint16_t physical,uint16_t bytes,uint8_t type) {
    fmmu::Register r{};r.logical_address=logical;r.physical_address=physical;r.length=bytes;r.logical_stop_bit=7;r.type=type;r.activate=1;
    write(reg::FMMU+i*sizeof(r),&r,sizeof(r));
   };
   fmmu(0,0x10000+n*0x1000,0x1800,io.bytes(true),2);fmmu(1,0x10200+n*0x1000,0x1c00,io.bytes(false),1);
   sim.slave->start();state(State::PRE_OP);require(sim.slave->state()==State::PRE_OP,"PREOP failed");
   auto sdo=[&](uint16_t index,uint8_t sub,uint8_t command,uint32_t value=0) {
    std::vector<uint8_t> raw(128,0);auto* h=reinterpret_cast<mailbox::Header*>(raw.data());
    h->len=10;h->type=mailbox::Type::CoE;h->count=1;
    reinterpret_cast<CoE::Header*>(raw.data()+6)->service=CoE::Service::SDO_REQUEST;
    raw[8]=command;raw[9]=index&255;raw[10]=index>>8;raw[11]=sub;
    for(int k=0;k<4;++k)raw[12+k]=value>>(8*k);
    auto reply=sim.mailbox->processRequest(std::move(raw));
    for(int retry=0;reply.empty() && retry<100;++retry){sim.mailbox->process();reply=sim.mailbox->popReply();}
    require(reply.size()==128,"Missing/full-mailbox SDO response");return reply;
   };
   auto value=[](auto const& r){uint32_t v=0;for(int k=0;k<4;++k)v|=uint32_t(r[12+k])<<(8*k);return v;};
   auto abort=[&](uint16_t index,uint8_t sub,uint8_t command,uint32_t v,uint32_t expected) {
    auto r=sdo(index,sub,command,v);require(r[8]==0x80,"Abort command invalid");
    require(value(r)==expected,"Abort reason differs");
   };
   require(value(sdo(0x1018,2,0x40))==8086609,"CPX identity read failed");
   for(auto const& e:contract["entries"]) {
    auto r=sdo(e["index"],e["subindex"],0x40);require(r[8]!=0x80,"Supported OD read failed");
    if(e["index"]==0xf030)require(sdo(e["index"],e["subindex"],e["bits"]==8?0x2f:0x23,value(r))[8]==0x60,"F030 same config rejected");
    auto index=e["index"].get<uint16_t>();
    if(index>=0x1600 && index<=0x1c13) {
     auto cmd=e["bits"]==8?0x2f:e["bits"]==16?0x2b:0x23;
     abort(index,e["subindex"],cmd,0,0x06010002);
     abort(index,e["subindex"],cmd,value(r),0x06010002);
     require(value(sdo(index,e["subindex"],0x40))==value(r),"Rejected write changed mapping");
    }
   }
   abort(0xf030,1,0x23,1,0x06090030);abort(0xf030,0,0x2f,0,0x06090030);
   abort(0x1c12,0,0x50,0,0x06010000);abort(0x1c12,0,0x3f,0,0x06010000);
   for(auto index:{0x27f0,0x27f1,0x10f3,0x2000,0x1af0,0x1af1})abort(index,0,0x40,0,0x06020000);
   // Refuse an SM length that truncates the fixed byte image, then recover.
   sm(2,0x1800,io.bytes(true)+1,0x64);state(State::SAFE_OP);
   require(sim.slave->state()==State::PRE_OP,"Wrong SM length entered SAFEOP");
   state(State::PRE_OP|State::ERROR_ACK);sm(2,0x1800,io.bytes(true),0x64);
   state(State::SAFE_OP);require(sim.slave->state()==State::SAFE_OP,"Fixed PDO SAFEOP failed");
   abort(0x1c12,0,0x2f,0,0x06010002);
   sim.slave->validateOutputData();state(State::OPERATIONAL);require(sim.slave->state()==State::OPERATIONAL,"Fixed PDO OP failed");
   abort(0xf030,1,0x23,0x2084,0x08000022);abort(0x1c12,0,0x2f,0,0x06010002);
   // Fill every mapped output including 4 supply bits and padding with a distinct bit pattern.
   for(size_t i=0;i<io.bytes(true);++i)sim.output[i]=uint8_t(0x81+i*17);
   io.sample(true);auto snapshot=io.snapshot(n-1);snapshot=io.snapshot(n-1);
   require(snapshot["active"].get<bool>(),"Fresh OP output invalid");
   size_t bit=0;
   for(auto const& e:contract["rx"]) {
    if(e["index"]!=0) {
     uint32_t expected=0;unsigned bits=e["bits"];
     for(unsigned k=0;k<bits;++k)expected|=uint32_t((sim.output[(bit+k)/8]>>((bit+k)%8))&1)<<k;
     require(value(sdo(e["index"],e["subindex"],0x40))==expected,"Sub-byte OD unpack failed");
    }
    bit+=e["bits"].get<unsigned>();
   }
   json feedback=json::array();
   for(auto const& e:contract["entries"])if(e.value("tx",false))feedback.push_back({{"index",e["index"]},{"subindex",e["subindex"]},{"data",e["bits"]==1?"01":"0080"}});
   io.feedback(feedback);sim.pdo->updateInput();
   std::vector<uint8_t> image(io.bytes(false));
   DatagramHeader read{};read.command=Command::LRD;read.address=0x10200+n*0x1000;read.len=image.size();
   uint16_t readWkc=0;sim.esc->processDatagram(&read,image.data(),&readWkc);require(readWkc==1,"PDO master read failed");
   require(image==std::vector<uint8_t>(sim.input.begin(),sim.input.begin()+image.size()),"PDO publication failed");
   require(value(sdo(0x1001,0,0x40))==0 && value(sdo(0x6102,1,0x40))==0,"Normal CPX error summary differs");
   state(State::PRE_OP);io.sample(false);require(!io.snapshot(n-1)["active"].get<bool>(),"Lost OP remained valid");
   if(argc==4){state(State::SAFE_OP);sim.slave->validateOutputData();state(State::OPERATIONAL);}
  }
  if(argc==4) {
   ModelClient host(argv[3]);require(host.request({{"op","describe"}})==spec,"IO host contract mismatch");
   std::vector<json> snapshots;
   for(int cycle=0;cycle<25;++cycle) {
    json updates=json::array();snapshots.clear();
    for(size_t i=0;i<ios.size();++i){ios[i]->sample(true);snapshots.push_back(ios[i]->snapshot(i));updates.push_back(snapshots.back());}
    auto response=host.request({{"op","io_exchange"},{"session","test"},{"request_id",cycle},{"stations",updates}});
    require(!response.at("host_failed").get<bool>(),"IO scheduler host failed");
    for(auto const& station:response.at("stations"))ios.at(station.at("slave_index"))->feedback(station.at("values"));
    std::this_thread::sleep_for(std::chrono::milliseconds(8));
   }
   for(auto indices:{std::tuple{0,1,1},std::tuple{1,0,2}}) {
    auto [source,target,sub]=indices;std::string expected;
    for(auto const& e:snapshots[source]["values"])if(e["index"]==0x7030 && e["subindex"]==sub)expected=e["data"];
    auto result=ios[target]->sdo({{"op","read"},{"index",0x6030},{"subindex",sub}});
    require(!expected.empty() && result["data"]==expected,"Cross-station OD/IPC/model/PDO result differs");
   }
   std::cout<<"CPX IPC scheduler test passed: two independent test adapters, bidirectional station binding, signed raw values\n";
  }
  EmulatedNetwork network(escs);Frame frame;uint16_t status=0;
  frame.addDatagram(0,Command::BRD,uint32_t(reg::AL_STATUS)<<16,&status,2);frame.finalize();
  require(network.route(frame),"Network route failed");frame.resetContext();auto [h,d,wkc]=frame.peekDatagram();(void)h;(void)d;
  require(wkc && *wkc==slaves.size(),"Multi-station EtherCAT WKC failed");
  std::cout<<"CPX protocol test passed: stations="<<slaves.size()<<" identity/F030/F050/read-only maps/Abort/OP/bit-PDO/WKC\n";
  return 0;
 }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}
}
