#pragma once
#include <cstdint>
#include <map>
#include <set>
#include <vector>
#include <stdexcept>
#include <utility>

namespace cmmt {
struct MappingError : std::runtime_error {
    uint32_t code;
    MappingError(uint32_t c, char const* message):std::runtime_error(message),code(c) {}
};
struct MappingEntry {
    uint16_t index;
    uint8_t subindex;
    uint8_t bits;
    uint32_t word() const {return (uint32_t(index)<<16)|(uint32_t(subindex)<<8)|bits;}
};
// No behaviour-model or IPC dependency. Candidate OD and active layout are distinct.
class DynamicMapping {
public:
    using Key=std::pair<uint16_t,uint8_t>;
    struct Capability {uint8_t bits; bool rx; bool tx;};
    using Layout=std::vector<MappingEntry>;
    struct Configuration {Layout rx,tx;};
private:
    std::map<Key,Capability> capabilities_;
    std::map<Key,uint32_t> candidate_;
    Configuration active_;
    bool active_valid_=false;
    static bool mapping(uint16_t index) {return index==0x1600 || index==0x1a00;}
    static bool assignment(uint16_t index) {return index==0x1c12 || index==0x1c13;}
    void validateEntry(uint32_t word,bool rx) const {
        MappingEntry e{uint16_t(word>>16),uint8_t(word>>8),uint8_t(word)};
        if(!e.bits || e.bits%8)throw MappingError(0x06040041,"PDO entry must be byte aligned");
        if(!e.index) {
            if(e.subindex)throw MappingError(0x06040041,"Invalid padding subindex");
            return;
        }
        auto it=capabilities_.find({e.index,e.subindex});
        if(it==capabilities_.end() || (rx?!it->second.rx:!it->second.tx))
            throw MappingError(0x06040041,"OD cannot be mapped in this direction");
        if(e.bits!=it->second.bits)throw MappingError(0x06040041,"PDO bit length differs from OD");
    }
    Layout layout(uint16_t index,uint32_t count,bool require) const {
        if(count>16)throw MappingError(0x06040042,"PDO item limit exceeded");
        Layout result; std::set<Key> used; unsigned bytes=0;
        for(uint8_t sub=1;sub<=count;++sub) {
            uint32_t word=read(index,sub);validateEntry(word,index==0x1600);
            MappingEntry e{uint16_t(word>>16),uint8_t(word>>8),uint8_t(word)};
            if(e.index && !used.emplace(e.index,e.subindex).second)
                throw MappingError(0x06040041,"Duplicate OD mapping");
            bytes+=e.bits/8;
            if(bytes>64)throw MappingError(0x06040042,"PDO byte limit exceeded");
            result.push_back(e);
        }
        if(require && !used.count({uint16_t(index==0x1600?0x6040:0x6041),0}))
            throw MappingError(0x06040041,"Required controlword/statusword missing");
        return result;
    }
public:
    explicit DynamicMapping(std::map<Key,Capability> capabilities):capabilities_(std::move(capabilities)) {
        for(auto index:{0x1600,0x1a00,0x1c12,0x1c13})
            for(uint8_t sub=0;sub<=(mapping(index)?16:1);++sub)candidate_[{uint16_t(index),sub}]=0;
    }
    uint32_t read(uint16_t index,uint8_t sub) const {
        auto it=candidate_.find({index,sub});
        if(it==candidate_.end())throw MappingError(0x06090011,"Mapping subindex does not exist");
        return it->second;
    }
    void write(uint16_t index,uint8_t sub,uint32_t value,bool preop) {
        if(!preop)throw MappingError(0x08000022,"PDO configuration requires PRE-OP");
        read(index,sub);
        if(mapping(index)) {
            uint16_t assign=index==0x1600?0x1c12:0x1c13;
            if(read(assign,0))throw MappingError(0x06040043,"Clear assignment before editing mapping");
            if(sub==0) {if(value)layout(index,value,false);}
            else {
                if(read(index,0))throw MappingError(0x06040043,"Clear mapping count before editing entries");
                validateEntry(value,index==0x1600);
            }
        } else if(assignment(index)) {
            if(sub==0) {
                if(value>1)throw MappingError(0x06090030,"Only one PDO per direction supported");
                if(value && read(index,1)!=(index==0x1c12?0x1600u:0x1a00u))
                    throw MappingError(0x06040041,"Unsupported assigned PDO");
            } else {
                if(read(index,0))throw MappingError(0x06040043,"Clear assignment before editing entry");
                if(value!=(index==0x1c12?0x1600u:0x1a00u))throw MappingError(0x06040041,"Unsupported assigned PDO");
            }
        }
        candidate_[{index,sub}]=value;
    }
    Configuration prepare() const {
        if(read(0x1c12,0)!=1 || read(0x1c13,0)!=1)
            throw MappingError(0x06040041,"Incomplete PDO assignments");
        return {layout(0x1600,read(0x1600,0),true),layout(0x1a00,read(0x1a00,0),true)};
    }
    void activate(Configuration prepared) {active_=std::move(prepared);active_valid_=true;}
    bool active() const {return active_valid_;}
    Configuration const& configuration() const {return active_;}
    static size_t bytes(Layout const& entries) {size_t n=0;for(auto const& e:entries)n+=e.bits/8;return n;}
};
}
