/** ---------------------------------------------------------------------------
 * \file
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#ifndef INC_ECSIMULATORRASSERVER
#define INC_ECSIMULATORRASSERVER

/*-INCLUDES------------------------------------------------------------------*/
#ifndef INC_ECOS
#include "EcOs.h"
#endif
#ifndef INC_ECRASTYPE
#include "EcRasType.h"
#endif

/*-FUNCTION DECLARATION------------------------------------------------------*/
#ifdef __cplusplus
extern "C"
{
#endif

/* EC-Simulator RAS Server API */
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvGetVersion(EC_T_VOID );
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvStart(const EC_T_RAS_SERVER_PARMS* pParms, EC_T_PVOID* ppHandle);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvStop(EC_T_PVOID pvHandle, EC_T_DWORD dwTimeout);
EC_API const EC_T_CHAR* EC_API_FNCALL esRasErrorText(EC_T_DWORD dwError);
EC_API const EC_T_CHAR* EC_API_FNCALL esRasEventText(EC_T_DWORD dwEvent);

#if (defined INCLUDE_RAS_TRACESUPPORT)
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvTraceEnable(EC_T_BOOL bEnable);
#endif

EC_API EC_T_DWORD EC_API_FNCALL esRasSrvSetAccessLevel(EC_T_PVOID pvHandle, EC_T_DWORD dwAccessLevel);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvGetAccessLevel(EC_T_PVOID pvHandle, EC_T_DWORD* pdwAccessLevel);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvConfigAccessLevel(EC_T_PVOID pvHandle, const EC_T_RAS_SPOCCFG* poConfigData, EC_T_DWORD dwCnt);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvSetAccessControl(EC_T_PVOID pvHandle, EC_T_BOOL bActive);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvSetCallAccessLevel(
    EC_T_PVOID      pvHandle        /**< [in]   Handle to previously started Server */
    , EC_T_DWORD    dwOrdinal       /**< [in]   Function call ID */
    , EC_T_DWORD    dwIndex         /**< [in]   Function call index */
    , EC_T_DWORD    dwSubIndex      /**< [in]   Function call subindex */
    , EC_T_DWORD    dwAccessLevel   /**< [in]   New Access level */
    );

EC_API EC_T_DWORD EC_API_FNCALL esRasGetMemoryUsage(EC_T_PVOID pvHandle, EC_T_DWORD* pdwCurrentUsage, EC_T_DWORD* pdwMaxUsage);
EC_API EC_T_DWORD EC_API_FNCALL esRasSrvSetLogParms(EC_T_PVOID pvHandle, const EC_T_LOG_PARMS* pLogParms);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* INC_ECSIMULATORRASSERVER */

/*-END OF SOURCE FILE--------------------------------------------------------*/
