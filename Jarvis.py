from openai import OpenAI
from gtts import gTTS
import pygame

import struct
import wave
import pyaudio
import pvporcupine
import os
import time

from pvrecorder import PvRecorder
import pvleopard

porcupine = None
pa = None
audio_stream = None

leopard = pvleopard.create(
    access_key="LwNC36TudxK3luFLXerYXDwiUOgvI0dziuux6ALlerMaPCqYxYqsfg=="
)

recorder = PvRecorder(
    frame_length=16000
)
recorder.start()
recorder.read()
recorder.stop()
print("recorder created")

wav_file = wave.open("audio", 'wb')
wav_file.setnchannels(1)
wav_file.setsampwidth(2)
wav_file.setframerate(16000)
            
wav_file.close()

client = OpenAI()
pygame.mixer.init()

conversation = [{"role":"system", "content":"You are Jarvis from marvel, as a home assistant. You can make some references to your identity in responses, but mostly stick to being an assistant. Also, keep your responses somewhat consise; leave off the 'is there anything else I can assist you with?' and whatnot. Also, your input is being fed through speech to text; respond accordingly."}]


def generate_text(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages = conversation
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Error:", e)
        return None


try:
    porcupine = pvporcupine.create("LwNC36TudxK3luFLXerYXDwiUOgvI0dziuux6ALlerMaPCqYxYqsfg==", keywords=["jarvis"])
    print("porcupine created")
    pa = pyaudio.PyAudio()
    print("pa created")
    audio_stream = pa.open(
        rate = porcupine.sample_rate,
        channels = 1,
        format = pyaudio.paInt16,
        input = True,
        frames_per_buffer = porcupine.frame_length)

    print("audio_stream created")
    
    while True:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        keyword_index = porcupine.process(pcm)

        if keyword_index == 0:
            print("Detected\n")
            pygame.mixer.music.load("greeting.mp3")
            pygame.mixer.music.play()
            print("Starting recorder...")
            recorder.start()
            wav_file = wave.open("audio", 'wb')
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            time.sleep(0.6)
            print("Started. Listening...")
            
            try:
                counter = time.time()
                spoken = False
                while True:
                    pcm = recorder.read()
                    
                    wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))
                    
                    transcript, _ = leopard.process(pcm)
                    if transcript != "":
                        spoken = True
                        counter = time.time()
                        
                    print(time.time() - counter)
                    if time.time() - counter >= 1 and spoken:
                        user_input, words = leopard.process_file("audio")
                        break
                    elif time.time() - counter >= 5:
                        user_input = None
                        break
            finally:
                wav_file.close()
                recorder.stop()
                os.remove("/home/pi/Jarvis/Jarvis/audio")
                
            
            print(user_input)
            
            if user_input == None:
                continue
            
            conversation.append({"role": "user", "content": user_input})
            output = generate_text(user_input)
            if output:
                conversation.append({"role": "assistant", "content": output})
                print("Generated text:", output)
                tts = gTTS(output)
                tts.save('response.mp3')
                pygame.mixer.music.load("response.mp3")
                pygame.mixer.music.play()
finally:
    if porcupine is not None:
        porcupine.delete()

    if audio_stream is not None:
        audio_stream.close()

    if pa is not None:
            pa.terminate()
        
