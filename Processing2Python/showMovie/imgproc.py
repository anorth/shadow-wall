#!/usr/bin/env python
import itertools

from showMovie.defish import create_fisher
import cv2
import numpy as np
from showMovie.helperFunctions import make_gamma_table
from perspective_transform import four_point_transform

THRESHOLD = int(255 * 0.7)
MIN_CONTOUR_AREA = 10

# Observed framing of the camera I used
right_crop = 178+10
left_crop = 216+10
diameter = 1920 - (left_crop + right_crop)
vshift = 40
top_margin = ((diameter - 1080) / 2) + vshift
bottom_margin = ((diameter - 1080) / 2) - vshift

gammatable = np.array(make_gamma_table(0.7), dtype=np.uint8)

class Pipeline(object):
    def __init__(self, defish, crop=(), bg=None):
        """
        :param defish: whether to defish
        :param crop: (width, height) for bottom-centre crop
        """
        assert not (defish and crop)
        if defish:
            self.defisher = create_fisher((diameter,diameter), (1080,1080))
        else:
            self.defisher = None
        self.crop = crop
        self.bg = bg
        self.prev_grey_img = None
        self.flowstate = None

    def process(self, img):
        shape = img.shape

        if self.crop:
            xmargin = shape[1] - self.crop[0]
            ymargin = shape[0] - self.crop[1]
            croprect = slice(ymargin, shape[0]), slice(xmargin/2, shape[1]-xmargin/2)
        else:
            croprect = slice(0, shape[0]), slice(0, shape[1])

        # Crop as early as possible for performance. We might downsize as well if needed.
        img = img[croprect[0], croprect[1]]

        #these coords need tweaking....currently dep on shape of img from movie
        #nats perspective transform:
        # pts = np.array([(0,200), (640, 200), (500, 426), (140, 426)], dtype = "float32")
        # img = four_point_transform(img, pts)

        # Simplify to grayscale for processing
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        is_color = False

        if self.bg:
            img = self.bg.process(img)

        if self.defisher:
            img = img[0:1080, left_crop:-right_crop]
            img = cv2.copyMakeBorder(img, top_margin, bottom_margin, 0, 0, cv2.BORDER_CONSTANT)
            # cv2.imwrite("border.jpg", img)

            img = self.defisher.unwarp(img)
            # cv2.imwrite("defished.jpg", img)
            img = cv2.resize(img, (img.shape[1]/2, img.shape[0]/2))

        ### Analysis (in greyscale)
        img = morph_cleanup(img)
        contours = find_contours(img)

        # brighter = cv2.LUT(img, gammatable)
        # img = brighter
        # self.flowstate, flowimg = compute_flow(self.prev_grey_img, img, self.flowstate)
        # self.prev_grey_img = img
        # if flowimg is not None:
        #     img = flowimg
        #     is_color = True

        ### Drawing (in colour)
        if not is_color:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        # draw_contours(img, contours)
        # draw_rectangles(img, contours) #better identifies individual contours - allows to easily detect 'bottom' of contour for future 'moving down the screen'
        # bottom_of_contour(img, contours)

        cv2.imshow("debug", img)
        return img


class BackgroundRejecterMog(object):
    def __init__(self):
        # length_history = 100
        # number_gaussian_mixtures = 6
        # background_ratio = 0.9
        # noise_strength_sigma = 1
        self.fgbg = cv2.BackgroundSubtractorMOG()#history=200, nmixtures=6, backgroundRatio=0.1, noiseSigma=1)

    def process(self, frame):
        fgmask = self.fgbg.apply(frame)
        cv2.imshow("bg", fgmask)
        frame = frame & fgmask
        return frame

class BackgroundRejecterAvg(object):
    def __init__(self, frame=None):
        self.avg = np.float32(frame) if frame else None

    def process(self, frame):
        if self.avg is None:
            self.avg = np.float32(frame)

        cv2.accumulateWeighted(frame, self.avg, 0.003)
        res = cv2.convertScaleAbs(self.avg)
        cv2.imshow("bg", res)

        # Method 1: reject by subtraction. Avoids hard boundaries, only works well when background is dark.
        res = np.minimum(res, frame)
        frame = frame - res

        # Method 2: reject by masking. Leaves more information but creates hard "glow" boundaries at threshold
        # mask = np.abs(frame - res) > 10
        # frame = np.where(mask, frame, 0)
        return frame

def morph_cleanup(img):
    ### Morphological cleanup
    # http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html
    # http://stackoverflow.com/questions/29104091/morphological-reconstruction-in-opencv
    morph_kernel = np.ones((3, 3), np.uint8)

    # img = cv2.erode(img, morph_kernel)
    # img = cv2.dilate(img, morph_kernel)

    # Morph open to remove noise
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, morph_kernel, iterations=2)

    # Morph close to fill dark holes
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, morph_kernel, iterations=3)
    return img

def find_contours(img):
    #when doing edge detection, remove/denoise image first, then apply Canny
    # img = cv2.GaussianBlur(img, (5, 5), 0)
    # edges = cv2.Canny(img, 100, 200)

    # Contours appropriate for filling with colour
    edges = cv2.Canny(img, 20, 40)
    edges = cv2.GaussianBlur(edges, (5, 5), 0) #consider blurring again, after edge detection

    contours, hchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return contours

def compute_flow(previmg, img, prevflow):
    pyramidScale = 0.5 # 0.5 is each layer half the size
    pyramidLevels = 3
    windowSize = 10 # higher is faster, robust, blurrier
    iterations = 3
    polySize = 5 # typically 5 or 7
    polySigma = 1.2 # suggested 5->1.1, 7->1.5
    gaussian = False

    if previmg is None:
        return None, None

    flags = 0
    if gaussian:
        flags |= cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    if prevflow is not None:
        flags |= cv2.OPTFLOW_USE_INITIAL_FLOW

    flow = cv2.calcOpticalFlowFarneback(previmg, img,
        pyramidScale, pyramidLevels, windowSize, iterations,
        polySize, polySigma, flags, prevflow)

    magMax = 8
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    mag = np.clip(mag, 0, magMax)

    hsv = np.zeros(img.shape+(3,), 'uint8')
    hsv[..., 0] = ang * 180 / np.pi / 2  # hue is angle
    hsv[..., 1] = 255  # full saturation
    hsv[..., 2] = mag * (255 / magMax)  # value is magnitude
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return flow, rgb

def draw_contours(img, contours):
    # Draw and fill all contours
    # cv2.drawContours(img, contours, -1, (0, 255, 0), -1)
    colors = itertools.cycle(itertools.product(*([(0, 255)] * 3)))
    for i, c in enumerate(contours):
        cv2.drawContours(img, contours, i, next(colors), -1)

def local_max(img):
    kernel = np.ones((40, 40), np.uint8)
    mask = cv2.dilate(img, kernel)
    result = cv2.compare(img, mask, cv2.CMP_GE)
    return result

def draw_rectangles(img, contours):
    #draw the bounding rectangles around contours
    for i, ctr in enumerate(contours):
        x, y, w, h = cv2.boundingRect(ctr)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

def bottom_of_contour(img, contours):
    bottom_x = []
    bottom_y = []
    #get the bounding rectangles around contours
    for i, ctr in enumerate(contours):
        x, y, w, h = cv2.boundingRect(ctr)
        bottom_x.append(x + w/2)
        bottom_y.append(y + h)
        cv2.circle(img,(int(bottom_x[i]),int(bottom_y[i])),3,(255,0,0))

    return zip(bottom_x, bottom_y)
