#include "mapping_store.h"
#include <sys/wait.h>
#include <sys/stat.h>
#include <iostream>
using namespace cmmt;
using json=nlohmann::json;
static int fault=0;
extern "C" ssize_t __real_write(int,const void*,size_t);
extern "C" int __real_fsync(int);
extern "C" int __real_rename(const char*,const char*);
extern "C" ssize_t __wrap_write(int fd,const void* p,size_t n){
 if(fault==1){errno=ENOSPC;return -1;}return __real_write(fd,p,n);
}
extern "C" int __wrap_fsync(int fd){
 struct stat st{};fstat(fd,&st);bool dir=S_ISDIR(st.st_mode);
 if((fault==2&&!dir)||(fault==4&&dir)){errno=EIO;return -1;}
 int rc=__real_fsync(fd);
 if(fault==5&&!dir)_exit(55); // durable temporary file, before rename
 if(fault==6&&dir)_exit(56); // durable commit, before activation
 return rc;
}
extern "C" int __wrap_rename(const char* a,const char* b){
 if(fault==3){errno=EIO;return -1;}return __real_rename(a,b);
}
static void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static DynamicMapping make(){return DynamicMapping({{{0x6040,0},{16,true,false}},{{0x6041,0},{16,false,true}}});}
static DynamicMapping::Configuration config(bool padded){
 DynamicMapping::Configuration c{{{0x6040,0,16}},{{0x6041,0,16}}};
 if(padded)c.rx.insert(c.rx.begin(),{0,0,8});return c;
}
static std::string read(std::filesystem::path p){std::ifstream f(p);return {std::istreambuf_iterator<char>(f),{}};}
static uint32_t crc(std::string const& s){uint32_t c=~0u;for(unsigned char b:s){c^=b;for(int i=0;i<8;++i)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return ~c;}
int main(){
 char temp[]="/tmp/rf014-fail-XXXXXX";check(mkdtemp(temp),"temporary directory");
 std::filesystem::path root=temp,path=root/"pdo-mappings/61786973.json";
 try{
  for(int kind=1;kind<=7;++kind){
   {MappingStore s(root,"axis",{{"id","axis"}});s.save(config(false));}
   auto old=read(path);auto active=make();active.activate(config(false));
   if(kind==5||kind==6){
    auto pid=fork();check(pid>=0,"fork");
    if(pid==0){MappingStore s(root,"axis",{{"id","axis"}});fault=kind;s.save(config(true));_exit(90);}
    int status=0;check(waitpid(pid,&status,0)==pid,"waitpid");
    check(WIFEXITED(status)&&WEXITSTATUS(status)==(kind==5?55:56),"crash boundary not reached");
   }else{
    MappingStore s(root,"axis",{{"id","axis"}});bool failed=false;
    try{fault=kind<=4?kind:0;s.save(config(true));if(kind==7)throw std::runtime_error("activation unavailable");active.activate(config(true));}
    catch(std::exception const&){failed=true;}fault=0;
    check(failed,"fault not observed");check(DynamicMapping::bytes(active.configuration().rx)==2,"active layout changed on failure");
   }
   bool committed=kind==4||kind==6||kind==7;
   if(!committed)check(read(path)==old,"old durable bytes changed");
   auto restored=make();{MappingStore s(root,"axis",{{"id","axis"}});check(s.load(restored),"restore missing");}
   check(DynamicMapping::bytes(restored.configuration().rx)==(committed?3u:2u),"wrong restored generation");
   std::cout<<"STORE_BOUNDARY case="<<kind<<" restored="<<(committed?"new":"old")<<" passed\n";
  }
  auto valid=json::parse(read(path));
  for(int kind=0;kind<3;++kind){
   auto bad=valid;bad.erase("checksum");
   if(kind==0)bad["schema_version"]=999;
   if(kind==2)bad["rx"]=json::array({8}); // valid envelope, missing controlword
   bad["checksum"]=crc(bad.dump());if(kind==1)bad["checksum"]=0;
   {std::ofstream f(path);f<<bad.dump();}
   auto original=read(path);auto m=make();bool rejected=false,logical=false;
   try{MappingStore s(root,"axis",{{"id","axis"}});s.load(m);}
   catch(MappingError const&){rejected=true;logical=true;}catch(std::exception const&){rejected=true;}
   check(rejected&&logical==(kind==2),"wrong restore error category");
   check(!m.active()&&m.read(0x1c12,0)==0,"partial candidate restored");
   check(read(path)==original,"invalid source modified");
   std::cout<<"STORE_RESTORE case="<<kind<<" passed\n";
  }
  std::filesystem::remove_all(root);
 }catch(...){fault=0;std::filesystem::remove_all(root);throw;}
}
