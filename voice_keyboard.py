#!/usr/bin/env python3
"""
2021 January 17
James Whong
This is a simple voice keyboard, tested on Ubuntu 20.
First install the requirements listed in requirements.txt

When you run this script, it will listen to the keyboard. When PRESS_TO_TALK_COMBO is detected (default cmd+alt),
the script will start recording the microphone until the combo is released.
The recorded clip is then sent to the Google speech recognition service and converted to text.
The text is then typed into the keyboard, so it will appear in whatever text box has focus at the time.
"""

import speech_recognition as sr
import pyaudio as pa
from pynput import keyboard
from threading import Semaphore

# When set to true, plays back recorded audio before sending it up for speech recognition
PLAYBACK=False
# While pressed, this script records the default microphone
# When released, sends the audio clip to Google's speech recognition API
PRESS_TO_TALK_COMBO=(keyboard.Key.alt, keyboard.Key.cmd)
# What conversion backend to use?  Accepts "GOOGLE" and "SPHINX"
BACKEND = "GOOGLE"

# Default audio parameters
CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
SAMPLE_WIDTH = 2
N_CHANNELS = 1

#Instantiate PyAudio once and share it
global_p = pa.PyAudio()

def audioToText(recognizer:sr.Recognizer, audio:sr.AudioData)->str:
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        if BACKEND == "GOOGLE":
            return recognizer.recognize_google(audio)
        elif BACKEND == "SPHINX":
            return recognizer.recognize_sphinx(audio)
        else:
            raise Exception("Invalid BACKEND value: %s"%BACKEND)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print("Could not request results; {0}".format(e))
    except Exception as e:
        print("Unhandled exception occurred in audioToText: ", e)
    return ""

def playAudio(audio:sr.AudioData)->None:
    global global_p

    chunk_size_bytes = CHUNK_SIZE * audio.sample_width
    stream = global_p.open(format=global_p.get_format_from_width(audio.sample_width),
                    channels=1,
                    rate=audio.sample_rate,
                    output=True)
    for i in range(0, len(audio.frame_data)*audio.sample_width, chunk_size_bytes):
        chunk = audio.frame_data[i:i+chunk_size_bytes]
        stream.write(chunk)
    stream.stop_stream()
    stream.close()

class MyKeyController(object):
    """Utility class to check for a specific key combination.
    Signals a semaphore when key combination is pressed.
    Combo status can be checked with isComboPressed"""
    def __init__(self, listen_for_combo=(keyboard.Key.alt, keyboard.Key.cmd), sem_to_signal=None):
        self.kb = keyboard.Controller()
        self.key_combo = set(listen_for_combo)
        self.pressed_keys = set()
        self.combo_pressed = False
        self.sem_to_signal = sem_to_signal
        listener = keyboard.Listener(
            on_press=self.__onPress,
            on_release=self.__onRelease)
        listener.start()
    def __onPress(self, key):
        if key in self.key_combo:
            self.pressed_keys.add(key)
            if (self.pressed_keys == self.key_combo) and not self.combo_pressed:
                self.combo_pressed = True
                if self.sem_to_signal: self.sem_to_signal.release()
    def __onRelease(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            if self.combo_pressed:
                self.combo_pressed = False
    def isComboPressed(self): return self.combo_pressed

def recordWhile(cb_returns_true)->sr.AudioData:
    """Records audio and polls the provided callback.
    When the callback returns false, recording is terminated and the recorded clip returned as AudioData.
    Expect the callback to be polled at SAMPLE_RATE/CHUNK_SIZE = 44100Hz/1024 = 43.07Hz"""
    global global_p
    stream = global_p.open(format=global_p.get_format_from_width(SAMPLE_WIDTH),
                    channels=N_CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    output=False)
    frames = []
    while cb_returns_true():
        data = stream.read(CHUNK_SIZE)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    return sr.AudioData(b''.join(frames), SAMPLE_RATE, SAMPLE_WIDTH)

class MyTextFormatter(object):
    """The speech to text conversion doesn't pad its returned values with spaces, so if you invoke this multiple times
    in a row your textwillstackup. This class just spaces out the text between invocations, and also capitalizes the first
    word if the last thing we remember sending was the end of a sentence."""
    SENTENCE_ENDINGS = ('.', '?', '!')
    def __init__(self):
        self.capitalization_due = True
    def process(self, input:str)->str:
        if not input: return input
        working = list(input)
        if self.capitalization_due:
            working[0] = working[0].capitalize()
            self.capitalization_due = False
        if working[-1] in MyTextFormatter.SENTENCE_ENDINGS:
            self.capitalization_due = True
        working.append(' ')
        return ''.join(working)

if __name__ == "__main__":
    print("Voice keyboard starting...")

    sem = Semaphore(0)
    recognizer = sr.Recognizer()
    key_controller = MyKeyController(listen_for_combo=PRESS_TO_TALK_COMBO, sem_to_signal=sem)
    formatter = MyTextFormatter()

    while True:
        print("Waiting for key combo...")
        sem.acquire()
        print("Recording...")
        audio = recordWhile(key_controller.isComboPressed)
        audio_length = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
        print("Received audio of length %0.1fs" % audio_length)
        if PLAYBACK:
            print("Playing back...")
            playAudio(audio)
        text = audioToText(recognizer, audio)
        if text:
            text = formatter.process(text)
            print("Sending to keyboard: ", text)
            key_controller.kb.type(text)
        print("Going back to sleep.")
