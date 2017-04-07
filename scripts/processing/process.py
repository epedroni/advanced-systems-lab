#!/usr/bin/python3

# Processes milestone 2 part 1 results
import sys
import os
from pathlib import Path
import Gnuplot, Gnuplot.funcutils
from numpy import percentile, histogram

# custom imports from "upstairs"
sys.path.append("/home/eddy/uni/eth/asl/dev")
import memaslap
import middleware

base = Path("/home/eddy/uni/eth/asl/dev/part1")
expdir = "sec1-c{client}-v{thread}-r{run}"
clients = [120, 160, 200, 240, 280, 320, 360]
threads = [10, 20, 30, 40]
runs = 5

def defaultPlot():
    g = Gnuplot.Gnuplot()
    g("set grid")
    g("set yrange [0:]")
    g("set xrange [0:]")
    return g

def plotThroughput():
    g = defaultPlot()
    g.title("Throughput as a Function of Total Clients")
    g.xlabel("Total Clients")
    g.ylabel("Throughput (operations/s)")
    g("set key inside bottom right")
    g("set xtic 40")
    
    # create one line for each thread
    for t in threads:
        # go over all clients
        tTps = []
        for c in clients:
            # create a list of lists with machines for each run
            logs = [[str(l) for l in (base / expdir.format(client=c, thread=t, run=r)).glob("mema*.log")] for r in range(0, runs)]
            results = memaslap.process(logs)
            tTps.append((c, results["getTps"][0], results["getTps"][1]))
        g._add_to_queue([Gnuplot.Data(tTps, title=(str(t) + " threads"), with_="yerrorbar lt " + str(t/10))])
        g._add_to_queue([Gnuplot.Data(tTps, with_="lp lt " + str(t/10))])
    
    g.hardcopy(filename="tps-all-threads.png", terminal="png")
    
def plotResponseTimeDistribution(clientCount):
    g = defaultPlot()
    g.title("Response Time Distribution with " + str(clientCount) + " Total Clients")
    g.xlabel("Response Time (s)")
    g.ylabel("Occurrences")
    g("set key inside top left")
    
    # create one line for each thread
    for (i, t) in enumerate(threads):
        # create a list of lists with machines for each run
        logs = [[str(l) for l in (base / expdir.format(client=clientCount, thread=t, run=r)).glob("mema*.log")] for r in range(0, runs)]
        results = memaslap.combineRuns(logs)
        
        hist = histogram([x[1] for x in results["getRtStacked"]], bins="auto")
        tmp = [(x, hist[0][i]) for (i, x) in enumerate(hist[1][:-1])]
        
        g._add_to_queue([Gnuplot.Data(tmp, title=(str(t) + " threads"), with_="lp lt " + str(i + 1))])
    
    g.hardcopy(filename="rt-distribution.png", terminal="png")
    
def plotResponseTimeByClient():
    g = defaultPlot()
    g.title("Response Time as a Function of Total Clients")
    g.xlabel("Total Clients")
    g.ylabel("Response Time (s)")
    g("set key inside top left")
    g("set xtic 40")
    g("unset yrange")
        
    # create one line for each thread
    for t in threads:
        # go over all clients
        tTps = []
        for c in clients:
            # create a list of lists with machines for each run
            logs = [[str(l) for l in (base / expdir.format(client=c, thread=t, run=r)).glob("mema*.log")] for r in range(0, runs)]
            results = memaslap.process(logs)
            tTps.append((c, results["getRtStacked"][0], results["getRt"][1]))
        g._add_to_queue([Gnuplot.Data(tTps, title=(str(t) + " threads"), with_="yerrorbar lt " + str(t/10))])
        g._add_to_queue([Gnuplot.Data(tTps, with_="lp lt " + str(t/10))])
    
    g.hardcopy(filename="rt-all-threads.png", terminal="png")
    
