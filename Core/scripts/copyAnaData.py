#!/usr/bin/env python
import sys,os,re, time

import ROOT
ROOT.gROOT.SetBatch(True)

from ROOT import *
ROOT.gSystem.Load("libFWCoreFWLite.so")
FWLiteEnabler.enable()

from optparse import OptionParser
import subprocess

import CommonFSQFramework.Core.Util




def checkRootFile(fp):
    while "//" in fp:
       fp = fp.replace("//","/")
    cmd = ["root", "-l", "-b", "-q", fp]
    #ret = subprocess.call(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while proc.poll() == None:
        time.sleep(1)

    errInStdout = False
    outData =""
    for line in proc.stdout:
        outData += line
        if "Error " in line:
            errInStdout = True
            break

    outData += "stderr::\n"
    for line in proc.stderr:
        outData += line
        if "Error " in line:
            errInStdout = True
            break

    if errInStdout:
        print ("\nProblem processing call: "+" ".join(cmd)+ "\n\noutdata:\n\n" + outData)
        sys.exit(1)

    ret = proc.poll()
    return ret
    


def checkDataIntegrity(remove = False, checkFilesWithRoot = False):

    sampleList=CommonFSQFramework.Core.Util.getAnaDefinition("sam")
    for s in sampleList:
        todo = []
        if "pathTrees" in sampleList[s]:
            todo.append(sampleList[s]["pathTrees"])
        if "pathPAT" in sampleList[s]:
            todo.append(sampleList[s]["pathPAT"])

        if len(todo)>0:
            print "Checking", s
        else:
            print "No files found for sample", s, ",skipping"
            continue
        
        for t in todo:
            fileMap = {}
            for root, dirs, files in os.walk(t):
                for f in files:
                    fp = root + "/" + f
                    if not f.endswith(".root"):
                        print "Non root file:", fp
                        continue
                    spl = f.split("_")
                    try:
                        fileNum = int(spl[1])
                    except:
                        print "Error processing", fp,"- skipping"
                        continue

                    while "//" in fp:
                        fp = fp.replace("//","/")

                    if checkFilesWithRoot:
                        ret = checkRootFile(fp)
                        if ret != 0:
                            print "Bad file:", fp
                            continue

                    # root -l -b -q
                    fsize = os.path.getsize(fp)
                    if fsize == 0:
                        print "Empty file:", fp
                        if remove:
                            os.system("rm "+fp)
                    else:
                        fileMap.setdefault(fileNum, []).append(fp)
                    #print f

            for num in fileMap:
                if len(fileMap[num]) > 1:
                    print "Multiple files:", s, num, "-", len(fileMap[num])
                    for f in fileMap[num][:]:
                        #ret = 0
                        ret = checkRootFile(f)
                        if ret != 0:
                            print "Bad file:", f
                            if remove:
                                os.system("rm "+f)
                                filemap[num].remove(f)

                    if len(fileMap[num]) > 1: # after root file check
                        biggestFile = ""
                        biggestFileSize = 0
                        for f in fileMap[num]:
                            fsize = os.path.getsize(f)
                            if fsize > biggestFileSize:
                                biggestFileSize = fsize
                                biggestFile = f

                        for f in fileMap[num]:
                            if f == biggestFile:
                                continue
                            else:
                                print "Will remove", f
                                if remove:
                                    os.system("rm "+f)
                        

def makeDir(d):
    if "eos/cms" in d:
        os.system("xrd eoscms mkdir -p " + d)
        #print " would create dir: xrd eoscms mkdir -p ", d
    else:
        if (not os.path.exists(d)):
            os.system("mkdir -p "+ d)
            #print " would create dir:", d
        if not os.path.isdir(d):
            print ("Cannot create output dir "+d)
            sys.exit(1)
    #mkdirCmd = ['gfal-mkdir', pathSE+'/'+ subdir]
    #                        print (str(mkdirCmd))
    #mkdirCmdOut = subprocess.Popen(mkdirCmd)
    #t = out.communicate()[0],
    #if (mkdirCmdOut.returncode!=0):
    #    print ("error", str(mkdirCmd), str(mkdirCmd.returncode))
    #    sys.exit(1)                        
     
                            


        


