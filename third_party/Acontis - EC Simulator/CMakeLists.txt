# ##############################################################################################
# # CMakeLists.txt                                                                             #
# # Copyright                acontis technologies GmbH, Weingarten, Germany                    #
# # Response                 Paul Bussmann                                                     #
# # Description              EC-Master / EC-Monitor / EC-Simulator projects                    #
# ##############################################################################################
# Example usage to build Linux x64 Debug:
# $ cmake -DEC_OS=Linux -DEC_ARCH=x64 -DCMAKE_BUILD_TYPE=Debug .
# $ cmake --build . 
# $   -or-
# $ cmake --build . --target EcMasterDemo
# ##############################################################################################

cmake_minimum_required (VERSION 3.14)
project(EcEmbedded)

# ##############################################################################################
# check parameters
if (NOT DEFINED EC_OS)
  message(FATAL_ERROR "EC_OS not set!")
endif()
if (NOT DEFINED EC_ARCH)
  message(FATAL_ERROR "EC_ARCH not set!")
endif()

# ##############################################################################################
set(EC_BUILD_OUTPUT_DIR ${CMAKE_CURRENT_LIST_DIR} CACHE STRING "")
set(EC_TOP_LEVEL_DIR ${CMAKE_CURRENT_LIST_DIR} CACHE STRING "")

include(${EC_TOP_LEVEL_DIR}/Workspace/cmake/EcSupport.cmake)

if (EC_OS STREQUAL LxWin)
    add_subdirectory("${EC_TOP_LEVEL_DIR}/Workspace/Linux")
    set(EC_LXWIN_ADDITIONAL_SOCKET_SOURCES ${EC_TOP_LEVEL_DIR}/Sources/Common/EcSocketRtosLib.cpp CACHE STRING "")
else()
    add_subdirectory("${EC_TOP_LEVEL_DIR}/Workspace/${EC_OS}")
endif()
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/configurations/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/configurations)
    set(CMAKE_CONFIGURATION_TYPES "${CMAKE_CONFIGURATION_TYPES}" CACHE STRING "Available build configurations" FORCE)
endif()

# ##############################################################################################
# OS-independent settings
set(EC_OS_LAYER_INC SDK/INC/${EC_OS_LAYER_INC_NAME})

if ((EC_OS STREQUAL LxWin) AND (EXISTS ${EC_TOP_LEVEL_DIR}/SDK/Examples))
    # Debug output directories for .exe, .so, .a
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/Debug)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/Debug)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH}/Debug)

    # output directories for .exe, .so, .a
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE})
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/Bin/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE})
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/Linux/${EC_ARCH}/${CMAKE_BUILD_TYPE})
else()
    # Debug output directories for .exe, .so, .a
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/Debug)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/Debug)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/Debug)

    # output directories for .exe, .so, .a
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE})
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/Bin/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE})
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE})
endif()

# ##############################################################################################
# INCLUDE DIRECTORIES
set(EC_INCLUDE_DIRECTORIES ${EC_OS_LAYER_INC} SDK/INC Sources/Common ${EC_INCLUDE_DIRECTORIES_ARCH} ${CMAKE_INCLUDE_DIRECTORIES_ARCH} CACHE STRING "" FORCE)
if (EC_OS STREQUAL LxWin)
    set(EC_INCLUDE_DIRECTORIES ${EC_INCLUDE_DIRECTORIES} ${EC_LXWIN_LIBRARY_DIRECTORY}/SDK/inc ${EC_LXWIN_LIBRARY_DIRECTORY}/SDK/inc/Linux CACHE STRING "" FORCE)
endif()
include_directories(${EC_INCLUDE_DIRECTORIES})

# ##############################################################################################
# LINK DIRECTORIES (ADDITIONAL LIBRARY SEARCH PATHS)
if (NOT DEFINED EC_SDK_LIB_DIR)
    set (EC_SDK_LIB_DIR ${EC_TOP_LEVEL_DIR}/SDK/LIB/${EC_OS_LAYER_INC_NAME} CACHE STRING "")
