#pragma once
#include <map>
#include <algorithm>
#include <cstdint>
#include <set>
#include <future>
#include <cstring>
#include <nlohmann/json.hpp>
#include "kickcat/simulation/SimulatedSlave.h"
#include "../ipc/sdo_gateway.h"
#include "mapping_hook.h"

namespace softesc {
using json=nlohmann::json;
// CPX local OD and bit layout. Neither remapping nor persistence is delegated to IPC.
class FixedIO {
    using Key=std::pair<uint16_t,uint8_t>;
    kickcat::sim::SimulatedSlave& sim_;
    json spec_;
    std::map<Key,kickcat::CoE::Entry*> entries_;
    std::map<Key,uint32_t> idents_;
    std::set<Key> tx_keys_;
    static uint32_t get(uint8_t const* buffer,size_t bit,unsigned bits) {
        uint32_t result=0;
        for(unsigned n=0;n<bits;++n)result|=uint32_t((buffer[(bit+n)/8]>>((bit+n)%8))&1)<<n;
        return result;
    }
    static void put(uint8_t* buffer,size_t bit,unsigned bits,uint32_t value) {
        for(unsigned n=0;n<bits;++n) {
            auto& byte=buffer[(bit+n)/8];auto mask=uint8_t(1u<<((bit+n)%8));
            byte=(byte&~mask)|(((value>>n)&1)?mask:0);
        }
    }
    static std::string encode(uint32_t value,unsigned bytes) {
        char const* digits="0123456789abcdef";std::string result;
        for(unsigned n=0;n<bytes;++n){auto v=(value>>(8*n))&255;result+=digits[v>>4];result+=digits[v&15];}
        return result;
    }
    static uint32_t decode(std::string const& value,unsigned bytes) {
        if(value.size()!=bytes*2)throw std::runtime_error("IO OD data length mismatch");
        auto digit=[](char c)->unsigned {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("Invalid IO hex");};
        uint32_t result=0;for(unsigned n=0;n<bytes;++n)result|=(digit(value[n*2])*16+digit(value[n*2+1]))<<(8*n);
        return result;
    }
public:
    uint64_t sequence=0;
    bool valid_output=false, invalidation_pending=true;
    explicit FixedIO(kickcat::sim::SimulatedSlave& sim,json spec):sim_(sim),spec_(std::move(spec)) {
        for(auto const& e:spec_.at("entries")) {
            Key key{e.at("index"),e.at("subindex")};
            auto [object,entry]=kickcat::CoE::findObject(*sim_.dictionary,key.first,key.second);(void)object;
            if(!entry || entry->bitlen!=e.at("bits"))throw std::runtime_error("CPX ESI contract mismatch");
            entries_[key]=entry;
            if(e.value("tx",false))tx_keys_.insert(key);
            if(key.first==0xf030)idents_[key]=decode(e.at("initial"),(entry->bitlen+7)/8);
        }
        auto& gateway=cmmt::sdoGateways[sim_.mailbox.get()];
        for(auto const& [key,e]:entries_){(void)e;gateway.entries.insert(key);}
        gateway.submit=[this](json message) {std::promise<json> p;p.set_value(sdo(message));return p.get_future().share();};
        cmmt::mappingHooks[sim_.pdo.get()]=[this]() {
            using namespace kickcat;
            auto length=[&](uint8_t direction) {try{return unsigned(std::get<1>(sim_.esc->findSm(SM_CONTROL_MODE_BUFFERED|direction)).length);}catch(std::exception const&){return 0u;}};
            if(length(SM_CONTROL_DIRECTION_WRITE)!=bytes(true))return StatusCode::INVALID_OUTPUT_MAPPING;
            if(length(SM_CONTROL_DIRECTION_READ)!=bytes(false))return StatusCode::INVALID_INPUT_MAPPING;
            return sim_.pdo->isConfigOk();
        };
    }
    size_t bytes(bool rx) const {return spec_.at(rx?"rx_size":"tx_size").get<size_t>();}
    json sdo(json const& message) {
        Key key{message.at("index"),message.at("subindex")};auto it=entries_.find(key);
        auto error=[](uint32_t code,char const* text){return json{{"error",{{"code",code},{"message",text}}}};};
        if(it==entries_.end())return error(0x06020000,"Unsupported CPX object");
        auto* e=it->second;auto size=(e->bitlen+7)/8;
        if(message.at("op")=="write") {
            if(key.first!=0xf030)return error(0x06010002,"Read-only CPX object");
            if(sim_.slave->state()!=kickcat::State::PRE_OP)return error(0x08000022,"F030 requires PRE-OP");
            auto v=decode(message.at("data"),size);
            if(v!=idents_.at(key))return error(0x06090030,"Configured module list differs from physical configuration");
            // Only the configured ident/count is accepted; no topology/mapping mutation.
            return json::object();
        }
        uint32_t v=0;std::memcpy(&v,e->data,size);return {{"data",encode(v,size)}};
    }
    void sample(bool received) {
        if(sim_.slave->state()!=kickcat::State::OPERATIONAL) {
            if(valid_output)invalidation_pending=true;
            valid_output=false;
        }else if(received) {
            size_t bit=0;
            for(auto const& e:spec_.at("rx")) {
                unsigned bits=e.at("bits");uint16_t index=e.at("index");
                if(index){auto* entry=entries_.at({index,e.at("subindex")});auto v=get(sim_.output.data(),bit,bits);std::memcpy(entry->data,&v,(bits+7)/8);}
                bit+=bits;
            }
            ++sequence;valid_output=true;
        }
    }
    json snapshot(size_t index) {
        json values=json::array();
        for(auto const& e:spec_.at("entries"))if(e.value("rx",false)) {
            auto* entry=entries_.at({e.at("index"),e.at("subindex")});uint32_t v=0;
            std::memcpy(&v,entry->data,(entry->bitlen+7)/8);
            values.push_back({{"index",e.at("index")},{"subindex",e.at("subindex")},{"data",encode(v,(entry->bitlen+7)/8)}});
        }
        bool active=valid_output && !invalidation_pending;
        invalidation_pending=false;
        return {{"slave_index",index},{"sequence",sequence},{"active",active},{"values",values}};
    }
    using Values=std::map<Key,uint32_t>;
    Values prepareFeedback(json const& values) const {
        Values ready;
        for(auto const& e:values) {
            Key key{e.at("index"),e.at("subindex")};
            if(!tx_keys_.count(key) || ready.count(key))throw std::runtime_error("Invalid IO feedback address");
            auto bits=entries_.at(key)->bitlen;auto value=decode(e.at("data"),(bits+7)/8);
            if(bits==1 && value>1)throw std::runtime_error("Invalid IO boolean feedback");
            ready[key]=value;
        }
        if(ready.size()!=tx_keys_.size())throw std::runtime_error("Incomplete IO feedback");
        return ready;
    }
    void feedback(json const& values) {commitFeedback(prepareFeedback(values));}
    void commitFeedback(Values const& ready) {
        for(auto const& [key,value]:ready){auto* e=entries_.at(key);std::memcpy(e->data,&value,(e->bitlen+7)/8);}
        publish();
    }
    void publish() {
        size_t bit=0;
        for(auto const& e:spec_.at("tx")) {
            unsigned bits=e.at("bits");uint16_t index=e.at("index");uint32_t value=0;
            if(index){auto* entry=entries_.at({index,e.at("subindex")});std::memcpy(&value,entry->data,(bits+7)/8);}
            put(sim_.input.data(),bit,bits,value);bit+=bits;
        }
    }
};
}
