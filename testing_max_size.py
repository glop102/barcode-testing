import treepoem
from random import randrange

def generate_barcode(datalength:int):
    img = treepoem.generate_barcode(
        "qrcode",
        # "datamatrix",
        # randrange is the capital letters
        bytes([randrange(65,90) for _ in range(datalength)]),
        scale=8,
        options={"eclevel":"H"}
    )
    return img

low = 0
high = 256
#Initial Hydrate of finding the top end
try:
    while True:
        print(f"Up to {high}")
        generate_barcode(high)
        high+= 256
        low += 256
except:
    #We found some sort of max, so we can now back off and find the actual limit
    pass

#Now bisect the range to find the max
while low < high-1:
    diff = high-low
    middle = (diff//2)+low
    # always push the limit us for us testing
    if middle == low:
        middle+=1
    try:
        print(f"Attempting {middle}  ({low}/{high})")
        img = generate_barcode(middle)
        #Was able to make it, so the limit is probably higher and where we are is the new minimum
        low = middle
    except:
        #Failed, so the limit is probably below here
        high = middle

print(f"{low} seems to be the largest size we can generate for")
img.save("sample.png")