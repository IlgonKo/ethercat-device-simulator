/** ---------------------------------------------------------------------------
 * \file        EcSimulatorDs402.cpp
 * \brief       DS402 Slave Simulation
 * \author      Max Bachmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#include "EcSimulatorDs402.h"
#include "EcOs.h"
#include "EcSimulator.h"

const EcSimulatorDs402::CiA402Objects DefCiA402ObjectValues
= {
    0x0,/*(UINT16) ErrorCode 0x1001*/
    0x0,/*(UINT16) ControlWord 0x6040*/
    0x0,/*(UINT16) StatusWord 0x6041*/
    0x2,/*(INT16) QuickStopOptionCode 0x605A*/
    EC_DS402_DISABLE_DRIVE,/*(INT16)ShutdownOptionCode 0x605B*/
    EC_DS402_SLOW_DOWN_RAMP, /*(INT16) DisableOperationCode 0x605C*/
    EC_DS402_QUICKSTOP_RAMP,/*(INT16) FaultReactionCode 0x605E*/
    0x0,/*(INT16) ModeOfOperation 0x6060*/
    0x0,/*(INT16) Mode Of Operation Display 0x6061*/
    0x0,/*(INT32) Position Actual Value 0x6064*/
    0x0,/*(INT32) Velocity Actual Value 0x606C*/
    0x0,/*(INT16) Torque Actual Value 0x6077*/
    0x0,/*(INT32) Target Position 0x607A*/
    { -2000000000,2000000000 },/*TOBJ607D Software Position Limit (minLimit: -2000000000 / maxLimit: 2000000000)*/
    0x0,/*(UINT32) QuickStopDeclaration 0x6085*/
    0x0,/*(INT32) Target Velocity    0x60FF*/
    0x0/*(UINT32) Supported Drive Modes 0x6502*/
};

EC_T_VOID EcSimulatorDs402::APPL_InputMapping(EC_T_WORD* pData)
{
    EC_T_BYTE* pbyPdIn = esGetProcessImageInputPtr(m_dwInstanceId);

    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (m_aoAxes[wAxisIdx].bAxisIsActive)
        {
            CiA402Objects* pObjects = &m_aoAxes[wAxisIdx].Objects;
            CiA402ObjectsPointers* pCiA402ObjectsPointers = &m_aoAxes[wAxisIdx].oCiA402ObjectsPointers;

            if (NULL != pCiA402ObjectsPointers->pObjErrorCode)
                EC_SET_FRM_WORD(pCiA402ObjectsPointers->pObjErrorCode, pObjects->objStatusWord);
            if (NULL != pCiA402ObjectsPointers->pObjStatusWord)
                EC_SET_FRM_WORD(pCiA402ObjectsPointers->pObjStatusWord, pObjects->objStatusWord);
            if (NULL != pCiA402ObjectsPointers->pObjPositionActualValue)
                EC_SET_FRM_DWORD(pCiA402ObjectsPointers->pObjPositionActualValue, pObjects->objPositionActualValue);
            if (NULL != pCiA402ObjectsPointers->pObjVelocityActualValue)
                EC_SET_FRM_DWORD(pCiA402ObjectsPointers->pObjVelocityActualValue, pObjects->objVelocityActualValue);
            if (NULL != pCiA402ObjectsPointers->pObjTorqueActualValue)
                EC_SET_FRM_WORD(pCiA402ObjectsPointers->pObjTorqueActualValue, pObjects->objTorqueActualValue);
            if (NULL != pCiA402ObjectsPointers->pObjModesOfOperationDisplay)
                EC_SET_FRM_WORD(pCiA402ObjectsPointers->pObjModesOfOperationDisplay, pObjects->objModesOfOperationDisplay);
        }
    }

    OsMemcpy(pData, &pbyPdIn[m_oCfgSlaveInfo.dwPdOffsIn / 8], BIT2BYTE(m_oCfgSlaveInfo.dwPdSizeIn));
}

EC_T_VOID EcSimulatorDs402::APPL_OutputMapping(EC_T_WORD* pData)
{
    EC_UNREFPARM(pData);

    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (m_aoAxes[wAxisIdx].bAxisIsActive)
        {
            CiA402Objects* pObjects = &m_aoAxes[wAxisIdx].Objects;
            CiA402ObjectsPointers* pCiA402ObjectsPointers = &m_aoAxes[wAxisIdx].oCiA402ObjectsPointers;

            /* OUTPUTs */
            if (NULL != pCiA402ObjectsPointers->pObjControlWord)
                pObjects->objControlWord = EC_GET_FRM_WORD(pCiA402ObjectsPointers->pObjControlWord);
            if (NULL != pCiA402ObjectsPointers->pObjTargetPosition)
                pObjects->objTargetPosition = (EC_T_SDWORD)EC_GET_FRM_DWORD(pCiA402ObjectsPointers->pObjTargetPosition);
            if (NULL != pCiA402ObjectsPointers->pObjTargetVelocity)
                pObjects->objTargetVelocity = (EC_T_SDWORD)EC_GET_FRM_DWORD(pCiA402ObjectsPointers->pObjTargetVelocity);
        }
    }
}

EC_T_VOID EcSimulatorDs402::APPL_Application()
{
    CiA402_StateMachine();

    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (m_aoAxes[wAxisIdx].bAxisIsActive)
        {
            CiA402_Application(&m_aoAxes[wAxisIdx]);
        }
    }
}

