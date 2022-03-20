import cv2
import flask
import flask_sock
import json
import logging
import os
import threading
import time

import camera
import motorctl
import vision

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
sock = flask_sock.Sock(app)
motors = motorctl.MotorCtl()

IMAGEDIR = os.path.join(os.path.dirname(__file__), 'static', 'images')
os.makedirs(IMAGEDIR, exist_ok=True)

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

new_image_cond = threading.Condition()
@sock.route('/image-stream')
def images(ws):
    while True:
        with new_image_cond:
            new_image_cond.wait()
        
        filenames = sorted(fn for fn in os.listdir(IMAGEDIR) if not fn.endswith('.tmp.jpg'))
        raw_filenames = [fn for fn in filenames if fn.endswith('raw.jpg')]
        proc_filenames = [fn for fn in filenames if fn.endswith('proc.jpg')]

        for fn in raw_filenames[:-3] + proc_filenames[:-3]:
            try:
                _logger.debug("Deleting file " + fn)
                os.unlink(os.path.join(IMAGEDIR, fn))
            except:
                pass
            

        state = {
            "raw_file": raw_filenames[-1] if len(raw_filenames) else None,
            "proc_file": proc_filenames[-1] if len(proc_filenames) else None
        }
        _logger.debug(json.dumps(state))
        ws.send(json.dumps(state))

def vision_loop():

    while True:
        frame_in = camera.read_frame()
        frame_out = vision.process_frame(frame_in)

        curr_time_millis = int(time.time()*1000)
        raw_image_path_tmp = os.path.join(IMAGEDIR, f"{curr_time_millis}_raw.tmp.jpg")
        raw_image_path = os.path.join(IMAGEDIR, f"{curr_time_millis}_raw.jpg")
        proc_image_path_tmp = os.path.join(IMAGEDIR, f"{curr_time_millis}_proc.tmp.jpg")
        proc_image_path = os.path.join(IMAGEDIR, f"{curr_time_millis}_proc.jpg")

        cv2.imwrite(raw_image_path_tmp, frame_in)
        cv2.imwrite(proc_image_path_tmp, frame_out)

        os.rename(raw_image_path_tmp, raw_image_path)
        os.rename(proc_image_path_tmp, proc_image_path)

        with new_image_cond:
            new_image_cond.notify_all()

threading.Thread(target=vision_loop, daemon=True).start()
