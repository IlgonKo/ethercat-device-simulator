/** ---------------------------------------------------------------------------
 * \file        EcDemoApp.cpp
 * \brief       EC-Simulator demo application
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

/*-INCLUDES------------------------------------------------------------------*/
#include "EcDemoApp.h"
#include "EcSimulatorDs402.h"

/*-DEFINES-------------------------------------------------------------------*/
#define PERF_myAppWorkpd       0
#define MAX_JOB_NUM            1

/*-LOCAL VARIABLES-----------------------------------------------------------*/
static EC_T_PERF_MEAS_INFO_PARMS S_aPerfMeasInfos[MAX_JOB_NUM] =
{
    {"myAppWorkPd                    ", 0}
};

/*-FUNCTION DECLARATIONS-----------------------------------------------------*/
static EC_T_VOID  EcJobTask(EC_T_VOID* pvAppContext);
#if (defined INCLUDE_RAS_SERVER)
static EC_T_DWORD RasNotifyCallback(EC_T_DWORD dwCode, EC_T_NOTIFYPARMS* pParms);
#endif

/*-MYAPP---------------------------------------------------------------------*/
typedef struct _T_MY_APP_DESC
{
    EC_T_DWORD dwFlashPdBitSize; /* Size of process data memory */
    EC_T_DWORD dwFlashPdBitOffs; /* Process data offset of data */
    EC_T_DWORD dwFlashTimer;        /* flash timer [ns] */
    EC_T_DWORD dwFlashInterval;
    EC_T_BYTE  byFlashVal;          /* flash pattern */
    EC_T_BYTE* pbyFlashBuf;         /* flash buffer */
    EC_T_DWORD dwFlashBufSize;      /* flash buffer size */
} T_MY_APP_DESC;
static EC_T_DWORD myAppInit(T_EC_DEMO_APP_CONTEXT* pAppContext);
static EC_T_DWORD myAppPrepare(T_EC_DEMO_APP_CONTEXT* pAppContext);
static EC_T_DWORD myAppSetup(T_EC_DEMO_APP_CONTEXT* pAppContext);
static EC_T_DWORD myAppWorkpd(T_EC_DEMO_APP_CONTEXT* pAppContext);
static EC_T_DWORD myAppDiagnosis(T_EC_DEMO_APP_CONTEXT* pAppContext);
static EC_T_VOID EC_FNCALL CycFrameRxCallbackWrapper(EC_T_DWORD dwTaskId, EC_T_VOID* pvAppContext);

/*-FUNCTION DEFINITIONS------------------------------------------------------*/

