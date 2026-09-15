/** ---------------------------------------------------------------------------
 * \file        EcSimulatorDs402.h
 * \brief       DS402 Slave Simulation
 * \author      Max Bachmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#include "EcSimulator.h"
#include "EthernetServices.h"

#ifndef INC_EC_SIMULATOR_DS402
#define INC_EC_SIMULATOR_DS402

/*-DEFINES-------------------------------------------------------------------*/
/** 
 * For Multi-Axis motors the objects for each axis are defined by the following rule:
 * Axis No | PDO Entries
 * 1       | EC_DS402_OBJ_*
 * 2       | EC_DS402_OBJ_* + DS402_SLOT_INDEX_INCREMENT
 * n       | EC_DS402_OBJ_* + (n - 1) * DS402_SLOT_INDEX_INCREMENT
 * 
 * see ESI file in Descriptions/Groups/Device/Slots/SlotIndexIncrement
 */
#define DS402_SLOT_INDEX_INCREMENT ((EC_T_WORD)0x800)

/*-TYPEDEFS------------------------------------------------------------------*/
struct EcSimulatorDs402 {
    /** \brief 0x607D (Software Position Limit) data structure*/
    struct TOBJ607D {
       EC_T_SDWORD i32MinLimit; /**< \brief Minimum limit*/
       EC_T_SDWORD i32MaxLimit; /**< \brief Maximum limit*/
    };

    struct CiA402Objects {
        EC_T_WORD   objErrorCode;                  /**< \brief Error Code (0x603F)*/
        EC_T_WORD   objControlWord;                /**< \brief Control Word (0x6040)*/
        EC_T_WORD   objStatusWord;                 /**< \brief Status Word (0x6041)*/
        EC_T_SWORD  objQuickStopOptionCode;        /**< \brief Quick Stop Option Code (0x605A)*/
        EC_T_SWORD  objShutdownOptionCode;         /**< \brief Shutdown Option Code (0x605B)*/
        EC_T_SWORD  objDisableOperationOptionCode; /**< \brief Disable Operation Option Code (0x605C)*/
        EC_T_SWORD  objFaultReactionCode;          /**< \brief Fault Reaction Code (0x605E)*/
        EC_T_SWORD  objModesOfOperation;           /**< \brief Modes of Operation (0x6060)*/
        EC_T_SWORD  objModesOfOperationDisplay;    /**< \brief Mode of Operation Display (0x6061)*/
        EC_T_SDWORD objPositionActualValue;        /**< \brief Position Actual Value (0x6064)*/
        EC_T_SDWORD objVelocityActualValue;        /**< \brief Actual Velocity Value (0x606C)*/
        EC_T_SWORD  objTorqueActualValue;          /**< \brief Torque Actual Value (0x6077)*/
        EC_T_SDWORD objTargetPosition;             /**< \brief Target Position (0x607A)*/
        TOBJ607D    objSoftwarePositionLimit;      /**< \brief Software Position limit (0x607D)*/
        EC_T_DWORD  objQuickStopDeclaration;       /**< \brief Quick Stop Declaration (0x6085)*/
        EC_T_SDWORD objTargetVelocity;             /**< \brief Target Velocity (0x60FF)*/
        EC_T_DWORD  objSupportedDriveModes;        /**< \brief Supported Drive Modes (0x6502)*/
    };

    struct CiA402ObjectsPointers {
        EC_T_WORD*   pObjErrorCode;                  /**< \brief Error Code (0x603F)*/
        EC_T_WORD*   pObjControlWord;                /**< \brief Control Word (0x6040)*/
        EC_T_WORD*   pObjStatusWord;                 /**< \brief Status Word (0x6041)*/
        EC_T_SWORD*  pObjQuickStopOptionCode;        /**< \brief Quick Stop Option Code (0x605A)*/
        EC_T_SWORD*  pObjShutdownOptionCode;         /**< \brief Shutdown Option Code (0x605B)*/
        EC_T_SWORD*  pObjDisableOperationOptionCode; /**< \brief Disable Operation Option Code (0x605C)*/
        EC_T_SWORD*  pObjFaultReactionCode;          /**< \brief Fault Reaction Code (0x605E)*/
        EC_T_SWORD*  pObjModesOfOperation;           /**< \brief Modes of Operation (0x6060)*/
        EC_T_SWORD*  pObjModesOfOperationDisplay;    /**< \brief Mode of Operation Display (0x6061)*/
        EC_T_SDWORD* pObjPositionActualValue;        /**< \brief Position Actual Value (0x6064)*/
        EC_T_SDWORD* pObjVelocityActualValue;        /**< \brief Actual Velocity Value (0x606C)*/
        EC_T_SWORD*  pObjTorqueActualValue;          /**< \brief Torque Actual Value (0x6077)*/
        EC_T_SDWORD* pObjTargetPosition;             /**< \brief Target Position (0x607A)*/
        EC_T_DWORD*  pObjQuickStopDeclaration;       /**< \brief Quick Stop Declaration (0x6085)*/
        EC_T_SDWORD* pObjTargetVelocity;             /**< \brief Target Velocity (0x60FF)*/
        EC_T_DWORD*  pObjSupportedDriveModes;        /**< \brief Supported Drive Modes (0x6502)*/
    };

