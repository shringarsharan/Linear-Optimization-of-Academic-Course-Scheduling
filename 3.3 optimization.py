import pandas as pd
import numpy as np
from gurobipy import Model, GRB

def optimize (inputFile,outputFile):
    '''
    
    This function performs an optimization of the allocation of offered course sections to a combination of available 
    classrooms, days, and time slots. 
    
    It takes as an input two arguments:
    
    1) inputFile: string; indicates the path to the input file.
    2) outputFile: string; indicates the path to the output file.
    
    For a given input retrieved from the path specified in inputFile, the function returns an Excel spreadsheet to 
    the path specified in outputFile, containing optimized allocations.
    
    Please note that the format of both the input and the output files is prescribed in detail in 
    '3.6 Documentation of optimization tool' .pdf file.
    
    '''
    course = pd.read_excel(inputFile, sheet_name = "course", index_col=0)
    classroom = pd.read_excel(inputFile, sheet_name = "classroom", index_col=0)
    timeslot = pd.read_excel(inputFile, sheet_name = "timeslot", index_col=0)

    I = course.section #set of course sections
    J = ["Monday","Tuesday","Wednesday","Thursday","Friday"] #set of days
    K = classroom.index #set of classrooms
    L = timeslot.index #set of time slots
    A = course.loc[course.length == 90,"section"] #set of 90 minutes courses
    B = course.loc[course.length == 180,"section"] #set of 180 minutes courses
    C = course.loc[course.frequency == 1,"section"] #set of courses only meet once a week
    D = course.loc[course.frequency == 2,"section"] #set of courses meet twice a week
    R = course.first_instructor.unique() #set of professors
    F = course.loc[course.semester == "first","section"] #set of first-half semester course
    S = course.loc[course.semester == "second","section"] #sef of second-half semester course
    U = course.loc[course.semester == "full","section"] #set of full-semester course

    mod = Model()
    x = mod.addVars(I,J,K,L, vtype = GRB.BINARY)
    a = mod.addVars(I, vtype = GRB.BINARY) #if a section is scheduled on Monday
    b = mod.addVars(I, vtype = GRB.BINARY) #if a section is scheduled on Tuesday
    c = mod.addVars(I, vtype = GRB.BINARY) #if a section is scheduled on Wednesday
    d = mod.addVars(I, vtype = GRB.BINARY) #if a section is scheduled on Thursday
    e = mod.addVars(I, vtype = GRB.BINARY) #if a section is scheduled on Friday
    u = mod.addVars(I,K,vtype = GRB.BINARY) #if a section i is scheduled to classroom k
    w = mod.addVars(I,L,vtype = GRB.BINARY) #if a section i is scheduled to slot l
    z = mod.addVars(I,vtype = GRB.BINARY) #if a section meets twice a week, whether to assign it on MW

    mod.setObjective(sum(x[i,j,k,l]*course.loc[course.section == i,l] for i in I for j in J for k in K for l in L),sense = GRB.MAXIMIZE)

    #whether a section i is assigned to time slot l
    for i in I:
        for l in L:
            mod.addConstr(0.0001*sum(x[i,j,k,l] for j in J for k in K) <= w[i,l])
            mod.addConstr(sum(x[i,j,k,l] for j in J for k in K) >= w[i,l])

    #90 minutes class can at most be assigned to 1 timeslot, 180 minutes class can at most be assigned to 2 timeslots
    for i in A:
        mod.addConstr(sum(w[i,l] for l in L) == 1)
    for i in B:
        mod.addConstr(sum(w[i,l] for l in L) == 2)

    #whether a class is scheduled on Monday, Tuesday, Wednesday, Thursday and Friday
    for i in I:
        for j in J:
            if j == "Monday":
                mod.addConstr(0.0001*sum(x[i,j,k,l] for k in K for l in L) <= a[i])
                mod.addConstr(sum(x[i,j,k,l] for k in K for l in L) >= a[i])

            elif j == "Tuesday":
                mod.addConstr(0.0001*sum(x[i,j,k,l] for k in K for l in L) <= b[i])
                mod.addConstr(sum(x[i,j,k,l] for k in K for l in L) >= b[i])

            elif j == "Wednesday":
                mod.addConstr(0.0001*sum(x[i,j,k,l] for k in K for l in L) <= c[i])
                mod.addConstr(sum(x[i,j,k,l] for k in K for l in L) >= c[i])

            elif j == "Thursday":
                mod.addConstr(0.0001*sum(x[i,j,k,l] for k in K for l in L) <= d[i])
                mod.addConstr(sum(x[i,j,k,l] for k in K for l in L) >= d[i])

            elif j == "Friday":
                mod.addConstr(0.0001*sum(x[i,j,k,l] for k in K for l in L) <= e[i])
                mod.addConstr(sum(x[i,j,k,l] for k in K for l in L) >= e[i])

    #assign 1 day if a section meets once a week, assign 2 days if a section meets twice a week
    for i in C:
        mod.addConstr(a[i]+b[i]+c[i]+d[i]+e[i]==1)
    for i in D:
         mod.addConstr(a[i]+b[i]+c[i]+d[i]+e[i]==2)

    #assign MW or TH if a section meets twice a week
    for i in D:
        mod.addConstr(a[i]+c[i] == 2*z[i])
        mod.addConstr(b[i]+d[i] == 2*(1-z[i]))

    #whether a section i is assigned to classroom k
    for i in I:
        for k in K:
            mod.addConstr(0.0001*sum(x[i,j,k,l] for j in J for l in L) <= u[i,k])
            mod.addConstr(sum(x[i,j,k,l] for j in J for l in L) >= u[i,k])

    #each section can be assigned to at most 1 classroom
    for i in I:
        mod.addConstr(sum(u[i,k] for k in K) <= 1)

    #each combination of classroom and timeslot can only have 1 section assigned to it
    for j in J:
        for k in K:
            for l in L:
                mod.addConstr(sum(x[i,j,k,l] for i in I) <= 1)

    #professor doesn't have overlapping slot
    for l in L:
        for j in J:
            for r in R:
                mod.addConstr(sum(x[i,j,k,l] for k in K for i in course.loc[course.first_instructor==r,"section"])<=1)

    #assignment for classes only in the first half/second half semester
    for m in F:
        for n in U:
            for j in J:
                for k in K:
                    for l in L:
                        mod.addConstr(x[m,j,k,l]+x[n,j,k,l]<=1)

    for m in S:
        for n in U:
            for j in J:
                for k in K:
                    for l in L:
                        mod.addConstr(x[m,j,k,l]+x[n,j,k,l]<=1)

    mod.setParam('outputflag',False)
    mod.optimize()

    header_temp = []
    for k in K:
        for j in J:
            header_temp.append(j+k)

    header = pd.MultiIndex.from_product([classroom.index,['Monday','Tuesday','Wednesday','Thursday','Friday']],names=['Classroom','Days'])
    schedule = pd.DataFrame("", index=timeslot.index, columns=header_temp)
    for i in I:
        for j in J:
            for k in K:
                for l in L:
                    if x[i,j,k,l].x:
                        schedule.loc[l,j+k] = i

    writer=pd.ExcelWriter(outputFile)
    schedule.columns = header
    schedule.index = timeslot.time

    schedule.to_excel(writer,sheet_name='Schedule')
    writer.save()

if __name__=='__main__':
    import sys, os
    print (f'Running {sys.argv[0]} using argument list {sys.argv}')
    inputFile=sys.argv[1]
    outputFile=sys.argv[2]
    if os.path.exists(inputFile):
        optimize(inputFile,outputFile)
        print('Optimized successfully')
