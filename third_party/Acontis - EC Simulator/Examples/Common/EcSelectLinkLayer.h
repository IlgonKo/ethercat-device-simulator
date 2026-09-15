/** ---------------------------------------------------------------------------
 * \file        EcSelectLinkLayer.h
 * \brief       EC-Master link layer selection
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#ifndef INC_SELECTLINKAYER
#define INC_SELECTLINKAYER 1

/*-INCLUDES------------------------------------------------------------------*/
#if (defined INCLUDE_DUMMY)
#include "EcLinkDummy.h"
#endif

#include "stdio.h"
#include "stdlib.h"

/*-DEFINES-------------------------------------------------------------------*/
#if (!defined EXCLUDE_EMLL_ALL)

#if (EC_OS == EC_OS_CMSIS_RTOS)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #define INCLUDE_EMLLCMSISETH
#elif (EC_OS == EC_OS_ECOS)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #ifndef EXCLUDE_EMLLANTAIOS
 #define INCLUDE_EMLLANTAIOS
 #endif
#elif (EC_OS == EC_OS_FREERTOS)
 #define INCLUDE_EMLLTIENETCPSWG
 #define INCLUDE_EMLLTIENETICSSG
 #define INCLUDE_EMLL_SOC_NXP
 #define INCLUDE_EMLL_SOC_XILINX
#elif (EC_OS == EC_OS_INTEGRITY)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #define INCLUDE_EMLLI8254X
 #define INCLUDE_EMLLINTELGBE
#elif (EC_OS == EC_OS_INTIME)
 #define INCLUDE_EMLLHPE
 #define INCLUDE_EMLL_PCI_ALL
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLBCMNETXTREME
 #define INCLUDE_EMLLBCMNETXTREME
 #endif
#elif (EC_OS == EC_OS_LINUX)
 #define INCLUDE_EMLL_PCI_ALL
 #define INCLUDE_EMLL_SOC_ALL
 #ifndef EXCLUDE_EMLLMULTIPLIER
 #define INCLUDE_EMLLMULTIPLIER
 #endif
 #ifndef EXCLUDE_EMLLLAN743X
 #define INCLUDE_EMLLLAN743X
 #endif
 #if (EC_ARCH == EC_ARCH_X64)
 #ifndef EXCLUDE_EMLLALTERATSE
 #define INCLUDE_EMLLALTERATSE
 #endif
 #endif
 #ifndef EXCLUDE_EMLLEOM
 #define INCLUDE_EMLLEOM
 #endif
 #ifndef EXCLUDE_EMLLREMOTE
 #define INCLUDE_EMLLREMOTE
 #endif
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLSOCKRAW
 #define INCLUDE_EMLLSOCKRAW
 #endif
 #if (EC_ARCH == EC_ARCH_X64)
 #ifndef EXCLUDE_EMLLSOCKXDP
 #define INCLUDE_EMLLSOCKXDP
 #endif
 #endif
 #if (EC_ARCH == EC_ARCH_ARM64) || (EC_ARCH == EC_ARCH_X64)
 #ifndef EXCLUDE_EMLLDPDK
 #define INCLUDE_EMLLDPDK
 #endif
 #endif
 #ifndef EXCLUDE_EMLLBCMNETXTREME
 #define INCLUDE_EMLLBCMNETXTREME
 #endif
 #ifndef EXCLUDE_EMLLVLAN
 #define INCLUDE_EMLLVLAN
 #endif
#elif (EC_OS == EC_OS_MACOS)
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLWINPCAP
 #define INCLUDE_EMLLWINPCAP
 #endif
#elif (EC_OS == EC_OS_QNX)
 #define INCLUDE_EMLL_PCI_ALL
 #define INCLUDE_EMLL_SOC_ALL
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLBCMNETXTREME
 #define INCLUDE_EMLLBCMNETXTREME
 #endif
 #ifndef EXCLUDE_EMLLBPF
 #define INCLUDE_EMLLBPF
 #endif
#elif (EC_OS == EC_OS_SYLIXOS)
 #ifndef EXCLUDE_EMLLDW3504
 #define INCLUDE_EMLLDW3504
 #endif
