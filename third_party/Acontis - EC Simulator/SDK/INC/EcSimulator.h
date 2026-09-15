/** ---------------------------------------------------------------------------
 * \file
 * \brief       EC-Simulator
 * \author      Paul Bussmann
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#ifndef INC_ECSIMULATOR
#define INC_ECSIMULATOR 1

/*-PREDEFINES-FOR-INCLUDED-HEADERS-HEREIN------------------------------------*/
#undef  INSTANCE_MASTER_DEFAULT     /* always redefine to Simulator default value */
#define INSTANCE_MASTER_DEFAULT     ((EC_T_DWORD)0x00000000)

/*-INCLUDE-------------------------------------------------------------------*/
#ifndef INC_ECOS
#include "EcOs.h"
#endif
#ifndef INC_ECINTERFACECOMMON
#include "EcInterfaceCommon.h"
#endif
#ifndef INC_ECLINK
#include "EcLink.h"
#endif

/*-DEFINES/MACROS------------------------------------------------------------*/
#define SIMULATOR_SIGNATURE_PATTERN 0x7A200000
#define SIMULATOR_SIGNATURE EC_SIGNATURE_MAKE(SIMULATOR_SIGNATURE_PATTERN, EC_VERSION_MAJ, EC_VERSION_MIN, EC_VERSION_SERVICEPACK, EC_VERSION_BUILD)

#define SIMULATOR_SIGNATURE_SIL_PATTERN                0x00800000

/*-TYPEDEFS/ENUMS------------------------------------------------------------*/
#ifndef EC_SIMULATOR_DEVICE_CONNECTION_TYPE_AUTO
#define EC_SIMULATOR_DEVICE_CONNECTION_TYPE_AUTO         0
#define EC_SIMULATOR_DEVICE_CONNECTION_TYPE_SLAVE        1
#define EC_SIMULATOR_DEVICE_CONNECTION_TYPE_DEVICE       2
#define EC_SIMULATOR_DEVICE_CONNECTION_TYPE_DISCONNECTED 3

#include EC_PACKED_API_INCLUDESTART
typedef struct _EC_T_SIMULATOR_DEVICE_CONNECTION_DESC
{
    EC_T_DWORD dwType;                /* EC_SIMULATOR_DEVICE_CONNECTION_TYPE... */
    EC_T_DWORD dwInstanceID;          /* EC-Simulator Instance ID */
    EC_T_WORD  wCfgFixedAddress;      /* EC-Simulator Configuration (ENI/EXI) */
    EC_T_BYTE  byPort;                /* 0...3: Port A-D */
} EC_PACKED_API EC_T_SIMULATOR_DEVICE_CONNECTION_DESC;
#include EC_PACKED_INCLUDESTOP
#endif

#include EC_PACKED_API_INCLUDESTART
typedef struct _EC_T_SIMULATOR_INIT_PARMS
{
    EC_T_DWORD               dwSignature;                      /**< [in] Set to SIMULATOR_SIGNATURE */
    EC_T_DWORD               dwSize;                           /**< [in] Set to sizeof(EC_T_SIMULATOR_INIT_PARMS) */
    EC_T_LOG_PARMS           LogParms;

    EC_T_DWORD               dwSimulatorAddress;               /**< [in] Reserved */

    struct _EC_T_OS_PARMS*   pOsParms;                         /**< [in] OS layer parameters */
    EC_T_LINK_PARMS* apLinkParms[EC_SIMULATOR_MAX_LINK_PARMS]; /**< [in] Link layer parameters */

    EC_T_DWORD               dwBusCycleTimeNsec;               /**< [in] Bus cycle time in nanoseconds [ns] */
    EC_T_BOOL                bDisableProcessDataImage;         /**< [in] Disable Process Data Image (Process Data Variables not supported) */

    EC_T_SIMULATOR_DEVICE_CONNECTION_DESC aoDeviceConnection[EC_SIMULATOR_MAX_LINK_PARMS]; /**< [in] see EC_SIMULATOR_DEVICE_CONNECTION_TYPE... */
    EC_T_BOOL                bConnectHcGroups;                 /**< [in] Connect hot connect groups in topology (floating group heads to free ports) */

    /* Performance Measurements */
    EC_PACKED_API_MEMBER \
        EC_T_PERF_MEAS_INTERNAL_PARMS PerfMeasInternalParms;   /**< [in] Internal performance measurement parameters */

    EC_T_BOOL                bApiLockByApp;                    /**< [in] Lock pending API against esDeinitSimulator(). EC_FALSE (default): locked internally. EC_TRUE: application is responsible for locking. */
} EC_PACKED_API EC_T_SIMULATOR_INIT_PARMS;
#include EC_PACKED_INCLUDESTOP
#define EC_T_SIMULATOR_INIT_PARMS_SIZE    sizeof(EC_T_SIMULATOR_INIT_PARMS)

/* Slave SSC Application */
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_MAIN_INIT)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_ACK_ERROR_IND)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_APPLICATION)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_GET_DEVICE_ID)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_START_MAILBOX_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_STOP_MAILBOX_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_START_INPUT_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_STOP_INPUT_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_START_OUTPUT_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_STOP_OUTPUT_HANDLER)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_GENERATE_MAPPING)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*, EC_T_WORD*);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_INPUT_MAPPING)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_OUTPUT_MAPPING)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_COE_REMOVE_DIC_ENTRY)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_FOE_WRITE)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*, EC_T_WORD, EC_T_DWORD);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_FOE_READ_DATA)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_DWORD, EC_T_WORD, EC_T_WORD*);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_FOE_READ)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*, EC_T_WORD, EC_T_DWORD, EC_T_WORD, EC_T_WORD*);
typedef EC_T_WORD (EC_FNCALL *EC_PF_SSC_APPL_FOE_WRITE_DATA)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD*, EC_T_WORD, EC_T_BYTE);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_FOE_ERROR)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_DWORD);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_EOE_RECEIVE)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD* pwFrame, EC_T_WORD wFrameSize);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_EOE_SETTING_IND)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD* pwMacAddress, EC_T_WORD* pwIpV4Address, EC_T_WORD* pwIpV4SubNetMask, EC_T_WORD* pwIpV4DefaultGateway, EC_T_WORD* pwDnsIpV4Address);
typedef EC_T_VOID (EC_FNCALL *EC_PF_SSC_APPL_SET_PROC_VAR_PTR)(EC_T_VOID* pvContext, EC_T_DWORD dwSimulatorId, EC_T_WORD wCfgFixedAddress, EC_T_WORD, EC_T_BYTE, EC_T_BYTE*);

