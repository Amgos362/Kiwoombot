import sys
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import pymysql

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.dates = []
        self.closes = []
        self.volumes = []
        # self.conn = pymysql.connect(host='127.0.0.1', user='root', password='Quantum45**', db='INVESTAR', charset='utf8')
        # self.cursor = self.conn.cursor()

    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)

    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _event_connect(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("disconnected")

        self.login_event_loop.exit()

    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]

    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString", rqname, trcode, next, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if next == '2':
            self.remained_data = True
        else:
            self.remained_data = False

        if rqname == "opt10079_req":
            self._opt10079(rqname, trcode)

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)

        self.last_date = self._comm_get_data(trcode, "", rqname, 0, "체결시간")
        self.yesterday = self._comm_get_data(trcode, "", rqname, 0, "전일종가")
        if int(self.last_date) <= 20230821090000:
            self.remained_data = False

        for i in range(data_cnt):
            date = self._comm_get_data(trcode, "", rqname, i, "체결시간")
            close_value = int(self._comm_get_data(trcode, "", rqname, i, "현재가"))  # Convert to integer
            volume_value = int(self._comm_get_data(trcode, "", rqname, i, "거래량"))  # Convert to integer

            # print(date, close_value, volume_value)
            print(self.yesterday)

            self.dates.append(date)  # Add the date to the list
            self.closes.append(close_value)  # Add the close value to the list
            self.volumes.append(volume_value)  # Add the volume value to the list

        # 필터링한 결과를 임시 리스트에 저장합니다.
        filtered_dates = [date for idx, date in enumerate(self.dates) if int(date) >= 20230821090000]
        filtered_closes = [self.closes[idx] for idx, date in enumerate(self.dates) if int(date) >= 20230821090000]
        filtered_volumes = [self.volumes[idx] for idx, date in enumerate(self.dates) if int(date) >= 20230821090000]

        # 원래의 리스트를 필터링된 리스트로 대체합니다.
        self.dates = filtered_dates
        self.closes = filtered_closes
        self.volumes = filtered_volumes

        print(self.closes[-10:])
        print(self.volumes[-10:])


    def calculate_gangdo(self):
        buy_volume = 0
        sell_volume = 0
        signal = 0
        # print(self.dates)
        for i in range(len(self.dates)):
            if int(self.dates[i]) >= 20230821090000:
                if i > 0:
                    if self.closes[i] > self.closes[i - 1]:
                        buy_volume += self.volumes[i]
                        signal = 0
                    elif self.closes[i] < self.closes[i - 1]:
                        sell_volume += self.volumes[i]
                        signal = 1
                    else:
                        if signal == 0:
                            buy_volume += self.volumes[i]
                        elif signal == 1:
                            sell_volume += self.volumes[i]

        gangdo = buy_volume / sell_volume * 100 if sell_volume != 0 else 0  # Added check for division by zero
        print(gangdo)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    code = '085670'

    try:
        # 첫 번째 요청
        kiwoom.set_input_value("종목코드", code)
        kiwoom.set_input_value("틱범위", 1)
        kiwoom.set_input_value("수정주가구분", 1)
        kiwoom.comm_rq_data("opt10079_req", "opt10079", 0, "0101")

        while kiwoom.remained_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)

            # 이전 요청에서 마지막으로 받은 첫 번째 시간을 기준으로 다음 데이터 요청
            kiwoom.set_input_value("종목코드", code)
            kiwoom.set_input_value("틱범위", 1)
            kiwoom.set_input_value("수정주가구분", 1)
            kiwoom.set_input_value("기준일자", kiwoom.last_date)
            kiwoom.comm_rq_data("opt10079_req", "opt10079", 2, "0101")  # next를 2로 설정하여 연속데이터 요청


    except Exception as e:
        print(f"Error with code {code}: {e}")

    kiwoom.calculate_gangdo()