endif()
set(EC_LINK_DIRECTORIES
    ${EC_SDK_LIB_DIR}/${EC_ARCH}/${CMAKE_BUILD_TYPE}
    ${EC_SDK_LIB_DIR}/${EC_ARCH}
    ${EC_LINK_DIRECTORIES_ARCH}
    ${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}
    ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}
    ${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE}
    ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
    CACHE STRING "" FORCE)
if (EC_OS STREQUAL LxWin)
    set(EC_LINK_DIRECTORIES ${EC_LINK_DIRECTORIES} ${EC_LXWIN_LIBRARY_DIRECTORY}/SDK/lib/Linux/${EC_ARCH} CACHE STRING "" FORCE)
endif()
link_directories(${EC_LINK_DIRECTORIES})

message(STATUS "Building ${EC_OS}/${EC_ARCH}/${CMAKE_BUILD_TYPE} in ${EC_BUILD_OUTPUT_DIR}")
message(STATUS "CMAKE_TOOLCHAIN_FILE:                 ${CMAKE_TOOLCHAIN_FILE}")
message(STATUS "CMAKE_CXX_COMPILER_ID:                ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "CMAKE_CXX_COMPILER_VERSION:           ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "CMAKE_C_COMPILER:                     ${CMAKE_C_COMPILER}")
message(STATUS "CMAKE_CXX_COMPILER:                   ${CMAKE_CXX_COMPILER}")
message(STATUS "CMAKE_BUILD_TYPE:                     ${CMAKE_BUILD_TYPE}")
message(STATUS "CMAKE_CONFIGURATION_TYPES:            ${CMAKE_CONFIGURATION_TYPES}")
message(STATUS "CMAKE_RUNTIME_OUTPUT_DIRECTORY:       ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
message(STATUS "CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG: ${CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG}")
message(STATUS "CMAKE_LIBRARY_OUTPUT_DIRECTORY:       ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}")
message(STATUS "CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG: ${CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG}")
message(STATUS "CMAKE_ARCHIVE_OUTPUT_DIRECTORY:       ${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}")
message(STATUS "CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG: ${CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG}")
message(STATUS "CMAKE_C_FLAGS_DEBUG:                  ${CMAKE_C_FLAGS_DEBUG}")
message(STATUS "CMAKE_C_FLAGS_RELEASE:                ${CMAKE_C_FLAGS_RELEASE}")
message(STATUS "CMAKE_C_FLAGS_PROTECTED:              ${CMAKE_C_FLAGS_PROTECTED}")
message(STATUS "CMAKE_CXX_FLAGS_DEBUG:                ${CMAKE_CXX_FLAGS_DEBUG}")
message(STATUS "CMAKE_CXX_FLAGS_RELEASE:              ${CMAKE_CXX_FLAGS_RELEASE}")
message(STATUS "CMAKE_CXX_FLAGS_PROTECTED:            ${CMAKE_CXX_FLAGS_PROTECTED}")
message(STATUS "LDFLAGS_APP_LIBS:                     ${LDFLAGS_APP_LIBS}")
message(STATUS "LDFLAGS_SO_LIBS:                      ${LDFLAGS_SO_LIBS}")
message(STATUS "EC_OS:                                ${EC_OS}")
message(STATUS "EC_ARCH:                              ${EC_ARCH}")
message(STATUS "EC_TOP_LEVEL_DIR:                     ${EC_TOP_LEVEL_DIR}")
message(STATUS "EC_SDK_LIB_DIR:                       ${EC_SDK_LIB_DIR}")
message(STATUS "EC_OS_LAYER_INC:                      ${EC_OS_LAYER_INC}")
message(STATUS "EC_INCLUDE_DIRECTORIES:               ${EC_INCLUDE_DIRECTORIES}")
message(STATUS "EC_LINK_DIRECTORIES:                  ${EC_LINK_DIRECTORIES}")
message(STATUS "EC_BUILD_OUTPUT_DIR:                  ${EC_BUILD_OUTPUT_DIR}")
message(STATUS "EC_WIBU_DEVKIT_DIR:                   ${EC_WIBU_DEVKIT_DIR}")
message(STATUS "EC_ECLIPSE_PAHO_DIR:                  ${EC_ECLIPSE_PAHO_DIR}")
message(STATUS "EC_DPDK_DIR:                          ${EC_DPDK_DIR}")
message(STATUS "EC_DPDK_ENETC4_DIR:                   ${EC_DPDK_ENETC4_DIR}")
message(STATUS "EC_CPPUTEST_DIR:                      ${EC_CPPUTEST_DIR}")
message(STATUS "EC_CPPUTEST_LIB_DIR:                  ${EC_CPPUTEST_LIB_DIR}")
message(STATUS "EC_FMI_LIBRARY_DIRECTORY:             ${EC_FMI_LIBRARY_DIRECTORY}")
message(STATUS "EC_LXWIN_LIBRARY_DIRECTORY:           ${EC_LXWIN_LIBRARY_DIRECTORY}")

# ##############################################################################################
# Third Party Libraries

# mdf4lib
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/mdf4lib/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/mdf4lib)
endif()

