#!/usr/bin/env python2
#-*- coding: utf-8 -*-

import matplotlib.style
import matplotlib as mpl
mpl.style.use('classic')

from atf_msgs.msg import AtfResult

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


import yaml

import rosbag

import pprint
import re

import numpy as np

from matplotlib import cm

from collections import namedtuple

import argparse

import sys

import time

MetricAggregate = namedtuple('MetricAggregate', 'metric_name testblock_name num min max mean median std data_points')

class DemoPlotter(object):

    def __init__(self):
        self.atf_result = None


    def load_atf_result(self, filename):
        
        bag = rosbag.Bag(filename)
        print "number of files in bag:", bag.get_message_count()
        assert bag.get_message_count() == 1 # check if only one message is in the bag file
            
        for topic, msg, t in bag.read_messages():
            #print type(msg), type(AtfResult()), isinstance(msg, AtfResult) # check if message is an AtfResult message
            #assert isinstance(msg, AtfResult) # check if message is an AtfResult message
            if topic == "atf_result":
                self.atf_result = msg
            else:
                print "ERROR: invalid topic name in bag. ATF only expects topic 'atf_result'"
            bag.close()
            break

    def get_sorted_plot_dicts(self, atf_result, filter_tests, filter_testblocks, filter_metrics):
        tbm = {}
        tmb = {}
        bmt = {}
        mbt = {}

        for test in atf_result.results:
            #print test.name
            if len(filter_tests) != 0 and test.name not in filter_tests:
                continue
            for testblock in test.results:
                #print "  -", testblock.name
                if len(filter_testblocks) != 0 and testblock.name not in filter_testblocks:
                    continue

                for metric in testblock.results:
                    #print "    -", metric.name
                    if len(filter_metrics) != 0 and metric.name not in filter_metrics:
                        continue

                    # tbm
                    if test.name                 not in tbm.keys():
                        tbm[test.name] = {}
                    if testblock.name            not in tbm[test.name].keys():
                        tbm[test.name][testblock.name] = {}
                    tbm[test.name][testblock.name][metric.name] = metric

                    # tmb
                    if test.name                 not in tmb.keys():
                        tmb[test.name] = {}
                    if metric.name               not in tmb[test.name].keys():
                        tmb[test.name][metric.name] = {}
                    tmb[test.name][metric.name][testblock.name] = metric

                    # bmt
                    if testblock.name            not in bmt.keys():
                        bmt[testblock.name] = {}
                    if metric.name               not in bmt[testblock.name].keys():
                        bmt[testblock.name][metric.name] = {}
                    bmt[testblock.name][metric.name][test.name] =  metric

                    # mbt
                    if metric.name            not in mbt.keys():
                        mbt[metric.name] = {}
                    if testblock.name         not in mbt[metric.name].keys():
                        mbt[metric.name][testblock.name] = {}
                    mbt[metric.name][testblock.name][test.name] =  metric

        ret = {}
        ret['tbm'] = tbm
        ret['tmb'] = tmb
        ret['bmt'] = bmt
        ret['mbt'] = mbt
        return ret

    def merge(self):
        pass

    def print_structure(self):
        for test in self.atf_result.results:
            print test.name
            for testblock in test.results:
                print "  -", testblock.name
                for metric in testblock.results:
                    print "    -", metric.name

    def plot_fmw(self, style, filter_tests, filter_testblocks, filter_metrics):

        sorted_atf_results = self.get_sorted_plot_dicts(self.atf_result, filter_tests, filter_testblocks, filter_metrics)

        if style not in sorted_atf_results.keys():
            print "ERROR: style '%s' not implemented"%style
            return
        plot_dict = sorted_atf_results[style]

        rows = plot_dict.keys()
        cols = []
        plots = []
        nr_unique_plots = 0
        for row in rows:
            cols_tmp = plot_dict[row].keys()
            for col in cols_tmp:
                if col not in cols:
                    cols.append(col)
                    for plot in plot_dict[row][col].keys():
                        if plot not in plots:
                            plots.append(plot)
        
        # sort alphabetically
        rows.sort()
        cols.sort()
        plots.sort()

        print "\nplotting in style '%s' (rows: %d, cols: %d, plots: %d)"%(style, len(rows), len(cols), len(plots))
        meanlineprops = dict(linestyle='--', color='purple')
        fig, axs = plt.subplots(len(rows), len(cols), sharex=True, figsize=(20, 15)) # FIXME calculate width with nr_testblocks

        # always make this a numpy 2D matrix to access rows and cols correclty if len(rows)=1 or len(cols)=1
        axs = np.atleast_2d(axs) 
        axs = axs.reshape(len(rows), len(cols)) 

        for row in rows:
            #print "\nrow=", row
            
            
            for col in cols:
                #print "  col=", col

                x = np.arange(len(plots))
                ax = axs[rows.index(row)][cols.index(col)]

                # format x axis
                ax.set_xticks(x)
                ax.set_xticklabels(plots)
                (x_min, x_max) = ax.get_xlim()
                ax.set_xlim(x_min - 0.1, x_max + 0.1)

                y_min = 0
                y_max = 0

                # only set title for upper row and ylabel for left col
                if rows.index(row) == 0:
                    ax.set_title(col)
                if cols.index(col) == 0:
                    ax.set_ylabel(row, rotation=90)

                for plot in plots:
                    #print "    plot=", plot
                    try:
                        metric_result = plot_dict[row][col][plot]
                        #print "found", row, col, plot
                    except KeyError:
                        #print "skip", row, col, plot
                        continue
                    
                    ax.grid(True)
                    nr_unique_plots += 1

                    data = metric_result.data.data
                    lower = metric_result.groundtruth - metric_result.groundtruth_epsilon
                    upper = metric_result.groundtruth + metric_result.groundtruth_epsilon
                    y_min = min(-0.1, data, lower, upper)
                    y_max = max(data, lower, upper)

                    yerr = [[0], [0]]
                    if metric_result.groundtruth_available:
                        yerr = [[data - lower], [upper - data]]
                    ax.errorbar(plots.index(plot), data, yerr=yerr, fmt='D', markersize=12)
                    ax.plot(plots.index(plot), metric_result.min.data, '^', markersize=8)
                    ax.plot(plots.index(plot), metric_result.max.data, 'v', markersize=8)

                # format y axis
                (y_min_auto, y_max_auto) = ax.get_ylim()
                y_min = min (y_min_auto, y_min)
                y_max = max (y_max_auto, y_max)
                ax.set_ylim(y_min - 0.2*abs(y_min), y_max + 0.2*abs(y_max)) # make it a little bigger than the min/max values

        fig.autofmt_xdate(rotation=45)
        plt.tight_layout()

        title = "ATF Result for %s\ntotal # of tests: %d\ntotal # of plots: %d"%("PACKAGE", len(self.atf_result.results), nr_unique_plots)   # replace PACKAGE with self.atf_result.package (needs to be added to message first)
        st = fig.suptitle(title, fontsize="x-large")
        # shift subplots down:
        st.set_y(0.95)
        fig.subplots_adjust(top=0.85)

        fig.savefig("/tmp/test.png")
        plt.show()

        print "DONE plot_fmw"
        return

