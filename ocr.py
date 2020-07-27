import pytesseract as tess
import cv2

# TODO BW + high contrast will be the most reliable way to get the most readable text
# TODO train model on Electrolize font
# TODO split image into 4 parts - title / score / tp / judge breakdown
# TODO compare song title against the list of songs scraped from ct2v 

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
config = "--psm 12 -l eng+chi_sim+chi_tra+jpn"

#img = cv2.imread('c2ocrtest.png')
#img = cv2.imread('c2nobgtest.png')
img = cv2.imread('scores_without_share/c2phonetest.jpg', cv2.IMREAD_GRAYSCALE)

img = cv2.resize(img, (1920, 1080))
#(thresh, img) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)

alpha, beta = 1.2, 50

img = cv2.convertScaleAbs(img, alpha = alpha, beta = beta)

#cv2.imwrite('test.jpg', img)

TITLE_START_X, TITLE_END_X, TITLE_START_Y, TITLE_END_Y = 480, 1450, 0, 150
SCORE_START_X, SCORE_END_X, SCORE_START_Y, SCORE_END_Y = 140, 630, 480, 600
TP_START_X, TP_END_X, TP_START_Y, TP_END_Y = 860, 1060, 550, 650
JUDGE_START_X, JUDGE_END_X, JUDGE_START_Y, JUDGE_END_Y = 625, 1115, 925, 1050

title = img[TITLE_START_Y: TITLE_END_Y, TITLE_START_X:TITLE_END_X].copy()
score = img[SCORE_START_Y: SCORE_END_Y, SCORE_START_X:SCORE_END_X].copy()
tp = img[TP_START_Y: TP_END_Y, TP_START_X:TP_END_X].copy()
judge = img[JUDGE_START_Y: JUDGE_END_Y, JUDGE_START_X:JUDGE_END_X].copy()

def show_output(img, gray = False):
    if gray:
        height, width = img.shape
    else:
        height, width, _ = img.shape

    data = tess.image_to_data(img, config = config)

    for i, line in enumerate(data.splitlines()):
        if i != 0:
            line = line.split("\t")
            print(line)

            if len(line) == 12:
                x, y, char_w, char_h = int(line[6]), int(line[7]), int(line[8]), int(line[9])
                cv2.rectangle(img, (x, y), (char_w + x, char_h + y), (0, 0, 255), 3)
                cv2.putText(img, line[11], (x, y), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow('Result with blocks', img)
    cv2.waitKey(0)

show_output(judge, gray = True)