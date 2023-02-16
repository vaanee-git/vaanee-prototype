from flask import Flask, jsonify, request
from flask import send_file
from pymongo import MongoClient
from datetime import datetime
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


def get_current_date_time():
    now = datetime.now()

    # Format : dd/mm/YY H:M:S
    return now.strftime("%d/%m/%Y %H:%M:%S")


def save_to_db(call_dict):
    URI = "mongodb+srv://vaanee-sritej:ffng9vl1yE7fGjwl@cluster0.ensbbnz.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(URI)
    db = client["prototype"]
    col = db["user_response"]

    x = col.insert_one(call_dict)

    if x.inserted_id:
        return True
    return False


def recognize_from_api(data):
    res = requests.post(
        url='https://centralindia.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US&format=detailed',
        data=data,
        headers={'Content-Type': 'audio/wav', 'Ocp-Apim-Subscription-Key': '159f7108b2a74f279eecb004944afd95',
                 'Accept': 'application/json'})
    return res.json()["DisplayText"]


active_phone_numbers = {}


@app.route('/register_call_initiation', methods=['POST'])
def register_call_initiation():
    if "caller_number" in request.json:
        caller_number = str(request.json["caller_number"])
        if len(caller_number) == 10:
            if caller_number in active_phone_numbers.keys():
                return {"number_saved": True,
                        "caller_number": "ALREADY SAVED AS ACTIVE"}
            else:
                active_phone_numbers[caller_number] = {"call_start_time": get_current_date_time()}
                active_phone_numbers[caller_number]["user_responses"] = {}
                active_phone_numbers[caller_number]["current_turn"] = 0
            return {"number_saved": True}
        else:
            return {"number_saved": False,
                    "caller_number": "INVALID"}
    return {"number_saved": False,
            "caller_number": "NOT_FOUND"}


@app.route('/get_active_caller_numbers', methods=['GET'])
def get_active_caller_numbers():
    return {"active_caller_numbers": list(active_phone_numbers.keys())}


@app.route('/get_bot_response', methods=['GET'])
def get_bot_response():
    args = request.args
    caller_number = args.get("caller_number")
    if caller_number in active_phone_numbers.keys():
        turn = args.get("turn")
        if int(turn) > 0 and turn == str(active_phone_numbers[caller_number]["current_turn"] + 1):
            if turn in turn_audio.keys():
                path_to_file = turn_audio[turn]
                active_phone_numbers[caller_number]["current_turn"] = \
                    active_phone_numbers[caller_number]["current_turn"] + 1
                return send_file(
                    path_to_file,
                    mimetype="audio/wav",
                    as_attachment=True)
            else:
                return {"audio": "NOT_FOUND"}
        else:
            return {"invalid_turn_number": True}
    else:
        return {"caller_number": "INACTIVE"}


@app.route('/send_user_response', methods=['POST'])
def capture_user_response():
    if request.method == 'POST':
        args = request.args
        turn = args.get("turn")
        caller_number = str(args.get("caller_number"))
        if caller_number in active_phone_numbers.keys():
            if int(turn) > 0 and turn == str(active_phone_numbers[caller_number]["current_turn"]):
                # get audio and its transcription
                audio = request.files['user-audio']
                try:
                    transcription = recognize_from_api(audio)
                except:
                    return {"user_response": "NOT_SAVED",
                            "transcription": "COULD_NOT_GENERATE",
                        }

                # Save to Memory
                active_phone_numbers[caller_number]["user_responses"][turn] = transcription
                return {"user_response": "SAVED",
                        "transcription": transcription,
                        }
            else:
                return {"invalid_turn_number": True}
        else:
            return {"caller_number": "INACTIVE"}


@app.route('/get_user_responses', methods=['GET'])
def get_user_responses():
    args = request.args
    caller_number = str(args.get("caller_number"))
    if len(caller_number) == 10:
        return active_phone_numbers[caller_number]["user_responses"]


@app.route('/register_call_ended', methods=['POST'])
def register_call_ended():
        if "call-recording" in request.files:
            audio = request.files['call-recording']
            audio_avl = True
        else:
            audio_avl = False
        args = request.args
        caller_number = str(args.get("caller_number"))
        reason = str(args.get("reason"))
        valid_reasons = ["USER_ENDED", "UNABLE_TO_SAVE_CALLER_NUMBER", "AUDIO_NOT_FOUND",
                         "UNABLE_TO_FETCH_BOT_RESPONSE", "USER_RESPONSE_NOT_SAVED", "COULDNT_SEND_USER_RESPONSE"]
        if reason not in valid_reasons:
            return {"reason": "INVALID"}
        if caller_number and caller_number in active_phone_numbers.keys():
            call_details = active_phone_numbers[caller_number]
            call_dict = {"caller_number": caller_number,
                         "call_start_time": call_details["call_start_time"],
                         "call_end_time": get_current_date_time(),
                         "user_responses": call_details["user_responses"],
                         "reason": reason
                         }
            save_to_db(call_dict)
            del active_phone_numbers[caller_number]
            return {"call_details_saved": True,
                    "audio_saved": audio_avl}
        else:
            return {"caller_number": "INACTIVE"}
