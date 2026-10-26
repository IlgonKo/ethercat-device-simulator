#pragma once
#include <chrono>
#include <iostream>
#include <map>
#include <string>
#include <nlohmann/json.hpp>

namespace cmmt {
using TimingClock = std::chrono::steady_clock;
inline double milliseconds(TimingClock::time_point a, TimingClock::time_point b) {
    return std::chrono::duration<double,std::milli>(b-a).count();
}
struct TimingBucket {
    uint64_t count=0, over2=0, over8=0;
    double total=0, minimum=0, maximum=0;
    void add(double ms) {
        if(!count || ms<minimum)minimum=ms;
        if(!count || ms>maximum)maximum=ms;
        ++count; total+=ms; over2+=ms>2; over8+=ms>8;
    }
    nlohmann::json value() const {
        return {{"count",count},{"min_ms",minimum},{"avg_ms",count?total/count:0},
                {"max_ms",maximum},{"over_2ms",over2},{"over_8ms",over8}};
    }
};
class Timing {
    bool enabled_;
    TimingClock::time_point start_=TimingClock::now(), last_=start_;
    std::map<std::string,TimingBucket> buckets_;
public:
    size_t axes=0;
    uint64_t ipc_failures=0;
    explicit Timing(bool enabled):enabled_(enabled) {}
    bool enabled() const {return enabled_;}
    void add(std::string const& key,double ms) {if(enabled_)buckets_[key].add(ms);}
    void add(std::string const& key,TimingClock::time_point a,TimingClock::time_point b) {
        add(key,milliseconds(a,b));
    }
    void flush(std::string const& reason="interval") {
        if(!enabled_ || buckets_.empty())return;
        auto now=TimingClock::now();
        nlohmann::json metrics=nlohmann::json::object();
        for(auto const& [key,bucket]:buckets_)metrics[key]=bucket.value();
        auto unix_ms=std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        std::cout<<nlohmann::json({{"event","simulator-timing"},{"reason",reason},
            {"unix_ms",unix_ms},{"elapsed_s",milliseconds(start_,now)/1000},
            {"window_s",milliseconds(last_,now)/1000},{"axes",axes},
            {"ipc_failures",ipc_failures},{"metrics",metrics}}).dump()<<std::endl;
        buckets_.clear(); ipc_failures=0; last_=now;
        // Report logging overhead in the next window (not inside frame_busy).
        add("timing_log",now,TimingClock::now());
    }
    void due() {if(enabled_ && milliseconds(last_,TimingClock::now())>=1000)flush();}
};
}
