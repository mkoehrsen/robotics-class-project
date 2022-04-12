import flask
import logging
import os
import rtsp
import subprocess
import tempfile
import threading
import time
import vehicle_rpc

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
vehicle = vehicle_rpc.init_vehicle()
capture_dir = tempfile.mkdtemp()
capture_proc = None
proc_lock = threading.Lock()

@app.route("/")
def root():
    return flask.redirect(flask.url_for('static', filename='index.html'))

@app.route("/state/", methods=["POST"])
def update_state(): 
    state = flask.request.get_json()

    direction = state["direction"]
    throttle = float(state["throttle"])
    camera_on = bool(state["camera_on"])
    speed = max(0, min(int(throttle * 255), 255))
    if direction == "forward":
        vehicle.forwardManual(speed)
    elif direction == "reverse":
        vehicle.reverseManual(speed)
    elif direction == "left":
        # TODO -- scale back throttle for turning?
        vehicle.leftManual(speed)
    elif direction == "right":
        # TODO -- scale back throttle for turning?
        vehicle.rightManual(speed)
    else:
        vehicle.stopManual()

    with proc_lock:
        global capture_proc
        if camera_on and capture_proc is None:
            capture_cmd = ['nvgstcapture', '-m', '2', '--file-name', capture_dir + "/capture"]
            capture_proc = subprocess.Popen(capture_cmd, stdin=subprocess.PIPE)
            capture_proc.stdin.write('1\n'.encode('ascii'))
            capture_proc.stdin.flush()
        elif not camera_on and capture_proc is not None:
            # Having trouble getting "q" to work so just wait a little bit for
            # recording to finish and then kill the subprocess
            capture_proc.stdin.write('0\n'.encode('ascii'))
            capture_proc.stdin.flush()
            time.sleep(.25)
            # capture_proc.kill()
            capture_proc.communicate('q\n'.encode('ascii'))
            capture_proc = None

    return flask.make_response({
        "status": "OK",
        "video_files": os.listdir(capture_dir)
    })

@app.route("/videos/<filename>")
def download_video(filename):
    return flask.send_file(os.path.join(capture_dir, filename), as_attachment=True)

# threading.Thread(target=rtsp.run_server).start()
