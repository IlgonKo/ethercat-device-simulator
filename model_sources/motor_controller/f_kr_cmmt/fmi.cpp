#include "fmi3Functions.h"
#include "drive.hpp"
#include <cstring>
#include <new>
#include "variant.hpp"
struct Instance { fkr::Drive drive{ANGULAR_SCALE}; int phase=0; double time=0; };
static bool readable(Instance* m) {return m && m->phase<3;}
const char* fmi3GetVersion(){return "3.0";}
fmi3Status fmi3SetDebugLogging(fmi3Instance i,fmi3Boolean,size_t n,const fmi3String[]) {return readable((Instance*)i)&&!n?fmi3OK:fmi3Error;}
fmi3Instance fmi3InstantiateCoSimulation(fmi3String name,fmi3String token,fmi3String,
 fmi3Boolean,fmi3Boolean,fmi3Boolean events,fmi3Boolean,const fmi3ValueReference[],size_t count,
 fmi3InstanceEnvironment,fmi3LogMessageCallback,fmi3IntermediateUpdateCallback) {
 if(!name||!*name||!token||std::strcmp(token,TOKEN)||events||count)return nullptr;
 return new(std::nothrow) Instance;
}
void fmi3FreeInstance(fmi3Instance i){delete (Instance*)i;}
fmi3Status fmi3EnterInitializationMode(fmi3Instance i,fmi3Boolean td,fmi3Float64 tol,fmi3Float64 start,fmi3Boolean sd,fmi3Float64 end){
 auto m=(Instance*)i;if(!m||m->phase!=0||!std::isfinite(start)||(td&&(!std::isfinite(tol)||tol<=0))||(sd&&(!std::isfinite(end)||end<=start)))return fmi3Error;
 m->time=start;m->phase=1;return fmi3OK;
}
fmi3Status fmi3ExitInitializationMode(fmi3Instance i){auto m=(Instance*)i;if(!m||m->phase!=1)return fmi3Error;m->drive.initialize();m->phase=2;return fmi3OK;}
fmi3Status fmi3Terminate(fmi3Instance i){auto m=(Instance*)i;if(!m||m->phase!=2)return fmi3Error;m->phase=3;return fmi3OK;}
fmi3Status fmi3Reset(fmi3Instance i){auto m=(Instance*)i;if(!m)return fmi3Error;*m=Instance{};return fmi3OK;}
#include "accessors.hpp"
fmi3Status fmi3DoStep(fmi3Instance i,fmi3Float64 t,fmi3Float64 h,fmi3Boolean,
 fmi3Boolean* event,fmi3Boolean* terminate,fmi3Boolean* early,fmi3Float64* last){
 auto m=(Instance*)i;if(!m||m->phase!=2||!event||!terminate||!early||!last)return fmi3Error;
 *event=*terminate=*early=fmi3False;*last=m->time;
 if(!std::isfinite(t)||!std::isfinite(h)||h<=0||h>.1||!std::isfinite(t+h)||t+h<=t||std::abs(t-m->time)>1e-12*std::max(1.,std::abs(t)))return fmi3Error;
 try{m->drive.step(h);if(!std::isfinite(m->drive.out.actual_position)||!std::isfinite(m->drive.out.actual_velocity))throw std::runtime_error("Nonfinite feedback");}
 catch(...){m->phase=4;return fmi3Error;}
 m->time=t+h;*last=m->time;return fmi3OK;
}
