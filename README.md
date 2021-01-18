# SimpleVoiceKeyboard
A simple hotkey activated Python voice keyboard leveraging the SpeechRecognition, pynput, and pyaudio modules

Requirements:
Python3

Python Modules:
SpeechRecognition
pynput
pyaudio

In *nix you should be able to install the python modules from the cmd line with ./install_reqs.sh .  

Usage:
From anywhere, just run voice_keyboard.py. The script will listen to the keyboard. When PRESS_TO_TALK_COMBO is detected (default cmd+alt), the script will start recording the microphone until the combo is released.
The recorded clip is then sent to the selected backend (either Google speech recognition or Sphinx) and converted to text.
The text is then sent as keypresses to the keyboard, so it will appear in whatever text box has focus at the time.
Exit with Ctrl-C.
