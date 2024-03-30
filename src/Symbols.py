import math
from PyQt6 import QtWidgets
from PyQt6.QtCore import QRectF, QPointF, QSizeF, QLineF, Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QGlyphRun, QFont, QFontDatabase


class RadarContact(QtWidgets.QGraphicsItem):

    def __init__(self, center: QPointF, 
                 heading: float=0, 
                 altitude: float=0, 
                 velocity: float=0, 
                 callsign: str="", 
                 pilot: str="", 
                 scale: float=1,
                 size: float=150, 
                 parent=None) -> None:
        super(RadarContact, self).__init__(parent)
        self._center = center
        self._initial_size = size
        self._size = size
        self._scale = scale
        self._color = QColor(0,0,255,255)
        self.heading = float(heading)
        self.altitude = float(altitude)
        self.velocity = float(velocity)
        self.callsign = callsign
        self.pilot = pilot
        
        # TODO move this
        # font_File_path = "fonts/app6a05.ttf"; # Specify the path to your font file
        # self.font_id = self.load_custom_font(font_File_path)
        
    def update(self,
                center: QPointF,
                heading: float=0, 
                altitude: float=0, 
                velocity: float=0,
                callsign: str="", 
                pilot: str="", 
                scale: float=1):
        self._center = center
        self._scale = float(scale)
        if heading: self.heading = float(heading)
        if altitude: self.altitude = float(altitude)
        if velocity: self.velocity = float(velocity)
        self.callsign = callsign
        self.pilot = pilot
        if not self.velocity:
            pass
        
    def load_custom_font(self, font_File_path):
        font_id = QFontDatabase.addApplicationFont(font_File_path)
        if font_id:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if len(font_families):
                print(font_families)
                return font_id

    def boundingRect(self) -> QRectF:
        return QRectF(self._center.x()-self._size/2.0, self._center.y()-self._size/2.0, self._size, self._size)

    def shapeRect(self) -> QRectF:
        # Point 1/8 the way between center and bounding top left
        top_left = QPointF(self._center.x() - self._size/16.0, self._center.y() - self._size/16.0) 
        area = QSizeF(self._size/8.0, self._size/8.0)

        return QRectF(top_left, area)

    def getVelLine(self) -> QLineF:

        vel_scale = self.velocity / 1000.0
        vel_vec_len_px = min(self._size/2.0, vel_scale*self._size/2.0)

        start_pt = self._center

        heading_rad = math.radians(self.heading-90) # -90 rotaes north to up
        end_x = start_pt.x() + vel_vec_len_px*math.cos(heading_rad)
        end_y = start_pt.y() + vel_vec_len_px*math.sin(heading_rad)
        end_pt = QPointF(end_x, end_y)

        return QLineF(start_pt, end_pt)

    def scaleInPlace(self, scale):
        self._scale = scale
        self._size = self._initial_size * scale

    def paint(self, painter: QPainter | None, 
              option: QtWidgets.QStyleOptionGraphicsItem | None, 
              widget: QtWidgets.QWidget | None = ...) -> None:
        
        
        # Draw Velocity Line
        pen = QPen(QBrush(QColor(0,0,255,255)), self._size/50.0)
        painter.setPen(pen)
        painter.drawLine(self.getVelLine())
        
        painter.drawRect(self.shapeRect())
        

        # pen = QPen(Qt.GlobalColor.blue)
        # pen.setWidth = 4000
        # pen = QPen(QBrush(Qt.GlobalColor.blue), self._size/20.0)
        # painter.setPen(pen)
        # painter.drawArc(self.shapeRect(), 16*180, -16*180)
    
        # # Scale font size
        # font = QFont("MapSym-EN-Air", 30)
        # font.setBold(True)
        # font.setWeight(QFont::Black)
        # scaled_font = font
        # scaled_font.setPointSizeF(scaled_font.pointSizeF() * self._scale)
        # painter.setFont(scaled_font)

        # # Draw text
        # text = "0" # Character to draw
        # painter.drawText(self.shapeRect(), Qt.AlignmentFlag.AlignCenter, text)
        # # painter.drawText(self.shapeRect(), Qt.AlignmentFlag.AlignCenter, "0")
        
        
