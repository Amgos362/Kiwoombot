import sys
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import pymysql
import matplotlib.pyplot as plt
import numpy as np

TR_REQ_TIME_INTERVAL = 0.7

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.time = []
        self.gangdo = []
        self.close = []
        self.index = []
        self.transaction_avg = []
        self.last_time = None

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

        if rqname == "opt10003_req":
            self._opt10003(rqname, trcode)

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

        # sMessage = self.dynamicCall("GetCommErrorMsg(QString)", trcode)
        # if "조회 과다" in sMessage:
        #     print("조회 과다로 인한 오류 발생!")
        #     sys.exit()  # 예시로 프로그램을 종료하는 코드를 넣었습니다.

    def _opt10003(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)

        for i in range(data_cnt):
            time = self._comm_get_data(trcode, "", rqname, i, "시간")
            up = self._comm_get_data(trcode, "", rqname, i, "우선매도호가단위")
            down = self._comm_get_data(trcode, "", rqname, i, "우선매수호가단위")
            gangdo = self._comm_get_data(trcode, "", rqname, i, "체결강도")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "체결거래량")
            accum_volume = self._comm_get_data(trcode, "", rqname, i, "누적거래량")
            accum_amount = self._comm_get_data(trcode, "", rqname, i, "누적거래대금")

            gangdo_value = float(gangdo)

            # gangdo 값이 200 이상이면 200으로 제한
            if gangdo_value > 200:
                gangdo_value = 200

            accum_volume = int(accum_volume)
            accum_amount = int(accum_amount)

            if accum_volume > 0:
                trans_avg = accum_amount / accum_volume
            else:
                trans_avg = 0

            self.time.append(time)
            self.gangdo.append(gangdo_value)
            self.close.append(abs(int(close)))
            self.index.append(len(self.index))
            self.transaction_avg.append(int(trans_avg))
            print(trans_avg)

        self.time = self.time[::-1]
        self.gangdo = self.gangdo[::-1]
        self.close = self.close[::-1]
        self.index = self.index[::-1]
        self.transaction_avg = self.transaction_avg[::-1]
        if self.time:
            self.last_time = self.time[-1]


    def draw_plots(self):
        fig, ax1 = plt.subplots(figsize=(20, 5))

        # gangdo 그래프 그리기
        ax1.plot(self.index, self.transaction_avg, color='tab:blue')
        ax1.set_xlabel('Index')
        ax1.set_ylabel('Transaction average', color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')

        ax2 = ax1.twinx()

        # close 그래프 그리기
        ax2.plot(self.index, self.close, color='tab:green')
        ax2.set_ylabel('Close', color='tab:green')
        ax2.tick_params(axis='y', labelcolor='tab:green')

        # close의 이동평균 20 계산 및 그래프 그리기
        close_series = pd.Series(self.close)
        ma_20 = close_series.rolling(window=20).mean().to_numpy()
        ax2.plot(self.index, ma_20, color='tab:red', label='MA20')  # 이동평균선을 빨간색으로 표시
        ax2.legend(loc="upper left")  # 범례 표시

        # 두 데이터셋의 최소 및 최대 값 구하기
        min_val = min(np.nanmin(ma_20), min(self.transaction_avg), min(self.close))
        max_val = max(np.nanmax(ma_20), max(self.transaction_avg), max(self.close))

        # 두 y축의 범위를 동일하게 설정
        ax1.set_ylim(min_val, max_val)
        ax2.set_ylim(min_val, max_val)

        fig.tight_layout()
        plt.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    code = '094170'

    try:

        # 첫 번째 요청
        kiwoom.set_input_value("종목코드", code)
        if kiwoom.last_time:
            kiwoom.set_input_value("시작시간", kiwoom.last_time)
        kiwoom.comm_rq_data("opt10003_req", "opt10003", 0, "0101")

        while kiwoom.remained_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)

            # 이전 요청에서 마지막으로 받은 첫 번째 시간을 기준으로 다음 데이터 요청
            kiwoom.set_input_value("종목코드", code)
            kiwoom.comm_rq_data("opt10003_req", "opt10003", 2, "0101")  # next를 2로 설정하여 연속데이터 요청


    except Exception as e:
        print(f"Error with code {code}: {e}")

    kiwoom.draw_plots()


