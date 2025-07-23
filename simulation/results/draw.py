# -*- coding: utf-8 -*-
import plotters
import os
import sys
from collections import deque

font = {'family': 'Times new roman', 'weight': 'bold', 'size': '22'}

def draw_from_file(filename, flow_mapping, signals_port_num, time_limit_low=None, time_limit_high=None):
    x_axis = [[] for _ in range(19)]
    y_axis = [[] for _ in range(19)]
    x_mpd = [[] for _ in range(19)]
    y_mpd = [[] for _ in range(19)]
    signals_x = [[] for _ in range(signals_port_num)]
    signals_y = [[] for _ in range(signals_port_num)]
    smooth_x = [[] for _ in range(signals_port_num)]
    smooth_y = [[] for _ in range(signals_port_num)]
    with open("./data/"+filename+".txt", "r") as raw_file:
        q = [deque() for _ in range(19)]
        avg = [0 for _ in range(19)]
        for line in raw_file:
            items = line.split()
            if len(items) < 4:
                continue
            if items[0] == "Rate:":
                time = int(items[1])
                if time_limit_low is not None and time < time_limit_low:
                    continue
                if time_limit_high is not None and time > time_limit_high:
                    continue
                srcip = items[2]
                rate = float(items[3])
                if srcip in flow_mapping:
                    x_axis[flow_mapping[srcip]].append(time / 1e6 - 2000)
                    y_axis[flow_mapping[srcip]].append(rate)
            elif items[0] == "Port:":
                time = int(items[1])
                port = int(items[2])
                utilization = float(items[3])
                if port < signals_port_num:
                    signals_x[port].append(time / 1e9)
                    signals_y[port].append(utilization)
            elif items[0] == "SPort:":
                time = int(items[1])
                port = int(items[2])
                utilization = float(items[3])
                if port < signals_port_num:
                    smooth_x[port].append(time / 1e9)
                    smooth_y[port].append(utilization)
            elif items[0] == "SMPD:":
                time = int(items[1])
                srcip = items[2]
                mpd = float(items[3])
                if srcip in flow_mapping:
                    x_mpd[flow_mapping[srcip]].append(time / 1e6 - 2000)
                    y_mpd[flow_mapping[srcip]].append(mpd)
                    q[flow_mapping[srcip]].append(mpd)
                    avg[flow_mapping[srcip]] += mpd
                    if len(q[flow_mapping[srcip]]) == 51:
                        oldest = q[flow_mapping[srcip]].popleft()
                        avg[flow_mapping[srcip]] -= oldest
    # if signals_port_num > 2:
    #     signals_y[2] = []
    #     signals_x[2] = []
    #     smooth_y[2] = []
    #     smooth_x[2] = []
    non_empty_count = sum(1 for lst in y_axis if lst)
    scale = 1
    if "100G" in filename:
        scale = 10
    plotters.draw("line", y_axis, "./rate/"+filename+".png", x_axis=x_axis, 
                xylabels=["Time (ms)", "Flow Rate (Gbps)"],
                markersize=0, linewidth=1.5,
                ylim = (-0.2*scale, 10.5*scale),
                yticks=[0, 2.5*scale, 5*scale, 7.5*scale, 10*scale],
                figure_size=(7, 5),
                legends=["Flow {}".format(i) for i in range(non_empty_count)])
    non_empty_count = sum(1 for lst in y_mpd if lst)
    plotters.draw("line", y_mpd, "./mpd/"+filename+".png", x_axis=x_mpd, 
                xylabels=["Time (ms)", "MPD (%)"],
                markersize=0, linewidth=1,
                figure_size=(7, 5),
                legends=["Flow {}".format(i) for i in range(non_empty_count)])
    non_empty_count = sum(1 for lst in signals_y if lst)
    plotters.draw("line", signals_y, "./signal/"+filename+"_signals.png", x_axis=signals_x, 
                xylabels=["Time (ms)", "Utilization"],
                markersize=0, linewidth=1,
                figure_size=(7, 5),
                legends=["Port {}".format(i) for i in range(non_empty_count)])
    non_empty_count = sum(1 for lst in smooth_y if lst)
    plotters.draw("line", smooth_y, "./smoothed_signal/"+filename+"_smooth.png", x_axis=smooth_x, 
                xylabels=["Time (ms)", "Utilization"],
                markersize=0, linewidth=1,
                figure_size=(7, 5),
                legends=["Port {}".format(i) for i in range(non_empty_count)])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "用法: python draw.py <文件名（不带.txt）> [time_limit_low] [time_limit_high]"
        sys.exit(1)
    
    filename = sys.argv[1]
    
    try:
        time_limit_low = float(sys.argv[2])*1e9 if len(sys.argv) > 2 else None
        time_limit_high = float(sys.argv[3])*1e9 if len(sys.argv) > 3 else None
    except ValueError:
        print "错误: 时间限制参数必须是数字"
        sys.exit(1)
    
    if time_limit_low == 0:
        time_limit_low = None
    if time_limit_high == 0:
        time_limit_high = None
    
    flow_mapping = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4}
    signals_port_num = 15
    
    draw_from_file(filename, flow_mapping, signals_port_num, time_limit_low, time_limit_high)
    
    print "Processed %s with time limit: [%s, %s]" % (
        filename, 
        time_limit_low if time_limit_low is not None else "None", 
        time_limit_high if time_limit_high is not None else "None"
    )