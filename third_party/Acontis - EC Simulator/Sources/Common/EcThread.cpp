/** ---------------------------------------------------------------------------
 * \file
 * \brief       Thread class implementation
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

/*-LOGGING-------------------------------------------------------------------*/
#ifndef pEcLogParms
#define pEcLogParms (GetLogParms())
#endif

/*-INCLUDES------------------------------------------------------------------*/
#include "EcOs.h"
#include "EcLog.h"
#include "EcMemoryLog.h"
#include "EcThread.h"
#include "EcTimer.h"
#include "EcError.h"

/*-CLASS FUNCTIONS-----------------------------------------------------------*/
CEcThread::CEcThread(const struct _EC_T_LOG_PARMS* poLogParms, EC_T_DWORD dwMemTrace, struct _EC_T_MEMORY_LOGGER* poMemLog)
    : m_poLogParms((struct _EC_T_LOG_PARMS*)poLogParms)
    , m_dwMemTrace(dwMemTrace)
    , m_poMemLog(poMemLog)
    , m_pfThreadEntry(EC_NULL)
    , m_pvParams(EC_NULL)
    , m_pfExceptionCallback(EC_NULL)
    , m_pvCbParams(EC_NULL)
    , m_hThread(EC_NULL)
    , m_bThreadStop(EC_FALSE)
    , m_bThreadReady(EC_FALSE)
    , m_pszName(EC_NULL)
{
    OsMemset(&m_oLogParmsStub, 0, sizeof(EC_T_LOG_PARMS));
    if (EC_NULL == poLogParms)
    { 
        m_poLogParms = &m_oLogParmsStub;
    }
}

CEcThread::~CEcThread()
{
    /* thread should be stopped */
    OsDbgAssert(isStopped());
    if ((EC_NULL != GetMemLog()) && (EC_NULL != m_pszName))
    {
        EC_TRACE_SUBMEM(m_dwMemTrace, "CEcThread::~CEcThread m_pszName", m_pszName, OsStrlen(m_pszName) + 1); 
    }
    OsSafeFree(m_pszName);
    OsDbgAssert(m_hThread == EC_NULL);
}

EC_T_DWORD CEcThread::Start(EC_T_LOG_PARMS* pLogParms, EC_PF_THREADENTRY pfThreadEntry, EC_T_VOID* pvParams, const EC_T_CHAR* szThreadName,
    EC_T_CPUSET cpuIstCpuAffinityMask, EC_T_DWORD dwPrio, EC_T_DWORD dwStackSize, EC_T_DWORD dwTimeout)
{
    EC_T_DWORD dwRetVal = EC_E_NOERROR;
    size_t nThreadNameSize = 0;
    CEcTimer startTimeout;

    if (EC_NULL == pLogParms)
    {
        return EC_E_INVALIDPARM;
    }
    if ((EC_NULL != m_hThread) || (EC_NULL != m_pszName))
    {
        return EC_E_INVALIDSTATE;
    }

    if (EC_NULL != pLogParms)
    {
        m_poLogParms = pLogParms;
    }

    setThreadProc(pfThreadEntry, pvParams);

    nThreadNameSize = OsStrlen(szThreadName) + 1;
    m_pszName = (EC_T_CHAR*)OsMalloc(nThreadNameSize);
    if (EC_NULL != m_pszName)
    {
        if (EC_NULL != GetMemLog())
        {
            EC_TRACE_ADDMEM(m_dwMemTrace, "CEcThread::Start m_pszName", m_pszName, OsStrlen(szThreadName) + 1);
        }
        OsSafeStrncpy2(m_pszName, szThreadName, nThreadNameSize);
    }

    m_bThreadStop = EC_FALSE;
    m_hThread = OsCreateThread(szThreadName, (EC_PF_THREADENTRY)threadProc, cpuIstCpuAffinityMask, dwPrio, dwStackSize, this);

    if (EC_NULL == m_hThread)
    {
        /* reset thread entry */
        setThreadProc(EC_NULL, EC_NULL);

        dwRetVal = EC_E_NOMEMORY;
        goto Exit;
    }

    for (startTimeout.Start(dwTimeout); !startTimeout.IsElapsed(); )
    {
        if (isReady())
        {
            break;
        }
        OsSleep(1);
    }
    if (!isReady())
    {
        dwRetVal = EC_E_TIMEOUT;
    }

Exit:
    return dwRetVal;
}