if __name__ == '__main__':
    # example call could be:
    #   rosrun atf_plotter plot.py plot-metric -m tf_length_translation -tb testblock_circle -t ts0_c0_r0_e0_s0_0 ~/atf_result.txt
    # to get info about the file, this could be helpful:
    #   rosrun atf_plotter plot.py info-structure ~/atf_result.txt

    add_test = lambda sp: sp.add_argument('--test', '-t', type=str, dest='test', default="", help='TBD')
    add_test_case_ident = lambda sp: sp.add_argument('--testident', '-ti', type=str, dest='test_case_ident', required=True, help='like test name without repetition, e.g. ts0_c0_r0_e0_s0')
    add_testblock = lambda sp: sp.add_argument('--testblock', '-tb', type=str, dest='testblock', default="", help='TBD')
    add_metric = lambda sp: sp.add_argument('--metric', '-m', type=str, dest='metric', default="", help='TBD')
    add_style = lambda sp: sp.add_argument('--style', '-s', type=str, dest='style', default='bmt', help='style, e.g. tbm (default) tmb, bmt, ...')


    parser = argparse.ArgumentParser(
        conflict_handler='resolve',
        description='WIP CLI for plotting an atf result in different ways',
        epilog='for more information on sub-commands, type SUB-COMMAND --help')


    subparsers = parser.add_subparsers(help='sub-command help TBD', dest='command')


    sub_parser = subparsers.add_parser(
        'plot-metric',
        help='visualize data and groundtruth for a given metric in a given testblock for a given test, e.g. time in '
             'testblock_small from atf_test/ts0_c0_r0_e0_s0_0'
    )
    add_metric(sub_parser)
    add_testblock(sub_parser)
    add_test(sub_parser)


    sub_parser = subparsers.add_parser(
        'plot-b',
        help='visualize data for a all metrics in a given testblock for a given test'
    )
    add_testblock(sub_parser)
    add_test(sub_parser)


    sub_parser = subparsers.add_parser('plot-c', help='visualize data for all metrics in all testblocks in all tests')


    sub_parser = subparsers.add_parser('plot-d', help='visualize aggregated data for all test repetitions for a given test, e.g. atf_test/ts0_c0_r0_e0_s0_0..10')
    add_test_case_ident(sub_parser)

    sub_parser = subparsers.add_parser('plot-fmw', help='fmw test plot')
    add_style(sub_parser)
    add_test(sub_parser)
    add_testblock(sub_parser)
    add_metric(sub_parser)

    sub_parser = subparsers.add_parser('compare-a', help='visualize comparison for a given metric in various testblocks of a given test, e.g. path_length in testblock testblock_small and testblock testblock_large from atf_test/ts0_c0_r0_e0_s0_0')

    sub_parser = subparsers.add_parser('compare-b', help='visualize comparision for all repetitions for a given test, e.g. atf_test/ts0_c0_r0_e0_s0_0..10')

    sub_parser = subparsers.add_parser('visualize-series', help='visualize time series data for a given metric in a given testblock for a given test, e.g. time in testblock_small from atf_test/ts0_c0_r0_e0_s0_0 from all atf_result.txt files')

    sub_parser = subparsers.add_parser('info-structure', help='TBD')


    parser.add_argument('filenames', metavar='filenames', nargs='+',
                        help='merged atf result file (multiple files not yet implemented)')



    #argparse_result = parser.parse_args(['--help'])
    #argparse_result = parser.parse_args(['plot metric', '--help'])
    #argparse_result = parser.parse_args(['plot foo', '--help'])


    #filename = '/tmp/atf_test_app_tf/results_txt/atf_result.txt'
    #filename = '/home/bge/Projekte/atf_data/atf_test_app_tf/results_txt/atf_result.txt'
    #filename = '/home/bge/Projekte/atf_data/atf_test/results_txt/atf_result.txt'

    #filename = '/home/bge/Projekte/atf_data/atf_test_app_navigation__series__atf_result.txt'
    filename = '/home/bge/Projekte/atf_data/atf_test__series__atf_result.txt'

    test_args = [
        [  # 0
            '--help'
        ],
        [  # 1
            'plot-metric',
            '--help'
        ],
        [  # 2
            'plot-metric',
            '-m', 'tf_length_translation',
            '-tb', 'testblock_small',
            '-t', 'ts0_c0_r0_e0_s0_0',
            filename
        ],
        [  # 3
            'plot-b',
            '-tb', 'testblock_small',
            '-t', 'ts0_c0_r0_e0_s0_0',
            filename
        ],
        [  # 4
            'plot-c',
            filename
        ],
        [  # 5
            'plot-d',
            '-ti', 'ts0_c0_r0_e0_s0',
            filename
        ],
        [  # 6
            'plot-fmw',
            filename
        ],
        [  # -1
            'info-structure',
            filename
        ],
    ]

    #argparse_result = parser.parse_args(test_args[5])
    argparse_result = parser.parse_args()


    dp = DemoPlotter()
    print 'loading file...',
    sys.stdout.flush()
    stime = time.time()
    dp.load_atf_result(filename=argparse_result.filenames[0])
    dtime = time.time() - stime
    print 'DONE (took %.3fs)' % (dtime)
    sys.stdout.flush()
    #dp._quicktest()

    dp.print_structure()


    if argparse_result.command == 'plot-metric':
        dp.plot_data_and_groundtruth_for_given_metric_testblock_test(
            metric=argparse_result.metric,
            testblock=argparse_result.testblock,
            test=argparse_result.test
        )
    elif argparse_result.command == 'plot-b':
        dp.plot_all_metrics_for_given_testblock_test(
            testblock=argparse_result.testblock,
            test=argparse_result.test
        )
    elif argparse_result.command == 'plot-c':
        dp.plot_all_metrics_testblocks_tests()
    elif argparse_result.command == 'plot-d':
        dp.plot_aggregated_data_for_all_test_repetitions_for_given_test_ident(argparse_result.test_case_ident)
    elif argparse_result.command == 'plot-fmw':
        dp.plot_fmw(argparse_result.style, argparse_result.test, argparse_result.testblock, argparse_result.metric)
    elif argparse_result.command == 'info-structure':
        dp.print_structure()
    else:
        raise NotImplementedError('sub-command <%s> not implemented yet' % argparse_result.command)

