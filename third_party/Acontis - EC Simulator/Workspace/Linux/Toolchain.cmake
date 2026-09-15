# ##############################################################################################
# # Workspace/Linux/Toolchain.cmake                                                            #
# # Copyright                acontis technologies GmbH, Weingarten, Germany                    #
# # Response                 Paul Bussmann                                                     #
# # Description              Linux cross compilation toolchain settings (optional)             #
# ##############################################################################################
# Example usage to cross compile for Linux x64 Debug on Windows with cmake and ninja:
# Workspace\Linux\x64\Debug> cmake.exe -G Ninja ..\..\..\.. -DCMAKE_TOOLCHAIN_FILE=..\..\Toolchain.cmake -DEC_OS=Linux -DEC_ARCH=x64 -DCMAKE_BUILD_TYPE=Debug
# Workspace\Linux\x64\Debug> ninja.exe
# ##############################################################################################

cmake_minimum_required (VERSION 3.14)

# ##############################################################################################
# work-around cmake bug in passing parameters (environment variables are always preserved)
if (EC_OS)
    set(ENV{_EC_OS} "${EC_OS}")
else ()
    set(EC_OS "$ENV{_EC_OS}")
endif ()
if (EC_ARCH)
    set(ENV{_EC_ARCH} "${EC_ARCH}")
else ()
    set(EC_ARCH "$ENV{_EC_ARCH}")
endif ()

# ##############################################################################################
# check parameters
if (NOT DEFINED EC_OS)
  message(FATAL_ERROR "EC_OS not set!")
endif()
if (NOT DEFINED EC_ARCH)
  message(FATAL_ERROR "EC_ARCH not set!")
endif()

