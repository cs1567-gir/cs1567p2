#!/usr/bin/env python
import math
import cv2
import cv_bridge
import rospy
import numpy
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import *
from cs1567p2.msg import *

class RobotLocation():
    def __init__(self, color):
        self.location = Location()
        self.valid = False
        self.location.robot_num = color

    def set_location(self, x, y, theta):
        self.location.x = x
        self.location.y = y
        self.location.theta = theta


locpub = None
pubs = []
kinect_masks = [Image(), Image(), Image()]
robots = None


######## COLOR DEFINITIONS ####################################

lower_blue = numpy.array([100,40,200])
upper_blue = numpy.array([120,130,255])

#lower_orange = numpy.array([20, int(0.4*255), int(.8*255)])
#upper_orange = numpy.array([50, int(1.00*255), int(1.0*255)])

lower_orange = numpy.array([15, int(0.06*255), int(.8*255)])
upper_orange = numpy.array([28, int(0.88*255), int(1.0*255)])

lower_purple = numpy.array([115, int(0.2*255), int(0.6*255)])
upper_purple = numpy.array([135, int(0.9*255), int(1.0*255)])

lower_red = numpy.array([150, int(0.15*255), int(0.80*255)])
upper_red = numpy.array([180, int(0.6*255), int(1.0*255)])

color_mask_list = [[lower_blue, upper_blue],[lower_orange, upper_orange], [lower_purple, upper_purple], [lower_red, upper_red]]
blobs_by_color = [ [[],[],[],[]],
                   [[],[],[],[]],
                   [[],[],[],[]] ]

color_string_list = ['BLUE', 'ORANGE', 'PURPLE', 'RED']


########  GLOBAL CONSTANTS #####################################

KINECT1 = 0
KINECT2 = 1
KINECT3 = 2

MIN_BLOB_SIZE = 250
MAX_BLOB_SIZE = 500
MAX_BLOB_DISTANCE = 40

NUM_ROBOTS = len(color_mask_list) - 1

K1_REAL_OFFSET = (0.0, 0.0)
K2_REAL_OFFSET = (0.2147, -1.156)
K3_REAL_OFFSET = (0.157, 0.8692)

ORIGIN_OFFSETS = [K1_REAL_OFFSET, K2_REAL_OFFSET, K3_REAL_OFFSET]
INVERT_Y = -1

########  CALLBACKS  ##########################################

def mask_image_and_update(message, camera):
    global color_mask_list
    global kinect_masks
    global threshold
    global pubs
    global blobs_by_color
    masks = [] # list of our binary masked images by color (from color list)
    bridge = cv_bridge.CvBridge()	# CvBridge
    cv_image = bridge.imgmsg_to_cv2(message, "bgr8")
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)  # convert to HSV colorspace
    for color in color_mask_list:			# for each color, generate a mask
        mask = cv2.inRange(hsv, color[0], color[1])
        mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2,2)))
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2,2)))
        masks.append(mask)
    multi_mask = masks[0]				# create a multiple-color mask for viewing if necessary
    for x in range(len(masks)):					# populate the multi-color mask
        blobs_by_color[camera][x] = []
        multi_mask = cv2.bitwise_or(multi_mask, masks[x])
        contours,hierarchy = cv2.findContours(masks[x],cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            M = cv2.moments(cnt)
            area = cv2.contourArea(cnt)
            if area > MIN_BLOB_SIZE and area < MAX_BLOB_SIZE: 
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                blobs_by_color[camera][x].append((cx, cy))
                #print color_string_list[x], " blob at x: ", cx, ' y: ', cy
    res = cv2.bitwise_and(cv_image,cv_image, mask= multi_mask)
    kinect_masks[camera] = bridge.cv2_to_imgmsg(res, "bgr8")    
    pubs[camera].publish(kinect_masks[camera]) #publish the mask for viewing
    update_robots(camera)
    print "done", camera
    


def k1_image_callback(message):
    mask_image_and_update(message, KINECT1)
        
def k2_image_callback(message):
    mask_image_and_update(message, KINECT2)

def k3_image_callback(message):
    mask_image_and_update(message, KINECT3)


################## UTILITY FUNCTIONS ####################################

def get_distance(base_x, base_y, point_x, point_y):
    distance = math.sqrt((point_x - base_x)**2 + (point_y - base_y)**2)
    return distance

def get_heading(base_x, base_y, point_x, point_y):
    distance = get_distance(base_x, base_y, point_x, point_y)
    theta = 0.0
    if distance != 0:
        theta = math.degrees(math.asin((point_y - base_y)/distance))
        if point_x < base_x:
            theta = math.degrees(math.acos((point_x - base_x)/distance))
            if point_y < base_y:
                theta = 360.0 - theta
    return theta

def pixels_to_real_offset(x, y):
    x_pixel_offset = x - 320.0
    real_x = 0.0049294111 * x_pixel_offset - 0.0001978074
    y_pixel_offset = y - 240
    real_y = 0.004981428 * y_pixel_offset + 0.0040695362
    return (real_x, real_y)

def update_robots(camera):
    global robots
    global locpub
    locations = []
    points_of_interest = []
    real_points = []
    pair_colors = []
    n = len(blobs_by_color[camera])
    for red_blob in blobs_by_color[camera][n-1]:
        for i in range(n-1):
            for base_blob in blobs_by_color[camera][i]:
                distance = get_distance(base_blob[0], base_blob[1], red_blob[0], red_blob[1])      
                if distance < MAX_BLOB_DISTANCE:
                    print "FOUND PAIR: ", color_string_list[i]
                    x, y = pixels_to_real_offset(base_blob[0], base_blob[1])
                    point_x, point_y = pixels_to_real_offset(red_blob[0], red_blob[1])
                    #print "before origin offsets: ", x, y, point_x, point_y
                    x -= ORIGIN_OFFSETS[camera][0]
                    point_x -= ORIGIN_OFFSETS[camera][0]
                    y -= ORIGIN_OFFSETS[camera][1]
                    y *= INVERT_Y
                    #print "Y offset: ", ORIGIN_OFFSETS[camera][1]
                    point_y -= ORIGIN_OFFSETS[camera][1]
                    point_y *= INVERT_Y
                    theta = get_heading(x, y, point_x, point_y)
                    #print "(", x, ",", y, ") (", point_x, ",", point_y, ") ", theta
                    robots[i].set_location(x, y, theta)                    
                    robots[i].valid = True
    for robot in robots:
        locations.append(robot.location)
    locpub.publish(locations)


########  INITIALIZATION ########################################

def initialize():
    global pubs
    global locpub
    global robots
    robots = []
    for i in range(len(color_mask_list)-1):
        robots.append(RobotLocation(i))

    rospy.init_node("gort_localize")
    locpub = rospy.Publisher("/gort/location",LocationList) #publish your locations
    pubs.append(rospy.Publisher("/gort/mask1",Image))
    pubs.append(rospy.Publisher("/gort/mask2",Image))
    pubs.append(rospy.Publisher("/gort/mask3",Image))
    rospy.Subscriber("/kinect3/rgb/image_color", Image, k3_image_callback, queue_size=1)
    rospy.Subscriber("/kinect2/rgb/image_color", Image, k2_image_callback, queue_size=1)
    rospy.Subscriber("/kinect1/rgb/image_color", Image, k1_image_callback, queue_size=1)
    rospy.spin()

if __name__ == "__main__":
    initialize()

