/* Soft ESC raw Int16 pure transport delay, FMI 3.0 Co-Simulation.
 * Values are sampled at t; outputs are evaluated after completing [t,t+h].
 * No dependence on EtherCAT, wall time, or a particular importing application.
 */
#include "fmi3Functions.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>
#define TOKEN "{f42d8c6a-1be6-4ad1-876f-aeb827aa0130}"
#define VR_COMMAND 1
#define VR_FEEDBACK 2
#define VR_DELAY 3
#define VR_TIME 4

typedef struct Sample {double time;fmi3Int16 value;struct Sample* next;} Sample;
typedef struct {int phase;double time,delay;fmi3Int16 command,feedback;Sample *head,*tail;} Model;
static void clear(Model* m) {while(m->head){Sample* next=m->head->next;free(m->head);m->head=next;}m->tail=NULL;}
static int readable(Model* m) {return m && m->phase<3;}
/* Tolerate importer floating-point clock accumulation, far below an 8 ms tick. */
static double tolerance(double t) {return 1e-12*fmax(1.,fabs(t));}
const char* fmi3GetVersion(void){return "3.0";}
fmi3Status fmi3SetDebugLogging(fmi3Instance instance,fmi3Boolean loggingOn,size_t nCategories,const fmi3String categories[]) {
    (void)loggingOn;(void)categories;return readable(instance) && nCategories==0?fmi3OK:fmi3Error;
}
fmi3Instance fmi3InstantiateCoSimulation(fmi3String instanceName,fmi3String instantiationToken,fmi3String resourcePath,
    fmi3Boolean visible,fmi3Boolean loggingOn,fmi3Boolean eventModeUsed,fmi3Boolean earlyReturnAllowed,
    const fmi3ValueReference requiredIntermediateVariables[],size_t nRequiredIntermediateVariables,
    fmi3InstanceEnvironment instanceEnvironment,fmi3LogMessageCallback logMessage,fmi3IntermediateUpdateCallback intermediateUpdate) {
    (void)resourcePath;(void)visible;(void)loggingOn;(void)earlyReturnAllowed;(void)requiredIntermediateVariables;
    (void)instanceEnvironment;(void)logMessage;(void)intermediateUpdate;
    if(!instanceName || !*instanceName || !instantiationToken || strcmp(instantiationToken,TOKEN) || eventModeUsed || nRequiredIntermediateVariables)return NULL;
    Model* m=calloc(1,sizeof(Model));if(m)m->delay=.016;return m;
}
void fmi3FreeInstance(fmi3Instance instance) {Model* m=instance;if(m){clear(m);free(m);}}
fmi3Status fmi3EnterInitializationMode(fmi3Instance instance,fmi3Boolean toleranceDefined,fmi3Float64 toleranceValue,
    fmi3Float64 startTime,fmi3Boolean stopTimeDefined,fmi3Float64 stopTime) {
    Model* m=instance;
    if(!m || m->phase!=0 || !isfinite(startTime) || (toleranceDefined && (!isfinite(toleranceValue) || toleranceValue<=0)) || (stopTimeDefined && (!isfinite(stopTime) || stopTime<=startTime)))return fmi3Error;
    m->time=startTime;m->phase=1;return fmi3OK;
}
fmi3Status fmi3ExitInitializationMode(fmi3Instance instance) {
    Model* m=instance;if(!m || m->phase!=1)return fmi3Error;m->feedback=0;m->phase=2;return fmi3OK;
}
fmi3Status fmi3Terminate(fmi3Instance instance) {Model* m=instance;if(!m || m->phase!=2)return fmi3Error;m->phase=3;return fmi3OK;}
fmi3Status fmi3Reset(fmi3Instance instance) {
    Model* m=instance;if(!m)return fmi3Error;clear(m);memset(m,0,sizeof(*m));m->delay=.016;return fmi3OK;
}
fmi3Status fmi3GetFloat64(fmi3Instance instance,const fmi3ValueReference vr[],size_t nvr,fmi3Float64 values[],size_t nValues) {
    Model* m=instance;if(!readable(m) || nvr!=nValues || (nvr && (!vr || !values)))return fmi3Error;
    for(size_t i=0;i<nvr;++i)if(vr[i]!=VR_DELAY && vr[i]!=VR_TIME)return fmi3Error;
    for(size_t i=0;i<nvr;++i)values[i]=vr[i]==VR_DELAY?m->delay:m->time;
    return fmi3OK;
}
fmi3Status fmi3SetFloat64(fmi3Instance instance,const fmi3ValueReference vr[],size_t nvr,const fmi3Float64 values[],size_t nValues) {
    Model* m=instance;if(!readable(m) || m->phase>1 || nvr!=nValues || (nvr && (!vr || !values)))return fmi3Error;
    for(size_t i=0;i<nvr;++i)if(vr[i]!=VR_DELAY || !isfinite(values[i]) || values[i]<0 || values[i]>10)return fmi3Error;
    for(size_t i=0;i<nvr;++i)m->delay=values[i];
    return fmi3OK;
}
fmi3Status fmi3GetInt16(fmi3Instance instance,const fmi3ValueReference vr[],size_t nvr,fmi3Int16 values[],size_t nValues) {
    Model* m=instance;if(!readable(m) || nvr!=nValues || (nvr && (!vr || !values)))return fmi3Error;
    for(size_t i=0;i<nvr;++i)if(vr[i]!=VR_COMMAND && vr[i]!=VR_FEEDBACK)return fmi3Error;
    for(size_t i=0;i<nvr;++i)values[i]=vr[i]==VR_COMMAND?m->command:m->feedback;
    return fmi3OK;
}
fmi3Status fmi3SetInt16(fmi3Instance instance,const fmi3ValueReference vr[],size_t nvr,const fmi3Int16 values[],size_t nValues) {
    Model* m=instance;if(!readable(m) || nvr!=nValues || (nvr && (!vr || !values)))return fmi3Error;
    for(size_t i=0;i<nvr;++i)if(vr[i]!=VR_COMMAND)return fmi3Error;
    for(size_t i=0;i<nvr;++i)m->command=values[i];
    return fmi3OK;
}
fmi3Status fmi3DoStep(fmi3Instance instance,fmi3Float64 currentCommunicationPoint,fmi3Float64 communicationStepSize,
    fmi3Boolean noSetFMUStatePriorToCurrentPoint,fmi3Boolean* eventHandlingNeeded,fmi3Boolean* terminateSimulation,
    fmi3Boolean* earlyReturn,fmi3Float64* lastSuccessfulTime) {
    (void)noSetFMUStatePriorToCurrentPoint;Model* m=instance;
    if(!m || m->phase!=2 || !eventHandlingNeeded || !terminateSimulation || !earlyReturn || !lastSuccessfulTime)return fmi3Error;
    *eventHandlingNeeded=*terminateSimulation=*earlyReturn=fmi3False;*lastSuccessfulTime=m->time;
    double end=currentCommunicationPoint+communicationStepSize;
    if(!isfinite(currentCommunicationPoint) || !isfinite(communicationStepSize) || communicationStepSize<=0 || !isfinite(end) || end<=currentCommunicationPoint || fabs(currentCommunicationPoint-m->time)>tolerance(m->time))return fmi3Error;
    Sample* next=malloc(sizeof(Sample));if(!next)return fmi3Error;
    next->time=currentCommunicationPoint;next->value=m->command;next->next=NULL;
    if(m->tail)m->tail->next=next;else m->head=next;m->tail=next;
    while(m->head && m->head->time+m->delay<=end+tolerance(end)) {
        Sample* sample=m->head;m->feedback=sample->value;m->head=sample->next;free(sample);
    }
    if(!m->head)m->tail=NULL;
    m->time=end;*lastSuccessfulTime=end;return fmi3OK;
}