/********************************************************************************/
/** \brief EC-Simulator demo application.
*
* This is an EC-Simulator demo application.
*
* \return  Status value.
*/
EC_T_DWORD EcDemoApp(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EC_T_DWORD             dwRetVal          = EC_E_NOERROR;
    EC_T_DWORD             dwRes             = EC_E_NOERROR;

    T_EC_DEMO_APP_PARMS*   pAppParms         = &pAppContext->AppParms;

    EC_T_VOID*             pvJobTaskHandle   = EC_NULL;

    EC_T_REGISTERRESULTS   RegisterClientResults;
    OsMemset(&RegisterClientResults, 0, sizeof(EC_T_REGISTERRESULTS));

    CEcTimer               oAppDuration;

#if (defined INCLUDE_RAS_SERVER)
    EC_T_VOID*             pvRasServerHandle = EC_NULL;
#endif

    DS402_T_INIT_PARMS oDS402InitParms;
    EcSimulatorDemoMotion oEcSimulatorDemoMotion;
    OsMemset(&oDS402InitParms, 0, sizeof(DS402_T_INIT_PARMS));

    pAppContext->pNotificationHandler = EC_NEW(CEmNotification(pAppContext));
    if (EC_NULL == pAppContext->pNotificationHandler)
    {
        dwRetVal = EC_E_NOMEMORY;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot create notification handler\n"));
        goto Exit;
    }
    pAppContext->pMyAppDesc = (T_MY_APP_DESC*)OsMalloc(sizeof(T_MY_APP_DESC));
    if (EC_NULL == pAppContext->pMyAppDesc)
    {
        dwRetVal = EC_E_NOMEMORY;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot create myApp descriptor\n"));
        goto Exit;
    }
    OsMemset(pAppContext->pMyAppDesc, 0, sizeof(T_MY_APP_DESC));

    dwRes = myAppInit(pAppContext);
    if (EC_E_NOERROR != dwRes)
    {
        dwRetVal = dwRes;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppInit failed: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        goto Exit;
    }

    /* initialize EC-Simulator */
    {
        EC_T_SIMULATOR_INIT_PARMS oInitParms;
        OsMemset(&oInitParms, 0, sizeof(EC_T_SIMULATOR_INIT_PARMS));
        OsMemcpy(&oInitParms.LogParms, &pAppContext->LogParms, sizeof(EC_T_LOG_PARMS));
        oInitParms.LogParms.dwLogLevel = pAppParms->dwMasterLogLevel;
        oInitParms.dwSignature         = SIMULATOR_SIGNATURE;
        oInitParms.dwSize              = sizeof(EC_T_SIMULATOR_INIT_PARMS);
        OsMemcpy(oInitParms.apLinkParms, pAppParms->apLinkParms, EC_AT_MOST(EC_SIMULATOR_MAX_LINK_PARMS, MAX_LINKLAYER) * sizeof(EC_T_LINK_PARMS*));
        OsMemcpy(oInitParms.aoDeviceConnection, pAppParms->aoDeviceConnection, EC_AT_MOST(EC_SIMULATOR_MAX_LINK_PARMS, MAX_LINKLAYER) * sizeof(EC_T_SIMULATOR_DEVICE_CONNECTION_DESC));
        oInitParms.bDisableProcessDataImage = pAppParms->bDisableProcessDataImage;
        oInitParms.bConnectHcGroups    = pAppParms->bConnectHcGroups;
        oInitParms.PerfMeasInternalParms.bEnabled = (pAppParms->dwPerfMeasLevel > 0);
        oInitParms.dwBusCycleTimeNsec  = pAppParms->dwBusCycleTimeNsec;

        dwRes = esInitSimulator(pAppContext->dwInstanceId, &oInitParms);
        if (dwRes != EC_E_NOERROR)
        {
            dwRetVal = dwRes;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot initialize EC-Simulator: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            goto Exit;
        }
        if (0 != OsStrlen(pAppParms->szLicenseKey))
        {
            dwRes = esSetLicenseKey(pAppContext->dwInstanceId, pAppParms->szLicenseKey);
            if (dwRes != EC_E_NOERROR)
            {
                dwRetVal = dwRes;
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot set license key: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
                goto Exit;
            }
        }
    }

    /* initalize performance measurement */
    if (pAppParms->dwPerfMeasLevel > 0)
    {
        EC_T_PERF_MEAS_APP_PARMS oPerfMeasAppParms;
        OsMemset(&oPerfMeasAppParms, 0, sizeof(EC_T_PERF_MEAS_APP_PARMS));
        oPerfMeasAppParms.dwNumMeas = MAX_JOB_NUM;
        oPerfMeasAppParms.aPerfMeasInfos = S_aPerfMeasInfos;

        dwRes = esPerfMeasAppCreate(pAppContext->dwInstanceId, &oPerfMeasAppParms, &pAppContext->pvPerfMeas);
        if (dwRes != EC_E_NOERROR)
        {
            dwRetVal = dwRes;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot initialize app performance measurement: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            goto Exit;
        }
        pAppContext->dwPerfMeasLevel = pAppParms->dwPerfMeasLevel;
    }

    if (pAppParms->bUseFingerprint)
    {
        EC_T_CHAR szLicenseFingerprint[EC_LICENSE_FINGERPRINT_STRSIZE];

        dwRes = esGetLicenseFingerprint(pAppContext->dwInstanceId, pAppParms->byFingerprintMethod, szLicenseFingerprint);
        if (dwRes != EC_E_NOERROR)
        {
            dwRetVal = dwRes;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot get fingerprint: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            goto Exit;
        }
        EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "Fingerprint: %s\n", szLicenseFingerprint));
    }
    else
    /* print MAC address */
    if (pAppParms->nVerbose >= 0)
    {
        ETHERNET_ADDRESS oSrcMacAddress;
        OsMemset(&oSrcMacAddress, 0, sizeof(ETHERNET_ADDRESS));

        dwRes = esGetSrcMacAddress(pAppContext->dwInstanceId, &oSrcMacAddress);
        if (dwRes != EC_E_NOERROR)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot get MAC address: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        }
        EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "EtherCAT network adapter MAC: %02X-%02X-%02X-%02X-%02X-%02X\n",
            oSrcMacAddress.b[0], oSrcMacAddress.b[1], oSrcMacAddress.b[2], oSrcMacAddress.b[3], oSrcMacAddress.b[4], oSrcMacAddress.b[5]));
    }

    /* set OEM key if available */
    if (0 != pAppParms->qwOemKey)
    {
        dwRes = esSetOemKey(pAppContext->dwInstanceId, pAppParms->qwOemKey);
        if (dwRes != EC_E_NOERROR)
        {
            dwRetVal = dwRes;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Cannot set OEM key at master: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            goto Exit;
        }
    }

    /* configure network */
    dwRes = esConfigureNetwork(pAppContext->dwInstanceId, pAppParms->eCnfType, pAppParms->pbyCnfData, pAppParms->dwCnfDataLen);
    if (dwRes != EC_E_NOERROR)
    {
        dwRetVal = dwRes;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot configure EtherCAT network: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        goto Exit;
    }

    oDS402InitParms.dwInstanceId = pAppContext->dwInstanceId;
    oDS402InitParms.dwNumSlaves = pAppParms->dwDS402NumSlaves;
    oDS402InitParms.pSlaveAddr = pAppParms->awDS402SlaveAddr;

    oEcSimulatorDemoMotion.InitInstance(G_pEcLogParms, &oDS402InitParms);

    /* print slave and process data variables info */
    if (pAppParms->dwAppLogLevel >= EC_LOG_LEVEL_VERBOSE)
    {
        PrintSlaveInfos(pAppContext);
    }
    if (pAppContext->AppParms.bPrintVars)
    {
        PrintAllSlavesProcVarInfos(pAppContext);
    }

    /* check link layer parameter */
    if (EC_NULL == pAppParms->apLinkParms[0])
    {
        dwRetVal = EC_E_NOERROR;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Started without link layer. Exiting.\n"));
        goto Exit;
    }

    dwRes = InitLoggingFeatures(pAppContext);
    if (dwRes != EC_E_NOERROR)
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot initialize logging features: %s (0x%lx))\n", ecatGetText(dwRes), dwRes));
    }

    /* register CycFrameRxCallbackWrapper */
    {
        EC_T_CYCFRAME_RX_CBDESC oCycRxDesc;
        OsMemset(&oCycRxDesc, 0, sizeof(EC_T_CYCFRAME_RX_CBDESC));
        oCycRxDesc.pCallbackContext = pAppContext;
        oCycRxDesc.pfnCallback = CycFrameRxCallbackWrapper;

        dwRes = esIoCtl(pAppContext->dwInstanceId, EC_IOCTL_REGISTER_CYCFRAME_RX_CB, &oCycRxDesc, sizeof(EC_T_CYCFRAME_RX_CBDESC), EC_NULL, 0, EC_NULL);
        if (dwRes != EC_E_NOERROR)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: EC_IOCTL_REGISTER_CYCFRAME_RX_CB: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            dwRetVal = dwRes;
            goto Exit;
        }
    }

    /* create cyclic task to trigger jobs */
    {
        CEcTimer oTimeout(2000);

        pAppContext->bJobTaskRunning = EC_FALSE;
        pAppContext->bJobTaskShutdown = EC_FALSE;
        pvJobTaskHandle = OsCreateThread((EC_T_CHAR*)"EcJobTask", EcJobTask, pAppParms->CpuSet,
            pAppParms->dwJobsThreadPrio, pAppParms->dwJobsThreadStackSize, (EC_T_VOID*)pAppContext);

        /* wait until thread is running */
        while (!oTimeout.IsElapsed() && !pAppContext->bJobTaskRunning)
        {
            OsSleep(10);
        }
        if (!pAppContext->bJobTaskRunning)
        {
            dwRetVal = EC_E_TIMEOUT;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Timeout starting JobTask\n"));
            goto Exit;
        }
    }