    struct TCiA402Axis {
        EC_T_BOOL       bAxisIsActive;               /**< \brief Indicates if active is active*/
        EC_T_BOOL       bBrakeApplied;               /**< \brief Motor break is applied*/
        EC_T_BOOL       bLowLevelPowerApplied;       /**< \brief Low Level Power applied*/
        EC_T_BOOL       bHighLevelPowerApplied;      /**< \brief High Level Power applied*/
        EC_T_BOOL       bAxisFunctionEnabled;        /**< \brief Axis functions enabled*/
        EC_T_BOOL       bConfigurationAllowed;       /**< \brief Configuration allowed*/

        EC_T_WORD       i16State;                    /**< \brief Axis state*/
        EC_T_WORD       u16PendingOptionCode;        /**< \brief Pending operation code*/
        EC_T_LREAL      fCurPosition;                /**< \brief Current position within control loop*/
        EC_T_DWORD      u32CycleTime;                /**< \brief Motion controller cycletime in us*/

        CiA402Objects Objects;                       /**< \brief CiA402 Axis object variable*/
        CiA402ObjectsPointers oCiA402ObjectsPointers;
    };

    EcSimulatorDs402()
      : m_wAxisCnt(0), m_aoAxes(EC_NULL)
    {
        OsMemset(&m_oCfgSlaveInfo, 0, sizeof(EC_T_CFG_SLAVE_INFO));
    }

    ~EcSimulatorDs402()
    {
        OsSafeFree(m_aoAxes);
    }

    EC_T_DWORD InitInstance(EC_T_DWORD dwInstanceId, EC_T_WORD wCfgFixedAddress);
    EC_T_DWORD InstallInstance();

    EC_T_VOID APPL_InputMapping(EC_T_WORD* pData);
    static EC_T_VOID EC_FNCALL APPL_InputMappingWrapper(EC_T_VOID* pvContext, EC_T_DWORD /* dwSimulatorId */, EC_T_WORD /* wCfgFixedAddress */, EC_T_WORD* pData) {
        ((EcSimulatorDs402*)pvContext)->APPL_InputMapping(pData);
    }

    EC_T_VOID APPL_OutputMapping(EC_T_WORD* pData);
    static EC_T_VOID EC_FNCALL APPL_OutputMappingWrapper(EC_T_VOID* pvContext, EC_T_DWORD /* dwSimulatorId */, EC_T_WORD /* wCfgFixedAddress */, EC_T_WORD* pData) {
        ((EcSimulatorDs402*)pvContext)->APPL_OutputMapping(pData);
    }


    EC_T_VOID APPL_Application();
    static EC_T_VOID EC_FNCALL APPL_ApplicationWrapper(EC_T_VOID* pvContext, EC_T_DWORD /* dwSimulatorId */, EC_T_WORD /* wCfgFixedAddress */) {
        ((EcSimulatorDs402*)pvContext)->APPL_Application();
    }


    EC_T_WORD APPL_StartInputHandler(EC_T_WORD* pIntMask);
    static EC_T_WORD EC_FNCALL APPL_StartInputHandlerWrapper(EC_T_VOID* pvContext, EC_T_DWORD /* dwSimulatorId */, EC_T_WORD /* wCfgFixedAddress */, EC_T_WORD* pIntMask) {
        return ((EcSimulatorDs402*)pvContext)->APPL_StartInputHandler(pIntMask);
    }

    static EC_T_VOID EC_FNCALL OBJ_WriteObject0x6060(EC_T_VOID* pvContext, EC_T_DWORD dwInstanceId, EC_T_WORD wSlaveAddress,
        EC_T_WORD wIndex, EC_T_BYTE bySubindex, EC_T_DWORD dwSize, EC_T_BYTE* pbyData,
        EC_T_BOOL bCompleteAccess, EC_T_BOOL bCheckWriteAccess, EC_T_DWORD* pdwErrorCode);

private:
    EC_T_VOID CiA402_StateMachine(EC_T_VOID);
    EC_T_VOID CiA402_Application(TCiA402Axis *pCiA402Axis);
    EC_T_VOID CiA402_DummyMotionControl(TCiA402Axis* pCiA402Axis);
    EC_T_BOOL CiA402_TransitionAction(EC_T_SWORD Characteristic);
    EC_T_DWORD MapInputObjects();
    EC_T_DWORD MapOutputObjects();
    EC_T_DWORD InitAxesCount();

    EC_T_WORD           m_wAxisCnt;
    TCiA402Axis*        m_aoAxes;
    EC_T_DWORD          m_dwInstanceId;
    EC_T_WORD           m_wSlaveAddress;
    EC_T_DWORD          m_dwSlaveId;
    EC_T_CFG_SLAVE_INFO m_oCfgSlaveInfo;
};

struct DS402_T_INIT_PARMS {
    EC_T_DWORD dwInstanceId; /**< [in] Simulator instance ID */
    EC_T_DWORD dwNumSlaves;  /**< [in] Amount of slaves */
    EC_T_WORD* pSlaveAddr;   /**< [in] Slaves */
};

struct EcSimulatorDemoMotion {
    EcSimulatorDemoMotion()
      : m_pSscApplDescs(EC_NULL), m_pApplContexts(EC_NULL) {}

    ~EcSimulatorDemoMotion();

    EC_T_DWORD InitInstance(EC_T_LOG_PARMS* pLogParms, DS402_T_INIT_PARMS* initParms);

    EC_INLINESTART EC_T_LOG_PARMS* GetLogParms(EC_T_VOID)
                    { return m_pLogParms; } EC_INLINESTOP


private:
    EC_T_LOG_PARMS*     m_pLogParms;
    EC_T_SLAVE_SSC_APPL_DESC* m_pSscApplDescs;
    EcSimulatorDs402* m_pApplContexts;
};

#endif /* INC_EC_SIMULATOR_DS402 */