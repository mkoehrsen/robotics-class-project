import flask
import logging
import motorctl
import rtsp2
import threading

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
motors = motorctl.MotorCtl()

@app.route("/")
def root():
    return flask.redirect(flask.url_for('static', filename='index.html'))

@app.route("/state/", methods=["POST"])
def update_state(): 
    state = flask.request.get_json()

    direction = state["direction"]
    throttle = float(state["throttle"])
    if direction == "forward":
        motors.set_speeds(throttle, throttle)
    elif direction == "reverse":
        motors.set_speeds(-throttle, -throttle)
    elif direction == "left":
        # TODO -- scale back throttle for turning?
        motors.set_speeds(-throttle, throttle)
    elif direction == "right":
        # TODO -- scale back throttle for turning?
        motors.set_speeds(throttle, -throttle)
    else:
        motors.set_speeds(0, 0)

    # TODO -- camera control

    return flask.make_response({"status": "OK"})

threading.Thread(target=rtsp2.run_server).start()
