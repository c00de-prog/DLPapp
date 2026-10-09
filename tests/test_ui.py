"""Opt-in GUI smoke checks: DLPAPP_GUI_TESTS=1 python -m unittest discover -s tests."""
import os
import tempfile
import unittest
from pathlib import Path
from app import DLPapp
from settings import Settings
from clipboard import paste


@unittest.skipUnless(os.environ.get('DLPAPP_GUI_TESTS')=='1','Opt-in display test')
class UITests(unittest.TestCase):
    def test_resizing_settings_language_paste_and_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            app=DLPapp(Settings(Path(folder)/'settings.json'),schedule_updates=False)
            try:
                app.geometry('1600x1000');app.update()
                self.assertLessEqual(float(app.content_canvas.itemcget(app.content_window,'width')),860)
                app.clipboard_clear();app.clipboard_append('https://example.com/video');paste(app.entry)
                self.assertEqual(app.url.get(),'https://example.com/video')
                app.events.put(('ready',(app.url.get(),{'title':'Test video','formats':[{'height':720,'vcodec':'avc1'}]},[720])))
                app._poll();app.update()
                self.assertEqual(str(app.download['state']),'normal')
                app._settings('general');app.update()
                app.nickname_choice.set('Tester');app.parent_choice.set(folder);app.language_selector.current(2)
                app._save_settings();app.update()
                self.assertEqual(app.language,'ru')
                self.assertEqual(app.settings.get('nickname'),'Tester')
                self.assertEqual(app.folder,Path(folder)/'DDownloads')
                app._settings('downloads');app.update()
                app.settings.record(app.folder/'test.mp4','Test',app.folder,app.url.get(),'MP4')
                app._refresh_history();app.update()
                self.assertEqual(len(app.history_tree.get_children()),1)
                app._settings('general');app.language_selector.current(1);app._save_settings();app.update()
                self.assertEqual(app.language,'en')
                app._close_settings()
                app.format.set('MP3');app._options_changed();app.update()
                self.assertEqual(str(app.combo['state']),'disabled')
                self.assertEqual(str(app.download['state']),'normal')
            finally:
                app._quit()
