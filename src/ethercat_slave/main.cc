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
        if(std::string(argv[1])=="--self-test") {
            auto require=[](bool ok,char const* text){if(!ok)throw std::runtime_error(text);};
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];auto mapping=mappings[i];
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
                std::cout<<"DYNAMIC_MAPPING_SELF_TEST axis="<<i<<" passed"<<std::endl;
            }
            return 0;
        }
        if(std::string(argv[1])=="--validate") {
            if(timing.enabled()) {
                for(size_t i=0;i<slaves.size();++i)request(i,{{"op","idle"}});
                timing.flush("validation");
            }
            std::cout<<"Fixture and model validated: "<<slaves.size()<<" slaves"<<std::endl;
            return 0;
        }
        EmulatedNetwork network(escs);
        auto [socket,unused]=createSockets(argv[1],"");
        socket->setTimeout(std::chrono::milliseconds(10));
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
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];
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
        };
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
                        pdo[i]=pdo[i] || cmmt::targetsOutput(*slaves[i]->esc,*header,cmmt::DynamicMapping::bytes(mappings[i]->configuration().rx));
                }
            }
            if(socket->write(frame.data(),n)!=n)throw std::runtime_error("EtherCAT frame write failed");
            auto replied=cmmt::TimingClock::now();
            timing.add("rx_to_reply",received,replied);
            size_t cycled=0;
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];
                auto routine_start=cmmt::TimingClock::now();
                uint16_t control=0;sim.esc->read(reg::AL_CONTROL,&control,sizeof(control));
                bool wait_for_inactive=sim.slave->state()==State::PRE_OP && (control & 0x0f)==State::SAFE_OP
                    && !host_failed && (!inactive_confirmed[i] || pending[i].valid());
                if(!wait_for_inactive)sim.slave->routine();
                timing.add("slave_routine",routine_start,cmmt::TimingClock::now());
                auto state=sim.slave->state();
                if(state==State::SAFE_OP && pdo[i])sim.slave->validateOutputData();
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