#if (defined INCLUDE_RAS_SERVER)
    /* start RAS server */
    if (pAppParms->bStartRasServer)
    {
        EC_T_RAS_SERVER_PARMS oRemoteApiConfig;

        OsMemset(&oRemoteApiConfig, 0, sizeof(EC_T_RAS_SERVER_PARMS));
        oRemoteApiConfig.dwSignature  = EC_RAS_SERVER_SIGNATURE;
        oRemoteApiConfig.dwSize       = sizeof(EC_T_RAS_SERVER_PARMS);
        oRemoteApiConfig.oAddr.dwAddr = 0;                      /* INADDR_ANY */
        oRemoteApiConfig.wPort        = pAppParms->wRasServerPort;
        oRemoteApiConfig.dwCycleTime  = EC_RAS_CYCLE_TIME;
        oRemoteApiConfig.dwCommunicationTimeout = EC_RAS_MAX_WATCHDOG_TIMEOUT;
        oRemoteApiConfig.oAcceptorThreadCpuAffinityMask = pAppParms->CpuSet;
        oRemoteApiConfig.dwAcceptorThreadPrio           = MAIN_THREAD_PRIO;
        oRemoteApiConfig.dwAcceptorThreadStackSize      = JOBS_THREAD_STACKSIZE;
        oRemoteApiConfig.oClientWorkerThreadCpuAffinityMask = pAppParms->CpuSet;
        oRemoteApiConfig.dwClientWorkerThreadPrio           = MAIN_THREAD_PRIO;
        oRemoteApiConfig.dwClientWorkerThreadStackSize      = JOBS_THREAD_STACKSIZE;
        oRemoteApiConfig.pfnRasNotify    = RasNotifyCallback;   /* RAS notification callback function */
        oRemoteApiConfig.pvRasNotifyCtxt = pAppContext;         /* RAS notification callback function context */
        oRemoteApiConfig.dwMaxQueuedNotificationCnt = 100;      /* pre-allocation */
        oRemoteApiConfig.dwMaxParallelMbxTferCnt    = 50;       /* pre-allocation */
        oRemoteApiConfig.dwCycErrInterval           = 500;      /* span between to consecutive cyclic notifications of same type */

        if (pAppParms->nVerbose >= 1)
        {
            OsMemcpy(&oRemoteApiConfig.LogParms, &pAppContext->LogParms, sizeof(EC_T_LOG_PARMS));
            oRemoteApiConfig.LogParms.dwLogLevel = EC_LOG_LEVEL_ERROR;
        }
        dwRes = esRasSrvStart(&oRemoteApiConfig, &pvRasServerHandle);
        if (EC_E_NOERROR != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "esRasSrvStart(): %s (0x%08X))\n", esGetText(0, dwRes), dwRes));
        }
    }
