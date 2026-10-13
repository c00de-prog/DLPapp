import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dlpapp_cli import cli, config, engine


class Tests(unittest.TestCase):
    def test_config_namespace_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'settings.json'
            p.write_text('{"app_id":"DLPapp","nickname":"GUI"}')
            self.assertEqual(config.load(p)['nickname'],'')
            p.write_text('broken')
            self.assertEqual(config.load(p)['network'],'ipv4')
            config.save({**config.DEFAULTS,'nickname':'Шохи'},p)
            self.assertEqual(config.load(p)['nickname'],'Шохи')

    def test_config_resolves_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp,patch('dlpapp_cli.config.config_path') as path,contextlib.redirect_stdout(io.StringIO()):
            path.return_value=Path(tmp)/'settings.json'
            self.assertEqual(cli.main(['config','--output','relative folder','--language','ru']),0)
            self.assertEqual(config.load()['output'],str(Path('relative folder').resolve()))

    def test_platform_paths_and_language(self):
        with patch.object(sys,'platform','darwin'):
            self.assertIn('Library/Application Support/DLPappCLI',str(config.config_path()))
        with patch.object(sys,'platform','linux'),patch.dict(os.environ,{'XDG_CONFIG_HOME':'/test/config','LC_ALL':'ru_RU.UTF-8'}):
            self.assertEqual(config.config_path(),Path('/test/config/dlpapp-cli/settings.json'))
            self.assertEqual(config.language(config.DEFAULTS),'ru')

    def test_url_validation(self):
        for url in ('file:///tmp/a','--help','https://user:pass@example.com/x'):
            with self.assertRaises(ValueError): engine.validate_url(url)
        self.assertEqual(engine.validate_url(' https://example.com/x?a=1&b=2 '),'https://example.com/x?a=1&b=2')

    def test_quality_compatibility(self):
        s=engine.selector('720p','mp4')
        self.assertIn('[height<=720]',s)
        self.assertIn('ba[ext=m4a]',s)
        self.assertNotIn('height',engine.selector('best','mkv'))
        for q in ('0','-1','bad','20000'):
            with self.assertRaises(ValueError): engine.quality(q)

    def test_network_and_argv(self):
        with patch('dlpapp_cli.engine.downloader',return_value=['python','-m','yt_dlp']),patch('dlpapp_cli.engine.tool',return_value=None):
            c=engine.command(config.DEFAULTS,'https://example.com/x?a=1&b=2',Path('/folder with spaces'),'download','mp4','720')
            self.assertIn('--force-ipv4',c)
            self.assertEqual(c[-2:],['--','https://example.com/x?a=1&b=2'])
            self.assertEqual(c[c.index('-P')+1],'/folder with spaces')
            self.assertNotIn('--force-ipv4',engine.base({**config.DEFAULTS,'network':'auto'}))

    def test_tools_and_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/('ffmpeg.exe' if os.name=='nt' else 'ffmpeg')
            p.touch()
            self.assertEqual(engine.tool('ffmpeg',{**config.DEFAULTS,'tools_dir':tmp}),str(p.resolve()))
        with patch('dlpapp_cli.engine.base',return_value=['yt-dlp']):
            c=engine.command(config.DEFAULTS,'https://example.com/x',Path('.'),'audio','flac')
            self.assertIn('--no-overwrites',c)
            self.assertEqual(c[c.index('--audio-format')+1],'flac')

    def test_metadata_failure_and_playlist(self):
        with patch('dlpapp_cli.engine.base',return_value=[]),patch('dlpapp_cli.engine.run') as run:
            run.return_value=subprocess.CompletedProcess([],1,stdout='not json')
            with self.assertRaises(RuntimeError): engine.info(config.DEFAULTS,'https://example.com/x')
            run.return_value=subprocess.CompletedProcess([],0,stdout='{"title":"Video","formats":[]}')
            self.assertEqual(engine.info(config.DEFAULTS,'https://example.com/x')['title'],'Video')
            run.return_value.stdout='{"entries":[]}'
            with self.assertRaises(ValueError): engine.info(config.DEFAULTS,'https://example.com/x')

    def test_subprocess_no_shell(self):
        with patch('subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            engine.run(['tool','argument with spaces'])
            args,kwargs=run.call_args
            self.assertEqual(args[0],['tool','argument with spaces'])
            self.assertNotIn('shell',kwargs)
            self.assertEqual(kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'],'1')

    def test_no_tty_and_menu_exit(self):
        with patch('sys.stdin.isatty',return_value=False),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main([]),0)
            self.assertIn('download',out.getvalue())
        with patch('builtins.input',side_effect=['bad','0']),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.menu(),0)

    def test_missing_dependencies_and_download_exit(self):
        with patch('dlpapp_cli.engine.require_media_tools',side_effect=RuntimeError('missing FFmpeg')),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['download','https://example.com/x']),1)
        with patch('dlpapp_cli.engine.require_media_tools'),patch('dlpapp_cli.engine.command',return_value=['tool']),patch('dlpapp_cli.engine.run',return_value=subprocess.CompletedProcess([],5)),tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['download','https://example.com/x','-o',tmp]),1)

    def test_help(self):
        self.assertIn('постоянной сессии нет',cli.help_text({**config.DEFAULTS,'language':'ru'}))
        self.assertIn('not available',cli.help_text({**config.DEFAULTS,'language':'en'}))

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg not installed')
    def test_real_offline_audio_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'sample.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.1',str(source)],check=True)
            destination=Path(tmp)/'out'
            args=cli.parser().parse_args(['convert',str(source),'--format','flac','-o',str(destination)])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.convert(args,config.DEFAULTS),0)
                self.assertGreater((destination/'sample.flac').stat().st_size,0)
                with self.assertRaises(ValueError): cli.convert(args,config.DEFAULTS)


if __name__=='__main__': unittest.main()