#elif (EC_OS == EC_OS_RTOS32)
 #define EXCLUDE_EMLLDW3504
 #if !(EC_DLL)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #endif
 #define INCLUDE_EMLL_PCI_ALL
 #ifndef EXCLUDE_EMLLMULTIPLIER
 #define INCLUDE_EMLLMULTIPLIER
 #endif
#elif (EC_OS == EC_OS_RTX)
 #define INCLUDE_EMLL_PCI_ALL
 #ifndef EXCLUDE_EMLLBCMNETXTREME
 #define INCLUDE_EMLLBCMNETXTREME
 #endif
#elif (EC_OS == EC_OS_RX72)
 #ifndef EXCLUDE_EMLL_SOC_RENESAS
 #define INCLUDE_EMLL_SOC_RENESAS
 #endif
#elif (EC_OS == EC_OS_TIRTOS)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 /* #define INCLUDE_EMLL_SOC_TI */ /* currently set in specific demo project file */
#elif (EC_OS == EC_OS_UC3)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #if (defined SOC_RZT1)
  #define INCLUDE_EMLLRZT1
 #elif (defined SOC_STM32H7)
  #define INCLUDE_EMLLCMSISETH
 #elif (defined SOC_IMX8)
  #define INCLUDE_EMLL_SOC_NXP
 #elif (defined SOC_RZN2H)
  #define INCLUDE_EMLL_SOC_SYNOPSYS
 #else
  #define INCLUDE_EMLL_SOC_SYNOPSYS
 #endif
#elif (EC_OS == EC_OS_UCOS)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #define INCLUDE_EMLL_SOC_NXP
#elif (EC_OS == EC_OS_VXWORKS)
 #define INCLUDE_EMLL_PCI_ALL
 #define INCLUDE_EMLL_SOC_ALL
 #define INCLUDE_EMLLSNARF
 #if ((EC_OS_VERSION == 690) || (EC_OS_VERSION == 700))
  #ifndef EXCLUDE_EMLLSIMULATOR
  #define INCLUDE_EMLLSIMULATOR
  #endif
  #ifndef EXCLUDE_EMLLMULTIPLIER
  #define INCLUDE_EMLLMULTIPLIER
  #endif
 #endif
#elif (EC_OS == EC_OS_WINCE)
 #define INCLUDE_EMLL_PCI_ALL
  #ifndef EXCLUDE_EMLLR6040
 #define INCLUDE_EMLLR6040
 #endif
#elif (EC_OS == EC_OS_WINDOWS)
 #define EXCLUDE_EMLLDW3504
 #define EXCLUDE_EMLLEG20T
 #define EXCLUDE_EMLLI8255X
 #define EXCLUDE_EMLLRTL8139
 #define INCLUDE_EMLL_PCI_ALL
 #ifndef EXCLUDE_EMLLNDIS
 #define INCLUDE_EMLLNDIS
 #endif
 #ifndef EXCLUDE_EMLLREMOTE
 #define INCLUDE_EMLLREMOTE
 #endif
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLTAP
 #define INCLUDE_EMLLTAP
 #endif
 #ifndef EXCLUDE_EMLLMULTIPLIER
 #define INCLUDE_EMLLMULTIPLIER
 #endif
 #ifndef EXCLUDE_EMLLEOM
 #define INCLUDE_EMLLEOM
 #endif
 #ifndef EXCLUDE_EMLLBCMNETXTREME
 #define INCLUDE_EMLLBCMNETXTREME
 #endif
 #ifndef EXCLUDE_EMLLVLAN
 #define INCLUDE_EMLLVLAN
 #endif
#elif (EC_OS == EC_OS_XENOMAI)
 #define INCLUDE_EMLL_PCI_ALL
 #define INCLUDE_EMLL_SOC_ALL
 #ifndef EXCLUDE_EMLLSOCKRAW
 #define INCLUDE_EMLLSOCKRAW
 #endif
 #ifndef EXCLUDE_EMLLSIMULATOR
 #define INCLUDE_EMLLSIMULATOR
 #endif
 #ifndef EXCLUDE_EMLLMULTIPLIER
 #define INCLUDE_EMLLMULTIPLIER
 #endif
