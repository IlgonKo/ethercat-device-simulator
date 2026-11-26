#include <algorithm>
#include <csignal>
#include <cstring>
#include <fstream>
#include <memory>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <nlohmann/json.hpp>
#include "kickcat/EmulatedNetwork.h"
#include "kickcat/Frame.h"
#include "kickcat/helpers.h"
#include "kickcat/simulation/SimulatedSlave.h"
#include "process_data/dynamic_mapping.h"
#include "process_data/mapping_store.h"
#include "process_data/mapping_hook.h"
#include "process_data/pdo_target.h"
#include "process_data/fixed_io.h"
#include "diagnostics/timing.h"
#include "ipc/async_model_client.h"
#include "ipc/sdo_gateway.h"

using json = nlohmann::json;
using namespace kickcat;
static volatile std::sig_atomic_t running = 1;
static void stop(int) { running = 0; }

static std::string hex(void const* ptr, size_t size) {
    static char const digits[] = "0123456789abcdef";
    auto p = static_cast<uint8_t const*>(ptr);
    std::string result; result.reserve(2*size);
    for (size_t i=0;i<size;++i) { result += digits[p[i]>>4]; result += digits[p[i]&15]; }
    return result;
}
static void decode(std::string const& data, void* ptr, size_t size) {
    if (data.size()!=2*size) throw std::runtime_error("IPC payload length mismatch");
    auto p = static_cast<uint8_t*>(ptr);
    auto digit=[](char c)->uint8_t { if(c>='0'&&c<='9')return c-'0'; if(c>='a'&&c<='f')return c-'a'+10; throw std::runtime_error("Invalid hex"); };
    for(size_t i=0;i<size;++i)p[i]=(digit(data[2*i])<<4)|digit(data[2*i+1]);
}



