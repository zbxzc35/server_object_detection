#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
import six.moves.urllib as urllib
import sys

import tensorflow as tf
from PIL import Image
import numpy as np
import cv2
from flask import Flask
from flask import request
from flask import jsonify
import requests
from io import BytesIO
from flask import render_template
from urllib import request as ul_request

sys.path.append(os.path.join(os.path.dirname(__file__), "./"))
from utils import label_map_util
from utils import visualization_utils as vis_util

app = Flask(__name__)

@app.before_first_request
def get_model():
    """

    :return:
    """
    # What model to download.
    # PATH_TO_CKPT = 'D:/giant/models/object_detection/checkpoint/ssd_mobilenet_v1_coco_11_06_2017/frozen_inference_graph.pb'
    PATH_TO_CKPT = 'D:/giant/models/object_detection/checkpoint/rfcn_resnet101_coco_11_06_2017/frozen_inference_graph.pb'

    # List of the strings that is used to add correct label for each box.
    PATH_TO_LABELS = os.path.join('./data', 'mscoco_label_map.pbtxt')
    NUM_CLASSES = 90
    global detection_graph
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    global category_index
    category_index = label_map_util.create_category_index(categories)

    global sess
    # with detection_graph.as_default():
    #     # with tf.Session(graph=detection_graph) as sess:
    sess = tf.Session(graph=detection_graph)
    # sess.run(tf.global_variables_initializer())

    global image_tensor
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
    global detection_boxes
    detection_boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
    global detection_scores
    detection_scores = detection_graph.get_tensor_by_name('detection_scores:0')
    global detection_classes
    detection_classes = detection_graph.get_tensor_by_name('detection_classes:0')
    global num_detections
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')



def load_image_into_numpy_array(image):
    """
    load image into numpy array
    :param image:
    :return:
    """
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
           (im_height, im_width, 3)).astype(np.uint8)


def get_box(box_xy, image):
    """
    :param box_xy:
    :param image:
    :return: box
    """
    box = []
    (im_width, im_height) = image.size
    left = box_xy[1] * im_width
    box.append(int(left))
    right = box_xy[3] * im_width
    box.append(int(right))
    top = box_xy[0] * im_height
    box.append(int(top))
    bottom = box_xy[2] * im_height
    box.append(int(bottom))
    return box


def get_class_box(boxes, scores, classes, num, image):
    """
    :param boxes:
    :param scores:
    :param classes:
    :param num:
    :param image:
    :return:
    """
    object_list = []
    for i, category_num in zip(range(int(num)), classes):
        object = {}
        box = []
        if scores[i] > 0.7:
            box = get_box(boxes[i], image)
            category_name = category_index[category_num]['name']
            object['name'] = category_name
            object['scores'] = int(scores[i]*100)
            object['box'] = str(box)
            object_list.append(object)
    return object_list


def detection(url):
    """
    :param url:
    :return:
    """

    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    print (image.size)

    image_np = load_image_into_numpy_array(image)

    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    # print(image_np_expanded.shape, type(image_np_expanded))
    # print(image_np_expanded)
    # Actual detection.
    (boxes, scores, classes, num) = sess.run(
        [detection_boxes, detection_scores, detection_classes, num_detections],
        feed_dict={image_tensor: image_np_expanded})
    object_list = get_class_box(np.squeeze(boxes),
                                np.squeeze(scores),
                                np.squeeze(classes).astype(np.int32),
                                num,
                                image)

    # return object_list

    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
                                                        image_np,
                                                        np.squeeze(boxes),
                                                        np.squeeze(classes).astype(np.int32),
                                                        np.squeeze(scores),
                                                        category_index,
                                                        use_normalized_coordinates=True,
                                                        min_score_thresh=.6,
                                                        line_thickness=2)
    # IMAGE_SIZE = (12, 8)
    # plt.figure(figsize=IMAGE_SIZE)
    # plt.imshow(image_np)
    # plt.show()
    return image_np, object_list

@app.route("/detection", methods=['GET', 'POST'])
def server():
    """

    :return:
    """
    params = request.args
    if 'url' in params and 'show' in params:
        if params['show'] == '0':
            url = params['url']
            data = {}
            image, object_list = detection(url)
            data['object'] = object_list
            return jsonify(data)
        else:
            import base64
            url = params['url']
            image, object_list = detection(url)
            img = Image.fromarray(image, 'RGB')
            print(img.size)
            out = BytesIO()
            img.save(out, 'PNG')
            out = base64.b64encode(out.getvalue()).decode('ascii')
            return render_template('index.html',
                                   img_stream=out)

    else:
        return 'error params!'




if __name__ == '__main__':
    app.run(port=8002, debug=True, use_reloader=False)