EC_T_DWORD CEcThread::Stop(EC_T_DWORD dwTimeout)
{
    EC_T_DWORD dwRetVal = EC_E_NOERROR;
    CEcTimer stopTimeout;
    CEcTimer stopTimeoutWarnTimout(20000);

    if (EC_NULL == m_hThread)
    {
        return EC_E_NOERROR;
    }

    stopThread();

    if (EC_NOWAIT != dwTimeout)
    {
        if (EC_WAITINFINITE != dwTimeout)
        {
            stopTimeout.Start(dwTimeout);
        }
        while (!isStopped() && !stopTimeout.IsElapsed())
        {
            if (stopTimeoutWarnTimout.IsElapsed())
            {
                stopTimeoutWarnTimout.Stop();
                EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "CEcThread::Stop Stopping thread%s%s takes longer than 20s!\n", (m_pszName ? " ": ""), m_pszName));
            }
            OsSleep(1);
        }
        if (!isStopped())
        {
            dwRetVal = EC_E_TIMEOUT;
            EcLogMsg(EC_LOG_LEVEL_ERROR, (pEcLogContext, EC_LOG_LEVEL_ERROR, "CEcThread::Stop Time-out stopping thread%s%s!\n", (m_pszName ? " ": ""), m_pszName));
        }
    }

    if (EC_NULL != m_hThread)
    {
        OsDeleteThreadHandle(m_hThread);
    }
    m_hThread = EC_NULL;

    if ((EC_NULL != GetMemLog()) && (EC_NULL != m_pszName))
    {
        EC_TRACE_SUBMEM(m_dwMemTrace, "CEcThread::Stop m_pszName", m_pszName, OsStrlen(m_pszName) + 1); 
    }
    OsSafeFree(m_pszName);

    return dwRetVal;
}

EC_T_VOID CEcThread::SetExceptionCallback(EC_PF_EXCEPTION_CALLBACK pfExceptionCallback, EC_T_VOID* pvCbParams)
{
    m_pfExceptionCallback = pfExceptionCallback;
    m_pvCbParams = pvCbParams;
}

EC_T_DWORD CEcThread::threadProc(EC_T_PVOID pvParams)
{
    CEcThread* pThis = (CEcThread*)pvParams;

#if (!defined EC_EXCEPTIONS_NOTSUPPORTED)
    try
#endif
    {
        pThis->m_bThreadReady = EC_TRUE;

        while (!pThis->m_bThreadStop)
        {
            pThis->m_pfThreadEntry(pThis->m_pvParams);
        }
    }
#if (!defined EC_EXCEPTIONS_NOTSUPPORTED)
    catch (...)
    {
        if (EC_NULL != pThis->m_pfExceptionCallback)
        {
            pThis->m_pfExceptionCallback(pThis->m_pszName, pThis->m_pvCbParams);
        }

        /* indicate that stopped */
        pThis->setThreadProc(EC_NULL, EC_NULL);
        throw;
    }
#endif

    /* indicate that stopped */
    pThis->setThreadProc(EC_NULL, EC_NULL);

    return 0;
}

EC_T_VOID CEcThread::setThreadProc(EC_PF_THREADENTRY pfThreadEntry, EC_T_VOID* pvParams)
{
    m_pfThreadEntry = pfThreadEntry;
    m_pvParams = pvParams;
}

/*-END OF SOURCE FILE--------------------------------------------------------*/