EC_T_DWORD EcSimulatorDs402::MapInputObjects()
{
    EC_T_DWORD dwRes = EC_E_ERROR;
    EC_T_BYTE* pbyPdIn = esGetProcessImageInputPtr(m_dwInstanceId);
    EC_T_WORD wSlaveOutpVarNumOf = 0;
    EC_T_WORD wSlaveOutpVarNum = 0;
    EC_PT_PROCESS_VAR_INFO_EX pSlaveProcVarInfoEntries = EC_NULL;

    dwRes = esGetSlaveInpVarInfoNumOf(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    pSlaveProcVarInfoEntries = (EC_PT_PROCESS_VAR_INFO_EX)OsMalloc(wSlaveOutpVarNumOf * sizeof(EC_T_PROCESS_VAR_INFO_EX));
    if (EC_NULL == pSlaveProcVarInfoEntries)
    {
        dwRes = EC_E_NOMEMORY;
        goto Exit;
    }

    dwRes = esGetSlaveInpVarInfoEx(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, wSlaveOutpVarNumOf, pSlaveProcVarInfoEntries, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    for(wSlaveOutpVarNum = 0; wSlaveOutpVarNum < wSlaveOutpVarNumOf; wSlaveOutpVarNum++)
    {
        EC_PT_PROCESS_VAR_INFO_EX poVarInfoEx = &pSlaveProcVarInfoEntries[wSlaveOutpVarNum];
        EC_T_BYTE* pbyPdVarPtr = &pbyPdIn[poVarInfoEx->nBitOffs / 8];
        EC_T_WORD wAxis = 0;
        EC_T_WORD wIndex = poVarInfoEx->wIndex;

        while (wIndex >= DS402_SLOT_INDEX_INCREMENT && wAxis < m_wAxisCnt)
        {
            switch (wIndex)
            {
            case EC_DS402_OBJ_ERROR_CODE:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjErrorCode = (EC_T_WORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_STATUS_WORD:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjStatusWord = (EC_T_WORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_MODES_OF_OPERATION_DISPLAY:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjModesOfOperationDisplay = (EC_T_SWORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_POSITION_ACTUAL_VALUE:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjPositionActualValue = (EC_T_SDWORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_VELOCITY_ACTUAL_VALUE:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjVelocityActualValue = (EC_T_SDWORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_TORQUE_ACTUAL_VALUE:
                m_aoAxes[wAxis].oCiA402ObjectsPointers.pObjTorqueActualValue = (EC_T_SWORD*)pbyPdVarPtr;
                break;
            default:
                wIndex -= DS402_SLOT_INDEX_INCREMENT;
                ++wAxis;
                continue;
            }

            /* break after finding correct axis */
            break;
        }
    }

Exit:
    OsSafeFree(pSlaveProcVarInfoEntries);
    return dwRes;
}

EC_T_DWORD EcSimulatorDs402::MapOutputObjects()
{
    EC_T_DWORD dwRes = EC_E_ERROR;
    EC_T_BYTE* pbyPdOut = esGetProcessImageOutputPtr(m_dwInstanceId);
    EC_T_WORD wSlaveOutpVarNumOf = 0;
    EC_T_WORD wSlaveOutpVarNum   = 0;
    EC_PT_PROCESS_VAR_INFO_EX pSlaveProcVarInfoEntries = EC_NULL;

    dwRes = esGetSlaveOutpVarInfoNumOf(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    pSlaveProcVarInfoEntries = (EC_PT_PROCESS_VAR_INFO_EX)OsMalloc(wSlaveOutpVarNumOf * sizeof(EC_T_PROCESS_VAR_INFO_EX));
    if (EC_NULL == pSlaveProcVarInfoEntries)
    {
        dwRes = EC_E_NOMEMORY;
        goto Exit;
    }

    dwRes = esGetSlaveOutpVarInfoEx(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, wSlaveOutpVarNumOf, pSlaveProcVarInfoEntries, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    for(wSlaveOutpVarNum = 0; wSlaveOutpVarNum < wSlaveOutpVarNumOf; wSlaveOutpVarNum++)
    {
        EC_PT_PROCESS_VAR_INFO_EX poVarInfoEx = &pSlaveProcVarInfoEntries[wSlaveOutpVarNum];
        EC_T_BYTE* pbyPdVarPtr = &pbyPdOut[poVarInfoEx->nBitOffs / 8];
        EC_T_WORD  wAxisIdx = 0;
        EC_T_WORD  wIndex = poVarInfoEx->wIndex;

        while ((wIndex >= DS402_SLOT_INDEX_INCREMENT) && (wAxisIdx < m_wAxisCnt))
        {
            switch (wIndex)
            {
            case EC_DS402_OBJ_CONTROL_WORD:
                m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjControlWord = (EC_T_WORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_MODES_OF_OPERATION:
                m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjModesOfOperation = (EC_T_SWORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_TARGET_POSITION:
                m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjTargetPosition = (EC_T_SDWORD*)pbyPdVarPtr;
                break;
            case EC_DS402_OBJ_TARGET_VELOCITY:
                m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjTargetVelocity = (EC_T_SDWORD*)pbyPdVarPtr;
                break;
            default:
                wIndex -= DS402_SLOT_INDEX_INCREMENT;
                wAxisIdx++;
                continue;
            }

            /* break after finding correct axis */
            break;
        }
    }

Exit:
    OsSafeFree(pSlaveProcVarInfoEntries);
    return dwRes;
}

EC_T_DWORD EcSimulatorDs402::InitAxesCount()
{
    EC_T_DWORD dwRes = EC_E_ERROR;
    EC_T_WORD wSlaveOutpVarNumOf = 0;
    EC_T_WORD wSlaveOutpVarNum   = 0;
    EC_PT_PROCESS_VAR_INFO_EX pSlaveProcVarInfoEntries = EC_NULL;

    dwRes = esGetSlaveOutpVarInfoNumOf(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    pSlaveProcVarInfoEntries = (EC_PT_PROCESS_VAR_INFO_EX)OsMalloc(wSlaveOutpVarNumOf * sizeof(EC_T_PROCESS_VAR_INFO_EX));
    if (EC_NULL == pSlaveProcVarInfoEntries)
    {
        dwRes = EC_E_NOMEMORY;
        goto Exit;
    }

    dwRes = esGetSlaveOutpVarInfoEx(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, wSlaveOutpVarNumOf, pSlaveProcVarInfoEntries, &wSlaveOutpVarNumOf);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    /* count axis by counting control words, since each axis requires a control word */
    for (wSlaveOutpVarNum = 0; wSlaveOutpVarNum < wSlaveOutpVarNumOf; wSlaveOutpVarNum++)
    {
        EC_PT_PROCESS_VAR_INFO_EX poVarInfoEx = &pSlaveProcVarInfoEntries[wSlaveOutpVarNum];
        EC_T_WORD wIndex = poVarInfoEx->wIndex;

        if (wIndex >= EC_DS402_OBJ_CONTROL_WORD)
        {
            EC_T_WORD wSlotOffset = (EC_T_WORD)(wIndex - EC_DS402_OBJ_CONTROL_WORD);
            if (0 == wSlotOffset % DS402_SLOT_INDEX_INCREMENT)
            {
                EC_T_WORD wAxis = (EC_T_WORD)(wSlotOffset / DS402_SLOT_INDEX_INCREMENT);
                if (wAxis + 1 > m_wAxisCnt)
                {
                    m_wAxisCnt = (EC_T_WORD)(wAxis + 1);
                }
            }
        }
    }

    m_aoAxes = (TCiA402Axis*)OsMalloc(m_wAxisCnt * sizeof(TCiA402Axis));
    if (EC_NULL == m_aoAxes)
    {
        dwRes = EC_E_NOMEMORY;
        goto Exit;
    }

Exit:
    OsSafeFree(pSlaveProcVarInfoEntries);
    return dwRes;
}


EC_T_DWORD EcSimulatorDs402::InitInstance(EC_T_DWORD dwInstanceId, EC_T_WORD wSlaveAddress)
{
    EC_T_DWORD dwRes = EC_E_ERROR;
    EC_T_WORD wAxisIdx = 0;

    dwRes = esGetCfgSlaveInfo(dwInstanceId, EC_TRUE, wSlaveAddress, &m_oCfgSlaveInfo);
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    m_dwInstanceId = dwInstanceId;
    m_wSlaveAddress = wSlaveAddress;
    m_dwSlaveId = esGetSlaveId(m_dwInstanceId, m_wSlaveAddress);

    dwRes = InitAxesCount();
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    for (wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        /*Reset Axis buffer*/
        OsMemset(&m_aoAxes[wAxisIdx], 0, sizeof(TCiA402Axis));

        m_aoAxes[wAxisIdx].bAxisIsActive = EC_FALSE;
        m_aoAxes[wAxisIdx].bBrakeApplied = EC_TRUE;
        m_aoAxes[wAxisIdx].bLowLevelPowerApplied = EC_TRUE;
        m_aoAxes[wAxisIdx].bHighLevelPowerApplied = EC_FALSE;
        m_aoAxes[wAxisIdx].bAxisFunctionEnabled = EC_FALSE;
        m_aoAxes[wAxisIdx].bConfigurationAllowed = EC_TRUE;

        m_aoAxes[wAxisIdx].i16State = EC_DS402_STATE_NOT_READY_TO_SWITCH_ON;
        m_aoAxes[wAxisIdx].u16PendingOptionCode = 0x00;

        m_aoAxes[wAxisIdx].fCurPosition = 0;
        m_aoAxes[wAxisIdx].u32CycleTime = 0;


        /***********************************
            init objects
        *************************************/

        /*set default values*/
        OsMemcpy(&m_aoAxes[wAxisIdx].Objects, &DefCiA402ObjectValues, sizeof(CiA402Objects));
    }

    dwRes = MapInputObjects();
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

    dwRes = MapOutputObjects();
    if (EC_E_NOERROR != dwRes)
    {
        goto Exit;
    }

Exit:
    return dwRes;
}


EC_T_DWORD EcSimulatorDs402::InstallInstance()
{
    EC_T_DWORD dwRes = EC_E_NOERROR;
    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (NULL != m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjControlWord)
        {
            dwRes = esSetSlaveCoeObjectTransferCallbacks(m_dwInstanceId, m_wSlaveAddress, (EC_T_WORD)(EC_DS402_OBJ_MODES_OF_OPERATION + DS402_SLOT_INDEX_INCREMENT * wAxisIdx), EC_NULL, OBJ_WriteObject0x6060, this);
            if (EC_E_NOERROR != dwRes)
            {
                goto Exit;
            }
        }
    }

Exit:
    return dwRes;
}

/////////////////////////////////////////////////////////////////////////////////////////
/**
 \brief    CiA402_DummyMotionControl
 \brief this functions provides an simple feedback functionality
*////////////////////////////////////////////////////////////////////////////////////////
EC_T_VOID EcSimulatorDs402::CiA402_DummyMotionControl(TCiA402Axis* pCiA402Axis)
{
    float IncFactor    = (float)0.0010922 * (float) pCiA402Axis->u32CycleTime;

    EC_T_SDWORD i32TargetVelocity = 0;
    /*Motion Controller shall only be triggered if application is trigger by DC Sync Signals,
    and a valid mode of operation is set*/

    /*calculate actual position */
    pCiA402Axis->fCurPosition += ((double)pCiA402Axis->Objects.objVelocityActualValue) * IncFactor;
    pCiA402Axis->Objects.objPositionActualValue = (EC_T_SDWORD)(pCiA402Axis->fCurPosition);

    if(pCiA402Axis->bAxisFunctionEnabled &&
       pCiA402Axis->bLowLevelPowerApplied &&
       pCiA402Axis->bHighLevelPowerApplied &&
       !pCiA402Axis->bBrakeApplied)
    {
        if((pCiA402Axis->Objects.objSoftwarePositionLimit.i32MaxLimit > pCiA402Axis->Objects.objPositionActualValue
            || pCiA402Axis->Objects.objPositionActualValue > pCiA402Axis->Objects.objTargetPosition) &&
            (pCiA402Axis->Objects.objSoftwarePositionLimit.i32MinLimit < pCiA402Axis->Objects.objPositionActualValue
            || pCiA402Axis->Objects.objPositionActualValue < pCiA402Axis->Objects.objTargetPosition))
        {
            pCiA402Axis->Objects.objStatusWord &= ~EC_DS402_STATUSWORD_INTERNAL_LIMIT;

            switch(pCiA402Axis->Objects.objModesOfOperationDisplay)
            {
            case EC_DS402_CYCLIC_SYNC_POSITION_MODE:
                if (IncFactor != 0)
                {
                    i32TargetVelocity = (pCiA402Axis->Objects.objTargetPosition - pCiA402Axis->Objects.objPositionActualValue) / ((long)IncFactor);
                }
                else
                {
                    i32TargetVelocity = 0;
                }
//acontis change start
                if(pCiA402Axis->Objects.objTargetPosition - pCiA402Axis->Objects.objPositionActualValue == 0)
                {
                    pCiA402Axis->Objects.objStatusWord |= EC_DS402_STATUSWORD_TARGET_REACHED;
                }
                else
                {
                    pCiA402Axis->Objects.objStatusWord &= ~EC_DS402_STATUSWORD_TARGET_REACHED;
                }
//acontis change end
                break;
            case EC_DS402_CYCLIC_SYNC_VELOCITY_MODE:
                if (pCiA402Axis->i16State == EC_DS402_STATE_OPERATION_ENABLED)
                {
                    i32TargetVelocity = pCiA402Axis->Objects.objTargetVelocity;
                }
                else
                {
                    i32TargetVelocity = 0;
                }
                break;
            default:
                break;
            }
        }
        else
        {
            pCiA402Axis->Objects.objStatusWord |= EC_DS402_STATUSWORD_INTERNAL_LIMIT;
        }
    }

    pCiA402Axis->Objects.objVelocityActualValue = i32TargetVelocity;

    /*Accept new mode of operation*/
    pCiA402Axis->Objects.objModesOfOperationDisplay = pCiA402Axis->Objects.objModesOfOperation;

}

/////////////////////////////////////////////////////////////////////////////////////////
/**
 \return TRUE if moving on predefined ramp is finished

 \brief    CiA402-TransitionAction
 \brief this function shall calculate the desired Axis input values to move on a predefined ramp
 \brief if the ramp is finished return TRUE
*////////////////////////////////////////////////////////////////////////////////////////
EC_T_BOOL EcSimulatorDs402::CiA402_TransitionAction(EC_T_SWORD Characteristic)
{
    switch(Characteristic)
    {
    case EC_DS402_SLOW_DOWN_RAMP:
    case EC_DS402_QUICKSTOP_RAMP:
    case EC_DS402_STOP_ON_CURRENT_LIMIT:
    case EC_DS402_STOP_ON_VOLTAGE_LIMIT:
        return EC_TRUE;
    default:
        return EC_FALSE;
    }
}



/////////////////////////////////////////////////////////////////////////////////////////
/**
 \brief    CiA402-Application
 \brief check if a state transition is pending and pass desired ramp-code to CiA402TransitionAction()
 \brief if this functions returns true the state transition is finished.
*////////////////////////////////////////////////////////////////////////////////////////
EC_T_VOID EcSimulatorDs402::CiA402_Application(TCiA402Axis *pCiA402Axis)
{
    /*clear "Drive follows the command value" flag if the target values from the master overwritten by the local application*/
    if(pCiA402Axis->u16PendingOptionCode != 0 &&
        (pCiA402Axis->Objects.objModesOfOperationDisplay == EC_DS402_CYCLIC_SYNC_POSITION_MODE ||
        pCiA402Axis->Objects.objModesOfOperationDisplay == EC_DS402_CYCLIC_SYNC_VELOCITY_MODE))
    {
        pCiA402Axis->Objects.objStatusWord &= ~ EC_DS402_STATUSWORD_DRIVE_FOLLOWS_COMMAND;
    }
    else
    {
        pCiA402Axis->Objects.objStatusWord |= EC_DS402_STATUSWORD_DRIVE_FOLLOWS_COMMAND;
    }


    switch(pCiA402Axis->u16PendingOptionCode)
    {
    case 0x605A:
        /* state transition 11 is pending analyse shutdown option code (0x605A) */
        {
            EC_T_WORD ramp = pCiA402Axis->Objects.objQuickStopOptionCode;


            /* masked and execute specified quick stop ramp characteristic */
            if(pCiA402Axis->Objects.objQuickStopOptionCode > 4 && pCiA402Axis->Objects.objQuickStopOptionCode < 9)
            {
//acontis change start
                if (pCiA402Axis->Objects.objQuickStopOptionCode == 5)
                {
                    ramp = EC_DS402_SLOW_DOWN_RAMP;
                }
                if (pCiA402Axis->Objects.objQuickStopOptionCode == 6)
                {
                    ramp = EC_DS402_QUICKSTOP_RAMP;
                }
                if (pCiA402Axis->Objects.objQuickStopOptionCode == 7)
                {
                    ramp = EC_DS402_STOP_ON_CURRENT_LIMIT;
                }
                if (pCiA402Axis->Objects.objQuickStopOptionCode == 8)
                {
                    ramp = EC_DS402_STOP_ON_VOLTAGE_LIMIT;
                }
//acontis change end
            }

            if(CiA402_TransitionAction(ramp))
            {
                /* quick stop ramp is finished complete state transition */
                pCiA402Axis->u16PendingOptionCode = 0x0;
                if(pCiA402Axis->Objects.objQuickStopOptionCode > 0 && pCiA402Axis->Objects.objQuickStopOptionCode < 5)
                {
                    pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED;    // continue state transition 12
                }
                else if (pCiA402Axis->Objects.objQuickStopOptionCode > 4 && pCiA402Axis->Objects.objQuickStopOptionCode < 9)
                {
                    pCiA402Axis->Objects.objStatusWord |= EC_DS402_STATUSWORD_TARGET_REACHED;
                }
            }
        }
        break;
    case 0x605B:
        /* state transition 8 is pending analyse shutdown option code (0x605B) */
        {
            if(CiA402_TransitionAction(pCiA402Axis->Objects.objShutdownOptionCode))
            {
                /* shutdown ramp is finished complete state transition */
                pCiA402Axis->u16PendingOptionCode = 0x0;
                pCiA402Axis->i16State = EC_DS402_STATE_READY_TO_SWITCH_ON;    // continue state transition 8
            }
        }
        break;
    case 0x605C:
        /* state transition 5 is pending analyse Disable operation option code (0x605C) */
        {
            if(CiA402_TransitionAction(pCiA402Axis->Objects.objDisableOperationOptionCode))
            {
                /* disable operation ramp is finished complete state transition */
                pCiA402Axis->u16PendingOptionCode = 0x0;
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCHED_ON;  // continue state transition 5
            }
        }
        break;

    case 0x605E:
        /*state transition 14 is pending analyse Fault reaction option code (0x605E)*/
        {
            if(CiA402_TransitionAction(pCiA402Axis->Objects.objFaultReactionCode))
            {
                /* fault reaction ramp is finished complete state transition */
                pCiA402Axis->u16PendingOptionCode = 0x0;
                pCiA402Axis->i16State = EC_DS402_STATE_FAULT;    // continue state transition 14
            }
        }
        break;
    default:
        // pending transition code is invalid => values from the master are used
        pCiA402Axis->Objects.objStatusWord |=  EC_DS402_STATUSWORD_DRIVE_FOLLOWS_COMMAND;
        break;
    }

    CiA402_DummyMotionControl(pCiA402Axis);
}


/////////////////////////////////////////////////////////////////////////////////////////
/**
 \brief    CiA402-Statemachine
        This function handles the state machine for devices using the CiA402 profile.
        called cyclic from MainLoop()
        All described transition numbers are referring to the document
        "ETG Implementation Guideline for the CiA402 Axis Profile" located on the EtherCAT.org download section

*////////////////////////////////////////////////////////////////////////////////////////
EC_T_VOID EcSimulatorDs402::CiA402_StateMachine(EC_T_VOID)
{
    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (!m_aoAxes[wAxisIdx].bAxisIsActive)
        {
            continue;
        }

        TCiA402Axis* pCiA402Axis = &m_aoAxes[wAxisIdx];
        EC_T_WORD StatusWord = pCiA402Axis->Objects.objStatusWord;
        EC_T_WORD ControlWord6040 = pCiA402Axis->Objects.objControlWord;
        EC_T_WORD wCurrDevState = 0;
        EC_T_WORD wReqDevState = 0;

        /* clear statusword state and controlword processed complete bits */
        StatusWord &= ~(EC_DS402_STATUSWORD_STATE_MASK | EC_DS402_STATUSWORD_REMOTE);

        /* skip state state transition if the previous transition is pending */
        if (pCiA402Axis->u16PendingOptionCode!= 0x0)
        {
            return;
        }


        if (esGetSlaveState(m_dwInstanceId, m_dwSlaveId, &wCurrDevState, &wReqDevState) != 0) {
            continue;
        }

        /* skip transition 1 and 2 */
        if (pCiA402Axis->i16State < EC_DS402_STATE_READY_TO_SWITCH_ON && (DEVICE_STATE_OP == (wCurrDevState & DEVICE_STATE_MASK)))
        {
            pCiA402Axis->i16State = EC_DS402_STATE_READY_TO_SWITCH_ON;
        }

        switch(pCiA402Axis->i16State)
        {
        case EC_DS402_STATE_NOT_READY_TO_SWITCH_ON:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_NOTREADYTOSWITCHON);
            if(DEVICE_STATE_OP == (wCurrDevState & DEVICE_STATE_MASK))
            {
                // Automatic transition -> Communication shall be activated
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 1
            }
            else
            {
                /*
                CiA402 statemachine shall stay in "EC_STATE_NOT_READY_TO_SWITCH_ON" if EtherCAT state is not OP.
                */
                pCiA402Axis->i16State = EC_DS402_STATE_NOT_READY_TO_SWITCH_ON; // stay in current state
            }

            break;
        case EC_DS402_STATE_SWITCH_ON_DISABLED:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_SWITCHEDONDISABLED);
            if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN_MASK) == EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN)
            {
                pCiA402Axis->i16State = EC_DS402_STATE_READY_TO_SWITCH_ON; // Transition 2
            }
            break;
        case EC_DS402_STATE_READY_TO_SWITCH_ON:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_READYTOSWITCHON);
            if (((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP_MASK) == EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP)
                || ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE_MASK) == EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE))
            {
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 7
            }
            else if (((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_SWITCHON_MASK) == EC_DS402_CONTROLWORD_COMMAND_SWITCHON) ||
                    ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_ENABLEOPERATION_MASK) == EC_DS402_CONTROLWORD_COMMAND_ENABLEOPERATION))
                {
                    pCiA402Axis->i16State = EC_DS402_STATE_SWITCHED_ON;           // Transition 3
                }
                break;
        case EC_DS402_STATE_SWITCHED_ON:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_SWITCHEDON);

            if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN_MASK) == EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN)
            {
                pCiA402Axis->i16State = EC_DS402_STATE_READY_TO_SWITCH_ON; // Transition 6

            }
            else if (((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP_MASK) == EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP
                    || (ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE_MASK) == EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE))
                {
                    pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 10

                }
            else if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_ENABLEOPERATION_MASK) == EC_DS402_CONTROLWORD_COMMAND_ENABLEOPERATION)
                    {
                        pCiA402Axis->i16State = EC_DS402_STATE_OPERATION_ENABLED;  // Transition 4
                        //The Axis function shall be enabled and all internal set-points cleared.
                    }
                    break;
        case EC_DS402_STATE_OPERATION_ENABLED:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_OPERATIONENABLED);

            if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_DISABLEOPERATION_MASK) == EC_DS402_CONTROLWORD_COMMAND_DISABLEOPERATION)
            {
                if(pCiA402Axis->Objects.objDisableOperationOptionCode!= EC_DS402_DISABLE_DRIVE)
                {
                    /*disable operation pending*/
                    pCiA402Axis->u16PendingOptionCode = 0x605C; //STATE_TRANSITION (EC_STATE_OPERATION_ENABLED,EC_STATE_SWITCHED_ON);
                    return;
                }
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCHED_ON;           // Transition 5
            } else {
                if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP_MASK) == EC_DS402_CONTROLWORD_COMMAND_QUICKSTOP)
                {
                    pCiA402Axis->i16State = EC_DS402_STATE_QUICK_STOP_ACTIVE;  // Transition 11
                } else {
                    if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN_MASK) == EC_DS402_CONTROLWORD_COMMAND_SHUTDOWN)
                    {
                        if(pCiA402Axis->Objects.objShutdownOptionCode != EC_DS402_DISABLE_DRIVE)
                        {
                            /*shutdown operation required*/
                            pCiA402Axis->u16PendingOptionCode = 0x605B; //STATE_TRANSITION (EC_STATE_OPERATION_ENABLED,EC_STATE_READY_TO_SWITCH_ON);
                            return;
                        }

                        pCiA402Axis->i16State = EC_DS402_STATE_READY_TO_SWITCH_ON; // Transition 8

                    } else {
                        if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE_MASK) == EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE)
                        {
                            pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 9
                        }
                    }
                }
            }
            break;
        case EC_DS402_STATE_QUICK_STOP_ACTIVE:
            StatusWord |= EC_DS402_STATUSWORD_STATE_QUICKSTOPACTIVE;

            if((pCiA402Axis->Objects.objQuickStopOptionCode != EC_DS402_DISABLE_DRIVE) &&
                ((pCiA402Axis->Objects.objStatusWord & EC_DS402_STATUSWORD_STATE_MASK)!= EC_DS402_STATUSWORD_STATE_QUICKSTOPACTIVE))
            {
                /* Only execute quick stop action in state transition 11 */
                pCiA402Axis->u16PendingOptionCode = 0x605A; // STATE_TRANSITION (EC_STATE_OPERATION_ENABLED,EC_STATE_QUICK_STOP_ACTIVE);
                return;
            }

            if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE_MASK) == EC_DS402_CONTROLWORD_COMMAND_DISABLEVOLTAGE)
            {
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 12
            }

            /* NOTE: it is not recommend to support transition 16 */
            break;
        case EC_DS402_STATE_FAULT_REACTION_ACTIVE:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_FAULTREACTIONACTIVE);
            if(pCiA402Axis->Objects.objFaultReactionCode != EC_DS402_DISABLE_DRIVE)
            {
                /* fault reaction pending */
                pCiA402Axis->u16PendingOptionCode = 0x605E;
                return;
            }

            // Automatic transition
            pCiA402Axis->i16State = EC_DS402_STATE_FAULT; // Transition 14
            break;
        case EC_DS402_STATE_FAULT:
            StatusWord |= (EC_DS402_STATUSWORD_STATE_FAULT);

            if ((ControlWord6040 & EC_DS402_CONTROLWORD_COMMAND_FAULTRESET_MASK) == EC_DS402_CONTROLWORD_COMMAND_FAULTRESET)
            {
                pCiA402Axis->i16State = EC_DS402_STATE_SWITCH_ON_DISABLED; // Transition 15
            }
            break;

        default:    // the state variable is set to in invalid value => rest Axis
            StatusWord = (EC_DS402_STATUSWORD_STATE_NOTREADYTOSWITCHON);
            pCiA402Axis->i16State = EC_DS402_STATE_FAULT_REACTION_ACTIVE;
            break;

        } // switch(current state)



        /* Update operational functions (the low level power supply is always TRUE */
        switch(pCiA402Axis->i16State)
        {
        case EC_DS402_STATE_NOT_READY_TO_SWITCH_ON:
        case EC_DS402_STATE_SWITCH_ON_DISABLED:
        case EC_DS402_STATE_READY_TO_SWITCH_ON:
            pCiA402Axis->bBrakeApplied = EC_TRUE;
            pCiA402Axis->bHighLevelPowerApplied =  EC_FALSE;
            pCiA402Axis->bAxisFunctionEnabled = EC_FALSE;
            pCiA402Axis->bConfigurationAllowed = EC_TRUE;
            break;
        case EC_DS402_STATE_SWITCHED_ON:
            pCiA402Axis->bBrakeApplied = EC_TRUE;
            pCiA402Axis->bHighLevelPowerApplied =  EC_TRUE;
            pCiA402Axis->bAxisFunctionEnabled = EC_FALSE;
            pCiA402Axis->bConfigurationAllowed = EC_TRUE;
            break;
        case EC_DS402_STATE_OPERATION_ENABLED:
        case EC_DS402_STATE_QUICK_STOP_ACTIVE:
        case EC_DS402_STATE_FAULT_REACTION_ACTIVE:
            pCiA402Axis->bBrakeApplied = EC_FALSE;
            pCiA402Axis->bHighLevelPowerApplied =  EC_TRUE;
            pCiA402Axis->bAxisFunctionEnabled = EC_TRUE;
            pCiA402Axis->bConfigurationAllowed = EC_FALSE;
            break;
        case EC_DS402_STATE_FAULT:
            pCiA402Axis->bBrakeApplied = EC_TRUE;
            pCiA402Axis->bHighLevelPowerApplied =  EC_FALSE;
            pCiA402Axis->bAxisFunctionEnabled = EC_FALSE;
            pCiA402Axis->bConfigurationAllowed = EC_TRUE;
            break;
        default:
            pCiA402Axis->bBrakeApplied = EC_TRUE;
            pCiA402Axis->bHighLevelPowerApplied = EC_FALSE;
            pCiA402Axis->bAxisFunctionEnabled = EC_FALSE;
            pCiA402Axis->bConfigurationAllowed = EC_TRUE;
            break;
        }

        if (pCiA402Axis->bHighLevelPowerApplied == EC_TRUE)
        {
            StatusWord |= EC_DS402_STATUSWORD_VOLTAGE_ENABLED;
        }
        else
        {
            StatusWord &= ~EC_DS402_STATUSWORD_VOLTAGE_ENABLED;
        }

        /* state transition finished set controlword complete bit and update status object 0x6041 */
        pCiA402Axis->Objects.objStatusWord = (EC_T_WORD)(StatusWord | EC_DS402_STATUSWORD_REMOTE);
    }
}