#include EC_PACKED_API_INCLUDESTART
typedef struct _EC_T_SLAVE_SSC_APPL_DESC
{
    EC_T_DWORD                           dwSignature;            /**< [in]   Set to SIMULATOR_SIGNATURE */
    EC_T_DWORD                           dwSize;                 /**< [in]   Set to sizeof(EC_T_SLAVE_SSC_APPL_DESC) */
    EC_T_CHAR*                           szName;
    EC_T_CHAR*                           szParameter;
    EC_T_VOID*                           pvContext;              /**< [in]   First parameter of SSC_APPL-callbacks */
    EC_PF_SSC_APPL_MAIN_INIT             pfnMainInit;            /**< [in]   SSC_APPL-callback for APPL_MainInit, called by SSC when slave initialization finished */
    EC_PF_SSC_APPL_ACK_ERROR_IND         pfnAckErrorInd;         /**< [in]   SSC_APPL-callback for APPL_AckErrorInd, called by SSC on error acknowledge by master */
    EC_PF_SSC_APPL_APPLICATION           pfnApplication;         /**< [in]   SSC_APPL-callback for APPL_Application, called after frame processing */   
    EC_PF_SSC_APPL_GET_DEVICE_ID         pfnGetDeviceID;         /**< [in]   SSC_APPL-callback for APPL_GetDeviceID, called by SSC on Explicit Device ID request by master */
    EC_PF_SSC_APPL_START_MAILBOX_HANDLER pfnStartMailboxHandler; /**< [in]   SSC_APPL-callback for APPL_StartMailboxHandler, called by SSC on INIT to PREOP and INIT to BOOT transition */
    EC_PF_SSC_APPL_STOP_MAILBOX_HANDLER  pfnStopMailboxHandler;  /**< [in]   SSC_APPL-callback for APPL_StopMailboxHandler, called by SSC on PREOP to INIT and BOOT to INIT transition */
    EC_PF_SSC_APPL_START_INPUT_HANDLER   pfnStartInputHandler;   /**< [in]   SSC_APPL-callback for APPL_StartInputHandler, called by SSC on PREOP to SAFEOP transition (even if no INPUTs configured) */
    EC_PF_SSC_APPL_STOP_INPUT_HANDLER    pfnStopInputHandler;    /**< [in]   SSC_APPL-callback for APPL_StopInputHandler, called by SSC on SAFEOP to PREOP transition (even if no INPUTs configured) */
    EC_PF_SSC_APPL_START_OUTPUT_HANDLER  pfnStartOutputHandler;  /**< [in]   SSC_APPL-callback for APPL_StartOutputHandler, called by SSC on SAFEOP to OP transition (even if no OUTPUTs configured) */
    EC_PF_SSC_APPL_STOP_OUTPUT_HANDLER   pfnStopOutputHandler;   /**< [in]   SSC_APPL-callback for APPL_StopOutputHandler, called by SSC on OP to SAFEOP transition (even if no OUTPUTs configured) */
    EC_PF_SSC_APPL_GENERATE_MAPPING      pfnGenerateMapping;     /**< [in]   SSC_APPL-callback for APPL_GenerateMapping, called by SSC on PREOP to SAFEOP transition */
    EC_PF_SSC_APPL_INPUT_MAPPING         pfnInputMapping;        /**< [in]   SSC_APPL-callback for APPL_InputMapping, called by SSC to map (copy) INPUTs */
    EC_PF_SSC_APPL_OUTPUT_MAPPING        pfnOutputMapping;       /**< [in]   SSC_APPL-callback for APPL_OutputMapping, called by SSC to map (copy) OUTPUTs */
    EC_T_PF_AOE_READ_CB                  pfnAoeRead;             /**< [in]   SSC_APPL-callback for APPL_AoeRead, called by SSC on AoE read request */
    EC_T_PF_AOE_WRITE_CB                 pfnAoeWrite;            /**< [in]   SSC_APPL-callback for APPL_AoeWrite, called by SSC on AoE write request */
    EC_T_PF_AOE_READWRITE_CB             pfnAoeReadWrite;        /**< [in]   SSC_APPL-callback for APPL_AoeReadWrite, called by SSC on AoE read/write request */
    EC_PF_SSC_APPL_EOE_RECEIVE           pfnEoeReceive;          /**< [in]   SSC_APPL-callback for APPL_EoeReceive, called by SSC on received EoE Ethernet frame completion */
    EC_PF_SSC_APPL_EOE_SETTING_IND       pfnEoeSettingInd;       /**< [in]   SSC_APPL-callback for APPL_EoeSettingInd, called by SSC on EoE settings received */
    EC_PF_SSC_APPL_FOE_WRITE             pfnFoeWrite;            /**< [in]   SSC_APPL-callback for APPL_FoeWrite, called by SSC on FoE write request */
    EC_PF_SSC_APPL_FOE_WRITE_DATA        pfnFoeWriteData;        /**< [in]   SSC_APPL-callback for APPL_FoeWriteData, called by SSC when FoE data received */   
    EC_PF_SSC_APPL_FOE_READ              pfnFoeRead;             /**< [in]   SSC_APPL-callback for APPL_FoeRead, called by SSC on FoE read request to transmit first FoE data */
    EC_PF_SSC_APPL_FOE_READ_DATA         pfnFoeReadData;         /**< [in]   SSC_APPL-callback for APPL_FoeReadData, called by SSC to transmit next FoE read data, 2..n */
    EC_PF_SSC_APPL_FOE_ERROR             pfnFoeError;            /**< [in]   SSC_APPL-callback for APPL_FoeError, called by SSC on FoE abort by master */
    EC_PF_SSC_APPL_SET_PROC_VAR_PTR      pfnSetProcVarPtr;       /**< [in]   SSC_APPL-callback for APPL_SetProcVarPtr, called on esConfigureNetwork() for each process data variable */
} EC_PACKED_API EC_T_SLAVE_SSC_APPL_DESC;
#include EC_PACKED_INCLUDESTOP

#define EC_SIM_SLAVE_CFG_APP_NAME_MAX_LEN ((EC_T_DWORD)127)
#define EC_SIM_SLAVE_CFG_APP_PARMS_MAX_LEN ((EC_T_DWORD)127)
#define EC_SIM_SLAVE_CFG_APP_NAME_SIZE (EC_SIM_SLAVE_CFG_APP_NAME_MAX_LEN+1)
#define EC_SIM_SLAVE_CFG_APP_PARMS_SIZE (EC_SIM_SLAVE_CFG_APP_PARMS_MAX_LEN+1)

#include EC_PACKED_API_INCLUDESTART
/**
 * \typedef EC_T_SIM_SLAVE_CFG_INFO
 * \brief See EC_T_SIM_SLAVE_INFO, esGetSimSlaveInfo()
 */
typedef struct _EC_T_SIM_SLAVE_CFG_INFO
{
    EC_T_WORD   wFixedAddress;              /**< [out] Slave's station address (ENI/EXI: /EtherCATConfig/Config/Slave/Info/PhysAddr) */
    EC_T_BOOL   bPowerOff;                  /**< [out] Slave powered off on startup (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave@PowerOff) */
    EC_T_BOOL   bSimulated;                 /**< [out] Slave is simulated (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave/Simulated) */
    EC_T_BOOL   bIgnoreCoeDownloadError;    /**< [out] Slave ignores CoE download errors (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave/Mailbox/CoE@IgnoreDownloadError) */

    EC_PACKED_API_MEMBER \
        EC_T_SIMULATOR_DEVICE_CONNECTION_DESC aPortConnection[4]; /**< [out] Explicit port connection (optional) (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave/PortConnection) */

    EC_T_CHAR   szApplicationName[EC_SIM_SLAVE_CFG_APP_NAME_SIZE];    /**< [out] Configured slave application name (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave/Application/Name) */
    EC_T_CHAR   szApplicationParms[EC_SIM_SLAVE_CFG_APP_PARMS_SIZE];  /**< [out] Configured slave application parameters (EXI: /EtherCATConfig/ExtendedConfig/Slaves/Slave/Application/Parameter) */

    EC_T_DWORD adwReserved[16];             /**< [out] Reserved */
} EC_PACKED_API EC_T_SIM_SLAVE_CFG_INFO;
#include EC_PACKED_INCLUDESTOP

