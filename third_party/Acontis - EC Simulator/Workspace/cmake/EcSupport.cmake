# ##############################################################################################
# # Workspace/cmake/EcSupport.cmake                                                            #
# # Copyright                acontis technologies GmbH, Weingarten, Germany                    #
# # Description              Declarative OS/ARCH support matrix for components                 #
# ##############################################################################################
#
# Usage in a component's CMakeLists.txt:
#
#   ec_project_supports_arch(_supported_ARCH
#       Linux    ALL                                  # all archs supported on Linux
#       LxWin    ALL WITHOUT MUSL                     # all archs except *-musl variants
#       Windows  x86 x64                              # only listed archs supported
#       QNX      armv7-vfp-eabihf)                    # OSes not listed -> unsupported
#   ec_project_supports_build_types(_supported_BUILD_TYPE Eval Protected)
#   if (NOT _supported_ARCH OR NOT _supported_BUILD_TYPE)
#       return()
#   endif()
#
# Per-OS spec: <ALL | arch...> [WITHOUT <arch | MUSL>...]
#   - ALL                matches every arch
#   - <arch>...          matches only the listed archs
#   - WITHOUT MUSL       excludes any arch whose name ends in -musl
#   - WITHOUT <arch>...  excludes the listed archs
#
# Sets <out_var> to TRUE if the (EC_OS, EC_ARCH) pair is in the declared matrix, else FALSE.
# Keep keyword names in MULTI_VALUE in sync with the OS names used by the build.

function(ec_project_supports_arch out_var)
    cmake_parse_arguments(A "" "" "Linux;LxWin;Windows;QNX;Xenomai;Zephyr" ${ARGN})

    set(_archs "${A_${EC_OS}}")

    if (NOT _archs)
        set(${out_var} FALSE PARENT_SCOPE)            # OS not declared by component
        return()
    endif()

    # Split optional "WITHOUT <exclusions...>" tail
    set(_includes "")
    set(_excludes "")
    set(_in_excludes FALSE)
    foreach(_tok IN LISTS _archs)
        if (_tok STREQUAL "WITHOUT")
            set(_in_excludes TRUE)
        elseif (_in_excludes)
            list(APPEND _excludes "${_tok}")
        else()
            list(APPEND _includes "${_tok}")
        endif()
    endforeach()

    # Apply exclusions first (MUSL token matches any *-musl arch)
    if ("MUSL" IN_LIST _excludes AND EC_ARCH MATCHES "-musl$")
        set(${out_var} FALSE PARENT_SCOPE)
        return()
    endif()
    if (EC_ARCH IN_LIST _excludes)
        set(${out_var} FALSE PARENT_SCOPE)
        return()
    endif()

    if (_includes STREQUAL "ALL")
        set(${out_var} TRUE  PARENT_SCOPE)
    elseif (EC_ARCH IN_LIST _includes)
        set(${out_var} TRUE  PARENT_SCOPE)
    else()
        set(${out_var} FALSE PARENT_SCOPE)
    endif()
endfunction()

# Build-type gate, companion to ec_project_supports_arch above.
#
# Release and Debug are ALWAYS supported (baseline). Pass any ADDITIONAL build
# types the component supports; Sets <out_var> TRUE if the current
# CMAKE_BUILD_TYPE is allowed, else FALSE.
#
#   ec_project_supports_build_types(_supported_BUILD_TYPE Protected Eval)   # + Release/Debug baseline
#   ec_project_supports_build_types(_supported_BUILD_TYPE)                  # Release/Debug only
#   if (NOT _supported_BUILD_TYPE)
#       return()
#   endif()
function(ec_project_supports_build_types out_var)
    if (CMAKE_BUILD_TYPE STREQUAL "Release" OR CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(${out_var} TRUE  PARENT_SCOPE)
    elseif (CMAKE_BUILD_TYPE IN_LIST ARGN)
        set(${out_var} TRUE  PARENT_SCOPE)
    else()
        set(${out_var} FALSE PARENT_SCOPE)
    endif()
endfunction()

# ###END OF FILE################################################################################
