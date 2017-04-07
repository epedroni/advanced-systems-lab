# Handle memaslap logs
import re
from numpy import mean, sqrt, square, std
from pathlib import Path

rtScale = 1000000

# directory must be a Path object, runs is an integer, returns a list of lists of string log paths
def getLogs(base, directory, runs):
    return [[str(l) for l in (base / directory.format(run=r)).glob("mema*.log")] for r in range(0, runs)]

# Combine multiple runs into a single set of results - takes a list of lists of logs and assumes 5 runs for CI calculation
def process(runs, tValue=2.776):
    intermediate = combineRuns(runs)
    
    results = {}
    
    # aggregate using specific function depending on data    
    for k in ["getTps", "setTps", "combinedTps"]:
        if k in intermediate:
            results[k] = (mean(intermediate[k], axis=0)[1], cInterval([x[1] for x in intermediate[k]], tValue))
    for k in ["getRt", "setRt", "combinedRt"]:
        if k in intermediate:
            results[k] = (mean(intermediate[k], axis=0)[1], sqrt(mean(square([x[2] for x in intermediate[k]]))))
            results[k + "CI"] = (mean(intermediate[k], axis=0)[1], cInterval([x[1] for x in intermediate[k]], tValue))
        if k + "Stacked" in intermediate:
            results[k + "Stacked"] = (mean(intermediate[k + "Stacked"], axis=0)[1], sqrt(mean(square([x[2] for x in intermediate[k + "Stacked"]]))))
    
    # average the averages, but RMS the stddevs
    for k in ["getRtFinal", "setRtFinal", "combinedRtFinal", "combinedTpsFinal", "combinedTotalOps", "setTotalOps", "getTotalOps", "totalRuntime"]:
        if k in intermediate: results[k] = intermediate[k]
    
    return results

# Returns the 95% confidence interval of a sample assuming 5 runs
def cInterval(samples, tValue):
    return tValue * (std(samples) / sqrt(len(samples)))

# Combine multiple runs into a single set of results - takes a list of lists of logs
def combineRuns(runs):
    results = {}
    intermediate = [combineMachines(r) for r in runs if len(r) > 0]

    # aggregate using specific function depending on data    
    for k in ["getTps", "setTps", "combinedTps"]:
        if k in intermediate[0]: results[k] = run_aggregateTps([x[k] for x in intermediate])
    for k in ["getRt", "setRt", "combinedRt"]:
        if k in intermediate[0]: results[k] = aggregateRt([x[k] for x in intermediate])
        if k + "Stacked" in intermediate[0]: results[k + "Stacked"] = stackRt([x[k + "Stacked"] for x in intermediate])
        
    # average the averages, but RMS the stddevs
    for k in ["getRtFinal", "setRtFinal", "combinedRtFinal"]:
        if k in intermediate[0]: results[k] = (mean([x[k][0] for x in intermediate]), sqrt(mean(square([x[k][1] for x in intermediate]))))
    
    # aggregate totals, where applicable
    results["combinedTpsFinal"] = mean([x["combinedTpsFinal"] for x in intermediate])
    results["combinedTotalOps"] = mean([x["combinedTotalOps"] for x in intermediate])
    results["setTotalOps"] = mean([x["setTotalOps"] for x in intermediate])
    results["getTotalOps"] = mean([x["getTotalOps"] for x in intermediate])
    results["totalRuntime"] = mean([x["totalRuntime"] for x in intermediate])
    
    return results

# Combine periodic measurements from many machines into a single list
def combineMachines(logs):
    results = {}
    intermediate = [read(l) for l in logs]

    # aggregate using specific function depending on data    
    for k in ["getTps", "setTps", "combinedTps"]:
        if k in intermediate[0]: results[k] = machine_aggregateTps([x[k] for x in intermediate])
    for k in ["getRt", "setRt", "combinedRt"]:
        if k in intermediate[0]:
            data = [x[k] for x in intermediate]
            results[k] = aggregateRt(data)
            results[k + "Stacked"] = stackRt(data)
        
    # average the averages, but RMS the stddevs
    for k in ["getRtFinal", "setRtFinal", "combinedRtFinal"]:
        if k in intermediate[0]: results[k] = (mean([x[k][0] for x in intermediate]), sqrt(mean(square([x[k][1] for x in intermediate]))))
    
    # aggregate totals, where applicable
    results["combinedTpsFinal"] = sum([x["combinedTpsFinal"] for x in intermediate])
    results["combinedTotalOps"] = sum([x["combinedTotalOps"] for x in intermediate])
    results["setTotalOps"] = sum([x["setTotalOps"] for x in intermediate])
    results["getTotalOps"] = sum([x["getTotalOps"] for x in intermediate])
    results["totalRuntime"] = mean([x["totalRuntime"] for x in intermediate])
    
    return results