#endif

    dwRes = myAppPrepare(pAppContext);
    if (EC_E_NOERROR != dwRes)
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppPrepare failed: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        dwRetVal = dwRes;
        goto Exit;
    }

    dwRes = myAppSetup(pAppContext);
    if (EC_E_NOERROR != dwRes)
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppSetup failed: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        dwRetVal = dwRes;
        goto Exit;
    }

    /* register client */
    dwRes = esRegisterClient(pAppContext->dwInstanceId, CEmNotification::NotifyWrapper, pAppContext->pNotificationHandler, &RegisterClientResults);
    if (dwRes != EC_E_NOERROR)
    {
        dwRetVal = dwRes;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot register client: %s (0x%lx))\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        goto Exit;
    }
    pAppContext->pNotificationHandler->SetClientID(RegisterClientResults.dwClntId);

    /* check if link is connected on startup */
    {
        EC_T_DWORD dwIsLinkConnected = 0;
        dwRes = esIoCtl(pAppContext->dwInstanceId, EC_IOCTL_ISLINK_CONNECTED, EC_NULL, 0, &dwIsLinkConnected, sizeof(EC_T_DWORD), EC_NULL);
        if ((EC_E_NOERROR == dwRes) && (0 == dwIsLinkConnected))
        {
            EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "Start with link disconnected\n"));
        }
    }

    /* run the demo */
    if (pAppParms->dwDemoDuration != 0)
    {
        EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "%s will stop in %ds...\n", EC_DEMO_APP_NAME, pAppParms->dwDemoDuration / 1000));
        oAppDuration.Start(pAppParms->dwDemoDuration);
    }
    bRun = EC_TRUE;
    {
        CEcTimer oPerfMeasPrintTimer;

        if (pAppParms->bPerfMeasShowCyclic)
        {
            oPerfMeasPrintTimer.Start(2000);
        }

        while (bRun)
        {
            if (oPerfMeasPrintTimer.IsElapsed())
            {
                PRINT_PERF_MEAS();
                oPerfMeasPrintTimer.Restart();
            }

            /* check if demo shall terminate */
            bRun = !(OsTerminateAppRequest() || oAppDuration.IsElapsed());

            myAppDiagnosis(pAppContext);

            /* process notification jobs */
            pAppContext->pNotificationHandler->ProcessNotificationJobs();

            OsSleep(5);
        }
    }

    if (pAppContext->dwPerfMeasLevel > 0)
    {
        EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "\nJob times before shutdown\n"));
        PRINT_PERF_MEAS();
    }

Exit:

    /* unregister client */
    if (EC_NULL != pAppContext->pNotificationHandler)
    {
        EC_T_DWORD dwClientId = pAppContext->pNotificationHandler->GetClientID();
        if (INVALID_CLIENT_ID != dwClientId)
        {
            dwRes = esUnregisterClient(pAppContext->dwInstanceId, dwClientId);
            if (EC_E_NOERROR != dwRes)
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Cannot unregister client: %s (0x%lx))\n", ecatGetText(dwRes), dwRes));
            }
            pAppContext->pNotificationHandler->SetClientID(INVALID_CLIENT_ID);
        }
    }

    /* shutdown JobTask */
    {
        pAppContext->bJobTaskShutdown = EC_TRUE;
        while (pAppContext->bJobTaskRunning)
        {
            OsSleep(10);
        }
        if (EC_NULL != pvJobTaskHandle)
        {
            OsDeleteThreadHandle(pvJobTaskHandle);
        }
    }

#if (defined INCLUDE_RAS_SERVER)
    /* stop RAS server */
    if (EC_NULL != pvRasServerHandle)
    {
        EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "Stop Remote Api Server\n"));
        dwRes = esRasSrvStop(pvRasServerHandle, 2000);
        if (EC_E_NOERROR != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Remote API Server shutdown failed\n"));
        }
    }
#endif

    /* deinitialize EC-Simulator */
    dwRes = esDeinitSimulator(pAppContext->dwInstanceId);
    if (EC_E_NOERROR != dwRes)
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: Cannot de-initialize EC-Simulator: %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
    }

    DeinitLoggingFeatures(pAppContext);

    SafeDelete(pAppContext->pNotificationHandler);
    if (EC_NULL != pAppContext->pMyAppDesc)
    {
        OsSafeFree(pAppContext->pMyAppDesc->pbyFlashBuf);
        OsSafeFree(pAppContext->pMyAppDesc);
    }

    return dwRetVal;
}

