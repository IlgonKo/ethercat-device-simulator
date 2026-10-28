#pragma once
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <poll.h>
#include <chrono>
#include <cstdlib>
#include <nlohmann/json.hpp>
using json = nlohmann::json;
class ModelClient {
    int fd_ = -1;
    int timeout_ms_ = 100;
public:
    explicit ModelClient(std::string const& path) {
        if(auto value=std::getenv("DEVICE_SIMULATOR_MODEL_TIMEOUT_MS")) {
            std::string text(value);size_t used=0;timeout_ms_=std::stoi(text,&used);
            if(used!=text.size() || timeout_ms_<10 || timeout_ms_>5000)
                throw std::runtime_error("DEVICE_SIMULATOR_MODEL_TIMEOUT_MS must be 10..5000");
        }
        sockaddr_un address{}; address.sun_family=AF_UNIX;
        if(path.size()>=sizeof(address.sun_path))throw std::runtime_error("Socket path too long");
        std::memcpy(address.sun_path,path.c_str(),path.size()+1);
        fd_=::socket(AF_UNIX,SOCK_STREAM,0);
        if(fd_<0)throw std::runtime_error("Cannot create model socket");
        timeval timeout{timeout_ms_/1000,(timeout_ms_%1000)*1000};
        if(setsockopt(fd_,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)) ||
           setsockopt(fd_,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout)) ||
           connect(fd_,reinterpret_cast<sockaddr*>(&address),sizeof(address))) {
            close(fd_); fd_=-1; throw std::runtime_error("Cannot connect to model service");
        }
    }
    ~ModelClient(){if(fd_>=0)close(fd_);}
    json request(json const& message) {
        auto deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(timeout_ms_);
        auto ready=[&](short events) {
            auto remaining=std::chrono::duration_cast<std::chrono::milliseconds>(deadline-std::chrono::steady_clock::now()).count();
            if(remaining<=0)throw std::runtime_error("MODEL_RESPONSE_TIMEOUT");
            pollfd p{fd_,events,0};
            auto result=::poll(&p,1,static_cast<int>(remaining));
            if(result==0)throw std::runtime_error("MODEL_RESPONSE_TIMEOUT");
            if(result<0 || (p.revents & (POLLERR|POLLNVAL)))throw std::runtime_error("MODEL_HOST_DISCONNECTED");
        };
        auto data=message.dump()+"\n";
        size_t sent=0;
        while(sent<data.size()) {
            ready(POLLOUT);
            auto n=send(fd_,data.data()+sent,data.size()-sent,MSG_NOSIGNAL);
            if(n<=0)throw std::runtime_error("Model service send failed");
            sent+=n;
        }
        std::string response;
        // Read chunks with MSG_PEEK to consume exactly one newline-framed response.
        while(response.size()<=1024*1024) {
            ready(POLLIN);
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
