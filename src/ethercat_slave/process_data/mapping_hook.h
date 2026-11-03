#pragma once
#include <functional>
#include <map>
#include "kickcat/PDO.h"
namespace cmmt {
inline std::map<kickcat::PDO*,std::function<kickcat::StatusCode()>> mappingHooks;
}
