Testing scripts and playing with some barcode scanning/generation.

noisetesting.py : generates a small test barcode, then rotates and adds noise to the image before attempting to scan it again. It seems like qrcodes are more robust for getting parsed with the noise than datamatrix.

simple_test_code.py : just makes an image with a barcode in it, saved to sample.png

testing_max_size.py : randomly generates barcodes while doing a size bisection to search for the largest datasize that can be used. Some results are saved in this repo in the example_images folder.

webcam.py : opens the device /dev/video0 and scans for barcodes. The first one it finds in a frame, it will cut out and display on its own on the side. Useful for playing with different conditions to get an intuition of the limits of a barcode.

Requirements:
pillow
pyside6 (for the GUI)
treepoem (for generating parcodes)
zxingcpp (for parsing barcodes)
pyzbar (for parsing barcodes in the webcam.py)
