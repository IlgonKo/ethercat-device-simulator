#include "mapping_store.h"
#include <iostream>
using namespace cmmt;
static void require(bool ok){if(!ok)throw std::runtime_error("mapping storage check failed");}
static DynamicMapping make(){return DynamicMapping({{{0x6040,0},{16,true,false}},{{0x6041,0},{16,false,true}}});}
int main(){
 char root[]="/tmp/rf014-store-XXXXXX";require(mkdtemp(root));
 try {
   auto m=make();auto w=[&](int i,int s,uint32_t v){m.write(i,s,v,true);};
   for(auto p:{std::pair{0x1600,0x60400010u},std::pair{0x1a00,0x60410010u}}){
     w(p.first,1,p.second);w(p.first,0,1);int a=p.first==0x1600?0x1c12:0x1c13;w(a,1,p.first);w(a,0,1);
   }
   {
     MappingStore store(root,"axis/a",{{"id","axis/a"}});require(!store.load(m));
     bool locked=false;try{MappingStore second(root,"axis/a",{{"id","axis/a"}});}catch(...){locked=true;}require(locked);
     store.save(m.prepare()); // save before activation; restart restores committed config
   }
   {
     auto restored=make();MappingStore store(root,"axis/a",{{"id","axis/a"}});
     require(store.load(restored));require(restored.active());require(restored.read(0x1600,1)==0x60400010);
     restored.write(0x1c12,0,0,true); // uncommitted candidate must not persist
   }
   {
     auto restored=make();MappingStore store(root,"axis/a",{{"id","axis/a"}});
     require(store.load(restored));require(restored.read(0x1c12,0)==1);
   }
   {
     bool rejected=false;try{auto m2=make();MappingStore store(root,"axis/a",{{"id","changed"}});store.load(m2);}catch(...){rejected=true;}require(rejected);
   }
   for(auto const& f:std::filesystem::directory_iterator(std::filesystem::path(root)/"pdo-mappings"))
     if(f.path().extension()==".json"){std::ofstream bad(f.path());bad<<"broken";}
   {
     bool rejected=false;try{auto m2=make();MappingStore store(root,"axis/a",{{"id","axis/a"}});store.load(m2);}catch(...){rejected=true;}require(rejected);
   }
   std::filesystem::remove_all(root);std::cout<<"Durable mapping restore, isolation, lock and corruption checks passed\n";
 }catch(...){std::filesystem::remove_all(root);throw;}
}