# aggregate a list of lists of (x, mean, std) tuples into a single list of tuples (x, mean(mean), rms(std))
def aggregateRt(data):
    return [(data[0][y][0], mean([x[y][1] for x in data]), sqrt(mean(square([x[y][2] for x in data])))) for y in range(0, len(data[0]))]

# stack a list of lists of (x, mean, std) tuples into a single list of tuples (x, mean, std)
def stackRt(data):
    newData = []
    for d in data:
        newData = newData + d
    return newData

# aggregate a list of lists of (x, mean) tuples into a single list of tuples (x, sum(mean))
def machine_aggregateTps(data):
    return [(data[0][y][0], sum([x[y][1] for x in data])) for y in range(0, len(data[0]))]
    
# aggregate a list of lists of (x, sum) tuples into a single list of tuples (x, mean(sum))
def run_aggregateTps(data):
    return [(data[0][y][0], mean([x[y][1] for x in data])) for y in range(0, len(data[0]))]

# Reads a specified memaslap log file into an in-memory dictionary
def read(log):
    readX = 0
    writeX = 0
    totalX = 0

    results = {}
    
    # initialise all lists
    lists = ["getTps", "getRt", "setTps", "setRt", "combinedTps", "combinedRt"]
    for k in lists:
        results[k] = []
    
    f = open(log, "r")
    for line in f:
        #-------------------------------------------------------------
        if line.startswith("Get Statistics ("):
            next(f)
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtAvFinal = float(split[2]) / rtScale
            
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtStdFinal = float(split[2]) / rtScale
            
            results["getRtFinal"] = (rtAvFinal, rtStdFinal)
        #-------------------------------------------------------------
        elif line.startswith("Set Statistics ("):
            next(f)
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtAvFinal = float(split[2]) / rtScale
            
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtStdFinal = float(split[2]) / rtScale
            
            results["setRtFinal"] = (rtAvFinal, rtStdFinal)
        #-------------------------------------------------------------
        elif line.startswith("Total Statistics ("):
            next(f)
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtAvFinal = float(split[2]) / rtScale
            
            next(f)
            line = next(f)
            split = re.split(" +", line)
            rtStdFinal = float(split[2]) / rtScale
            
            results["combinedRtFinal"] = (rtAvFinal, rtStdFinal)
        #-------------------------------------------------------------
        elif line.startswith("Get Statistics"):
            ## skip two lines
            next(f)
            line = next(f)
            
            split = re.split(" +", line)
            results["getTps"].append((readX, int(split[3])))
            results["getRt"].append((readX, float(split[8]) / rtScale, float(split[9]) / rtScale))
            readX = readX + int(split[1])
        #-------------------------------------------------------------
        elif line.startswith("Set Statistics"):
            # skip two lines    
            next(f)
            line = next(f)
            
            split = re.split(" +", line)
            results["setTps"].append((writeX, int(split[3])))
            results["setRt"].append((writeX, float(split[8]) / rtScale, float(split[9]) / rtScale))
            writeX = writeX + int(split[1])
        #-------------------------------------------------------------
        elif line.startswith("Total Statistics"):
            # skip two lines
            next(f)
            line = next(f)
            
            split = re.split(" +", line)
            results["combinedTps"].append((totalX, int(split[3])))
            results["combinedRt"].append((totalX, float(split[8]) / rtScale, float(split[9]) / rtScale))
            totalX = totalX + int(split[1])
        #-------------------------------------------------------------
        elif line.startswith("cmd_get: "):
            results["getTotalOps"] = int(re.split(" +", line)[1])
        #-------------------------------------------------------------
        elif line.startswith("cmd_set: "):
            results["setTotalOps"] = int(re.split(" +", line)[1])
        #-------------------------------------------------------------
        elif line.startswith("Run time: "):
            split = re.split(" +", line)
            results["combinedTpsFinal"] = int(split[6])
            results["combinedTotalOps"] = int(split[4])
            results["totalRuntime"] = float(split[2].rstrip("s"))
    
    # make sure empty lists are set to none
    for k in lists:
        if len(results[k]) > 0:
            results[k] = results[k][1:-1]
        else:
            results.pop(k)
    
    return results
