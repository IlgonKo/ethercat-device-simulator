#pragma once
#include "dynamic_mapping.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>
#include <cerrno>
#include <cstring>

namespace cmmt {
class MappingStore {
    using json=nlohmann::json;
    std::filesystem::path path_;
    json identity_;
    uint64_t revision_=0;
    int lock_=-1;
    static uint32_t checksum(std::string const& text) {
        uint32_t crc=~0u;
        for(unsigned char c:text){crc^=c;for(int n=0;n<8;++n)crc=(crc>>1)^(0xedb88320u & (0u-(crc&1)));}
        return ~crc;
    }
    static json entries(DynamicMapping::Layout const& layout) {
        json result=json::array();for(auto const& e:layout)result.push_back(e.word());return result;
    }
    static void error(char const* what) {throw std::runtime_error(std::string(what)+": "+std::strerror(errno));}
public:
    MappingStore(std::filesystem::path root,std::string const& id,json identity):identity_(std::move(identity)) {
        auto dir=root/"pdo-mappings";std::filesystem::create_directories(dir);
        std::string key;char const* digits="0123456789abcdef";
        for(unsigned char c:id){key+=digits[c>>4];key+=digits[c&15];}
        if(key.empty())throw std::runtime_error("Empty mapping device ID");
        path_=dir/(key+".json");
        lock_=::open((path_.string()+".lock").c_str(),O_CREAT|O_RDWR|O_CLOEXEC,0600);
        if(lock_<0)error("Mapping lock open");
        if(flock(lock_,LOCK_EX|LOCK_NB)){::close(lock_);lock_=-1;error("Mapping store already in use");}
    }
    ~MappingStore(){if(lock_>=0)::close(lock_);}
    MappingStore(MappingStore const&)=delete;
    bool load(DynamicMapping& mapping) {
        if(!std::filesystem::exists(path_))return false;
        std::ifstream f(path_);json data;f>>data;
        auto sum=data.at("checksum").get<uint32_t>();data.erase("checksum");
        if(data.at("schema_version")!=1 || data.at("identity")!=identity_ || checksum(data.dump())!=sum)
            throw std::runtime_error("Incompatible or corrupt mapping file: "+path_.string());
        revision_=data.at("revision").get<uint64_t>();
        // Validate using a copy. Invalid content must not partially change candidate OD.
        auto candidate=mapping;
        for(auto pair:{std::pair{0x1600,"rx"},std::pair{0x1a00,"tx"}}) {
            auto const& a=data.at(pair.second);if(!a.is_array() || a.size()>16)throw MappingError(0x06040042,"Stored mapping length invalid");
            uint8_t sub=0;for(auto const& e:a)candidate.write(pair.first,++sub,e.get<uint32_t>(),true);
            candidate.write(pair.first,0,sub,true);
            uint16_t assign=pair.first==0x1600?0x1c12:0x1c13;
            candidate.write(assign,1,pair.first,true);candidate.write(assign,0,1,true);
        }
        auto ready=candidate.prepare();candidate.activate(std::move(ready));mapping=std::move(candidate);return true;
    }
    void save(DynamicMapping::Configuration const& config) {
        json data={{"schema_version",1},{"identity",identity_},{"revision",revision_+1},
                   {"rx",entries(config.rx)},{"tx",entries(config.tx)}};
        data["checksum"]=checksum(data.dump());auto bytes=data.dump(2)+"\n";
        auto tmp=path_.string()+".tmp";
        int fd=::open(tmp.c_str(),O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0600);
        if(fd<0)error("Mapping temporary file");
        try {
            size_t done=0;while(done<bytes.size()) {
                auto n=::write(fd,bytes.data()+done,bytes.size()-done);
                if(n<0 && errno==EINTR)continue;
                if(n<=0)error("Mapping write");
                done+=n;
            }
            if(::fsync(fd))error("Mapping file sync");
            ::close(fd);fd=-1;
            if(::rename(tmp.c_str(),path_.c_str()))error("Mapping replace");
            int dir=::open(path_.parent_path().c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC);
            if(dir<0)error("Mapping directory open after replace; commit uncertain");
            int rc=::fsync(dir);::close(dir);
            if(rc)error("Mapping directory sync after replace; commit uncertain");
            ++revision_;
        }catch(...){if(fd>=0)::close(fd);::unlink(tmp.c_str());throw;}
    }
};
}
