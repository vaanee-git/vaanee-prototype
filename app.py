from flask import Flask, jsonify, request
from flask import send_file
from pymongo import MongoClient
import azure.cognitiveservices.speech as speechsdk
import requests
import time

app = Flask(__name__)

turn_audio = {"1": "./audio/Greet_default.wav",
              "2": "./audio/AskCheckinDate_default.wav",
              "3": "./audio/AskGuests_default.wav",
              "4": "./audio/AskRoomType_default.wav",
              "5": "./audio/AskTwinBed_default.wav",
              "6": "./audio/CheckAvailability_default.wav",
              "7": "./audio/ConfirmAvailability_default.wav",
              "8": "./audio/BookRoom_default.wav",
              "9": "./audio/BookingSuccessful_default.wav",
              "10": "./audio/GymHours_default.wav",
              "11": "./audio/Goodbye_default.wav"}


@app.route('/bot_response', methods=['GET'])
def get_bot_response():
    args = request.args
    turn = args.get("turn")
    if int(turn) > 0:
        if turn in turn_audio.keys():
            path_to_file = turn_audio[turn]
            return send_file(
                path_to_file,
                mimetype="audio/wav",
                as_attachment=True)
    return {"Audio": "NOT FOUND"}


def save_to_db(turn, response):
    URI = "mongodb+srv://vaanee-sritej:ffng9vl1yE7fGjwl@cluster0.ensbbnz.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(URI)
    db = client["prototype"]
    col = db["user_response"]

    mydict = {"turn": int(turn), "response": response}
    x = col.insert_one(mydict)

    if x.inserted_id:
        return True
    return False


def recognize_from_wav(file_path):
    speech_config = speechsdk.SpeechConfig(subscription='159f7108b2a74f279eecb004944afd95', region='centralindia')
    speech_config.speech_recognition_language = "en-IN"
    audio_config = speechsdk.audio.AudioConfig(filename=file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")
    return None


def recognize_from_api(data):
    res = requests.post(
        url='https://centralindia.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US&format=detailed',
        data=data,
        headers={'Content-Type': 'audio/wav', 'Ocp-Apim-Subscription-Key': '159f7108b2a74f279eecb004944afd95',
                 'Accept': 'application/json'})
    return res.json()["DisplayText"]


@app.route('/user_response', methods=['POST'])
def save_user_response():
    if request.method == 'POST':
        turn = request.args.get("turn")
        audio = request.files['music_file']
        text = recognize_from_api(audio)

        # Save to DB
        start = time.time()
        save_to_db(turn=turn, response=text)
        end = time.time()
        print(end-start)
        return {"turn": turn,
                "response": text,
                }