def plotResponseTimePercentile(threadCount, clientCount, percentiles):
    g = defaultPlot()
    g.title("Response Time Percentiles for Optimum Case")
    g.xlabel("Percentile")
    g.ylabel("Response Time (s)")
    g("set key inside top left")
    #g("set xtic 40")
    
    # read data from logs only once
    data = memaslap.combineRuns([[str(l) for l in (base / expdir.format(client=clientCount, thread=threadCount, run=r)).glob("mema*.log")] for r in range(0, runs)])
    
    tmp = []
    for (i, p) in enumerate(percentiles):
        tmp.append((p, percentile(clientData["getRtStacked"], p, axis=0)[1]))

    g._add_to_queue([Gnuplot.Data(tmp, with_="lp ls 1")])
    g.hardcopy(filename="rt-opt-percentile.png", terminal="png")
    
def plotMwBreakdownBarsByClient(threadCount):
    g = Gnuplot.Gnuplot()
    g.title("Middleware Time Breakdown with " + str(threadCount) + " Read Threads")
    g.xlabel("Total Clients")
    g.ylabel("Time (s)")
    g("set key top left")
    g("set grid ytics")
    g("set style data histogram")
    g("set style histogram errorbars gap 1")
    g("set style fill pattern 0 border")
    g("set auto x")
    g("set xrange [-0.5:6.5]")
    g("set xtics ('120' 0, '160' 1, '200' 2, '240' 3, '280' 4, '320' 5, '360' 6)")
    
    # get data for all clients
    data = {}
    fields = ["Tqueue", "Tserver", "Tmw"]
    for f in fields:
        data[f] = []
    
    for c in clients:
        # create a list of logs from the runs
        logs = [str(base / expdir.format(client=c, thread=threadCount, run=r) / "middleware.log") for r in range(0, runs) if (base / expdir.format(client=c, thread=threadCount, run=r)).exists()]
        results = middleware.process(logs)
        for f in fields:
            data[f].append((c, results["get" + f + "MeanExp"][0], results["get" + f + "MeanExp"][1]))
    
    for f in fields:
        g._add_to_queue([Gnuplot.Data(data[f], title=f, using="2:3")])

    g.hardcopy(filename="mw-time-clients.png", terminal="png")

def plotMwBreakdownBarsByThread(clientCount):
    g = Gnuplot.Gnuplot()
    g.title("Middleware Time Breakdown with " + str(clientCount) + " Total Clients")
    g.xlabel("Read Threads")
    g.ylabel("Time (s)")
    g("set key top right")
    g("set grid ytics")
    g("set style data histogram")
    g("set style histogram errorbars gap 1")
    g("set style fill pattern 0 border")
    g("set auto x")
    g("set xrange [-0.5:3.5]")
    g("set xtics ('10' 0, '20' 1, '30' 2, '40' 3)")
    
    # get data for all clients
    data = {}
    fields = ["Tqueue", "Tserver", "Tmw"]
    for f in fields:
        data[f] = []
    
    for t in threads:
        # create a list of logs from the runs
        logs = [str(base / expdir.format(client=clientCount, thread=t, run=r) / "middleware.log") for r in range(0, runs)]
        results = middleware.process(logs)
        for f in fields:
            data[f].append((t, results["get" + f + "MeanExp"][0], results["get" + f + "MeanExp"][1]))
    
    for f in fields:
        g._add_to_queue([Gnuplot.Data(data[f], title=f, using="2:3")])

    g.hardcopy(filename="mw-time-threads.png", terminal="png")

def plotMwPercentile(threadCount, clientCount):
    g = defaultPlot()
    g.title("Middleware Percentiles with " + str(threadCount) + " Read Threads and " + str(clientCount) + " Total Clients")
    g.xlabel("Percentile")
    g.ylabel("Time (s)")
    g("set key inside top left")
    g("set logscale y")
    g("unset yrange")
    g("set format y \"10^{%L}\"")
    g("set xtics 25")
    
    # read data from logs only once
    logs = [str(base / expdir.format(client=clientCount, thread=threadCount, run=r) / "middleware.log") for r in range(0, runs)]
    data = middleware.process(logs)
    
    fields = ["Tqueue", "Tserver", "Tmw"]
    for (i, f) in enumerate(fields):
        g._add_to_queue([Gnuplot.Data(data["get" + f + "Percentile"], title=f, with_="lp ls " + str(i + 1), using="1:2")])
    
    g.hardcopy(filename="mw-opt-percentile.png", terminal="png")
    
