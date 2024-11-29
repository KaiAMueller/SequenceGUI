import glob
import os
from datetime import datetime
from enum import Enum

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.code_generation.artiq_code_generator as artiq_code_generator
import gui.settings as settings
import gui.widgets.Dock as Dock


class Level(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class GridLayoutWidget(QtW.QWidget):
    # wrapper for grid layout
    def __init__(self, parent=None):
        QtW.QWidget.__init__(self, parent)
        self.layout = QtW.QGridLayout()
        self.setLayout(self.layout)

    def addWidget(self, item, row=0, col=0, rowspan=1, colspan=1):
        self.layout.addWidget(item, row, col, rowspan, colspan)


class View(Dock.Dock):
    # creates the viewable interface, only handles very simple logic
    def __init__(self, gui):
        Dock.Dock.__init__(self, "📷 Camera", gui)

        # create MVC classes
        self.controller = Controller(self)

        self.grid = GridLayoutWidget()
        self.setWidget(self.grid)

        self.b1 = QtW.QCheckBox("Readout Camera")
        self.b1.setChecked(False)
        self.b1.stateChanged.connect(lambda: self.controller.checkBox())
        self.grid.addWidget(self.b1, 0, 1)

        self.label2 = QtW.QLabel(self)
        self.label2.setText("🔴🔴🔴🔴🔴")
        self.grid.addWidget(self.label2, 0, 3, colspan=3)

        self.labelNumImg = QtW.QLabel(self)
        self.labelNumImg.setText("Num Images:")
        self.grid.addWidget(self.labelNumImg, 1, 1)
        self.lineEdit = QtW.QLineEdit(self)
        self.lineEdit.setValidator(QtG.QIntValidator())
        self.lineEdit.setText("2")
        self.lineEdit.setFixedWidth(40)
        self.grid.addWidget(self.lineEdit, 1, 2)
        self.labelExposure = QtW.QLabel(self)
        self.labelExposure.setText("Exposure µs:")
        self.grid.addWidget(self.labelExposure, 1, 3)
        self.lineEditExposure = QtW.QLineEdit(self)
        self.lineEditExposure.setValidator(QtG.QIntValidator())
        self.lineEditExposure.setText("125")
        self.lineEditExposure.setFixedWidth(40)
        self.grid.addWidget(self.lineEditExposure, 1, 4)

        self.label = QtW.QLabel(self)
        self.label.setScaledContents(True)
        self.label.setSizePolicy(QtW.QSizePolicy.Policy.Ignored, QtW.QSizePolicy.Policy.Ignored)
        self.grid.addWidget(self.label, 2, 1, colspan=5)


class Controller:

    grasshopperClassCode = """
class Grasshopper:
    def __init__(self, dev="auto"):
        self.simulation = FORCE_SIMULATION or (dev is None)
        self.cam = self._get_camera(dev)
        if self.cam:
            self.cam.Init()
            self.nodemap = self.cam.GetNodeMap() # needs to be called after Init
        else:
            raise Exception("No camera found")
        self.acquisitionActive = False

    def close(self):
        if self.cam:
            self.endAcquisition()
            self.cam.DeInit()
        del self.cam
        self.system.ReleaseInstance()

    def _get_camera(self, dev):
        self.system = PySpin.System.GetInstance()
        version = self.system.GetLibraryVersion()
        cam_list = self.system.GetCameras()
        num_cams = cam_list.GetSize()
        CAM = None
        if num_cams == 0:
            cam_list.Clear()
            return CAM
        for i, cam in enumerate(cam_list):
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            device_vendor_name = _getInfo(nodemap_tldevice, 'DeviceVendorName')
            device_model_name = _getInfo(nodemap_tldevice, 'DeviceModelName')
            device_serial_number = _getInfo(nodemap_tldevice, 'DeviceSerialNumber')
            if dev == device_serial_number:
                CAM = cam
            elif dev == "auto" and i==0:
                CAM = cam
        if not CAM:
            logger.error("specified camera {} not found".format(dev))
        del cam
        cam_list.Clear()
        return CAM


    def configure_exposure(self,exposure_time_to_set=1000.0,gain=0.0):
        try:
            result = True

            if self.cam.PixelFormat.GetAccessMode() != PySpin.RW:
                print('cant write pixelformat')
                return False
            self.cam.PixelFormat.SetValue(PySpin.PixelFormat_Mono16)

            if self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                return False    
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)

            if self.cam.ExposureTime.GetAccessMode() != PySpin.RW:
                return False
            if exposure_time_to_set > self.cam.ExposureTime.GetMax():
                logging.error("exposure longer than " + str(self.cam.ExposureTime.GetMax()))
                return False
            self.cam.ExposureTime.SetValue(exposure_time_to_set)

            if self.cam.GammaEnable.GetAccessMode() != PySpin.RW:
                return False    
            self.cam.GammaEnable.SetValue(False)
            
            if self.cam.GainAuto.GetAccessMode() != PySpin.RW:
                return False    
            self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)

            if self.cam.Gain.GetAccessMode() != PySpin.RW:
                return False
            if gain > self.cam.Gain.GetMax():
                logging.error("gain bigger than " + str(self.cam.Gain.GetMax()))
                return False
            if gain < self.cam.Gain.GetMin():
                logging.error("gain smaller than " + str(self.cam.Gain.GetMin()))
                return False
            self.cam.Gain.SetValue(gain)

        except PySpin.SpinnakerException as ex:
            logging.error(ex)
            result = False

        return result

    def configure_trigger(self):
        result = True

        try:
            node_trigger_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode("TriggerMode"))
            if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
                return False

            node_trigger_mode_off = node_trigger_mode.GetEntryByName("Off")
            if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
                return False

            node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())
            node_trigger_source = PySpin.CEnumerationPtr(self.nodemap.GetNode("TriggerSource"))
            if not PySpin.IsAvailable(node_trigger_source) or not PySpin.IsWritable(node_trigger_source):
                return False

            if CHOSEN_TRIGGER == TriggerType.SOFTWARE:
                node_trigger_source_software = node_trigger_source.GetEntryByName("Software")
                if not PySpin.IsAvailable(node_trigger_source_software) or not PySpin.IsReadable(
                        node_trigger_source_software):
                    return False
                node_trigger_source.SetIntValue(node_trigger_source_software.GetValue())

            elif CHOSEN_TRIGGER == TriggerType.HARDWARE:
                node_trigger_source_hardware = node_trigger_source.GetEntryByName("Line0")
                if not PySpin.IsAvailable(node_trigger_source_hardware) or not PySpin.IsReadable(
                        node_trigger_source_hardware):
                    return False
                node_trigger_source.SetIntValue(node_trigger_source_hardware.GetValue())
                
                node_trigger_selector = PySpin.CEnumerationPtr(self.nodemap.GetNode("TriggerSelector"))
                node_trigger_selector_FS = node_trigger_selector.GetEntryByName("FrameStart")
                if not PySpin.IsAvailable(node_trigger_selector_FS) or not PySpin.IsReadable(
                        node_trigger_selector_FS):
                    return False
                node_trigger_selector.SetIntValue(node_trigger_selector_FS.GetValue())
                
                node_trigger_polarity = PySpin.CEnumerationPtr(self.nodemap.GetNode("TriggerActivation"))
                node_trigger_polarity_rising = node_trigger_polarity.GetEntryByName("RisingEdge")
                if not PySpin.IsAvailable(node_trigger_polarity_rising) or not PySpin.IsReadable(
                        node_trigger_polarity_rising):
                    return False
                node_trigger_polarity.SetIntValue(node_trigger_polarity_rising.GetValue())

            node_trigger_mode_on = node_trigger_mode.GetEntryByName("On")
            if not PySpin.IsAvailable(node_trigger_mode_on) or not  PySpin.IsReadable(node_trigger_mode_on):
                return False

            node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())

        except PySpin.SpinnakerException as ex:
            logging.error(ex)
            return False

        return result

    def configure_chunk_data(self):
        try:
            result = True

            chunk_mode_active = PySpin.CBooleanPtr(self.nodemap.GetNode('ChunkModeActive'))

            if PySpin.IsAvailable(chunk_mode_active) and PySpin.IsWritable(chunk_mode_active):
                chunk_mode_active.SetValue(True)

            chunk_selector = PySpin.CEnumerationPtr(self.nodemap.GetNode('ChunkSelector'))

            if not PySpin.IsAvailable(chunk_selector) or not PySpin.IsReadable(chunk_selector):
                return False

            entries = [PySpin.CEnumEntryPtr(chunk_selector_entry) for chunk_selector_entry in chunk_selector.GetEntries()]


            for chunk_selector_entry in entries:
                if not PySpin.IsAvailable(chunk_selector_entry) or not PySpin.IsReadable(chunk_selector_entry):
                    continue

                chunk_selector.SetIntValue(chunk_selector_entry.GetValue())

                chunk_str = '\t {}:'.format(chunk_selector_entry.GetSymbolic())

                chunk_enable = PySpin.CBooleanPtr(self.nodemap.GetNode('ChunkEnable'))

                if not PySpin.IsAvailable(chunk_enable):
                    result = False
                elif chunk_enable.GetValue() is True:
                    pass
                elif PySpin.IsWritable(chunk_enable):
                    chunk_enable.SetValue(True)
                else:
                    result = False

        except PySpin.SpinnakerException as ex:
            result = False

        return result

    def acquireImage(self):
        ''' this function acquires an image into the camera buffer '''
        if not self.cam:
            return
        if not self.acquisitionActive:
            self.acquisitionActive = True
            self.cam.BeginAcquisition()
        else:
            pass

    def ArmCamera(self,exposure,gain):
        if not self.configure_exposure(exposure,gain):
            raise Exception("couldnt set exposure")
        if not self.configure_trigger():
            raise Exception("couldnt configure trigger")
        if not self.configure_chunk_data():
            raise Exception("couldnt configure chunk data")
        self.acquireImage()


    def getImage(self, timeout=500 , EndAcquisition=True, filename=""):
        ''' returns the latest image from the camera buffer. blocking if there is no image in the buffer '''
        if not self.acquisitionActive:
            raise Exception("cant get picture, acquisition inactive")
            return
        image_result=None
        try:
            image_result = self.cam.GetNextImage(timeout)
            
            if image_result.IsIncomplete():
                raise Exception("incomplete image")
            else:
                metadata = chunk_data_from_image(image_result)
                #processor = PySpin.ImageProcessor()
                #image_converted = processor.Convert(image_result, PySpin.PixelFormat_Mono16)
                return image_result.GetNDArray().T.copy(order="C"), metadata
        except PySpin.SpinnakerException as ex:
            print(ex)
            raise Exception("couldnt get image")
            return
        finally:
            if image_result is not None:
                import os
                print("saving in ", os.getcwd())
                image_result.Save(filename + ".tiff")
                image_result.Release()
            if EndAcquisition:
                self.endAcquisition()
            
    def getImages(self, NumImages, rid):
        images = list()
        metadata = list()
        try:
            for i in range(NumImages):
                name = str(i)
                if i == 0:
                    name = "atom"
                if i == 1:
                    name = "beam"
                now = datetime.datetime.now()
                image, meta = self.getImage(EndAcquisition=False, filename= now.strftime("%Y%m")+"_" + now.strftime("%d%H") + "_" + str(rid) + "_" + name)
                images.append(image)
                metadata.append(meta)
            metadata = {key: [m[key] for m in metadata] for key in metadata[0]}#dict of arrays instead of array of dicts
            return images, metadata
        finally:
            self.endAcquisition()
        
        
            
    def setFrameBufferCount(self, NUM):
        ''' sets the frame buffer count to store NUM images on the camera before they need to be downloaded '''
        s_node_map = self.cam.GetTLStreamNodeMap()
        stream_buffer_count_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferCountMode'))
        if not PySpin.IsAvailable(stream_buffer_count_mode) or not PySpin.IsWritable(stream_buffer_count_mode):
            return False
        stream_buffer_count_mode_manual = PySpin.CEnumEntryPtr(stream_buffer_count_mode.GetEntryByName('Manual'))
        if not PySpin.IsAvailable(stream_buffer_count_mode_manual) or not PySpin.IsReadable(stream_buffer_count_mode_manual):
            return False
        stream_buffer_count_mode.SetIntValue(stream_buffer_count_mode_manual.GetValue())
        buffer_count = PySpin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
        if not PySpin.IsAvailable(buffer_count) or not PySpin.IsWritable(buffer_count):
            return False
        if NUM <= buffer_count.GetMax():
            buffer_count.SetValue(NUM)
        else:
            return False
        return True

    def setBufferHandlingMode(self, mode):
        s_node_map = self.cam.GetTLStreamNodeMap()
        handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(handling_mode) or not PySpin.IsWritable(handling_mode):
            return False
        handling_mode_entry = handling_mode.GetEntryByName(mode)
        handling_mode.SetIntValue(handling_mode_entry.GetValue())
        return True        
    
    def endAcquisition(self):
        if self.acquisitionActive:
            self.cam.EndAcquisition()
            self.acquisitionActive = False

        
    def setROI(self, width, height, offsetX, offsetY):
        success = True
        if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
            self.cam.Width.SetValue(width)
        else:
            return False
        if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
            self.cam.Height.SetValue(height)
        else:
            return  False
        if self.cam.OffsetX.GetAccessMode() == PySpin.RW:
            self.cam.OffsetX.SetValue(offsetX)
        else:
            return False
        if self.cam.OffsetY.GetAccessMode() == PySpin.RW:
            self.cam.OffsetY.SetValue(offsetY)
        else:
            return False
        
        return True


    def disableROI(self):
        '''
        resets the ROI to full image
        '''
        offsetX = self.cam.OffsetX.GetMin()
        offsetY = self.cam.OffsetY.GetMin()
        if self.cam.OffsetX.GetAccessMode() == PySpin.RW:
            self.cam.OffsetX.SetValue(offsetX)
        else:
            return False
        
        if self.cam.OffsetY.GetAccessMode() == PySpin.RW:
            self.cam.OffsetY.SetValue(offsetY)
        else:
            return False
        width = self.cam.Width.GetMax()
        height = self.cam.Height.GetMax()
        if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
            self.cam.Width.SetValue(width)
        else:
            return False
        if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
            self.cam.Height.SetValue(height)
        else:
            return False
        return True
 """
    grasshopperClassCodeIndented = ""

    def __init__(self, view):
        self.view = view
        Controller.controller = self

        Controller.grasshopperClassCodeIndented = Controller.grasshopperClassCode.replace("\n", "\n    ")

    def imgUpdater(self):
        project = settings.getCratePath()
        listOfImages = glob.glob(project + "/results/**/*.tiff", recursive=True)
        listOfImages.sort(key=lambda x: os.path.getctime(x))
        if len(listOfImages) < 2:
            return
        latestImage = listOfImages[-2]
        pixmap = QtG.QPixmap(latestImage)
        if not pixmap.isNull():
            size = self.view.label.size()
            self.view.label.setPixmap(pixmap)
            self.view.label.resize(size)
            imgDate = datetime.fromtimestamp(os.path.getctime(latestImage))
            timeRating = "🔴" if (datetime.now() - imgDate).seconds > 10 else "🟢"
            if (datetime.now() - imgDate).seconds < 0:
                timeRating = "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
            self.view.label2.setText(timeRating + imgDate.strftime("%Y/%m/%d, %H:%M:%S"))

    def checkBox(self):
        if self.view.b1.isChecked():
            artiq_code_generator.externalInitGenerators.append(Controller.initGenerator)
            #            artiq_code_generator.externalPrepareGenerators.append(Controller.prepareGenerator)
            self.analyzePointer = lambda: self.analyzeGenerator()
            artiq_code_generator.externalAnalyzeGenerators.append(self.analyzePointer)
            self.funcPointer = lambda: self.functionGenerator()
            artiq_code_generator.externalFunctionGenerators.append(self.funcPointer)
            artiq_code_generator.externalImportGenerators.append(Controller.importGenerator)
            artiq_code_generator.externalBuildGenerators.append(Controller.buildGenerator)
            self.timer = QtC.QTimer(self.view, timeout=self.imgUpdater, interval=1000)
            self.timer.start()
        else:
            artiq_code_generator.externalInitGenerators.remove(Controller.initGenerator)
            #            artiq_code_generator.externalPrepareGenerators.remove(Controller.prepareGenerator)
            artiq_code_generator.externalAnalyzeGenerators.remove(self.analyzePointer)
            artiq_code_generator.externalFunctionGenerators.remove(self.funcPointer)
            artiq_code_generator.externalImportGenerators.remove(Controller.importGenerator)
            artiq_code_generator.externalBuildGenerators.remove(Controller.buildGenerator)
            self.view.label2.setText("🔴🔴🔴🔴🔴")
            self.timer.stop()

    def buildGenerator():
        return """
        self.setattr_device("scheduler")"""

    def initGenerator():
        return """
        self.initCam()"""

    def analyzeGenerator(self):
        return f"""
        self.grasshopper.getImages({self.view.lineEdit.text()}, self.scheduler.rid)"""

    def importGenerator():
        return [
            "import PySpin",
            "import logging",
            "import datetime",
            """
class TriggerType:
    SOFTWARE = 1
    HARDWARE = 2

class ChunkDataTypes:
    IMAGE = 1
    NODEMAP = 2

CHOSEN_TRIGGER = TriggerType.HARDWARE
CHOSEN_CHUNK_DATA_TYPE = ChunkDataTypes.IMAGE
FORCE_SIMULATION = False""",
            """def _getInfo(nodemap_tldevice, s):
    device_info = ''
    node_device_info = PySpin.CStringPtr(nodemap_tldevice.GetNode(s))
    if PySpin.IsAvailable(node_device_info) and PySpin.IsReadable(node_device_info):
        device_info = node_device_info.ToString()
    return device_info""",
            """def chunk_data_from_image(image):
    try:
        metadata = {}
        chunk_data = image.GetChunkData()

        metadata["ImageCRC"] = chunk_data.GetCRC()

        metadata["FrameID"] = chunk_data.GetFrameID()

        metadata["ExposureTime"] = chunk_data.GetExposureTime()

        metadata["Gain"] = chunk_data.GetGain()

        metadata["Height"] = chunk_data.GetHeight()

        metadata["Width"] = chunk_data.GetWidth()

        metadata["OffsetX"] = chunk_data.GetOffsetX()

        metadata["OffsetY"] = chunk_data.GetOffsetY()

        metadata["BlackLevel"] = chunk_data.GetBlackLevel()

        metadata["PixelDynamicRangeMin"] = chunk_data.GetPixelDynamicRangeMin()
        metadata["PixelDynamicRangeMax"] = chunk_data.GetPixelDynamicRangeMax()

        metadata["SequencerSetActive"] = chunk_data.GetSequencerSetActive()

        metadata["Timestamp"] = chunk_data.GetTimestamp()

    except PySpin.SpinnakerException as ex:
        logging.error(ex)
        # result = False
    return metadata
""",
        ]

    def functionGenerator(self):
        return [
            Controller.grasshopperClassCodeIndented,
            f"""
    @rpc
    def initCam(self):
        self.grasshopper = Sequence.Grasshopper()
        if not self.grasshopper.setBufferHandlingMode('OldestFirst'):
            raise Exception("couldnt set buffer mode")
        if not self.grasshopper.setFrameBufferCount({self.view.lineEdit.text()}):
            raise Exception("couldnt set buffer size")
        self.grasshopper.ArmCamera({self.view.lineEditExposure.text()}.0,0.0)
""",
        ]