set(EC_OPTIONAL_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/ToolchainPrivate.cmake")
if(EXISTS "${EC_OPTIONAL_TOOLCHAIN_FILE}")
    message(STATUS "Including optional toolchain file: ${EC_OPTIONAL_TOOLCHAIN_FILE}")
    include("${EC_OPTIONAL_TOOLCHAIN_FILE}")
else()
    message(STATUS "No optional toolchain file '${EC_OPTIONAL_TOOLCHAIN_FILE}' found. Skipping!")
endif()

# ##############################################################################################
# Linux settings
set(CMAKE_SYSTEM_NAME Linux)

# For musl cross-toolchains: build try_compile tests as a static library so CMake's ABI and
# compiler-feature detection don't need to link an executable (which fails without a usable
# sysroot/CRT for the target). This keeps CMAKE_CXX_COMPILE_FEATURES populated so e.g.
# target_compile_features(... cxx_std_11) works.
if (EC_ARCH MATCHES "-musl$")
    set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
endif()

# aarch64
if (EC_ARCH STREQUAL aarch64)
    set(CMAKE_SYSTEM_PROCESSOR arm CACHE STRING "" FORCE)
    # sudo apt install crossbuild-essential-arm64
    set(CMAKE_C_COMPILER "aarch64-linux-gnu-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "aarch64-linux-gnu-g++" CACHE STRING "C++ Compiler" FORCE)

# aarch64-musl
elseif (EC_ARCH STREQUAL aarch64-musl)
    set(CMAKE_SYSTEM_PROCESSOR arm)
    # not in apt: download aarch64-linux-musl-cross from https://musl.cc and add its bin/ to PATH
    set(CMAKE_C_COMPILER "aarch64-linux-musl-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "aarch64-linux-musl-g++" CACHE STRING "C++ Compiler" FORCE)

# armv4t-eabi
elseif (EC_ARCH STREQUAL armv4t-eabi)
    set(CMAKE_SYSTEM_PROCESSOR arm CACHE STRING "" FORCE)
    # sudo apt install crossbuild-essential-armel
    # (defaults to armv5; -march=armv4t -mfloat-abi=soft below coerces it to armv4t)
    set(CMAKE_C_COMPILER "arm-linux-gnueabi-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "arm-linux-gnueabi-g++" CACHE STRING "C++ Compiler" FORCE)

# armv6-vfp-eabihf
elseif (EC_ARCH STREQUAL armv6-vfp-eabihf)
    set(CMAKE_SYSTEM_PROCESSOR arm)
    # sudo apt install crossbuild-essential-armhf
    # WARNING: Ubuntu's armhf toolchain targets armv7-a; -march=armv6 demotes it to Thumb-1,
    # which is incompatible with hard-float VFP. For real armv6 builds use a dedicated
    # toolchain (e.g. https://github.com/raspberrypi/tools or crosstool-ng).
    set(CMAKE_C_COMPILER "arm-linux-gnueabihf-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "arm-linux-gnueabihf-g++" CACHE STRING "C++ Compiler" FORCE)

# armv7-vfp-eabihf
elseif (EC_ARCH STREQUAL armv7-vfp-eabihf)
    set(CMAKE_SYSTEM_PROCESSOR arm)
    # sudo apt install crossbuild-essential-armhf
    set(CMAKE_C_COMPILER "arm-linux-gnueabihf-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "arm-linux-gnueabihf-g++" CACHE STRING "C++ Compiler" FORCE)

# armv7l-musleabihf
elseif (EC_ARCH STREQUAL armv7-vfp-eabihf-musl)
    set(CMAKE_SYSTEM_PROCESSOR arm)
    # not in apt: download armv7l-linux-musleabihf-cross from https://musl.cc and add its bin/ to PATH
    set(CMAKE_C_COMPILER "armv7l-linux-musleabihf-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "armv7l-linux-musleabihf-g++" CACHE STRING "C++ Compiler" FORCE)

# PPC
elseif (EC_ARCH STREQUAL PPC)
    set(CMAKE_SYSTEM_PROCESSOR powerpc)
    set(CMAKE_C_COMPILER "/opt/freescale-2011.03/bin/powerpc-linux-gnu-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "/opt/freescale-2011.03/bin/powerpc-linux-gnu-g++" CACHE STRING "C++ Compiler" FORCE)
    set(CMAKE_MODULE_LINKER_FLAGS "-te500v2" CACHE STRING "" FORCE)
    cmake_host_system_information(RESULT EC_HOSTNAME QUERY HOSTNAME)
    string(TOUPPER "${EC_HOSTNAME}" EC_HOSTNAME_UPPER)
    if ("${EC_HOSTNAME_UPPER}" STREQUAL "AT-VTST-EC-2")
        set(CMAKE_C_FLAGS "-te500v2" CACHE STRING "" FORCE)
        set(CMAKE_CXX_FLAGS "-te500v2" CACHE STRING "" FORCE)
    endif()

# riscv64
elseif (EC_ARCH STREQUAL riscv64)
    set(CMAKE_SYSTEM_PROCESSOR riscv CACHE STRING "" FORCE)
    # sudo apt install crossbuild-essential-riscv64
    set(CMAKE_C_COMPILER "riscv64-linux-gnu-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "riscv64-linux-gnu-g++" CACHE STRING "C++ Compiler" FORCE)

# x64
elseif (EC_ARCH STREQUAL x64)
    set(CMAKE_SYSTEM_PROCESSOR x86_64 CACHE STRING "" FORCE)
    set(CMAKE_C_COMPILER "gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "g++" CACHE STRING "C++ Compiler" FORCE)

# x64-musl
elseif (EC_ARCH STREQUAL x64-musl)
    set(CMAKE_SYSTEM_PROCESSOR x86_64 CACHE STRING "" FORCE)
    set(DPDK_SDK_DIRECTORY_ARCH "${EC_DPDK_DIR}/Linux/${EC_ARCH}" CACHE STRING "" FORCE)
    # not in apt: download x86_64-linux-musl-cross from https://musl.cc and add its bin/ to PATH
    # (Ubuntu's musl-tools package only provides a native musl-gcc wrapper, not a cross-compiler)
    set(CMAKE_C_COMPILER "x86_64-linux-musl-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "x86_64-linux-musl-g++" CACHE STRING "C++ Compiler" FORCE)

# x86
elseif (EC_ARCH STREQUAL x86)
    set(CMAKE_SYSTEM_PROCESSOR i686 CACHE STRING "" FORCE)
    # sudo apt-get install gcc-i686-linux-gnu g++-i686-linux-gnu
    set(CMAKE_C_COMPILER "i686-linux-gnu-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "i686-linux-gnu-g++" CACHE STRING "C++ Compiler" FORCE)

# x86-musl
elseif (EC_ARCH STREQUAL x86-musl)
    set(CMAKE_SYSTEM_PROCESSOR i686 CACHE STRING "" FORCE)
    set(DPDK_SDK_DIRECTORY_ARCH "${EC_DPDK_DIR}/Linux/${EC_ARCH}" CACHE STRING "" FORCE)
    # not in apt: download i686-linux-musl-cross from https://musl.cc and add its bin/ to PATH
    set(CMAKE_C_COMPILER "i686-linux-musl-gcc" CACHE STRING "C Compiler" FORCE)
    set(CMAKE_CXX_COMPILER "i686-linux-musl-g++" CACHE STRING "C++ Compiler" FORCE)
endif()

# ##############################################################################################
# check settings
if (NOT DEFINED CMAKE_CXX_COMPILER)
  message(FATAL_ERROR "CMAKE_CXX_COMPILER not set!")
endif()

# ###END OF FILE################################################################################
