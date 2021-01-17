#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class

import speech_recognition as sr
import pyaudio as pa
from pynput import keyboard

# Flags for defining behavior
PLAYBACK=False

def audioToText(audio:sr.AudioData)->str:
    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return ""
    except Exception as e:
        print("Unhandled exception occurred in audioToText: ", e)
        return ""

def playAudio(audio:sr.AudioData)->None:
    # instantiate PyAudio (1)
    p = pa.PyAudio()

    # open stream (2)
    chunk_size = 1024
    chunk_size_bytes = chunk_size * audio.sample_width
    stream = p.open(format=p.get_format_from_width(audio.sample_width),
                    channels=1,
                    rate=audio.sample_rate,
                    output=True)

    # play stream (3)
    for i in range(0, len(audio.frame_data)*audio.sample_width, chunk_size_bytes):
        chunk = audio.frame_data[i:i+chunk_size_bytes]
        stream.write(chunk)

    # stop stream (4)
    stream.stop_stream()
    stream.close()

    # close PyAudio (5)
    p.terminate()

# obtain audio from the microphone
r = sr.Recognizer()

class KeyComboListener(object):
    def __init__(self):
        self.kb = keyboard.Controller()
        self.key_combo = set((keyboard.Key.alt, keyboard.Key.cmd))
        self.pressed_keys = set()
        self.combo_engaged = False
        listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        listener.start()
    def on_press(self, key):
        if key in self.key_combo:
            self.pressed_keys.add(key)
            if (self.pressed_keys == self.key_combo) and not self.combo_engaged:
                self.combo_engaged = True
    def on_release(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            if self.combo_engaged:
                self.combo_engaged = False

keyboard_listener = KeyComboListener()

print("Listening...")
while True:
    with sr.Microphone() as mic:
        #print("Energy threshold before tuning: ", r.energy_threshold)
        #r.adjust_for_ambient_noise(mic, 1.0)  # listen to calibrate the energy threshold for ambient noise levels
        #print("Energy threshold after tuning: ", r.energy_threshold)
        r.dynamic_energy_threshold = False
        r.energy_threshold = 5000.0  # Fixed for now
        print("Listening...")
        try:
            audio = r.listen(mic, timeout=5.0)
        except sr.WaitTimeoutError:
            continue
    audio_length = len(audio.frame_data)/(audio.sample_rate*audio.sample_width)
    print("Received audio of length %0.1f"%audio_length)
    if PLAYBACK:
        print("Playing back...")
        playAudio(audio)
    text = audioToText(audio)
    if text:
        print("Sending to keyboard: ", text)
        kb.type(text)

if 0:
    # recognize speech using Google Cloud Speech
    GOOGLE_CLOUD_SPEECH_CREDENTIALS = r"""INSERT THE CONTENTS OF THE GOOGLE CLOUD SPEECH JSON CREDENTIALS FILE HERE"""
    try:
        print("Google Cloud Speech thinks you said " + r.recognize_google_cloud(audio, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS))
    except sr.UnknownValueError:
        print("Google Cloud Speech could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Cloud Speech service; {0}".format(e))
