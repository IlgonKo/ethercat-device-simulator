// Core-only fault injection: no extra public FMU input or reset interface.
#include "drive.hpp"
#include <cassert>
int main(){
 for(double scale:{1.,3.14159265358979323846/180.}){
  fkr::Drive d(scale);d.in.mode_request=6;d.initialize();
  for(int cw:{6,7,15}){d.in.control_word=cw;d.step(.008);}
  d.in.control_word=0x1f;for(int i=0;i<13;++i)d.step(.008);
  assert(d.out.status_word&0x8000);
  d.in.control_word=15;d.in.mode_request=3;d.step(.008);
  d.in.target_velocity=.1*scale;for(int i=0;i<20;++i)d.step(.008);
  d.state=fkr::Drive::Fault;d.step(.008);
  assert((d.out.status_word&0x6f)==8 && d.out.actual_velocity==0);
  double position=d.out.actual_position;
  d.in.control_word=0x80;d.step(.008);
  for(int cw:{6,7,15}){d.in.control_word=cw;d.step(.008);}
  assert(d.out.actual_position==position && (d.out.status_word&0x8000));
  d.in.control_word=0;d.step(.008);d.in.mode_request=6;
  for(int cw:{6,7,15}){d.in.control_word=cw;d.step(.008);}
  d.in.control_word=0x1f;d.step(.008);d.state=fkr::Drive::Fault;
  for(int i=0;i<20;++i)d.step(.008);
  assert(!(d.out.status_word&0x8000));
 }
}
