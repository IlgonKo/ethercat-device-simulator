#pragma once
#include "model_client.h"
#include <condition_variable>
#include <deque>
#include <future>
#include <mutex>
#include <thread>
#include <chrono>

// The only thread owning the RPC socket. Network/ESC thread never waits for RPCs.
class AsyncModelClient {
    struct Job { json message; std::promise<json> promise; };
    std::mutex mutex_;
    std::condition_variable changed_;
    std::deque<Job> jobs_;
    bool stopping_ = false;
    std::string failure_;
    std::thread worker_;
public:
    explicit AsyncModelClient(std::string path): worker_([this,path] {
        try {
            ModelClient client(path);
            for(;;) {
                Job job;
                {
                    std::unique_lock<std::mutex> lock(mutex_);
                    changed_.wait(lock,[this]{return stopping_ || !jobs_.empty();});
                    if(stopping_)return;
                    job=std::move(jobs_.front());jobs_.pop_front();
                }
                try { job.promise.set_value(client.request(job.message)); }
                catch(...) { job.promise.set_exception(std::current_exception());throw; }
            }
        } catch(std::exception const& e) {
            std::lock_guard<std::mutex> lock(mutex_);
            failure_=e.what();
            for(auto& job:jobs_)job.promise.set_exception(std::make_exception_ptr(std::runtime_error(failure_)));
            jobs_.clear();
        }
    }) {}
    ~AsyncModelClient() {
        {std::lock_guard<std::mutex> lock(mutex_);stopping_=true;}
        changed_.notify_all();worker_.join();
    }
    std::shared_future<json> submit(json message) {
        Job job{std::move(message),{}};
        auto future=job.promise.get_future().share();
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!failure_.empty())job.promise.set_exception(std::make_exception_ptr(std::runtime_error(failure_)));
            else if(jobs_.size()>=64)job.promise.set_exception(std::make_exception_ptr(std::runtime_error("Model queue full")));
            else jobs_.push_back(std::move(job));
        }
        changed_.notify_one();return future;
    }
    json request(json message) {return submit(std::move(message)).get();} // startup only
    std::string failure() {std::lock_guard<std::mutex> lock(mutex_);return failure_;}
};