def plotMwDistribution(threadCount, clientCount):
    g = defaultPlot()
    g.title("Middleware Time Distribution with " + str(clientCount) + " Total Clients")
    g.xlabel("Time (s)")
    g.ylabel("Occurrences")
    g("set key inside top right")
    g("unset xrange")
    g("unset yrange")
    g("set logscale x")
    g("set logscale y")
    
    logs = [str(base / expdir.format(client=clientCount, thread=threadCount, run=r) / "middleware.log") for r in range(0, runs)]
    data = middleware.process(logs)
    
    # create one line for each field
    fields = ["Tqueue", "Tserver", "Tmw"]
    for (i, f) in enumerate(fields):
        g._add_to_queue([Gnuplot.Data(data["get" + f + "Distribution"], title=f, with_="lp lt " + str(i + 1))])
    
    g.hardcopy(filename="mw-opt-distribution.png", terminal="png")

def plotResponseTimeHist(t):
    g = Gnuplot.Gnuplot()
    g.title("Response Time as a Function of Total Clients")
    g.xlabel("Total Clients")
    g.ylabel("Response Time (s)")
    g("set grid ytics")
    g("set style data candlesticks")
    g("set style fill pattern 0 border")
    g("set xtic 40")
    g("set boxwidth 0.75")
    g("set terminal png size 800,800")
    g("set xtics ('120' 0, '160' 1, '200' 2, '240' 3, '280' 4, '320' 5, '360' 6)")
    g("set xrange [-0.5:6.5]")
    g("set yrange [0:0.03]")
    
    # go over all clients
    rt = []
    for c in clients:
        # create a list of lists with machines for each run
        logs = [[str(l) for l in (base / expdir.format(client=c, thread=t, run=r)).glob("mema*.log")] for r in range(0, runs)]
        results = [x[1] for x in memaslap.combineRuns(logs)["getRtStacked"]]
        # X Min 1stQuartile Median 3rdQuartile Max
        
        rt.append((c, min(results), percentile(results, 25), percentile(results, 50), percentile(results, 75), max(results)))
    g._add_to_queue([Gnuplot.Data(rt, with_="candlesticks lt 1 whiskerbars 0.5", using="0:3:2:6:5")])
    g._add_to_queue([Gnuplot.Data(rt, with_="candlesticks lt -1", using="0:4:4:4:4")])
    
    g.hardcopy(filename="rt-percentile-no-threads.png", terminal="png")

#
if __name__ == "__main__":
    #plotResponseTimePercentile(320, 20, range(0, 101))
    for t in threads:
        plotResponseTimeHist(t)
        
    '''rtPercentile = (20, [0, 25, 50, 75, 95, 100]) # number of threads, percentiles
    rtDistribution = 320 # number of clients
    
    mwBreakdownThreads = 20 # number of threads
    mwBreakdownClients = 320 # number of clients
    mwPercentile = (20, 320) # threads, clients
    mwDistribution = (10, 360) # threads, clients

    if len(sys.argv) > 1:
        if sys.argv[1] == "tps":
            plotThroughput()
        elif sys.argv[1] == "rt":
            plotResponseTimePercentile(rtPercentile[0], rtPercentile[1])
            plotResponseTimeByClient()
            plotResponseTimeDistribution(rtDistribution)
        elif sys.argv[1] == "mw":
            plotMwBreakdownBarsByClient(mwBreakdownThreads)
            plotMwBreakdownBarsByThread(mwBreakdownClients)
            plotMwPercentile(mwPercentile[0], mwPercentile[1])
            plotMwDistribution(mwDistribution[0], mwDistribution[1])
    else:
        plotThroughput()
        plotResponseTimePercentile(rtPercentile[0], rtPercentile[1])
        plotResponseTimeByClient()
        plotResponseTimeDistribution(rtDistribution)
        
        plotMwBreakdownBarsByClient(mwBreakdownThreads)
        plotMwBreakdownBarsByThread(mwBreakdownClients)
        plotMwPercentile(mwPercentile[0], mwPercentile[1])
        plotMwDistribution(mwDistribution[0], mwDistribution[1])'''
    
