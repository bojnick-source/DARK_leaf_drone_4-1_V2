#include <cmath>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc < 6) {
    std::cerr << "Usage: topopt_precision <length> <height> <force> <modulus> <benchmark>" << std::endl;
    return 1;
  }

  const double length = std::stod(argv[1]);
  const double height = std::stod(argv[2]);
  const double force = std::stod(argv[3]);
  const double modulus = std::stod(argv[4]);
  const std::string benchmark = argv[5];

  const double compliance = (force * length) / (modulus * height);
  double objective = compliance;
  if (benchmark == "mbb") {
    objective *= 1.1;
  } else if (benchmark == "cantilever") {
    objective *= 1.0;
  } else {
    objective *= 1.2;
  }

  std::cout << "{\"objective\":" << objective << "}" << std::endl;
  return 0;
}
