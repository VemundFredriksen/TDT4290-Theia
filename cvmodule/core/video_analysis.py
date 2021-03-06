from ctypes import *
import math
import random
import shutil
import sys
import os

def sample(probs):
	s = sum(probs)
	probs = [a/s for a in probs]
	r = random.uniform(0, 1)
	for i in range(len(probs)):
		r = r - probs[i]
		if r <= 0:
			return i
	return len(probs)-1

def c_array(ctype, values):
	arr = (ctype*len(values))()
	arr[:] = values
	return arr

class BOX(Structure):
	_fields_ = [("x", c_float), ("y", c_float), ("w", c_float), ("h", c_float)]

class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]


libdarknet_path = ""
network_weights = ""
if os.path.isfile("./config.txt"):
	f = open("./config.txt")
	libdarknet_path = f.readline().strip().split('=')[1]
	f.readline() # Skips one line where ftp-path is declared
	network_weights = f.readline().strip().split('=')[1]
	fps = f.readline().strip().split('=')[1]
else:
	print("No config.txt found, you need to make a config.txt file here %s, the file should contain the full path to libdarknet.so, the dir for the ftp serve and the full path to the weights used in detection , each on a seperate line" % (os.getcwd()))

lib = CDLL(libdarknet_path, RTLD_GLOBAL)

lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

def classify(net, meta, im):
	out = predict_image(net, im)
	res = []
	for i in range(meta.classes):
		res.append((meta.names[i], out[i]))
	res = sorted(res, key=lambda x: -x[1])
	return res

def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
	im = load_image(image, 0, 0)
	num = c_int(0)
	pnum = pointer(num)
	predict_image(net, im)
	dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
	num = pnum[0]
	if (nms): do_nms_obj(dets, num, meta.classes, nms);

	res = []
	for j in range(num):
		for i in range(meta.classes):
			if dets[j].prob[i] > 0:
				b = dets[j].bbox
				res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
	res = sorted(res, key=lambda x: -x[1])
	free_image(im)
	free_detections(dets, num)
	return res

from video_converter import video_to_images
import glob
from PIL import Image, ImageDraw
import os
from datetime import datetime

def draw_prediction_box(image, preds, store_folder):
	img = Image.open(image)
	draw = ImageDraw.Draw(img)
	saved = store_folder + "/{}.{}".format(datetime.now(), "jpg")
	for pred in preds:
		rect = pred[2]
		draw.rectangle(((rect[0] - rect[2]/2, rect[1] - rect[3]/2), (rect[0] + rect[2]/2, rect[1] + rect[3]/2)))
	if(len(preds)>0):
		img.save(saved, "JPEG")
	return saved


def mock_gps():
    base = (63.415551, 10.372429)
    generated = (base[0] + random.uniform(0, 0.02600), base[1] + random.uniform(0, 0.05700))
    return "{}, {}".format(generated[0], generated[1])

def store_meta_data(imagePath, preds):

    dash = 0
    for i in range(len(imagePath) -1, -1, -1):
        if(imagePath[i] == '/'):
           dash = i
           break
    fileName = imagePath[dash + 1::]

    f = open("{}.meta".format(imagePath[:-4]), "w+")
    log = "{"
    log += "\n\"type\": \"pothole\","
    log += "\n\"priority\" : 5,"
    log += "\n\"coordinates\": [ {} ],".format(mock_gps())
    log += "\n\"status\": \"not fixed\","
    log += "\n\"filename\": \"{}\",".format(fileName)
    log += "\n\"bounding_box\": [\n"
    img = Image.open(imagePath)
    w,h = img.size
    for p in preds:
        box = p[2]
        log += "{{ \"x\": {},".format(box[0]/w)
        log += " \"y\": {},".format(box[1]/h)
        log += " \"w\": {},".format(box[2]/w)
        log += " \"h\": {}".format(box[3]/h)
        log += "},\n"

    log = log[:-2]
    log += "]\n"
    log += "},\n"
    log = log[:-3] + "\n},"
    f.write(log)
    f.close()

    return os.getcwd()

def start_progress(title):
    print(title + "[" + '-'*40 + "]" + chr(8)*41, flush=True, end='')


def update_progress(progress, prev_num_squares):
    new_num_squares = math.floor((progress/100)*40)
    squares_to_add = new_num_squares - prev_num_squares
    print('#'*squares_to_add, flush=True, end='')
    return new_num_squares

def finish_progress(prev_num_squares):
    squares_to_add = math.floor(40 - prev_num_squares)
    print('#'*squares_to_add + "]", flush=True)

def do_video_analysis(path_to_video, path_to_image_dir, path_to_save_dir):
	global network_weights
	global fps
	net = load_net("yolov3-pothole.cfg".encode("utf-8"), network_weights.encode("utf-8"), 0)
	meta = load_meta("obj.data".encode("utf-8"))

	video_to_images(path_to_video, path_to_image_dir, 1.0/(int(fps)))
	os.remove(path_to_video)
	
	start_progress("Images analysed: ")
	counter = 0
	pns = 0
	imgs = glob.glob(path_to_image_dir + "/*.jpg")
	for im in imgs:
		r = detect(net, meta, im.encode("utf-8"))
		counter += 1
		pns = update_progress(counter/len(imgs)*100, pns)
		if(len(r) > 0):
			image = draw_prediction_box(im, r, path_to_save_dir)
			store_meta_data(image, r)
	finish_progress(pns)


if __name__ == "__main__":
	print("Starting CV analysis.")
	do_video_analysis(sys.argv[1], sys.argv[2], sys.argv[3])

