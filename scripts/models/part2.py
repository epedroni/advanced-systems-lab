#!/usr/bin/python3

'''
Starting from the different configurations that you used in the second milestone,
build M/M/m queuing models of the system as a whole. Detail the characteristics
of these series of models and compare them with experimental data. The goal is
the analysis of the model and the real scalability of the system (explain the
similarities, the differences, and map them to aspects of the design or the
experiments). Make sure to follow the model-related guidelines described in the 
Notes!

Configurations in m2p2:
- Number of servers (S): 3, 5, 7
- Workload write proportion: 1%, 2.5%, 5%, 7.5%, 10%
- Middleware replication factor: 1, S
'''

import sys
import os
from pathlib import Path
sys.path.append("/home/eddy/uni/eth/asl/dev")
import cache
from model import model, show
from numpy import mean
import Gnuplot, Gnuplot.funcutils

base = Path("/home/eddy/uni/eth/asl/dev/m3/part2/")
dirTemplate = "sec3-rep{repl}-s{serv}-v{work}"

dataCache = cache.Cache(base / "data", base / "cache.yml")

# Constants
readThreads = 20
writeThreads = 1
threadsPerServer = readThreads + writeThreads

clientsPerMachine = 160
clientMachines = 2
clients = clientsPerMachine * clientMachines

requestType = "get"

# Experiment parameters
servers = [3, 5, 7]
replications = ["Single", "Full"]
workloads = ["1", "2.5", "5", "7.5", "10"]
runs = 5

littleslaw = []

# response time plot - triple plot, one for each server configuration
# lines for: measured rt, modelled rt, tserver. x axis is workload, y axis is rt (s)

def main():
    global requestType
    repIndex = 0
    #print("Servers\tWkload\tTPS\tReal Rt\tTqueue\tRho\tMod Rt\t\tMod Wt\t\tMod P0\tMod Pq\tMod JSystem\tMod JQueue\tLittle\t")
    requestType = "combined"
    
    for s in servers:
        g = Gnuplot.Gnuplot()
        g.title(str(s) + " Servers")
        g("set grid")
        g("set yrange [0:0.035]")
        #g("set xrange [0:4]")
        g("set xtics ('1' 0, '2.5' 1, '5' 2, '7.5' 3, '10' 4)")
        g("set terminal png size 480,400")

        g.xlabel("Workload Write Percentage")
        g.ylabel("Response Time (s)")
        g("set key off")
        
        mert = []
        mort = []
        for (i, w) in enumerate(workloads):
            exp = dirTemplate.format(repl=reps("Single"), serv=s, work=wl(w))
            data = compute(replications[repIndex], s, w)
            mert.append((i, dataCache.getData(exp, "memaslap", requestType + "RtFinal")[0]))
            mort.append((i, data["meanResponseTime"]))
        g._add_to_queue([Gnuplot.Data(mert, title="Measured Response Time", with_="lp")])
        g._add_to_queue([Gnuplot.Data(mort, title="Modelled Response Time", with_="lp")])
        g.hardcopy(filename="part2-rt-" + str(s) + ".png", terminal="png")
    

def jobs():
    global requestType
    repIndex = 0
    #print("Servers\tWkload\tTPS\tReal Rt\tTqueue\tRho\tMod Rt\t\tMod Wt\t\tMod P0\tMod Pq\tMod JSystem\tMod JQueue\tLittle\t")
    requestType = "combined"
    
    g = Gnuplot.Gnuplot()
    g.title("Average Number of Jobs in Queue")
    g("set grid")
    g("set yrange [0:]")
    #g("set xrange [0:4]")
    g("set xtics ('1' 0, '2.5' 1, '5' 2, '7.5' 3, '10' 4)")
    #g("set terminal png size 480,400")

    g.xlabel("Workload Write Percentage")
    g.ylabel("Jobs")
    g("set key top right")
    
    for s in servers:
        tmp = []
        for (i, w) in enumerate(workloads):
            data = compute(replications[repIndex], s, w)
            tmp.append((i, data["meanJobsQueue"]))
        g._add_to_queue([Gnuplot.Data(tmp, title=str(s) +  " Servers", with_="lp")])
    
    g.hardcopy(filename="part2-jq.png", terminal="png")

