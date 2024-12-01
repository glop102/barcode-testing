import treepoem
img = treepoem.generate_barcode(
    # "qrcode",
    "datamatrix",
    "Sample Data - 1 2 3 4",
    scale=8,
)
print("saving to sample.png")
img.save("sample.png")