/********************************************************************************/
/** \brief  Trigger jobs to drive master, and update process data.
*
* \return N/A
*/
static EC_T_VOID EcJobTask(EC_T_VOID* pvAppContext)
{
    EC_T_DWORD dwRes = EC_E_ERROR;
    T_EC_DEMO_APP_CONTEXT* pAppContext = (T_EC_DEMO_APP_CONTEXT*)pvAppContext;
    T_EC_DEMO_APP_PARMS*   pAppParms   = &pAppContext->AppParms;

    EC_T_USER_JOB_PARMS oJobParms;
    EC_T_BOOL bPollingMode = ((EC_NULL != pAppParms->apLinkParms[0]) && (EcLinkMode_POLLING == pAppParms->apLinkParms[0]->eLinkMode));

    OsMemset(&oJobParms, 0, sizeof(EC_T_USER_JOB_PARMS));

    /* demo loop */
    pAppContext->bJobTaskRunning = EC_TRUE;
    do
    {
        /* wait for next cycle (event from scheduler task) */
        dwRes = OsWaitForEvent(pAppContext->pvJobTaskEvent, 3000);
        if (EC_E_NOERROR != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: OsWaitForEvent(): %s (0x%lx)\n", ecatGetText(dwRes), dwRes));
            OsSleep(500);
        }

        /* start Task (required for enhanced performance measurement) */
        dwRes = esExecJob(pAppContext->dwInstanceId, eUsrJob_StartTask, EC_NULL);
        if (EC_E_NOERROR != dwRes && EC_E_INVALIDSTATE != dwRes && EC_E_LINK_DISCONNECTED != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: esExecJob(eUsrJob_StartTask): %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        }

        /* process all received frames (read new input values) */
        if (bPollingMode)
        {
            dwRes = esExecJob(pAppContext->dwInstanceId, eUsrJob_ProcessAllRxFrames, &oJobParms);
            if (EC_E_NOERROR != dwRes && EC_E_INVALIDSTATE != dwRes && EC_E_LINK_DISCONNECTED != dwRes)
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: esExecJob(eUsrJob_ProcessAllRxFrames): %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
            }
        }

        if (pAppContext->dwPerfMeasLevel > 0)
        {
            esPerfMeasAppStart(pAppContext->dwInstanceId, pAppContext->pvPerfMeas, PERF_myAppWorkpd);
        }
        {
            myAppWorkpd(pAppContext);
        }
        if (pAppContext->dwPerfMeasLevel > 0)
        {
            esPerfMeasAppEnd(pAppContext->dwInstanceId, pAppContext->pvPerfMeas, PERF_myAppWorkpd);
        }

        /* execute some administrative jobs. No bus traffic is performed by this function */
        dwRes = esExecJob(pAppContext->dwInstanceId, eUsrJob_SimulatorTimer, EC_NULL);
        if (EC_E_NOERROR != dwRes && EC_E_INVALIDSTATE != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: esExecJob(JOB_SimulatorTimer, EC_NULL): %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        }

        /* remove this code when using licensed version */
        if (EC_E_EVAL_EXPIRED == dwRes)
        {
            /* set shutdown flag */
            bRun = EC_FALSE;

            /* supress error messages after evaluation time limit reached */
            pEcLogParms->dwLogLevel = EC_LOG_LEVEL_SILENT;
            esSetLogParms(pAppContext->dwInstanceId, pEcLogParms);
        }

        /* stop Task (required for enhanced performance measurement) */
        dwRes = esExecJob(pAppContext->dwInstanceId, eUsrJob_StopTask, EC_NULL);
        if (EC_E_NOERROR != dwRes && EC_E_INVALIDSTATE != dwRes && EC_E_LINK_DISCONNECTED != dwRes)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: esExecJob(eUsrJob_StopTask): %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
        }
#if !(defined NO_OS)
    } while (!pAppContext->bJobTaskShutdown);

    pAppContext->bJobTaskRunning = EC_FALSE;
#else
    /* in case of NO_OS the job task function is called cyclically within the timer ISR */
    } while (EC_FALSE);
    pAppContext->bJobTaskRunning = !pAppContext->bJobTaskShutdown;
#endif

    return;
}

