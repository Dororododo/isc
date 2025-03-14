"""
db - flask - 프론트 로그인 페이지 기능 구현 코드

https://duckgugong.tistory.com/274
-> 해당 예제를 참고하였음


"""

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
    make_response,
)
import jwt
import datetime
import hashlib
from pymongo import MongoClient
from flask_socketio import SocketIO, join_room, leave_room, emit
from bson import ObjectId


SECRET_KEY = "SPARTA"

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "비밀번호 설정"
socketio = SocketIO(app)

client = MongoClient("mongodb+srv://rjh0162_rw:difbel0162@cluster0.6twyc.mongodb.net/")
db = client.ISC_database  # 사용자 탐색용 db

# 사용자 토큰 명
USERTOKEN = "usertoken"

# JWT토큰 암호/복호화 알고리즘
ALGORITHMS_JWT = "HS256"

HTML_INDEX = "index.html"
HTML_LOGIN = "login.html"
HTML_SIGNUP = "sign-up.html"
HTML_MAIN = "home.html"
HTML_OUTROOM = "chat_test_outroom.html"
HTML_INROOM = "chat.html"
HTML_MATCH = "match_page.html"
HTML_REQUEST = "match_personal.html"

####################
#  범용       함수   # --> 보안이나 편의성을 위하여 전반적으로 사용되는 함수
####################


# 보안: 유효한 캐시를 가지고 있는 사용자만
#  api_valid() -> 프론트에서 요청, is_valid(asdf) -> 백에서 알아서 검사
def is_valid():
    token_receive = request.cookies.get(USERTOKEN)

    if token_receive is None:
        # 쿠키가 없을 때의 처리
        return False
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        userinfo = db.user.find_one({"id": payload["id"]}, {"_id": 0})
        return True
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return False
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return False


# 현재 토큰 보유자의 json를 리턴한다. -> 지금은 안씀
def what_user():
    token_receive = request.cookies.get(USERTOKEN)

    if token_receive is None:
        # 쿠키가 없을 때의 처리
        return False
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        userinfo = db.user.find_one({"id": payload["id"]}, {"_id": 0})
        return userinfo
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return None
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return None


# 백엔드에서 캐시 방지 헤더 -> 지금은 안씀
def render_template_nocash(html):
    response = make_response(render_template(html))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


####################
#  페이지 이동 함수   # --> render_template를 이용해 html을 불러오는 함수
####################


# index - 첫 페이지, 잘못된 접근 시 해당 페이지로 이동
@app.route("/")
def home():
    if is_valid():
        return redirect("/main")
    return render_template(HTML_INDEX)


# 로그인 페이지
@app.route("/login")
def login():
    if is_valid():
        return redirect("/main")
    return render_template(HTML_LOGIN)


# 회원가입 페이지
@app.route("/signup")
def signup():
    if is_valid():
        return redirect("/main")
    return render_template(HTML_SIGNUP)


# 메칭 페이지 - 매칭 요청, 관게 끊기
@app.route("/match")
def match():
    if not is_valid():
        return redirect("/")
    return render_template((HTML_MATCH))


# 메인 페이지 - 정보 확인 및 페이지 이동가능
@app.route("/main")
def main():
    if not is_valid():
        return redirect("/")

    token_receive = request.cookies.get(USERTOKEN)
    # token을 시크릿키로 디코딩합니다.
    if token_receive:
        try:
            # token을 시크릿키로 디코딩합니다.
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
            # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
            user = db.user.find_one({"id": payload["id"]}, {"_id": 0})
            username = user["nick"] if user else ""
            role = user["role"] if user else ""
        except jwt.ExpiredSignatureError:
            # 토큰이 만료된 경우
            username = ""
            role = ""
        except jwt.InvalidTokenError:
            # 토큰이 유효하지 않은 경우
            username = ""
            role = ""
    else:
        # 토큰이 없는 경우
        username = ""
        role = ""
    if role == "care_coordi":
        return render_template(HTML_MAIN, username=username, role="케어코디")
    elif role == "keeper":
        return render_template(HTML_MAIN, username=username, role="보호자")

    # 비정상적인 접근 차단
    return redirect("/")


# 매칭 요청 관리 페이지 - 매칭 요청 거절, 매칭 요청 수락
@app.route("/match_personal")
def match_personal():
    if not is_valid():
        return redirect("/match_personal")
    return render_template((HTML_REQUEST))