# ##############################################################################################
# Core Libraries

# EC-Master Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMaster/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMaster)
endif()

# EC-Monitor Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMonitor/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMonitor)
endif()

# EC-Simulator Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulator/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulator)
endif()

# #################### Feature packs ###########################################################
# EC-DAQ Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcDaq/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcDaq)
endif()

# EC-EAP Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcEap/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcEap)
endif()

# EC-Motion-Advanced Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMotionAdvanced/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMotionAdvanced)
endif()

# ##############################################################################################
# RAS Libraries

# EC-Master RAS Client Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterRasClient/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterRasClient)
endif()
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterRasClientTls/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterRasClientTls)
endif()

# EC-Master RAS Server Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterRasServer/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterRasServer)
endif()
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterRasServerTls/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterRasServerTls)
endif()

# EC-Monitor RAS Server Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMonitorRasServer/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMonitorRasServer)
endif()

# EC-Simulator RAS Client Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorRasClient/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorRasClient)
endif()

# EC-Simulator RAS Server Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorRasServer/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorRasServer)
endif()

# EC-Master MQTT Server Core Library
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterMqttServer/CMakeLists.txt") 
    add_subdirectory(Workspace/cmake/EcMasterMqttServer)
endif()

# ##############################################################################################
# Link Layer

# emllAlteraTSE
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllAlteraTSE/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllAlteraTSE)
endif()

# emllBcmGenet
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllBcmGenet/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllBcmGenet)
endif()

# emllBcmNetXtreme
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllBcmNetXtreme/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllBcmNetXtreme)
endif()

# emllCCAT
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllCCAT/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllCCAT)
endif()

# emllCPSW
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllCPSW/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllCPSW)
endif()

# emllCPSWG
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllCPSWG/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllCPSWG)
endif()

# emllDpdk
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllDpdk/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllDpdk)
endif()

# emllDW3504
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllDW3504/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllDW3504)
endif()

# emllDwXgmac
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllDwXgmac/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllDwXgmac)
endif()

# emllEG20T
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllEG20T/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllEG20T)
endif()

# emllEom
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllEom/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllEom)
endif()

# emllETSEC
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllETSEC/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllETSEC)
endif()

# emllFslEnetc
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllFslEnetc/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllFslEnetc)
endif()

# emllFslFec
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllFslFec/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllFslFec)
endif()

# emllGEM
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllGEM/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllGEM)
endif()

# emllI8254x
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllI8254x/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllI8254x)
endif()

# emllI8255x
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllI8255x/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllI8255x)
endif()

# emllICSS
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllICSS/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllICSS)
endif()

