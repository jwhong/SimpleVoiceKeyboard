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
import os
from google.cloud import speech

# While pressed, this script records the default microphone
# When released, sends the audio clip to Google's speech recognition API
PRESS_TO_TALK_COMBO=(keyboard.Key.ctrl, keyboard.Key.cmd)

# Default audio parameters
SAMPLE_RATE = 44100 # Can be set to 16000 for lower bandwidth, but empirically I see better results with 44100
CHUNK_SIZE = 1024 * 10
SAMPLE_WIDTH = 2
N_CHANNELS = 1

#Instantiate PyAudio once and share it
global_p = pa.PyAudio()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "PATH_TO_YOUR_KEYFILE.json"

def newWordGenerator(responses):
    transcript_cache = ''
    def getNewPart(transcript, old_part)->str:
        i = 0
        if transcript.startswith(old_part):
            i = 0
        elif j := transcript.rfind(old_part) != -1:
            i = j
        new_part = transcript[len(old_part) + i:]
        if new_part:
            return transcript, new_part
        else:
            return old_part, ''

    for response in responses:
        if not response.results:
            continue
        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        new_part = ''
        if result.stability > 0.8:
            transcript_cache, new_part = getNewPart(transcript, transcript_cache)
        elif result.is_final:
            _, new_part = getNewPart(transcript, transcript_cache)
            transcript_cache = ''
        if new_part:
            yield new_part

def runVoiceKeyboard(run_while_returns_true):
    client = speech.SpeechClient()
    streaming_config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="en-US",
            profanity_filter=False,
            enable_spoken_punctuation=True,
            enable_automatic_punctuation=False,
            max_alternatives=0,
        ),
        single_utterance=False,
        interim_results=True,
    )

    stream = global_p.open(format=global_p.get_format_from_width(SAMPLE_WIDTH),
                           channels=N_CHANNELS,
                           rate=SAMPLE_RATE,
                           input=True,
                           output=False)
    def audioRequestGenerator():
        while run_while_returns_true():
            yield speech.StreamingRecognizeRequest(audio_content=stream.read(CHUNK_SIZE))
    print("Recognition running...")
    responses = client.streaming_recognize(streaming_config, requests=audioRequestGenerator())
    for x in newWordGenerator(responses):
        print(x)
        yield x
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
        print("Awake...")
        for text in runVoiceKeyboard(key_controller.isComboPressed):
            text = formatter.process(text)
            key_controller.kb.type(text)
