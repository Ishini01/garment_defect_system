import os
import platform
import subprocess

class AlarmManager:
    def __init__(self):
        self.alarm_sound_path = 'static/sounds/alarm.wav'
    
    def play_alarm(self):
        try:
            system = platform.system()
            if system == 'Windows':
                try:
                    import winsound
                    winsound.Beep(880, 500)
                    winsound.Beep(880, 500)
                except:
                    print('\a')
            else:
                print('\a')
        except:
            print('\a')