/********************************************************************************/
/** \brief  Handler for master RAS notifications
*
*
* \return  Status value.
*/
#ifdef INCLUDE_RAS_SERVER
static EC_T_DWORD RasNotifyCallback(
    EC_T_DWORD         dwCode,
    EC_T_NOTIFYPARMS*  pParms
)
{
    EC_T_DWORD dwRetVal = EC_E_ERROR;
    T_EC_DEMO_APP_CONTEXT* pAppContext = (T_EC_DEMO_APP_CONTEXT*)pParms->pCallerData;

    if ((EC_NULL == pParms))
    {
        dwRetVal = EC_E_INVALIDPARM;
        goto Exit;
    }

    switch (dwCode)
    {
    case EC_RAS_NOTIFY_CONNECTION:         /* GENERIC RAS | 1 */
    {
        EC_PT_RAS_CONNOTIFYDESC    pConNot = EC_NULL;
        if (sizeof(EC_T_RAS_CONNOTIFYDESC) > pParms->dwInBufSize)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "RAS Invalid Parameter size for EC_RAS_NOTIFY_CONNECTION\n"));
            dwRetVal = EC_E_INVALIDPARM;
            goto Exit;
        }

        pConNot = (EC_PT_RAS_CONNOTIFYDESC)pParms->pbyInBuf;
        if (pConNot->dwCause == EC_E_NOERROR)
        {
            EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "RAS Connection changed: Established!\n"));
        }
        else
        {
            EcLogMsg(EC_LOG_LEVEL_INFO, (pEcLogContext, EC_LOG_LEVEL_INFO, "RAS Connection changed: Cause: %s (0x%lx)\n",
                esGetText(pAppContext->dwInstanceId, pConNot->dwCause), pConNot->dwCause));
        }
    } break;
    case EC_RAS_NOTIFY_REGISTER:           /* GENERIC RAS | 2 */
    {
        if (sizeof(EC_T_RAS_REGNOTIFYDESC) > pParms->dwInBufSize)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "RAS Invalid Parameter size for EC_RAS_NOTIFY_REGISTER\n"));
            dwRetVal = EC_E_INVALIDPARM;
            goto Exit;
        }
    } break;
    case EC_RAS_NOTIFY_UNREGISTER:         /* GENERIC RAS | 3 */
    {
        if (sizeof(EC_T_RAS_REGNOTIFYDESC) > pParms->dwInBufSize)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "RAS Invalid Parameter size for EC_RAS_NOTIFY_UNREGISTER\n"));
            dwRetVal = EC_E_INVALIDPARM;
            goto Exit;
        }
    } break;
    case EC_RAS_NOTIFY_MARSHALERROR:       /* ERROR RAS | 1 */
    {
        EC_PT_RAS_MARSHALERRORDESC     pMarshNot = EC_NULL;
        if (sizeof(EC_T_RAS_MARSHALERRORDESC) > pParms->dwInBufSize)
        {
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Invalid Parameter size for EC_RAS_NOTIFY_MARSHALERROR\n"));
            dwRetVal = EC_E_INVALIDPARM;
            goto Exit;
        }

        pMarshNot = (EC_PT_RAS_MARSHALERRORDESC)pParms->pbyInBuf;
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Marshaling error! Cookie: 0x%lx\n", pMarshNot->dwCookie));
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Command: 0x%lx, Cause: %s (0x%lx)\n",
            pMarshNot->dwCommandCode, esGetText(pAppContext->dwInstanceId, pMarshNot->dwCause), pMarshNot->dwCause));
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Protocol Header: 0x%lx\n", pMarshNot->dwLenStatCmd));
    } break;
    case EC_RAS_NOTIFY_ACKERROR:           /* ERROR RAS | 2 */
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Acknowledge error! Error: %s (0x%lx)\n", esGetText(pAppContext->dwInstanceId, EC_GETDWORD(pParms->pbyInBuf)), EC_GETDWORD(pParms->pbyInBuf)));
    } break;
    case EC_RAS_NOTIFY_NONOTIFYMEMORY:     /* ERROR RAS | 3 */
    {
        EC_T_RAS_NONOTIFYMEMORYDESC NoNotifyMemoryDesc;
        EC_PT_RAS_NONOTIFYMEMORYDESC pNoNotifyMemoryDescSerialized = (EC_PT_RAS_NONOTIFYMEMORYDESC)pParms->pbyInBuf;
        OsDbgAssert(pParms->dwInBufSize >= sizeof(EC_T_RAS_NONOTIFYMEMORYDESC));
        NoNotifyMemoryDesc.dwCookie = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCookie);
        NoNotifyMemoryDesc.dwCode = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCode);

        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Out of notification memory! %s (0x%08X), cookie 0x%lx.\n",
            esGetNotifyText(pAppContext->dwInstanceId, NoNotifyMemoryDesc.dwCode), NoNotifyMemoryDesc.dwCode, NoNotifyMemoryDesc.dwCookie));
    } break;
    case EC_RAS_NOTIFY_STDNOTIFYMEMORYSMALL:   /* ERROR RAS | 4 */
    {
        EC_T_RAS_NONOTIFYMEMORYDESC NoNotifyMemoryDesc;
        EC_PT_RAS_NONOTIFYMEMORYDESC pNoNotifyMemoryDescSerialized = (EC_PT_RAS_NONOTIFYMEMORYDESC)pParms->pbyInBuf;
        OsDbgAssert(pParms->dwInBufSize >= sizeof(EC_T_RAS_NONOTIFYMEMORYDESC));
        NoNotifyMemoryDesc.dwCookie = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCookie);
        NoNotifyMemoryDesc.dwCode = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCode);

        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Out of non-mailbox notification memory! %s (0x%08X), cookie 0x%lx.\n",
            esGetNotifyText(pAppContext->dwInstanceId, NoNotifyMemoryDesc.dwCode), NoNotifyMemoryDesc.dwCode, NoNotifyMemoryDesc.dwCookie));
    } break;
    case EC_RAS_NOTIFY_MBXNOTIFYMEMORYSMALL:   /* ERROR RAS | 5 */
    {
        EC_T_RAS_NONOTIFYMEMORYDESC NoNotifyMemoryDesc;
        EC_PT_RAS_NONOTIFYMEMORYDESC pNoNotifyMemoryDescSerialized = (EC_PT_RAS_NONOTIFYMEMORYDESC)pParms->pbyInBuf;
        OsDbgAssert(pParms->dwInBufSize >= sizeof(EC_T_RAS_NONOTIFYMEMORYDESC));
        NoNotifyMemoryDesc.dwCookie = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCookie);
        NoNotifyMemoryDesc.dwCode = EC_GET_FRM_DWORD(&pNoNotifyMemoryDescSerialized->dwCode);

        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Out of mailbox notification memory! %s (0x%08X), cookie 0x%lx.\n",
            esGetNotifyText(pAppContext->dwInstanceId, NoNotifyMemoryDesc.dwCode), NoNotifyMemoryDesc.dwCode, NoNotifyMemoryDesc.dwCookie));
    } break;
    default:
    {
        EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "RasNotifyCallback: name = %s code = 0x%x\n", esGetNotifyText(pAppContext->dwInstanceId, dwCode), dwCode));
    } break;
    }

    dwRetVal = EC_E_NOERROR;
