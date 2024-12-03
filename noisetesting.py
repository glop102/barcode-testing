from functools import partial
from threading import Thread
from typing import Callable
from PIL.Image import Image, frombytes
from PIL.Image import new as ImageNew
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from random import random,uniform
import math
import time
import traceback
import treepoem
import zxingcpp

wanted_codetypes = [
    "datamatrix",
    "qrcode",
]
times_to_scan:list[float] = []

def create_base_matrices(encodings:list[tuple[str,str]])->list[Image]:
    """
    List of (data to encode,barcodetype)
    """
    imgs = []
    for data,codetype in encodings:
        try:
            img = treepoem.generate_barcode(codetype,data,scale=4)
            img = img.convert("RGB")
        except:
            traceback.print_exc()
            print(f"  ^ {codetype} : {data}")
            continue
        imgs.append(img)
    return imgs

def scan_for_barcodes(img:Image) -> zxingcpp.Result:
    return zxingcpp.read_barcodes(img)

def add_gausian_noise(img:Image,range=30.0)->Image:
    # # https://stackoverflow.com/questions/70780758/how-to-generate-random-normal-distribution-without-numpy-google-interview
    # # second answer is the right one
    # def getrand():
    #     u1 = 1-(random()**tightness)
    #     u2 = 1-(random()**tightness)
    #     return range * math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    def getrand()->float:
        #Box/Muller polar transform
        s = 1.0
        while s >= 1.0:
            u = uniform(-1.0,1.0)
            v = uniform(-1.0,1.0)
            s = (u*u) + (v*v)

        insqrt = (-2 * math.log(s)) / s
        sqrt = math.sqrt(insqrt)
        return u * sqrt
    def getscaledrand()->float:
        r = getrand()
        return r * range
    pixels = [
        min(255,max(0, int(v+getscaledrand())))
        for pixel in img.getdata()
        for v in pixel
    ]
    pixels = bytes(pixels)
    return frombytes(img.mode,img.size,pixels)

def noise_rotate_test_image(image:Image,rot_deg:float) -> tuple[Image,int]:
    # i_over = i_over.rotate(90)
    # for barcode in scan_for_barcodes(i_over):
    #     print("Result:")
    #     print(f"    Text:         {barcode.text}")
    #     print(f"    Valid:        {barcode.valid}")
    #     print(f"    Format:       {barcode.format}")
    #     print(f"    EC Level:     {barcode.ec_level}")
    #     print(f"    Content type: {barcode.content_type}")
    #     print(f"    Position:     {barcode.position}")
    #     print(f"    Orientation:  {barcode.orientation}")
    
    i_noise = add_gausian_noise(image)
    i_rot = i_noise.rotate(rot_deg)
    
    start = time.perf_counter()
    barcodes = scan_for_barcodes(i_rot)
    end = time.perf_counter()
    times_to_scan.append(end-start)
    return (
        i_rot,
            sum([
            b.valid for b in barcodes
        ])
    )

def test_image_full_circle(image:Image, updateCallback:Callable=None) -> tuple[int,float]:
    max_size = max(image.width,image.height)
    half_size = max_size//2
    i_over:Image = ImageNew(
        "RGB",
        (max_size*2,max_size*2),
        (255,255,255)
    )
    i_over.paste(
        image,
        box=(
            half_size,
            half_size,
            half_size+image.width,
            half_size+image.height
        )
    )
    found = 0
    for rot_deg in range(360):
        img_test,count = noise_rotate_test_image(i_over,rot_deg)
        if count == 1:
            found += 1
        if updateCallback:
            updateCallback(img_test)
    return (found,found/360.0)

def save_images_to_gif(filename:str,images:list[Image]):
    print(f"Saving {filename}")
    images[0].save(
        filename,
        save_all=True,
        append_images=images[1:],
        loop=0
    )
    print(f"Finished saving {filename}")

def pillow_to_pixmap(img:Image) -> QPixmap:
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
                img.width*3,
                QImage.Format.Format_RGBA8888
            )
        case "L":
            qimage = QImage(
                imgdata,
                img.width,
                img.height,
                img.width*3,
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

app = QApplication()
window = QMainWindow()
c = QWidget()
l = QVBoxLayout()
c.setLayout(l)
scrollarea = QScrollArea()
scrollarea.setWidget(c)
scrollarea.setWidgetResizable(True)
window.setCentralWidget(scrollarea)
window.show()

imgs = create_base_matrices(
    zip(
        ["data1","data2"],
        wanted_codetypes,
    )
)
imgs[0] = imgs[0].resize(imgs[1].size)
imgs_noised:list[Image] = []

label = QLabel()
l.addWidget(label)
app.processEvents()
app.processEvents()
def update_displayed_image(img:Image):
    imgs_noised.append(img)
    px = pillow_to_pixmap(img)
    label.setPixmap(px)
    app.processEvents()
    app.processEvents()
for i in imgs:
    found,percentage = test_image_full_circle(i,update_displayed_image)
    print(found,"  ",percentage*100,"%")

imgs_datamatrix = imgs_noised[:360]
imgs_qrcode = imgs_noised[360:]
t1 = Thread(
    target=partial(
        save_images_to_gif,
        "/tmp/datamatrix.gif",
        imgs_datamatrix,
    )
)
t2 = Thread(
    target=partial(
        save_images_to_gif,
        "/tmp/qrcode.gif",
        imgs_qrcode,
    )
)
# t1.start()
# t2.start()
print("Scan Times")
print(f"  datamatrix  {min(times_to_scan[:360])*1000:.3f} ms - {max(times_to_scan[:360])*1000:.3f} ms")
print(f"  qrcode      {min(times_to_scan[360:])*1000:.3f} ms - {max(times_to_scan[360:])*1000:.3f} ms")
app.exec()
app.shutdown()
# t1.join()
# t2.join()