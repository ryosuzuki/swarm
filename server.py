import base64
import os
import sys
import json
import time
import random

import numpy as np
import tornado
from tornado import websocket, web, ioloop

import cv2
from cv2 import aruco

fps = 1

dictionary_name = aruco.DICT_4X4_50
dictionary = aruco.getPredefinedDictionary(dictionary_name)

parameters = aruco.DetectorParameters_create()

# Thresholding
parameters.adaptiveThreshWinSizeMin = 3 # >= 3
parameters.adaptiveThreshWinSizeStep = 10 # 10
parameters.adaptiveThreshConstant = 7 # 7

# Contour Filtering
parameters.minMarkerPerimeterRate = 0.03 # 0.03
parameters.maxMarkerPerimeterRate = 0.1 # 4.0
parameters.minCornerDistanceRate = 0.2 # 0.05
parameters.minMarkerDistanceRate = 0.3 # 0.05
parameters.minDistanceToBorder = 5 # 3

# Bits Extraction
parameters.markerBorderBits = 1 # 1
parameters.minOtsuStdDev = 5.0 # 5.0
parameters.perspectiveRemoveIgnoredMarginPerCell = 0.4 # 0.13
# parameters.perpectiveRemovePixelPerCell = 10 # 4

# Marker Identification
parameters.maxErroneousBitsInBorderRate = 0.6 # 0.35
parameters.errorCorrectionRate = 2.8 # 0.6


class HttpHandler(web.RequestHandler):
  def get(self):
    self.render('./index.html')

class SocketHandler(websocket.WebSocketHandler):
  def initialize(self):
    self.state = True

  def open(self):
    self.cap = cv2.VideoCapture(0)
    self.cap.set(cv2.CAP_PROP_FPS, fps)
    w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(self.request.remote_ip, ': connection opened')
    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.send()

  def send(self):
    period = 1 / fps
    self.ioloop.add_timeout(time.time() + period, self.send)
    if self.ws_connection:
      image = self.capture()
      message = json.dumps({
        'image': image
      })
      self.write_message(message)

  def capture(self):
    ret, frame = self.cap.read()
    corners, ids, rejectedImgPoints = aruco.detectMarkers(frame, dictionary, parameters=parameters)
    frame = aruco.drawDetectedMarkers(frame, corners, ids, borderColor=(0, 0, 255))
    frame = aruco.drawDetectedMarkers(frame, rejectedImgPoints, borderColor=(0, 255, 0))
    frame = cv2.resize(frame, (int(frame.shape[1]/2), int(frame.shape[0]/2)))
    ret, buffer = cv2.imencode('.jpg', frame)
    data = base64.b64encode(buffer).decode('utf-8')
    return data
    # cv2.imshow('Edited Frame', frame)
    # print('capture')

  def on_close(self):
    self.cap.release()
    cv2.destroyAllWindows()
    self.state = False
    self.close()
    print(self.request.remote_ip, ': connection closed')

  def check_origin(self, origin):
    return True

def main():
  app = tornado.web.Application([
    (r'/', HttpHandler),
    (r'/ws', SocketHandler),
  ], static_path='static')
  print('start web server at localhost:8080')
  app.listen(8080)
  tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
  main()