# 채팅방 내부 - 채팅 가능
@app.route("/inroom", methods=["GET", "POST"])
def go_inroom():
    if not is_valid():
        return redirect("/")

    token_receive = request.cookies.get(USERTOKEN)
    # token을 시크릿키로 디코딩합니다.
    if token_receive:
        try:
            # token을 시크릿키로 디코딩합니다.
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
            # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
            user = db.user.find_one({"id": payload["id"]}, {"id": 0})
            matename = user["mate"]
        except jwt.ExpiredSignatureError:
            # 토큰이 만료된 경우
            matename == ""
        except jwt.InvalidTokenError:
            # 토큰이 유효하지 않은 경우
            matename == ""
    else:
        # 토큰이 없는 경우
        matename == ""
        return redirect("/")

    return render_template(HTML_INROOM, matename=matename)


# 채팅방 외부 - 채팅방을 골라서 들어갈 수 있음, 다만 디버깅 용임
@app.route("/chat")
def go_outroom():
    if not is_valid():
        return redirect("/")

    token_receive = request.cookies.get(USERTOKEN)
    # token을 시크릿키로 디코딩합니다.
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
    # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
    username = db.user.find_one({"id": payload["id"]}, {"_id": 0})

    return render_template((HTML_OUTROOM), username=username["nick"])


####################
#       기능 함수   # - @app.route("/api 를 사용하는 함수, 주로 methods= 가 존재함
####################

#### 계정 관련 함수 ####


# 회원가입
@app.route("/api/signup", methods=["POST"])
def api_register():
    # id가 ~~인 빈 칸에서 입력값을 받아온다.
    id_receive = request.form["id_give"]
    pw_receive = request.form["pw_give"]
    nickname_receive = request.form["nickname_give"]
    role_receive = request.form["role"]  # keeper 혹은 care_coordi을 전달받게 된다.

    # 암호화를 한다.
    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    # 빈칸 입력시 경고
    if (
        id_receive == ""
        or pw_receive == ""
        or nickname_receive == ""
        or role_receive == ""
    ):
        return jsonify({"result": "fail", "msg": "공란이 존재합니다!"})
    # 이미 존재하는 아이디면 패스!
    user_exists = db.user.find_one(
        {"$or": [{"id": id_receive}, {"nick": nickname_receive}]}
    )
    if user_exists:
        if user_exists["id"] == id_receive:
            return jsonify({"result": "fail", "msg": "이미 존재하는 아이디입니다!"})
        elif user_exists["nick"] == nickname_receive:
            return jsonify({"result": "fail", "msg": "이미 존재하는 닉네임입니다!"})
    else:
        # db에 기입
        db.user.insert_one(
            {
                "id": id_receive,
                "pw": pw_hash,
                "nick": nickname_receive,
                "role": role_receive,
                "mate": "",
            }
        )
        # 결과를 반환 - 프론트에 결과 전송
        return jsonify({"result": "success"})


# 로그인
@app.route("/api/login", methods=["POST"])
def api_login():
    id_receive = request.form["id_give"]
    pw_receive = request.form["pw_give"]
    role_receive = request.form["role"]  # keeper 혹은 care_coordi을 전달받게 된다.

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({"id": id_receive, "pw": pw_hash, "role": role_receive})

    # 찾으면 JWT 토큰을 만들어 발급합니다. - not None -> 존재한다면
    if result is not None:
        # JWT 토큰 생성 -> 해당 토큰에 id와 만료시간에 관련된 정보 삽입
        # 토큰 유효기간은 1000초
        payload = {
            "id": id_receive,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=1000),
        }
        # 토큰의 암호화!
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHMS_JWT)

        # token을 줍니다.
        return jsonify({"result": "success", "token": token})
    # 찾지 못하면
    else:
        return jsonify(
            {"result": "fail", "msg": "아이디/비밀번호/역힐 (이)가 일치하지 않습니다."}
        )


# 로그아웃
@app.route("/api/logout", methods=["POST"])
def api_logout():
    # 클라이언트에서 보내는 JWT 토큰을 지워줍니다.
    resp = jsonify({"result": "success", "msg": "로그아웃 되었습니다."})
    resp.set_cookie(
        USERTOKEN, "", expires=0
    )  # JWT 토큰을 삭제하기 위해 만료 시간을 0으로 설정
    return resp