EC_T_WORD EcSimulatorDs402::APPL_StartInputHandler(EC_T_WORD* pIntMask)
{
    EC_UNREFPARM(pIntMask);

    /* cycle time */
    EC_T_DWORD dwSync0CycleTime = 0;
    esReadSlaveRegister(m_dwInstanceId, EC_TRUE, m_wSlaveAddress, 0x09A0 /* ESC_DC_SYNC0_CYCLETIME_OFFSET */, (EC_T_BYTE*)&dwSync0CycleTime, 4, 5000);
    dwSync0CycleTime = EC_GET_FRM_DWORD(&dwSync0CycleTime);

    /* activate */
    for (EC_T_WORD wAxisIdx = 0; wAxisIdx < m_wAxisCnt; wAxisIdx++)
    {
        if (NULL != m_aoAxes[wAxisIdx].oCiA402ObjectsPointers.pObjControlWord)
        {
            m_aoAxes[wAxisIdx].bAxisIsActive = EC_TRUE;
        }
        m_aoAxes[wAxisIdx].u32CycleTime = (0 != dwSync0CycleTime) ? (dwSync0CycleTime / 1000) : 1000; /* fall-back to 1ms */
    }

    return 0;
}

EC_T_VOID EC_FNCALL EcSimulatorDs402::OBJ_WriteObject0x6060(EC_T_VOID* pvContext, EC_T_DWORD dwInstanceId, EC_T_WORD wSlaveAddress,
    EC_T_WORD wIndex, EC_T_BYTE bySubindex, EC_T_DWORD dwSize, EC_T_BYTE* pbyData,
    EC_T_BOOL bCompleteAccess, EC_T_BOOL bCheckWriteAccess, EC_T_DWORD* pdwErrorCode)
{
    EC_UNREFPARM(dwInstanceId);
    EC_UNREFPARM(wSlaveAddress); EC_UNREFPARM(bySubindex); EC_UNREFPARM(dwSize); 
    EC_UNREFPARM(bCompleteAccess); EC_UNREFPARM(bCheckWriteAccess);
    
    EC_T_WORD wAxis = (EC_T_WORD)((wIndex - EC_DS402_OBJ_MODES_OF_OPERATION) / DS402_SLOT_INDEX_INCREMENT);
    ((EcSimulatorDs402*)pvContext)->m_aoAxes[wAxis].Objects.objModesOfOperation = EC_GET_FRM_WORD((EC_T_WORD*)pbyData);

    *pdwErrorCode = EC_E_NOERROR;
}

