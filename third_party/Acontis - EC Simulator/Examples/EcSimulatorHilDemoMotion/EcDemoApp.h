/** ---------------------------------------------------------------------------
 * \file        EcDemoApp.h
 * \brief       Application specific settings for EC-Master demo
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#ifndef INC_ECDEMOAPP_H
#define INC_ECDEMOAPP_H 1

/*-LOGGING-------------------------------------------------------------------*/
#ifndef pEcLogParms
#define pEcLogParms (&(pAppContext->LogParms))
#endif

#ifndef EC_SIMULATOR_DS402
#define EC_SIMULATOR_DS402
#endif

#define INCLUDE_EC_SIMULATOR
#define INCLUDE_EC_SIMULATOR_HIL

/*-INCLUDES------------------------------------------------------------------*/
#include "EcSimulator.h"
#include "EcDemoPlatform.h"
#include "EcLogging.h"
#include "EcDemoParms.h"
#include "EcNotification.h"
#include "EcSelectLinkLayer.h"
#include "EcSlaveInfo.h"
#include "EcDemoTimingTaskPlatform.h"

/*-DEFINES-------------------------------------------------------------------*/
#define EC_DEMO_APP_NAME (EC_T_CHAR*)"EcSimulatorHilDemoMotion"

/* the RAS server is necessary to support the EC-Engineer or other remote applications */
#if (!defined INCLUDE_RAS_SERVER) && (defined EC_SOCKET_SUPPORTED)
#define INCLUDE_RAS_SERVER
#endif

#if (defined INCLUDE_RAS_SERVER)
#include "EcSimulatorRasServer.h"
#define EC_RAS_MAX_WATCHDOG_TIMEOUT    10000
#define EC_RAS_CYCLE_TIME              2
#endif

#ifndef ecatGetText
#define ecatGetText(dwTextId)       esGetText(0, (dwTextId))
#define ecatGetNotifyText(dwTextId) esGetNotifyText(0, (dwTextId))
#endif

#define PRINT_PERF_MEAS() ((EC_NULL != pEcLogContext)?((CAtEmLogging*)pEcLogContext)->PrintPerfMeas(0, pAppContext->dwInstanceId, pEcLogContext) : 0)

/*-FUNCTION DECLARATIONS-----------------------------------------------------*/
EC_T_DWORD EcDemoApp(T_EC_DEMO_APP_CONTEXT* pAppContext);

#endif /* INC_ECDEMOAPP_H */

/*-END OF SOURCE FILE--------------------------------------------------------*/
