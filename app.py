# -*- coding: utf-8 -*-
"""단어 농구 온라인 대전 서버 (Flask)
방 생성 -> 4자리 코드 -> 상대 입장 -> 2초 폴링으로 점수 동기화
"""
import random
import time
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

ROOMS = {}          # {code: {ts, p:{1:{score,ready},2:{score,ready}}, winner}}
ROOM_TTL = 7200     # 2시간 지난 방 정리
TARGET = 21


def _cleanup():
    now = time.time()
    for code in list(ROOMS):
        if now - ROOMS[code]["ts"] > ROOM_TTL:
            del ROOMS[code]


@app.route("/")
def index():
    return send_from_directory("static", "game.html")


@app.route("/api/room", methods=["POST"])
def create_room():
    _cleanup()
    code = str(random.randint(1000, 9999))
    while code in ROOMS:
        code = str(random.randint(1000, 9999))
    ROOMS[code] = {
        "ts": time.time(),
        "p": {1: {"score": 0, "ready": True}, 2: {"score": 0, "ready": False}},
        "winner": 0,
    }
    return jsonify(code=code, player=1)


@app.route("/api/room/<code>/join", methods=["POST"])
def join_room(code):
    room = ROOMS.get(code)
    if not room:
        return jsonify(error="no_room"), 404
    if room["p"][2]["ready"]:
        return jsonify(error="full"), 409
    room["p"][2]["ready"] = True
    room["ts"] = time.time()
    return jsonify(code=code, player=2)


@app.route("/api/room/<code>/score", methods=["POST"])
def report_score(code):
    room = ROOMS.get(code)
    if not room:
        return jsonify(error="no_room"), 404
    data = request.get_json(force=True, silent=True) or {}
    player = int(data.get("player", 0))
    score = int(data.get("score", 0))
    if player in (1, 2):
        # 단조 증가만 허용 (중복/지연 요청 안전)
        room["p"][player]["score"] = max(room["p"][player]["score"], score)
        if room["p"][player]["score"] >= TARGET and not room["winner"]:
            room["winner"] = player
    room["ts"] = time.time()
    return jsonify(ok=True)


@app.route("/api/room/<code>/state")
def room_state(code):
    room = ROOMS.get(code)
    if not room:
        return jsonify(error="no_room"), 404
    return jsonify(
        p1=room["p"][1]["score"],
        p2=room["p"][2]["score"],
        joined=room["p"][2]["ready"],
        winner=room["winner"],
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
