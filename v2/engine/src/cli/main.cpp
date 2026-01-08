#include <iostream>

#include "v2/engine/version.hpp"

int main() {
    std::cout << "v2_engine_cli " << v2::engine::engine_version() << '\n';
    return 0;
}
