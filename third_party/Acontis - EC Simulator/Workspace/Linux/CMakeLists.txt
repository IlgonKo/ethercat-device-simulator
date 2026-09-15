# ##############################################################################################
# # Workspace/Linux/CMakeLists.txt                                                             #
# # Copyright                acontis technologies GmbH, Weingarten, Germany                    #
# # Response                 Paul Bussmann                                                     #
# # Description              Linux settings                                                    #
# ##############################################################################################

cmake_minimum_required (VERSION 3.14)

if (DEFINED CMAKE_TOOLCHAIN_FILE)
MESSAGE(STATUS "Workspace/Linux/CMakeLists.txt: ${EC_OS} ${EC_ARCH} CMAKE_TOOLCHAIN_FILE: ${CMAKE_TOOLCHAIN_FILE}")
endif()

set(EC_OS_LAYER_INC_NAME Linux CACHE STRING "" FORCE)
set(EC_OS_LAYER_SOURCES                  ${EC_TOP_LEVEL_DIR}/Sources/OsLayer/Linux/EcOs.cpp CACHE STRING "" FORCE)
set(EC_LINK_OS_LAYER_INC                 ${EC_TOP_LEVEL_DIR}/Sources/LinkOsLayer/Linux/atemsys ${EC_TOP_LEVEL_DIR}/Sources/LinkOsLayer/Linux CACHE STRING "" FORCE)
set(EC_LINK_OS_LAYER_SOURCES             ${EC_TOP_LEVEL_DIR}/Sources/LinkOsLayer/Linux/LinkOsLayer.cpp CACHE STRING "" FORCE)
set(EC_DEMO_OS_LAYER_INC                 ${EC_TOP_LEVEL_DIR}/Examples/Common/Linux CACHE STRING "" FORCE)
set(EC_DEMO_OS_LAYER_TIMING_TASK_SOURCES ${EC_TOP_LEVEL_DIR}/Examples/Common/Linux/EcDemoTimingTaskPlatform.cpp CACHE STRING "" FORCE)
set(EC_DEMO_OS_LAYER_SOURCES             ${EC_TOP_LEVEL_DIR}/Examples/Common/Linux/EcDemoMain.cpp CACHE STRING "" FORCE)
set(EC_EOETAP_OS_LAYER_INC               ${EC_TOP_LEVEL_DIR}/Sources/NetworkDrv/EoE/LinuxTAP CACHE STRING "" FORCE)

# C/C++ Flags
set(EC_C_CXX_FLAGS "-fPIC -fno-builtin-strlen -fno-strict-aliasing -Wall -Werror -fmessage-length=0" CACHE STRING "" FORCE)
if (EC_ARCH MATCHES "^aarch64(-musl)?$")
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS} -Wno-psabi" CACHE STRING "" FORCE)
elseif (EC_ARCH STREQUAL armv4t-eabi)
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS} -Wno-psabi -march=armv4t -mfloat-abi=soft" CACHE STRING "" FORCE)
elseif (EC_ARCH STREQUAL armv6-vfp-eabihf)
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS} -Wno-psabi -marm -march=armv6 -mfpu=vfp -mfloat-abi=hard" CACHE STRING "" FORCE)
elseif (EC_ARCH MATCHES "^armv7-vfp-eabihf(-musl)?$")
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS} -Wno-psabi" CACHE STRING "" FORCE)
elseif (EC_ARCH STREQUAL PPC)
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS} -te500v2" CACHE STRING "" FORCE)
elseif (EC_ARCH STREQUAL riscv64)
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS}" CACHE STRING "" FORCE)
elseif (EC_ARCH MATCHES "^x64(-musl)?$")
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS}" CACHE STRING "" FORCE)
elseif (EC_ARCH MATCHES "^x86(-musl)?$")
    set(EC_C_CXX_FLAGS "${EC_C_CXX_FLAGS}" CACHE STRING "" FORCE)
endif()

if (EC_OS STREQUAL LxWin)
    set(CMAKE_C_FLAGS "-DLXWIN" CACHE STRING "" FORCE)
    set(CMAKE_CXX_FLAGS "-DLXWIN" CACHE STRING "" FORCE)
    set(CMAKE_MODULE_LINKER_FLAGS "-lrtos" CACHE STRING "" FORCE)
