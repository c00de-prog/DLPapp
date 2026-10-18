import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import patch

from notifications import DeliveryWatch, Tray
from app import DLPapp


class DeliveryTests(unittest.TestCase):
    def test_accepted_but_not_shown_triggers_fallback_once(self):
        events=queue.Queue()
        now=[0]
        delivery=DeliveryWatch(events,clock=lambda:now[0],timeout=5)
        delivery.begin('download-1')
        self.assertTrue(events.empty())
        now[0]=6
        delivery.expire()
        kind,data=events.get_nowait()
        self.assertEqual(kind,'notification_failed')
        self.assertEqual(data[0],'download-1')
        delivery.expire()
        self.assertTrue(events.empty())

    def test_confirmed_banner_does_not_trigger_fallback(self):
        events=queue.Queue()
        delivery=DeliveryWatch(events,clock=lambda:100)
        delivery.begin('done')
        delivery.shown()
        self.assertEqual(events.get_nowait(),('notification_shown','done'))
        delivery.deadline=0
        delivery.expire()
        self.assertTrue(events.empty())

    def test_replacement_and_rejection(self):
        events=queue.Queue()
        delivery=DeliveryWatch(events)
        delivery.begin('first')
        delivery.begin('second')
        self.assertEqual(events.get_nowait()[1][0],'first')
        delivery.failed('Windows rejected it')
        self.assertEqual(events.get_nowait(),('notification_failed',('second','Windows rejected it')))

    def test_native_initialization_failure_is_logged_and_unblocks_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=queue.Queue()
            tray=Tray(events,'missing.ico',Path(tmp)/'notifications.log')
            with patch.object(tray,'_run_windows',side_effect=RuntimeError('native startup failed')):
                tray._run()
            self.assertTrue(tray.started.is_set())
            self.assertFalse(tray.available)
            self.assertEqual(events.get_nowait(),('tray_failed',None))
            self.assertIn('native startup failed',(Path(tmp)/'notifications.log').read_text())

    def test_notify_returns_delivery_queue_state_and_closed_tray_refuses(self):
        tray=Tray(queue.Queue(),'icon.ico')
        with patch.object(tray,'start',return_value=True):
            self.assertTrue(tray.notify('Done','video.mp4',tag='done'))
        self.assertEqual(tray.commands.get_nowait(),('Done','video.mp4','done'))
        tray.close()
        self.assertFalse(tray.start())


class FallbackTests(unittest.TestCase):
    def fake_app(self, hidden=True):
        callbacks=[]
        logs=[]
        obj=SimpleNamespace(hidden=hidden,_notification_pending={},
                            tray=SimpleNamespace(notify=lambda *args,**kwargs:False,log=logs.append),
                            t=lambda key:'Native notification not confirmed',
                            after=lambda delay,callback:callbacks.append((delay,callback)))
        obj._restore=lambda:setattr(obj,'hidden',False)
        obj._notification_failed=MethodType(DLPapp._notification_failed,obj)
        return obj,callbacks,logs

    def test_no_tray_restores_hidden_window_and_notifies_once(self):
        obj,callbacks,logs=self.fake_app()
        with patch('app.messagebox.showinfo') as popup:
            tag=DLPapp._send_notification(obj,'Done','video.mp4')
            self.assertEqual(callbacks[0][0],0)
            callbacks[0][1]()
            self.assertFalse(obj.hidden)
            popup.assert_called_once()
            self.assertIn('video.mp4',popup.call_args.args[1])
            obj._notification_failed(tag,'late duplicate')
            popup.assert_called_once()
        self.assertTrue(logs)

    def test_visible_completion_does_not_open_an_unrequested_dialog(self):
        obj,callbacks,_=self.fake_app(hidden=False)
        with patch('app.messagebox.showinfo') as popup:
            DLPapp._send_notification(obj,'Done','video.mp4')
            callbacks[0][1]()
            popup.assert_not_called()

    def test_manual_test_always_has_visible_fallback(self):
        obj,callbacks,_=self.fake_app(hidden=False)
        with patch('app.messagebox.showinfo') as popup:
            DLPapp._send_notification(obj,'Test','Test message',force_fallback=True)
            callbacks[0][1]()
            popup.assert_called_once()

    def test_dead_native_worker_has_gui_watchdog(self):
        obj,callbacks,_=self.fake_app()
        obj.tray.notify=lambda *args,**kwargs:True
        with patch('app.messagebox.showinfo') as popup:
            DLPapp._send_notification(obj,'Done','video.mp4')
            self.assertEqual(callbacks[0][0],10000)
            callbacks[0][1]()
            popup.assert_called_once()


if __name__=='__main__':unittest.main()
