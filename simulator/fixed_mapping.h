#pragma once
#include <cstdint>
#include <map>
#include <stdexcept>
#include <utility>

// Internal simulator guard: permit the master's clear/rewrite/restore sequence
// for the selected mapping, without accepting a different process image.
class FixedMapping {
public:
    using Key = std::pair<uint16_t, uint8_t>;
    explicit FixedMapping(std::map<Key, uint32_t> expected)
        : expected_(std::move(expected)), current_(expected_) {}

    void write(uint16_t index, uint8_t subindex, uint32_t value, bool preop) {
        Key key{index, subindex};
        auto found = expected_.find(key);
        if (!preop || found == expected_.end())
            throw std::runtime_error("PDO configuration write outside supported PRE-OP contract");
        if (value != found->second && !(subindex == 0 && value == 0))
            throw std::runtime_error("Changing the selected PDO configuration is unsupported");
        current_[key] = value;
    }

    bool complete() const { return current_ == expected_; }

private:
    std::map<Key, uint32_t> expected_;
    std::map<Key, uint32_t> current_;
};