# emllIntelGbe
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllIntelGbe/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllIntelGbe)
endif()

# emllLAN743x
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllLAN743x/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllLAN743x)
endif()

# emllMultiplier
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllMultiplier/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllMultiplier)
endif()

# emllR6040
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllR6040/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllR6040)
endif()

# emllRemote
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllRemote/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllRemote)
endif()

# emllRTL8139
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllRTL8139/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllRTL8139)
endif()

# emllRTL8169
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllRTL8169/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllRTL8169)
endif()

# # emllSHEth
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllSHEth/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllSHEth)
endif()

# emllSimulator
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllSimulator/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllSimulator)
endif()

# emllSockRaw
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllSockRaw/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllSockRaw)
endif()

# emllSockXdp
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllSockXdp/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllSockXdp)
endif()

# emllVlan
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/emllVlan/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/emllVlan)
endif()

# ##############################################################################################
# Wrappers

# EcWrapper
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcWrapper/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcWrapper)
endif()

# ##############################################################################################
# Applications

# EcEapDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcEapDemo/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcEapDemo)
endif()

# EcEoeGateway
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcEoeGateway/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcEoeGateway)
endif()

# EcMasterDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemo/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemo)
endif()

# EcMasterDemoC
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoC/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoC)
endif()

# EcMasterDemoDaq
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoDaq/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoDaq)
endif()

# EcMasterDemoDc
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoDc/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoDc)
endif()

# EcMasterDemoEom
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoEom/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoEom)
endif()

# EcMasterDemoMasterRed
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoMasterRed/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoMasterRed)
endif()

# EcMasterDemoMinimal
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoMinimal/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoMinimal)
endif()

# EcMasterDemoMotionAdvanced
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoMotionAdvanced/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoMotionAdvanced)
endif()

# EcMasterDemoMqttServer
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoMqttServer/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoMqttServer)
endif()

# EcMasterDemoMulti
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoMulti/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoMulti)
endif()

# EcMasterDemoRasClient
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoRasClient/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoRasClient)
endif()

# EcMasterDemoRasClientTls
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoRasClientTls/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoRasClientTls)
endif()

# EcMasterDemoRasServer
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoRasServer/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoRasServer)
endif()

# EcMasterDemoRasServerTls
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoRasServerTls/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoRasServerTls)
endif()

# EcMasterDemoSyncSm
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMasterDemoSyncSm/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMasterDemoSyncSm)
endif()

# EcMonitorDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMonitorDemo/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMonitorDemo)
endif()

# EcMonitorDemoMqtt
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcMonitorDemoMqtt/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcMonitorDemoMqtt)
endif()

# EcSimulatorFmi
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorFmi/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorFmi)
endif()

# EcSimulatorHilDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorHilDemo/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorHilDemo)
endif()

# EcSimulatorHilDemoMotion
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorHilDemoMotion/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorHilDemoMotion)
endif()

# EcSimulatorHilDemoFmi
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorHilDemoFmi/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorHilDemoFmi)
endif()

# EcSimulatorSilDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorSilDemo/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorSilDemo)
endif()

# EcSimulatorSilDemoFmi
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorSilDemoFmi/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/EcSimulatorSilDemoFmi)
endif()

# EcSimulatorSilDemoMotion
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcSimulatorSilDemoMotion/CMakeLists.txt" AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Examples/EcMasterDemoMotionAdvanced")
    add_subdirectory(Workspace/cmake/EcSimulatorSilDemoMotion)
endif()

# EcWinDemo
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/EcWinDemo/CMakeLists.txt" AND EC_OS STREQUAL LxWin)
    add_subdirectory(Workspace/cmake/EcWinDemo)
endif()

# EC-Master / EC-Monitor / EC-Simulator Tests
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/Workspace/cmake/Tests/CMakeLists.txt")
    add_subdirectory(Workspace/cmake/Tests)
endif()

# ###END OF FILE################################################################################