Exit:
    return dwRetVal;
}
#endif

/*-MYAPP---------------------------------------------------------------------*/

/***************************************************************************************************/
/** \brief  Initialize the application before initializing EC-Simulator
 *
 * \return #EC_E_NOERROR or error code
 */
static EC_T_DWORD myAppInit(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EC_UNREFPARM(pAppContext);
    return EC_E_NOERROR;
}

/***************************************************************************************************/
/** \brief  Prepare the application before setup
 *
 * \return #EC_E_NOERROR or error code
 */
static EC_T_DWORD myAppPrepare(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EC_T_DWORD          dwRetVal   = EC_E_ERROR;
    EC_T_DWORD          dwRes      = EC_E_ERROR;
    T_MY_APP_DESC*      pMyAppDesc = pAppContext->pMyAppDesc;
    EC_T_CFG_SLAVE_INFO oCfgSlaveInfo;
    OsMemset(&oCfgSlaveInfo, 0, sizeof(EC_T_CFG_SLAVE_INFO));

    if (pAppContext->AppParms.bFlash)
    {
        EC_T_WORD wFlashSlaveAddr = pAppContext->AppParms.wFlashSlaveAddr;

        /* check if slave address is provided */
        if (wFlashSlaveAddr != 0)
        {
            /* get process data INPUT offset and size from slave */
            dwRes = esGetCfgSlaveInfo(pAppContext->dwInstanceId, EC_TRUE, wFlashSlaveAddr, &oCfgSlaveInfo);
            if (EC_E_NOERROR != dwRes)
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppPrepare: esGetCfgSlaveInfo() returns %s (0x%x), slave address=%d\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes, wFlashSlaveAddr));
                dwRetVal = dwRes;
                goto Exit;
            }

            if (oCfgSlaveInfo.dwPdSizeIn != 0)
            {
                pMyAppDesc->dwFlashPdBitSize = oCfgSlaveInfo.dwPdSizeIn;
                pMyAppDesc->dwFlashPdBitOffs = oCfgSlaveInfo.dwPdOffsIn;
            }
            else
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppPrepare: Slave address=%d has no INPUTs, therefore flashing not possible\n", wFlashSlaveAddr));
                dwRetVal = EC_E_NOTFOUND;
                goto Exit;
            }
        }
        else
        {
            /* get complete process data output size */
            EC_T_MEMREQ_DESC oPdMemorySize;
            OsMemset(&oPdMemorySize, 0, sizeof(EC_T_MEMREQ_DESC));

            dwRes = esIoCtl(pAppContext->dwInstanceId, EC_IOCTL_GET_PDMEMORYSIZE, EC_NULL, 0, &oPdMemorySize, sizeof(EC_T_MEMREQ_DESC), EC_NULL);
            if (EC_E_NOERROR != dwRes)
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppPrepare: esIoCtl(EC_IOCTL_GET_PDMEMORYSIZE) returns %s (0x%x)\n", esGetText(pAppContext->dwInstanceId, dwRes), dwRes));
                dwRetVal = dwRes;
                goto Exit;
            }
            pMyAppDesc->dwFlashPdBitSize = oPdMemorySize.dwPDInSize * 8;
        }
        if (pMyAppDesc->dwFlashPdBitSize > 0)
        {
            pMyAppDesc->dwFlashInterval = 20000000; /* flash every 20 msec */
            pMyAppDesc->dwFlashBufSize = BIT2BYTE(pMyAppDesc->dwFlashPdBitSize);
            pMyAppDesc->pbyFlashBuf = (EC_T_BYTE*)OsMalloc(pMyAppDesc->dwFlashBufSize);
            if (EC_NULL == pMyAppDesc->pbyFlashBuf)
            {
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "ERROR: myAppPrepare: no memory left \n"));
                dwRetVal = EC_E_NOMEMORY;
                goto Exit;
            }
            OsMemset(pMyAppDesc->pbyFlashBuf, 0 , pMyAppDesc->dwFlashBufSize);
        }
    }

    dwRetVal = EC_E_NOERROR;