# 보안: 로그인한 사용자만 통과할 수 있는 API - front에서 사용
@app.route("/api/isAuth", methods=["GET"])
def api_valid():
    token_receive = request.cookies.get(USERTOKEN)

    if token_receive is None:
        # 쿠키가 없을 때의 처리
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})

    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        userinfo = db.user.find_one({"id": payload["id"]}, {"_id": 0})
        return jsonify({"result": "success", "nickname": userinfo["nick"]})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


#### 채팅 관련 함수 ####


# outroom에서 사용하는 방 생성및 입장 코드
@app.route("/api/findchatroom", methods=["POST"])
def api_findchatroom():
    token_receive = request.cookies.get(USERTOKEN)
    try:
        # token에서 정보를 뽑아 냅니다.
        # 입력받은 id의 유저를 찾습니다.
        payload_user = jwt.decode(
            token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )
        id_receive = request.form["id_give"]

        # 예외조건 - 자신 - 자신 제외, 상대가 DB에 없을 시 오류 출력
        if payload_user["id"] == id_receive:
            return jsonify(
                {"result": "fail", "msg": "자기자신과의 대화는 지금도 할 수 있습니다."}
            )

        if db.user.find_one({"id": id_receive}) is None:
            return jsonify({"result": "fail", "msg": "대화상대가 존재하지않습니다."})

        # 두 유저가 존재하면서 활성화된 방이 없다면 새로운 방을 생성
        chatroom_info = db.chat_room.find_one(
            {
                "talker_box": {"$all": [payload_user["id"], id_receive]},
                "Is_room_active": True,
            }
        )  # 하나의 문서만 반환됩니다

        # 활성화된 채팅방이 없을 경우 채팅방을 생성한다.
        if not chatroom_info:
            chatroom_data = {
                "talker_box": [payload_user["id"], id_receive],
                "talk_box": [],
                "Is_room_active": True,
            }
            # MongoDB에 채팅 방 데이터 삽입
            result = db.chat_room.insert_one(chatroom_data)
            # 새로 생성된 채팅방 정보 가져오기 - none이기 때문
            chatroom_info = db.chat_room.find_one({"_id": result.inserted_id})

        # 토큰에 넣을 데이터 생성
        payload_chat = {
            "_id": str(chatroom_info["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=1000),
        }

        # 토큰의 암호화!
        token = jwt.encode(payload_chat, SECRET_KEY, algorithm=ALGORITHMS_JWT)

        # token을 줍니다. - 채팅방 입장
        return jsonify({"result": "success", "token": token, "msg": "채팅방 접속 성공"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


@app.route("/api/findchatroom_mate", methods=["POST"])
def api_findchatroom_mate():
    token_receive = request.cookies.get(USERTOKEN)
    try:
        # token에서 정보를 뽑아 냅니다.
        # 입력받은 id의 유저를 찾습니다.
        payload_user = jwt.decode(
            token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )
        user = db.user.find_one({"id": payload_user["id"]})
        if "mate" in user:
            user_mate = db.user.find_one({"id": user["mate"]})
        else:
            return jsonify({"result": "fail", "msg": "mate된 상대가 없습니다.."})

        # 자신의 mate상대가 없다면 실패
        if user["mate"] == "":
            return jsonify({"result": "fail", "msg": "mate된 상대가 없습니다.."})

        if user_mate is None:
            return jsonify(
                {
                    "result": "fail",
                    "msg": "mate가 존재하지않습니다. 운영팀에 연락바랍니다.",
                }
            )

        # 두 유저가 존재하면서 활성화된 방이 없다면 새로운 방을 생성
        chatroom_info = db.chat_room.find_one(
            {
                "talker_box": {"$all": [payload_user["id"], user_mate["id"]]},
                "Is_room_active": True,
            }
        )  # 하나의 문서만 반환됩니다

        # 활성화된 채팅방이 없을 경우 채팅방을 생성한다.
        if not chatroom_info:
            chatroom_data = {
                "talker_box": [payload_user["id"], user_mate["id"]],
                "talk_box": [],
                "Is_room_active": True,
            }
            # MongoDB에 채팅 방 데이터 삽입
            result = db.chat_room.insert_one(chatroom_data)
            # 새로 생성된 채팅방 정보 가져오기 - none이기 때문
            chatroom_info = db.chat_room.find_one({"_id": result.inserted_id})

        # 토큰에 넣을 데이터 생성
        payload_chat = {
            "_id": str(chatroom_info["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=500),
        }

        # 토큰의 암호화!
        token = jwt.encode(payload_chat, SECRET_KEY, algorithm=ALGORITHMS_JWT)

        # token을 줍니다. - 채팅방 입장
        return jsonify({"result": "success", "token": token, "msg": "채팅방 접속 성공"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


#### mate 관련 함수 ####


# mate 요청 보내기
@app.route("/api/send_match", methods=["POST"])
def api_send_match():
    # id가 ~~인 빈 칸에서 입력값을 받아온다.
    nickname_receive = request.form["nick_give"]

    # 빈칸 입력시 경고
    if nickname_receive == "":
        return jsonify({"result": "fail", "msg": "공란이 존재합니다!"})

    token_receive = request.cookies.get(USERTOKEN)
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])

        # 요청자와 수신자의 정보 확인
        userinfo_sender = db.user.find_one({"id": payload["id"]})
        userinfo_receiver = db.user.find_one({"nick": nickname_receive})

        # 존재하는 아이디일 경우, 해당 요청을 보낼 수 있는지 확인 -> 요청자와 role이 동일한가?, mate된 상대가 존재하는가?
        if userinfo_receiver is None:
            return jsonify({"result": "fail", "msg": "해당 사용자를 찾을 수 없습니다"})
        if userinfo_receiver["role"] == userinfo_sender["role"]:
            return jsonify(
                {"result": "fail", "msg": "동일 역할끼리는 매칭을 맺을 수 없습니다."}
            )
        if userinfo_sender["mate"] != "":
            return jsonify(
                {
                    "result": "fail",
                    "msg": "매칭자가 있는 상태에서는 매칭 요청을 할 수 없습니다.",
                }
            )
        if userinfo_receiver["mate"] != "":
            return jsonify({"result": "fail", "msg": "이미 매칭이 된 상대입니다."})

        # 해당 요청을 DB에 업로드
        result = db.mate_request.insert_one(
            {"sender": userinfo_sender["nick"], "receiver": userinfo_receiver["nick"]}
        )
        if result is None:
            return jsonify({"fail": "DB업로드 오류"})
        return jsonify({"result": "success"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})

    # mate 요청 보내기


# mate관계를 끊는다.
@app.route("/api/dis_match", methods=["POST"])
def api_dis_match():
    # 우선 사용자가 매칭된 상대가 있는지 확인한다. - 사용자가 누군지는 토큰 활용
    token_receive = request.cookies.get(USERTOKEN)
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])

        # 요청자와 수신자의 정보 확인
        user = db.user.find_one({"id": payload["id"]})
        if "mate" in user:
            user_mate = db.user.find_one({"id": user["mate"]})
        else:
            return jsonify(
                {
                    "result": "fail",
                    "msg": '비정상적인 계정입니다. - "mate"데이터 미존재',
                }
            )

        # 자신의 mate상대가 있다면 실패
        if user["mate"] == "":
            return jsonify({"result": "fail", "msg": "mate된 상대가 없습니다.."})

        if user_mate is None:
            return jsonify(
                {
                    "result": "fail",
                    "msg": "mate가 존재하지않습니다. 운영팀에 연락바랍니다.",
                }
            )

        # 유저 정보 또한 업데이트
        result_user = db.user.update_one({"nick": user["nick"]}, {"$set": {"mate": ""}})
        result_mate = db.user.update_one(
            {"nick": user_mate["nick"]}, {"$set": {"mate": ""}}
        )

        # 두 문서가 모두 수정되었는지 확인
        if result_user.modified_count > 0 and result_mate.modified_count > 0:
            return jsonify({"result": "success"})
        else:
            return jsonify({"result": "failure"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


# DB에서 자신에게 요청된 match를 list화 시켜서 보관한다.
@app.route("/api/hear_match", methods=["POST"])
def api_hear_match():
    token_receive = request.cookies.get(USERTOKEN)
    try:
        # token에서 정보를 뽑아 냅니다.
        # 입력받은 id의 유저를 찾습니다.
        payload_user = jwt.decode(
            token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )
        # 유저에게 온 요청들을 처리한다. - 과거에 온 요청을 우선적으로 띄운다.
        request_list = db.mate_request.find({"receiver": payload_user["id"]}).sort(
            "_id", 1
        )

        for request_part in request_list:
            payload_chat = {
                "id": str(request_part.get("id")),  # 'id' 필드
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=1000),
            }

        # 토큰의 암호화! -> 해당 리스트는 클라이언트에 저장된다. -> 항후 페이지 넘김에 적용
        token = jwt.encode(payload_chat, SECRET_KEY, algorithm=ALGORITHMS_JWT)

        # token을 줍니다. - 채팅방 입장
        return jsonify(
            {"result": "success", "token": token, "msg": "매칭 요청 조회 성공"}
        )

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})
    #


# 자신에게 요청된 요청을 리스트에서 찾아서 허가한다.
@app.route("/api/allow_match", methods=["POST"])
def api_allow_match():
    nickname_receive = request.form["nick_give"]
    token_receive = request.cookies.get(USERTOKEN)

    if nickname_receive == "":
        return jsonify({"result": "fail", "msg": "대상이 공란입니다. 입력해주세요"})

    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])

        # 수신자 정보 확인
        user = db.user.find_one({"id": payload["id"]})
        if user["mate"] != "":
            return jsonify(
                {
                    "result": "fail",
                    "msg": "매칭이 된 상태입니다. 추가로 매칭할 수 없습니다.",
                }
            )

        # 요청자 정보확인
        user_mate = db.user.find_one({"nick": nickname_receive})
        if user_mate["mate"] != "":
            return jsonify(
                {
                    "result": "fail",
                    "msg": "상대가 매칭이 된 상태입니다. 매칭되지 않습니다.",
                }
            )

        # 해당 요청이 현재 존재하는 지 확인
        request_inform = db.mate_request.find_one(
            {"receiver": user["nick"], "sender": user_mate["nick"]}
        )
        if request_inform == None:
            return jsonify(
                {"result": "fail", "msg": "해당 요청은 존재하지 않는 요청입니다."}
            )

        # 자신이 받은 요청을 삭제한다.
        result = db.mate_request.delete_one(
            {"receiver": user["nick"], "sender": user_mate["nick"]}
        )
        # mate를 바꾼다.

        db.user.update_one(
            {"nick": user["nick"]},  # user의 mate를 요청자의 닉네임으로 설정
            {"$set": {"mate": user_mate["nick"]}},
        )

        db.user.update_one(
            {"nick": user_mate["nick"]},  # user_mate의 mate를 수신자의 닉네임으로 설정
            {"$set": {"mate": user["nick"]}},
        )
        return jsonify({"result": "success", "msg": "매칭 요청 허가 성공"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


# 자신에게 요청된 요청을 거절한다. - 사용자가 누군지는 토큰 활용
@app.route("/api/disallow_match", methods=["POST"])
def disallow_match():
    nickname_receive = request.form["nick_give"]
    token_receive = request.cookies.get(USERTOKEN)

    if nickname_receive == "":
        return jsonify({"result": "fail", "msg": "대상이 공란입니다. 입력해주세요"})

    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])

        # 요청자와 수신자의 정보 확인
        user = db.user.find_one({"id": payload["id"]})

        if user["mate"] != "":
            return jsonify(
                {
                    "result": "fail",
                    "msg": "매칭이 된 상태입니다. 추가로 매칭할 수 없습니다.",
                }
            )

        # 해당 로직은 메이트를 바깥에서 받아야한다.
        user_mate = db.user.find_one({"nick": nickname_receive})

        if user_mate["mate"] != "":
            return jsonify(
                {
                    "result": "fail",
                    "msg": "상대가 매칭이 된 상태입니다. 매칭되지 않습니다.",
                }
            )

        # 해당 요청이 현재 존재하는 지 확인
        request_inform = db.mate_request.find_one(
            {"receiver": user["nick"], "sender": user_mate["nick"]}
        )
        if request_inform == None:
            return jsonify(
                {"result": "fail", "msg": "해당 요청은 존재하지 않는 요청입니다."}
            )

        # 자신이 받은 요청을 삭제한다.
        result = db.mate_request.delete_one(
            {"receiver": user["nick"], "sender": user_mate["nick"]}
        )

        return jsonify({"result": "success", "msg": "매칭 요청 거절 성공"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


# 자신에게 온 요청들을 확인한다.
# 메인 페이지에서 요청 확인 페이지로 가는 버튼을 누른 후에 작동한다.
@app.route("/api/first_match", methods=["POST"])
def first_match():
    nickname_receive = request.form["nick_give"]
    token_receive = request.cookies.get(USERTOKEN)

    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=[ALGORITHMS_JWT])
        # 수신자 정보 확인
        user = db.user.find_one({"id": payload["id"]})

        # 첫 페이지 입장시
        # 사용자에게 온 요청이 있는 지 확인한다.
        # 해당 요청이 현재 존재하는 지 확인

        request_inform = (
            db.mate_request.find({"receiver": user["nick"]})
            .sort("createdAt", 1)
            .limit(1)
        )

        # 사용자에게 온 요청이 없다면, 오류 메시지를 출력하고 밖으로 내보낸다.
        if request_inform.count_documents() == 0:
            return jsonify({"result": "fail", "msg": "온 요청이 없습니다."}), 404

        # 요청이 있을 경우 첫 번째 항목 가져오기
        request_data = request_inform[0]  # 첫 번째 요청

        # 관련 정보를 프론트로 다시 넘겨준다
        return jsonify(
            {
                "result": "success",
                "msg": "매칭 요청 확인 성공",
                "data": request_data["sender"],
            }
        )

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


# 지금 보고 있는 페이지의 이전 요청을 확인한다.
@app.route("/api/pred_match", methods=["POST"])
def pred_match():
    nickname_receive = request.form["nick_give"]
    token_receive = request.cookies.get(USERTOKEN)

    if nickname_receive == "":
        return jsonify({"result": "fail", "msg": "대상이 공란입니다. 입력해주세요"})

    try:
        # 첫 페이지 입장시
        # 우선 현재 페이지에 nick이 공란인지 확인한다.

        # 공란이라면 오류 메시지를 출력후 메인페이지로 이동한다.

        # 공란이 아니라면 해당 nick을 db에서 사용자에게 온 요청중 찾아본다

        # 해당 요청이 존재하지 않는다면 오류를 발생시키고 main페이지로 보낸다.

        # 해당 요청이 존재한다면, 해당 요청 이전 값을 찾아 해당 값을 띄운다.
        # 이전 값이 존재하지 않는다면 오류를 표기하고 해당 페이지에 머문다.
        return jsonify({"result": "success", "msg": "매칭 요청 페이지 이전 이동 성공"})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


# 지금 보고 있는 페이지의 다음 요청을 확인한다.
@app.route("/api/next_match", methods=["POST"])
def next_match():
    # 데이터는 span에서 받아온다.
    nickname_receive = request.form["nick_give"]
    token_receive = request.cookies.get(USERTOKEN)

    if nickname_receive == "":
        return jsonify({"result": "fail", "msg": "대상이 공란입니다. 입력해주세요"})

    try:
        # 첫 페이지 입장시
        # 우선 현재 페이지에 nick이 공란인지 확인한다.

        # 공란이라면 오류 메시지를 출력후 메인페이지로 이동한다.

        # 공란이 아니라면 해당 nick을 db에서 사용자에게 온 요청중 찾아본다

        # 해당 요청이 존재하지 않는다면 오류를 발생시키고 main페이지로 보낸다.

        # 해당 요청이 존재한다면, 해당 요청 다음 값을 찾아 해당 값을 띄운다.
        # 다음 값이 존재하지 않는다면 오류를 표기하고 해당 페이지에 머문다.
        return jsonify({"result": "success", "msg": "매칭 요청 페이지 다음 이동 성공"})

    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({"result": "fail", "msg": "로그인 시간이 만료되었습니다."})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({"result": "fail", "msg": "로그인 정보가 존재하지 않습니다."})


####################
#   socket.io 함수  # - @socketio을 사용하는 함수
####################


# 클라이언트가 특정 채팅방에 참여하는 이벤트 핸들러 -> 항후 오류 및 예외 처리 필요!
# 해당 함수에는 그 그거 함수랑 딸려오는 그거 그 변수 그거 필요없음! 그 캐시로 데이터를 받아오기 때문!
@socketio.on("join_chat")
def join_chat():
    print("hello,")
    try:
        # 쿠키에서 토큰 가져오기
        token_receive_user = request.cookies.get(USERTOKEN)
        token_receive_chat = request.cookies.get("chattoken")
        if not token_receive_user or not token_receive_chat:
            print("Error: Missing tokens in cookies.")
            return

        print("hello,")
        # 토큰 디코딩
        payload_user = jwt.decode(
            token_receive_user, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )
        payload_chat = jwt.decode(
            token_receive_chat, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )

        room_id = payload_chat["_id"]  # 대화방 ID
        customer_id = payload_user["id"]  # 고객 ID

        # 방 참여
        join_room(room_id)
        print(f"Customer {customer_id} has successfully joined room {room_id}")

        # DB에 있던 대화기록 출력 ->
        # DB의 object를 담는 array를 하나 만든다.
        # array에 따른 반복문 하나
        # 반복문은 emit을 통해서 서서히 출력한다.
        socketio.emit("clean_message")
        document = db.chat_room.find_one({"_id": ObjectId(room_id)})
        talk_box = document.get("talk_box", [])
        for item in talk_box:
            sender = item.get("talker", "Unknown")
            message = item.get("talk", "")
            timestamp = item.get("date", "")
            # 둘 중 한 명이라도 접속하면 작동, => 대화방에 한 명이 들어가 있으면 중복 출력되는 문제가 있음
            # 해당 명령어 이전에 html의 기록을 제거하는 식으로 해결함
            # socketio.emit('clean_message') 활용할것
            # 다만, 상대 접속시 재출력 현상 - 깜박이는 현상 발생 => 기능적 문제로 볼 수는 없으나 항후 기회가 되면 해결바람

            # 자신이 보낸 거면 receive_message_me
            # 대화상대가 보낸 거면 receive_message_you
            if customer_id == sender:
                socketio.emit(
                    "receive_message_me",
                    {"talker": sender, "talk": message, "date": timestamp},
                    room=room_id,
                )
            else:
                socketio.emit(
                    "receive_message_you",
                    {"talker": sender, "talk": message, "date": timestamp},
                    room=room_id,
                )

    except jwt.ExpiredSignatureError:
        print("Error: Token has expired.")
    except jwt.DecodeError:
        print("Error: Invalid token.")
    except Exception as e:
        print(f"Unexpected error: {e}")


# 채팅방에 메시지 보내기
@socketio.on("send_message")
def send_message(data):
    try:
        # 쿠키에서 토큰 가져오기
        token_receive_user = request.cookies.get(USERTOKEN)
        token_receive_chat = request.cookies.get("chattoken")
        if not token_receive_user or not token_receive_chat:
            print("Error: Missing tokens in cookies.")
            return

        # 토큰 디코딩
        payload_user = jwt.decode(
            token_receive_user, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )
        payload_chat = jwt.decode(
            token_receive_chat, SECRET_KEY, algorithms=[ALGORITHMS_JWT]
        )

        room_id = payload_chat["_id"]  # 대화방 ID
        user_id = payload_user["id"]  # 고객 ID

        message = data["message"]  # 메시지 - 이는 프론트에서 받아온 정보를 사용한다.
        time = data["time"]  # 메시지 - 이는 프론트에서 받아온 정보를 사용한다.

        filter_query = {"_id": ObjectId(room_id)}  # 대상 문서를 찾기 위한 조건

        # DB와 클라이언트에 전송할 대화 내용
        talk_box = {"talker": user_id, "talk": message, "date": time}
        # 배열에 객체 삽입
        try:
            result = db.chat_room.update_one(
                filter_query, {"$push": {"talk_box": talk_box}}
            )
            if result.matched_count == 0:
                print("No document matched the filter query.")
            elif result.modified_count == 0:
                print("Document matched but was not modified.")
            else:
                print("Document updated successfully.")

            # 자신이 보낸 거면 receive_message_me
            # 대화상대가 보낸 거면 receive_message_you
            socketio.emit(
                "receive_message_me",
                {"talker": user_id, "talk": message, "date": time},
                room=room_id,
            )
        except Exception as e:
            print(f"Database update error: {e}")
            socketio.emit("error", {"message": "Failed to update the database."})
            return

        # 이후 클라이언트에서 해당 데이터를 출력

    # jwt 관련 예외처리
    except jwt.ExpiredSignatureError:
        print("Error: Token has expired.")
        socketio.emit("error", {"message": "Authentication token expired."})
        return
    except jwt.DecodeError:
        print("Error: Invalid token.")
        socketio.emit("error", {"message": "Invalid authentication token."})
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        socketio.emit(
            "error", {"message": "An error occurred while sending the message."}
        )
        return


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
