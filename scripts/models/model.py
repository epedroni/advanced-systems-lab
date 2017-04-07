from math import factorial as fac

# M/M/m model, returns a dictionary of results for the given parameters
def model(lam, mu, m):
    results = {}
    results["arrivalRate"] = lam
    results["serviceRate"] = mu
    results["servers"] = m
    
    rho = lam / (mu * m)
    results["trafficIntensity"] = rho
    
    p0 = 1 / (1 + (((m * rho) ** m) / (fac(m) * (1 - rho))) + sum([((m * rho) ** n) / fac(n) for n in range(1, m)]))
    results["probabilityZeroSystem"] = p0
    
    pq = (((m * rho) ** m) / (fac(m) * (1 - rho))) * p0
    results["probabilityQueueing"] = pq
    
    results["meanJobsSystem"] = (m * rho) + ((rho * pq) / (1 - rho))
    
    results["meanJobsQueue"] = rho * pq * (1 - rho)
    
    results["meanResponseTime"] = (1 / mu) * (1 + (pq / (m * (1 - rho))))
    
    results["meanWaitingTime"] = pq / (m * mu * (1 - rho))
    
    return results

# Prints a dictionary of results to stdout
def show(results):
    print(" Model parameters")
    print("    Mean arrival rate (λ): {:,.2f} jobs/s".format(results["arrivalRate"]))
    print("    Mean service rate (µ): {:,.2f} jobs/s".format(results["serviceRate"]))
    print()
    print(" Modelled values")
    print("    Traffic intensity (ρ): {:,.6f}".format(results["trafficIntensity"]))
    print("    Probability of 0 jobs in the system (p0): {:,.6f}".format(results["probabilityZeroSystem"]))
    print("    Probability of queueing (ϱ): {:,.6f}".format(results["probabilityQueueing"]))
    print("    Mean number of jobs in the system (E[n]): {:,.2f} jobs".format(results["meanJobsSystem"]))
    print("    Mean number of jobs in the queue (E[nq]): {:,.2f} jobs".format(results["meanJobsQueue"]))
    print("    Mean response time (E[r]): {:,.6f} s".format(results["meanResponseTime"]))
    print("    Mean waiting time (E[w]): {:,.6f} s".format(results["meanWaitingTime"]))
    print()
