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
#include "fixed_mapping.h"
#include "pdo_target.h"
#include "timing.h"

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
class ModelClient {
    int fd_ = -1;
public:
    explicit ModelClient(std::string const& path) {
        sockaddr_un address{}; address.sun_family=AF_UNIX;
        if(path.size()>=sizeof(address.sun_path))throw std::runtime_error("Socket path too long");
        std::memcpy(address.sun_path,path.c_str(),path.size()+1);
        fd_=::socket(AF_UNIX,SOCK_STREAM,0);
        if(fd_<0)throw std::runtime_error("Cannot create model socket");
        timeval timeout{1,0};
        if(setsockopt(fd_,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)) ||
           setsockopt(fd_,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout)) ||
           connect(fd_,reinterpret_cast<sockaddr*>(&address),sizeof(address))) {
            close(fd_); fd_=-1; throw std::runtime_error("Cannot connect to model service");
        }
    }
    ~ModelClient(){if(fd_>=0)close(fd_);}
    json request(json const& message) {
        auto data=message.dump()+"\n";
        size_t sent=0;
        while(sent<data.size()) {
            auto n=send(fd_,data.data()+sent,data.size()-sent,MSG_NOSIGNAL);
            if(n<=0)throw std::runtime_error("Model service send failed");
            sent+=n;
        }
        std::string response;
        // Read chunks with MSG_PEEK to consume exactly one newline-framed response.
        while(response.size()<=1024*1024) {
            char buffer[4096]; auto n=recv(fd_,buffer,sizeof(buffer),MSG_PEEK);
            if(n<=0)throw std::runtime_error("Model service closed or timed out");
            auto newline=std::find(buffer,buffer+n,'\n');
            size_t count=newline==buffer+n?static_cast<size_t>(n):static_cast<size_t>(newline-buffer+1);
            auto used=recv(fd_,buffer,count,0);
            if(used<=0)throw std::runtime_error("Model service read failed");
            response.append(buffer,used);
            if(response.back()=='\n')return json::parse(response);
        }
        throw std::runtime_error("Model response too large");
    }
};


int main(int argc,char** argv) {
    if(argc!=5 && !(argc==6 && std::string(argv[5])=="--timing")) {std::cerr<<"Usage: cmmt_simulator NIC cmmt.json contract.json model.sock [--timing]\n";return 2;}
    std::signal(SIGINT,stop); std::signal(SIGTERM,stop);
    cmmt::Timing timing(argc==6);
    try {
        ModelClient model(argv[4]);
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
        std::vector<std::shared_ptr<FixedMapping>> mappings;
        std::vector<EmulatedESC*> escs;
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
                entry->before_access.push_back([&request,i,index,sub](uint16_t access,CoE::Entry* target) {
                    if(access & CoE::Access::READ) {
                        auto r=request(i,{{"op","read"},{"index",index},{"subindex",sub}});
                        decode(r.at("data"),target->data,(target->bitlen+7)/8);
                    }
                });
                entry->after_access.push_back([&request,i,index,sub](uint16_t access,CoE::Entry* target) {
                    if(access & CoE::Access::WRITE)
                        request(i,{{"op","write"},{"index",index},{"subindex",sub},
                                       {"data",hex(target->data,(target->bitlen+7)/8)}});
                });
            }
            std::map<FixedMapping::Key,uint32_t> mapping_values;
            for(auto& object:*sim.dictionary) {
                if(object.index!=0x1600 && object.index!=0x1a00 && object.index!=0x1c12 && object.index!=0x1c13)continue;
                for(auto& entry:object.entries) {
                    uint32_t value=0;
                    if(entry.bitlen>32 || !entry.data)throw std::runtime_error("Invalid PDO configuration entry");
                    std::memcpy(&value,entry.data,(entry.bitlen+7)/8);
                    mapping_values[{object.index,entry.subindex}]=value;
                }
            }
            auto mapping=std::make_shared<FixedMapping>(mapping_values);
            mappings.push_back(mapping);
            for(auto& object:*sim.dictionary) {
                if(object.index!=0x1600 && object.index!=0x1a00 && object.index!=0x1c12 && object.index!=0x1c13)continue;
                for(auto& entry:object.entries) {
                    entry.access=(entry.access & ~CoE::Access::WRITE) | CoE::Access::WRITE_PREOP;
                    uint16_t index=object.index;
                    entry.after_access.push_back([mapping,slave=sim.slave.get(),index](uint16_t access,CoE::Entry* target) {
                        if(!(access & CoE::Access::WRITE))return;
                        uint32_t value=0;
                        std::memcpy(&value,target->data,(target->bitlen+7)/8);
                        mapping->write(index,target->subindex,value,slave->state()==State::PRE_OP);
                    });
                }
            }
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
            decode(request(i,{{"op","idle"}}).at("data"),sim.input.data(),contracts[i].at("tx_size"));
        }
        std::cout<<"CMMT_READY slaves="<<slaves.size()<<std::endl;
        auto previous_rx=cmmt::TimingClock::time_point{};
        while(running) {
            timing.due();
            Frame frame;
            // readFrame() is a master helper which clears the EtherCAT length.
            // A simulator must preserve that header while routing the original frame.
            auto read_start=cmmt::TimingClock::now();
            auto n=socket->read(frame.data(),ETH_MAX_SIZE);
            auto received=cmmt::TimingClock::now();
            timing.add("socket_read_wait",read_start,received);
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
                        pdo[i]=pdo[i] || cmmt::targetsOutput(*slaves[i]->esc,*header,contracts[i].at("rx_size"));
                }
            }
            if(socket->write(frame.data(),n)!=n)throw std::runtime_error("EtherCAT frame write failed");
            auto replied=cmmt::TimingClock::now();
            timing.add("rx_to_reply",received,replied);
            size_t cycled=0;
            for(size_t i=0;i<slaves.size();++i) {
                auto& sim=*slaves[i];
                size_t rx_size=contracts[i].at("rx_size"),tx_size=contracts[i].at("tx_size");
                auto routine_start=cmmt::TimingClock::now();
                sim.slave->routine();
                timing.add("slave_routine",routine_start,cmmt::TimingClock::now());
                auto state=sim.slave->state();
                if((state==State::SAFE_OP || state==State::OPERATIONAL) && !mappings[i]->complete())
                    throw std::runtime_error("PDO configuration was not restored before SAFE-OP");
                if(state==State::SAFE_OP && pdo[i])sim.slave->validateOutputData();
                if(state==State::OPERATIONAL && pdo[i]) {
                    ++cycled;
                    auto r=request(i,{{"op","cycle"},{"data",hex(sim.output.data(),rx_size)}});
                    decode(r.at("data"),sim.input.data(),tx_size);
                    sim.pdo->updateInput();
                } else if(state!=State::OPERATIONAL) {
                    decode(request(i,{{"op","idle"}}).at("data"),sim.input.data(),tx_size);
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