#elif (EC_OS == EC_OS_XILINX_STANDALONE)
 #define INCLUDE_EMLL_SOC_XILINX
#elif (EC_OS == EC_OS_ZEPHYR)
 #define INCLUDE_EMLL_STATIC_LIBRARY
 #define INCLUDE_EMLLI8254X
 #define INCLUDE_EMLLINTELGBE
 #define INCLUDE_EMLLRTL8169
#endif

#if (defined INCLUDE_EMLL_PCI_ALL)
 #if (EC_ARCH == EC_ARCH_X86) || (EC_ARCH == EC_ARCH_X64) || (EC_ARCH == EC_ARCH_ARM) || (EC_ARCH == EC_ARCH_ARM64)
 #define INCLUDE_EMLL_PCI_BECKHOFF
 #endif
 #define INCLUDE_EMLL_PCI_INTEL
 #define INCLUDE_EMLL_PCI_REALTEK
 #if (EC_ARCH == EC_ARCH_X86) || (EC_ARCH == EC_ARCH_X64) || (EC_ARCH == EC_ARCH_ARM) || (EC_ARCH == EC_ARCH_ARM64)
 #ifndef EXCLUDE_EMLLDW3504
 #define INCLUDE_EMLLDW3504
 #endif
 #endif
#endif
#if (defined INCLUDE_EMLL_PCI_BECKHOFF)
 #ifndef EXCLUDE_EMLLCCAT
 #define INCLUDE_EMLLCCAT
 #endif
#endif
#if (defined INCLUDE_EMLL_PCI_INTEL)
 #if (EC_ARCH == EC_ARCH_X86)
 #ifndef EXCLUDE_EMLLEG20T
 #define INCLUDE_EMLLEG20T
 #endif
 #endif
 #ifndef EXCLUDE_EMLLI8254X
 #define INCLUDE_EMLLI8254X
 #endif
 #ifndef EXCLUDE_EMLLINTELGBE
 #define INCLUDE_EMLLINTELGBE
 #endif
 #if (EC_ARCH == EC_ARCH_X86)
 #ifndef EXCLUDE_EMLLI8255X
 #define INCLUDE_EMLLI8255X
 #endif
 #endif
#endif /* INCLUDE_EMLL_PCI_INTEL */

#if (defined INCLUDE_EMLL_PCI_REALTEK)
 #ifndef EXCLUDE_EMLLRTL8169
 #define INCLUDE_EMLLRTL8169
 #endif
 #if (EC_ARCH == EC_ARCH_X86)
 #ifndef EXCLUDE_EMLLRTL8139
 #define INCLUDE_EMLLRTL8139
 #endif
 #endif
#endif

#if (defined INCLUDE_EMLL_SOC_ALL)
 #define INCLUDE_EMLL_SOC_NXP
 #define INCLUDE_EMLL_SOC_SYNOPSYS
 #define INCLUDE_EMLL_SOC_TI
 #define INCLUDE_EMLL_SOC_XILINX
 #define INCLUDE_EMLL_SOC_BROADCOM
 #define INCLUDE_EMLL_SOC_RENESAS
#endif

#if (EC_ARCH == EC_ARCH_ARM)
 #if (defined INCLUDE_EMLL_SOC_BROADCOM)
  #ifndef EXCLUDE_EMLLBCMGENET
  #define INCLUDE_EMLLBCMGENET
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_NXP)
  #ifndef EXCLUDE_EMLLFSLFEC
  #define INCLUDE_EMLLFSLFEC
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_SYNOPSYS)
  #ifndef EXCLUDE_EMLLDW3504
  #define INCLUDE_EMLLDW3504
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_RENESAS)
  #ifndef EXCLUDE_EMLLSHETH
  #define INCLUDE_EMLLSHETH
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_TI)
  #ifndef EXCLUDE_EMLLCPSW
  #define INCLUDE_EMLLCPSW
  #endif
  #ifndef EXCLUDE_EMLLICSS
  #define INCLUDE_EMLLICSS
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_XILINX)
  #ifndef EXCLUDE_EMLLGEM
  #define INCLUDE_EMLLGEM
  #endif
 #endif