endif()

# DPDK SDK
if ((EC_ARCH STREQUAL aarch64) OR (EC_ARCH STREQUAL x64))
    set(DPDK_SDK_INCLUDE_DIRECTORIES_ARCH ${EC_DPDK_DIR}/Linux/${EC_ARCH}/include CACHE STRING "" FORCE)
    set(DPDK_SDK_LINK_DIRECTORIES_ARCH ${EC_DPDK_DIR}/Linux/${EC_ARCH}/lib CACHE STRING "" FORCE)
endif()

# WIBU Dongle
if (CMAKE_BUILD_TYPE STREQUAL WibuDongled)
    set(WIBU_SDK_INCLUDE_DIRECTORIES_ARCH "${EC_WIBU_DEVKIT_DIR}/include" CACHE STRING "" FORCE)
    set(WIBU_SDK_LINK_DIRECTORIES_ARCH    "${EC_WIBU_DEVKIT_DIR}/lib/Linux/${EC_ARCH}" CACHE STRING "" FORCE)
endif()

set(EC_INCLUDE_DIRECTORIES_ARCH ${WIBU_SDK_INCLUDE_DIRECTORIES_ARCH} CACHE STRING "" FORCE)
set(EC_LINK_DIRECTORIES_ARCH ${WIBU_SDK_LINK_DIRECTORIES_ARCH} CACHE STRING "" FORCE)

# CXX-only additions. -fno-sized-deallocation disables the C++14 sized
# operator delete(void*, size_t) codegen; CppUTest 0.2.0 doesn't override
# the sized form, so on GCC 5+ Valgrind reports "Mismatched free/delete"
# against pointers allocated through CppUTest's malloc-based new tracker.
# Only emitted on GCC >= 5: pre-C++14 toolchains (Freescale 2011.03 gcc 4.x for
# PPC, Debian-Wheezy gcc 4.7.2 for x64) don't emit sized deletes at all and
# reject the flag with "unrecognized command line option".
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL 5)
    set(EC_CXX_FLAGS "-fno-sized-deallocation" CACHE STRING "" FORCE)
else()
    set(EC_CXX_FLAGS "" CACHE STRING "" FORCE)
endif()

set(CMAKE_C_FLAGS_DEBUG       "${EC_C_CXX_FLAGS} -g -O0 -DDEBUG"                          CACHE STRING "" FORCE)
set(CMAKE_C_FLAGS_RELEASE     "${EC_C_CXX_FLAGS} -O2"                                     CACHE STRING "" FORCE)
set(CMAKE_C_FLAGS_PROTECTED   "${EC_C_CXX_FLAGS} -O2 -DPROTECTED_VERSION"                 CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_DEBUG     "${EC_C_CXX_FLAGS} ${EC_CXX_FLAGS} -g -O0 -DDEBUG"          CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_RELEASE   "${EC_C_CXX_FLAGS} ${EC_CXX_FLAGS} -O2"                     CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_PROTECTED "${EC_C_CXX_FLAGS} ${EC_CXX_FLAGS} -O2 -DPROTECTED_VERSION" CACHE STRING "" FORCE)

if (EC_OS STREQUAL Linux)
    set(LDFLAGS_APP_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH} -ldl -lrt -lpthread" CACHE STRING "" FORCE)
    set(LDFLAGS_SO_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH} -ldl -lrt -lpthread -Wl,-z,defs" CACHE STRING "" FORCE)
elseif (EC_OS STREQUAL LxWin)
	if (EXISTS ${EC_TOP_LEVEL_DIR}/SDK/Examples)
		# Linux-RTHV
		set(LDFLAGS_APP_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH} -lrtos -ldl -lrt -lpthread" CACHE STRING "" FORCE)
		set(LDFLAGS_SO_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH} -lrtos -ldl -lrt -lpthread -Wl,-z,defs" CACHE STRING "" FORCE)
	else()
		set(LDFLAGS_APP_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH} -lrtos -ldl -lrt -lpthread" CACHE STRING "" FORCE)
		set(LDFLAGS_SO_LIBS "-L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH} -lrtos -ldl -lrt -lpthread -Wl,-z,defs" CACHE STRING "" FORCE)
	endif()
endif()

# ###END OF FILE################################################################################
