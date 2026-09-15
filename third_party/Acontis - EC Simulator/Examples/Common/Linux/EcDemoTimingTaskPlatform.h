/** ---------------------------------------------------------------------------
 * \file        EcDemoTimingTaskPlatform.h
 * \brief       EtherCAT demo timing task
 * \author      Timo Nussbaumer
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#pragma once

#include "EcDemoTimingTask.h"

class CDemoTimingTaskPlatform
    : public CDemoTimingTask
{
public:
    typedef CDemoTimingTask TBaseClass;

    CDemoTimingTaskPlatform();
    explicit CDemoTimingTaskPlatform(_T_EC_DEMO_APP_CONTEXT& rAppContext);

protected:
    virtual EC_T_VOID TimingTask() EC_OVERRIDE;

public:
    static EC_T_DWORD GetHostTime(EC_T_VOID* pvContext, EC_T_UINT64* pnActualHostTimeInNsec);
};