def main():
    sampleList=CommonFSQFramework.Core.Util.getAnaDefinition("sam")

    parser = OptionParser(usage="usage: %prog [options] filename",
                            version="%prog 1.0")

    parser.add_option("-p", "--doPat", action="store_true", dest="pat")
    parser.add_option("-t", "--doTrees", action="store_true",  dest="trees")
    parser.add_option("-c", "--checkDataIntegrity", action="store_true",  dest="check")
    parser.add_option("-d", "--deleteBadFiles", action="store_true",  dest="remove")
    parser.add_option("-r", "--rootCheck", action="store_true",  dest="checkFilesWithRoot")
    parser.add_option("-m", "--maxFilesMC", action="store",  type="int", dest="maxFilesMC")
    (options, args) = parser.parse_args()


    maxFilesMC = -1
    if options.maxFilesMC:
        maxFilesMC = options.maxFilesMC


    if options.check:
        remove = False
        checkFilesWithRoot = False
        if options.remove: remove = True
        if options.checkFilesWithRoot: checkFilesWithRoot = options.checkFilesWithRoot
        
        checkDataIntegrity(remove, checkFilesWithRoot)
        sys.exit(0)

    doPAT = False
    doTrees = False

    if options.pat :
        doPAT = True
    elif options.trees:
        doTrees = True

    if not doPAT and not doTrees:
        print "Nothing to do. Run me with '-t' option to copy trees from current skim"
        sys.exit()
        
    #333
    cntSamples = 0
    cntCopySum = 0
    cntReadSum = 0
    myprocs = []
    for s in sampleList:
        if "pathSE" not in sampleList[s]:
            print "No SE path found for sample", s            
        try:
            todo = []
            if "pathTrees" in sampleList[s]:
                todo.append(sampleList[s]["pathTrees"])
            if "pathPAT" in sampleList[s]:
                todo.append(sampleList[s]["pathPAT"])
            for d in todo:
                makeDir(d)
        except:
            continue

        cntSamples += 1

        pathSE = sampleList[s]["pathSE"]
        flist = CommonFSQFramework.Core.Util.getFileListGFAL(pathSE)

        cntCopy = 0
        cntRead = 0
        createdDirs = []

        for srcFile in flist:
            cntRead += 1
            cntReadSum += 1
            path_components = srcFile.split("/")
            fname = path_components[-1] # filename
            patFile = "mnTrgAna_PAT_" in fname
            treeFile = "trees_" in fname
                                    
            doCopy = False
            if patFile and doPAT:
                doCopy = True
                targetDir = sampleList[s]["pathPAT"]
                typeString = "patFile"
            if treeFile and doTrees:
                doCopy = True
                targetDir = sampleList[s]["pathTrees"]
                typeString = "treeFile"

            if not doCopy: continue
            if not sampleList[s]["isData"] and maxFilesMC >= 0 and cntCopy >= maxFilesMC:
                continue

            # check eventual sub-paths
            subdir = ''
            if (len(path_components)>1):
                for isub in range(len(path_components)-1):
                    subdir += path_components[isub] + '/'
                    if (subdir not in createdDirs):
                        createdDirs.append(subdir)
                        makeDir(targetDir + '/' + subdir)

            cntCopy += 1

            targetFile = targetDir + "/" + subdir + fname
            cpCommand = ['gfal-copy', pathSE.rstrip('/') + '/' + srcFile, targetFile]            
	    #cpCommand = ['lcg-ls', srcFile]

	    #print "would be cpCommand: ", cpCommand
            
	    if "eos/cms" not in targetDir and os.path.isfile(targetFile):
                print "Allready present", typeString, subdir+fname, " #"+str(cntCopy), "from", s
                continue

            print "Copying", typeString, subdir+fname, " #"+str(cntCopy), "from", s
            cntCopySum += 1

            myproc = subprocess.Popen(cpCommand)
            myprocs.append( (myproc, cpCommand) ) 
            while len(myprocs) > 3:
                time.sleep(1)
                for p in myprocs[:]:
                    exitCode = p[0].poll()
                    #print exitCode, p[1]
                    if exitCode != None:
                        if exitCode != 0:
                            print "Problem with ", p[1]
                        myprocs.remove(p)

    while len(myprocs) > 0:
        time.sleep(1)
        for p in myprocs[:]:
            exitCode = p[0].poll()
            #print exitCode, p[1]
            if exitCode != None:
                if exitCode != 0:
                    print "Problem with ", p[1]
                myprocs.remove(p)


    print "Finished copying " + str(cntCopySum) + " of total " + str(cntReadSum) + " files from " + str(cntSamples) + " samples "  
            
    ###


if __name__ == "__main__":
    main()
