"""Restart regressions; native PowerShell acceptance tests also run on Windows."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from startup_ack import StartupAcknowledgement
from updates import restart_environment, install_script
from version import VERSION


class RestartTests(unittest.TestCase):
    def test_restart_environment_drops_runtime_but_keeps_user_settings(self):
        original = {'_PYI_ARCHIVE_FILE':'old.exe', '_PYI_APPLICATION_HOME_DIR':'old',
                    '_MEIPASS2':'old', 'DLPAPP_EXE':'old.exe', 'DLPAPP_RUNTIME':'old',
                    'DLPAPP_UPDATE_ACK':'old.ready.json','DLPAPP_UPDATE_TOKEN':'old',
                    'PYTHONPATH':'old','TCL_LIBRARY':'old','TK_LIBRARY':'old',
                    'PATH':'system paths','LOCALAPPDATA':'profile','LANG':'ru_RU'}
        result=restart_environment(original)
        self.assertEqual(result, {'PATH':'system paths','LOCALAPPDATA':'profile','LANG':'ru_RU',
                                  'PYINSTALLER_RESET_ENVIRONMENT':'1'})
        self.assertEqual(original['_PYI_ARCHIVE_FILE'],'old.exe')

    def test_ack_retries_failed_write_without_losing_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings=Path(tmp)/'settings.json'
            ack=Path(tmp)/'updates/test.ready.json'
            env={'DLPAPP_UPDATE_ACK':str(ack),'DLPAPP_UPDATE_TOKEN':'a'*32}
            retries=[]
            from settings import atomic_json
            def writer(path,data):
                if not retries: raise PermissionError('file temporarily busy')
                atomic_json(path,data)
            confirmation=StartupAcknowledgement(settings,VERSION,lambda delay,fn:retries.append((delay,fn)),
                                                lambda:Path(tmp)/'DLPapp.exe',env,writer)
            self.assertFalse(confirmation.attempt())
            self.assertIn('DLPAPP_UPDATE_ACK',env)
            self.assertEqual(retries[0][0],500)
            self.assertTrue(retries[0][1]())
            data=json.loads(ack.read_text())
            self.assertEqual(data['token'],'a'*32)
            self.assertEqual(data['version'],VERSION)
            self.assertEqual(data['pid'],os.getpid())
            self.assertNotIn('DLPAPP_UPDATE_ACK',env)
            self.assertIn('temporarily busy',(Path(tmp)/'update-startup.log').read_text())

    def test_old_installer_without_token_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            ack=Path(tmp)/'updates/DLPapp.ready.json'
            env={'DLPAPP_UPDATE_ACK':str(ack)}
            self.assertTrue(StartupAcknowledgement(Path(tmp)/'settings.json',VERSION,None,lambda:None,env).attempt())
            self.assertEqual(json.loads(ack.read_text())['app_id'],'DLPapp')

    def test_ack_outside_update_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ack=Path(tmp)/'not-allowed.ready.json'
            self.assertFalse(StartupAcknowledgement(Path(tmp)/'settings.json',VERSION,None,lambda:None,
                             {'DLPAPP_UPDATE_ACK':str(ack)}).attempt())
            self.assertFalse(ack.exists())

    def test_persistent_ack_failure_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            retries=[]
            def writer(*_): raise PermissionError('busy')
            helper=StartupAcknowledgement(Path(tmp)/'settings.json',VERSION,lambda d,f:retries.append(f),
                  lambda:None,{'DLPAPP_UPDATE_ACK':str(Path(tmp)/'updates/a.ready.json')},writer)
            helper.attempt()
            while retries: retries.pop(0)()
            self.assertEqual(helper.attempts,20)

    def test_install_requests_unique_ack_and_does_not_delete_new_exe(self):
        with tempfile.TemporaryDirectory() as tmp,patch('updates.settings_path',return_value=Path(tmp)/'settings.json'):
            one=install_script(Path(tmp)/'source.exe',Path(tmp)/'target.exe',123,'a'*64)
            two=install_script(Path(tmp)/'source.exe',Path(tmp)/'target.exe',123,'a'*64)
            self.assertNotEqual(one,two)
            self.assertNotIn('Remove-Item -LiteralPath $dst',one)
            self.assertIn('Copy-Item -LiteralPath $src',one)
            self.assertIn("$env:PYINSTALLER_RESET_ENVIRONMENT = '1'",one)


@unittest.skipUnless(os.name=='nt','Native Windows PowerShell integration test')
class WindowsInstallerTests(unittest.TestCase):
    def powershell(self, code, env=None):
        encoded=base64.b64encode(code.encode('utf-16le')).decode()
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',encoded],
                              env=env,capture_output=True,text=True,timeout=60)

    def test_real_ps_install_success_checksum_failure_and_no_ack_rollback(self):
        # Compile a controlled fixture in a private folder. Never touch an installed app.
        with tempfile.TemporaryDirectory(prefix="DLPapp update user's ") as tmp:
            root=Path(tmp)
            source=root/'new.exe'
            code=r'''using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
public class Fixture {
 public static void Main() {
  if (Environment.GetEnvironmentVariable("DLPAPP_TEST_SILENT") == "1") return;
  string ack=Environment.GetEnvironmentVariable("DLPAPP_UPDATE_ACK");
  string token=Environment.GetEnvironmentVariable("DLPAPP_UPDATE_TOKEN");
  string exe=Process.GetCurrentProcess().MainModule.FileName.Replace("\\", "\\\\");
  int pid=Process.GetCurrentProcess().Id;
  File.WriteAllText(Environment.GetEnvironmentVariable("DLPAPP_TEST_PIDFILE"),pid.ToString());
  File.WriteAllText(ack,"{\"app_id\":\"DLPapp\",\"version\":\"__VERSION__\",\"token\":\""+token+"\",\"exe\":\""+exe+"\",\"pid\":"+pid+"}");
  Thread.Sleep(10000);
 }
}'''.replace('__VERSION__',VERSION)
            from updates import ps_literal
            compiled=self.powershell('Add-Type -TypeDefinition '+ps_literal(code)+' -OutputAssembly '+ps_literal(source)+' -OutputType WindowsApplication')
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            for scenario in ('success','bad-hash','no-ack'):
                with self.subTest(scenario=scenario):
                    folder=root/scenario
                    folder.mkdir()
                    target=folder/'DLPapp.exe'
                    target.write_bytes(b'original EXE fixture')
                    settings=folder/'settings.json'
                    settings.write_text('{"nickname":"keep me"}')
                    pidfile=folder/'fixture.pid'
                    env=restart_environment()
                    env['DLPAPP_TEST_PIDFILE']=str(pidfile)
                    if scenario=='no-ack':env['DLPAPP_TEST_SILENT']='1'
                    with patch('updates.settings_path',return_value=settings):
                        script=install_script(source,target,2147483000,digest if scenario!='bad-hash' else '0'*64,
                                              VERSION,timeout_seconds=2,show_errors=False)
                    (folder/'updates').mkdir()
                    path=folder/'install.ps1'
                    path.write_text(script,encoding='utf-8-sig')
                    try:
                        result=self.powershell('& '+ps_literal(path),env)
                        self.assertEqual(result.returncode,0,result.stderr)
                        self.assertEqual(settings.read_text(),'{"nickname":"keep me"}')
                        self.assertTrue(source.exists())
                        if scenario=='success':
                            self.assertEqual(target.read_bytes(),source.read_bytes())
                            self.assertFalse((folder/'update-error.log').exists())
                            self.assertFalse(list(folder.glob('*.dlpapp-backup-*')))
                        else:
                            self.assertEqual(target.read_bytes(),b'original EXE fixture')
                            self.assertTrue((folder/'update-error.log').exists())
                            if scenario=='no-ack':self.assertTrue(list(folder.glob('*.dlpapp-failed-*')))
                    finally:
                        if pidfile.exists():
                            # Only the process created by this private fixture.
                            fixture_pid=int(pidfile.read_text())
                            self.powershell('Stop-Process -Id '+str(fixture_pid)+' -Force -ErrorAction SilentlyContinue')


if __name__=='__main__':unittest.main()
