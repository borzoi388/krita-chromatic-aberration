from krita import *
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QPushButton, QWidget, QSlider, QLabel, QLineEdit, QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QTimer

class ChromaticAberration(Extension):

    dialog = QDialog()

    perspective = False

    displaceXinput = QLineEdit()
    displaceYinput = QLineEdit()
    displaceSizeInput = QLineEdit()

    displacementLayout = QHBoxLayout()

    action = None

    hue = None
    hueSlider = None

    alphaLockCheck = QCheckBox()
    duplicateOriginalCheck = QCheckBox()

    selectButton = QPushButton()
    selectMenu = QMenu()
    XYaction = QAction("Displace")
    sizeAction = QAction("Perspective")
    
    hueWidget = QWidget()
    hueWidget2 = QWidget()

    crosschannel = None
    levels = None
    

    def __init__(self, parent):
        super().__init__(parent)


    def openDialog(self):
        self.dialog.exec()

    def closeDialog(self):
        self.dialog.done(0)

    def setDisplaceXY(self):
        self.perspective = False
        self.selectButton.setText("Displace")
        self.clearLayout(self.displacementLayout)
        for w in [QLabel("X:"), self.displaceXinput, QLabel("px"), QLabel("Y:"), self.displaceYinput, QLabel("px")]:
            self.displacementLayout.addWidget(w)
    
    def setDisplaceSize(self):
        self.perspective = True
        self.selectButton.setText("Perspective")
        self.clearLayout(self.displacementLayout)
        for w in [QLabel("Size:"), self.displaceSizeInput, QLabel("px")]:
            self.displacementLayout.addWidget(w)

    def checkValid(self):
        doc = Krita.instance().activeDocument()
        if (not doc is None and doc.activeNode().type() == "paintlayer" and doc.activeNode().visible()):
            self.openDialog()
        else:
            QMessageBox.information(None, "Cannot apply filter", "Make sure visible paint layer is selected in valid document", QMessageBox.Ok, QMessageBox.Ok)

    def clearLayout(self, layout):
        i = layout.count()-1
        while i > -1:
            layout.itemAt(i).widget().setParent(None)
            i-=1

    def updateHue(self, value):
        self.hue = value

        palette = self.hueWidget.palette()
        palette.setColor(self.hueWidget.backgroundRole(), QColor.fromHsv(value, 255, 255))
        self.hueWidget.setPalette(palette)

        temp = value-180 if value+180 > 359 else value+180
        palette.setColor(self.hueWidget2.backgroundRole(), QColor.fromHsv(temp, 255, 255))
        self.hueWidget2.setPalette(palette)

        self.hueWidget.update()
        self.hueWidget2.update()

    def doAction(self, action):
        Krita.instance().action(action).trigger()
        Krita.instance().activeDocument().waitForDone()

    def applyFilter(self):
        alphaLock = self.alphaLockCheck.isChecked()
        duplicateOriginal = self.duplicateOriginalCheck.isChecked()

        self.dialog.done(0)
        app = Krita.instance()
        doc = app.activeDocument()

        # creating the duplicate
        
        if duplicateOriginal:
            dupe = doc.activeNode().duplicate()
            doc.activeNode().setName("Duplicate of "+dupe.name())
            doc.activeNode().setVisible(False)
            doc.waitForDone()
            doc.activeNode().parentNode().addChildNode(dupe, doc.activeNode())
            doc.waitForDone()

        layer = doc.activeNode()
        parent = layer.parentNode()

        # creating the temp merge layer for alphalock

        if alphaLock:
            tempLayer = doc.createNode(layer.name(), "paintlayer")
            parent.addChildNode(tempLayer, layer)
            parent.removeChildNode(layer)
            parent.addChildNode(layer, tempLayer)
            doc.setActiveNode(layer)


        self.doAction("add_new_paint_layer")


        parent.addChildNode(doc.createNode("group", "grouplayer"), doc.activeNode())
        group = doc.activeNode()

        blackInfo = InfoObject()
        blackInfo.setProperty("color", QColor.fromRgb(0, 0, 0))
        selection = Selection()
        selection.select(0, 0, doc.width(), doc.height(), 255)

        group.addChildNode(doc.createNode("temp", "paintlayer"), None)
        doc.waitForDone()

        if self.perspective:
            fill = doc.createFillLayer("fill", "color", blackInfo, selection)
            doc.waitForDone()
            group.addChildNode(fill, None)
            doc.waitForDone()
            fill.mergeDown()
            doc.waitForDone()
        group.addChildNode(layer.duplicate(), None)
        doc.waitForDone()
        doc.activeNode().mergeDown()
        doc.waitForDone()
        doc.activeNode().cropNode(0, 0, doc.width(), doc.height())

        info = InfoObject()
        info.setProperty("color", QColor.fromHsv(self.hue, 255, 255))

        group.addChildNode(doc.createFillLayer("fill", "color", info, selection), doc.activeNode())
        doc.waitForDone()
        doc.activeNode().setBlendingMode("multiply")
        doc.waitForDone()
        doc.activeNode().setInheritAlpha(True)
        doc.waitForDone()

        doc.activeNode().mergeDown()
        doc.waitForDone()
        group.mergeDown()
        doc.waitForDone()

        self.levels.apply(doc.activeNode(), 0, 0, doc.width(), doc.height())
        doc.waitForDone()

        if self.perspective:
            self.crosschannel.apply(doc.activeNode(), 0, 0, doc.width(), doc.height())
            doc.waitForDone()
        subLayer = doc.activeNode()
        subLayer.setBlendingMode("subtract")
        doc.waitForDone()

        parent.addChildNode(subLayer.duplicate(), subLayer)
        doc.waitForDone()
        addLayer = doc.activeNode()
        addLayer.setBlendingMode("add")
        doc.waitForDone()

        if self.perspective:
            size = int(self.displaceSizeInput.text())
            subLayer.scaleNode(QPointF(doc.width()/2, doc.height()/2), doc.width()+2*size, doc.height()+2*size, "bicubic")
            doc.waitForDone()
            addLayer.scaleNode(QPointF(doc.width()/2, doc.height()/2), doc.width()-2*size, doc.height()-2*size, "bicubic")
        else:
            displaceX = int(self.displaceXinput.text())
            displaceY = int(self.displaceYinput.text())
            subLayer.move(-displaceX, -displaceY)
            doc.waitForDone()
            addLayer.move(displaceX, displaceY)
        doc.waitForDone()

        alphaGroup = None

        if alphaLock:
            parent.addChildNode(doc.createNode("group", "grouplayer"), doc.activeNode())
            alphaGroup = doc.activeNode()

            layerDupe = layer.duplicate()
            subDupe = subLayer.duplicate()
            addDupe = addLayer.duplicate()

            alphaGroup.addChildNode(layerDupe, None)
            doc.waitForDone()
            layer.remove()
            doc.waitForDone()

            alphaGroup.addChildNode(subDupe, layerDupe)
            doc.waitForDone()
            subLayer.remove()
            doc.waitForDone()
            
            alphaGroup.addChildNode(addDupe, subDupe)
            doc.waitForDone()
            addLayer.remove()
            doc.waitForDone()

            subLayer = subDupe
            addLayer = addDupe

            subLayer.setInheritAlpha(True)
            addLayer.setInheritAlpha(True)
            doc.waitForDone()


        
        subLayer.mergeDown()
        doc.waitForDone()
        addLayer.mergeDown()
        doc.waitForDone()

        if alphaLock:
            alphaGroup.mergeDown()
    
        app.activeDocument().refreshProjection()

        

        

    # Krita.instance() exists, so do any setup work
    def setup(self):

        self.updateHue(0)
        self.dialog.setWindowTitle("Filter: Chromatic Aberration")

        for w in [self.displaceXinput, self.displaceYinput, self.displaceSizeInput]:
            w.setInputMask('000')
            w.setText('0')

        # crosschannel

        self.crosschannel = Krita.instance().filter("crosschannel")
        cfg = self.crosschannel.configuration()
        
        cfg.setProperty("nTransfers", 8)
        cfg.setProperty("driver4", 7)
        cfg.setProperty("activeCurve", 4)
        cfg.setProperty("curve4", "0,0;1,1")

        # levels

        self.levels = Krita.instance().filter("levels")
        cfg2 = self.levels.configuration()

        cfg2.setProperty("outblackvalue", 1)

        # select
        selectLayout = QHBoxLayout()
        self.XYaction.triggered.connect(self.setDisplaceXY)
        self.sizeAction.triggered.connect(self.setDisplaceSize)

        
        self.selectButton = QPushButton()
        self.selectButton.setMenu(self.selectMenu)

        self.selectMenu.addAction(self.XYaction)
        self.selectMenu.addAction(self.sizeAction)
        self.selectMenu.setActiveAction(self.XYaction)

        self.alphaLockCheck.setText("Alpha Lock")
        self.alphaLockCheck.setToolTip("Recommended for layers with transparent backgrounds")
        self.duplicateOriginalCheck.setText("Duplicate Original")
        self.duplicateOriginalCheck.setChecked(True)
        self.alphaLockCheck.setChecked(True)
        
        for w in [self.selectButton, self.alphaLockCheck, self.duplicateOriginalCheck]:
            selectLayout.addWidget(w)

        self.setDisplaceXY()


        # hue
        hueLayout = QHBoxLayout()

        self.hueSlider = QSlider(Qt.Orientation.Horizontal)
        self.hueSlider.valueChanged.connect(self.updateHue)
        self.hueSlider.setRange(0, 359)

        for w in [self.hueWidget, self.hueWidget2]:
            w.setMinimumSize(50, 50)
            w.setAutoFillBackground(True)

        hueLayout.addWidget(QLabel("Hue:"))
        hueLayout.addWidget(self.hueSlider)

        hueLayout.addWidget(self.hueWidget)
        hueLayout.addWidget(self.hueWidget2)

        # footer
        footerLayout = QHBoxLayout()
        
        submitBtn = QPushButton("OK")
        cancelBtn = QPushButton("Cancel")
        submitBtn.clicked.connect(self.applyFilter)
        cancelBtn.clicked.connect(self.closeDialog)

        footerLayout.addWidget(cancelBtn)
        footerLayout.addWidget(submitBtn)

        # everything
        mainLayout = QVBoxLayout()

        mainLayout.addLayout(selectLayout)
        mainLayout.addLayout(self.displacementLayout)
        mainLayout.addLayout(hueLayout)
        mainLayout.addLayout(footerLayout)

        self.dialog.setLayout(mainLayout)

    # called after setup(self)
    def createActions(self, window):
        app = Krita.instance()
        self.action = window.createAction("", "Chromatic Aberration")
        self.action.triggered.connect(self.checkValid)
        app.notifier().setActive(True)