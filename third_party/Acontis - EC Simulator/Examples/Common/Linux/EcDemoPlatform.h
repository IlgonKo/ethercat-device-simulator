/** ---------------------------------------------------------------------------
 * \file        EcDemoPlatform.h
 * \brief       Platform specific settings for examples
 * \author      Holger Oelhaf
 * \copyright   acontis technologies GmbH, Weingarten, Germany
 *---------------------------------------------------------------------------*/

#ifndef INC_ECDEMOPLATFORM_H
#define INC_ECDEMOPLATFORM_H 1

/*-DEFINES-------------------------------------------------------------------*/
#define TIMER_THREAD_PRIO           ((EC_T_DWORD)99)    /* Timing task priority */
#define JOBS_THREAD_PRIO            ((EC_T_DWORD)98)    /* Job task priority */
#define RECV_THREAD_PRIO            ((EC_T_DWORD)97)    /* Real-time Ethernet Driver interrupt service thread (IST) priority */
#define REMOTE_RECV_THREAD_PRIO     ((EC_T_DWORD)39)    /* RAS Client thread priority */
#define MAIN_THREAD_PRIO            ((EC_T_DWORD)39)    /* Main thread priority */
#define LOG_THREAD_PRIO             ((EC_T_DWORD)29)    /* Log thread priority */

#define TIMER_THREAD_STACKSIZE      0x1000
#if ((EC_ARCH == EC_ARCH_X64) || (EC_ARCH == EC_ARCH_ARM64) || (EC_ARCH == EC_ARCH_RISCV64))
#define JOBS_THREAD_STACKSIZE       0x8000
#define LOG_THREAD_STACKSIZE        0x8000
#else
#define JOBS_THREAD_STACKSIZE       0x4000
#define LOG_THREAD_STACKSIZE        0x4000
#endif

#endif /* INC_ECDEMOPLATFORM_H */

/*-END OF SOURCE FILE--------------------------------------------------------*/
