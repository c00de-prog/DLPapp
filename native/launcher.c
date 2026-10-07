/* Portable launcher: verify/extract embedded ZIP once, then reuse its runtime. */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shlobj.h>
#include <wincrypt.h>
#include <stdio.h>
#include <stdint.h>
#include <wchar.h>

#pragma pack(push,1)
typedef struct { char magic[8]; uint64_t offset,size; char hash[64]; uint32_t mode,reserved; } Trailer;
#pragma pack(pop)
#define CAP 4096
static int russian(void) { return PRIMARYLANGID(GetUserDefaultUILanguage()) == LANG_RUSSIAN; }
static void error(const wchar_t *en,const wchar_t *ru) {
 wchar_t text[4600];swprintf(text,4600,L"%ls\nWindows error: %lu",russian()?ru:en,GetLastError());
 MessageBoxW(NULL,text,L"DLPapp",MB_OK|MB_ICONERROR);
}
static int exists(const wchar_t *p) { DWORD a=GetFileAttributesW(p);return a!=INVALID_FILE_ATTRIBUTES && !(a&FILE_ATTRIBUTE_DIRECTORY); }
static void quote_ps(const wchar_t *p,wchar_t *out) {
 while(*p) { if(*p==L'\'') *out++=L'\''; *out++=*p++; } *out=0;
}
static HWND splash(void) {
 HWND w=CreateWindowExW(WS_EX_TOPMOST,L"STATIC",L"DLPapp",WS_OVERLAPPED|WS_CAPTION,
  (GetSystemMetrics(SM_CXSCREEN)-480)/2,(GetSystemMetrics(SM_CYSCREEN)-110)/2,480,110,NULL,NULL,GetModuleHandleW(NULL),NULL);
 HWND label=CreateWindowW(L"STATIC",russian()?L"Подготовка первого запуска…\nРаспаковка выполняется один раз для каждой версии.":L"Preparing first launch…\nComponents are extracted once per version.",WS_CHILD|WS_VISIBLE,
  18,15,440,55,w,NULL,GetModuleHandleW(NULL),NULL);
 SendMessageW(label,WM_SETFONT,(WPARAM)GetStockObject(DEFAULT_GUI_FONT),TRUE);
 ShowWindow(w,SW_SHOW);UpdateWindow(w);return w;
}
static DWORD wait_process(HANDLE h) {
 MSG msg;
 for(;;) {
  DWORD r=MsgWaitForMultipleObjects(1,&h,FALSE,INFINITE,QS_ALLINPUT);
  if(r==WAIT_OBJECT_0)break;
  if(r==WAIT_FAILED)return 1;
  while(PeekMessageW(&msg,NULL,0,0,PM_REMOVE)){TranslateMessage(&msg);DispatchMessageW(&msg);}
 }
 DWORD code=1;GetExitCodeProcess(h,&code);return code;
}
static int write_payload(FILE *self,Trailer *t,const wchar_t *destination) {
 FILE *out=_wfopen(destination,L"wb");if(!out)return 0;
 HCRYPTPROV provider=0;HCRYPTHASH digest=0;int ok=0;
 if(!CryptAcquireContextW(&provider,NULL,NULL,PROV_RSA_AES,CRYPT_VERIFYCONTEXT))goto end;
 if(!CryptCreateHash(provider,CALG_SHA_256,0,0,&digest))goto end;
 if(_fseeki64(self,t->offset,SEEK_SET))goto end;
 unsigned char buffer[1024*1024];uint64_t left=t->size;
 while(left){size_t n=left>sizeof(buffer)?sizeof(buffer):(size_t)left;
  if(fread(buffer,1,n,self)!=n || fwrite(buffer,1,n,out)!=n || !CryptHashData(digest,buffer,(DWORD)n,0))goto end;
  left-=n;
 }
 BYTE result[32];DWORD size=32;char hex[65];
 if(!CryptGetHashParam(digest,HP_HASHVAL,result,&size,0))goto end;
 for(int i=0;i<32;i++)sprintf(hex+i*2,"%02x",result[i]);
 ok=!memcmp(hex,t->hash,64);
 end:if(digest)CryptDestroyHash(digest);if(provider)CryptReleaseContext(provider,0);
 if(fclose(out))ok=0;
 return ok;
}
static int ready(const wchar_t *cache,Trailer *t) {
 wchar_t path[CAP];char hash[64];
 swprintf(path,CAP,L"%ls\\.ready",cache);FILE *f=_wfopen(path,L"rb");if(!f)return 0;
 int valid=fread(hash,1,64,f)==64&&!memcmp(hash,t->hash,64);fclose(f);if(!valid)return 0;
 const wchar_t *files_python[]={L"pythonw.exe",L"python312.dll",L"bootstrap.py",L"app.py",L"i18n.py",L"assets\\logo.png",L"tools\\yt-dlp.exe",L"tools\\ffmpeg.exe",L"tools\\ffprobe.exe",L"tools\\deno.exe"};
 const wchar_t *files_frozen[]={L"DLPappRuntime\\DLPappRuntime.exe",L"DLPappRuntime\\_internal\\assets\\logo.png",L"DLPappRuntime\\_internal\\tools\\yt-dlp.exe",L"DLPappRuntime\\_internal\\tools\\ffmpeg.exe",L"DLPappRuntime\\_internal\\tools\\ffprobe.exe",L"DLPappRuntime\\_internal\\tools\\deno.exe"};
 const wchar_t **files=t->mode==1?files_python:files_frozen;
 int count=t->mode==1?10:6;
 for(int i=0;i<count;i++){swprintf(path,CAP,L"%ls\\%ls",cache,files[i]);if(!exists(path))return 0;}return 1;
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR arguments,int show) {
 (void)instance;(void)previous;(void)arguments;(void)show;
 wchar_t selfpath[CAP],home[CAP],local[CAP],parent[CAP],cache[CAP],zip[CAP],hash[65],mutex_name[100];
 DWORD len=GetModuleFileNameW(NULL,selfpath,CAP);if(!len||len>=CAP){error(L"Cannot locate executable.",L"Не удалось определить путь EXE.");return 1;}
 wcscpy(home,selfpath);wchar_t *slash=wcsrchr(home,L'\\');if(!slash)return 1;*slash=0;
 FILE *self=_wfopen(selfpath,L"rb");if(!self)return 1;
 _fseeki64(self,0,SEEK_END);int64_t total=_ftelli64(self);Trailer t;
 if(total<(int64_t)sizeof(t)||_fseeki64(self,-(int64_t)sizeof(t),SEEK_END)||fread(&t,1,sizeof(t),self)!=sizeof(t)
  ||memcmp(t.magic,"DLPCA02",8)||t.offset>(uint64_t)total||t.size>(uint64_t)total-t.offset
  ||t.offset+t.size!=(uint64_t)total-sizeof(t)||(t.mode!=1&&t.mode!=2)){
  fclose(self);error(L"Invalid embedded runtime.",L"Повреждён встроенный архив.");return 1;
 }
 for(int i=0;i<64;i++){if(!((t.hash[i]>='0'&&t.hash[i]<='9')||(t.hash[i]>='a'&&t.hash[i]<='f'))){fclose(self);return 1;}hash[i]=t.hash[i];}hash[64]=0;
 if(SHGetFolderPathW(NULL,CSIDL_LOCAL_APPDATA|CSIDL_FLAG_CREATE,NULL,SHGFP_TYPE_CURRENT,local)!=S_OK){fclose(self);return 1;}
 swprintf(parent,CAP,L"%ls\\DLPapp\\runtime",local);SHCreateDirectoryExW(NULL,parent,NULL);
 swprintf(cache,CAP,L"%ls\\%ls",parent,hash);swprintf(zip,CAP,L"%ls\\%ls.zip",parent,hash);
 swprintf(mutex_name,100,L"Local\\DLPapp-%ls",hash);HANDLE mutex=CreateMutexW(NULL,FALSE,mutex_name);
 if(!mutex){fclose(self);return 1;}DWORD lock=WaitForSingleObject(mutex,INFINITE);
 if(lock!=WAIT_OBJECT_0&&lock!=WAIT_ABANDONED){CloseHandle(mutex);fclose(self);return 1;}
 int success=1;
 if(!ready(cache,&t)) {
  HWND window=splash();
  if(!write_payload(self,&t,zip)){success=0;error(L"Unable to prepare the embedded runtime.",L"Не удалось подготовить встроенный архив.");}
  if(success){
   wchar_t system[CAP],powershell[CAP],qzip[CAP*2],qcache[CAP*2],command[32768];
   GetSystemDirectoryW(system,CAP);swprintf(powershell,CAP,L"%ls\\WindowsPowerShell\\v1.0\\powershell.exe",system);
   quote_ps(zip,qzip);quote_ps(cache,qcache);
   swprintf(command,32768,L"\"%ls\" -NoLogo -NoProfile -NonInteractive -Command \"$ErrorActionPreference='Stop'; if(Test-Path -LiteralPath '%ls'){Remove-Item -LiteralPath '%ls' -Recurse -Force}; Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('%ls','%ls')\"",powershell,qcache,qcache,qzip,qcache);
   STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
   if(!CreateProcessW(powershell,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,parent,&si,&pi))success=0;
   else {CloseHandle(pi.hThread);success=wait_process(pi.hProcess)==0;CloseHandle(pi.hProcess);}
   if(!success)error(L"Runtime extraction failed. Check free disk space and try again.",L"Не удалось распаковать компоненты. Проверьте свободное место и повторите запуск.");
  }
  if(success){wchar_t marker[CAP],temp[CAP];swprintf(marker,CAP,L"%ls\\.ready",cache);swprintf(temp,CAP,L"%ls\\.ready.tmp",cache);
   FILE *f=_wfopen(temp,L"wb");if(!f)success=0;else{success=fwrite(t.hash,1,64,f)==64;if(fclose(f))success=0;}
   if(success)success=MoveFileExW(temp,marker,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)&&ready(cache,&t);
   if(!success){DeleteFileW(marker);error(L"The extracted runtime is incomplete.",L"Распакованные компоненты неполны.");}
  }
  DeleteFileW(zip);DestroyWindow(window);
 }
 ReleaseMutex(mutex);CloseHandle(mutex);fclose(self);if(!success)return 1;
 SetEnvironmentVariableW(L"DLPAPP_HOME",home);SetEnvironmentVariableW(L"DLPAPP_RUNTIME",cache);
 SetEnvironmentVariableW(L"PYTHONHOME",NULL);SetEnvironmentVariableW(L"PYTHONPATH",NULL);
 wchar_t program[CAP],command[CAP*2];
 swprintf(program,CAP,t.mode==1?L"%ls\\pythonw.exe":L"%ls\\DLPappRuntime\\DLPappRuntime.exe",cache);
 swprintf(command,CAP*2,t.mode==1?L"\"%ls\" -E -s bootstrap.py":L"\"%ls\"",program);
 STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
 if(!CreateProcessW(program,command,NULL,NULL,FALSE,0,NULL,cache,&si,&pi)){error(L"Unable to start DLPapp.",L"Не удалось запустить DLPapp.");return 1;}
 CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return 0;
}