def traffint():
    global requestType
    repIndex = 0
    #print("Servers\tWkload\tTPS\tReal Rt\tTqueue\tRho\tMod Rt\t\tMod Wt\t\tMod P0\tMod Pq\tMod JSystem\tMod JQueue\tLittle\t")
    requestType = "combined"
    
    g = Gnuplot.Gnuplot()
    g.title("Traffic Intensity")
    g("set grid")
    g("set yrange [0:]")
    #g("set xrange [0:4]")
    g("set xtics ('1' 0, '2.5' 1, '5' 2, '7.5' 3, '10' 4)")
    #g("set terminal png size 480,400")

    g.xlabel("Workload Write Percentage")
    g.ylabel("Traffic Intensity")
    g("set key top right")
    
    for s in servers:
        tmp = []
        for (i, w) in enumerate(workloads):
            data = compute(replications[repIndex], s, w)
            tmp.append((i, data["trafficIntensity"]))
        g._add_to_queue([Gnuplot.Data(tmp, title=str(s) +  " Servers", with_="lp")])
    
    g.hardcopy(filename="part2-traffint.png", terminal="png")
    
# Run the model with numbers from the specified directory
def compute(replication, server, workload, showResults=False):
    exp = dirTemplate.format(repl=reps(replication), serv=server, work=wl(workload))

    # Average time window
    runtime = dataCache.getData(exp, "memaslap", "totalRuntime")

    # Assume job flow balance since memaslap does not return until all requests have been fulfilled
    # Jobs complete meaning the middleware forwarded something back to the client, even if it wasn't what the client expected
    arrivals = dataCache.getData(exp, "memaslap", requestType + "TotalOps")
    completions = dataCache.getData(exp, "memaslap", requestType + "TotalOps")

    # According to slides
    throughput = (completions / runtime)
    arrivalRate = (arrivals / runtime) # according to the book, this is actually 1 / interarrival time

    # According to the book
    meanServiceTime = dataCache.getData(exp, "middleware", requestType + "TserverMeanExp")[0]
    meanServiceRate = (1 / meanServiceTime) * threadsPerServer

    results = model(arrivalRate, meanServiceRate, server)
    
    if showResults:
        show(results)
        # Print sanity checks
        print(" Checks")
        print("    Utilization: {:,.2f}%".format((throughput / (threadsPerServer)) * (meanServiceTime / server) * 100))
        print("    Memaslap response time: {:,.6f} s".format(dataCache.getData(exp, "memaslap", "combinedRtFinal")[0]))
        print("    Memaslap submission rate: {:,.2f} jobs/s".format(clients / dataCache.getData(exp, "memaslap", "combinedRtFinal")[0]))
        print("    Memaslap throughput: {:,.2f} jobs/s".format(dataCache.getData(exp, "memaslap", "combinedTpsFinal")))
    
    #                                                       Mod Wt-   Mod P0-  Mod Pq-  Mod MSystem-Mod MQueue
    '''print("{:d}\t{:s}\t{:,.0f}\t{:,.4f}\t{:,.4f}\t{:,.4f}\t{:,.6f}\t{:,.6f}\t{:,.2f}\t{:,.2f}\t{:,.2f}\t\t{:,.2f}\t\t{:,.2f}".format(
                                                                server, 
                                                                workload, 
                                                                dataCache.getData(exp, "memaslap", requestType + "TpsFinal"), 
                                                                dataCache.getData(exp, "memaslap", requestType + "RtFinal")[0],
                                                                dataCache.getData(exp, "middleware", requestType + "TqueueMeanExp")[0],
                                                                results["trafficIntensity"], 
                                                                results["meanResponseTime"],
                                                                results["meanWaitingTime"],
                                                                results["probabilityZeroSystem"],
                                                                results["probabilityQueueing"],
                                                                results["meanJobsSystem"],
                                                                results["meanJobsQueue"],
                                                                arrivalRate * dataCache.getData(exp, "memaslap", requestType + "RtFinal")[0]))'''
    return results
    
def wl(w):
    if w == "2.5":
        return "2"
    elif w == "7.5":
        return "7"
    else:
        return w

def reps(r):
    if r == "Single":
        return "1"
    elif r == "Full":
        return "A"

if __name__ == "__main__":
    main()
