#pragma once
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <nlohmann/json.hpp>
using json = nlohmann::json;
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