#include EC_PACKED_API_INCLUDESTART
/**
* \typedef EC_T_SIM_SLAVE_STATUS_INFO
* \brief See EC_T_SIM_SLAVE_INFO, esGetSimSlaveInfo()
*/
typedef struct _EC_T_SIM_SLAVE_STATUS_INFO
{
    EC_T_BOOL   bIsPowerOn;                 /**< [out] Slave is powered on. See esPowerSlave(). */
    EC_T_BOOL   bIsPresent;                 /**< [out] Slave is present in topology segment and connected to the network. See esConnectPorts(), Hot Connect. */
    EC_T_WORD   wAlStatusReq;               /**< [out] AL Status (0x0130) requested from Simulator application. See esSetSimSlaveState(). */
    EC_T_WORD   wAlStatusCodeReq;           /**< [out] AL Status (0x0134) requested from Simulator application. See esSetSimSlaveState(). */
    EC_T_DWORD  adwRes1[4];                 /**< [out] Reserved */

    EC_PACKED_API_MEMBER \
        EC_T_SIMULATOR_DEVICE_CONNECTION_DESC aPortConnection[4]; /**< [out] See esConnectPorts() */

    EC_T_DWORD adwRes2[16];                 /**< [out] Reserved */
} EC_PACKED_API EC_T_SIM_SLAVE_STATUS_INFO;
#include EC_PACKED_INCLUDESTOP

#include EC_PACKED_API_INCLUDESTART
typedef struct _EC_T_SIM_SLAVE_INFO
{
    EC_PACKED_API_MEMBER \
        EC_T_SIM_SLAVE_CFG_INFO oCfg;       /**< [out] Config Info (ENI/EXI) */

    EC_PACKED_API_MEMBER \
        EC_T_SIM_SLAVE_STATUS_INFO oStatus; /**< [out] Status Info */

    EC_T_DWORD adwReserved[32];             /**< [out] Reserved */
} EC_PACKED_API EC_T_SIM_SLAVE_INFO;
#include EC_PACKED_INCLUDESTOP

