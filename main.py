#!/usr/bin/env python3

import speech_recognition as sr
import pyaudio as pa
from pynput import keyboard
from time import sleep
from threading import Semaphore

# Some magic numbers
CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
SAMPLE_WIDTH = 2
N_CHANNELS = 1

# When true, plays back recorded audio before sending it up for speech recognition
PLAYBACK=False

def audioToText(audio:sr.AudioData)->str:
    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        return recognizer.recognize_google(audio)
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
    p = pa.PyAudio()

    chunk_size_bytes = CHUNK_SIZE * audio.sample_width
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

class MyKeyController(object):
    def __init__(self, listen_for_combo=(keyboard.Key.alt, keyboard.Key.cmd), sem_to_signal=None):
        self.kb = keyboard.Controller()
        self.key_combo = set(listen_for_combo)
        self.pressed_keys = set()
        self.combo_pressed = False
        self.sem_to_signal = sem_to_signal
        listener = keyboard.Listener(
            on_press=self.onPress,
            on_release=self.onRelease)
        listener.start()
    def onPress(self, key):
        if key in self.key_combo:
            self.pressed_keys.add(key)
            if (self.pressed_keys == self.key_combo) and not self.combo_pressed:
                self.combo_pressed = True
                if self.sem_to_signal: self.sem_to_signal.release()
    def onRelease(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            if self.combo_pressed:
                self.combo_pressed = False
    def isComboPressed(self): return self.combo_pressed

def recordWhile(cb_returns_true)->sr.AudioData:
    p = pa.PyAudio()
    stream = p.open(format=p.get_format_from_width(SAMPLE_WIDTH),
                    channels=N_CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    output=False)
    # read data
    frames = []
    while cb_returns_true():
        data = stream.read(CHUNK_SIZE)
        frames.append(data)

    # stop stream (4)
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Stitch together into AudioData
    return sr.AudioData(b''.join(frames), SAMPLE_RATE, SAMPLE_WIDTH)

class MyTextFormatter(object):
    SENTENCE_ENDINGS = ('.','?','!')
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
    # obtain audio from the microphone
    sem = Semaphore(0)
    recognizer = sr.Recognizer()
    key_controller = MyKeyController(sem_to_signal=sem)
    formatter = MyTextFormatter()

    while True:
        sem.acquire()
        print("Recording...")
        audio = recordWhile(key_controller.isComboPressed)
        audio_length = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
        print("Received audio of length %0.1fs" % audio_length)
        if PLAYBACK:
            print("Playing back...")
            playAudio(audio)
        text = audioToText(audio)
        if text:
            text = formatter.process(text)
            print("Sending to keyboard: ", text)
            key_controller.kb.type(text)
        print("Going back to sleep.")
