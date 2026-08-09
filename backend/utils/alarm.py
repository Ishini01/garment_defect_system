import os
import platform
import subprocess
import sys
import time

class AlarmManager:
    def __init__(self):
        self.alarm_sound_path = 'static/sounds/alarm.wav'
        self._create_fallback_sound()
    
    def _create_fallback_sound(self):
        """Create a simple beep sound file if it doesn't exist"""
        try:
            # Create sounds directory if it doesn't exist
            os.makedirs('static/sounds', exist_ok=True)
            
            # Check if file already exists
            if os.path.exists('static/sounds/alarm.wav'):
                return
            
            # Try to create a simple beep using scipy
            try:
                import numpy as np
                from scipy.io import wavfile
                
                sample_rate = 44100
                duration = 0.5
                frequency = 880  # A5 note
                
                t = np.linspace(0, duration, int(sample_rate * duration))
                # Create a square wave for a more alarming sound
                wave = 0.5 * np.sign(np.sin(2 * np.pi * frequency * t))
                
                # Add some harmonics for more impact
                wave += 0.25 * np.sign(np.sin(2 * np.pi * (frequency * 2) * t))
                wave += 0.125 * np.sign(np.sin(2 * np.pi * (frequency * 3) * t))
                
                # Normalize
                wave = wave / np.max(np.abs(wave))
                wave = (wave * 32767).astype(np.int16)
                
                wavfile.write('static/sounds/alarm.wav', sample_rate, wave)
                print("✅ Alarm sound file created with scipy")
                return
            except ImportError:
                print("⚠️ scipy not available, trying alternative...")
            except Exception as e:
                print(f"⚠️ scipy creation failed: {e}")
            
            # Try alternative: create using wave module
            try:
                self._create_simple_wav()
                print("✅ Alarm sound file created with wave module")
                return
            except Exception as e:
                print(f"⚠️ Wave creation failed: {e}")
            
        except Exception as e:
            print(f"⚠️ Could not create alarm sound: {e}")
    
    def _create_simple_wav(self):
        """Create a simple WAV file without scipy"""
        try:
            import wave
            import struct
            import math
            
            sample_rate = 44100
            duration = 0.3
            frequency = 880
            
            # Generate square wave
            samples = []
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                value = math.sin(2 * math.pi * frequency * t)
                if value > 0.5:
                    samples.append(32767)
                elif value < -0.5:
                    samples.append(-32768)
                else:
                    samples.append(0)
            
            # Write WAV file
            with wave.open('static/sounds/alarm.wav', 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
            
        except Exception as e:
            print(f"⚠️ Simple WAV creation failed: {e}")
            raise
    
    def play_alarm(self):
        """Play alarm sound when defect is detected"""
        print("🔊 ALARM TRIGGERED! Playing alarm...")
        
        system = platform.system()
        
        # ============================================
        # WINDOWS - Multiple methods
        # ============================================
        if system == 'Windows':
            # Method 1: Winsound (built-in, most reliable)
            try:
                import winsound
                print("🔊 Playing alarm via winsound...")
                winsound.Beep(880, 400)
                winsound.Beep(880, 400)
                winsound.Beep(880, 400)
                print("✅ Alarm played via winsound")
                return
            except Exception as e:
                print(f"⚠️ Winsound error: {e}")
            
            # Method 2: Playsound library
            try:
                from playsound import playsound
                if os.path.exists('static/sounds/alarm.wav'):
                    playsound('static/sounds/alarm.wav', block=False)
                    print("✅ Alarm played via playsound")
                    return
            except ImportError:
                print("⚠️ playsound not installed")
            except Exception as e:
                print(f"⚠️ playsound error: {e}")
            
            # Method 3: Windows API MessageBeep
            try:
                import ctypes
                ctypes.windll.user32.MessageBeep(0xFFFFFFFF)
                print("✅ Alarm played via Windows MessageBeep")
                return
            except Exception as e:
                print(f"⚠️ MessageBeep error: {e}")
            
            # Method 4: Try using the sound file with winsound
            try:
                import winsound
                if os.path.exists('static/sounds/alarm.wav'):
                    winsound.PlaySound('static/sounds/alarm.wav', winsound.SND_FILENAME)
                    print("✅ Alarm played via winsound file")
                    return
            except:
                pass
            
            # Method 5: System beep via print
            print('\a')
            print("✅ Alarm played via terminal bell")
            return
        
        # ============================================
        # MAC OS
        # ============================================
        elif system == 'Darwin':
            # Method 1: afplay
            try:
                if os.path.exists('static/sounds/alarm.wav'):
                    subprocess.run(['afplay', 'static/sounds/alarm.wav'], 
                                 capture_output=True, timeout=2)
                    print("✅ Alarm played via afplay")
                    return
            except Exception as e:
                print(f"⚠️ afplay error: {e}")
            
            # Method 2: AppleScript beep
            try:
                subprocess.run(['osascript', '-e', 'beep 3'], capture_output=True)
                print("✅ Alarm played via AppleScript")
                return
            except:
                pass
            
            # Method 3: Terminal bell
            print('\a')
            print("✅ Alarm played via terminal bell")
            return
        
        # ============================================
        # LINUX
        # ============================================
        else:
            # Method 1: aplay
            try:
                if os.path.exists('static/sounds/alarm.wav'):
                    subprocess.run(['aplay', 'static/sounds/alarm.wav'], 
                                 capture_output=True, timeout=2)
                    print("✅ Alarm played via aplay")
                    return
            except:
                pass
            
            # Method 2: paplay (PulseAudio)
            try:
                if os.path.exists('static/sounds/alarm.wav'):
                    subprocess.run(['paplay', 'static/sounds/alarm.wav'], 
                                 capture_output=True, timeout=2)
                    print("✅ Alarm played via paplay")
                    return
            except:
                pass
            
            # Method 3: speaker-test
            try:
                subprocess.run(['speaker-test', '-t', 'sine', '-f', '880', '-l', '1'], 
                             capture_output=True, timeout=1)
                print("✅ Alarm played via speaker-test")
                return
            except:
                pass
            
            # Method 4: Terminal bell
            print('\a')
            print('\a')
            print('\a')
            print("✅ Alarm played via terminal bell")
            return
    
    def play_defect_alert(self, defect_type):
        """Play different alert sounds based on defect type"""
        print(f"🔊 Playing {defect_type} alert...")
        
        try:
            system = platform.system()
            
            # Different patterns for different defects
            if system == 'Windows':
                import winsound
                if defect_type == 'missing_button' or defect_type == 'missing':
                    # Rapid beeps for missing button
                    winsound.Beep(1000, 200)
                    time.sleep(0.1)
                    winsound.Beep(1000, 200)
                    time.sleep(0.1)
                    winsound.Beep(1000, 200)
                    print("✅ Missing button alert played")
                elif defect_type == 'misalignment' or defect_type == 'alignment':
                    # Slower beeps for misalignment
                    winsound.Beep(600, 400)
                    time.sleep(0.2)
                    winsound.Beep(600, 400)
                    print("✅ Misalignment alert played")
                else:
                    # Default alarm
                    self.play_alarm()
            else:
                # For non-Windows, use terminal bell with patterns
                if defect_type == 'missing_button':
                    print('\a')
                    time.sleep(0.2)
                    print('\a')
                    time.sleep(0.2)
                    print('\a')
                elif defect_type == 'misalignment':
                    print('\a')
                    time.sleep(0.4)
                    print('\a')
                else:
                    self.play_alarm()
        except Exception as e:
            print(f"⚠️ Defect alert error: {e}")
            self.play_alarm()
    
    def test_alarm(self):
        """Test the alarm system"""
        print("=" * 60)
        print("🔊 TESTING ALARM SYSTEM")
        print("=" * 60)
        
        print("\n📋 Testing default alarm...")
        self.play_alarm()
        
        print("\n📋 Testing missing button alert...")
        self.play_defect_alert('missing_button')
        
        print("\n📋 Testing misalignment alert...")
        self.play_defect_alert('misalignment')
        
        print("\n" + "=" * 60)
        print("✅ Alarm test complete!")
        print("=" * 60)