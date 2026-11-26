#!/usr/bin/env python3
"""Build both self-contained native F-KR CMMT FMI 3.0 CS variants."""
import argparse, hashlib, json, platform, re, subprocess, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'model_sources/motor_controller/f_kr_cmmt'
INPUTS=[('control_word','UInt16',0),('mode_request','Int8',1),('quick_stop_option','Int16',2),
 ('target_position','Float64',0),('target_velocity','Float64',0),('profile_velocity','Float64',.1),
 ('profile_acceleration','Float64',1),('profile_deceleration','Float64',1),('quick_stop_deceleration','Float64',1),
 ('position_min','Float64',-1),('position_max','Float64',1),('positive_velocity_limit','Float64',.2),
 ('negative_velocity_limit','Float64',.2),('position_window','Float64',.00002),('position_window_time','Float64',.02)]
OUTPUTS=[('status_word','UInt16'),('mode_display','Int8'),('actual_position','Float64'),('actual_velocity','Float64')]
def build(mode,folder):
 import fmpy
 from fmpy.validation import validate_fmu
 headers=Path(fmpy.__file__).parent/'c-code'
 identifier='FKrCmmt'+mode.title(); token='softesc-f-kr-cmmt-'+mode+'-v1'
 variables=[(i+1,n,k,'input',v) for i,(n,k,v) in enumerate(INPUTS)]+[(101+i,n,k,'output',None) for i,(n,k) in enumerate(OUTPUTS)]
 xml=E.Element('fmiModelDescription',fmiVersion='3.0',modelName=identifier,instantiationToken=token,generationTool='Soft ESC native C++ build',variableNamingConvention='flat')
 E.SubElement(xml,'CoSimulation',modelIdentifier=identifier,canHandleVariableCommunicationStepSize='true',canBeInstantiatedOnlyOncePerProcess='false',hasEventMode='false',mightReturnEarlyFromDoStep='false')
 units=E.SubElement(xml,'UnitDefinitions')
 for name,attrs in [('s',{'s':'1'}),('m' if mode=='linear' else 'rad',{'m':'1'} if mode=='linear' else {'rad':'1'}),('m/s' if mode=='linear' else 'rad/s',dict({'m':'1'} if mode=='linear' else {'rad':'1'},s='-1')),('m/s2' if mode=='linear' else 'rad/s2',dict({'m':'1'} if mode=='linear' else {'rad':'1'},s='-2'))]:E.SubElement(E.SubElement(units,'Unit',name=name),'BaseUnit',**attrs)
 mv=E.SubElement(xml,'ModelVariables')
 for vr,name,kind,causality,start in variables:
  attrs=dict(name=name,valueReference=str(vr),causality=causality,variability='continuous' if kind=='Float64' else 'discrete')
  if start is not None:attrs['start']=str(start)
  else:attrs['initial']='calculated'
  if kind=='Float64':attrs['unit']='s' if name=='position_window_time' else ('m/s2' if mode=='linear' else 'rad/s2') if 'acceleration' in name or 'deceleration' in name else ('m/s' if mode=='linear' else 'rad/s') if 'velocity' in name else ('m' if mode=='linear' else 'rad')
  E.SubElement(mv,kind,**attrs)
 E.SubElement(mv,'Float64',name='time',valueReference='200',causality='independent',variability='continuous',unit='s')
 structure=E.SubElement(xml,'ModelStructure')
 for tag in ['Output','InitialUnknown']:
  for vr,_,_,causality,_ in variables:
   if causality=='output':E.SubElement(structure,tag,valueReference=str(vr))
 access=[]
 for kind in ['Float64','UInt16','Int8','Int16']:
  candidates=[v for v in variables if v[2]==kind]
  def expr(v):return 'm->drive.'+('in.' if v[3]=='input' else 'out.')+v[1]
  for action in ['Get','Set']:
   writable=action=='Set'; items=[v for v in candidates if not writable or v[3]=='input']
   cases=''.join(f'case {v[0]}: '+(f'{expr(v)}=values[j];' if writable else f'values[j]={expr(v)};')+'break;' for v in items)
   allowed=' && '.join(f'vr[j]!={v[0]}' for v in items)
   if kind=='Float64' and not writable:allowed+=' && vr[j]!=200';cases+='case 200: values[j]=m->time;break;'
   finite=' || !std::isfinite(values[j])' if writable and kind=='Float64' else ''
   access.append(f'fmi3Status fmi3{action}{kind}(fmi3Instance i,const fmi3ValueReference vr[],size_t n, {"const " if writable else ""}fmi3{kind} values[],size_t count){{auto m=(Instance*)i;if(!readable(m)||n!=count||(n&&(!vr||!values)))return fmi3Error;for(size_t j=0;j<n;++j)if(({allowed}){finite})return fmi3Error;for(size_t j=0;j<n;++j){{switch(vr[j]){{{cases}}}}}return fmi3OK;}}')
 code=(SOURCE/'fmi.cpp').read_text(); access='\n'.join(access)
 signatures={n:(ret,args) for ret,n,args in re.findall(r'typedef\s+([\w *]+?)\s+(fmi3\w+)TYPE\s*\((.*?)\);',(headers/'fmi3FunctionTypes.h').read_text(),re.S)}
 exports=re.findall(r'FMI3_Export\s+\w+TYPE\s+(fmi3\w+)\s*;',(headers/'fmi3Functions.h').read_text())
 implemented=set(re.findall(r'\b(fmi3[A-Z]\w+)\s*\(',code+access));stubs=['#include "fmi3Functions.h"']
 for name in exports:
  if name in implemented:continue
  ret,args=signatures[name];ret=' '.join(ret.split());body='return fmi3Error;' if ret=='fmi3Status' else 'return nullptr;' if ret=='fmi3Instance' else '' if ret=='void' else None
  if body is None:raise ValueError(name)
  stubs.append(f'{ret} {name}({args}){{{body}}}')
 with tempfile.TemporaryDirectory(prefix='fkr-build-') as tmp:
  stage=Path(tmp);s=stage/'sources';s.mkdir()
  for name in ['drive.hpp','fmi.cpp']:(s/name).write_bytes((SOURCE/name).read_bytes())
  for name in ['fmi3Functions.h','fmi3FunctionTypes.h','fmi3PlatformTypes.h']:(s/name).write_bytes((headers/name).read_bytes())
  (s/'accessors.hpp').write_text(access);(s/'unsupported.cpp').write_text('\n'.join(stubs))
  (s/'variant.hpp').write_text(f'#define TOKEN "{token}"\n#define ANGULAR_SCALE '+('1.0' if mode=='linear' else '(3.14159265358979323846/180.0)')+'\n')
  (s/'buildDescription.xml').write_text(f'<fmiBuildDescription fmiVersion="3.0"><BuildConfiguration modelIdentifier="{identifier}"><SourceFileSet language="C++17"><SourceFile name="fmi.cpp"/><SourceFile name="unsupported.cpp"/></SourceFileSet></BuildConfiguration></fmiBuildDescription>')
  E.indent(xml);E.ElementTree(xml).write(stage/'modelDescription.xml',encoding='utf-8',xml_declaration=True)
  subprocess.run(['g++','-std=c++17','-O2','-I'+str(SOURCE),str(ROOT/'tests/native/test_f_kr_drive.cpp'),'-o',str(stage/'core-test')],check=True)
  subprocess.run([str(stage/'core-test')],check=True)
  (stage/'core-test').unlink()
  binary=stage/f'binaries/x86_64-linux/{identifier}.so';binary.parent.mkdir(parents=True)
  subprocess.run(['g++','-std=c++17','-shared','-fPIC','-O2','-Wl,--build-id=none','-I'+str(s),str(s/'fmi.cpp'),str(s/'unsupported.cpp'),'-o',str(binary)],check=True)
  folder.mkdir(parents=True,exist_ok=True);output=folder/f'{identifier}-linux.fmu';tmpout=output.with_suffix('.tmp')
  with zipfile.ZipFile(tmpout,'w',zipfile.ZIP_DEFLATED) as z:
   for f in sorted(stage.rglob('*')):
    if f.is_file():
     info=zipfile.ZipInfo(f.relative_to(stage).as_posix(),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,f.read_bytes())
  errors=validate_fmu(str(tmpout))
  if errors:raise ValueError(errors)
  tmpout.replace(output)
 report=dict(mode=mode,fmi='3.0',platform='x86_64-linux',artifact_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'drive.hpp',SOURCE/'fmi.cpp',Path(__file__)]})
 output.with_suffix('.provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,default=ROOT/'model_artifacts');a=p.parse_args()
 if platform.system()!='Linux' or platform.machine()!='x86_64':p.error('Linux x86-64 required')
 for mode in ['linear','rotary']:build(mode,a.output_dir)
