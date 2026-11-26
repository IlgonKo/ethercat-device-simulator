// RF-015 kinematic drive, independent of EtherCAT and FMI.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace fkr {
struct Inputs {
    uint16_t control_word=0;
    int8_t mode_request=1;
    int16_t quick_stop_option=2;
    double target_position=0, target_velocity=0, profile_velocity=.1;
    double profile_acceleration=1, profile_deceleration=1, quick_stop_deceleration=1;
    double position_min=-1, position_max=1;
    double positive_velocity_limit=.2, negative_velocity_limit=.2;
    double position_window=.00002, position_window_time=.02;
};
struct Outputs {
    uint16_t status_word=0x40;
    int8_t mode_display=1;
    double actual_position=0, actual_velocity=0;
};
class Drive {
public:
    Inputs in;
    Outputs out;
    enum State {Disabled, Ready, Switched, Enabled, Fault, QuickStop};
    State state=Disabled;
    explicit Drive(double angular_scale=1): scale(angular_scale) {}
    void initialize() { out.mode_display=in.mode_request; }
    void step(double h) {
        if (!std::isfinite(h) || h<=0 || h>.1) throw std::invalid_argument("Invalid step size");
        if (in.quick_stop_option!=2 || in.quick_stop_deceleration<=0)
            throw std::invalid_argument("Invalid Quick Stop configuration");
        if (in.mode_request!=0 && in.mode_request!=1 && in.mode_request!=3 &&
            in.mode_request!=-3 && in.mode_request!=6 && in.mode_request!=8)
            throw std::invalid_argument("Unsupported mode");
        if (in.profile_velocity<0 || in.profile_acceleration<0 || in.profile_deceleration<0 ||
            in.positive_velocity_limit<0 || in.negative_velocity_limit<0 ||
            in.position_window<0 || in.position_window_time<0 || in.position_min>in.position_max)
            throw std::invalid_argument("Invalid physical input bounds");
        dt=h;cw=in.control_word;halt=(cw&0x100)!=0;
        const auto old=state; transition();
        if(state==QuickStop) {
            if(old!=QuickStop) begin_stop(Quick,in.quick_stop_deceleration);
            step_stop();
        } else if(state!=Enabled) {
            cancel();apply_mode();
        } else {
            apply_mode();
            if(stop==None && !halt && neutral()) rearm=false;
            if(!(cw&0x10)) {armed=true;ack=false;}
            if(halt && out.mode_display!=8) {
                rearm=true;
                if(moving() && stop==None) begin_stop(Halt,has_pp?pp.decel:in.profile_deceleration);
                if(out.mode_display==1) reached=false;
            }
            if(stop!=None) step_stop();
            else if(!halt || out.mode_display==8) {
                switch(out.mode_display) {
                    case 1: pp_step(); break;
                    case 3: {
                        double target=in.target_velocity;
                        double cap=std::abs(target>=0?in.positive_velocity_limit:in.negative_velocity_limit);
                        if(cap>0) target=std::clamp(target,-cap,cap);
                        velocity_step(target);break;
                    }
                    case -3: {
                        bool pos=cw&0x10,neg=cw&0x20;
                        double cap=0;
                        for(double value:{std::abs(in.profile_velocity),std::abs(in.positive_velocity_limit),std::abs(in.negative_velocity_limit)})
                            if(value>0 && (cap==0 || value<cap)) cap=value;
                        const double factor=(cw&0x1000)?1:(cw&0x800)?.25:.5;
                        velocity_step(pos==neg?0:(pos?1:-1)*cap*factor);break;
                    }
                    case 6: home_step();break;
                    case 8: csp_step();break;
                }
            }
        }
        if((pp_active || velocity_active) && has_limits && out.actual_position>=lo && out.actual_position<=hi) warning=false;
        out.status_word=base_status();
        if(reached) out.status_word|=0x400;
        if(ack && out.mode_display==1) out.status_word|=0x1000;
        if(moving()) out.status_word|=0x100;
        if(warning) out.status_word|=0x880;
        if(referenced) out.status_word|=0x8000;
        previous=cw;
    }
private:
    struct Profile { double target,velocity,accel,decel; } pp{};
    enum Stop {None,Halt,Normal,Limit,Quick};
    double scale,dt=0,stop_decel=0,lo=0,hi=0,home_elapsed=0,window_elapsed=0;
    double last_csp=0,pp_target=0;
    int window_count=0;
    uint16_t previous=0,cw=0;
    bool halt=false,has_pp=false,pp_active=false,ack=false,armed=false;
    bool velocity_active=false,rearm=false,has_limits=false,home_active=false,referenced=false;
    bool reached=false,warning=false;
    Stop stop=None;
    double eps() const {return 1e-9*scale;}
    bool moving() const {return std::abs(out.actual_velocity)>eps() || pp_active || home_active || velocity_active || stop!=None;}
    bool neutral() const {
        if(out.mode_display==3) return in.target_velocity==0;
        if(out.mode_display==-3) return bool(cw&0x10)==bool(cw&0x20);
        return in.target_velocity==0 && !(cw&0x30);
    }
    void transition() {
        if(cw&0x80) {if(state==Fault)state=Disabled;return;}
        if((cw&0x87)==0) {state=Disabled;return;}
        if(state==QuickStop) {
            if((cw&0x8f)==7)state=Switched;
            else if((cw&0x87)==6)state=Ready;
            return;
        }
        if(state==Enabled && (cw&0x86)==2){state=QuickStop;return;}
        if(state==Disabled && (cw&0x87)==6)state=Ready;
        else if(state==Ready && (cw&0x8f)==7)state=Switched;
        else if(state==Switched) {
            if((cw&0x8f)==15)state=Enabled;
            else if((cw&0x87)==6)state=Ready;
        } else if(state==Enabled) {
            if((cw&0x8f)==7)state=Switched;
            else if((cw&0x87)==6)state=Ready;
        }
    }
    uint16_t base_status() const {
        switch(state){case Disabled:return 0x40;case Ready:return 0x21;case Switched:return 0x23;
            case Enabled:return 0x27;case QuickStop:return 7;default:return 8;}
    }
    void cancel() {
        out.actual_velocity=0;pp_active=false;ack=false;has_pp=false;stop=None;
        velocity_active=false;rearm=true;armed=false;
        if(home_active)referenced=false;
        home_active=false;home_elapsed=0;window_count=0;window_elapsed=0;reached=false;
    }
    void apply_mode() {
        if(in.mode_request==out.mode_display || moving())return;
        out.mode_display=in.mode_request;has_pp=false;ack=false;reached=false;has_limits=false;
    }
    void limits() {
        if(in.position_min>in.position_max) throw std::invalid_argument("Reversed limits");
        lo=in.position_min;hi=in.position_max;has_limits=true;
    }
    static double approach(double value,double target,double delta) {
        if(delta<=0)return value;
        if(std::abs(target-value)<=delta)return target;
        return value+delta*(target>value?1:-1);
    }
    void begin_stop(Stop kind,double decel) {
        if(stop!=None && kind!=Quick)return;
        decel=std::abs(decel);
        if(!std::isfinite(decel)||decel<=0)throw std::invalid_argument("Invalid stop deceleration");
        stop=kind;stop_decel=decel;pp_active=false;ack=false;armed=false;
        velocity_active=false;rearm=true;
        if(home_active)referenced=false;
        home_active=false;home_elapsed=0;reached=false;
    }
    void step_stop() {
        if(stop==None)return;
        out.actual_velocity=approach(out.actual_velocity,0,stop_decel*dt);
        out.actual_position+=out.actual_velocity*dt;
        if(std::abs(out.actual_velocity)<=eps()) {
            out.actual_velocity=0;auto reason=stop;stop=None;has_pp=false;
            if(reason==Quick)state=Disabled;
            else if(!halt && neutral())rearm=false;
        }
    }
    void home_step() {
        if(home_active && !(cw&0x10)) {home_active=false;referenced=false;home_elapsed=0;reached=false;return;}
        bool edge=(cw&0x10) && !(previous&0x10);
        if(edge && !moving()){home_active=true;home_elapsed=0;referenced=false;reached=false;}
        if(!home_active)return;
        home_elapsed+=dt;
        if(home_elapsed+1e-12<.1)return;
        out.actual_position=0;out.actual_velocity=0;pp_target=0;has_pp=false;has_limits=false;
        home_active=false;referenced=true;reached=true;
    }
    void pp_complete() {
        if(std::abs(out.actual_position-pp_target)<=std::abs(in.position_window) && std::abs(out.actual_velocity)<=eps())
            window_elapsed+=dt;
        else {window_elapsed=0;return;}
        if(window_elapsed+1e-12>=std::max(0.,in.position_window_time)){reached=true;pp_active=false;}
    }
    void pp_step() {
        bool edge=(cw&0x10) && !(previous&0x10);
        if(edge && armed && !moving()) {
            armed=false;reached=false;
            if(!referenced)return;
            limits();
            if(in.target_position<lo || in.target_position>hi){warning=true;return;}
            double velocity=std::abs(in.profile_velocity);
            double cap=std::abs(in.target_position>=out.actual_position?in.positive_velocity_limit:in.negative_velocity_limit);
            if(cap>0)velocity=std::min(velocity,cap);
            pp={in.target_position,velocity,std::abs(in.profile_acceleration),std::abs(in.profile_deceleration)};
            has_pp=true;pp_target=pp.target;pp_active=true;ack=true;window_elapsed=0;
        }
        if(!pp_active)return;
        double error=pp.target-out.actual_position,distance=std::abs(error);
        if(distance<=std::abs(in.position_window) && std::abs(out.actual_velocity)<=std::max(pp.decel*dt,eps())){
            out.actual_position=pp.target;out.actual_velocity=0;pp_complete();return;
        }
        double direction=error>=0?1:-1, toward=out.actual_velocity*direction;
        double stopping=pp.decel>0?std::pow(std::max(toward,0.),2)/(2*pp.decel):0;
        double desired, ramp;
        if(toward<0 || distance<=stopping){desired=0;ramp=pp.decel;}
        else {desired=direction*pp.velocity;ramp=pp.accel;}
        out.actual_velocity=approach(out.actual_velocity,desired,ramp*dt);
        double next=out.actual_position+out.actual_velocity*dt;
        if(error==0 || error*(pp.target-next)<=0){out.actual_position=pp.target;out.actual_velocity=0;}
        else out.actual_position=next;
        pp_complete();
    }
    void velocity_step(double target) {
        if(rearm){if(std::abs(target)<=1e-12*scale)rearm=false;return;}
        if(target==0){
            if(velocity_active || std::abs(out.actual_velocity)>eps()){begin_stop(Normal,in.profile_deceleration);step_stop();}
            return;
        }
        if(!velocity_active){limits();velocity_active=true;}
        if((target>0 && out.actual_position>=hi)||(target<0 && out.actual_position<=lo)){
            warning=true;begin_stop(Limit,in.profile_deceleration);step_stop();return;
        }
        bool reverse=target*out.actual_velocity<0;
        double desired=reverse?0:target;
        double ramp=(reverse || std::abs(desired)<std::abs(out.actual_velocity))?in.profile_deceleration:in.profile_acceleration;
        out.actual_velocity=approach(out.actual_velocity,desired,ramp*dt);
        out.actual_position+=out.actual_velocity*dt;
        reached=std::abs(out.actual_velocity-target)<=eps();
    }
    void csp_step() {
        double target=in.target_position;
        if(target!=last_csp){
            if(!referenced)target=last_csp;
            else if(target<in.position_min || target>in.position_max){warning=true;cancel();target=out.actual_position;}
            last_csp=target;
        }
        if(halt || !referenced){
            out.actual_velocity=approach(out.actual_velocity,0,std::abs(in.profile_deceleration)*dt);
            out.actual_position+=out.actual_velocity*dt;
            reached=halt && std::abs(out.actual_velocity)<=eps();return;
        }
        double cap=std::abs(in.positive_velocity_limit);
        if(target<out.actual_position && in.negative_velocity_limit>0)cap=std::abs(in.negative_velocity_limit);
        double velocity=cap>0?std::min(std::abs(in.profile_velocity),cap):std::abs(in.profile_velocity);
        double desired=std::clamp(5*(target-out.actual_position),-velocity,velocity);
        double ramp=std::abs(desired)>std::abs(out.actual_velocity)?in.profile_acceleration:in.profile_deceleration;
        out.actual_velocity+=std::clamp(desired-out.actual_velocity,-ramp*dt,ramp*dt);
        out.actual_position+=out.actual_velocity*dt;
        if(std::abs(target-out.actual_position)<=std::abs(in.position_window))++window_count;
        else {window_count=0;reached=false;}
        if(window_count>=std::max(1,int(in.position_window_time/dt)))reached=true;
    }
};
}