int main(int argc,char** argv) {
    if(argc!=5 && !(argc==6 && std::string(argv[5])=="--timing")) {std::cerr<<"Usage: cmmt_simulator NIC cmmt.json contract.json model.sock [--timing]\n";return 2;}
    std::signal(SIGINT,stop); std::signal(SIGTERM,stop);
    cmmt::Timing timing(argc==6);
    try {
        AsyncModelClient model(argv[4]);
        std::ifstream input(argv[3]); json expected; input>>expected;
        auto spec=model.request({{"op","describe"}});
        if(spec!=expected)throw std::runtime_error("Fixture/model contract mismatch");
        bool fleet = spec.at("protocol") == 2;
        std::vector<json> contracts;
        std::vector<std::string> paths;
        if(fleet) {
            std::ifstream manifest_file(argv[2]); json manifest; manifest_file>>manifest;
            paths=manifest.at("slaves").get<std::vector<std::string>>();
            for(auto const& device:spec.at("devices")) contracts.push_back(device.at("contract"));
        } else { paths.push_back(argv[2]); contracts.push_back(spec); }
        if(paths.empty() || paths.size()!=contracts.size())throw std::runtime_error("Invalid slave manifest");
        std::vector<std::unique_ptr<sim::SimulatedSlave>> slaves;
        std::vector<std::shared_ptr<cmmt::DynamicMapping>> mappings;
        std::vector<std::shared_ptr<cmmt::MappingStore>> stores;
        std::vector<std::map<cmmt::DynamicMapping::Key,std::string>> feedback(paths.size());
        std::vector<std::shared_ptr<softesc::FixedIO>> fixed_io(paths.size());
        std::shared_future<json> io_pending;
        uint64_t io_request_id=0;
        auto io_next=cmmt::TimingClock::now();
        bool has_io=false;
        std::vector<bool> inactive_confirmed(paths.size(),false);
        std::vector<bool> pending_active(paths.size(),false);
        std::vector<uint64_t> request_ids(paths.size(),0);
        auto session=std::to_string(::getpid());
        std::vector<EmulatedESC*> escs;
        bool host_failed=false;
        std::vector<json> mapping_diagnostics(paths.size());
        auto mappingDiagnostic=[&](size_t i,std::string code,std::string detail) {
            auto now=std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
            auto& d=mapping_diagnostics[i];
            if(code.empty()) {
                if(d.is_null())return;
                d["history"]["resolved_at"]=now;d["action"]="resolved";std::cerr<<d.dump()<<std::endl;d=nullptr;return;
            }
            if(!d.is_null() && d["definition"]["code"]==code && d["detail"]==detail)return;
            d={{"event","diagnostic"},{"action","detected"},{"diagnostic_id","mapping-"+std::to_string(i)+"-"+std::to_string(now)},
               {"definition",{{"code",code},{"level","alarm"},{"title",code},{"description",detail},{"latching",false}}},
               {"source",{{"type","ethercat_slave"},{"index",i}}},
               {"history",{{"occurred_at",now},{"acknowledged_at",nullptr},{"resolved_at",nullptr}}},
               {"detail",detail},{"context",{{"operation_allowed",false}}}};
            std::cerr<<d.dump()<<std::endl;
        };
        std::vector<std::shared_future<json>> pending(paths.size());
        std::vector<cmmt::TimingClock::time_point> pending_since(paths.size());
        timing.axes=paths.size();
        auto request=[&model,&timing,fleet](size_t i,json message) {
            if(fleet)message["slave_index"]=i;
            if(!timing.enabled())return model.request(message);
            auto begin=cmmt::TimingClock::now();
            auto key="ipc_axis_"+std::to_string(i)+"_"+message.at("op").get<std::string>();
            try {
                auto result=model.request(message);
                auto end=cmmt::TimingClock::now();
                timing.add(key,begin,end);
                timing.add("ipc_all",begin,end);
                return result;
            } catch(...) {
                timing.add(key+"_failed",begin,cmmt::TimingClock::now());
                ++timing.ipc_failures;
                throw;
            }
        };
        for(size_t i=0;i<paths.size();++i) {
            slaves.push_back(std::make_unique<sim::SimulatedSlave>(sim::buildSlave(paths[i])));
            auto& sim=*slaves.back();
            auto const& spec=contracts[i];
            escs.push_back(sim.esc.get());

            if(!sim.dictionary)throw std::runtime_error("Missing CoE dictionary");

            for(auto const& e:spec.at("entries")) {
                uint16_t index=e.at("index"); uint8_t sub=e.at("subindex");
                auto [object,entry]=CoE::findObject(*sim.dictionary,index,sub);
                (void)object;
                if(!entry || !entry->data || entry->bitlen!=e.at("bits").get<uint16_t>())
                    throw std::runtime_error("ESI/model entry mismatch");
                cmmt::sdoGateways[sim.mailbox.get()].entries.emplace(index,sub);

            }
            if(spec.at("profile")=="cpx-ap-i-ec") {
                fixed_io[i]=std::make_shared<softesc::FixedIO>(sim,spec);has_io=true;
                mappings.push_back(nullptr);stores.push_back(nullptr);
                continue;
            }
            std::map<cmmt::DynamicMapping::Key,cmmt::DynamicMapping::Capability> capabilities;
            for(auto const& e:spec.at("entries")) {
                capabilities[{e.at("index"),e.at("subindex")}]=
                    {e.at("bits"),e.value("rx",false),e.value("tx",false)};
                if(e.value("tx",false)) feedback[i][{e.at("index"),e.at("subindex")}]=e.at("initial");
            }
            auto mapping=std::make_shared<cmmt::DynamicMapping>(capabilities);
            mappings.push_back(mapping);
            auto id=fleet?expected.at("devices").at(i).at("device").at("id").get<std::string>():"axis-0";
            auto root=std::getenv("DEVICE_SIMULATOR_STATE_DIR");
            auto store=std::make_shared<cmmt::MappingStore>(root?root:"state",id,
                json{{"id",id},{"profile",spec.at("profile")},{"vendor",spec.at("vendor")},{"product",spec.at("product")}});
            stores.push_back(store);
            try {store->load(*mapping);}
            catch(cmmt::MappingError const& e){mappingDiagnostic(i,"PDO_MAPPING_RESTORE_INVALID",e.what());}
            auto& gateway=cmmt::sdoGateways[sim.mailbox.get()];
            for(auto& object:*sim.dictionary) {
                if(object.index!=0x1600 && object.index!=0x1a00 && object.index!=0x1c12 && object.index!=0x1c13)continue;
                for(auto& entry:object.entries) {
                    entry.access=(entry.access & ~CoE::Access::WRITE) | CoE::Access::WRITE_PREOP;
                    gateway.entries.emplace(object.index,entry.subindex);
                    uint32_t value=mapping->read(object.index,entry.subindex);
                    std::memcpy(entry.data,&value,(entry.bitlen+7)/8);
                }
            }
            gateway.submit=[&model,&slaves,&host_failed,&feedback,mapping,fleet,i](json message){
                auto index=message.at("index").get<uint16_t>();auto sub=message.at("subindex").get<uint8_t>();
                if(index==0x1600 || index==0x1a00 || index==0x1c12 || index==0x1c13) {
                    std::promise<json> result;
                    try {
                        if(message.at("op")=="write") {
                            auto data=message.at("data").get<std::string>();uint32_t v=0;decode(data,&v,data.size()/2);
                            mapping->write(index,sub,v,slaves[i]->slave->state()==State::PRE_OP);
                            result.set_value(json::object());
                        } else {auto v=mapping->read(index,sub);result.set_value({{"data",hex(&v,sub==0?1:(index==0x1600 || index==0x1a00?4:2))}});}
                    } catch(cmmt::MappingError const& e){result.set_value({{"error",{{"code",e.code},{"message",e.what()}}}});}
                    return result.get_future().share();
                }
                if(message.at("op")=="read" && index==0x6041 && sub==0 && host_failed) {
                    std::promise<json> result; result.set_value({{"data",feedback[i].at({0x6041,0})}});
                    return result.get_future().share();
                }
                if(fleet)message["slave_index"]=i;
                return model.submit(std::move(message));
            };
            cmmt::mappingHooks[sim.pdo.get()]=[&,i,mapping,store]() {
                bool saving=false;
                try {
                    // Completion of inactive OD exchange is the ordering barrier.
                    if(host_failed || !inactive_confirmed[i] || pending[i].valid())
                        return StatusCode::UNSPECIFIED_ERROR;
                    auto ready=mapping->prepare();
                    auto& current=*slaves[i];
                    auto [rxIndex,rxSm]=current.esc->findSm(SM_CONTROL_MODE_BUFFERED|SM_CONTROL_DIRECTION_WRITE);
                    auto [txIndex,txSm]=current.esc->findSm(SM_CONTROL_MODE_BUFFERED|SM_CONTROL_DIRECTION_READ);
                    (void)rxIndex;(void)txIndex;
                    if(rxSm.length!=cmmt::DynamicMapping::bytes(ready.rx))return StatusCode::INVALID_OUTPUT_MAPPING;
                    if(txSm.length!=cmmt::DynamicMapping::bytes(ready.tx))return StatusCode::INVALID_INPUT_MAPPING;
                    auto status=current.pdo->isConfigOk();if(status!=StatusCode::ECAT_NO_ERROR)return status;
                    saving=true;store->save(ready);
                    mapping->activate(std::move(ready));
                    mappingDiagnostic(i,"","");
                    return StatusCode::ECAT_NO_ERROR;
                }catch(std::exception const& e){
                    mappingDiagnostic(i,saving?"PDO_MAPPING_SAVE_FAILED":"PDO_MAPPING_INVALID",e.what());
                    return StatusCode::INVALID_OUTPUT_MAPPING;
                }
            };
        }
        if(has_io && (std::string(argv[1])=="--self-test" || std::string(argv[1])=="--motion-self-test" || std::string(argv[1]).rfind("--ipc-self-test-",0)==0))
            throw std::runtime_error("Axis-only self-test: use test_remote_io for CPX profiles");
        if(std::string(argv[1])=="--self-test" || std::string(argv[1])=="--motion-self-test") {
            auto require=[](bool ok,char const* text){if(!ok)throw std::runtime_error(text);};
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];auto mapping=mappings[i];
                if(std::string(argv[1])=="--motion-self-test" && mapping->active()) {
                    auto const& restored=mapping->configuration().tx;
                    require(restored.size()==3 && restored[0].word()==8*(i+1) &&
                            restored[1].word()==0x60410010 && restored[2].word()==0x60640020,
                            "Per-axis mapping did not restore independently");
                }

                if(!mapping_diagnostics[i].is_null()) {
                    require(!mapping->active() && mapping->read(0x1c12,0)==0 && mapping->read(0x1c13,0)==0,
                            "Invalid restored mapping was partially applied");
                }

                auto exchange=[&](bool active,json values) {
                    json reads=json::array();
                    for(auto const& e:contracts[i].at("entries"))if(e.value("tx",false))reads.push_back({{"index",e.at("index")},{"subindex",e.at("subindex")}});
                    return request(i,{{"op","exchange"},{"active",active},{"values",values},{"reads",reads},
                                      {"session",session},{"request_id",++request_ids[i]}});
                };
                exchange(false,json::array());inactive_confirmed[i]=true;
                auto setSm=[&](uint16_t index,uint16_t address,uint16_t length,uint8_t control) {
                    SyncManager::Register sm{};sm.start_address=address;sm.length=length;sm.control=control;sm.activate=1;
                    DatagramHeader d{};d.command=Command::BWR;d.address=uint32_t(reg::SYNC_MANAGER+index*sizeof(sm))<<16;d.len=sizeof(sm);
                    uint16_t wkc=0;sim.esc->processDatagram(&d,&sm,&wkc);require(wkc==1,"SM configuration failed");
                };
                setSm(0,0x1000,128,0x26);setSm(1,0x1400,128,0x22);
                setSm(2,0x1800,3,0x64);setSm(3,0x1c00,7,0x20);
                sim.slave->start();
                uint16_t requested=State::PRE_OP;
                DatagramHeader al{};al.command=Command::BWR;al.address=uint32_t(reg::AL_CONTROL)<<16;al.len=2;
                uint16_t count=0;sim.esc->processDatagram(&al,&requested,&count);sim.slave->routine();
                require(sim.slave->state()==State::PRE_OP,"Cannot enter PRE-OP in self test");
                auto sdo=[&](uint16_t index,uint8_t sub,uint8_t command,uint32_t value) {
                    std::vector<uint8_t> raw(128,0);
                    auto h=reinterpret_cast<mailbox::Header*>(raw.data());h->len=10;h->type=mailbox::Type::CoE;h->count=1;
                    reinterpret_cast<CoE::Header*>(raw.data()+6)->service=CoE::Service::SDO_REQUEST;
                    raw[8]=command;raw[9]=index&255;raw[10]=index>>8;raw[11]=sub;
                    for(int n=0;n<4;++n)raw[12+n]=value>>(8*n);
                    auto reply=sim.mailbox->processRequest(std::move(raw));
                    for(int retry=0;reply.empty() && retry<100;++retry) {sim.mailbox->process();reply=sim.mailbox->popReply();}
                    require(reply.size()==128,"Missing SDO reply");return reply;
                };
                auto w=[&](uint16_t index,uint8_t sub,uint32_t value,bool) {
                    uint8_t command=sub==0?0x2f:(index==0x1600 || index==0x1a00?0x23:0x2b);
                    require(sdo(index,sub,command,value)[8]==0x60,"Mapping SDO rejected");
                };
                require(sdo(0x1c12,0,0x50,0)[8]==0x80,"Complete Access read not rejected");
                require(sdo(0x1c12,0,0x3f,0)[8]==0x80,"Complete Access write not rejected");
                // Different order, optional fields omitted, padding included.
                w(0x1c12,0,0,true);w(0x1600,0,0,true);
                require(sdo(0x1600,1,0x23,0x60400008)[8]==0x80,"Invalid bit length not rejected");
                w(0x1600,1,8,true);w(0x1600,2,0x60400010,true);
                w(0x1600,0,2,true);w(0x1c12,1,0x1600,true);w(0x1c12,0,1,true);
                w(0x1c13,0,0,true);w(0x1a00,0,0,true);
                w(0x1a00,1,0x60640020,true);w(0x1a00,2,0x60410010,true);
                w(0x1a00,3,8,true);w(0x1a00,0,3,true);
                w(0x1c13,1,0x1a00,true);w(0x1c13,0,1,true);
                // Exercise the actual ESM transition, not only prepare() rejection.
                auto transition=[&](uint16_t state) {
                    requested=state;sim.esc->processDatagram(&al,&requested,&count);sim.slave->routine();
                };
                auto readRegister=[&](uint16_t address) {
                    uint16_t value=0,wkc=0;DatagramHeader d{};
                    d.command=Command::BRD;d.address=uint32_t(address)<<16;d.len=2;
                    sim.esc->processDatagram(&d,&value,&wkc);
                    require(wkc==1,"AL register read failed");return value;
                };
                auto readCandidate=[&](uint16_t index,uint8_t sub) {
                    auto reply=sdo(index,sub,0x40,0);
                    require(reply[8]!=0x80,"Candidate upload failed");
                    uint32_t value=0;std::memcpy(&value,reply.data()+12,sub?4:1);return value;
                };
                auto layoutWords=[](cmmt::DynamicMapping::Configuration const& c) {
                    json result={{"rx",json::array()},{"tx",json::array()}};
                    for(auto const& e:c.rx)result["rx"].push_back(e.word());
                    for(auto const& e:c.tx)result["tx"].push_back(e.word());
                    return result;
                };
                auto persisted=[&]() {
                    json result=json::object();
                    auto root=std::getenv("DEVICE_SIMULATOR_STATE_DIR");
                    for(auto const& entry:std::filesystem::directory_iterator(
                            std::filesystem::path(root?root:"state")/"pdo-mappings")) {
                        if(entry.path().extension()!=".json")continue;
                        std::ifstream f(entry.path());result[entry.path().filename().string()]=
                            std::string(std::istreambuf_iterator<char>(f),{});
                    }
                    return result;
                };
                transition(State::SAFE_OP);
                require(readRegister(reg::AL_STATUS)==State::SAFE_OP,"Baseline SAFE-OP failed");
                transition(State::PRE_OP);
                for(int failure=0;failure<4;++failure) {
                    auto saved=persisted();auto active=layoutWords(mapping->configuration());
                    uint16_t assign=(failure==1 || failure==3)?0x1c13:0x1c12;
                    uint16_t object=assign==0x1c12?0x1600:0x1a00;
                    w(assign,0,0,true);
                    if(failure<2) {
                        w(object,0,0,true);w(object,2,16,true); // same size padding replaces required OD
                        w(object,0,object==0x1600?2:3,true);w(assign,0,1,true);
                    }
                    transition(State::SAFE_OP);
                    require(readRegister(reg::AL_STATUS)==(State::PRE_OP|State::ERROR_ACK),
                            "Invalid mapping did not stay PRE-OP with AL error");
                    require(readRegister(reg::AL_STATUS_CODE)==StatusCode::INVALID_OUTPUT_MAPPING,
                            "Unexpected mapping AL status code");
                    require(!mapping_diagnostics[i].is_null() &&
                            mapping_diagnostics[i]["definition"]["code"]=="PDO_MAPPING_INVALID",
                            "Missing mapping diagnostic");
                    require(persisted()==saved,"Rejected configuration changed persisted mapping");
                    require(layoutWords(mapping->configuration())==active,"Rejected configuration changed active mapping");
                    require(readCandidate(failure<2?object:assign,failure<2?2:0)==uint32_t(failure<2?16:0),
                            "Candidate readback lost rejected whole configuration");
                    require(exchange(false,json::array()).at("values").is_array(),"Model did not survive rejection");
                    // Repeating SAFE-OP without AL acknowledgement must remain blocked.
                    transition(State::SAFE_OP);
                    require(readRegister(reg::AL_STATUS)==(State::PRE_OP|State::ERROR_ACK),"AL error cleared without acknowledgement");
                    transition(State::PRE_OP|State::ERROR_ACK);
                    require(readRegister(reg::AL_STATUS)==State::PRE_OP,"PRE-OP error acknowledgement failed");
                    if(failure<2) {
                        w(assign,0,0,true);w(object,0,0,true);
                        w(object,2,object==0x1600?0x60400010:0x60410010,true);
                        w(object,0,object==0x1600?2:3,true);
                    }
                    w(assign,0,1,true);
                    transition(State::SAFE_OP);
                    require(readRegister(reg::AL_STATUS)==State::SAFE_OP && readRegister(reg::AL_STATUS_CODE)==0,
                            "Corrected mapping could not enter SAFE-OP");
                    require(mapping_diagnostics[i].is_null(),"Corrected mapping diagnostic not resolved");
                    require(readCandidate(assign,0)==1,"Corrected assignment readback failed");
                    transition(State::PRE_OP);
                    std::cout<<"MAPPING_REJECTION_RECOVERY axis="<<i<<" case="<<failure<<" passed"<<std::endl;
                }
                // Force a real open() failure only in this isolated self-test store.
                auto id=fleet?expected.at("devices").at(i).at("device").at("id").get<std::string>():"axis-0";
                auto root=std::getenv("DEVICE_SIMULATOR_STATE_DIR");
                auto blocked=std::filesystem::path(root?root:"state")/"pdo-mappings"/(hex(id.data(),id.size())+".json.tmp");
                auto savedBeforeFailure=persisted();
                auto activeBeforeFailure=layoutWords(mapping->configuration());
                w(0x1c12,0,0,true);w(0x1600,0,0,true);w(0x1600,1,16,true);
                w(0x1600,0,2,true);w(0x1c12,0,1,true);setSm(2,0x1800,4,0x64);
                require(std::filesystem::create_directory(blocked),"Cannot install isolated storage failure");
                transition(State::SAFE_OP);
                require(readRegister(reg::AL_STATUS)==(State::PRE_OP|State::ERROR_ACK),"Save failure allowed SAFE-OP");
                require(mapping_diagnostics[i]["definition"]["code"]=="PDO_MAPPING_SAVE_FAILED","Missing storage diagnostic");
                require(persisted()==savedBeforeFailure && layoutWords(mapping->configuration())==activeBeforeFailure,
                        "Storage failure changed durable or active mapping");
                require(readCandidate(0x1600,1)==16,"Save failure lost candidate");
                require(exchange(false,json::array()).at("values").is_array(),"Model failed after storage error");
                std::filesystem::remove(blocked);
                transition(State::PRE_OP|State::ERROR_ACK);transition(State::SAFE_OP);
                require(readRegister(reg::AL_STATUS)==State::SAFE_OP && mapping_diagnostics[i].is_null(),
                        "Storage correction did not recover");
                require(cmmt::DynamicMapping::bytes(mapping->configuration().rx)==4,"New mapping not activated after retry");
                transition(State::PRE_OP);
                w(0x1c12,0,0,true);w(0x1600,0,0,true);w(0x1600,1,8,true);
                w(0x1600,0,2,true);w(0x1c12,0,1,true);setSm(2,0x1800,3,0x64);
                std::cout<<"MAPPING_STORAGE_RECOVERY axis="<<i<<" passed"<<std::endl;
                require(sim.pdo->configure()==0,"PDO configure failed");
                auto rc=sim.pdo->configureMapping(*sim.dictionary);
                if(rc!=StatusCode::ECAT_NO_ERROR)throw std::runtime_error("Dynamic configure hook failed: "+std::to_string(rc));
                require(cmmt::DynamicMapping::bytes(mapping->configuration().rx)==3,"Wrong Rx length");
                require(cmmt::DynamicMapping::bytes(mapping->configuration().tx)==7,"Wrong Tx length");
                requested=State::SAFE_OP;sim.esc->processDatagram(&al,&requested,&count);sim.slave->routine();
                require(sim.slave->state()==State::SAFE_OP,"SAFE-OP transition failed");
                require(sdo(0x1c12,0,0x2f,0)[8]==0x80,"SAFE-OP mapping write not rejected");
                require(mapping->read(0x1c12,0)==1,"Rejected mapping write changed candidate");
                require(sdo(0x1c00,0,0x50,0)[8]==0x80,"Communication CA read not rejected");
                auto before=request(i,{{"op","read"},{"index",0x6081},{"subindex",0}}).at("data");
                for(uint16_t cw:{6,7,15}) {
                    auto response=exchange(true,json::array({{{"index",0x6040},{"subindex",0},{"data",hex(&cw,2)}}}));
                    require(response.at("values").is_array(),"Missing OD feedback");
                }
                require(request(i,{{"op","read"},{"index",0x6081},{"subindex",0}}).at("data")==before,"Omitted velocity changed");
                exchange(false,json::array());
                if(std::string(argv[1])=="--motion-self-test") {
                    auto readValue=[&](size_t axis,uint16_t index) {
                        auto data=request(axis,{{"op","read"},{"index",index},{"subindex",0}}).at("data").get<std::string>();
                        int32_t value=0;decode(data,&value,data.size()/2);return value;
                    };
                    auto otherSnapshot=[&]() {
                        json snapshot=json::object();
                        for(size_t j=0;j<slaves.size();++j)if(j!=i) {
                            json od=json::object();for(uint16_t index:{0x607a,0x6081,0x6064,0x6041})od[std::to_string(index)]=readValue(j,index);
                            snapshot[std::to_string(j)]={{"layout",layoutWords(mappings[j]->configuration())},{"od",od},
                                {"state",slaves[j]->slave->state()}};
                        }
                        auto files=persisted();
                        auto id=expected.at("devices").at(i).at("device").at("id").get<std::string>();
                        files.erase(hex(id.data(),id.size())+".json");snapshot["files"]=files;return snapshot;
                    };
                    auto others=otherSnapshot();
                    auto writeValue=[&](uint16_t index,int32_t value,size_t size) {
                        auto result=request(i,{{"op","write"},{"index",index},{"subindex",0},{"data",hex(&value,size)}});
                        require(!result.contains("error"),"Motion setup SDO rejected");
                    };
                    auto cycle=[&](uint16_t cw) {
                        std::this_thread::sleep_for(std::chrono::milliseconds(2));
                        exchange(true,json::array({{{"index",0x6040},{"subindex",0},{"data",hex(&cw,2)}}}));
                        require(!(readValue(i,0x6041)&8),"Unexpected drive Fault in PP test");
                        return readValue(i,0x6064);
                    };
                    sim.slave->validateOutputData();transition(State::OPERATIONAL);
                    require(sim.slave->state()==State::OPERATIONAL,"Motion test OP transition failed");
                    bool internal=expected.at("devices").at(i).at("device").at("model").at("type")=="f_kr_cmmt";
                    if(internal) {
                        writeValue(0x6060,6,1);for(uint16_t cw:{6,7,15,31})cycle(cw);
                        for(int n=0;n<100 && !(readValue(i,0x6041)&0x8000);++n)cycle(31);
                        require(readValue(i,0x6041)&0x8000,"Homing did not reference F-KR");
                        cycle(15);
                    }
                    writeValue(0x6060,1,1);writeValue(0x6081,1,4);
                    for(uint16_t cw:{6,7,15})cycle(cw);
                    writeValue(0x607a,10000,4);cycle(0x3f);
                    for(int n=0;n<20;++n)cycle(15);
                    auto moving=readValue(i,0x6064);
                    require(moving>0 && moving<10000,"PP did not begin an unfinished move");
                    writeValue(0x607a,-10000,4);
                    for(int n=0;n<20;++n)cycle(15);
                    require(readValue(i,0x6064)>moving && readValue(i,0x6064)<10000,"SDO target redirected active move");
                    require(readValue(i,0x607a)==-10000,"SDO target not retained");
                    cycle(0x3f); // leave start high across the actual remapping boundary
                    transition(State::PRE_OP);exchange(false,json::array());inactive_confirmed[i]=true;
                    auto stopped=readValue(i,0x6064);
                    w(0x1c13,0,0,true);w(0x1a00,0,0,true);
                    w(0x1a00,1,uint32_t(8*(i+1)),true);w(0x1a00,2,16,true);w(0x1a00,3,0x60640020,true);
                    w(0x1a00,0,3,true);w(0x1c13,0,1,true);setSm(3,0x1c00,uint16_t(i+7),0x20);
                    transition(State::SAFE_OP);
                    require(readRegister(reg::AL_STATUS)==(State::PRE_OP|State::ERROR_ACK),"Missing SW remap unexpectedly succeeded");
                    require(otherSnapshot()==others,"Failed remap changed another axis");
                    transition(State::PRE_OP|State::ERROR_ACK);
                    w(0x1c13,0,0,true);w(0x1a00,0,0,true);w(0x1a00,2,0x60410010,true);
                    w(0x1a00,0,3,true);w(0x1c13,0,1,true);
                    transition(State::SAFE_OP);require(sim.slave->state()==State::SAFE_OP,"New per-axis mapping failed");
                    sim.slave->validateOutputData();transition(State::OPERATIONAL);
                    require(sim.slave->state()==State::OPERATIONAL,"Remapped OP failed");
                    for(uint16_t cw:{0x16,0x17,0x3f})require(cycle(cw)==stopped,"Held start moved on re-enable");
                    for(int n=0;n<20;++n)require(cycle(0x3f)==stopped,"Held start resumed motion");
                    cycle(15);cycle(0x3f);
                    for(int n=0;n<30;++n)cycle(15);
                    require(readValue(i,0x6064)<stopped,"Fresh start did not apply new target");
                    require(otherSnapshot()==others,"Successful remap/move changed another axis");
                    exchange(false,json::array());transition(State::PRE_OP);
                    std::cout<<"PP_REMAP_ISOLATION axis="<<i<<" model="<<(internal?"f_kr_cmmt":"copley")
                        <<" tx_bytes="<<cmmt::DynamicMapping::bytes(mapping->configuration().tx)<<" passed"<<std::endl;
                }
                std::cout<<"DYNAMIC_MAPPING_SELF_TEST axis="<<i<<" passed"<<std::endl;
            }
            return 0;
        }
        if(std::string(argv[1])=="--validate") {
            if(timing.enabled()) {
                for(size_t i=0;i<slaves.size();++i)if(!fixed_io[i])request(i,{{"op","idle"}});
                timing.flush("validation");
            }
            std::cout<<"Fixture and model validated: "<<slaves.size()<<" slaves"<<std::endl;
            return 0;
        }
        EmulatedNetwork network(escs);
        for(size_t i=0;i<slaves.size();++i) {
            auto& sim=*slaves[i];
            sim.slave->start();
            std::fill(sim.input.begin(),sim.input.end(),0);
        }
        std::cout<<"CMMT_READY slaves="<<slaves.size()<<std::endl;
        auto previous_rx=cmmt::TimingClock::time_point{};
        auto fail_host=[&](std::string const& cause) {
            if(host_failed)return;
            host_failed=true;
            auto code=cause.find("TIMEOUT")!=std::string::npos?"MODEL_RESPONSE_TIMEOUT":"MODEL_HOST_DISCONNECTED";
            auto now=std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
            std::cerr<<json({{"event","diagnostic"},{"action","detected"},
                {"diagnostic_id","host-"+std::to_string(now)},
                {"definition",{{"code",code},{"level","fault"},{"title",code},{"description","Model Host unavailable; manual Docker restart required"},{"latching",true}}},
                {"source",{{"type","model_host"},{"index",0}}},
                {"history",{{"occurred_at",now},{"acknowledged_at",nullptr},{"resolved_at",nullptr}}},
                {"detail",cause},{"context",{{"feedback_valid",false},{"restart_required",true}}}}).dump()<<std::endl;
        };
        auto pump=[&]() {
            if(!model.failure().empty())fail_host(model.failure());
            if(io_pending.valid() && io_pending.wait_for(std::chrono::seconds(0))==std::future_status::ready) {
                try {
                    auto response=io_pending.get();
                    if(!host_failed) {
                        if(response.at("host_failed").get<bool>())throw std::runtime_error("MODEL_RESPONSE_TIMEOUT");
                        if(response.at("session")!=session || response.at("request_id")!=io_request_id)throw std::runtime_error("IO snapshot response identity mismatch");
                        std::set<size_t> seen;
                        std::vector<std::pair<size_t,softesc::FixedIO::Values>> prepared;
                        for(auto const& station:response.at("stations")) {
                            auto i=station.at("slave_index").get<size_t>();
                            if(i>=fixed_io.size() || !fixed_io[i] || !seen.insert(i).second)throw std::runtime_error("Invalid IO station response");
                            prepared.emplace_back(i,fixed_io[i]->prepareFeedback(station.at("values")));
                        }
                        if(seen.size()!=size_t(std::count_if(fixed_io.begin(),fixed_io.end(),[](auto const& p){return bool(p);})))throw std::runtime_error("Incomplete IO station response");
                        for(auto const& [i,values]:prepared)fixed_io[i]->commitFeedback(values);
                    }
                }catch(std::exception const& e){fail_host(e.what());}
                io_pending={};
            }
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];
                if(fixed_io[i]) {
                    fixed_io[i]->sample(false);fixed_io[i]->publish();
                    if(sim.slave->state()==State::OPERATIONAL || sim.slave->state()==State::SAFE_OP)sim.pdo->updateInput();
                    continue;
                }
                if(pending[i].valid() && pending[i].wait_for(std::chrono::seconds(0))==std::future_status::ready) {
                    try {
                        auto response=pending[i].get();
                        if(!host_failed) {
                            if(response.at("session")!=session || response.at("request_id")!=request_ids[i])
                                throw std::runtime_error("OD response identity mismatch");
                            auto validated=feedback[i];std::set<cmmt::DynamicMapping::Key> seen;
                            for(auto const& e:response.at("values")) {
                                cmmt::DynamicMapping::Key key{e.at("index"),e.at("subindex")};
                                if(!validated.count(key) || !seen.insert(key).second)throw std::runtime_error("Invalid OD feedback address");
                                auto data=e.at("data").get<std::string>();
                                std::vector<uint8_t> check(validated.at(key).size()/2);decode(data,check.data(),check.size());
                                validated[key]=data;
                            }
                            if(seen.size()!=validated.size())throw std::runtime_error("Incomplete OD feedback");
                            feedback[i]=std::move(validated);
                            if(!pending_active[i])inactive_confirmed[i]=true;
                            timing.add("ipc_async_axis_"+std::to_string(i),pending_since[i],cmmt::TimingClock::now());
                        }
                    } catch(std::exception const& e) {fail_host(e.what());}
                    pending[i]={};
                }
                if(host_failed) {
                    uint16_t sw=0;decode(feedback[i].at({0x6041,0}),&sw,2);
                    sw=(sw & ~0x106f)|8;feedback[i][{0x6041,0}]=hex(&sw,2);
                }
                if(mappings[i]->active()) {
                    size_t offset=0;
                    for(auto const& e:mappings[i]->configuration().tx) {
                        if(e.index)decode(feedback[i].at({e.index,e.subindex}),sim.input.data()+offset,e.bits/8);
                        else std::fill_n(sim.input.data()+offset,e.bits/8,0);
                        offset+=e.bits/8;
                    }
                }
                if(sim.slave->state()==State::OPERATIONAL || sim.slave->state()==State::SAFE_OP)
                    sim.pdo->updateInput();
            }
            auto now=cmmt::TimingClock::now();
            if(has_io && !host_failed && !io_pending.valid() && now>=io_next) {
                json snapshots=json::array();
                for(size_t i=0;i<fixed_io.size();++i)if(fixed_io[i])snapshots.push_back(fixed_io[i]->snapshot(i));
                io_pending=model.submit({{"op","io_exchange"},{"session",session},{"request_id",++io_request_id},{"stations",snapshots}});
                io_next=now+std::chrono::milliseconds(8);
            }
        };
        // Shared by the physical frame loop and NIC-free transition tests.
        auto runRoutine=[&](size_t i) {
            auto& sim=*slaves[i];
                uint16_t control=0;sim.esc->read(reg::AL_CONTROL,&control,sizeof(control));
                bool wait_for_inactive=!fixed_io[i] && sim.slave->state()==State::PRE_OP && (control & 0x0f)==State::SAFE_OP
                    && !host_failed && (!inactive_confirmed[i] || pending[i].valid());
                if(!wait_for_inactive)sim.slave->routine();
        };
        if(std::string(argv[1]).rfind("--ipc-self-test-",0)==0) {
            auto scenario=std::string(argv[1]).substr(16);
            auto require=[](bool ok,char const* text){if(!ok)throw std::runtime_error(text);};
            auto& sim=*slaves[0];auto mapping=mappings[0];
            auto regWrite=[&](uint16_t address,void* data,uint16_t len) {
                DatagramHeader d{};d.command=Command::BWR;d.address=uint32_t(address)<<16;d.len=len;
                uint16_t wkc=0;sim.esc->processDatagram(&d,data,&wkc);require(wkc==1,"Register write failed");
            };
            auto setSm=[&](int index,int address,int length,int control) {
                SyncManager::Register sm{};sm.start_address=address;sm.length=length;sm.control=control;sm.activate=1;
                regWrite(reg::SYNC_MANAGER+index*sizeof(sm),&sm,sizeof(sm));
            };
            auto setState=[&](uint16_t state){regWrite(reg::AL_CONTROL,&state,2);};
            setSm(0,0x1000,128,0x26);setSm(1,0x1400,128,0x22);
            setSm(2,0x1800,2,0x64);setSm(3,0x1c00,2,0x20);
            setState(State::PRE_OP);runRoutine(0);
            require(sim.slave->state()==State::PRE_OP,"PRE-OP setup failed");
            for(auto pair:{std::pair{0x1600,0x60400010u},std::pair{0x1a00,0x60410010u}}) {
                mapping->write(pair.first,1,pair.second,true);mapping->write(pair.first,0,1,true);
                int a=pair.first==0x1600?0x1c12:0x1c13;
                mapping->write(a,1,pair.first,true);mapping->write(a,0,1,true);
            }
            inactive_confirmed[0]=true;setState(State::SAFE_OP);runRoutine(0);
            require(sim.slave->state()==State::SAFE_OP,"Baseline mapping activation failed");
            setState(State::PRE_OP);runRoutine(0);
            mapping->write(0x1c13,0,0,true);mapping->write(0x1a00,0,0,true);
            mapping->write(0x1a00,1,8,true);mapping->write(0x1a00,2,0x60410010,true);
            mapping->write(0x1a00,3,0x60640020,true);mapping->write(0x1a00,0,3,true);
            mapping->write(0x1c13,0,1,true);setSm(3,0x1c00,7,0x20);
            auto durableSnapshot=[&]() {
                json result=json::object();auto root=std::getenv("DEVICE_SIMULATOR_STATE_DIR");
                for(auto const& f:std::filesystem::directory_iterator(std::filesystem::path(root)/"pdo-mappings"))
                    if(f.path().extension()==".json") {
                        std::ifstream in(f.path());result[f.path().filename().string()]=std::string(std::istreambuf_iterator<char>(in),{});
                    }
                return result;
            };
            auto oldStore=durableSnapshot();auto oldFeedback=feedback[0];
            auto submitExchange=[&](bool active) {
                json reads=json::array();
                for(auto const& e:contracts[0].at("entries"))if(e.value("tx",false))reads.push_back({{"index",e.at("index")},{"subindex",e.at("subindex")}});
                json msg={{"op","exchange"},{"active",active},{"values",json::array()},
                    {"reads",reads},{"session",session},{"request_id",++request_ids[0]}};
                if(fleet)msg["slave_index"]=0;
                pending_active[0]=active;pending_since[0]=cmmt::TimingClock::now();pending[0]=model.submit(msg);
            };
            // A previous active exchange is still outstanding when SAFE-OP is requested.
            inactive_confirmed[0]=false;submitExchange(true);setState(State::SAFE_OP);
            auto begin=std::chrono::steady_clock::now();unsigned routed=0,blocked=0;
            bool inactiveSubmitted=false,activeCompleted=false;
            while(std::chrono::steady_clock::now()-begin<std::chrono::milliseconds(350)) {
                pump();
                if(!host_failed && !pending[0].valid() && !inactiveSubmitted) {
                    require(!inactive_confirmed[0],"Active response incorrectly confirmed deactivation");
                    require(cmmt::DynamicMapping::bytes(mapping->configuration().tx)==2,"Old response used new mapping");
                    activeCompleted=true;submitExchange(false);inactiveSubmitted=true;
                }
                bool waiting=!host_failed && (!inactive_confirmed[0] || pending[0].valid());
                runRoutine(0);
                if(waiting) {
                    require(sim.slave->state()==State::PRE_OP,"SAFE-OP entered before inactive completion");
                    require(cmmt::DynamicMapping::bytes(mapping->configuration().tx)==2,"Mapping activated before barrier");
                    require(durableSnapshot()==oldStore,"Mapping persisted before barrier");++blocked;
                }
                Frame frame;uint16_t status=0;frame.addDatagram(0,Command::BRD,uint32_t(reg::AL_STATUS)<<16,&status,2);
                frame.finalize();require(network.route(frame),"Frame routing stopped");frame.resetContext();
                auto [h,d,wkc]=frame.peekDatagram();(void)h;(void)d;
                require(wkc && *wkc==slaves.size(),"ESC response lost during IPC fault");++routed;
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            require(routed>50 && blocked>0,"No transition wait/routing coverage");
            if(scenario=="delay") {
                require(activeCompleted && inactiveSubmitted && inactive_confirmed[0] && !host_failed,"Delayed barrier did not finish");
                require(sim.slave->state()==State::SAFE_OP && cmmt::DynamicMapping::bytes(mapping->configuration().tx)==7,
                        "New mapping not applied after inactive completion");
            }else {
                require(host_failed && sim.slave->state()==State::PRE_OP,"Host failure did not block transition");
                require(cmmt::DynamicMapping::bytes(mapping->configuration().tx)==2 && durableSnapshot()==oldStore,
                        "Host failure changed active/durable mapping");
                require(feedback[0].at({0x6064,0})==oldFeedback.at({0x6064,0}),"Late/stale position applied");
                uint16_t sw=0;decode(feedback[0].at({0x6041,0}),&sw,2);require((sw&0x6f)==8,"Host Fault not reflected in statusword");
                // Master-side reset bits cannot undo the separately latched Host failure.
                uint16_t reset=0x80;std::memcpy(sim.output.data(),&reset,2);
                setState(State::PRE_OP|State::ERROR_ACK);runRoutine(0);setState(State::SAFE_OP);runRoutine(0);pump();
                require(host_failed && sim.slave->state()==State::PRE_OP,"Reset cleared Host fault");
            }
            std::cout<<"IPC_REMAP_TEST scenario="<<scenario<<" frames="<<routed<<" blocked="<<blocked<<" passed"<<std::endl;
            return 0;
        }
        auto [socket,unused]=createSockets(argv[1],"");
        socket->setTimeout(std::chrono::milliseconds(has_io?1:10));
        while(running) {
            timing.due();
            pump();
            Frame frame;
            // readFrame() is a master helper which clears the EtherCAT length.
            // A simulator must preserve that header while routing the original frame.
            auto read_start=cmmt::TimingClock::now();
            auto n=socket->read(frame.data(),ETH_MAX_SIZE);
            auto received=cmmt::TimingClock::now();
            timing.add("socket_read_wait",read_start,received);
            for(size_t i=0;i<slaves.size();++i)if(fixed_io[i])runRoutine(i);
            pump();
            if(n<static_cast<int>(sizeof(EthernetHeader)+sizeof(EthercatHeader)))continue;
            if(frame.ethernet()->type!=ETH_ETHERCAT_TYPE)continue;
            if(frame.header()->len+sizeof(EthernetHeader)+sizeof(EthercatHeader)>static_cast<size_t>(n))continue;
            if(previous_rx!=cmmt::TimingClock::time_point{})timing.add("rx_gap",previous_rx,received);
            previous_rx=received;
            auto route_start=cmmt::TimingClock::now();
            if(!network.route(frame)) {timing.add("route_rejected",route_start,cmmt::TimingClock::now());continue;}
            timing.add("route",route_start,cmmt::TimingClock::now());
            std::vector<bool> pdo(slaves.size(),false);
            frame.resetContext();
            while(true) {
                auto [header,data,wkc]=frame.peekDatagram();
                (void)data;
                if(!header)break;
                // Only acknowledged logical writes advance the model; mailbox frames never do.
                if(wkc && *wkc && (header->command==Command::LRW || header->command==Command::LWR)) {
                    for(size_t i=0;i<slaves.size();++i)
                        pdo[i]=pdo[i] || cmmt::targetsOutput(*slaves[i]->esc,*header,fixed_io[i]?fixed_io[i]->bytes(true):cmmt::DynamicMapping::bytes(mappings[i]->configuration().rx));
                }
            }
            if(socket->write(frame.data(),n)!=n)throw std::runtime_error("EtherCAT frame write failed");
            auto replied=cmmt::TimingClock::now();
            timing.add("rx_to_reply",received,replied);
            size_t cycled=0;
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];
                auto routine_start=cmmt::TimingClock::now();
                runRoutine(i);
                timing.add("slave_routine",routine_start,cmmt::TimingClock::now());
                auto state=sim.slave->state();
                if(state==State::SAFE_OP && pdo[i])sim.slave->validateOutputData();
                if(fixed_io[i]) {fixed_io[i]->sample(pdo[i]);continue;}
                bool active=state==State::OPERATIONAL;
                if(!host_failed && !pending[i].valid() && ((active && pdo[i]) || (!active && !inactive_confirmed[i]))) {
                    json values=json::array(), reads=json::array();
                    if(active) {
                        inactive_confirmed[i]=false;++cycled;size_t offset=0;
                        for(auto const& e:mappings[i]->configuration().rx) {
                            if(e.index)values.push_back({{"index",e.index},{"subindex",e.subindex},{"data",hex(sim.output.data()+offset,e.bits/8)}});
                            offset+=e.bits/8;
                        }
                    }
                    for(auto const& e:contracts[i].at("entries"))if(e.value("tx",false))
                        reads.push_back({{"index",e.at("index")},{"subindex",e.at("subindex")}});
                    json message={{"op","exchange"},{"active",active},{"values",values},{"reads",reads},
                        {"session",session},{"request_id",++request_ids[i]}};
                    if(fleet)message["slave_index"]=i;
                    pending_active[i]=active;
                    pending_since[i]=cmmt::TimingClock::now();
                    pending[i]=model.submit(std::move(message));
                }
            }
            auto finished=cmmt::TimingClock::now();
            timing.add("post_reply",replied,finished);
            timing.add("frame_busy",received,finished);
            if(cycled) {
                timing.add("pdo_frame_busy",received,finished);
                timing.add("pdo_post_reply",replied,finished);
            }
        }
        timing.flush("stop");
        return 0;
    } catch(std::exception const& e) {timing.flush("error");std::cerr<<e.what()<<std::endl;return 1;}
}
