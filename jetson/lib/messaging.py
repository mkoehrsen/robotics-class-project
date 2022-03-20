import queue
import threading

QNAME_CALIBRATOR = "calibrator"
QNAME_IMAGE_PROCESSOR = "image_processor"

_queue_map = {}
_queue_map_lock = threading.Lock()
def _get_queue(qname):
    with _queue_map_lock:
        if qname not in _queue_map:
            _queue_map[qname] = queue.Queue()
        return _queue_map[qname]

def enqueue(qname, obj):
    _get_queue(qname).put(obj)

def readone(qname, block=True, timeout=None):
    try:
        return _get_queue(qname).get(block=block, timeout=timeout)
    except queue.Empty:
        return None

def readall(qname, at_least_one=True):
    result = []

    obj = readone(qname, block=at_least_one)
    while obj is not None:
        result.append(obj)
        obj = readone(qname, block=False)

    return result

