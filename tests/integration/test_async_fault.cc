#include "ipc/async_model_client.h"
#include "kickcat/EmulatedNetwork.h"
#include <iostream>
#include <array>
using namespace kickcat;
static void require(bool ok,char const* text){if(!ok)throw std::runtime_error(text);}
int main() {
    try {
        for(bool delay:{true,false}) {
            std::string path="/tmp/ecat-fault-"+std::to_string(getpid())+".sock";
            int server=::socket(AF_UNIX,SOCK_STREAM,0);
            sockaddr_un addr{};addr.sun_family=AF_UNIX;std::strcpy(addr.sun_path,path.c_str());
            require(::bind(server,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0,"bind failed");
            require(::listen(server,1)==0,"listen failed");
            std::thread host([&] {
                int peer=::accept(server,nullptr,nullptr);
                char data[1024];::recv(peer,data,sizeof(data),0);
                if(delay) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(220));
                    std::string late="{\"data\":\"late\"}\n";
                    ::send(peer,late.data(),late.size(),MSG_NOSIGNAL);
                }
                ::close(peer);
            });
            bool fault=false;unsigned routed=0;
            {
                AsyncModelClient client(path);
                auto pending=client.submit({{"op","cycle"}});
                std::array<EmulatedESC,4> esc;
                EmulatedNetwork network({&esc[0],&esc[1],&esc[2],&esc[3]});
                auto begin=std::chrono::steady_clock::now();
                while(std::chrono::steady_clock::now()-begin<std::chrono::milliseconds(300)) {
                    Frame frame;uint16_t value=0;
                    frame.addDatagram(0,Command::BRD,static_cast<uint32_t>(reg::AL_STATUS)<<16,&value,2);
                    frame.finalize();require(network.route(frame),"route failed during Host stall");
                    frame.resetContext();auto [h,d,wkc]=frame.peekDatagram();(void)h;(void)d;
                    require(wkc && *wkc==4,"ESCs stopped responding");++routed;
                    if(!fault && pending.wait_for(std::chrono::seconds(0))==std::future_status::ready) {
                        try{pending.get();}
                        catch(std::runtime_error const&){fault=true;}
                        require(fault,"late response was accepted");
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                }
                require(!client.failure().empty(),"Host failure not latched");
                auto retry=client.submit({{"op","cycle"}});
                require(retry.wait_for(std::chrono::milliseconds(5))==std::future_status::ready,"Fault retry blocked");
                try{retry.get();throw std::logic_error("fault was reset implicitly");}catch(std::runtime_error const&){}
            }
            host.join();::close(server);::unlink(path.c_str());
            require(fault && routed>100,"routing stalled on model RPC");
            std::cout<<(delay?"timeout":"disconnect")<<": four ESCs routed "<<routed<<" frames; Host fault latched\n";
        }
    } catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}
}
