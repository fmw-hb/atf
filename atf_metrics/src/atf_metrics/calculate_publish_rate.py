#!/usr/bin/env python
import rospy
import math

class CalculatePublishRateParamHandler:
    def __init__(self):
        """
        Class for returning the corresponding metric class with the given parameter.
        """
        pass

    def parse_parameter(self, testblock_name, params):
        """
        Method that returns the metric method with the given parameter.
        :param params: Parameter
        """
        metrics = []
        if type(params) is not list:
            rospy.logerr("metric config not a list")
            return False

        for metric in params:
            # check for optional parameters
            try:
                groundtruth = metric["groundtruth"]
                groundtruth_epsilon = metric["groundtruth_epsilon"]
            except (TypeError, KeyError):
                #rospy.logwarn_throttle(10, "No groundtruth parameters given, skipping groundtruth evaluation for metric 'publish_rate' in testblock '%s'"%testblock_name)
                groundtruth = None
                groundtruth_epsilon = None
            metrics.append(CalculatePublishRate(metric["topic"], groundtruth, groundtruth_epsilon))
        return metrics

class CalculatePublishRate:
    def __init__(self, topic, groundtruth, groundtruth_epsilon):

        self.started = False
        self.finished = False
        self.active = False
        self.groundtruth = groundtruth
        self.groundtruth_epsilon = groundtruth_epsilon
        if topic.startswith("/"): # we need to use global topics because rostopic.get_topic_class(topic) can not handle non-global topics and recorder will always record global topics starting with "/"
            self.topic = topic
        else:
            self.topic = "/" + topic

        self.counter = 0
        self.start_time = None
        self.stop_time = None

    def start(self, timestamp):
        #print "--> publish rate start"
        self.start_time = timestamp
        self.active = True
        self.started = True

    def stop(self, timestamp):
        #print "--> publish rate stop"
        self.stop_time = timestamp
        self.active = False
        self.finished = True

    def pause(self, timestamp):
        # TODO: Implement pause time and counter calculation
        #FIXME: check rate calculation in case of pause (counter, start_time and stop_time)
        pass

    def purge(self, timestamp):
        # TODO: Implement purge as soon as pause is implemented
        pass

    def update(self, topic, msg, t):
        if self.active:
            if topic == self.topic:
                self.counter += 1

    def get_topics(self):
            return []

    def get_result(self):
        groundtruth_result = None
        details = {"topic": self.topic}
        if self.started and self.finished: #  we check if the testblock was ever started and stoped
            data = round(self.counter / (self.stop_time - self.start_time).to_sec(), 3)
            if self.groundtruth != None and self.groundtruth_epsilon != None:
                if math.fabs(self.groundtruth - data) <= self.groundtruth_epsilon:
                    groundtruth_result = True
                else:
                    groundtruth_result = False
            return "publish_rate", data, groundtruth_result, self.groundtruth, self.groundtruth_epsilon, details
        else:
            return False