/*-FUNCTION DECLARATION------------------------------------------------------*/
#ifdef __cplusplus
extern "C"
{
#endif

/* Perf measurement API functions */

EC_API const EC_T_CHAR* EC_API_FNCALL esGetText(EC_T_DWORD dwInstanceID, EC_T_DWORD dwTextId);
EC_API const EC_T_CHAR* EC_API_FNCALL esGetNotifyText(EC_T_DWORD dwInstanceID, EC_T_DWORD dwNotifyCode);
EC_API EC_T_DWORD EC_API_FNCALL esConvertEcErrorToAdsError(EC_T_DWORD dwInstanceID, EC_T_DWORD dwErrorCode);
EC_API EC_T_DWORD EC_API_FNCALL esConvertEcErrorToFoeError(EC_T_DWORD dwInstanceID, EC_T_DWORD dwErrorCode);
EC_API EC_T_DWORD EC_API_FNCALL esConvertEcErrorToSoeError(EC_T_DWORD dwInstanceID, EC_T_DWORD dwErrorCode);
EC_API EC_T_DWORD EC_API_FNCALL esConvertEcErrorToCoeError(EC_T_DWORD dwInstanceID, EC_T_DWORD dwErrorCode);

/* New Perf measurement API functions */

EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppCreate(EC_T_DWORD dwInstanceID, EC_T_PERF_MEAS_APP_PARMS* pPerfMeasAppParms, EC_T_VOID** ppvPerfMeas);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppDelete(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppStart(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD dwIndex);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppEnd(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD dwIndex);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppReset(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD dwIndex);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppGetRaw(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_VAL* pPerfMeasVal, EC_T_PERF_MEAS_HISTOGRAM* pPerfMeasHistogram, EC_T_DWORD dwPerfMeasNumOf);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppGetInfo(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_INFO* pPerfMeasInfo, EC_T_DWORD dwPerfMeasNumOf);
EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasAppGetNumOf(EC_T_DWORD dwInstanceID, EC_T_VOID* pvPerfMeas, EC_T_DWORD* pdwNumOf);

EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasResetByTaskId(EC_T_DWORD dwInstanceID, EC_T_DWORD dwTaskId, EC_T_DWORD dwIndex);
static EC_INLINESTART EC_T_DWORD esPerfMeasReset(EC_T_DWORD dwInstanceID, EC_T_DWORD dwIndex)
{
    return esPerfMeasResetByTaskId(dwInstanceID, 0, dwIndex);
} EC_INLINESTOP

EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasGetRawByTaskId(EC_T_DWORD dwInstanceID, EC_T_DWORD dwTaskId, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_VAL* pPerfMeasVal, EC_T_PERF_MEAS_HISTOGRAM* pPerfMeasHistogram, EC_T_DWORD dwPerfMeasNumOf);
static EC_INLINESTART EC_T_DWORD esPerfMeasGetRaw(EC_T_DWORD dwInstanceID, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_VAL* pPerfMeasVal, EC_T_PERF_MEAS_HISTOGRAM* pPerfMeasHistogram, EC_T_DWORD dwPerfMeasNumOf)
{
    return esPerfMeasGetRawByTaskId(dwInstanceID, 0, dwIndex, pPerfMeasVal, pPerfMeasHistogram, dwPerfMeasNumOf);
} EC_INLINESTOP


EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasGetInfoByTaskId(EC_T_DWORD dwInstanceID, EC_T_DWORD dwTaskId, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_INFO* pPerfMeasInfo, EC_T_DWORD dwPerfMeasNumOf);
static EC_INLINESTART EC_T_DWORD esPerfMeasGetInfo(EC_T_DWORD dwInstanceID, EC_T_DWORD dwIndex, EC_T_PERF_MEAS_INFO* pPerfMeasInfo, EC_T_DWORD dwPerfMeasNumOf)
{
    return esPerfMeasGetInfoByTaskId(dwInstanceID, 0, dwIndex, pPerfMeasInfo, dwPerfMeasNumOf);
} EC_INLINESTOP

EC_API EC_T_DWORD EC_API_FNCALL esPerfMeasGetNumOfByTaskId(EC_T_DWORD dwInstanceID, EC_T_DWORD dwTaskId, EC_T_DWORD* pdwNumOf);
static EC_INLINESTART EC_T_DWORD esPerfMeasGetNumOf(EC_T_DWORD dwInstanceID, EC_T_DWORD* pdwNumOf)
{
    return esPerfMeasGetNumOfByTaskId(dwInstanceID, 0, pdwNumOf);
} EC_INLINESTOP


/* Multi instance API functions */

EC_API EC_T_DWORD EC_API_FNCALL esInitSimulator(    EC_T_DWORD                       dwInstanceID,
                                                    const EC_T_SIMULATOR_INIT_PARMS* pParms );

EC_API EC_T_DWORD EC_API_FNCALL esDeinitSimulator(  EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esGetSimulatorParms(EC_T_DWORD                 dwInstanceID,
                                                    EC_T_SIMULATOR_INIT_PARMS* pParms,
                                                    EC_T_DWORD                 dwParmsBufSize  );

EC_API EC_T_DWORD EC_API_FNCALL esSetSimulatorParms(EC_T_DWORD                       dwInstanceID,
                                                    const EC_T_SIMULATOR_INIT_PARMS* pParms );

EC_API EC_T_DWORD EC_API_FNCALL esSetLogParms(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_LOG_PARMS* pLogParms               );

EC_API EC_T_DWORD EC_API_FNCALL esConnectPorts(     EC_T_DWORD              dwInstanceID1,
                                                    EC_T_WORD               wCfgFixedAddress1,
                                                    EC_T_BYTE               byPort1,

                                                    EC_T_DWORD              dwInstanceID2,
                                                    EC_T_WORD               wCfgFixedAddress2,
                                                    EC_T_BYTE               byPort2         );

EC_API EC_T_DWORD EC_API_FNCALL esDisconnectPort(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort          );

EC_API EC_T_DWORD EC_API_FNCALL esPowerSlave(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BOOL               bOn             );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveSscApplication(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_SLAVE_SSC_APPL_DESC* pSscApplDesc  );

EC_API EC_T_DWORD EC_API_FNCALL esExtendSlaveCoeObjectDictionary(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    struct _EC_T_COE_DICTIONARY_DESC* pDict );

EC_API EC_T_DWORD EC_API_FNCALL esDeleteSlaveCoeObject(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_WORD               wIndex          );

EC_API EC_T_DWORD EC_API_FNCALL esClearSlaveCoeObjectDictionary(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress);

EC_API EC_T_DWORD EC_API_FNCALL esResetSlaveCoeObjectDictionary(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress);

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveAoeObjectTransferCallbacks(
                                                    EC_T_DWORD                  dwInstanceID,
                                                    EC_T_WORD                   wCfgFixedAddress,
                                                    EC_T_PF_AOE_READ_CB         pfRead,
                                                    EC_T_PF_AOE_WRITE_CB        pfWrite,
                                                    EC_T_PF_AOE_READWRITE_CB    pfReadWrite,
                                                    EC_T_VOID*                  pvContext);

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveCoeObjectTransferCallbacks(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_WORD               wObjectIndex,
                                                    EC_T_PF_COE_READ_CB     pfRead,
                                                    EC_T_PF_COE_WRITE_CB    pfWrite,
                                                    EC_T_VOID*              pvContext);

EC_API EC_T_DWORD EC_API_FNCALL esLinkSendFrame(    EC_T_DWORD              dwInstanceID,
                                                    EC_T_LINK_FRAMEDESC*    pLinkFrameDesc);

EC_API EC_T_DWORD EC_API_FNCALL esLinkRegister(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_LINK_DRV_DESC*     pLinkDrvDesc,
                                                    EC_T_DWORD              dwLinkDrvDescSize );

EC_API EC_T_DWORD EC_API_FNCALL esSetMasterRedStateReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bActive         );

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterRedState(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbActive        );

EC_API EC_T_BYTE* EC_API_FNCALL esGetMasterRedProcessImageInputPtr(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_BYTE* EC_API_FNCALL esGetMasterRedProcessImageOutputPtr(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esIoCtl(            EC_T_DWORD             dwInstanceID,
                                                    EC_T_DWORD             dwCode,
                                                    const EC_T_VOID* const pbyInBuf,
                                                    EC_T_DWORD             dwInBufSize,
                                                    EC_T_VOID* const       pbyOutBuf,
                                                    EC_T_DWORD             dwOutBufSize,
                                                    EC_T_DWORD* const      pdwNumOutData    );

EC_API EC_T_DWORD EC_API_FNCALL esScanBus(          EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esRescueScan(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esConfigureNetwork( EC_T_DWORD              dwInstanceID,
                                                    EC_T_CNF_TYPE           eCnfType,
                                                    EC_T_PBYTE              pbyCnfData,
                                                    EC_T_DWORD              dwCnfDataLen    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigLoad(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_CNF_TYPE           eCnfType,
                                                    EC_T_PBYTE              pbyCnfData,
                                                    EC_T_DWORD              dwCnfDataLen    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigExcludeSlave(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wPhysAddress    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigIncludeSlave(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wPhysAddress    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigSetPreviousPort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wPhysAddress,
                                                    EC_T_WORD               wPhysAddressPrev,
                                                    EC_T_WORD               wPortPrev       );

EC_API EC_T_DWORD EC_API_FNCALL esConfigAddJunctionRedundancyConnection(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wHeadPhysAddress,
                                                    EC_T_WORD               wHeadRedPort,
                                                    EC_T_WORD               wTailPhysAddress,
                                                    EC_T_WORD               wTailRedPort    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigApply(      EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esConfigExtend(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bResetConfig,
                                                    EC_T_DWORD              dwTimeout       );
EC_API EC_T_DWORD EC_API_FNCALL esIsConfigured(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbIsConfigured  );

EC_API EC_T_DWORD EC_API_FNCALL esSetMasterState(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout,
                                                    EC_T_STATE              eReqState       );

EC_API EC_T_STATE EC_API_FNCALL esGetMasterState(   EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterStateEx( EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD*              pwCurrState,
                                                    EC_T_WORD*              pwReqState      );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveId(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wStationAddress );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveFixedAddr(EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD*              pwFixedAddr     );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveIdAtPosition(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wAutoIncAddress );

EC_API EC_T_BOOL EC_API_FNCALL  esGetSlaveProp(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_SLAVE_PROP*        pSlaveProp      );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlavePortState(EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD*              pwPortState     );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveState(    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD*              pwCurrDevState,
                                                    EC_T_WORD*              pwReqDevState   );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveState(    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wDeviceState,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esTferSingleRawCmd( EC_T_DWORD              dwInstanceID,
                                                    EC_T_CMD                eCmd,
                                                    EC_T_DWORD              dwMemoryAddress,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveRegister(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wRegisterOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveRegisterReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wRegisterOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen            );

EC_API EC_T_DWORD EC_API_FNCALL esWriteSlaveRegister(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wRegisterOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esWriteSlaveRegisterReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wRegisterOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen            );

EC_API EC_T_DWORD EC_API_FNCALL esQueueRawCmd(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wInvokeId,
                                                    EC_T_CMD                eCmd,
                                                    EC_T_DWORD              dwMemoryAddress,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen            );

EC_API EC_T_DWORD EC_API_FNCALL esClntQueueRawCmd(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClntId,
                                                    EC_T_WORD               wInvokeId,
                                                    EC_T_CMD                eCmd,
                                                    EC_T_DWORD              dwMemoryAddress,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wLen            );

EC_API EC_T_DWORD EC_API_FNCALL esGetNumConfiguredSlaves(EC_T_DWORD         dwInstanceID    );

EC_API EC_T_MBXTFER* EC_API_FNCALL esMbxTferCreate( EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER_DESC*      pMbxTferDesc    );

EC_API EC_T_DWORD EC_API_FNCALL esMbxTferAbort(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer        );

EC_API EC_T_VOID EC_API_FNCALL esMbxTferDelete(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer        );

EC_API EC_T_DWORD EC_API_FNCALL esClntSendRawMbx(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClntId,
                                                    EC_T_BYTE*              pbyMbxCmd,
                                                    EC_T_DWORD              dwMbxCmdLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeSdoDownloadReq(EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_BYTE               byObSubIndex,
                                                    EC_T_DWORD              dwTimeout,
                                                    EC_T_DWORD              dwFlags         );

EC_API EC_T_DWORD EC_API_FNCALL esCoeSdoDownload(   EC_T_DWORD              dwInstanceID
                                                   ,EC_T_DWORD              dwSlaveId
                                                   ,EC_T_WORD               wObIndex
                                                   ,EC_T_BYTE               byObSubIndex
                                                   ,const EC_T_BYTE*        pbyData
                                                   ,EC_T_DWORD              dwDataLen
                                                   ,EC_T_DWORD              dwTimeout
                                                   ,EC_T_DWORD              dwFlags         );

EC_API EC_T_DWORD EC_API_FNCALL esCoeSdoUploadReq(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_BYTE               byObSubIndex,
                                                    EC_T_DWORD              dwTimeout,
                                                    EC_T_DWORD              dwFlags         );

EC_API EC_T_DWORD EC_API_FNCALL esCoeSdoUpload(     EC_T_DWORD              dwInstanceID
                                                   ,EC_T_DWORD              dwSlaveId
                                                   ,EC_T_WORD               wObIndex
                                                   ,EC_T_BYTE               byObSubIndex
                                                   ,EC_T_BYTE*              pbyData
                                                   ,EC_T_DWORD              dwDataLen
                                                   ,EC_T_DWORD*             pdwOutDataLen
                                                   ,EC_T_DWORD              dwTimeout
                                                   ,EC_T_DWORD              dwFlags         );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetODListReq(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_COE_ODLIST_TYPE    eListType,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetODList(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_COE_ODLIST_TYPE    eListType,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_COE_ODLIST*        poOdList,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetObjectDescReq(EC_T_DWORD          dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetObjectDesc( EC_T_DWORD             dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_CHAR*              pchObName,
                                                    EC_T_WORD               wObNameLen,
                                                    EC_T_COE_OBDESC*        poObDesc,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetEntryDescReq(EC_T_DWORD           dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_BYTE               byObSubIndex,
                                                    EC_T_BYTE               byValueInfo,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeGetEntryDesc(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wObIndex,
                                                    EC_T_BYTE               byObSubIndex,
                                                    EC_T_BYTE               byValueInfo,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_WORD               wDataLen,
                                                    EC_T_COE_ENTRYDESC*     poEntryDesc,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esCoeRxPdoTfer(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_DWORD              dwNumber,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSendSlaveCoeEmergency(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_WORD               wCode,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen       );

EC_API EC_T_DWORD EC_API_FNCALL esEoeSendFrame(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE*              pbyFrame,
                                                    EC_T_DWORD              dwFrameLen);

EC_API EC_T_DWORD EC_API_FNCALL esFoeFileUpload(    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        achFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD*             pdwOutDataLen,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esFoeFileDownload(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        achFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esFoeUploadReq(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        achFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esFoeSegmentedUploadReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        szFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_DWORD              dwFileSize,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esFoeDownloadReq(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        achFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esFoeSegmentedDownloadReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    const EC_T_CHAR*        szFileName,
                                                    EC_T_DWORD              dwFileNameLen,
                                                    EC_T_DWORD              dwFileSize,
                                                    EC_T_DWORD              dwPassword,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esEoeRegisterEndpoint(
                                                    EC_T_DWORD              dwInstanceID,
                                                    const EC_T_CHAR*        szEoEDrvIdent,
                                                    EC_T_LINK_DRV_DESC*     pLinkDrvDesc    );

EC_API EC_T_DWORD EC_API_FNCALL esEoeUnregisterEndpoint(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_LINK_DRV_DESC*     pLinkDrvDesc    );

EC_API EC_T_DWORD EC_API_FNCALL esSoeWrite(         EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE               byDriveNo,
                                                    EC_T_BYTE*              pbyElementFlags,
                                                    EC_T_WORD               wIDN,
                                                    const EC_T_BYTE*        pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esSoeRead(          EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE               byDriveNo,
                                                    EC_T_BYTE*              pbyElementFlags,
                                                    EC_T_WORD               wIDN,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD*             pdwOutDataLen,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esSoeAbortProcCmd(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE               byDriveNo,
                                                    EC_T_BYTE*              pbyElementFlags,
                                                    EC_T_WORD               wIDN,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esSoeWriteReq(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE               byDriveNo,
                                                    EC_T_BYTE*              pbyElementFlags,
                                                    EC_T_WORD               wIDN,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esSoeReadReq(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE               byDriveNo,
                                                    EC_T_BYTE*              pbyElementFlags,
                                                    EC_T_WORD               wIDN,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esAoeGetSlaveNetId( EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poAoeNetId       );

EC_API EC_T_DWORD EC_API_FNCALL esAoeRead(          EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_DWORD              dwIndexGroup,
                                                    EC_T_DWORD              dwIndexOffset,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD*             pdwDataOutLen,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_DWORD*             pdwCmdResult,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esAoeReadReq(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_DWORD              dwIndexGroup,
                                                    EC_T_DWORD              dwIndexOffset,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAoeWrite(         EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_DWORD              dwIndexGroup,
                                                    EC_T_DWORD              dwIndexOffset,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_DWORD*             pdwCmdResult,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAoeWriteReq(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_DWORD              dwIndexGroup,
                                                    EC_T_DWORD              dwIndexOffset,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAoeReadWrite(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_DWORD              dwIndexGroup,
                                                    EC_T_DWORD              dwIndexOffset,
                                                    EC_T_DWORD              dwReadDataLen,
                                                    EC_T_DWORD              dwWriteDataLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD*             pdwDataOutLen,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_DWORD*             pdwCmdResult,
                                                    EC_T_DWORD              dwTimeout        );

EC_API EC_T_DWORD EC_API_FNCALL esAoeWriteControl(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_AOE_NETID*         poTargetNetId,
                                                    EC_T_WORD               wTargetPort,
                                                    EC_T_WORD               wAoEState,
                                                    EC_T_WORD               wDeviceState,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_DWORD*             pdwCmdResult,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esVoeRead(          EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD*             pdwOutDataLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esVoeWrite(         EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwDataLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esVoeWriteReq(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_MBXTFER*           pMbxTfer,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esExecJob(          EC_T_DWORD              dwInstanceID,
                                                    EC_T_USER_JOB           eUserJob,
                                                    EC_T_USER_JOB_PARMS*    pUserJobParms   );

EC_API EC_T_DWORD EC_API_FNCALL esGetProcessData(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwLength,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSetProcessData(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwOffset,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwLength,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSetProcessDataBits(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwBitOffsetPd,
                                                    EC_T_BYTE*              pbyDataSrc,
                                                    EC_T_DWORD              dwBitLength,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esGetProcessDataBits(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwBitOffsetPd,
                                                    EC_T_BYTE*              pbyDataDst,
                                                    EC_T_DWORD              dwBitLength,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esForceProcessDataBits(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwBitOffsetPd,
                                                    EC_T_WORD               wBitLength,
                                                    EC_T_BYTE*              pbyData,
                                                    EC_T_DWORD              dwTimeout);

EC_API EC_T_DWORD EC_API_FNCALL esReleaseProcessDataBits(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_BOOL               bOutputData,
                                                    EC_T_DWORD              dwBitOffsetPd,
                                                    EC_T_WORD               wBitLength,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReleaseAllProcessDataBits(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esGetNumConnectedSlaves(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esGetNumConnectedSlavesMain(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esGetNumConnectedSlavesRed(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveEEPRom(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wEEPRomStartOffset,
                                                    EC_T_WORD*              pwReadData,
                                                    EC_T_DWORD              dwReadLen,
                                                    EC_T_DWORD*             pdwNumOutData,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveEEPRomReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wEEPRomStartOffset,
                                                    EC_T_WORD*              pwReadData,
                                                    EC_T_DWORD              dwReadLen,
                                                    EC_T_DWORD*             pdwNumOutData,
                                                    EC_T_DWORD              dwTimeout      );

EC_API EC_T_DWORD EC_API_FNCALL esWriteSlaveEEPRom( EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wEEPRomStartOffset,
                                                    const EC_T_WORD*        pwWriteData,
                                                    EC_T_DWORD              dwWriteLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esWriteSlaveEEPRomReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wEEPRomStartOffset,
                                                    const EC_T_WORD*        pwWriteData,
                                                    EC_T_DWORD              dwWriteLen,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReloadSlaveEEPRom(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReloadSlaveEEPRomReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esResetSlaveController(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAssignSlaveEEPRom(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL               bSlavePDIAccessEnable,
                                                    EC_T_BOOL               bForceAssign,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAssignSlaveEEPRomReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL               bSlavePDIAccessEnable,
                                                    EC_T_BOOL               bForceAssign,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esActiveSlaveEEPRom(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL*              pbSlavePDIAccessActive,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esActiveSlaveEEPRomReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL*              pbSlavePDIAccessActive,
                                                    EC_T_DWORD              dwTimeout      );

EC_API EC_T_DWORD EC_API_FNCALL esHCAcceptTopoChange(
                                                    EC_T_DWORD              dwInstanceID   );

EC_API EC_T_DWORD EC_API_FNCALL esHCGetNumGroupMembers(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwGroupIndex    );

EC_API EC_T_DWORD EC_API_FNCALL esHCGetSlaveIdsOfGroup(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwGroupIndex,
                                                    EC_T_DWORD*             adwSlaveId,
                                                    EC_T_DWORD              dwMaxNumSlaveIds );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlavePortState(EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wPort,
                                                    EC_T_BOOL               bClose,
                                                    EC_T_BOOL               bForce,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlavePortStateReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_WORD               wPort,
                                                    EC_T_BOOL               bClose,
                                                    EC_T_BOOL               bForce,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSlaveSerializeMbxTfers(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId       );

EC_API EC_T_DWORD EC_API_FNCALL esSlaveParallelMbxTfers(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId       );

EC_API EC_T_DWORD EC_API_FNCALL esRegisterClient(   EC_T_DWORD              dwInstanceID,
                                                    EC_PF_NOTIFY            pfnNotify,
                                                    EC_T_VOID*              pCallerData,
                                                    EC_T_REGISTERRESULTS*   pRegResults     );

EC_API EC_T_DWORD EC_API_FNCALL esUnregisterClient( EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClntId        );

EC_API EC_T_DWORD EC_API_FNCALL esDcEnable(         EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcDisable(        EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcIsEnabled(      EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbDcIsEnabled);

EC_API EC_T_DWORD EC_API_FNCALL esDcConfigure(      EC_T_DWORD                dwInstanceID,
                                                    const EC_T_DC_CONFIGURE*  pDcConfigure );

EC_API EC_T_DWORD EC_API_FNCALL esDcContDelayCompEnable(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcContDelayCompDisable(EC_T_DWORD       dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcmConfigure(
                                                    EC_T_DWORD              dwInstanceID,
                                                    const EC_T_DCM_CONFIG*  pDcmConfig,
                                                    EC_T_DWORD              dwInSyncTimeout );

EC_API EC_T_DWORD EC_API_FNCALL esDcmGetStatus(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_INT*               pnDiffCur,
                                                    EC_T_INT*               pnDiffAvg,
                                                    EC_T_INT*               pnDiffMax       );

EC_API EC_T_DWORD EC_API_FNCALL esDcxGetStatus(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD*             pdwErrorCode,
                                                    EC_T_INT*               pnDiffCur,
                                                    EC_T_INT*               pnDiffAvg,
                                                    EC_T_INT*               pnDiffMax,
                                                    EC_T_INT64*             pnTimeStampDiff);

EC_API EC_T_DWORD EC_API_FNCALL esDcmResetStatus(   EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcmGetBusShiftConfigured(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbBusShiftConfigured);

EC_API EC_T_DWORD EC_API_FNCALL esDcmGetLog(        EC_T_DWORD              dwInstanceID,
                                                    EC_T_CHAR**             pszLog          );

EC_API EC_T_DWORD EC_API_FNCALL esDcmShowStatus(    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esDcmGetAdjust(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_INT*               pnAdjustPermil  );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveInfo(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_GET_SLAVE_INFO*    pGetSlaveInfo   );

EC_API EC_T_DWORD EC_API_FNCALL esGetCfgSlaveInfo(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bStationAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_CFG_SLAVE_INFO*    pSlaveInfo      );

EC_API EC_T_DWORD EC_API_FNCALL esGetCfgSlaveEoeInfo(EC_T_DWORD             dwInstanceID,
                                                    EC_T_BOOL               bStationAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_CFG_SLAVE_EOE_INFO* pSlaveEoeInfo  );

EC_API EC_T_DWORD EC_API_FNCALL esGetCfgSlaveSmInfo(EC_T_DWORD             dwInstanceID,
                                                    EC_T_BOOL               bStationAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_CFG_SLAVE_SM_INFO* pSlaveSmInfo);

EC_API EC_T_DWORD EC_API_FNCALL esGetBusSlaveInfo(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bStationAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BUS_SLAVE_INFO*    pSlaveInfo      );

EC_API EC_T_DWORD EC_API_FNCALL esGetProcessVarInfoNumOf(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_VAR_DIRECTION      eVarDirection,
                                                    EC_T_VAR_SOURCE         eVarSource,
                                                    EC_T_BOOL               bFixedAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_DWORD*             pdwProcessVarInfoNumOf);

EC_API EC_T_DWORD EC_API_FNCALL esGetProcessVarInfoEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_VAR_DIRECTION      eVarDirection,
                                                    EC_T_VAR_SOURCE         eVarSource,
                                                    EC_T_BOOL               bFixedAddress,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_PROCESS_VAR_INFO_EX* aoVarInfo,
                                                    EC_T_DWORD              dwMaxProcessVarInfoNumOf,
                                                    EC_T_DWORD*             pdwProcessVarInfoNumOf);

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveInpVarInfoNumOf(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD*              pwSlaveInpVarInfoNumOf);

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveOutpVarInfoNumOf(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD*              pwSlaveOutpVarInfoNumOf);

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveInpVarInfo(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wNumOfVarsToRead,
                                                    EC_T_PROCESS_VAR_INFO*  pSlaveProcVarInfoEntries,
                                                    EC_T_WORD*              pwReadEntries   );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveInpVarInfoEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wNumOfVarsToRead,
                                                    EC_T_PROCESS_VAR_INFO_EX* pSlaveProcVarInfoEntries,
                                                    EC_T_WORD*              pwReadEntries   );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveOutpVarInfo(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wNumOfVarsToRead,
                                                    EC_T_PROCESS_VAR_INFO*  pSlaveProcVarInfoEntries,
                                                    EC_T_WORD*              pwReadEntries   );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveOutpVarInfoEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wNumOfVarsToRead,
                                                    EC_T_PROCESS_VAR_INFO_EX* pSlaveProcVarInfoEntries,
                                                    EC_T_WORD*              pwReadEntries   );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveOutpVarByObjectEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wIndex,
                                                    EC_T_WORD               wSubIndex,
                                                    EC_T_PROCESS_VAR_INFO_EX* pProcessVarInfoEntry);

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveInpVarByObjectEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wIndex,
                                                    EC_T_WORD               wSubIndex,
                                                    EC_T_PROCESS_VAR_INFO_EX* pProcessVarInfoEntry);

EC_API EC_T_DWORD EC_API_FNCALL esFindOutpVarByName(EC_T_DWORD              dwInstanceID,
                                                    const EC_T_CHAR*        szVariableName,
                                                    EC_T_PROCESS_VAR_INFO*  pSlaveOutpVarInfo);

EC_API EC_T_DWORD EC_API_FNCALL esFindOutpVarByNameEx(
                                                    EC_T_DWORD              dwInstanceID,
                                                    const EC_T_CHAR*        szVariableName,
                                                    EC_T_PROCESS_VAR_INFO_EX* pProcessVarInfoEntry);

EC_API EC_T_DWORD EC_API_FNCALL esFindInpVarByName( EC_T_DWORD              dwInstanceID,
                                                    const EC_T_CHAR*        szVariableName,
                                                    EC_T_PROCESS_VAR_INFO*  pProcessVarInfoEntry);

EC_API EC_T_DWORD EC_API_FNCALL esFindInpVarByNameEx(EC_T_DWORD             dwInstanceID,
                                                    const EC_T_CHAR*        szVariableName,
                                                    EC_T_PROCESS_VAR_INFO_EX* pProcessVarInfoEntry);

EC_API EC_T_DWORD EC_API_FNCALL esEthDbgMsg(        EC_T_DWORD              dwInstanceID,
                                                    EC_T_BYTE               byEthTypeByte0,
                                                    EC_T_BYTE               byEthTypeByte1,
                                                    EC_T_CHAR*              szMsg           );

EC_API EC_T_DWORD EC_API_FNCALL esBlockNode(        EC_T_DWORD              dwInstanceID,
                                                    EC_T_SB_MISMATCH_DESC*  pMisMatch,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esOpenBlockedPorts( EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esForceTopologyChange(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esIsTopologyChangeDetected(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbTopologyChangeDetected);

EC_API EC_T_DWORD EC_API_FNCALL esIsTopologyKnown(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbTopologyKnown );

EC_API EC_T_DWORD EC_API_FNCALL esGetBusTime(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_UINT64*            pqwBusTime      );

EC_API EC_T_DWORD EC_API_FNCALL esIsSlavePresent(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_BOOL*              pbPresence      );

EC_API EC_PTS_STATE EC_API_FNCALL esPassThroughSrvGetStatus(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esPassThroughSrvStart(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_PTS_SRV_START_PARMS* poPtsStartParams,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esPassThroughSrvStop(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esPassThroughSrvEnable(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esPassThroughSrvDisable(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAdsAdapterStart(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_ADS_ADAPTER_START_PARMS* poStartParams,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esAdsAdapterStop(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_BYTE* EC_API_FNCALL esGetProcessImageInputPtr(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_BYTE* EC_API_FNCALL esGetProcessImageOutputPtr(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_BYTE* EC_API_FNCALL esGetDiagnosisImagePtr(
                                                    EC_T_DWORD              dwInstanceID    );
                                                    
EC_API EC_T_DWORD EC_API_FNCALL esGetDiagnosisImageSize(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esNotifyApp(        EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwCode,
                                                    EC_T_NOTIFYPARMS*       pParms          );

EC_API EC_T_DWORD EC_API_FNCALL esLogFrameEnable(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_PFLOGFRAME_CB      pvLogFrameCallBack,
                                                    EC_T_VOID*              pvContext       );

EC_API EC_T_DWORD EC_API_FNCALL esLogFrameDisable(  EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esGetSrcMacAddress( EC_T_DWORD              dwInstanceID,
                                                    ETHERNET_ADDRESS*       pMacSrc         );

EC_API EC_T_DWORD EC_API_FNCALL esGetLicenseFingerprint(EC_T_DWORD dwInstanceID,
                                                        EC_T_BYTE  byMethod,
                                                        EC_T_CHAR* szLicenseFingerprint);

EC_API EC_T_DWORD EC_API_FNCALL esSetLicenseKey(    EC_T_DWORD              dwInstanceID,
                                                    const EC_T_CHAR*        szLicenseKey   );

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterProperties(EC_T_DWORD            dwInstanceID,
                                                    EC_T_DWORD*             pdwMasterPropNumEntries,
                                                    EC_T_MASTER_PROP_DESC** ppaMasterPropEntries);

EC_API EC_T_DWORD EC_API_FNCALL esGetVersion(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD*             pdwVersion,
                                                    EC_T_DWORD*             pdwVersionType  );

EC_API EC_T_DWORD EC_API_FNCALL esTraceDataConfig(  EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wTraceDataSize  );

EC_API EC_T_DWORD EC_API_FNCALL esTraceDataGetInfo( EC_T_DWORD              dwInstanceID,
                                                    EC_T_TRACE_DATA_INFO*   pTraceDataInfo  );

EC_API EC_T_DWORD EC_API_FNCALL esFastModeInit(     EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esFastSendAllCycFrames(
                                                    EC_T_DWORD              dwInstanceID    );

EC_API EC_T_DWORD EC_API_FNCALL esFastProcessAllRxFrames(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL*              pbAreAllCycFramesProcessed);

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveIdentification(   EC_T_DWORD     dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wAdo,
                                                    EC_T_WORD*              pwValue,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esReadSlaveIdentificationReq(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwClientId,
                                                    EC_T_DWORD              dwTferId,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_WORD               wAdo,
                                                    EC_T_WORD*              pwValue,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveDisabled( EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL               bDisabled       );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlavesDisabled(EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_SLAVE_SELECTION    eSlaveSelection,
                                                    EC_T_BOOL               bDisabled       );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlaveDisconnected(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_BOOL               bDisconnected   );

EC_API EC_T_DWORD EC_API_FNCALL esSetSlavesDisconnected(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bFixedAddressing,
                                                    EC_T_WORD               wSlaveAddress,
                                                    EC_T_SLAVE_SELECTION    eSlaveSelection,
                                                    EC_T_BOOL               bDisconnected   );

EC_API EC_T_DWORD EC_API_FNCALL esGetMemoryUsage(   EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD*             pdwCurrentUsage,
                                                    EC_T_DWORD*             pdwMaxUsage     );

EC_API EC_T_DWORD EC_API_FNCALL esGetSlaveStatistics(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId,
                                                    EC_T_SLVSTATISTICS_DESC* pSlaveStatisticsDesc);

EC_API EC_T_DWORD EC_API_FNCALL esClearSlaveStatistics(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_DWORD              dwSlaveId       );

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterSyncUnitInfoNumOf(
                                                    EC_T_DWORD              dwInstanceID);

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterSyncUnitInfo(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wMsuId,
                                                    EC_T_MSU_INFO*          pMsuInfo        );

EC_API EC_T_DWORD EC_API_FNCALL esGetMasterDump(    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BYTE*              pbyBuffer,
                                                    EC_T_DWORD              dwBufferSize,
                                                    EC_T_DWORD*             pdwDumpSize     );

EC_API EC_T_DWORD EC_API_FNCALL esBadConnectionsDetect(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_BOOL               bRefreshSlaveStatistics,
                                                    EC_T_DWORD              dwTimeout       );

EC_API EC_T_DWORD EC_API_FNCALL esSelfTestScan(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_SELFTESTSCAN_PARMS* pParms         );

EC_API EC_T_DWORD EC_API_FNCALL esSetErrorAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort,
                                                    EC_T_BOOL               bOutgoing       );

EC_API EC_T_DWORD EC_API_FNCALL esSetErrorGenerationAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort,
                                                    EC_T_BOOL               bOutgoing,
                                                    EC_T_DWORD              dwLikelihoodPpm,
                                                    EC_T_DWORD              dwFixedGoodFramesCnt,
                                                    EC_T_DWORD              dwFixedErroneousFramesCnt);

EC_API EC_T_DWORD EC_API_FNCALL esResetErrorGenerationAtSlavePorts(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress );

EC_API EC_T_DWORD EC_API_FNCALL esSetLinkDownAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort,
                                                    EC_T_BOOL               bDown,
                                                    EC_T_DWORD              dwLinkDownTimeMs );

EC_API EC_T_DWORD EC_API_FNCALL esSetLinkDownGenerationAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort,
                                                    EC_T_DWORD              dwLikelihoodPpm,
                                                    EC_T_DWORD              dwFixedLinkDownTimeMs,
                                                    EC_T_DWORD              dwFixedLinkUpTimeMs );

EC_API EC_T_DWORD EC_API_FNCALL esResetLinkDownGenerationAtSlavePorts(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress    );

EC_API EC_T_DWORD EC_API_FNCALL esLogFrameEnableAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort,
                                                    EC_T_PFLOGFRAME_CB      pvLogFrameCallBack,
                                                    EC_T_VOID*              pvContext           );

EC_API EC_T_DWORD EC_API_FNCALL esLogFrameDisableAtSlavePort(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_BYTE               byPort              );

EC_API EC_T_DWORD EC_API_FNCALL esVoeSend(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_WORD               wDstFixedAddress,
                                                    const EC_T_BYTE*        pbyData,
                                                    EC_T_DWORD              dwDataLen           );

EC_API EC_T_DWORD EC_API_FNCALL esSetVoeReceiveCallback(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_PF_VOE_RECEIVE_CB  pfVoeReceive,
                                                    EC_T_VOID*              pvContext);

EC_API EC_T_DWORD EC_API_FNCALL esGetSimSlaveInfo(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_SIM_SLAVE_INFO*    pSimSlaveInfo);

EC_API EC_T_DWORD EC_API_FNCALL esSetSimSlaveState(
                                                    EC_T_DWORD              dwInstanceID,
                                                    EC_T_WORD               wCfgFixedAddress,
                                                    EC_T_WORD               wDeviceState,
                                                    EC_T_WORD               wDeviceStatusCode);

/*-INLINE METHODS------------------------------------------------------------*/
#ifndef ECAT_INTERFACE
static EC_INLINESTART const EC_T_CHAR* ecatStateToStr(EC_T_STATE eState)
{
    return eState == eEcatState_INIT ? "INIT":
     (eState == eEcatState_PREOP ? "PREOP":
      (eState == eEcatState_SAFEOP ? "SAFEOP":
       (eState == eEcatState_OP ? "OP":
        (eState == eEcatState_BOOTSTRAP ? "BOOTSTRAP":
         (eState == eEcatState_UNKNOWN ? "UNKNOWN":
          "STATE INVALID")))));
} EC_INLINESTOP
#define ecatDeviceStateText(eState)     esGetText(0, ((EC_T_DWORD)(EC_TXT_DEVICE_STATE_BASE+(eState))))
#endif

#ifndef ECAT_INTERFACE
static EC_INLINESTART const EC_T_CHAR* ecatSlaveStateText(EC_T_WORD nState)
{
    if (nState & DEVICE_STATE_ERROR)
        return esGetText(0, ((EC_T_DWORD)(EC_TXT_SLAVE_STATE_ERROR_BASE+(nState & DEVICE_STATE_MASK))));
    else
        return esGetText(0, ((EC_T_DWORD)(EC_TXT_DEVICE_STATE_BASE+(nState & DEVICE_STATE_MASK))));
} EC_INLINESTOP
#endif

static EC_INLINESTART EC_T_DWORD esLinkIoCtl(
    EC_T_DWORD             dwInstanceID,        /**< [in]  Instance ID (Multiple EtherCAT Network Support) */
    EC_T_DWORD             dwAdapterID,         /**< [in]  Adapter ID: 0...3 (EC_SIMULATOR_MAX_LINK_PARMS) */
    EC_T_DWORD             dwCode,              /**< [in]  IOCTL code (EC_LINKIOCTL_...) */
    const EC_T_VOID* const pbyInBuf,            /**< [in]  IOCTL input parameters */
    EC_T_DWORD             dwInBufSize,         /**< [in]  Size of IOCTL input parameters in bytes */
    EC_T_VOID* const       pbyOutBuf,           /**< [out] Buffer for IOCTL output */
    EC_T_DWORD             dwOutBufSize,        /**< [in]  Size of buffer at pbyOutBuf in bytes */
    EC_T_DWORD* const      pdwNumOutData        /**< [out] Amount of bytes written to pbyOutBuf by IOCTL. EC_NULL: amount not set by IOCTL. */
)
{
    return esIoCtl(dwInstanceID, EC_IOCTL_LINKLAYER_MAIN | (dwAdapterID << EC_IOCTL_LINKLAYER_IDX_SHIFT) | dwCode,
                   pbyInBuf, dwInBufSize, pbyOutBuf, dwOutBufSize, pdwNumOutData);
} EC_INLINESTOP

static EC_INLINESTART EC_T_DWORD esSetOemKey(       EC_T_DWORD              dwInstanceID,
                                                    EC_T_UINT64             qwOemKey        )
{
    return esIoCtl(dwInstanceID, EC_IOCTL_SET_OEM_KEY, &qwOemKey, sizeof(EC_T_UINT64), EC_NULL, 0, EC_NULL);
} EC_INLINESTOP

static EC_INLINESTART EC_T_DWORD esCheckOemKey(     EC_T_DWORD              dwInstanceID,
                                                    EC_T_UINT64             qwOemKey        )
{
    return esIoCtl(dwInstanceID, EC_IOCTL_CHECK_OEM_KEY, &qwOemKey, sizeof(EC_T_UINT64), EC_NULL, 0, EC_NULL);
} EC_INLINESTOP

#ifdef __cplusplus
} /* extern "C" */
#endif

#ifndef ECAT_INTERFACE
#define ECAT_INTERFACE
#endif

#endif /* INC_ECSIMULATOR */

/*-END OF SOURCE FILE--------------------------------------------------------*/
