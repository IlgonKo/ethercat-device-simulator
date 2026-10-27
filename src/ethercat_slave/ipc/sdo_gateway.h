#pragma once
#include <functional>
#include <map>
#include <set>
#include <nlohmann/json.hpp>
#include "kickcat/CoE/mailbox/response.h"

namespace cmmt {
struct SdoGateway {
    std::set<std::pair<uint16_t,uint8_t>> entries;
    std::function<nlohmann::json(nlohmann::json)> request;
};
// Registered once at startup; mailbox processing runs on the Slave thread.
inline std::map<kickcat::mailbox::response::Mailbox*, SdoGateway> sdoGateways;
}