#endif

#if (EC_ARCH == EC_ARCH_ARM64)
 #if (defined INCLUDE_EMLL_SOC_BROADCOM)
  #ifndef EXCLUDE_EMLLBCMGENET
  #define INCLUDE_EMLLBCMGENET
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_NXP)
  #ifndef EXCLUDE_EMLLFSLFEC
  #define INCLUDE_EMLLFSLFEC
  #endif
  #ifndef EXCLUDE_EMLLFSLENETC
  #define INCLUDE_EMLLFSLENETC
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_XILINX)
  #ifndef EXCLUDE_EMLLGEM
  #define INCLUDE_EMLLGEM
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_TI)
  #ifndef EXCLUDE_EMLLCPSWG
  #define INCLUDE_EMLLCPSWG
  #endif
 #endif
 #if (defined INCLUDE_EMLL_SOC_SYNOPSYS)
  #ifndef EXCLUDE_EMLLDW3504
  #define INCLUDE_EMLLDW3504
  #endif
  #ifndef EXCLUDE_EMLLDWXGMAC
  #define INCLUDE_EMLLDWXGMAC
  #endif
 #endif
#endif

#if (EC_ARCH == EC_ARCH_PPC)
 #if (defined INCLUDE_EMLL_SOC_NXP)
  #ifndef EXCLUDE_EMLLETSEC
  #define INCLUDE_EMLLETSEC
  #endif
 #endif
#endif

#if (EC_ARCH == EC_ARCH_RX)
 #if (defined INCLUDE_EMLL_SOC_RENESAS)
  #ifndef EXCLUDE_EMLLSHETH
  #define INCLUDE_EMLLSHETH
  #endif
 #endif
#endif

#if (EC_ARCH == EC_ARCH_RISCV64)
 #if (defined INCLUDE_EMLL_SOC_XILINX)
  #ifndef EXCLUDE_EMLLGEM
  #define INCLUDE_EMLLGEM
  #endif
 #endif
#endif

#endif /* EXCLUDE_EMLL_ALL */

/*-FUNCTION DECLARATION------------------------------------------------------*/
EC_T_CHAR* GetNextWord(EC_T_CHAR **ppCmdLine, EC_T_CHAR *pStorage);

EC_T_DWORD CreateLinkParmsFromCmdLine(T_EC_DEMO_APP_CONTEXT* pAppContext, EC_T_CHAR** ptcWord, EC_T_CHAR** lpCmdLine, EC_T_CHAR* tcStorage, EC_T_BOOL* pbGetNextWord,
                                      EC_T_LINK_PARMS** ppLinkParms);
/* legacy */
#if (defined __cplusplus)
static EC_INLINESTART EC_T_DWORD CreateLinkParmsFromCmdLine(EC_T_CHAR** ptcWord, EC_T_CHAR** lpCmdLine, EC_T_CHAR* tcStorage, EC_T_BOOL* pbGetNextWord, EC_T_LINK_PARMS** ppLinkParms)
{
    return CreateLinkParmsFromCmdLine(EC_NULL, ptcWord, lpCmdLine, tcStorage, pbGetNextWord, ppLinkParms);
} EC_INLINESTOP
#endif

EC_T_VOID  FreeLinkParms(EC_T_LINK_PARMS* pLinkParms);

EC_T_BOOL  ParseIpAddress(EC_T_CHAR* ptcWord, EC_T_BYTE* pbyIpAddress);

#if (defined INCLUDE_EMLL_STATIC_LIBRARY)
EC_PF_LLREGISTER DemoGetLinkLayerRegFunc(const EC_T_CHAR* szDriverIdent, const EC_T_CHAR* szLoadPath);
#endif
#endif /* INC_SELECTLINKAYER */

/*-END OF SOURCE FILE--------------------------------------------------------*/