Exit:
    return dwRetVal;
}

/***************************************************************************************************/
/** \brief  Setup the application
 *
 * \return #EC_E_NOERROR or error code
 */
static EC_T_DWORD myAppSetup(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EC_UNREFPARM(pAppContext);

    return EC_E_NOERROR;
}

/***************************************************************************************************/
/** \brief  Application working process data function
 *
 * \return #EC_E_NOERROR or error code
 */
static EC_T_DWORD myAppWorkpd(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    T_MY_APP_DESC* pMyAppDesc = pAppContext->pMyAppDesc;
    EC_T_BYTE*     pbyPdIn    = esGetProcessImageInputPtr(pAppContext->dwInstanceId);

    /* demo code flashing */
    if (pMyAppDesc->dwFlashPdBitSize != 0)
    {
        pMyAppDesc->dwFlashTimer += pAppContext->AppParms.dwBusCycleTimeNsec;
        if (pMyAppDesc->dwFlashTimer >= pMyAppDesc->dwFlashInterval)
        {
            pMyAppDesc->dwFlashTimer = 0;

            /* flash with pattern */
            pMyAppDesc->byFlashVal++;
            OsMemset(pMyAppDesc->pbyFlashBuf, pMyAppDesc->byFlashVal, pMyAppDesc->dwFlashBufSize);

            /* update INPUTs */
            EC_COPYBITS(pbyPdIn, pMyAppDesc->dwFlashPdBitOffs, pMyAppDesc->pbyFlashBuf, 0, pMyAppDesc->dwFlashPdBitSize);
        }
    }

    return EC_E_NOERROR;
}

/***************************************************************************************************/
/** \brief  Application diagnosis called from time to time
 *
 * \return #EC_E_NOERROR or error code
 */
static EC_T_DWORD myAppDiagnosis(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EC_UNREFPARM(pAppContext);
    return EC_E_NOERROR;
}

/***************************************************************************************************/
/**
\brief  call myAppWorkpd after cyclic frame processing

  This function is called cyclically after cyclic frame processed by EC-Simulator (replaces myAppWorkpd from Job Task)
*/
static EC_T_VOID EC_FNCALL CycFrameRxCallbackWrapper(EC_T_DWORD dwTaskId, EC_T_VOID* pvAppContext)
{
    T_EC_DEMO_APP_CONTEXT* pAppContext = (T_EC_DEMO_APP_CONTEXT*)pvAppContext;
    EC_UNREFPARM(dwTaskId);

    if (pAppContext->dwPerfMeasLevel > 0)
    {
        esPerfMeasAppStart(pAppContext->dwInstanceId, pAppContext->pvPerfMeas, PERF_myAppWorkpd);
    }
    {
        myAppWorkpd(pAppContext);
    }
    if (pAppContext->dwPerfMeasLevel > 0)
    {
        esPerfMeasAppEnd(pAppContext->dwInstanceId, pAppContext->pvPerfMeas, PERF_myAppWorkpd);
    }
}

EC_T_VOID ShowSyntaxAppUsage(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    const EC_T_CHAR* szAppUsage = "<LinkLayer> -ds402 FixedAddress1,...,FixedAddressN [-f ENI-FileName] [-t time] [-b cycle time] [-a affinity] [-v lvl] [-perf [level]] [-log prefix [msg cnt]] [-lic key] [-oem key] [-flash address] [-printvars]"
#if (defined INCLUDE_RAS_SERVER)
        " [-sp [port]]"
#endif
#if (defined INCLUDE_PCAP_RECORDER)
        " [-rec [prefix [frame cnt]]]"
#endif
        ;
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "%s V%s for %s %s\n", EC_DEMO_APP_NAME, EC_FILEVERSIONSTR, ATECAT_PLATFORMSTR, EC_COPYRIGHT));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "Syntax:\n"));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "%s %s\n", EC_DEMO_APP_NAME, szAppUsage));
}

EC_T_VOID ShowSyntaxApp(T_EC_DEMO_APP_CONTEXT* pAppContext)
{
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "   -flash            Flash outputs\n"));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "     address         0=all, >0 = slave station address\n"));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "   -printvars        Print process variable name and offset for all variables of all slaves\n"));
#if (defined INCLUDE_PCAP_RECORDER)
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "   -rec              Record network traffic to pcap file\n"));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "    [prefix          Pcap file name prefix\n"));
    EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "    [frame cnt]      Frame count for log buffer allocation (default = %d, with %d bytes per message)]\n", PCAP_RECORDER_BUF_FRAME_CNT, ETHERNET_MAX_FRAMEBUF_LEN));
#endif
}

/*-END OF SOURCE FILE--------------------------------------------------------*/
