#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)

from HistosHelper import getHistos

from CommonFSQFramework.Core.DrawPlots import DrawPlots

import  CommonFSQFramework.Core.Style

from mnDraw import DrawMNPlots 
from array import array
from optparse import OptionParser
import math

import sys
def main():
    CommonFSQFramework.Core.Style.setTDRStyle()


    parser = OptionParser(usage="usage: %prog [options] filename",
                            version="%prog 1.0")

    parser.add_option("-v", "--variant",   action="store", dest="variant", type="string", \
                                help="choose analysis variant")
    parser.add_option("-n", "--normalization",   action="store", dest="normalization", type="string", \
                                help="how should I normalize the plots?")
    parser.add_option("-b", "--normalizeToBinWidth",   action="store_true", dest="normalizeToBinWidth")
    parser.add_option("-s", type="float", dest="scaleExtra")   

    (options, args) = parser.parse_args()
    scaleExtra = 1.
    if options.scaleExtra:
        scaleExtra = 1./options.scaleExtra

    normalizeToBinWidth = False
    if options.normalizeToBinWidth:
        normalizeToBinWidth = True

    if not options.variant:
        print "Provide analysis variant"
        sys.exit()

    if not options.normalization:
        print "Provide normalization variant"
        sys.exit()

    norms = ["xs", "area"]
    if options.normalization not in norms:
        print "Normalization not known. Possible choices: " + " ".join(norms)
        sys.exit()

    indir = "~/tmp/unfolded_{}/".format(options.variant)


    (options, args) = parser.parse_args()
    if not options.variant:
        print "Provide analysis variant"
        sys.exit()

    indir = "~/tmp/unfolded_{}/".format(options.variant)
    histofile = "plotsMNxs_{}.root".format(options.variant)


    lumiUncertainty = 0.04
    herwigIn=indir+"/mnxsHistos_unfolded_herwigOnData.root"
    pythiaIn=indir+"/mnxsHistos_unfolded_pythiaOnData.root"
    ofileName = indir+"/mnxsHistos_unfolded_onData_merged.root"


    histos = {}
    histos["herwig"]=getHistos(herwigIn)
    histos["pythia"]=getHistos(pythiaIn)
    #print histos["herwig"]["_jet15"].keys()
    #sys.exit()
    # TODO: test that dirs have the same contents

    # ['xsunfolded_central_jet15', 'xsunfolded_jecDown_jet15', 'xs_central_jet15', 'xsunfolded_jerDown_jet15', 'xsunfolded_jecUp_jet15', 'xsunfolded_jerUp_jet15']
    finalSet = {}

    todo = ["_jet15", "_dj15fb"]
    #todo = ["_jet15"]
    for t in todo:
        finalSet[t] = {}
        for hName in histos["herwig"][t]:
            if hName.startswith("xs_"): continue # skip detector level histogram

            hAvg = histos["herwig"][t][hName].Clone()

            hAvg.Add(histos["pythia"][t][hName])
            hAvg.Scale(0.5)
            finalSet[t][hName]=hAvg

            # add herwig/pythia central histo as variations
            #  in case we would have more than two MC - for every MC
            #   add a central value as "up" variation, as a "down"
            #   variation use the averaged histogram
            #    this way we have consistent list of up/down variations,
            #    where the down variation doesnt enlarge uncertainty band
            if "_central_" in hName:
                newNameHerwig = hName.replace("_central_", "_modelUp_")
                newNamePythia = hName.replace("_central_", "_modelDown_")
                finalSet[t][newNameHerwig] = histos["herwig"][t][hName].Clone(newNameHerwig)
                finalSet[t][newNamePythia] = histos["pythia"][t][hName].Clone(newNamePythia)

                # at the same point - use the averaged histogram to add lumi uncertainy
                #  BTW: should we do it here??
                newNameAvgUp = hName.replace("_central_", "_lumiUp_")
                newNameAvgDown = hName.replace("_central_", "_lumiDown_")
                finalSet[t][newNameAvgUp] = hAvg.Clone(newNameAvgUp)
                finalSet[t][newNameAvgDown] = hAvg.Clone(newNameAvgDown)
                finalSet[t][newNameAvgUp].Scale(1.+lumiUncertainty)
                finalSet[t][newNameAvgDown].Scale(1.-lumiUncertainty)



    # add jet15 and dj15 histos
    # note: histo binning should be the same from beginning!
    finalSet["merged"] = {}
    for t in finalSet["_jet15"]:
        newName = t.replace("_jet15", "_jet15andDJ15FB")
        finalHisto = finalSet["_jet15"][t].Clone(newName)
        finalHisto.Add(finalSet["_dj15fb"][t.replace("_jet15", "_dj15fb")].Clone())
        if options.normalization == "area":
            finalHisto.Scale(1./finalHisto.Integral())
        if normalizeToBinWidth:
            finalHisto.Scale(1., "width")

        finalHisto.Scale(scaleExtra)

        finalSet["merged"][newName] = finalHisto
            



    # save all to file
    ofile = ROOT.TFile(ofileName, "RECREATE")
    for dirName in finalSet:
        odir = ofile.mkdir(dirName)
        for h in finalSet[dirName]:
            odir.WriteTObject(finalSet[dirName][h])


    # make final plot, including uncertainty band
    central = [ finalSet["merged"][hName] for hName in finalSet["merged"].keys() if "_central_" in hName ]
    if len(central) != 1:
        raise Exception("Error: more than one central histo found")
    central = central[0]

    uncert  = [finalSet["merged"][hName] for hName in finalSet["merged"].keys() if "_central_" not in hName ]
    #uncert  = [finalSet["merged"][hName] for hName in finalSet["merged"].keys() if "_model" in hName ]

    uncResult= DrawPlots.getUncertaintyBand(uncert, central)
    unc = uncResult["band"]


    # get GEN level distributions
    histosFromPyAnalyzer = getHistos(histofile)
    herwigDir = "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
    pythiaDir =  "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
    genHistoHerwig = histosFromPyAnalyzer[herwigDir]["detaGen_central_jet15"].Clone()
    genHistoHerwig.Add(histosFromPyAnalyzer[herwigDir]["detaGen_central_dj15fb"])
    genHistoPythia = histosFromPyAnalyzer[pythiaDir]["detaGen_central_jet15"].Clone()
    genHistoPythia.Add(histosFromPyAnalyzer[pythiaDir]["detaGen_central_dj15fb"])

    if options.normalization == "area":
        map(lambda h: h.Scale(1./h.Integral()), [genHistoPythia, genHistoHerwig] )
    if normalizeToBinWidth:
        map(lambda h: h.Scale(1, "width"), [genHistoPythia, genHistoHerwig] )
    map(lambda h: h.Scale(scaleExtra), [genHistoPythia, genHistoHerwig] )

    maxima = []
    maxima.append(uncResult["max"])
    for t in [unc, central, genHistoHerwig, genHistoPythia]:
        maxima.append(t.GetMaximum())

    c = ROOT.TCanvas()
    c.Divide(1,2)
    c.cd(1)
    split = 0.2
    margin = 0.005
    ROOT.gPad.SetPad(.005, split+margin, .995, .995)
    c.cd(2)
    ROOT.gPad.SetPad(.005, .005, .995, split)
    c.cd(1)

    ROOT.gPad.SetTopMargin(0.1)
    #c.SetRightMargin(0.07)
    central.SetMaximum(max(maxima)*1.05)
    unc.SetFillColor(17);
    central.Draw()
    #central.GetXaxis().SetRangeUser(5,8)
    #central.GetYaxis().SetRangeUser(0,250000)

    central.GetXaxis().SetTitle("#Delta#eta")
    central.GetYaxis().SetTitle("#sigma [pb]")
    central.GetYaxis().SetTitleOffset(1.8)
    unc.Draw("2SAME")
    central.Draw("SAME")

    genHistoHerwig.Draw("SAME HIST")
    genHistoHerwig.SetLineColor(2)

    genHistoPythia.Draw("SAME HIST")
    genHistoPythia.SetLineColor(4)

    DrawMNPlots.banner()


    legend = ROOT.TLegend(0.6, 0.7, 0.9, 0.85)
    legend.SetFillColor(0)
    legend.AddEntry(central, "data", "pel")
    legend.AddEntry(unc, "syst. unc.", "f")
    legend.AddEntry(genHistoHerwig, "herwig", "l")
    legend.AddEntry(genHistoPythia, "pythia", "l")
    legend.Draw("SAME")    

    c.cd(2)
    frame = ROOT.gPad.DrawFrame(central.GetXaxis().GetXmin(), 0, central.GetXaxis().GetXmax(), 3)
    #frame.GetXaxis().SetRangeUser(5,8)

    yUp = array('d')
    yDown = array('d')
    x = array('d')
    y = array('d')
    xDown = array('d')
    xUp = array('d')

    y4Rivet = array('d')
    yUp4Rivet = array('d')
    yDown4Rivet = array('d')
    for iBin in xrange(1, central.GetNbinsX()+1):
        val =  central.GetBinContent(iBin)
        if val == 0: continue

        if val != 0:
            binErr  = central.GetBinError(iBin)
            errUp = unc.GetErrorYhigh(iBin-1)
            errDown =  unc.GetErrorYlow(iBin-1)
            valDown = errDown/val
            valUp =   errUp/val
            yDown.append(valDown)
            yUp.append(valUp)
            valDown4Rivet = math.sqrt(errDown*errDown + binErr*binErr  )
            valUp4Rivet   = math.sqrt(errUp*errUp + binErr*binErr  )
            yUp4Rivet.append(valUp4Rivet)
            yDown4Rivet.append(valDown4Rivet)
            #print valDown, valUp
        else:
           yUp.append(0)
           yDown.append(0)
        #print 
        x.append(unc.GetX()[iBin-1])
        y.append(1)
        ratio = unc.GetY()[iBin-1]/val
        if max(ratio-1., 1.-ratio)>0.001:
            raise Exception("Expected equal values")

        y4Rivet.append(val)
        xDown.append(unc.GetErrorXlow(iBin-1))
        xUp.append(unc.GetErrorXhigh(iBin-1))

    #print type(x)
    uncRatio =     ROOT.TGraphAsymmErrors(len(x), x, y, xDown, xUp, yDown, yUp)
    result4Rivet = ROOT.TGraphAsymmErrors(len(x), x, y4Rivet, xDown, xUp, yDown4Rivet, yUp4Rivet)

    #uncRatio = ROOT.TGraphAsymmErrors(len(x), x, y, xDown, xUp, yDown, yUp)

    uncRatio.SetFillStyle(3001)
    uncRatio.SetFillColor(17)
    uncRatio.Draw("2SAME")


    centralRatio = central.Clone()
    centralRatio.Divide(central)
    centralRatio.Draw("SAME")

    herwigRatio = genHistoHerwig.Clone()
    herwigRatio.Divide(central)

    pythiaRatio = genHistoPythia.Clone()
    pythiaRatio.Divide(central)

    herwigRatio.Draw("SAME L")
    pythiaRatio.Draw("SAME L")


    c.Print(indir+"/mergedUnfolded_{}.png".format(options.normalization))
    c.Print(indir+"/mergedUnfolded_{}.pdf".format(options.normalization))
    c.Print(indir+"/mergedUnfolded_{}.root".format(options.normalization))
    c.cd(1)
    ROOT.gPad.SetLogy()
    c.Print(indir+"/mergedUnfolded_{}_log.png".format(options.normalization))
    c.Print(indir+"/mergedUnfolded_{}_log.pdf".format(options.normalization))


    # rivet export
    from do import todoCatAll
    if len(todoCatAll) != 6:
        raise Exception("Error: inconsistent number of categories in todoCatAll")
    rivet = ROOT.TFile("toRivet.root", "RECREATE")
    rivetNum = todoCatAll.index(options.variant)+1
    if "area" == options.normalization:
        rivetNum += 10
    numAsStr = str(rivetNum)
    if len (numAsStr) == 1:
        numAsStr = "0"+numAsStr

    rivetName = "d"+numAsStr+"-x01-y01"
    print options.normalization, rivetNum, rivetName
    rivet.WriteTObject(result4Rivet, rivetName)
    rivet.Close()
    del rivet

    import os
    r2f = "/cvmfs/cms.cern.ch/slc6_amd64_gcc481/external/rivet/1.8.2-cms8/bin/root2flat"
    if not os.path.isfile(r2f):
        raise Exception("Cannot find root2flat. Rivet export failed")

    os.system(r2f + " toRivet.root")

    import yoda
    analysisobjects = yoda.readFLAT(rivetName+".dat")
    #print type(analysisobjects)
    #print analysisobjects.keys()
    for k in analysisobjects:
        pth = "/CMS_2015_FWD071/"+rivetName
        #print dir(analysisobjects[k])
        #analysisobjects[k].setTitle(pth)
        #analysisobjects[k].setPath(pth)
        analysisobjects[k].setAnnotation("Title", pth)
        analysisobjects[k].setAnnotation("Path",  pth)

    yoda.writeYODA(analysisobjects, rivetName+".yoda")



    # /cvmfs/cms.cern.ch/slc6_amd64_gcc481/external/rivet/1.8.2-cms8/bin/root2flat


if __name__ == "__main__":
    main()

