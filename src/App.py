import queue

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QPointF

from AcmiParse import ACMIFileParser
from Symbols import RadarContact
from TRTTClient import TRTTClientThread

def runRadarApp(arguments):

    data_queue = queue.Queue()

    # Create the Tacview RT Relemetry client
    # tac_client = TRTTClientThread(data_queue)
    # tac_client.start()
    
    app = QtWidgets.QApplication(arguments)
    window = Window()
    window.setGeometry(500, 300, 800, 600)
    window.show()
    app.exec()
    # tac_client.join() 
    return

class RadarWidget(QtWidgets.QGraphicsView):
    mapClicked = QtCore.pyqtSignal(QtCore.QPointF)

    def __init__(self, parent):
        super(RadarWidget, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._map = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._map)
        self._units = QtWidgets.QGraphicsItemGroup()
        self._scene.addItem(self._units)
        self.setScene(self._scene)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

    def hasMap(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._map.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasMap():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setMap(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
            self._map.setPixmap(pixmap)
            self._map.setZValue(-10)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            self._map.setPixmap(QtGui.QPixmap())
            self._map.setZValue(-10)
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasMap():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom <= 0:
                self.fitInView()
            else:
                self._zoom = 0

            def print_mat(matrix):
                for i in range (1,4):
                    for j in range (1,4):
                        val = getattr(matrix, f"m{j}{i}")()
                        print(  f"{val:1.04f}", end=" ")
                    print("")
            
            # print(self.viewportTransform().inverted()[0].mapRect(self.viewport().rect())) # Screenspace current viewable rect

            # view_mat = self.viewportTransform().inverted()[0]
            # print_mat(view_mat)

            trans_mat = self.transform().inverted()[0]
            # print_mat(trans_mat)
            for item in self._units.childItems():
                item.scaleInPlace(trans_mat.m11()) # Scale in place is only a member of the custom subclass in Symbols # TODO subclass QGraphicsItemGroup 
                
    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        elif not self._map.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._map.isUnderMouse():
            self.mapClicked.emit(self.mapToScene(event.position().toPoint()))
        super(RadarWidget, self).mousePressEvent(event)

    def updateContact(self,str):
        pass

    def draw_aircontact(self, x, y):

        aircraft = RadarContact(QPointF(x,y))
        self._units.addToGroup(aircraft)

        return aircraft
    
    def rm_aircontact(self, object_id):

        pass

class Window(QtWidgets.QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.map = RadarWidget(self)
        self.setWindowTitle("OpenRadar")
        # 'Load image' button
        self.btnLoad = QtWidgets.QToolButton(self)
        self.btnLoad.setText('Load image')
        self.btnLoad.clicked.connect(self.loadImage)
        # Button to change from drag/pan to getting pixel info
        self.btnPixInfo = QtWidgets.QToolButton(self)
        self.btnPixInfo.setText('Enter pixel info mode')
        self.btnPixInfo.clicked.connect(self.pixInfo)
        self.editPixInfo = QtWidgets.QLineEdit(self)
        self.editPixInfo.setReadOnly(True)
        self.map.mapClicked.connect(self.photoClicked)
        # Button to load ACMI
        self.btnUpdateMap = QtWidgets.QToolButton(self)
        self.btnUpdateMap.setText('Update MAP')
        self.btnUpdateMap.clicked.connect(self.updateMap)
        # Arrange layout
        VBlayout = QtWidgets.QVBoxLayout(self)
        VBlayout.addWidget(self.map)
        HBlayout = QtWidgets.QHBoxLayout()
        HBlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        HBlayout.addWidget(self.btnLoad)
        HBlayout.addWidget(self.btnPixInfo)
        HBlayout.addWidget(self.editPixInfo)
        HBlayout.addWidget(self.btnUpdateMap)
        VBlayout.addLayout(HBlayout)

    def loadImage(self):
        self.map.setMap(QtGui.QPixmap('maps/balkans_4k_airbases.png'))

    def pixInfo(self):
        self.map.toggleDragMode()

    def photoClicked(self, pos):
        if self.map.dragMode() == QtWidgets.QGraphicsView.DragMode.NoDrag:
            self.editPixInfo.setText('%d, %d' % (pos.x(), pos.y()))

    def updateMap(self, state):
        self.map.draw_aircontact(2000, 2000)