EcSimulatorDemoMotion::~EcSimulatorDemoMotion()
{
    SafeDeleteArray(m_pApplContexts);
    OsSafeFree(m_pSscApplDescs);
}

EC_T_DWORD EcSimulatorDemoMotion::InitInstance(EC_T_LOG_PARMS* pLogParms, DS402_T_INIT_PARMS* poInitParms)
{
    EC_T_DWORD dwRes = EC_E_NOERROR;
    EC_T_DWORD dwDriveIdx = 0;
    m_pLogParms = pLogParms;

    m_pApplContexts = EC_NEW(EcSimulatorDs402)[poInitParms->dwNumSlaves];
    if (EC_NULL == m_pApplContexts)
    {
        dwRes = EC_E_NOMEMORY;
        goto Error;
    }

    m_pSscApplDescs = (EC_T_SLAVE_SSC_APPL_DESC*)OsMalloc(poInitParms->dwNumSlaves * sizeof(EC_T_SLAVE_SSC_APPL_DESC));
    if (EC_NULL == m_pSscApplDescs)
    {
        dwRes = EC_E_NOMEMORY;
        goto Error;
    }
    OsMemset(m_pSscApplDescs, 0, poInitParms->dwNumSlaves * sizeof(EC_T_SLAVE_SSC_APPL_DESC));

    for (dwDriveIdx = 0; dwDriveIdx < poInitParms->dwNumSlaves; ++dwDriveIdx)
    {
        EC_T_WORD wDriveFixedAddr = poInitParms->pSlaveAddr[dwDriveIdx];

        dwRes = m_pApplContexts[dwDriveIdx].InitInstance(poInitParms->dwInstanceId, wDriveFixedAddr);

        if (dwRes != EC_E_NOERROR)
        {
            goto Error;
        }

        m_pSscApplDescs[dwDriveIdx].dwSignature = SIMULATOR_SIGNATURE;
        m_pSscApplDescs[dwDriveIdx].dwSize = sizeof(EC_T_SLAVE_SSC_APPL_DESC);
        m_pSscApplDescs[dwDriveIdx].pvContext = &m_pApplContexts[dwDriveIdx];
        m_pSscApplDescs[dwDriveIdx].pfnInputMapping = EcSimulatorDs402::APPL_InputMappingWrapper;
        m_pSscApplDescs[dwDriveIdx].pfnOutputMapping = EcSimulatorDs402::APPL_OutputMappingWrapper;
        m_pSscApplDescs[dwDriveIdx].pfnApplication = EcSimulatorDs402::APPL_ApplicationWrapper;
        m_pSscApplDescs[dwDriveIdx].pfnStartInputHandler = EcSimulatorDs402::APPL_StartInputHandlerWrapper;

        dwRes = esSetSlaveSscApplication(poInitParms->dwInstanceId, wDriveFixedAddr, &m_pSscApplDescs[dwDriveIdx]);
        if (dwRes != EC_E_NOERROR)
        {
            goto Error;
        }

        dwRes = m_pApplContexts[dwDriveIdx].InstallInstance();
        if (dwRes != EC_E_NOERROR)
        {
            goto Error;
        }
    }

    return dwRes;

Error:
    for (dwDriveIdx = 0; dwDriveIdx < poInitParms->dwNumSlaves; ++dwDriveIdx)
    {
        EC_T_SLAVE_SSC_APPL_DESC aSscApplDesc;
        OsMemset(&aSscApplDesc, 0, sizeof(EC_T_SLAVE_SSC_APPL_DESC));
        aSscApplDesc.dwSignature = SIMULATOR_SIGNATURE;
        aSscApplDesc.dwSize = sizeof(EC_T_SLAVE_SSC_APPL_DESC);

        esSetSlaveSscApplication(poInitParms->dwInstanceId, poInitParms->pSlaveAddr[dwDriveIdx], &aSscApplDesc);
    }

    SafeDeleteArray(m_pApplContexts);
    OsSafeFree(m_pSscApplDescs);
    return dwRes;
}