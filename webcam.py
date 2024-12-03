from threading import Thread,Event,Lock
from typing import Any, Callable
from PIL.Image import Image, Transform
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
import av
import math
import time
import traceback
import zxingcpp

class PillowDisplay(QLabel):
    def setPillow(self,img):
        pixmap = self.__pillow_to_pixmap(img)
        self.setPixmap(pixmap)
    def __pillow_to_pixmap(self,img:Image) -> QPixmap:
        imgdata = img.tobytes()
        match img.mode:
            case "RGB":
                qimage = QImage(
                    imgdata,
                    img.width,
                    img.height,
                    img.width*3,
                    QImage.Format.Format_RGB888
                )
            case "RGBA":
                qimage = QImage(
                    imgdata,
                    img.width,
                    img.height,
                    img.width*4,
                    QImage.Format.Format_RGBA8888
                )
            case "L":
                qimage = QImage(
                    imgdata,
                    img.width,
                    img.height,
                    img.width,
                    QImage.Format.Format_Grayscale8
                )
            case  _:
                print("Unknown image format {}, converting to RGB as a fallback".format(img.mode))
                img = img.convert("RGB")
                qimage = QImage(
                    imgdata,
                    img.width,
                    img.height,
                    img.width*3,
                    QImage.Format.Format_RGB888
                )
        return QPixmap(qimage)

class BarcodeParser(QObject):
    # Isolated barcode image segments and time taken to scan the image and return the barcodes
    foundBarcodeResults = Signal(Image,list,float)
    _thread:Thread
    _stopflag:Event
    _imageAvailToParse:Event
    _imgBufferLock:Lock
    _imgBuffer:Image

    parserForBarcodes:Callable[[Image],list[Any]]

    def __init__(self,parsingFunction:Callable[[Image],list[Any]]):
        super().__init__()
        self._thread = Thread(target=self._thread_worker)
        self._stopflag = Event()
        self._imageAvailToParse = Event()
        self._imgBufferLock = Lock()
        self._imgBuffer = None

        self.parserForBarcodes = parsingFunction

        self._thread.start()

    def _thread_worker(self):
        while True:
            self._imageAvailToParse.wait()
            if self._stopflag.is_set():
                break
            with self._imgBufferLock:
                img = self._imgBuffer.copy()
                self._imgBuffer = None
            self._imageAvailToParse.clear()

            start = time.perf_counter()
            try:
                barcode_results:list[Any] = self.parserForBarcodes(img)
            except:
                barcode_results = []
            end = time.perf_counter()

            self.foundBarcodeResults.emit(img,barcode_results,end-start)
    
    def askForImageParsing(self,img:Image):
        with self._imgBufferLock:
            self._imgBuffer = img
        self._imageAvailToParse.set()
    def stop(self):
        self._stopflag.set()
        self._imageAvailToParse.set()

class ZXingCppParser(BarcodeParser):
    def __init__(self):
        super().__init__(zxingcpp.read_barcodes)
class ZXingCppDisplay(QWidget):
    _parser:ZXingCppParser
    _barcode_type:QLabel
    _barcode_duration:QLabel
    _barcode_text:QLabel
    _barcode_position:QLabel
    _barcode_orientation:QLabel
    _barcode_image:PillowDisplay

    def __init__(self):
        super().__init__()
        self._barcode_type = QLabel()
        self._barcode_duration = QLabel()
        self._barcode_text = QLabel()
        self._barcode_position = QLabel()
        self._barcode_orientation = QLabel()
        self._barcode_image = PillowDisplay()
        l = QVBoxLayout()
        self.setLayout(l)
        l.addWidget(self._barcode_type)
        l.addWidget(self._barcode_duration)
        l.addWidget(self._barcode_text)
        l.addWidget(self._barcode_position)
        l.addWidget(self._barcode_orientation)
        l.addWidget(self._barcode_image)

        self._parser = ZXingCppParser()
        self._parser.foundBarcodeResults.connect(self.displayResults)
    def scanForBarcodes(self,img:Image):
        self._parser.askForImageParsing(img)
    def displayResults(self,originalImg:Image,results:list[zxingcpp.Result],delta_s:float):
        self._barcode_duration.setText(f"{delta_s*1000:.2f} ms")
        if len(results) == 0:
            return
        self._barcode_type.setText(str(results[0].format))
        self._barcode_text.setText(results[0].text)
        self._barcode_position.setText(str(results[0].position))
        self._barcode_orientation.setText(str(results[0].orientation))
        position = results[0].position

        def dist_between_points(p1:zxingcpp.Point,p2:zxingcpp.Point):
            dx = p1.x-p2.x
            dy = p1.y-p2.y
            return math.sqrt((dx*dx)+(dy*dy))
        longest_side = max([
            dist_between_points(position.top_left,position.top_right),
            dist_between_points(position.top_right,position.bottom_right),
            dist_between_points(position.bottom_right,position.bottom_left),
            dist_between_points(position.bottom_left,position.top_left),
        ])
        longest_side = int(longest_side)

        subimg = originalImg.transform(
            size = (longest_side,longest_side),
            method = Transform.QUAD,
            data = [
                position.top_left.x,position.top_left.y,
                position.top_right.x,position.top_right.y,
                position.bottom_right.x,position.bottom_right.y,
                position.bottom_left.x,position.bottom_left.y,
            ]
        )
        self._barcode_image.setPillow(subimg)

class WebcamDisplay(PillowDisplay):
    newFrame = Signal(Image)
    _parsingThread:Thread
    _stopflag:Event

    def __init__(self):
        super().__init__()
        self._parsingThread = Thread(target=self._threadedVideoDecoder)
        self._stopflag = Event()
        self.newFrame.connect(self.setPillow)
        self._parsingThread.start()

    def _threadedVideoDecoder(self):
        container = av.open("/dev/video0",format="v4l2")
        decoder_generator = container.decode()
        while not self._stopflag.is_set():
            frame = decoder_generator.__next__()
            img = frame.to_image()
            self.newFrame.emit(img)
    def stop(self):
        self._stopflag.set()

app = QApplication()
window = QMainWindow()
window.show()
center = QWidget()
window.setCentralWidget(center)
center_layout = QHBoxLayout()
center.setLayout(center_layout)

webcam = WebcamDisplay()
center_layout.addWidget(webcam)
# My little laptop runs this on my webcam in about 8-10 ms
parser = ZXingCppDisplay()
webcam.newFrame.connect(parser.scanForBarcodes)
center_layout.addWidget(parser)

app.exec()
webcam.stop()
parser._parser.stop()