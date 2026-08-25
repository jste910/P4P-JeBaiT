CAPSNETEXE = "./bin/capsnet_full.exe"
CONV1EXE = "./bin/conv1.exe"
CONV2DEXE = "./bin/primaryCaps_conv2d.exe"
PRIMARYSQUASHEXE = "./bin/primarySquash.exe"
DIGITCAPSEXE = "./bin/digitcaps.exe"
LENGTHEXE = "./bin/length.exe"

PARTIALCAPSMODEL = "model/partial_caps.xmodel"
CONV1MODEL = "model/conv1.xmodel"
CONV2DMODEL = "model/primarycap_conv2d.xmodel"

XCLBIN = "../dpu.xclbin"
IMG_PATH = "img/MNIST/t10k-images-idx3-ubyte"
WEIGHTS_PATH = "weights/new_digitcaps_weights.txt"
images = "50"
LABEL_PATH = "img/MNIST/t10k-labels-idx1-ubyte"
RERUN = "1"

fullcapsoutput = "intermediate_results/full_capsnet_0.85V"

conv1folder = "intermediate_results/conv1_0.85V"
primarycapsfolder = "intermediate_results/primarycaps_0.85V"
squashfolder = "intermediate_results/squash_0.85V"
digitcapsfolder = "intermediate_results/digitcaps_0.85V"
lengthfolder = "intermediate_results/length_0.85V"

conv2dtxt = "convolutional_output.txt"
primarycapstxt = "primarycaps_output.txt"
primarysquashtxt = "primary_squash_output.txt"
digitcapstxt = "digitcaps_output.txt"



capsnetfull = f"{CAPSNETEXE} {PARTIALCAPSMODEL} {XCLBIN} {IMG_PATH} {WEIGHTS_PATH} {images} {LABEL_PATH} {RERUN} {fullcapsoutput}"
conv1 = f"{CONV1EXE} {CONV1MODEL} {IMG_PATH} {images} {conv1folder} {RERUN}"
primaryCaps = f"{CONV2DEXE} {CONV2DMODEL} {conv1folder} {images} {primarycapsfolder} {conv2dtxt} {RERUN}"
primarySquash = f"{PRIMARYSQUASHEXE} {XCLBIN} {primarycapsfolder} {images} {squashfolder} {primarycapstxt} {RERUN}"
digitCaps = f"{DIGITCAPSEXE} {XCLBIN} {WEIGHTS_PATH} {squashfolder} {images} {digitcapsfolder} {primarysquashtxt} {RERUN}"
length = f"{LENGTHEXE} {XCLBIN} {digitcapsfolder} {images} {lengthfolder} {digitcapstxt} {RERUN}"









print(capsnetfull)
print(conv1)
print(primaryCaps)
print(primarySquash)
print(digitCaps)
print(length)


