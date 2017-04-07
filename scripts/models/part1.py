#!/usr/bin/python3

import sys
import os
import yaml
from pathlib import Path

# custom imports from "upstairs"
sys.path.append("/home/eddy/uni/eth/asl/dev")
import memaslap
import middleware

base = Path("/home/eddy/uni/eth/asl/dev/m3/part1")

readThreads = 20
writeThreads = 1
servers = 3
mwThreads = servers * (readThreads + writeThreads)

clientThreads = 64
clients = 3
mwClients = clientThreads * clients

source = "middleware"
requestType = "combined"
measurement = "Tserver"
suffix="MeanExp"

# Caching
# Cut here:------------------------------------------------------------------------------------
memaResults = None
middResults = None

with open("cache.yml", "r") as f: data = yaml.load(f)
if data is None: data = {}

def getData(source, field):
    global memaResults, middResults, data
    
    if source not in data:
        data[source] = {}
    
    if field not in data[source]:
        if source == "memaslap":
            if memaResults is None: memaResults = memaslap.process([[str(l) for l in (base / "trace").glob("mema*.log")]])
            data[source][field] = memaResults[field]
        elif source == "middleware":
            if middResults is None: middResults = middleware.process([str(base / "trace" / "middleware.log")])
            data[source][field] = middResults[field]
    
    return data[source][field]      
# Cut here:------------------------------------------------------------------------------------  

# Average time window
runtime = getData("memaslap", "totalRuntime")

# Assume job flow balance since memaslap does not return until all requests have been fulfilled
# Jobs complete meaning the middleware forwarded something back to the client, even if it wasn't what the client expected
arrivals = getData("memaslap", "totalOps")
completions = getData("memaslap", "totalOps")

# According to slides
throughput = (completions / runtime)
arrivalRate = (arrivals / runtime) # according to the book, this is actually 1 / interarrival time

# According to the book
meanServiceTime = getData(source, requestType + measurement + suffix)[0]
#meanServiceRate = (1 / meanServiceTime) * mwThreads
meanServiceRate = ((mwClients + 1) / mwClients) * arrivalRate

# M/M/1 parameters:
lam = arrivalRate
mu = meanServiceRate

# Modelled values
rho = lam / mu

# Print modelled things
print(" Model parameters")
print("    Mean arrival rate (λ): {:,.2f} jobs/s".format(lam))
print("    Mean service rate (µ): {:,.2f} jobs/s".format(mu))
print()
print(" Modelled values")
print("    Traffic intensity (ρ): {:,.6f}".format(rho))
print("    Probability of 0 jobs in the system (p0): {:,.6f}".format(1 - rho))
print("    Mean number of jobs in the system (E[n]): {:,.2f} jobs".format(rho / (1 - rho)))
#print("    Variance of number of jobs in the system (Var[n]): {:,}".format(rho / ((1 - rho) ** 2)))
print("    Mean number of jobs in the queue (E[nq]): {:,.2f} jobs".format((rho ** 2) / (1 - rho)))
#print("    Variance of number of jobs in the queue (Var[nq]): {:,}".format(?))
print("    Mean response time (E[r]): {:,.6f} s".format((1 / mu) / (1 - rho)))
print("    Mean waiting time (E[w]): {:,.6f} s".format((rho * ((1 / mu) / (1 - rho)))))
print("    Mean number of jobs served in one busy period: {:,.2f} jobs".format(1 / (1 - rho)))
print("    Mean busy period duration: {:,.6f} s".format(1 / (mu * (1 - rho))))
print()
print(" Checks")
print("    Utilization: {:,.2f}%".format((throughput / mwThreads) * meanServiceTime * 100))
print("    Memaslap response time: {:,.6f} s".format(getData("memaslap", "combinedRtFinal")[0]))
print("    Memaslap submission rate: {:,.6f} jobs/s".format(192 / getData("memaslap", "combinedRtFinal")[0]))
print("    Memaslap throughput: {:,.2f} jobs/s".format(getData("memaslap", "combinedTpsFinal")))
print("    Real waiting time: {:,.6f} s".format(getData("memaslap", "combinedRtFinal")[0] - getData("middleware", "combinedTserverMeanExp")[0]))

# Update cache in case we loaded something new
with open("cache.yml", "w") as f: yaml.dump(data, stream=f)

