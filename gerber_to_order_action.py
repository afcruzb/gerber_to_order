import pcbnew
import os
import shutil
import wx
import locale
import zipfile

outputDirName = "gerber_to_order"

layers = [
    [ pcbnew.F_Cu,     'GTL' ],
    [ pcbnew.B_Cu,     'GBL' ],
    [ pcbnew.F_SilkS,  'GTO' ],
    [ pcbnew.B_SilkS,  'GBO' ],
    [ pcbnew.F_Mask,   'GTS' ],
    [ pcbnew.B_Mask,   'GBS' ],
    [ pcbnew.Edge_Cuts,'GML' ],
    [ pcbnew.In1_Cu,   'GL2' ],
    [ pcbnew.In2_Cu,   'GL3' ],
    [ pcbnew.In3_Cu,   'GL4' ],
    [ pcbnew.In4_Cu,   'GL5' ],
]

def removeFile(fileName):
    if os.path.exists(fileName):
        os.remove(fileName)

def renameFile(src, dst):
    removeFile(dst)
    os.rename(src, dst)

def createZip(pcbServiceName, mergeNpth, useAuxOrigin, excellonFormat):
    board = pcbnew.GetBoard()
    boardFileName = board.GetFileName()
    boardDirPath = os.path.dirname(boardFileName)
    boardProjectName = (os.path.splitext(os.path.basename(boardFileName)))[0]

    outputDirPath = '%s/%s' % (boardDirPath, outputDirName)
    gerberDirName = '%s_for_%s' % (boardProjectName, pcbServiceName)
    gerberDirPath = '%s/%s' % (outputDirPath, gerberDirName)
    drillFilePath = '%s/%s.TXT' % (gerberDirPath, boardProjectName)
    npthFilePath = '%s/%s-NPTH.TXT' % (gerberDirPath, boardProjectName)
    zipFilePath = '%s/%s.zip' % (outputDirPath, gerberDirName)
    if not os.path.exists(outputDirPath):
        os.mkdir(outputDirPath)
    if os.path.exists(gerberDirPath):
        shutil.rmtree(gerberDirPath)
    os.mkdir(gerberDirPath)
    targetLayerCount = board.GetCopperLayerCount() + 5

    # PLOT
    pc = pcbnew.PLOT_CONTROLLER(board)
    po = pc.GetPlotOptions()

    po.SetOutputDirectory(gerberDirPath)
    po.SetPlotValue(True)
    po.SetPlotReference(True)
    po.SetExcludeEdgeLayer(False)
    po.SetLineWidth(pcbnew.FromMM(0.1))
    po.SetSubtractMaskFromSilk(True)
    po.SetUseAuxOrigin(useAuxOrigin)

    for layer in layers:
        targetname = '%s/%s.%s' % (gerberDirPath, boardProjectName, layer[1])
        removeFile(targetname)
    removeFile(drillFilePath)
    removeFile(npthFilePath)
    removeFile(zipFilePath)

    plotFileNames = []
    for i in range(targetLayerCount):
        layer = layers[i]
        pc.SetLayer(layer[0])
        pc.OpenPlotfile(layer[1], pcbnew.PLOT_FORMAT_GERBER, layer[1])
        pc.PlotLayer()
        plotFileNames.append(pc.GetPlotFileName())
    pc.ClosePlot()

    for i in range(targetLayerCount):
        layer = layers[i]
        newFileName = '%s/%s.%s' % (gerberDirPath, boardProjectName, layer[1])
        renameFile(plotFileNames[i], newFileName)

    # DRILL
    ew = pcbnew.EXCELLON_WRITER(board)
    ew.SetFormat(True, excellonFormat, 3, 3)
    offset = pcbnew.wxPoint(0,0)
    if(useAuxOrigin):
        offset = board.GetAuxOrigin()
    ew.SetOptions(False, False, offset, mergeNpth)
    ew.CreateDrillandMapFilesSet(gerberDirPath,True,False)
    if mergeNpth:
        renameFile('%s/%s.drl' % (gerberDirPath, boardProjectName), drillFilePath)
    else:
        renameFile('%s/%s-PTH.drl' % (gerberDirPath, boardProjectName), drillFilePath)
        renameFile('%s/%s-NPTH.drl' % (gerberDirPath, boardProjectName), npthFilePath)

    # ZIP
    shutil.make_archive(zipFilePath, 'zip', outputDirPath, gerberDirName)

    return zipFilePath

class GerberToOrderAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Gerber to order"
        self.category = "A descriptive category name"
        self.description = "A plugin to creage zip compressed gerber files to order PCB for Elecrow, FusionPCB or PCBWay."
        self.show_toolbar_button = False # Optional, defaults to False
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        class Dialog(wx.Dialog):
            def __init__(self, parent):
                wx.Dialog.__init__(self, parent, id=-1, title='Gerber to order')
                self.panel = wx.Panel(self)
                self.description = wx.StaticText(self.panel, wx.ID_ANY, "hello world", pos=(20,10))
                # self.mergeNpth = wx.CheckBox(self.panel, wx.ID_ANY, getstr('MERGE',lang), pos=(30,40))
                # self.useAuxOrigin = wx.CheckBox(self.panel, wx.ID_ANY, getstr('AUXORIG',lang), pos=(30,60))
                # self.zeros = wx.RadioBox(self.panel,wx.ID_ANY, getstr('ZEROS',lang), pos=(30,90), choices=[getstr('DECIMAL',lang), getstr('SUPPRESS',lang)], style=wx.RA_HORIZONTAL)
                self.execbtn = wx.Button(self.panel, wx.ID_ANY, 'exec', pos=(30,150))
                self.clsbtn = wx.Button(self.panel, wx.ID_ANY, 'close', pos=(170,150))
                # self.mergeNpth.SetValue(mergeNpth)
                # self.useAuxOrigin.SetValue(useAuxOrigin)
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
            def OnClose(self,e):
                e.Skip()
                self.Close()
            def OnExec(self,e):
                # mergeNpth = True if self.mergeNpth.GetValue() else False
                # useAuxOrigin = True if self.useAuxOrigin.GetValue() else False
                # excellonFormat = (EXCELLON_WRITER.DECIMAL_FORMAT, EXCELLON_WRITER.SUPPRESS_LEADING)[self.zeros.GetSelection()]
                try:
                    zipFilePath = createZip(
                        pcbServiceName = 'Elecrow',
                        mergeNpth = False,
                        useAuxOrigin = True,
                        excellonFormat = pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT # pcbnew.EXCELLON_WRITER.SUPPRESS_LEADING
                    )
                    # wx.MessageBox(getstr('COMPLETE')%zip_fname, 'Gerber Zip', wx.OK|wx.ICON_INFORMATION)
                    wx.MessageBox(zipFilePath, 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox('Error: ' + str(e), 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
