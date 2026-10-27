#include "sdo_gateway.h"
#include <cstring>
#include <stdexcept>
using namespace kickcat;
using namespace kickcat::mailbox;
using namespace kickcat::mailbox::response;
using json = nlohmann::json;

// GNU linker wrapper: leave the upstream factory and submodule unchanged.
extern "C" std::shared_ptr<AbstractMessage> originalFactory(Mailbox*,std::vector<uint8_t>&&)
    asm("__real__ZN7kickcat7mailbox8response16createSDOMessageEPNS1_7MailboxEOSt6vectorIhSaIhEE");

namespace {
constexpr size_t H = sizeof(mailbox::Header), C = sizeof(CoE::Header);
constexpr size_t S = H+C, P = S+sizeof(CoE::ServiceData);
std::string hex(uint8_t const* p, size_t n) {
    char const* digits="0123456789abcdef"; std::string s;
    for(size_t i=0;i<n;++i){s+=digits[p[i]>>4];s+=digits[p[i]&15];} return s;
}
std::vector<uint8_t> unhex(std::string const& s,size_t n) {
    if(s.size()!=n*2)throw std::runtime_error("SDO IPC size mismatch");
    auto digit=[](char c)->int {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("Invalid SDO hex");};
    std::vector<uint8_t> out(n);
    for(size_t i=0;i<n;++i)out[i]=(digit(s[2*i])<<4)|digit(s[2*i+1]);
    return out;
}
class GatewayMessage final: public AbstractMessage {
    std::shared_ptr<AbstractMessage> delegate_;
    cmmt::SdoGateway* gateway_;
    void abort(uint32_t code) {
        // Keep the complete mailbox buffer: ESC publishes only on last-byte write.
        if(data_.size()<P+4)data_.resize(P+4);
        reinterpret_cast<mailbox::Header*>(data_.data())->len=C+sizeof(CoE::ServiceData)+4;
        reinterpret_cast<CoE::Header*>(data_.data()+H)->service=CoE::Service::SDO_REQUEST;
        data_[S]=0x80; // Full command byte, not only the 3-bit command field.
        for(unsigned i=0;i<4;++i)data_[P+i]=static_cast<uint8_t>(code>>(8*i));
        reply(std::move(data_));
    }
    void normalizeReplies() {
        std::vector<std::vector<uint8_t>> replies;
        for(;;) {
            auto r=mailbox_->popReply(); if(r.empty())break;
            if(r.size()>=P+4 && reinterpret_cast<mailbox::Header*>(r.data())->type==mailbox::Type::CoE
               && reinterpret_cast<CoE::Header*>(r.data()+H)->service==CoE::Service::SDO_REQUEST
               && (r[S]>>5)==4) {
                r[S]=0x80;
                reinterpret_cast<mailbox::Header*>(r.data())->len=C+sizeof(CoE::ServiceData)+4;
            }
            replies.push_back(std::move(r));
        }
        for(auto& r:replies)reply(std::move(r));
    }
public:
    GatewayMessage(Mailbox* m,std::vector<uint8_t> raw,cmmt::SdoGateway* g,
                   std::shared_ptr<AbstractMessage> delegate):AbstractMessage(m),delegate_(std::move(delegate)),gateway_(g) {
        data_=std::move(raw);
    }
    ProcessingResult process() override {
        if(delegate_) {
            try {
                auto result=delegate_->process(); normalizeReplies(); return result;
            } catch(std::exception const&) {
                // Some upstream hooks run after queuing success. Remove that
                // reply before translating an application rejection to Abort.
                while(!mailbox_->popReply().empty()) {}
                abort(0x08000000);return ProcessingResult::FINALIZE;
            }
        }
        auto const* h=reinterpret_cast<mailbox::Header const*>(data_.data());
        auto const* s=reinterpret_cast<CoE::ServiceData const*>(data_.data()+S);
        uint16_t index=s->index; uint8_t sub=s->subindex;
        if(h->len<C+sizeof(CoE::ServiceData)+4 || H+h->len>data_.size()) {abort(0x06070010);return ProcessingResult::FINALIZE;}
        if(!gateway_->entries.count({index,sub})) {abort(0x06090011);return ProcessingResult::FINALIZE;}
        if(s->complete_access){abort(0x06010000);return ProcessingResult::FINALIZE;}
        auto [object,entry]=CoE::findObject(mailbox_->getDictionary(),index,sub); (void)object;
        if(!entry){abort(0x06020000);return ProcessingResult::FINALIZE;}
        auto size=(entry->bitlen+7u)/8u;
        if(size>4 || size==0){abort(0x06010000);return ProcessingResult::FINALIZE;}
        bool write=s->command==CoE::SDO::request::DOWNLOAD;
        if(!write && s->command!=CoE::SDO::request::UPLOAD){abort(0x05040001);return ProcessingResult::FINALIZE;}
        if(!(entry->access & (write?CoE::Access::WRITE:CoE::Access::READ))) {
            abort(write?0x06010002:0x06010001);return ProcessingResult::FINALIZE;
        }
        json request={{"op",write?"write":"read"},{"index",index},{"subindex",sub}};
        std::vector<uint8_t> value;
        if(write) {
            size_t offset=P; uint32_t length=0;
            if(s->transfer_type)length=s->size_indicator?4-s->block_size:size;
            else {
                if(!s->size_indicator){abort(0x06010000);return ProcessingResult::FINALIZE;}
                std::memcpy(&length,data_.data()+P,4);offset+=4;
            }
            if(length!=size || offset+size>H+h->len){abort(0x06070010);return ProcessingResult::FINALIZE;}
            value.assign(data_.begin()+offset,data_.begin()+offset+size);
            request["data"]=hex(value.data(),size);
        }
        try {
            auto result=gateway_->request(request);
            if(result.contains("error")) {
                abort(result.at("error").at("code").get<uint32_t>());return ProcessingResult::FINALIZE;
            }
            if(!write)value=unhex(result.at("data").get<std::string>(),size);
            // Commit local OD only after model acceptance; never queue success first.
            std::memcpy(entry->data,value.data(),size);
            // Keep the complete mailbox buffer: ESC publishes only on last-byte write.
        if(data_.size()<P+4)data_.resize(P+4);
            reinterpret_cast<mailbox::Header*>(data_.data())->len=C+sizeof(CoE::ServiceData)+4;
            reinterpret_cast<CoE::Header*>(data_.data()+H)->service=CoE::Service::SDO_RESPONSE;
            data_[S]=write?0x60:static_cast<uint8_t>(0x43|((4-size)<<2));
            std::fill(data_.begin()+P,data_.end(),0);
            if(!write)std::copy(value.begin(),value.end(),data_.begin()+P);
            reply(std::move(data_));
        } catch(std::exception const&) {abort(0x08000000);}
        return ProcessingResult::FINALIZE;
    }
    ProcessingResult process(std::vector<uint8_t> const& raw) override {
        if(!delegate_)return ProcessingResult::NOOP;
        auto result=delegate_->process(raw);normalizeReplies();return result;
    }
};
}
extern "C" std::shared_ptr<AbstractMessage> wrappedFactory(Mailbox* m,std::vector<uint8_t>&& raw)
    asm("__wrap__ZN7kickcat7mailbox8response16createSDOMessageEPNS1_7MailboxEOSt6vectorIhSaIhEE");
extern "C" std::shared_ptr<AbstractMessage> wrappedFactory(Mailbox* m,std::vector<uint8_t>&& raw) {
    auto it=cmmt::sdoGateways.find(m);
    if(it==cmmt::sdoGateways.end())return originalFactory(m,std::move(raw));
    if(raw.size()>=P && reinterpret_cast<mailbox::Header*>(raw.data())->type==mailbox::Type::CoE
       && reinterpret_cast<CoE::Header*>(raw.data()+H)->service==CoE::Service::SDO_REQUEST) {
        auto index=reinterpret_cast<CoE::ServiceData*>(raw.data()+S)->index;
        auto pos=it->second.entries.lower_bound({index,0});
        if(pos!=it->second.entries.end() && pos->first==index)
            return std::make_shared<GatewayMessage>(m,std::move(raw),&it->second,nullptr);
    }
    auto copy=raw;
    auto delegate=originalFactory(m,std::move(raw));
    if(!delegate)return nullptr;
    return std::make_shared<GatewayMessage>(m,std::move(copy),nullptr,std::move(delegate));
}
