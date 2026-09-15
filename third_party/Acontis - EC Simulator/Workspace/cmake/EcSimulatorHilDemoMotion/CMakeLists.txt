# ##############################################################################################
# # Workspace/cmake/EcSimulatorHilDemoMotion/CMakeLists.txt                                    #
# # Copyright                acontis technologies GmbH, Weingarten, Germany                    #
# # Response                 Paul Bussmann                                                     #
# # Description              EcSimulatorHilDemoMotion                                          #
# ##############################################################################################

cmake_minimum_required (VERSION 3.14)

ec_project_supports_arch(_supported_ARCH
    Linux ALL WITHOUT MUSL
    LxWin x86 x64
    Windows ALL)
ec_project_supports_build_types(_supported_BUILD_TYPE)
if (NOT _supported_ARCH OR NOT _supported_BUILD_TYPE)
    return()
endif()

# EcSimulatorHilDemoMotion
project(EcSimulatorHilDemoMotion LANGUAGES C CXX)
set(ECSIMULATORHILDEMOMOTION_SOURCES
    ${EC_TOP_LEVEL_DIR}/Examples/EcSimulatorHilDemoMotion/EcDemoApp.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcDemoParms.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcDemoTimingTask.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcLogging.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcNotification.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcSelectLinkLayer.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcSimulatorDs402.cpp
    ${EC_TOP_LEVEL_DIR}/Examples/Common/EcSlaveInfo.cpp
    ${EC_TOP_LEVEL_DIR}/Sources/Common/EcThread.cpp
    ${EC_TOP_LEVEL_DIR}/Sources/Common/EcTimer.cpp
    ${EC_DEMO_OS_LAYER_TIMING_TASK_SOURCES}
    ${EC_DEMO_OS_LAYER_SOURCES})
add_executable(EcSimulatorHilDemoMotion ${ECSIMULATORHILDEMOMOTION_SOURCES})
target_include_directories(EcSimulatorHilDemoMotion PRIVATE ${EC_TOP_LEVEL_DIR}/Examples/EcSimulatorHilDemoMotion ${EC_DEMO_OS_LAYER_INC} ${EC_TOP_LEVEL_DIR}/Examples/Common)
target_compile_definitions(EcSimulatorHilDemoMotion PRIVATE INCLUDE_PCAP_RECORDER EC_SIMULATOR_DS402)
if ((EC_OS STREQUAL Linux) OR (EC_OS STREQUAL LxWin))
    target_link_libraries(EcSimulatorHilDemoMotion -L${CMAKE_ARCHIVE_OUTPUT_DIRECTORY} -L${EC_BUILD_OUTPUT_DIR}/SDK/LIB/${EC_OS}/${EC_ARCH} -L${CMAKE_LIBRARY_OUTPUT_DIRECTORY} -lEcSimulatorRasServer -lEcSimulator ${LDFLAGS_APP_LIBS})
elseif (EC_OS STREQUAL Windows)
    target_link_libraries(EcSimulatorHilDemoMotion EcSimulatorRasServer.lib EcSimulator.lib setupapi.lib ws2_32.lib winmm.lib)
endif()
if (EXISTS "${EC_TOP_LEVEL_DIR}/Workspace/cmake/EcSimulator/CMakeLists.txt")
    add_dependencies(EcSimulatorHilDemoMotion EcSimulator)
endif()
if (EXISTS "${EC_TOP_LEVEL_DIR}/Workspace/cmake/EcSimulatorRasServer/CMakeLists.txt")
    add_dependencies(EcSimulatorHilDemoMotion EcSimulatorRasServer)
endif()

# ###END OF FILE################################################################################
